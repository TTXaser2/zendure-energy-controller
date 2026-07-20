# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persistent, bounded operational event journal for the status UI.

The observer runs in a daemon thread outside the controller loop. It only reads
state snapshots and writes through its own SQLite connection. Event state is
strictly diagnostic and never participates in controller decisions or command
suppression.
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


_SENTINEL = object()
_FLAP_EVENT_TYPES = {"mqtt", "zendure_telemetry", "command_effect", "measurement_logging"}
_FLAP_COMPACT_WINDOW_S = 30 * 60


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
        conn.execute(
            """
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
        """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_operational_events_started ON operational_events(started_at DESC)")
        conn.commit()
        return conn

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="zec-operational-events", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _add(
        self,
        conn: sqlite3.Connection,
        event_type: str,
        severity: str,
        title: str,
        detail: str,
        *,
        dedupe_key: str = "",
        open_event: bool = False,
        values: Optional[Dict[str, Any]] = None,
        dedupe_window_s: float = 30.0,
    ) -> None:
        """Insert or safely merge a diagnostic event.

        A repeated open incident may reopen a recently resolved row. When that
        happens all semantic fields are updated together (title, severity,
        status and end time). This prevents the RC5 contradiction where a row
        titled "wieder aktuell" could later contain a new stale reason while
        still remaining resolved.
        """
        now = time.time()
        encoded_values = json.dumps(values or {}, ensure_ascii=False)
        if dedupe_key and dedupe_window_s > 0:
            recent = conn.execute(
                """
                SELECT id,started_at,status,occurrence_count
                FROM operational_events
                WHERE dedupe_key=?
                ORDER BY id DESC
                LIMIT 1
                """,
                (dedupe_key,),
            ).fetchone()
            if recent and now - float(recent[1]) < float(dedupe_window_s):
                if open_event:
                    reopened_started_at = now if str(recent[2]) != "open" else float(recent[1])
                    conn.execute(
                        """
                        UPDATE operational_events
                        SET event_type=?,severity=?,title=?,detail=?,started_at=?,ended_at=NULL,
                            status='open',detail_json=?,occurrence_count=?
                        WHERE id=?
                        """,
                        (
                            event_type,
                            severity,
                            title,
                            detail,
                            reopened_started_at,
                            encoded_values,
                            int(recent[3]) + 1,
                            recent[0],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE operational_events
                        SET event_type=?,severity=?,title=?,detail=?,ended_at=?,
                            status='resolved',detail_json=?,occurrence_count=?
                        WHERE id=?
                        """,
                        (
                            event_type,
                            severity,
                            title,
                            detail,
                            now,
                            encoded_values,
                            int(recent[3]) + 1,
                            recent[0],
                        ),
                    )
                conn.commit()
                return
        conn.execute(
            """
            INSERT INTO operational_events(
              event_type,severity,title,detail,started_at,ended_at,status,
              dedupe_key,detail_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                event_type,
                severity,
                title,
                detail,
                now,
                None if open_event else now,
                "open" if open_event else "resolved",
                dedupe_key,
                encoded_values,
            ),
        )
        conn.commit()
        conn.execute(
            """
            DELETE FROM operational_events
            WHERE id IN (
              SELECT id FROM operational_events
              WHERE status='resolved'
              ORDER BY started_at DESC
              LIMIT -1 OFFSET 10000
            )
            """
        )
        conn.commit()

    def _resolve(self, conn: sqlite3.Connection, dedupe_key: str, title: str, detail: str) -> None:
        row = conn.execute(
            """
            SELECT id,started_at
            FROM operational_events
            WHERE dedupe_key=? AND status='open'
            ORDER BY id DESC
            LIMIT 1
            """,
            (dedupe_key,),
        ).fetchone()
        now = time.time()
        if row:
            conn.execute(
                """
                UPDATE operational_events
                SET ended_at=?,status='resolved',title=?,detail=?
                WHERE id=?
                """,
                (now, title, detail, row[0]),
            )
            conn.commit()

    def _transition(
        self,
        conn: sqlite3.Connection,
        key: str,
        value: Any,
        bad_values,
        title_bad: str,
        title_ok: str,
        detail_bad,
        *,
        detail_ok: str = "Zustand wieder normal.",
        severity: str = "warning",
        dedupe_window_s: float = _FLAP_COMPACT_WINDOW_S,
    ) -> None:
        old = self._previous.get(key, _SENTINEL)
        self._previous[key] = value
        if old is _SENTINEL or old == value:
            return
        was_bad = old in bad_values
        is_bad = value in bad_values
        if is_bad and not was_bad:
            self._add(
                conn,
                key,
                severity,
                title_bad,
                detail_bad(value),
                dedupe_key=key,
                open_event=True,
                dedupe_window_s=dedupe_window_s,
            )
        elif is_bad and was_bad:
            # Different technical bad states belong to the same open incident.
            self._add(
                conn,
                key,
                severity,
                title_bad,
                detail_bad(value),
                dedupe_key=key,
                open_event=True,
                dedupe_window_s=dedupe_window_s,
            )
        elif was_bad and not is_bad:
            self._resolve(conn, key, title_ok, detail_ok)

    def _observe(self, conn: sqlite3.Connection, s: Dict[str, Any]) -> None:
        mode = str(s.get("current_mode") or "")
        old_mode = self._previous.get("mode")
        self._previous["mode"] = mode
        if old_mode and old_mode != mode:
            # Mode changes are individually meaningful and are not flap-merged.
            self._add(conn, "mode", "info", "Betriebsmodus geändert", f"{old_mode} → {mode}")

        mqtt = bool(s.get("mqtt_connected"))
        old_mqtt = self._previous.get("mqtt_connected")
        self._previous["mqtt_connected"] = mqtt
        if old_mqtt is not None and old_mqtt != mqtt:
            if not mqtt:
                self._add(
                    conn,
                    "mqtt",
                    "error",
                    "MQTT-Verbindung getrennt",
                    "Keine Verbindung zum MQTT-Broker.",
                    dedupe_key="mqtt",
                    open_event=True,
                    dedupe_window_s=_FLAP_COMPACT_WINDOW_S,
                )
            else:
                self._resolve(
                    conn,
                    "mqtt",
                    "MQTT-Verbindung wiederhergestellt",
                    "Brokerverbindung ist wieder aktiv.",
                )

        tele = str(s.get("zendure_mqtt_overall_status") or "")
        bad = {
            "ZENDURE_MQTT_STALE",
            "ZENDURE_MQTT_PARTIAL_STALE",
            "ZENDURE_MQTT_RETAINED_ONLY",
            "ZENDURE_MQTT_AFTER_BROKER_RESTART_NO_LIVE_UPDATES",
        }
        self._transition(
            conn,
            "zendure_telemetry",
            tele,
            bad,
            "Zendure-Telemetrie nicht aktuell",
            "Zendure-Telemetrie wieder aktuell",
            lambda v: str(s.get("zendure_mqtt_status_reason") or v),
            detail_ok="Datenversorgung vollständig wiederhergestellt.",
            severity="warning",
            dedupe_window_s=_FLAP_COMPACT_WINDOW_S,
        )

        effect = str(s.get("command_effect_state_category") or s.get("command_effect_category") or "")
        bad_effect = {"not_effective", "command_not_effective", "uncertain"}
        self._transition(
            conn,
            "command_effect",
            effect,
            bad_effect,
            "Zendure-Kommando nicht bestätigt",
            "Zendure-Kommando wieder wirksam",
            lambda v: str(s.get("command_not_effective_reason") or s.get("command_effect_reason") or v),
            detail_ok="Sollwert und Gerätewirkung stimmen wieder plausibel überein.",
            severity="error",
            dedupe_window_s=_FLAP_COMPACT_WINDOW_S,
        )

        resync_count = int(s.get("command_resync_count") or 0)
        old_count = int(self._previous.get("resync_count") or 0)
        self._previous["resync_count"] = resync_count
        if resync_count > old_count:
            reason = str(s.get("command_resync_reason") or "Kommunikationsunsicherheit")
            target = int(s.get("command_uncertain_mqtt_target_w") or s.get("zendure_target_signed_power") or 0)
            self._add(
                conn,
                "command_resync",
                "info",
                "Zendure-Kommandoabgleich ausgeführt",
                f"AC-Modus und Lade-/Entladelimits für Soll {target:+d} W erneut gesendet · {reason}",
                dedupe_key="command_resync",
                dedupe_window_s=5 * 60,
            )

        log_status = str(s.get("measurement_log_status") or "")
        self._transition(
            conn,
            "measurement_logging",
            log_status,
            {"error", "fallback"},
            "Messdaten-Logging eingeschränkt",
            "Messdaten-Logging wiederhergestellt",
            lambda v: str(s.get("measurement_log_status_reason") or v),
            detail_ok="Messdatenspeicherung arbeitet wieder über das reguläre Ziel.",
            severity="warning",
            dedupe_window_s=_FLAP_COMPACT_WINDOW_S,
        )

    @staticmethod
    def _normalise_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """Repair RC5 semantic display contradictions without rewriting history."""
        item = dict(row)
        event_type = str(item.get("event_type") or "")
        status = str(item.get("status") or "")
        detail = str(item.get("detail") or "")
        if event_type == "zendure_telemetry":
            if status == "open":
                item["title"] = "Zendure-Telemetrie nicht aktuell"
            else:
                item["title"] = "Zendure-Telemetrie wieder aktuell"
                if not detail.lower().startswith(("datenversorgung", "zustand wieder")):
                    item["detail"] = f"Datenversorgung vollständig wiederhergestellt · zuvor: {detail}"
                elif detail == "Zustand wieder normal.":
                    item["detail"] = "Datenversorgung vollständig wiederhergestellt."
        elif event_type == "mqtt":
            item["title"] = "MQTT-Verbindung getrennt" if status == "open" else "MQTT-Verbindung wiederhergestellt"
        elif event_type == "command_effect":
            item["title"] = "Zendure-Kommando nicht bestätigt" if status == "open" else "Zendure-Kommando wieder wirksam"
        elif event_type == "measurement_logging":
            item["title"] = "Messdaten-Logging eingeschränkt" if status == "open" else "Messdaten-Logging wiederhergestellt"
        return item

    @staticmethod
    def _compact_for_display(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collapse RC5 flap rows into one readable incident per 30-minute window."""
        compacted: List[Dict[str, Any]] = []
        by_key: Dict[tuple, int] = {}
        for raw in rows:
            row = OperationalEventJournal._normalise_row(raw)
            event_type = str(row.get("event_type") or "")
            status = str(row.get("status") or "")
            if event_type not in _FLAP_EVENT_TYPES:
                compacted.append(row)
                continue
            key = (event_type, status)
            existing_index = by_key.get(key)
            if existing_index is not None:
                existing = compacted[existing_index]
                newest = float(existing.get("started_at") or 0)
                current = float(row.get("started_at") or 0)
                if newest - current <= _FLAP_COMPACT_WINDOW_S:
                    existing["occurrence_count"] = int(existing.get("occurrence_count") or 1) + int(row.get("occurrence_count") or 1)
                    continue
            by_key[key] = len(compacted)
            compacted.append(row)
        return compacted

    def _run(self) -> None:
        try:
            conn = self._connect()
            self._add(
                conn,
                "controller_start",
                "info",
                "Controller-Weboberfläche gestartet",
                datetime.now().strftime("Start am %d.%m.%Y um %H:%M:%S"),
                dedupe_key="controller_start",
            )
        except Exception:
            return
        while not self._stop.wait(2.0):
            try:
                self._observe(conn, self.state.snapshot())
            except Exception:
                # The journal is deliberately best-effort and must never affect
                # the controller or the web status route.
                pass
        try:
            conn.close()
        except Exception:
            pass

    def list_recent(self, days: int = 2, limit: int = 250) -> List[Dict[str, Any]]:
        try:
            conn = self._connect()
            since = time.time() - max(1, days) * 86400
            rows = conn.execute(
                """
                SELECT id,event_type,severity,title,detail,started_at,ended_at,status,occurrence_count
                FROM operational_events
                WHERE started_at>=? OR status='open'
                ORDER BY CASE WHEN status='open' THEN 0 ELSE 1 END, started_at DESC
                LIMIT ?
                """,
                (since, limit),
            ).fetchall()
            conn.close()
            keys = [
                "id",
                "event_type",
                "severity",
                "title",
                "detail",
                "started_at",
                "ended_at",
                "status",
                "occurrence_count",
            ]
            items = [dict(zip(keys, row)) for row in rows]
            return self._compact_for_display(items)
        except Exception:
            return []


def read_recent_events(config: Dict[str, Any], days: int = 2, limit: int = 250) -> List[Dict[str, Any]]:
    class _Dummy:
        def snapshot(self):
            return {}

    journal = OperationalEventJournal(lambda: config, _Dummy())
    return journal.list_recent(days=days, limit=limit)
