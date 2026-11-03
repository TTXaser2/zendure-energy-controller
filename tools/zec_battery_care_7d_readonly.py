#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""ZEC V18 Battery Care – bounded, read-only field-evidence extractor.

Never imports the product, mutates settings/database, or sends control commands.
Data quality and requested vs proven hardware effect are kept separate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sqlite3
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import re
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
FORMAT = "ZEC_BATCARE_READONLY_7D_V1_1"
MAX_FILES = 900
MAX_SCAN_BYTES = 3 * 1024**3
MAX_V4_ROWS = 360000
MAX_SQLITE_ROWS = 360000
MAX_EVENTS = 30000
MAX_GAP_SECONDS = 15.0

V4_FIELDS = (
    "measurement_epoch_ms", "measurement_time_utc", "config_control_hash",
    "operating_mode", "control_intent", "control_input_valid", "safe_state_active",
    "manual_stop_active", "night_window_active", "control_night_reserve_active",
    "grid_power_w", "grid_power_valid", "grid_power_fresh", "grid_power_age_s",
    "zendure_soc_percent", "zendure_soc_valid", "zendure_soc_fresh", "zendure_soc_age_s",
    "zendure_actual_power_w", "zendure_actual_power_valid", "zendure_actual_power_fresh",
    "zendure_actual_power_age_s", "zendure_battery_signed_power_w",
    "zendure_battery_temp_max_c", "zendure_battery_temp_valid",
    "second_battery_power_w", "second_battery_power_valid", "second_battery_power_fresh",
    "second_battery_soc_percent", "second_battery_soc_valid", "second_battery_soc_fresh",
    "primary_discharge_floor_soc_percent", "primary_discharge_floor_valid",
    "control_cross_charge_detected", "control_cross_charge_limited",
    "target_raw_w", "target_final_w", "target_final_reason", "target_changed_by_soc_limit",
    "target_changed_by_cross_charge", "command_action", "command_requested_w",
    "command_sent_w", "command_sent_flag", "command_lifecycle_state",
    "command_neutralization_active", "command_neutralization_reason",
    "command_effect_category", "command_effect_reason", "command_effect_confirmed",
    "command_readback_matches_desired", "command_not_effective_active",
    "command_not_effective_duration_s", "command_resync_count",
    "command_mismatch_resolution", "command_desired_signed_target_w",
    "command_desired_reason", "command_publish_event_id", "command_publish_fields",
    "physical_power_direction_change_count", "command_ac_mode_change_count",
    "harvest_target_selected_by", "fast_capture_active", "pv_power_w", "pv_power_valid",
)
SQL_FIELDS = (
    "ts_ms", "soc_percent", "zendure_target_power_w", "zendure_actual_power_w",
    "grid_power_w", "soc_valid", "grid_valid", "mode", "control_reason",
    "primary_soc_percent", "primary_power_w", "safe_state_active", "cross_charge_limited",
    "night_window_active", "night_reserve_active", "config_control_hash"
)
TIMELINE_FIELDS = (
    "effective_from_ms", "config_control_hash", "known", "min_soc", "max_soc",
    "reserve_soc", "night_start", "night_end", "care_enabled", "care_start", "care_end",
    "care_r", "care_n", "care_e", "source"
)
EVENT_FIELDS = ("id", "event_type", "severity", "title", "started_at", "ended_at",
                "status", "occurrence_count", "detail_json")


def finite(value):
    try:
        if value is None or value == "":
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def validflag(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def time_text(epoch_ms):
    return datetime.fromtimestamp(int(epoch_ms) / 1000, tz=TZ).isoformat(timespec="seconds")


def safe_config(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            result = json.load(f)
            return result if isinstance(result, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def db_connection(path):
    if not path.is_file():
        return None
    # `mode=ro`: forbid creating/writing data; do not use immutable=1 (would ignore live WAL).
    uri = "file:" + path.resolve().as_posix() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=1.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=1000")
    conn.execute("PRAGMA cache_size=-2048")
    return conn


def exists_table(conn, name):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def actual_columns(conn, table):
    return {r[1] for r in conn.execute("PRAGMA table_info('" + table + "')")}


def read_timeline(conn, out_path, start_ms, end_ms, warnings):
    segments = []
    if conn is None or not exists_table(conn, "graph_config_timeline"):
        with out_path.open("w", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=TIMELINE_FIELDS).writeheader()
        warnings.append("NO_HISTORICAL_CONFIG_TIMELINE")
        return segments
    cols = actual_columns(conn, "graph_config_timeline")
    query_cols = ",".join(c if c in cols else "NULL AS " + c for c in TIMELINE_FIELDS)
    q = ("SELECT " + query_cols + " FROM graph_config_timeline "
         "WHERE effective_from_ms < ? ORDER BY effective_from_ms DESC LIMIT 1")
    prev = conn.execute(q, (start_ms,)).fetchone()
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TIMELINE_FIELDS)
        writer.writeheader()
        if prev is not None:
            row = dict(prev); segments.append(row); writer.writerow(row)
        q = ("SELECT " + query_cols + " FROM graph_config_timeline "
             "WHERE effective_from_ms >= ? AND effective_from_ms < ? ORDER BY effective_from_ms")
        for item in conn.execute(q, (start_ms, end_ms)):
            row = dict(item); segments.append(row); writer.writerow(row)
    return segments


def in_care_season(ms, row):
    start = str(row.get("care_start") or "")
    end = str(row.get("care_end") or "")
    if len(start) != 5 or len(end) != 5 or start[2] != "-" or end[2] != "-":
        return None
    day = datetime.fromtimestamp(ms / 1000, TZ).strftime("%m-%d")
    return start <= day <= end if start <= end else day >= start or day <= end


def config_for_time(ms, segments, index):
    while index + 1 < len(segments) and int(segments[index + 1]["effective_from_ms"]) <= ms:
        index += 1
    if segments and int(segments[index]["effective_from_ms"]) <= ms:
        return segments[index], index
    return None, index


_V4_DATED = re.compile(r"zendure_measurements_v4_(\d{8}T\d{6}Z)\.csv$")


def timestamped_filename(path):
    """Return filename UTC epoch-ms; unknown names explicitly reported, not guessed by mtime."""
    match = _V4_DATED.fullmatch(path.name)
    if match is None:
        return None
    try:
        return int(datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)
    except ValueError:
        return None


def discover_v4(root, config, explicit_dirs, explicit_files, warnings, start_ms=None, end_ms=None):
    dirs = {root / "logs", root / "logs" / "fallback"}
    for d in explicit_dirs:
        dirs.add(Path(d).expanduser())
    storage = str(config.get("MEASUREMENT_LOG_STORAGE_TARGET") or "internal_sd")
    rawdir = str(config.get("MEASUREMENT_LOG_DIR") or "logs")
    if storage == "external_mount":
        mount = str(config.get("MEASUREMENT_LOG_MOUNTPOINT") or "")
        if mount:
            dirs.add(Path(mount) / rawdir.lstrip("/"))
        else:
            warnings.append("V4_EXTERNAL_AUTO_MOUNT_UNKNOWN: use --v4-dir with actual mount/log directory")
    else:
        dirs.add((root / rawdir) if not os.path.isabs(rawdir) else Path(rawdir))
    fallback = str(config.get("MEASUREMENT_LOG_FALLBACK_DIR") or "logs/fallback")
    dirs.add((root / fallback) if not os.path.isabs(fallback) else Path(fallback))
    paths = {Path(f).expanduser() for f in explicit_files}
    for directory in dirs:
        if not directory.is_dir():
            continue
        try:
            for candidate in directory.glob("zendure_measurements_v4*.csv"):
                if candidate.is_file() and not candidate.is_symlink():
                    paths.add(candidate)
        except OSError as exc:
            warnings.append("V4_DIR_READ_FAILED: " + str(exc))
    paths = sorted((p for p in paths if p.is_file() and not p.is_symlink()), key=lambda p: str(p))
    discovered = len(paths)
    explicitly_selected = {str(Path(f).expanduser()) for f in explicit_files}
    dated = sorted((timestamped_filename(p), str(p), p) for p in paths if timestamped_filename(p) is not None)
    candidate = set()
    if start_ms is not None and end_ms is not None:
        # Include last file preceding start, as it may span the window boundary.
        prior = [p for ts, _, p in dated if ts < start_ms]
        if prior:
            candidate.add(prior[-1])
        candidate.update(p for ts, _, p in dated if start_ms <= ts < end_ms)
        # Unknown filename timestamps cannot be excluded on temporal grounds.
        unknown = [p for p in paths if timestamped_filename(p) is None]
        if unknown:
            warnings.append(f"V4_UNDATED_FILE_CANDIDATES: count={len(unknown)}")
        candidate.update(unknown)
        candidate.update(p for p in paths if str(p) in explicitly_selected)
    else:
        candidate.update(paths)
    selected = sorted(candidate, key=lambda p: (timestamped_filename(p) if timestamped_filename(p) is not None else -1, str(p)))
    limit_hit = len(selected) > MAX_FILES
    if limit_hit:
        warnings.append(f"V4_FILE_SELECTION_TRUNCATED: eligible={len(selected)} max={MAX_FILES} discovered={discovered}")
        # Retain newest dated files, not arbitrary filesystem recency.
        selected = selected[-MAX_FILES:]
    return selected, {"files_discovered": discovered, "files_eligible": len(candidate),
                      "files_selected": len(selected), "file_selection_truncated": limit_hit,
                      "selection_strategy": "filename_utc_window_with_predecessor_not_mtime"}


def export_v4(paths, dest, start_ms, end_ms, warnings):
    stats = {"files_scanned": 0, "bytes_examined": 0, "rows_scanned": 0,
             "rows_selected": 0, "files_with_rows": 0, "missing_columns": [],
             "truncated": False, "time_min": None, "time_max": None}
    seen_columns = set()
    with dest.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=("source_name", "local_time") + V4_FIELDS)
        writer.writeheader()
        for path in paths:
            try:
                size = path.stat().st_size
                if stats["bytes_examined"] + size > MAX_SCAN_BYTES:
                    warnings.append("V4_SCAN_LIMIT_REACHED"); stats["truncated"] = True; break
                stats["bytes_examined"] += size
                stats["files_scanned"] += 1
                rows_here = 0
                with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
                    reader = csv.DictReader(source, delimiter=";")
                    cols = set(reader.fieldnames or [])
                    if not {"schema_version", "measurement_epoch_ms", "zendure_soc_percent"}.issubset(cols):
                        warnings.append("SKIPPED_NON_V4_SCHEMA: " + path.name); continue
                    seen_columns.update(cols)
                    for row in reader:
                        stats["rows_scanned"] += 1
                        if stats["rows_scanned"] > MAX_V4_ROWS * 12:
                            warnings.append("V4_SCAN_ROW_BUDGET_REACHED")
                            stats["truncated"] = True
                            break
                        ts = finite(row.get("measurement_epoch_ms"))
                        if ts is None or not (start_ms <= ts < end_ms):
                            continue
                        if len(str(row.get("measurement_epoch_ms") or "")) > 30:
                            continue
                        # Only the fields needed for independent state/effect/recovery review.
                        export = {k: row.get(k, "") for k in V4_FIELDS}
                        export["source_name"] = path.name
                        export["local_time"] = time_text(int(ts))
                        writer.writerow(export)
                        rows_here += 1
                        stats["rows_selected"] += 1
                        stats["time_min"] = int(ts) if stats["time_min"] is None else min(stats["time_min"], int(ts))
                        stats["time_max"] = int(ts) if stats["time_max"] is None else max(stats["time_max"], int(ts))
                        if stats["rows_selected"] >= MAX_V4_ROWS:
                            warnings.append("V4_EXPORT_ROW_LIMIT_REACHED")
                            stats["truncated"] = True
                            break
                if rows_here:
                    stats["files_with_rows"] += 1
                if stats["truncated"]:
                    break
            except (OSError, csv.Error, ValueError) as exc:
                warnings.append("V4_FILE_ERROR: " + path.name + " / " + str(exc)[:160])
    stats["missing_columns"] = sorted(set(V4_FIELDS) - seen_columns)
    if not stats["rows_selected"]:
        warnings.append("V4_NO_ROWS: detailed command/validity evidence not available")
    return stats


def export_events(conn, dest, start_ms, end_ms, warnings):
    counts = Counter()
    stages = Counter()
    if conn is None or not exists_table(conn, "operational_events"):
        with dest.open("w", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=("local_time",) + EVENT_FIELDS).writeheader()
        warnings.append("OPERATIONAL_EVENTS_MISSING")
        return {"count": 0, "types": {}}
    cols = actual_columns(conn, "operational_events")
    selected = ",".join(c if c in cols else "NULL AS " + c for c in EVENT_FIELDS)
    # Care events and context (mode transitions, command-effect + monitoring events).
    query = ("SELECT " + selected + " FROM operational_events WHERE "
             "(started_at >= ? AND started_at < ?) AND "
             "(event_type LIKE 'battery_care%' OR event_type IN "
             "('mode','command_effect','grid_stale','grid_processing_stale','mqtt')) "
             "ORDER BY started_at LIMIT ?")
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("local_time",) + EVENT_FIELDS)
        writer.writeheader()
        for item in conn.execute(query, (start_ms / 1000, end_ms / 1000, MAX_EVENTS + 1)):
            if sum(counts.values()) >= MAX_EVENTS:
                warnings.append("EVENT_EXPORT_LIMIT_REACHED"); break
            row = dict(item)
            counts[str(row.get("event_type") or "UNKNOWN")] += 1
            # Do NOT export full free-form journal 'detail' or dedupe keys.
            # detail_json is limited to selected care keys, never full arbitrary blobs.
            detail = {}
            if str(row.get("event_type") or "").startswith("battery_care"):
                try:
                    original = json.loads(row.get("detail_json") or "{}")
                    if isinstance(original, dict):
                        allow = {"stage_from", "stage_to", "floor_from_soc", "floor_to_soc",
                                 "controller_cycle_id", "observed_mode", "requested_power_w",
                                 "policy_floor_soc", "source", "physical_effect_confirmed",
                                 "reason", "target_w", "actual_w", "soc_percent"}
                        detail = {k: v for k, v in original.items()
                                  if k in allow and isinstance(v, (str, int, float, bool, type(None)))}
                        if row.get("event_type") == "battery_care_stage_transition":
                            stage_to = str(detail.get("stage_to") or "")
                            if stage_to:
                                stages[stage_to] += 1
                except (ValueError, TypeError):
                    pass
            row["detail_json"] = json.dumps(detail, ensure_ascii=False, separators=(",", ":"))
            row["title"] = str(row.get("title") or "")[:120]
            writer.writerow({"local_time": time_text(int(float(row["started_at"]) * 1000)), **row})
    return {"count": sum(counts.values()), "types": dict(counts),
            "care_stages": dict(stages)}


def new_day():
    return {"sqlite_samples": 0, "observed_interval_s": 0., "valid_soc_interval_s": 0.,
            "valid_grid_interval_s": 0., "soc_min": None, "soc_max": None,
            "soc_start": None, "soc_end": None, "soc_below_r_s": 0.,
            "care_eligible_observed_s": 0., "care_unknown_policy_s": 0.,
            "soc_at_or_below_n_s": 0., "soc_at_or_below_e_s": 0.,
            "observed_charge_kwh": 0., "observed_discharge_kwh": 0.,
            "observed_grid_import_kwh": 0., "observed_grid_export_kwh": 0.,
            "normalization_gaps": 0, "modes_s": Counter(), "care_limit_samples": 0}


def export_sqlite(conn, dest, daily_path, reserve_path, segments, start_ms, end_ms, warnings):
    daily = defaultdict(new_day)
    stats = {"rows": 0, "truncated": False, "sqlite_backend": None,
             "core_data_usable": False, "required_columns_present": False, "useful_rows": 0,
             "coverage_start": None, "coverage_end": None}
    if conn is None or not exists_table(conn, "measurement_raw"):
        with dest.open("w", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=("local_time", "care_enabled_hist",
                "care_r_hist", "care_n_hist", "care_e_hist", "care_season_hist") + SQL_FIELDS).writeheader()
        with daily_path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(["date", "sqlite_samples", "observed_interval_s", "soc_min", "soc_max"])
        with reserve_path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(["request_ts_ms", "request_local", "outcome"])
        warnings.append("MEASUREMENT_RAW_DB_MISSING")
        return stats, daily
    cols = actual_columns(conn, "measurement_raw")
    core = {"ts_ms", "soc_percent", "zendure_actual_power_w", "grid_power_w", "soc_valid", "grid_valid"}
    stats["required_columns_present"] = core.issubset(cols)
    if not stats["required_columns_present"]:
        warnings.append("SQLITE_CORE_COLUMNS_MISSING: daily graph-derived statistics NOT_EVALUABLE")
    sql_cols = ",".join(c if c in cols else "NULL AS " + c for c in SQL_FIELDS)
    query = "SELECT " + sql_cols + " FROM measurement_raw WHERE ts_ms >= ? AND ts_ms < ? ORDER BY ts_ms LIMIT ?"
    stats["sqlite_backend"] = "measurement_raw_v3_or_v2_graph"
    prev = None
    config_index = 0
    pending_reserve = None
    reserve_candidates = []
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("local_time", "care_enabled_hist",
                 "care_r_hist", "care_n_hist", "care_e_hist", "care_season_hist") + SQL_FIELDS)
        writer.writeheader()
        for item in conn.execute(query, (start_ms, end_ms, MAX_SQLITE_ROWS + 1)):
            if stats["rows"] >= MAX_SQLITE_ROWS:
                stats["truncated"] = True; warnings.append("SQLITE_ROW_LIMIT_REACHED"); break
            row = dict(item)
            if (finite(row.get("soc_percent")) is not None and validflag(row.get("soc_valid"))
                    and finite(row.get("zendure_actual_power_w")) is not None):
                stats["useful_rows"] += 1
            ts = int(row["ts_ms"])
            policy, config_index = config_for_time(ts, segments, config_index)
            season = in_care_season(ts, policy) if policy and validflag(policy.get("known")) else None
            enabled = validflag(policy.get("care_enabled")) if policy and policy.get("care_enabled") is not None else None
            extra = {"local_time": time_text(ts),
                     "care_enabled_hist": enabled if enabled is not None else "",
                     "care_r_hist": policy.get("care_r") if policy else "",
                     "care_n_hist": policy.get("care_n") if policy else "",
                     "care_e_hist": policy.get("care_e") if policy else "",
                     "care_season_hist": season if season is not None else ""}
            writer.writerow({**extra, **row})
            stats["rows"] += 1
            stats["coverage_start"] = ts if stats["coverage_start"] is None else stats["coverage_start"]
            stats["coverage_end"] = ts
            day_key = datetime.fromtimestamp(ts / 1000, TZ).date().isoformat()
            d = daily[day_key]; d["sqlite_samples"] += 1
            soc = finite(row.get("soc_percent")) if validflag(row.get("soc_valid")) else None
            if soc is not None:
                d["soc_start"] = soc if d["soc_start"] is None else d["soc_start"]
                d["soc_end"] = soc
                d["soc_min"] = soc if d["soc_min"] is None else min(d["soc_min"], soc)
                d["soc_max"] = soc if d["soc_max"] is None else max(d["soc_max"], soc)
            reason = str(row.get("control_reason") or "").upper()
            if "BATTERY_CARE_RESERVE" in reason or "BATTERY CARE" in reason:
                d["care_limit_samples"] += 1
            if prev is not None:
                last, last_ts, last_policy, last_enabled, last_season = prev
                delta = (ts - last_ts) / 1000
                if 0 < delta <= MAX_GAP_SECONDS:
                    prior_day = datetime.fromtimestamp(last_ts / 1000, TZ).date().isoformat()
                    x = daily[prior_day]
                    x["observed_interval_s"] += delta
                    x["modes_s"][str(last.get("mode") or "UNKNOWN")] += delta
                    psoc = finite(last.get("soc_percent")) if validflag(last.get("soc_valid")) else None
                    if psoc is not None:
                        x["valid_soc_interval_s"] += delta
                        if last_enabled is True and last_season is True and last_policy is not None:
                            floor = finite(last_policy.get("care_r"))
                            n = finite(last_policy.get("care_n"))
                            e = finite(last_policy.get("care_e"))
                            x["care_eligible_observed_s"] += delta
                            if floor is not None and psoc < floor:
                                x["soc_below_r_s"] += delta
                            if n is not None and psoc <= n:
                                x["soc_at_or_below_n_s"] += delta
                            if e is not None and psoc <= e:
                                x["soc_at_or_below_e_s"] += delta
                        elif last_enabled is None or last_season is None:
                            x["care_unknown_policy_s"] += delta
                    g = finite(last.get("grid_power_w")) if validflag(last.get("grid_valid")) else None
                    if g is not None:
                        x["valid_grid_interval_s"] += delta
                        if g >= 0:
                            x["observed_grid_import_kwh"] += g * delta / 3600000
                        else:
                            x["observed_grid_export_kwh"] += -g * delta / 3600000
                    # Graph SQLite does not retain the V4 power-valid/fresh contract.
                    p = finite(last.get("zendure_actual_power_w"))
                    if p is not None:
                        if p >= 0:
                            x["observed_charge_kwh"] += p * delta / 3600000
                        else:
                            x["observed_discharge_kwh"] += -p * delta / 3600000
                else:
                    daily[datetime.fromtimestamp(last_ts / 1000, TZ).date().isoformat()]["normalization_gaps"] += 1
            # Read-only provisional transition detection: graph values lack V4 power-validity.
            tgt = finite(row.get("zendure_target_power_w"))
            actual = finite(row.get("zendure_actual_power_w"))
            is_reserve = ("BATTERY_CARE_RESERVE" in reason or
                          ("BATTERY CARE" in reason and "RESERVE" in reason))
            if pending_reserve is not None:
                elapsed = (ts - pending_reserve["request_ts_ms"]) / 1000
                if elapsed > 30:
                    pending_reserve["outcome"] = "NO_GRAPH_NEUTRALITY_WITHIN_30S"
                    pending_reserve["observed_ts_ms"] = ""
                    reserve_candidates.append(pending_reserve)
                    pending_reserve = None
                elif actual is not None and abs(actual) <= 50:
                    pending_reserve["outcome"] = "GRAPH_NEUTRALITY_CANDIDATE"
                    pending_reserve["observed_ts_ms"] = ts
                    pending_reserve["elapsed_s"] = round(elapsed, 3)
                    pending_reserve["observed_actual_w"] = actual
                    reserve_candidates.append(pending_reserve)
                    pending_reserve = None
            if (pending_reserve is None and is_reserve and tgt is not None
                    and abs(tgt) <= 25 and actual is not None and actual < -50):
                pending_reserve = {"request_ts_ms": ts, "request_local": time_text(ts),
                                   "request_soc": soc, "request_target_w": tgt,
                                   "request_actual_w": actual, "observed_ts_ms": "",
                                   "elapsed_s": "", "observed_actual_w": "",
                                   "outcome": "PENDING"}
            prev = (row, ts, policy, enabled, season)
    stats["core_data_usable"] = bool(stats["required_columns_present"] and stats["useful_rows"] > 0)
    if stats["rows"] and not stats["core_data_usable"]:
        warnings.append("SQLITE_CORE_DATA_EMPTY: graph daily statistics NOT_EVALUABLE; V4 fallback required")
    if pending_reserve is not None:
        pending_reserve["outcome"] = "WINDOW_ENDED_BEFORE_CONCLUSION"
        reserve_candidates.append(pending_reserve)
    with reserve_path.open("w", newline="", encoding="utf-8") as handle:
        cols = ("request_ts_ms", "request_local", "request_soc", "request_target_w",
                "request_actual_w", "observed_ts_ms", "elapsed_s", "observed_actual_w", "outcome")
        writer = csv.DictWriter(handle, fieldnames=cols)
        writer.writeheader()
        writer.writerows(reserve_candidates)
    stats["reserve_graph_candidates"] = dict(Counter(x["outcome"] for x in reserve_candidates))
    keys = ["date", "sqlite_samples", "observed_interval_s", "valid_soc_interval_s",
            "valid_grid_interval_s", "valid_power_interval_s", "soc_start", "soc_end", "soc_min", "soc_max",
            "care_eligible_observed_s", "care_unknown_policy_s", "soc_below_r_s",
            "soc_at_or_below_n_s", "soc_at_or_below_e_s", "care_limit_samples",
            "observed_charge_kwh", "observed_discharge_kwh", "observed_grid_import_kwh",
            "observed_grid_export_kwh", "normalization_gaps", "modes_seconds_json"]
    with daily_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for day in sorted(daily):
            d = daily[day]
            row = {"date": day, **{k: round(v, 4) if isinstance(v, float) else v
                                    for k, v in d.items() if k != "modes_s"}}
            row["modes_seconds_json"] = json.dumps(d["modes_s"], sort_keys=True)
            writer.writerow({k: row.get(k, "") for k in keys})
    return stats, daily


def export_v4_daily(v4_path, daily_path, segments, warnings):
    """Recalculate only from valid and fresh V4 observations; stream, never load history."""
    daily = defaultdict(new_day)
    prev = None
    last_ts = -1
    index = 0
    duplicate = 0
    with v4_path.open("r", newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            ts = finite(row.get("measurement_epoch_ms"))
            if ts is None:
                continue
            ts = int(ts)
            if ts <= last_ts:
                duplicate += 1
                continue
            last_ts = ts
            day = datetime.fromtimestamp(ts / 1000, TZ).date().isoformat()
            d = daily[day]
            d["sqlite_samples"] = 0
            d["v4_samples"] = d.get("v4_samples", 0) + 1
            soc = (finite(row.get("zendure_soc_percent"))
                   if validflag(row.get("zendure_soc_valid")) and validflag(row.get("zendure_soc_fresh")) else None)
            if soc is not None:
                d["soc_start"] = soc if d["soc_start"] is None else d["soc_start"]
                d["soc_end"] = soc
                d["soc_min"] = soc if d["soc_min"] is None else min(soc, d["soc_min"])
                d["soc_max"] = soc if d["soc_max"] is None else max(soc, d["soc_max"])
            policy, index = config_for_time(ts, segments, index)
            in_season = in_care_season(ts, policy) if policy and validflag(policy.get("known")) else None
            enabled = validflag(policy.get("care_enabled")) if policy and policy.get("care_enabled") is not None else None
            if prev is not None:
                last, last_ts, last_policy, last_season, last_enabled = prev
                dt = (ts - last_ts)/1000.0
                if 0 < dt <= MAX_GAP_SECONDS:
                    old_day = datetime.fromtimestamp(last_ts/1000, TZ).date().isoformat()
                    x = daily[old_day]
                    x["observed_interval_s"] += dt
                    x["modes_s"][str(last.get("operating_mode") or "UNKNOWN")] += dt
                    old_soc = (finite(last.get("zendure_soc_percent")) if
                               validflag(last.get("zendure_soc_valid")) and validflag(last.get("zendure_soc_fresh")) else None)
                    if old_soc is not None:
                        x["valid_soc_interval_s"] += dt
                        if last_enabled is True and last_season is True and last_policy is not None:
                            x["care_eligible_observed_s"] += dt
                            for field, key, comparator in (("care_r", "soc_below_r_s", lambda a,b:a<b),
                                                           ("care_n", "soc_at_or_below_n_s", lambda a,b:a<=b),
                                                           ("care_e", "soc_at_or_below_e_s", lambda a,b:a<=b)):
                                bound = finite(last_policy.get(field))
                                if bound is not None and comparator(old_soc, bound):
                                    x[key] += dt
                        elif last_enabled is None or last_season is None:
                            x["care_unknown_policy_s"] += dt
                    g = (finite(last.get("grid_power_w")) if
                         validflag(last.get("grid_power_valid")) and validflag(last.get("grid_power_fresh")) else None)
                    if g is not None:
                        x["valid_grid_interval_s"] += dt
                        x["observed_grid_import_kwh" if g>=0 else "observed_grid_export_kwh"] += abs(g)*dt/3600000
                    power = (finite(last.get("zendure_actual_power_w")) if
                             validflag(last.get("zendure_actual_power_valid")) and validflag(last.get("zendure_actual_power_fresh")) else None)
                    if power is not None:
                        x["valid_power_interval_s"] = x.get("valid_power_interval_s", 0.) + dt
                        x["observed_charge_kwh" if power>=0 else "observed_discharge_kwh"] += abs(power)*dt/3600000
                else:
                    daily[datetime.fromtimestamp(last_ts/1000, TZ).date().isoformat()]["normalization_gaps"] += 1
            prev = (row, ts, policy, in_season, enabled)
    keys = ["date", "source", "v4_samples", "sqlite_samples", "observed_interval_s", "valid_soc_interval_s",
            "valid_grid_interval_s", "valid_power_interval_s", "soc_start", "soc_end", "soc_min", "soc_max",
            "care_eligible_observed_s", "care_unknown_policy_s", "soc_below_r_s",
            "soc_at_or_below_n_s", "soc_at_or_below_e_s", "care_limit_samples",
            "observed_charge_kwh", "observed_discharge_kwh", "observed_grid_import_kwh",
            "observed_grid_export_kwh", "normalization_gaps", "modes_seconds_json"]
    with daily_path.open("w", newline="", encoding="utf-8") as out:
        w = csv.DictWriter(out, fieldnames=keys); w.writeheader()
        for day in sorted(daily):
            d = daily[day]
            result = {k: (round(v, 5) if isinstance(v, float) else v) for k,v in d.items() if k!='modes_s'}
            # Lack of valid data is UNKNOWN, never zero energy inferred from absent readings.
            if not d["valid_grid_interval_s"]:
                result["observed_grid_import_kwh"] = result["observed_grid_export_kwh"] = ""
            if not d.get("valid_power_interval_s"):
                result["observed_charge_kwh"] = result["observed_discharge_kwh"] = ""
            if not d["valid_soc_interval_s"]:
                result["soc_below_r_s"] = result["soc_at_or_below_n_s"] = result["soc_at_or_below_e_s"] = ""
            result["modes_seconds_json"] = json.dumps(d["modes_s"], sort_keys=True)
            result["source"] = "V4_VALID_FRESH"
            result["v4_samples"] = d.get("v4_samples",0)
            w.writerow({k:result.get(k,"") for k in keys})
    if duplicate:
        warnings.append(f"V4_DUPLICATE_OR_OUT_OF_ORDER_ROWS_SKIPPED: {duplicate}")
    return {"daily_source":"V4_VALID_FRESH", "days":len(daily), "duplicate_or_nonmonotonic_skipped":duplicate}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser(description="ZEC V18 Battery Care, last 7 days: read-only bounded forensic export")
    p.add_argument("--root", type=Path, default=Path("/opt/zendure-controller"))
    p.add_argument("--config", type=Path, help="Read config ONLY for paths; never exported")
    p.add_argument("--db", type=Path, help="Measurement SQLite (read-only)")
    p.add_argument("--events-db", type=Path, help="Operational events SQLite (read-only)")
    p.add_argument("--v4-dir", type=str, action="append", default=[], help="Additional V4 measurement directory")
    p.add_argument("--v4-file", type=str, action="append", default=[], help="Explicit V4 CSV path")
    p.add_argument("--days", type=float, default=7.0)
    p.add_argument("--from", dest="from_date", help="Override: ISO local datetime, e.g. 2026-10-28T00:00")
    p.add_argument("--until", help="Override: ISO local datetime; exclusive")
    p.add_argument("--output-dir", type=Path, default=Path.home() / "Downloads")
    args = p.parse_args(argv)
    if not (0 < args.days <= 31):
        p.error("--days must be in (0,31]")
    now = datetime.now(TZ)
    def local_iso(value):
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ)
    end = local_iso(args.until) if args.until else now
    start = local_iso(args.from_date) if args.from_date else end - timedelta(days=args.days)
    if start >= end or end - start > timedelta(days=31):
        p.error("invalid window: 0 < interval <= 31 days")
    start_ms = int(start.timestamp() * 1000); end_ms = int(end.timestamp() * 1000)
    root = args.root.resolve()
    config = safe_config(args.config or root / "config.json")
    def resolved_user_path(value, fallback):
        if value:
            path = Path(str(value)).expanduser()
            return path if path.is_absolute() else root / path
        return fallback
    if args.db:
        db_path = args.db
    else:
        db_path = resolved_user_path(config.get("MEASUREMENT_DB_PATH"),
               resolved_user_path(config.get("MEASUREMENT_DB_FILE") or "zec_measurements.sqlite3",
                                  root / "logs" / "zec_measurements.sqlite3"))
        if not config.get("MEASUREMENT_DB_PATH") and not Path(str(config.get("MEASUREMENT_DB_FILE") or "")).is_absolute():
            # Usually co-located with measurement logs, not necessarily root/logs.
            base_dir = str(config.get("MEASUREMENT_LOG_DIR") or "logs")
            storage = str(config.get("MEASUREMENT_LOG_STORAGE_TARGET") or "internal_sd")
            if storage == "external_mount" and config.get("MEASUREMENT_LOG_MOUNTPOINT"):
                base = Path(config["MEASUREMENT_LOG_MOUNTPOINT"]) / base_dir.lstrip("/")
            else:
                base = Path(base_dir) if os.path.isabs(base_dir) else root / base_dir
            db_path = base / str(config.get("MEASUREMENT_DB_FILE") or "zec_measurements.sqlite3")
    events_path = args.events_db or resolved_user_path(config.get("OPERATIONAL_EVENTS_DB_PATH"),
                                         db_path.parent / "zec_operational_events.sqlite3")
    warnings = []
    outdir = args.output_dir.expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    name = "ZEC_BATCARE_7D_EVIDENCE_" + stamp
    folder = outdir / name
    folder.mkdir(mode=0o700)
    conn = events_conn = None
    try:
        try:
            conn = db_connection(db_path)
        except sqlite3.Error as exc:
            warnings.append("SQLITE_READ_ERROR: " + str(exc))
        try:
            events_conn = db_connection(events_path)
        except sqlite3.Error as exc:
            warnings.append("EVENT_DB_READ_ERROR: " + str(exc))
        segments = read_timeline(conn, folder / "historical_care_config.csv", start_ms, end_ms, warnings)
        sql_stats, daily = export_sqlite(conn, folder / "sqlite_graph_points.csv",
                                         folder / "daily_summary.csv", folder / "reserve_graph_candidates.csv", segments, start_ms, end_ms, warnings)
        paths, selection_stats = discover_v4(root, config, args.v4_dir, args.v4_file,
                                              warnings, start_ms, end_ms)
        v4_stats = export_v4(paths, folder / "v4_command_and_effect_points.csv", start_ms, end_ms, warnings)
        v4_stats.update(selection_stats)
        v4_stats["truncated"] = bool(v4_stats["truncated"] or selection_stats["file_selection_truncated"])
        if not sql_stats["core_data_usable"]:
            if v4_stats["rows_selected"]:
                v4_daily_stats = export_v4_daily(folder / "v4_command_and_effect_points.csv",
                                                 folder / "daily_summary.csv", segments, warnings)
            else:
                # The legacy SQLite rollup cannot be trusted. Preserve only the header,
                # not misleading 0 kWh or 0 s measurements.
                with (folder / "daily_summary.csv").open("w", newline="", encoding="utf-8") as empty_daily:
                    csv.writer(empty_daily).writerow(["date", "source", "status"])
                warnings.append("NO_VALID_DAILY_SOURCE: daily summary NOT_EVALUABLE")
                v4_daily_stats = {"daily_source":"NOT_EVALUABLE", "days":0}
        else:
            v4_daily_stats = {"daily_source":"SQLITE_GRAPH", "days":len(daily)}
        event_stats = export_events(events_conn, folder / "care_and_context_events.csv", start_ms, end_ms, warnings)
    finally:
        if conn: conn.close()
        if events_conn: events_conn.close()
    if not sql_stats["rows"]:
        warnings.append("NO_SQLITE_GRAPH_DATA: coverage/energy/SOC aggregate NOT_EVALUABLE")
    if not segments:
        warnings.append("CARE_POLICY_HISTORY_UNKNOWN: do not extrapolate current R/N/E backwards")
    stage_counts = event_stats.get("care_stages", {})
    care_evidence = {
        "reserve_neutralization": (
            "GRAPH_CANDIDATE_REQUIRES_V4_INDEPENDENT_VALIDATION"
            if sql_stats.get("reserve_graph_candidates", {}).get("GRAPH_NEUTRALITY_CANDIDATE", 0) else
            "NOT_EVALUABLE_FROM_GRAPH_CANDIDATES"),
        "pv_priority": ("REQUEST_OBSERVED_PHYSICAL_EFFECT_REVIEW_REQUIRED"
                        if stage_counts.get("PV_PRIORITY_REQUESTED", 0) else "NOT_EVALUABLE_NO_STAGE_EVENT"),
        "grid_maintenance": ("REQUEST_OBSERVED_PHYSICAL_EFFECT_REVIEW_REQUIRED"
                             if stage_counts.get("GRID_REQUESTED", 0) else "NOT_EVALUABLE_NO_STAGE_EVENT"),
        "emergency_charging": ("REQUEST_OBSERVED_PHYSICAL_EFFECT_REVIEW_REQUIRED"
                               if stage_counts.get("EMERGENCY_REQUESTED", 0) else "NOT_EVALUABLE_NO_STAGE_EVENT"),
    }
    report = {
        "format": FORMAT, "controller_expected": "V18.0.0 / v18.0.0-20261027",
        "created_local": now.isoformat(), "window_start_local": start.isoformat(),
        "window_end_exclusive_local": end.isoformat(), "window_hours": round((end_ms-start_ms)/3600000, 4),
        "read_only": True, "network_calls": 0, "mqtt_publishes": 0,
        "controller_modifications": 0, "device_commands": 0,
        "measurement_db_available": bool(sql_stats["rows"]),
        "sqlite_core_usable": bool(sql_stats["core_data_usable"]),
        "daily_recalculation": v4_daily_stats,
        "historical_care_config_segments": len(segments),
        "sqlite_graph": sql_stats, "v4": v4_stats, "events": event_stats,
        "care_evidence_levels": care_evidence,
        "analysis_status": "EVIDENCE_EXTRACTED_NOT_PRODUCTIVE_PASS" if sql_stats["core_data_usable"] or v4_stats["rows_selected"] else "NOT_EVALUABLE",
        "warnings": sorted(set(warnings)),
        "limits": {"max_v4_rows_exported": MAX_V4_ROWS, "max_sqlite_rows_exported": MAX_SQLITE_ROWS,
                   "max_v4_files": MAX_FILES, "max_v4_scanned_bytes": MAX_SCAN_BYTES,
                   "max_integrated_gap_s": MAX_GAP_SECONDS},
        "interpretation": [
            "SQLite graph AC power lacks independent V4 valid/fresh flag: kWh are estimates, not validated physics.",
            "Daily observed durations exclude >15s gaps, are not whole-day uptime.",
            "Historical care policy UNKNOWN unless backed by known graph_config_timeline segments.",
            "Care stage events and sent commands prove requests, never independently prove physical effect.",
            "Physical effect requires V4 valid/fresh readings, signed direction, SOC trend, readback and recovery checks.",
            "No causal counterfactual efficiency gain or SOH inference is calculated.",
            "Care PV, grid maintenance and emergency require separate natural episodes; missing episodes = NOT_EVALUABLE.",
            "Event table excludes full details/dedupe keys; current config file and secrets are never exported.",
            "V4 rows are ordered by source-file UTC timestamps, and repeated/nonmonotonic rows are skipped in daily fallback. Offline causal reconstruction still requires a global sort/dedup.",
            "Truncation includes window-eligible file selection; non-window archival files are not counted as truncated.",
        ],
    }
    (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = []
    for path in sorted(folder.iterdir()):
        if path.is_file():
            manifest.append(f"{digest(path)}  {path.name}")
    (folder / "SHA256SUMS.txt").write_text("\n".join(manifest) + "\n", encoding="ascii")
    archive = outdir / (name + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for path in sorted(folder.iterdir()):
            z.write(path, arcname=name + "/" + path.name)
    with zipfile.ZipFile(archive) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError("ZIP_CRC_FAIL: " + bad)
    print("EVIDENCE_ZIP=" + str(archive))
    print("SHA256=" + digest(archive))
    print("ZIP_BYTES=" + str(archive.stat().st_size))
    print("WINDOW_LOCAL=" + start.isoformat() + " -> " + end.isoformat() + " (exclusive)")
    print("SQLITE_POINTS=" + str(sql_stats["rows"]))
    print("V4_SELECTED_ROWS=" + str(v4_stats["rows_selected"]))
    print("EVENTS=" + str(event_stats["count"]))
    print("WARNINGS=" + json.dumps(sorted(set(warnings)), ensure_ascii=False))
    print("NO_CONFIG_OR_CONTROL_MUTATION=TRUE")
    return 0 if sql_stats["rows"] or v4_stats["rows_selected"] else 2


if __name__ == "__main__":
    sys.exit(main())
