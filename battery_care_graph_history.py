# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only historical Battery-Care SOC overlays and confirmed incident markers.

The overlay NEVER infers past Care settings from the present configuration.
Historical lines mean a configured seasonal AUTO policy floor, NOT a proven
physical discharge/charge effect or an undisclosed app/BMS hard limit.
"""
from __future__ import annotations

from datetime import date, datetime
import json
import math
import os
import sqlite3
from typing import Any, Mapping, Sequence

from battery_care_policy import in_care_season
from battery_care_stage_events import STAGES
from measurement_db import resolve_measurement_db_path


def _confirmed_mode_intervals(points: Sequence[Mapping[str, Any]], accepted_mode: str) -> list[tuple[float, float]]:
    """Bounded visualization intervals from actual historical operating-mode samples.

    No interpolation through STOP, unknown modes or measurement gaps >3 min.
    Endpoints are anchored at observed samples, not at the end of a day.
    """
    valid = []
    for row in points:
        try:
            minute = float(row.get("minute"))
            mode = str(row.get("mode") or "").strip().upper()
            if math.isfinite(minute) and 0 <= minute < 1440:
                valid.append((minute, mode == accepted_mode))
        except (TypeError, ValueError):
            continue
    valid.sort()
    intervals = []
    begin = end = None
    for minute, is_auto in valid:
        if not is_auto:
            if begin is not None:
                intervals.append((begin, end))
            begin = end = None
            continue
        if begin is None:
            begin = end = minute
        elif minute - end <= 3:
            end = minute
        else:
            intervals.append((begin, end))
            begin = end = minute
    if begin is not None:
        intervals.append((begin, end))
    # An isolated sample is a *point*, not evidence of a continuous policy
    # interval. Never draw a fabricated horizontal threshold for it.
    return [(a, b) for a, b in intervals if b > a]


def _night_windows(segment: Mapping[str, Any]) -> list[tuple[int, int]]:
    """Historical local night window. Missing, equal or invalid clocks prove nothing."""
    def minute(key: str) -> int | None:
        raw = segment.get(key)
        if not isinstance(raw, str) or len(raw) != 5 or raw[2] != ":":
            return None
        try:
            hour, minute = int(raw[:2]), int(raw[3:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour * 60 + minute
        except ValueError:
            pass
        return None

    begin, end = minute("night_start"), minute("night_end")
    if begin is None or end is None or begin == end:
        return []
    if begin < end:
        return [(begin, end)]
    return [(0, end), (begin, 1440)]


def care_day_lines(segments: Sequence[Mapping[str, Any]], day: str,
                   points: Sequence[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    target_day = date.fromisoformat(day)
    result = []
    auto_intervals = _confirmed_mode_intervals(points, "AUTO")
    night_intervals = _confirmed_mode_intervals(points, "NIGHT_DISCHARGE")
    for segment in segments:
        # Legacy/config-gap rows must not be reinterpreted as today's settings.
        if segment.get("known") is not True or segment.get("care_enabled") not in (1, True):
            continue
        if not in_care_season(target_day, segment.get("care_start"), segment.get("care_end")):
            continue
        try:
            reserve, regular, emergency = (segment.get(key) for key in ("care_r", "care_n", "care_e"))
            if any(isinstance(v, bool) or v is None or not math.isfinite(float(v)) or
                   float(v) != int(float(v)) for v in (reserve, regular, emergency)):
                continue
            reserve, regular, emergency = (int(v) for v in (reserve, regular, emergency))
            if not (0 <= emergency < regular < reserve <= 100 and
                    regular - emergency >= 2 and reserve - regular >= 2):
                continue
            minimum = segment.get("min_soc")
            if isinstance(minimum, bool) or minimum is None or not math.isfinite(float(minimum)):
                continue  # Effective AUTO floor cannot be stated without baseline.
            floor = max(reserve, float(minimum))
            start = max(0, min(1440, int(segment["start_minute"])))
            end = max(0, min(1440, int(segment["end_minute"])))
            if start >= end or not 0 <= floor <= 100:
                continue
            for evidence_start, evidence_end in auto_intervals:
                left, right = max(start, evidence_start), min(end, evidence_end)
                if right <= left:
                    continue
                result.append({"start_minute": left, "end_minute": right,
                               "auto_floor_soc": floor, "effective_discharge_floor_soc": floor,
                               "reserve_soc": reserve, "grid_trigger_soc": regular,
                               "emergency_soc": emergency,
                               "kind": "configured_seasonal_auto_policy",
                               "mode_source": "historical_observed_AUTO_samples",
                               "physical_effect_confirmed": False})
            # NIGHT is historically credible only with BOTH observed
            # NIGHT_DISCHARGE mode and a matching, recorded local night window.
            # Its higher configured night reserve must never be reduced by R.
            night_stop = segment.get("reserve_soc")
            if night_stop is not None:
                if isinstance(night_stop, bool) or not math.isfinite(float(night_stop)) or not 0 <= float(night_stop) <= 100:
                    continue
                night_floor = max(floor, float(night_stop))
            else:
                night_floor = floor
            for window_start, window_end in _night_windows(segment):
                for evidence_start, evidence_end in night_intervals:
                    left = max(start, window_start, evidence_start)
                    right = min(end, window_end, evidence_end)
                    if right <= left:
                        continue
                    result.append({"start_minute": left, "end_minute": right,
                                   "night_floor_soc": night_floor,
                                   "effective_discharge_floor_soc": night_floor,
                                   "reserve_soc": reserve, "grid_trigger_soc": regular,
                                   "emergency_soc": emergency,
                                   "kind": "configured_seasonal_night_policy",
                                   "mode_source": "historical_observed_NIGHT_DISCHARGE_samples_and_configured_window",
                                   "physical_effect_confirmed": False})
        except (TypeError, ValueError, KeyError, OverflowError):
            continue
    return sorted(result, key=lambda item: (item["start_minute"], item["end_minute"]))


def care_day_incidents(config: Mapping[str, Any], day: str, *, limit: int = 150) -> dict[str, Any]:
    """Bounded, read-only event-history query (not the recent-event UI window).

    Only persisted confirmed emergency failures and persisted resolved times
    qualify. Missing DB/tables are explicit, not invented 'no incidents'.
    """
    target_day = date.fromisoformat(day)
    start = datetime.combine(target_day, datetime.min.time()).timestamp()
    end = datetime.combine(date.fromordinal(target_day.toordinal() + 1), datetime.min.time()).timestamp()
    explicit = str(config.get("OPERATIONAL_EVENTS_DB_PATH") or "").strip()
    db = os.path.abspath(explicit) if explicit else os.path.join(
        os.path.dirname(resolve_measurement_db_path(dict(config))), "zec_operational_events.sqlite3")
    if not os.path.isfile(db):
        return {"status": "not_recorded", "items": []}
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=0.3)
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='operational_events'").fetchone()
        if not exists:
            return {"status": "not_recorded", "items": []}
        rows = conn.execute(
            "SELECT id,started_at,ended_at,status FROM operational_events "
            "WHERE event_type='battery_care_emergency_failure' "
            "AND ((started_at>=? AND started_at<?) OR (ended_at>=? AND ended_at<?)) "
            "ORDER BY started_at,id LIMIT ?",
            (start, end, start, end, max(1, min(300, int(limit)))),
        ).fetchall()
        items = []
        for event_id, started, ended, status in rows:
            for epoch, kind in ((started, "failure_confirmed"),
                                (ended, "reserve_recovered" if status == "resolved" else None)):
                if kind is None or epoch is None or not start <= float(epoch) < end:
                    continue
                local = datetime.fromtimestamp(float(epoch))
                items.append({"event_id": int(event_id), "kind": kind,
                              "minute": (local.hour * 60 + local.minute + local.second / 60),
                              "source": "persistent_operational_event"})
        # A distinct source family: confirmed controller transition intents.
        # Historical incident-only/legacy stores may have no detail_json column;
        # that absence must not erase the confirmed failure history above.
        try:
            transitions = conn.execute(
                "SELECT id,started_at,detail_json FROM operational_events "
                "WHERE event_type='battery_care_stage_transition' "
                "AND started_at>=? AND started_at<? ORDER BY started_at,id LIMIT ?",
                (start, end, max(1, min(300, int(limit)))),
            ).fetchall()
        except sqlite3.OperationalError:
            transitions = []
        for event_id, epoch, encoded in transitions:
            try:
                info = json.loads(encoded or '{}')
                if (not isinstance(info, dict) or info.get('source') != 'distinct_completed_controller_cycles'
                        or info.get('physical_effect_confirmed') is not False
                        or info.get('stage_from') not in STAGES or info.get('stage_to') not in STAGES):
                    continue
                local = datetime.fromtimestamp(float(epoch))
                items.append({"event_id": int(event_id), "kind": "stage_transition",
                              "stage_from": info['stage_from'], "stage_to": info['stage_to'],
                              "floor_from_soc": info.get("floor_from_soc"),
                              "floor_to_soc": info.get("floor_to_soc"),
                              "minute": local.hour * 60 + local.minute + local.second / 60,
                              "source": "persistent_controller_stage_transition",
                              "physical_effect_confirmed": False})
            except (ValueError, TypeError, OverflowError):
                continue
        return {"status": "recorded", "items": sorted(items, key=lambda r: (r["minute"], r["event_id"]))}
    except (OSError, sqlite3.Error, ValueError, TypeError):
        return {"status": "unavailable", "items": []}
    finally:
        if conn is not None:
            conn.close()
