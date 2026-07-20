# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persistent, bounded operational event journal for the status UI.

The observer runs in a daemon thread outside the controller loop. It only reads
state snapshots and writes through its own SQLite connection.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from measurement_db import resolve_measurement_db_path


class OperationalEventJournal:
    def __init__(self, config_getter, state) -> None:
        self.config_getter = config_getter
        self.state = state
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._previous: Dict[str, Any] = {}

    def path(self) -> str:
        cfg = self.config_getter()
        explicit = str(cfg.get("OPERATIONAL_EVENTS_DB_PATH", "") or "").strip()
        if explicit:
            return os.path.abspath(explicit)
        base = resolve_measurement_db_path(cfg)
        return os.path.join(os.path.dirname(base), "zec_operational_events.sqlite3")

    def _connect(self) -> sqlite3.Connection:
        path = self.path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path, timeout=1.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
          CREATE TABLE IF NOT EXISTS operational_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL,
            started_at REAL NOT NULL,
            ended_at REAL,
            status TEXT NOT NULL,
            dedupe_key TEXT,
            detail_json TEXT,
            occurrence_count INTEGER NOT NULL DEFAULT 1
          )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_operational_events_started ON operational_events(started_at DESC)")
        conn.commit()
        return conn

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="zec-operational-events", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _add(self, conn: sqlite3.Connection, event_type: str, severity: str, title: str, detail: str, *, dedupe_key: str = "", open_event: bool = False, values: Optional[Dict[str, Any]] = None) -> None:
        now = time.time()
        if dedupe_key:
            recent = conn.execute("SELECT id,started_at,occurrence_count FROM operational_events WHERE dedupe_key=? ORDER BY id DESC LIMIT 1", (dedupe_key,)).fetchone()
            if recent and now - float(recent[1]) < 30:
                conn.execute("UPDATE operational_events SET occurrence_count=?, detail=?, detail_json=? WHERE id=?", (int(recent[2])+1, detail, json.dumps(values or {}, ensure_ascii=False), recent[0]))
                conn.commit(); return
        conn.execute("INSERT INTO operational_events(event_type,severity,title,detail,started_at,ended_at,status,dedupe_key,detail_json) VALUES(?,?,?,?,?,?,?,?,?)", (event_type,severity,title,detail,now,None if open_event else now,"open" if open_event else "resolved",dedupe_key,json.dumps(values or {},ensure_ascii=False)))
        conn.commit()
        conn.execute("DELETE FROM operational_events WHERE id IN (SELECT id FROM operational_events WHERE status='resolved' ORDER BY started_at DESC LIMIT -1 OFFSET 10000)")
        conn.commit()

    def _resolve(self, conn: sqlite3.Connection, dedupe_key: str, title: str, detail: str) -> None:
        row = conn.execute("SELECT id,started_at FROM operational_events WHERE dedupe_key=? AND status='open' ORDER BY id DESC LIMIT 1", (dedupe_key,)).fetchone()
        now = time.time()
        if row:
            conn.execute("UPDATE operational_events SET ended_at=?,status='resolved',title=?,detail=? WHERE id=?", (now,title,detail,row[0]))
            conn.commit()

    def _transition(self, conn, key, value, bad_values, title_bad, title_ok, detail_bad, severity="warning"):
        old = self._previous.get(key, object())
        self._previous[key] = value
        if old == value or old.__class__ is object:
            return
        if value in bad_values:
            self._add(conn,key,severity,title_bad,detail_bad(value),dedupe_key=key,open_event=True)
        elif old in bad_values:
            self._resolve(conn,key,title_ok,"Zustand wieder normal.")

    def _observe(self, conn: sqlite3.Connection, s: Dict[str, Any]) -> None:
        mode = str(s.get("current_mode") or "")
        old_mode = self._previous.get("mode")
        self._previous["mode"] = mode
        if old_mode and old_mode != mode:
            self._add(conn,"mode","info","Betriebsmodus geändert",f"{old_mode} → {mode}",dedupe_key="mode")

        mqtt = bool(s.get("mqtt_connected"))
        old_mqtt = self._previous.get("mqtt_connected")
        self._previous["mqtt_connected"] = mqtt
        if old_mqtt is not None and old_mqtt != mqtt:
            if not mqtt:
                self._add(conn,"mqtt","error","MQTT-Verbindung getrennt","Keine Verbindung zum MQTT-Broker.",dedupe_key="mqtt",open_event=True)
            else:
                self._resolve(conn,"mqtt","MQTT-Verbindung wiederhergestellt","Brokerverbindung ist wieder aktiv.")

        tele = str(s.get("zendure_mqtt_overall_status") or "")
        bad = {"ZENDURE_MQTT_STALE","ZENDURE_MQTT_PARTIAL_STALE","ZENDURE_MQTT_RETAINED_ONLY","ZENDURE_MQTT_AFTER_BROKER_RESTART_NO_LIVE_UPDATES"}
        self._transition(conn,"zendure_telemetry",tele,bad,"Zendure-Telemetrie nicht aktuell","Zendure-Telemetrie wieder aktuell",lambda v: str(s.get("zendure_mqtt_status_reason") or v),"warning")

        effect = str(s.get("command_effect_state_category") or s.get("command_effect_category") or "")
        bad_effect = {"not_effective","command_not_effective","uncertain"}
        self._transition(conn,"command_effect",effect,bad_effect,"Zendure-Kommando nicht bestätigt","Zendure-Kommando wieder wirksam",lambda v: str(s.get("command_not_effective_reason") or s.get("command_effect_reason") or v),"error")

        resync_count = int(s.get("command_resync_count") or 0)
        old_count = int(self._previous.get("resync_count") or 0)
        self._previous["resync_count"] = resync_count
        if resync_count > old_count:
            reason = str(s.get("command_resync_reason") or "Kommunikationsunsicherheit")
            target = int(s.get("command_uncertain_mqtt_target_w") or s.get("zendure_target_signed_power") or 0)
            self._add(conn,"command_resync","info","Zendure-Kommandoabgleich ausgeführt",f"AC-Modus und Lade-/Entladelimits für Soll {target:+d} W erneut gesendet · {reason}",dedupe_key="command_resync")

        log_status = str(s.get("measurement_log_status") or "")
        self._transition(conn,"measurement_logging",log_status,{"error","fallback"},"Messdaten-Logging eingeschränkt","Messdaten-Logging wiederhergestellt",lambda v: str(s.get("measurement_log_status_reason") or v),"warning")

    def _run(self) -> None:
        try:
            conn = self._connect()
            self._add(conn,"controller_start","info","Controller-Weboberfläche gestartet",datetime.now().strftime("Start am %d.%m.%Y um %H:%M:%S"),dedupe_key="controller_start")
        except Exception:
            return
        while not self._stop.wait(2.0):
            try:
                self._observe(conn, self.state.snapshot())
            except Exception:
                pass
        try: conn.close()
        except Exception: pass

    def list_recent(self, days: int = 2, limit: int = 250) -> List[Dict[str, Any]]:
        try:
            conn = self._connect()
            since = time.time() - max(1, days) * 86400
            rows = conn.execute("SELECT id,event_type,severity,title,detail,started_at,ended_at,status,occurrence_count FROM operational_events WHERE started_at>=? OR status='open' ORDER BY CASE WHEN status='open' THEN 0 ELSE 1 END, started_at DESC LIMIT ?", (since, limit)).fetchall()
            conn.close()
            keys = ["id","event_type","severity","title","detail","started_at","ended_at","status","occurrence_count"]
            return [dict(zip(keys,row)) for row in rows]
        except Exception:
            return []

def read_recent_events(config: Dict[str, Any], days: int = 2, limit: int = 250) -> List[Dict[str, Any]]:
    class _Dummy:
        def snapshot(self): return {}
    journal = OperationalEventJournal(lambda: config, _Dummy())
    return journal.list_recent(days=days, limit=limit)
