# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persistent, bounded operational event journal for the status UI.

Routine observation runs asynchronously outside the controller loop. Only
a confirmed Battery-Care emergency command-effect failure is written through
immediately using a short-timeout SQLite connection. Event state is diagnostic
and never participates in command authorization or suppression.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from measurement_db import resolve_measurement_db_path
from battery_care_stage_events import observed_care_stage, stage_label


_SENTINEL = object()
_FLAP_EVENT_TYPES = {"mqtt", "zendure_telemetry", "command_effect", "measurement_logging"}
_FLAP_COMPACT_WINDOW_S = 30 * 60


class OperationalEventJournal:
    def __init__(self, config_getter, state, *, sma_energy_meter_client=None, shelly_sampler=None) -> None:
        self.config_getter = config_getter
        self.state = state
        self.sma_energy_meter_client = sma_energy_meter_client
        self.shelly_sampler = shelly_sampler
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._previous: Dict[str, Any] = {}
        self._stable_candidates: Dict[str, Dict[str, Any]] = {}
        # Deliberately process-local: restart must re-confirm fresh distinct SOC
        # samples, while the incident itself remains persistent in SQLite.
        self._care_recovery_candidates: Dict[int, Dict[str, Any]] = {}
        self._care_stage_candidate: Optional[Dict[str, Any]] = None
        self._care_stage_schema_ready = False

    def path(self) -> str:
        cfg = self.config_getter()
        explicit = str(cfg.get("OPERATIONAL_EVENTS_DB_PATH", "") or "").strip()
        if explicit:
            return os.path.abspath(explicit)
        if os.environ.get("ZEC_INSTALLER_PREFLIGHT") == "1":
            return os.path.join(
                "/tmp", f"zec-installer-preflight-{os.getpid()}",
                "zec_operational_events.sqlite3",
            )
        base = resolve_measurement_db_path(cfg)
        return os.path.join(os.path.dirname(base), "zec_operational_events.sqlite3")

    def _connect(self, *, urgent: bool = False) -> sqlite3.Connection:
        path = self.path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path, timeout=0.2 if urgent else 1.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            # The rare confirmed emergency failure is written through with
            # FULL durability; routine polling remains NORMAL and asynchronous.
            conn.execute("PRAGMA synchronous=FULL" if urgent else "PRAGMA synchronous=NORMAL")
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
        except Exception:
            conn.close()
            raise

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="zec-operational-events", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            try:
                thread.join(timeout=3.0)
            except Exception:
                pass
            if not thread.is_alive():
                self._thread = None

    def record_admin_action(self, action: str, detail: str, values: Optional[Dict[str, Any]] = None) -> None:
        """Persist one explicit administrative action outside the control loop."""
        try:
            conn = self._connect()
            try:
                self._add(
                    conn,
                    "admin_action",
                    "info",
                    str(action),
                    str(detail),
                    dedupe_key="",
                    open_event=False,
                    values=values or {},
                    dedupe_window_s=0.0,
                )
            finally:
                conn.close()
        except Exception:
            # The audit journal is diagnostic. An unavailable journal must not
            # make an otherwise authorized admin action unsafe or half-applied.
            return

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
        """Resolve every stale open row for one live incident key.

        Older releases could leave more than one row open across restarts and
        used inconsistent or empty dedupe keys. A verified healthy live state
        therefore closes the complete canonical event-type family as well as
        the current key, so history cannot masquerade as an active fault.
        """
        now = time.time()
        cursor = conn.execute(
            """
            UPDATE operational_events
            SET ended_at=?,status='resolved',title=?,detail=?
            WHERE status='open' AND (dedupe_key=? OR event_type=?)
            """,
            (now, title, detail, dedupe_key, dedupe_key),
        )
        if cursor.rowcount:
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
        if old is _SENTINEL:
            if value in bad_values:
                self._add(
                    conn, key, severity, title_bad, detail_bad(value),
                    dedupe_key=key, open_event=True, dedupe_window_s=dedupe_window_s,
                )
            else:
                self._resolve(conn, key, title_ok, detail_ok)
            return
        if old == value:
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

    def _stable_incident(
        self,
        conn: sqlite3.Connection,
        key: str,
        is_bad: bool,
        *,
        title_bad: str,
        title_ok: str,
        detail_bad: str,
        detail_ok: str,
        severity: str = "warning",
        bad_stable_s: float = 6.0,
        ok_stable_s: float = 6.0,
    ) -> None:
        """Journal only a diagnosis state that remains stable for a short window.

        This observer-side debounce is diagnostic only.  It never feeds back into
        control, MQTT resync eligibility or command deduplication.
        """
        now = time.monotonic()
        stable_key = f"stable:{key}"
        old = self._previous.get(stable_key, _SENTINEL)
        if old is _SENTINEL:
            # A bad state already present when the observer starts must not be
            # silently treated as a healthy baseline.  Start a candidate from
            # an assumed healthy state and open it only after the same bounded
            # stability window.  A short startup flap therefore still creates
            # no event, while a persistent incident becomes visible and keeps
            # the journal/footer consistent with the current diagnosis.
            if bool(is_bad):
                self._previous[stable_key] = False
                self._stable_candidates[key] = {
                    "value": True,
                    "since": now,
                    "detail": detail_bad,
                }
            else:
                # Start from an assumed prior incident so a continuously healthy
                # live state can reconcile stale open rows after the same bounded
                # recovery window used during normal operation.
                self._previous[stable_key] = True
                self._stable_candidates[key] = {
                    "value": False,
                    "since": now,
                    "detail": detail_bad,
                }
            return
        if bool(old) == bool(is_bad):
            self._stable_candidates.pop(key, None)
            return
        candidate = self._stable_candidates.get(key)
        if not candidate or bool(candidate.get("value")) != bool(is_bad):
            self._stable_candidates[key] = {"value": bool(is_bad), "since": now, "detail": detail_bad}
            return
        candidate["detail"] = detail_bad
        threshold = bad_stable_s if is_bad else ok_stable_s
        if now - float(candidate.get("since") if candidate.get("since") is not None else now) < threshold:
            return
        self._previous[stable_key] = bool(is_bad)
        self._stable_candidates.pop(key, None)
        if is_bad:
            self._add(
                conn, key, severity, title_bad, str(candidate.get("detail") or detail_bad),
                dedupe_key=key, open_event=True, dedupe_window_s=_FLAP_COMPACT_WINDOW_S,
            )
        else:
            self._resolve(conn, key, title_ok, detail_ok)

    @staticmethod
    def _public_resync_reason(reason: str) -> str:
        value = str(reason or "").strip().upper()
        labels = {
            "RESYNC_AFTER_RECONNECT": "nach Wiederherstellung der MQTT-Verbindung",
            "RESYNC_AFTER_LONG_STALE": "nach längerer Phase veralteter Telemetriedaten",
            "RESYNC_SUPPRESSED_COOLDOWN": "wegen laufender Cooldown-Zeit nicht erneut gesendet",
        }
        if value.startswith("RESYNC_AFTER_CONFIRMED_MISMATCH"):
            return "nach bestätigter Abweichung zwischen Sollwert und Gerätewirkung"
        return labels.get(value, str(reason or "Kommunikationsunsicherheit"))

    @staticmethod
    def _care_failure_key(failure_id: str) -> str:
        # New events use an identity-specific key. Older CP18/19 rows used
        # only the event type; they remain discoverable below.
        return "battery_care_emergency_failure:" + failure_id

    @classmethod
    def _care_find_failure(cls, conn: sqlite3.Connection, failure_id: str):
        """Return the durable event for *this* ID, including legacy CP18/19.

        JSON is parsed only for historical rows without an identity-specific
        key, avoiding a runtime dependency on SQLite's optional JSON1 module.
        """
        row = conn.execute(
            "SELECT id,status,detail_json FROM operational_events "
            "WHERE event_type='battery_care_emergency_failure' AND dedupe_key=? "
            "ORDER BY id DESC LIMIT 1", (cls._care_failure_key(failure_id),),
        ).fetchone()
        if row is not None:
            return row
        for historical in conn.execute(
            "SELECT id,status,detail_json FROM operational_events "
            "WHERE event_type='battery_care_emergency_failure' "
            "AND (dedupe_key='battery_care_emergency_failure' OR dedupe_key IS NULL OR dedupe_key='')"
        ):
            try:
                values = json.loads(historical[2] or '{}')
                if isinstance(values, dict) and values.get('failure_event_id') == failure_id:
                    return historical
            except (ValueError, TypeError, AttributeError):
                continue
        return None

    def persist_confirmed_emergency_failure(self, snapshot: Dict[str, Any]) -> bool:
        """Durably write one independently confirmed emergency failure ID.

        A second emergency episode remains independent of any older open
        incident; neither ACK nor a mere publish authorizes writing. The
        routine event observer still owns SOC-based recovery for every ID.
        """
        if snapshot.get("care_emergency_failure_confirmed") is not True:
            return False
        failure_id = str(snapshot.get("care_emergency_failure_event_id") or "").strip()
        reserve = snapshot.get("care_emergency_incident_reserve_soc")
        if (not failure_id or len(failure_id) > 160 or type(reserve) is not int
                or not 0 <= reserve <= 100):
            return False
        conn = self._connect(urgent=True)
        try:
            self._observe_battery_care_incident(conn, snapshot)
            row = self._care_find_failure(conn, failure_id)
            if row is None:
                return False
            try:
                values = json.loads(row[2] or '{}')
                # A reused failure ID with a different reserve is a conflict,
                # never evidence that this new episode was persisted.
                return (isinstance(values, dict)
                        and values.get('failure_event_id') == failure_id
                        and type(values.get('incident_reserve_soc')) is int
                        and values['incident_reserve_soc'] == reserve)
            except (ValueError, TypeError, AttributeError):
                return False
        finally:
            conn.close()

    def _observe_battery_care_incident(self, conn: sqlite3.Connection, snapshot: Dict[str, Any]) -> None:
        """Serialize confirmed-failure insertion across urgent/background writers."""
        if snapshot.get("care_emergency_failure_confirmed") is True:
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                self._observe_battery_care_incident_inner(conn, snapshot)
        else:
            self._observe_battery_care_incident_inner(conn, snapshot)

    def _observe_battery_care_incident_inner(self, conn: sqlite3.Connection, snapshot: Dict[str, Any]) -> None:
        """Independently persist and recover *each* open emergency incident.

        Every row retains its own immutable incident reserve, event ID and
        separate process-local distinct-SOC candidate. One incident can close
        while another remains open at a higher reserve. Restart never carries
        tentative candidate samples to the new observer process.
        """
        event_type = "battery_care_emergency_failure"
        failed = snapshot.get("care_emergency_failure_confirmed") is True
        soc = snapshot.get("care_soc_percent")
        valid_soc = (isinstance(soc, (int, float)) and not isinstance(soc, bool)
                     and math.isfinite(float(soc)) and 0 <= soc <= 100)
        soc_fresh = snapshot.get("care_soc_fresh") is True
        sample_id = str(snapshot.get("care_soc_sample_id") or "").strip()

        if failed:
            failure_id = str(snapshot.get("care_emergency_failure_event_id") or "").strip()
            reserve = snapshot.get("care_emergency_incident_reserve_soc")
            if (failure_id and len(failure_id) <= 160 and type(reserve) is int
                    and 0 <= reserve <= 100 and self._care_find_failure(conn, failure_id) is None):
                reason = str(snapshot.get("care_emergency_failure_reason") or "Ladeanforderung ohne bestätigte Wirkung")[:400]
                values = {
                    "episode_id": str(snapshot.get("care_episode_id") or "")[:100],
                    "failure_event_id": failure_id,
                    "incident_reserve_soc": reserve,
                    "initial_failure_reason": reason,
                    "first_failure_epoch": time.time(),
                    "min_observed_soc": float(soc) if valid_soc and soc_fresh else None,
                    "charging_restored": False,
                    "recovery_observation_count": 0,
                }
                # Identity-based dedupe key, not the shared event family. Do
                # not coalesce/reopen another episode, resolved or still open.
                self._add(
                    conn, event_type, "error", "Battery Care: Notladung nicht erfolgreich",
                    f"Notladeanforderung nicht wirksam; Schutzreserve {reserve} % noch nicht wiederhergestellt. " + reason,
                    dedupe_key=self._care_failure_key(failure_id), open_event=True,
                    values=values, dedupe_window_s=0.0,
                )

        rows = conn.execute(
            "SELECT id,detail_json FROM operational_events "
            "WHERE event_type=? AND status='open' ORDER BY id", (event_type,),
        ).fetchall()
        active_ids = {int(row[0]) for row in rows}
        for row_id in list(self._care_recovery_candidates):
            if row_id not in active_ids:
                self._care_recovery_candidates.pop(row_id, None)

        for raw_id, encoded in rows:
            row_id = int(raw_id)
            try:
                values = json.loads(encoded or "{}")
                if not isinstance(values, dict):
                    values = {}
            except (ValueError, TypeError):
                values = {}
            reserve = values.get("incident_reserve_soc")
            if type(reserve) is not int or not 0 <= reserve <= 100:
                self._care_recovery_candidates.pop(row_id, None)
                continue
            modified = False
            if valid_soc and soc_fresh:
                minimum = values.get("min_observed_soc")
                if minimum is None or float(soc) < float(minimum):
                    values["min_observed_soc"] = float(soc)
                    modified = True
            if snapshot.get("care_physical_charge_confirmed") is True and not values.get("charging_restored"):
                values["charging_restored"] = True
                values["charging_restored_epoch"] = time.time()
                modified = True

            if not (valid_soc and soc_fresh and sample_id and float(soc) >= reserve):
                self._care_recovery_candidates.pop(row_id, None)
                if modified:
                    label = (f"Ladung wiederhergestellt – Schutzreserve {reserve} % noch nicht erreicht."
                             if values.get("charging_restored") else
                             f"Schutzreserve {reserve} % noch nicht wiederhergestellt.")
                    conn.execute(
                        "UPDATE operational_events SET detail=?,detail_json=? WHERE id=? AND status='open'",
                        (label, json.dumps(values, ensure_ascii=False), row_id),
                    )
                    conn.commit()
                continue

            now = time.monotonic()
            c = self._care_recovery_candidates.get(row_id)
            if c is None or now < c.get("started_mono", now):
                c = {"started_mono": now, "count": 0, "last_id": None}
                self._care_recovery_candidates[row_id] = c
            if sample_id != c.get("last_id"):
                c["count"] += 1
                c["last_id"] = sample_id
            if c["count"] >= 2 and now - c["started_mono"] >= 3.0:
                values["recovery_observation_count"] = c["count"]
                values["recovery_reserve_soc"] = reserve
                values["recovery_soc"] = float(soc)
                values["resolved_epoch"] = time.time()
                conn.execute(
                    """UPDATE operational_events SET ended_at=?,status='resolved',
                           title=?,detail=?,detail_json=? WHERE id=? AND status='open'""",
                    (time.time(), "Battery Care: Schutzreserve wiederhergestellt",
                     f"Schutzreserve {reserve} % mit unabhängigen frischen SOC-Proben bestätigt.",
                     json.dumps(values, ensure_ascii=False), row_id),
                )
                conn.commit()
                self._care_recovery_candidates.pop(row_id, None)
            elif modified:
                conn.execute(
                    "UPDATE operational_events SET detail_json=? WHERE id=? AND status='open'",
                    (json.dumps(values, ensure_ascii=False), row_id),
                )
                conn.commit()

    def _observe_battery_care_stage(self, conn: sqlite3.Connection, snapshot: Dict[str, Any]) -> None:
        """Persist confirmed *dispatch/policy* transitions, never inferred effect.

        Two different completed controller cycles must agree. SQLite's stable
        cursor suppresses duplicate entry markers after journal/process restart.
        The transition row and cursor advance in one short transaction; a DB
        failure does not advance the process-local confirmation candidate.
        """
        stage = observed_care_stage(snapshot)
        if stage is None:
            return
        cycle = int(snapshot["loop_counter"])
        floor_raw = snapshot.get("care_effective_discharge_floor_soc") if snapshot.get("care_policy_valid") is True else None
        floor = (float(floor_raw) if isinstance(floor_raw, (int, float))
                 and not isinstance(floor_raw, bool) and math.isfinite(float(floor_raw))
                 and 0 <= float(floor_raw) <= 100 else None)
        candidate = self._care_stage_candidate
        if candidate is None or candidate["stage"] != stage or candidate["floor"] != floor:
            self._care_stage_candidate = {"stage": stage, "floor": floor, "cycle": cycle, "count": 1}
            return
        if cycle == candidate["cycle"]:
            return  # polling same control cycle is NOT independent evidence
        if cycle < candidate["cycle"]:
            self._care_stage_candidate = {"stage": stage, "floor": floor, "cycle": cycle, "count": 1}
            return
        candidate["cycle"] = cycle
        candidate["count"] += 1
        if candidate["count"] < 2:
            return
        if not self._care_stage_schema_ready:
            conn.execute("""CREATE TABLE IF NOT EXISTS battery_care_stage_cursor (
                            id INTEGER PRIMARY KEY CHECK(id=1), stage TEXT NOT NULL,
                            last_event_id INTEGER, changed_at REAL NOT NULL,
                            floor_soc REAL)""")
            conn.commit()
            self._care_stage_schema_ready = True
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            stored = conn.execute("SELECT stage,floor_soc FROM battery_care_stage_cursor WHERE id=1").fetchone()
            before = str(stored[0]) if stored else "NONE"
            previous_floor = float(stored[1]) if stored and stored[1] is not None else None
            if (before == stage and previous_floor == floor) or (stored is None and stage in ("NONE", "STOP_HOLD")):
                return
            # Only record real policy/dispatch changes, not a generic STOP
            # that occurred before Battery Care had ever been active.
            values = {
                "stage_from": before, "stage_to": stage,
                "floor_from_soc": previous_floor, "floor_to_soc": floor,
                "controller_cycle_id": cycle,
                "observed_mode": str(snapshot.get("current_mode") or "")[:50],
                "requested_power_w": (int(snapshot["care_dispatched_target_w"])
                                      if stage.endswith("REQUESTED") else 0),
                "policy_floor_soc": (float(snapshot["care_effective_discharge_floor_soc"])
                                     if snapshot.get("care_policy_valid") is True and
                                     isinstance(snapshot.get("care_effective_discharge_floor_soc"), (int, float))
                                     and not isinstance(snapshot.get("care_effective_discharge_floor_soc"), bool)
                                     else None),
                "source": "distinct_completed_controller_cycles",
                "physical_effect_confirmed": False,
            }
            now = time.time()
            title = "Battery Care: Stufenwechsel"
            detail = (f"Wirksame Policy-Untergrenze {previous_floor:g} → {floor:g} % (keine Hardwarebestätigung)"
                      if before == stage and floor is not None and previous_floor is not None else
                      f"{stage_label(before)} → {stage_label(stage)} (Regleranforderung, nicht Gerätewirkung)")
            cur = conn.execute("""INSERT INTO operational_events (
                              event_type,severity,title,detail,started_at,ended_at,status,dedupe_key,detail_json)
                              VALUES (?,?,?,?,?,?,?,?,?)""",
                              ("battery_care_stage_transition", "info", title, detail,
                               now, now, "resolved", "", json.dumps(values, ensure_ascii=False)))
            conn.execute("""INSERT INTO battery_care_stage_cursor(id,stage,last_event_id,changed_at,floor_soc)
                            VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                            stage=excluded.stage,last_event_id=excluded.last_event_id,
                            changed_at=excluded.changed_at,floor_soc=excluded.floor_soc""",
                         (stage, int(cur.lastrowid), now, floor))

    def _observe(self, conn: sqlite3.Connection, s: Dict[str, Any]) -> None:
        self._observe_battery_care_incident(conn, s)
        self._observe_battery_care_stage(conn, s)
        mode = str(s.get("current_mode") or "")
        old_mode = self._previous.get("mode")
        self._previous["mode"] = mode
        if old_mode and old_mode != mode:
            # Mode changes are individually meaningful and are not flap-merged.
            self._add(conn, "mode", "info", "Betriebsmodus geändert", f"{old_mode} → {mode}")

        mqtt = bool(s.get("mqtt_connected"))
        old_mqtt = self._previous.get("mqtt_connected")
        self._previous["mqtt_connected"] = mqtt
        if old_mqtt is None:
            if mqtt:
                self._resolve(
                    conn, "mqtt", "MQTT-Verbindung wiederhergestellt",
                    "Brokerverbindung ist wieder aktiv.",
                )
            else:
                self._add(
                    conn, "mqtt", "error", "MQTT-Verbindung getrennt",
                    "Keine Verbindung zum MQTT-Broker.", dedupe_key="mqtt",
                    open_event=True, dedupe_window_s=_FLAP_COMPACT_WINDOW_S,
                )
        elif old_mqtt != mqtt:
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

        # A frozen control-loop grid sample is an operational incident even if
        # the SMA receiver remains healthy. Never depend on run_once to report it.
        cfg = self.config_getter()
        meter_source = str(cfg.get("GRID_METER_SOURCE") or "shelly_http")
        timeout_s = float(cfg.get("SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS", 15) if meter_source == "sma_energy_meter_udp" else cfg.get("SHELLY_STALE_TIMEOUT_SECONDS", 15) or 15)
        age_s = s.get("grid_power_age_seconds")
        # On startup / source replacement there may never have been a valid
        # grid sample.  A missing timestamp must not suppress incidents for
        # hours.  Only report once the configured source had time to become
        # available; the observer's existing hysteresis handles debounce.
        no_sample = age_s is None and s.get("grid_power_valid") is False
        startup_epoch = s.get("startup_epoch", getattr(self.state, "startup_epoch", None))
        startup_age_s = None
        try:
            if startup_epoch is not None:
                startup_age_s = max(0.0, time.time() - float(startup_epoch))
        except (TypeError, ValueError, OverflowError):
            pass
        no_sample_overdue = bool(no_sample and startup_age_s is not None and startup_age_s > timeout_s)
        try:
            bad_grid = (age_s is not None and float(age_s) > timeout_s) or no_sample_overdue
        except (ValueError, TypeError, OverflowError):
            bad_grid = no_sample_overdue
        controller_path = "GRID_NEVER_RECEIVED" if no_sample_overdue else "CONTROLLER_PROCESSING_OR_SOURCE_STALE"
        if bad_grid and meter_source == "sma_energy_meter_udp" and self.sma_energy_meter_client is not None:
            try:
                source_epoch = self.sma_energy_meter_client.snapshot().last_received_epoch
                if source_epoch is not None:
                    source_age_s = max(0.0, time.time() - float(source_epoch))
                    controller_path = "CONTROLLER_PROCESSING_STALE" if source_age_s <= timeout_s else "SMA_SOURCE_STALE"
            except Exception:
                controller_path = "SMA_SOURCE_STATUS_UNKNOWN"
        elif bad_grid and meter_source == "shelly_http" and self.shelly_sampler is not None:
            try:
                source_epoch = self.shelly_sampler.snapshot().last_received_epoch
                if source_epoch is not None:
                    source_age_s = max(0.0, time.time() - float(source_epoch))
                    controller_path = "CONTROLLER_PROCESSING_STALE" if source_age_s <= timeout_s else "SHELLY_SOURCE_STALE"
            except Exception:
                controller_path = "SHELLY_SOURCE_STATUS_UNKNOWN"
        reason = str(s.get("grid_power_validity_reason") or "GRID_STALE")
        # Older/unit snapshots without a grid field are NOT an active grid
        # incident. Avoid a synthetic event or extra debounce clocks.
        if age_s is not None or no_sample_overdue or "stable:grid_telemetry_stale" in self._previous:
            age_label = f"{age_s} s alt" if age_s is not None else "nie empfangen (Quelle überfällig)"
            self._stable_incident(
                conn, "grid_telemetry_stale", bool(bad_grid),
                title_bad="Netzleistungsdaten nicht aktuell",
                title_ok="Netzleistungsdaten wieder aktuell",
                detail_bad=f"Netzleistung {age_label}; Quelle {meter_source}; Diagnose {controller_path}; Zustand {mode}; Grund {reason}",
                detail_ok="Controller-Netzleistungsdaten werden wieder innerhalb des zulässigen Zeitfensters aktualisiert.",
                severity="error", bad_stable_s=6.0, ok_stable_s=4.0,
            )

        tele = str(s.get("zendure_mqtt_overall_status") or "")
        bad = {
            "ZENDURE_MQTT_STALE",
            "ZENDURE_MQTT_PARTIAL_STALE",
            "ZENDURE_MQTT_RETAINED_ONLY",
            "ZENDURE_MQTT_AFTER_BROKER_RESTART_NO_LIVE_UPDATES",
        }
        self._stable_incident(
            conn,
            "zendure_telemetry",
            tele in bad,
            title_bad="Zendure-Telemetrie nicht aktuell",
            title_ok="Zendure-Telemetrie wieder aktuell",
            detail_bad=str(s.get("zendure_mqtt_status_reason") or tele),
            detail_ok="Datenversorgung vollständig wiederhergestellt.",
            severity="warning",
            bad_stable_s=6.0,
            ok_stable_s=6.0,
        )

        effect = str(s.get("command_effect_state_category") or s.get("command_effect_category") or "")
        # Telemetry can become uncertain after a mismatch was already confirmed.
        # The open physical-effect incident must remain open until a later
        # independent observation confirms recovery; loss of observability is
        # not recovery.
        if bool(s.get("command_not_effective_active")) and effect not in {
            "COMMAND_MISMATCH_CONFIRMED",
            "COMMAND_NEUTRALIZATION_MISMATCH",
            "COMMAND_RECOVERY_VERIFYING",
        }:
            effect = "COMMAND_MISMATCH_CONFIRMED"
        bad_effect = {
            "not_effective", "command_not_effective", "uncertain",
            "COMMAND_MISMATCH_CONFIRMED", "COMMAND_NEUTRALIZATION_MISMATCH",
            "COMMAND_RECOVERY_VERIFYING",
        }
        mismatch_resolution = str(s.get("command_mismatch_resolution") or "")
        if mismatch_resolution == "MISMATCH_SUPERSEDED_BY_SAFETY_NEUTRALIZATION":
            command_title_ok = "Zendure-Mismatch durch Schutzneutralisierung beendet"
            command_detail_ok = "Der vorherige Lade-/Entladeintent wurde nicht als wiederhergestellt gewertet; ein neuer sicherheitsrelevanter 0-W-Intent hat ihn abgelöst."
        elif mismatch_resolution == "MISMATCH_ABORTED_BY_INTENT_CHANGE":
            command_title_ok = "Zendure-Mismatch durch Intentwechsel beendet"
            command_detail_ok = "Der vorherige Intent wurde legitim abgelöst und nicht als physisch wiederhergestellt gewertet."
        elif mismatch_resolution == "MISMATCH_RECLASSIFIED_AS_CHARGE_ACCEPTANCE_LIMITED":
            command_title_ok = "Zendure-Mismatch als Ladeannahmebegrenzung reklassifiziert"
            command_detail_ok = "Laderichtung und Batterieladung sind bestätigt; die reduzierte Leistung wird als High-SOC-/BMS-Ladeannahmebegrenzung bewertet."
        else:
            command_title_ok = "Zendure-Kommandowirkung wiederhergestellt"
            command_detail_ok = "Die physische Gerätewirkung wurde wieder bestätigt."
        self._transition(
            conn,
            "command_effect",
            effect,
            bad_effect,
            "Zendure-Kommando nicht wirksam",
            command_title_ok,
            lambda v: str(s.get("command_not_effective_reason") or s.get("command_effect_reason") or v),
            detail_ok=command_detail_ok,
            severity="error",
            dedupe_window_s=_FLAP_COMPACT_WINDOW_S,
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
            if status == "open":
                item["title"] = "Zendure-Kommando nicht wirksam"
            elif not str(item.get("title") or "").strip():
                item["title"] = "Zendure-Kommandowirkung wiederhergestellt"
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
        conn: Optional[sqlite3.Connection] = None
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
            while not self._stop.wait(2.0):
                try:
                    self._observe(conn, self.state.snapshot())
                except Exception:
                    # The journal is deliberately best-effort and must never affect
                    # the controller or the web status route.
                    pass
        except Exception:
            return
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def list_recent(self, days: int = 2, limit: int = 250) -> List[Dict[str, Any]]:
        conn: Optional[sqlite3.Connection] = None
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
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass


def read_recent_events(config: Dict[str, Any], days: int = 2, limit: int = 250) -> List[Dict[str, Any]]:
    class _Dummy:
        def snapshot(self):
            return {}

    journal = OperationalEventJournal(lambda: config, _Dummy())
    return journal.list_recent(days=days, limit=limit)
