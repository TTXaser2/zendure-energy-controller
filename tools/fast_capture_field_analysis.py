#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only closed-loop field analysis for ZEC V17 Fast Capture A400/R100.

The analyzer deliberately separates state, calculation, physical effect and
recovery evidence. Missing natural episodes are NOT_EVALUABLE, never an
invented PASS. It does not write configuration and does not publish commands.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

FORMAT = "ZEC_FAST_CAPTURE_FIELD_ANALYSIS_V1"
EXPECTED_SCHEMA_VERSION = "4"
EXPECTED_CONTROLLER_VERSION = "17.0.1"
ATTACK_W_PER_S = 400.0
RELEASE_W_PER_S = 100.0
FULL_IDLE_CONFIRM_S = 15.0
CONTINUITY_GAP_S = 10.0
TOLERANCE_W = 2.0

FAST_FIELDS = (
    "fast_capture_mode", "fast_capture_active", "fast_capture_primary_state",
    "fast_capture_block_reason", "fast_capture_baseline_target_w",
    "fast_capture_desired_overlay_w", "fast_capture_overlay_w",
    "fast_capture_combined_target_w", "fast_capture_primary_reserve_w",
    "fast_capture_full_idle_progress_s", "fast_capture_observation_dt_s",
    "fast_capture_observation_distinct", "fast_capture_attack_limited",
    "fast_capture_release_limited", "fast_capture_forced_zero_reason",
    "fast_capture_activation_count", "fast_capture_forced_zero_count",
    "fast_capture_effective_zendure_limit_w", "fast_capture_primary_max_charge_w",
)
REQUIRED_CONTEXT_FIELDS = (
    "schema_version", "measurement_epoch_ms", "config_control_hash",
    "grid_power_w", "zendure_actual_power_w", "zendure_actual_power_valid",
    "zendure_actual_power_fresh", "second_battery_power_w",
    "second_battery_power_valid", "second_battery_power_fresh",
    "target_final_w", "target_changed_by_power_limit",
    "target_changed_by_cross_charge", "target_changed_by_soc_limit",
    "target_changed_by_mode", "target_changed_by_safe_state",
    "control_cross_charge_detected", "command_effect_category",
    "command_readback_matches_desired",
)


def describe_contract() -> Dict[str, Any]:
    return {
        "format": FORMAT,
        "read_only": True,
        "commands_published": 0,
        "configuration_mutations": 0,
        "expected_schema_version": EXPECTED_SCHEMA_VERSION,
        "expected_controller_version": EXPECTED_CONTROLLER_VERSION,
        "strategy": "A400_R100",
        "attack_w_per_s": ATTACK_W_PER_S,
        "release_w_per_s": RELEASE_W_PER_S,
        "required_fast_fields": list(FAST_FIELDS),
        "required_context_fields": list(REQUIRED_CONTEXT_FIELDS),
        "result_states": ["PASS", "FAIL", "WARN", "NOT_EVALUABLE"],
        "evidence_dimensions": ["state", "calculation", "physical_effect", "recovery"],
    }


def _float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def _int(value: Any) -> Optional[int]:
    number = _float(value)
    return None if number is None else int(round(number))


def _bool(value: Any) -> Optional[bool]:
    if value in (None, ""):
        return None
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _median(values: Iterable[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return None if not nums else float(statistics.median(nums))


def _status_from_counts(fails: int, evaluable: int, warnings: int = 0) -> str:
    if fails:
        return "FAIL"
    if evaluable == 0:
        return "NOT_EVALUABLE"
    return "WARN" if warnings else "PASS"


def _issue(items: List[Dict[str, Any]], dimension: str, status: str, code: str, detail: str, row: Optional[Dict[str, str]] = None) -> None:
    item: Dict[str, Any] = {"dimension": dimension, "status": status, "code": code, "detail": detail}
    if row is not None:
        item["measurement_epoch_ms"] = _int(row.get("measurement_epoch_ms"))
    items.append(item)


def _load_json(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _expand_csv_args(values: Sequence[str]) -> List[Path]:
    found: List[Path] = []
    seen = set()
    for value in values:
        matches = [Path(x) for x in glob.glob(value)] or [Path(value)]
        for path in matches:
            if path.is_file() and path.resolve() not in seen:
                seen.add(path.resolve()); found.append(path.resolve())
    return sorted(found)


def _read_rows(paths: Sequence[Path]) -> Tuple[List[Dict[str, str]], List[str]]:
    rows: List[Dict[str, str]] = []
    headers: List[str] = []
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            header = list(reader.fieldnames or [])
            if not headers:
                headers = header
            missing = [field for field in FAST_FIELDS + REQUIRED_CONTEXT_FIELDS if field not in header]
            if missing:
                raise ValueError(f"{path}: missing required V17 Fast Capture fields: {', '.join(missing)}")
            for row in reader:
                if row:
                    row["__source_file"] = str(path)
                    rows.append(row)
    rows.sort(key=lambda r: (_int(r.get("measurement_epoch_ms")) or 0, r.get("__source_file", "")))
    return rows, headers


def _config_version_evidence(snapshots: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if snapshots is None:
        return {"status": "WARN", "detail": "CONFIG_SNAPSHOTS_NOT_PROVIDED", "versions": []}
    versions = sorted({str(x.get("controller_version") or "") for x in snapshots.get("snapshots", []) if isinstance(x, dict) and x.get("controller_version")})
    ok = bool(versions) and all(v == EXPECTED_CONTROLLER_VERSION for v in versions)
    return {"status": "PASS" if ok else "FAIL", "detail": "CONTROLLER_VERSION_MATCH" if ok else "CONTROLLER_VERSION_MISMATCH", "versions": versions}


def _manifest_evidence(manifest: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if manifest is None:
        return {"status": "WARN", "detail": "MEASUREMENT_MANIFEST_NOT_PROVIDED"}
    schema = str(manifest.get("schema_version") or "")
    files = [x for x in manifest.get("files", []) if isinstance(x, dict)]
    ok = schema == EXPECTED_SCHEMA_VERSION and bool(files) and all(str(x.get("schema_version") or "") == EXPECTED_SCHEMA_VERSION for x in files)
    return {"status": "PASS" if ok else "FAIL", "detail": "SCHEMA_V4" if ok else "MANIFEST_SCHEMA_MISMATCH", "file_count": len(files), "schema_version": schema}


def _downstream_clear(row: Dict[str, str]) -> bool:
    flags = (
        "target_changed_by_power_limit", "target_changed_by_cross_charge", "target_changed_by_soc_limit",
        "target_changed_by_mode", "target_changed_by_safe_state",
    )
    return not any(_bool(row.get(key)) is True for key in flags)


def _split_episodes(rows: Sequence[Dict[str, str]]) -> List[List[Dict[str, str]]]:
    episodes: List[List[Dict[str, str]]] = []
    current: List[Dict[str, str]] = []
    last_ms: Optional[int] = None
    for row in rows:
        mode = str(row.get("fast_capture_mode") or "off").lower()
        state = str(row.get("fast_capture_primary_state") or "RESERVE_UNKNOWN")
        overlay = _float(row.get("fast_capture_overlay_w")) or 0.0
        desired = _float(row.get("fast_capture_desired_overlay_w")) or 0.0
        relevant = mode in {"shadow", "active"} and (state in {"FULL_IDLE", "NEAR_LIMIT"} or overlay > 0 or desired > 0)
        now = _int(row.get("measurement_epoch_ms"))
        if not relevant:
            if current:
                episodes.append(current); current=[]
            last_ms = now
            continue
        gap = None if now is None or last_ms is None else (now-last_ms)/1000.0
        if current and gap is not None and gap > CONTINUITY_GAP_S:
            episodes.append(current); current=[]
        current.append(row); last_ms=now
    if current:
        episodes.append(current)
    return episodes


def analyze_rows(rows: Sequence[Dict[str, str]], *, manifest: Optional[Dict[str, Any]] = None, snapshots: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    state_eval = state_fail = calc_eval = calc_fail = recovery_eval = recovery_fail = 0
    shadow_eval = shadow_fail = 0
    previous: Optional[Dict[str, str]] = None

    for row in rows:
        mode = str(row.get("fast_capture_mode") or "off").lower()
        primary_state = str(row.get("fast_capture_primary_state") or "RESERVE_UNKNOWN")
        baseline = _float(row.get("fast_capture_baseline_target_w"))
        desired = _float(row.get("fast_capture_desired_overlay_w"))
        overlay = _float(row.get("fast_capture_overlay_w"))
        combined = _float(row.get("fast_capture_combined_target_w"))
        limit = _float(row.get("fast_capture_effective_zendure_limit_w"))
        active = _bool(row.get("fast_capture_active"))
        dt = _float(row.get("fast_capture_observation_dt_s"))
        distinct = _bool(row.get("fast_capture_observation_distinct"))
        forced = str(row.get("fast_capture_forced_zero_reason") or "")

        state_eval += 1
        if mode not in {"off", "shadow", "active"}:
            state_fail += 1; _issue(issues,"state","FAIL","MODE_INVALID",f"invalid mode {mode!r}",row)
        if primary_state not in {"FULL_IDLE", "NEAR_LIMIT", "RESERVE_UNKNOWN"}:
            state_fail += 1; _issue(issues,"state","FAIL","PRIMARY_STATE_INVALID",f"invalid primary state {primary_state!r}",row)
        if primary_state == "RESERVE_UNKNOWN" and (abs(overlay or 0.0) > TOLERANCE_W or abs(desired or 0.0) > TOLERANCE_W):
            state_fail += 1; _issue(issues,"state","FAIL","RESERVE_UNKNOWN_NONZERO_OVERLAY","RESERVE_UNKNOWN must have zero desired/effective overlay",row)
        if primary_state == "FULL_IDLE" and (_float(row.get("fast_capture_full_idle_progress_s")) or 0.0) + 0.05 < FULL_IDLE_CONFIRM_S:
            state_fail += 1; _issue(issues,"state","FAIL","FULL_IDLE_CONFIRM_TOO_SHORT","FULL_IDLE reported before 15 s evidence",row)
        if active is True and not (mode == "active" and (overlay or 0.0) > 0):
            state_fail += 1; _issue(issues,"state","FAIL","ACTIVE_FLAG_INCONSISTENT","fast_capture_active requires active mode and positive overlay",row)

        if None not in (baseline, overlay, combined, limit):
            calc_eval += 1
            expected_combined = min(float(limit), float(baseline) + max(0.0, float(overlay)))
            if abs(float(combined)-expected_combined) > TOLERANCE_W:
                calc_fail += 1; _issue(issues,"calculation","FAIL","COMBINED_TARGET_MISMATCH",f"combined={combined:.1f}, expected={expected_combined:.1f}",row)
        if primary_state == "NEAR_LIMIT":
            primary_power = _float(row.get("second_battery_power_w")); primary_max = _float(row.get("fast_capture_primary_max_charge_w")); reserve = _float(row.get("fast_capture_primary_reserve_w"))
            if None not in (primary_power, primary_max, reserve):
                calc_eval += 1
                expected_reserve=max(0.0,float(primary_max)-max(0.0,float(primary_power)))
                if abs(float(reserve)-expected_reserve)>TOLERANCE_W:
                    calc_fail += 1; _issue(issues,"calculation","FAIL","PRIMARY_RESERVE_MISMATCH",f"reserve={reserve:.1f}, expected={expected_reserve:.1f}",row)

        if previous is not None and distinct is True and dt is not None and 0.0 < dt <= CONTINUITY_GAP_S and overlay is not None:
            prev_overlay=_float(previous.get("fast_capture_overlay_w"))
            if prev_overlay is not None and not forced:
                delta=overlay-prev_overlay
                if delta > TOLERANCE_W:
                    calc_eval += 1
                    if delta > ATTACK_W_PER_S*dt+TOLERANCE_W:
                        calc_fail += 1; _issue(issues,"calculation","FAIL","A400_EXCEEDED",f"+{delta:.1f} W in {dt:.2f} s",row)
                elif delta < -TOLERANCE_W:
                    calc_eval += 1
                    if -delta > RELEASE_W_PER_S*dt+TOLERANCE_W:
                        calc_fail += 1; _issue(issues,"calculation","FAIL","R100_EXCEEDED",f"{delta:.1f} W in {dt:.2f} s",row)

        if mode == "shadow" and baseline is not None and _downstream_clear(row):
            target=_float(row.get("target_final_w"))
            if target is not None:
                shadow_eval += 1
                if abs(target-baseline)>TOLERANCE_W:
                    shadow_fail += 1; _issue(issues,"calculation","FAIL","SHADOW_TARGET_MUTATION",f"target_final={target:.1f}, baseline={baseline:.1f}",row)
        if mode == "active" and overlay is not None and overlay > TOLERANCE_W and combined is not None and _downstream_clear(row):
            target=_float(row.get("target_final_w"))
            if target is not None:
                calc_eval += 1
                if abs(target-combined)>TOLERANCE_W:
                    calc_fail += 1; _issue(issues,"calculation","FAIL","ACTIVE_TARGET_NOT_COMBINED",f"target_final={target:.1f}, combined={combined:.1f}",row)

        if forced:
            recovery_eval += 1
            if abs(overlay or 0.0)>TOLERANCE_W or active is True:
                recovery_fail += 1; _issue(issues,"recovery","FAIL","FORCED_ZERO_NOT_ZERO",f"forced reason {forced} retained overlay/active",row)
        previous=row

    episodes=_split_episodes(rows)
    episode_reports=[]
    physical_evaluable=0; physical_pass=0; physical_warn=0; physical_fail=0
    for idx, episode in enumerate(episodes, start=1):
        start_ms=_int(episode[0].get("measurement_epoch_ms")); end_ms=_int(episode[-1].get("measurement_epoch_ms"))
        modes=sorted({str(r.get("fast_capture_mode") or "off").lower() for r in episode})
        states=sorted({str(r.get("fast_capture_primary_state") or "RESERVE_UNKNOWN") for r in episode})
        overlays=[_float(r.get("fast_capture_overlay_w")) for r in episode]
        active_rows=[r for r in episode if str(r.get("fast_capture_mode") or "").lower()=="active" and (_float(r.get("fast_capture_overlay_w")) or 0)>TOLERANCE_W]
        status="NOT_EVALUABLE"; detail="SHADOW_OR_NO_POSITIVE_ACTIVE_OVERLAY"
        metrics: Dict[str, Any] = {"max_overlay_w": max([v for v in overlays if v is not None], default=0.0)}
        if active_rows:
            valid=[r for r in active_rows if _bool(r.get("zendure_actual_power_valid")) is True and _bool(r.get("zendure_actual_power_fresh")) is True]
            if len(valid) >= 3:
                physical_evaluable += 1
                grid_exports=[max(0.0,-(_float(r.get("grid_power_w")) or 0.0)) for r in valid]
                actual=[_float(r.get("zendure_actual_power_w")) for r in valid]
                desired=[_float(r.get("fast_capture_overlay_w")) for r in valid]
                effect_categories=[str(r.get("command_effect_category") or "") for r in valid]
                metrics.update({
                    "median_grid_export_w": _median(grid_exports),
                    "median_zendure_actual_power_w": _median(actual),
                    "median_overlay_w": _median(desired),
                    "command_effect_categories": sorted(set(effect_categories)),
                })
                confirmed=sum(1 for r in valid if str(r.get("command_effect_category") or "") in {"COMMAND_DIRECTION_EFFECTIVE","COMMAND_TARGET_TRACKING_EFFECTIVE","COMMAND_PARTIALLY_EFFECTIVE"})
                mismatch=sum(1 for r in valid if str(r.get("command_effect_category") or "") == "COMMAND_MISMATCH_CONFIRMED")
                import_rows=sum(1 for r in valid if (_float(r.get("grid_power_w")) or 0.0) > 100.0)
                if mismatch or import_rows:
                    status="FAIL"; detail="MISMATCH_OR_PERSISTENT_IMPORT_DURING_ACTIVE"; physical_fail += 1
                elif confirmed:
                    status="PASS"; detail="INDEPENDENT_EFFECT_EVIDENCE_PRESENT"; physical_pass += 1
                else:
                    status="WARN"; detail="ACTIVE_EPISODE_WITHOUT_ROBUST_EFFECT_CLASSIFICATION"; physical_warn += 1
            else:
                status="NOT_EVALUABLE"; detail="INSUFFICIENT_FRESH_INDEPENDENT_POWER_SAMPLES"
        episode_reports.append({"episode":idx,"start_ms":start_ms,"end_ms":end_ms,"row_count":len(episode),"modes":modes,"primary_states":states,"physical_effect_status":status,"physical_effect_detail":detail,"metrics":metrics})

    manifest_ev=_manifest_evidence(manifest); version_ev=_config_version_evidence(snapshots)
    structural_fail=sum(1 for x in (manifest_ev,version_ev) if x.get("status")=="FAIL")
    structural_warn=sum(1 for x in (manifest_ev,version_ev) if x.get("status")=="WARN")
    state_status=_status_from_counts(state_fail,state_eval)
    calc_status=_status_from_counts(calc_fail,calc_eval)
    recovery_status=_status_from_counts(recovery_fail,recovery_eval)
    physical_status="FAIL" if physical_fail else ("PASS" if physical_pass and not physical_warn else ("WARN" if physical_warn else "NOT_EVALUABLE"))
    shadow_status=_status_from_counts(shadow_fail,shadow_eval)
    fail_count=structural_fail + state_fail + calc_fail + recovery_fail + shadow_fail + physical_fail
    any_fast_evidence=any(str(r.get("fast_capture_mode") or "off").lower() in {"shadow","active"} for r in rows)
    if fail_count:
        overall="FAIL"
    elif not any_fast_evidence or (not episodes and shadow_eval==0):
        overall="NOT_EVALUABLE"
    elif physical_status=="NOT_EVALUABLE":
        overall="WARN"
    elif structural_warn or physical_warn:
        overall="WARN"
    else:
        overall="PASS"
    return {
        "format":FORMAT,"status":overall,"strategy":"A400_R100","row_count":len(rows),
        "episode_count":len(episodes),"manifest_evidence":manifest_ev,"controller_version_evidence":version_ev,
        "dimensions":{
            "state":{"status":state_status,"evaluated":state_eval,"failures":state_fail},
            "calculation":{"status":calc_status,"evaluated":calc_eval,"failures":calc_fail,"shadow_mutation":{"status":shadow_status,"evaluated":shadow_eval,"failures":shadow_fail}},
            "physical_effect":{"status":physical_status,"evaluable_episodes":physical_evaluable,"pass":physical_pass,"warn":physical_warn,"fail":physical_fail},
            "recovery":{"status":recovery_status,"evaluated":recovery_eval,"failures":recovery_fail},
        },
        "episodes":episode_reports,"issues":issues,
        "commands_published_by_this_tool":0,"configuration_mutations_by_this_tool":0,
    }


def analyze_files(csv_paths: Sequence[Path], *, manifest_path: Optional[Path] = None, config_snapshots_path: Optional[Path] = None) -> Dict[str, Any]:
    if not csv_paths:
        raise ValueError("No Measurement-V4 CSV files supplied")
    rows, header=_read_rows(csv_paths)
    result=analyze_rows(rows,manifest=_load_json(manifest_path),snapshots=_load_json(config_snapshots_path))
    result["input"]={"csv_files":[str(p) for p in csv_paths],"header_field_count":len(header),"manifest":str(manifest_path) if manifest_path else None,"config_snapshots":str(config_snapshots_path) if config_snapshots_path else None}
    return result


def _human(result: Dict[str, Any]) -> str:
    lines=["ZEC Fast Capture A400/R100 field analysis",f"status={result.get('status')}",f"rows={result.get('row_count')} episodes={result.get('episode_count')}"]
    for name,data in (result.get("dimensions") or {}).items():
        lines.append(f"{name}={data.get('status')}")
    for ep in result.get("episodes") or []:
        lines.append(f"episode {ep['episode']}: {ep['physical_effect_status']} {ep['physical_effect_detail']} [{ep['start_ms']}..{ep['end_ms']}]")
    for issue in result.get("issues") or []:
        lines.append(f"{issue['status']} {issue['dimension']} {issue['code']}: {issue['detail']}")
    return "\n".join(lines)+"\n"


def parse_args(argv: Optional[Sequence[str]]=None) -> argparse.Namespace:
    p=argparse.ArgumentParser(description="Read-only ZEC V17 Fast Capture A400/R100 field analysis")
    p.add_argument("csv", nargs="*", help="Measurement-V4 CSV files or glob patterns")
    p.add_argument("--manifest", default="")
    p.add_argument("--config-snapshots", default="")
    p.add_argument("--output", default="")
    p.add_argument("--human-output", default="")
    p.add_argument("--describe", action="store_true", help="Describe analyzer contract without reading field data")
    p.add_argument("--json", action="store_true", help="Print JSON result")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]]=None) -> int:
    args=parse_args(argv)
    if args.describe:
        result=describe_contract()
        print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True) if args.json else _human({"status":"CONTRACT","row_count":0,"episode_count":0,"dimensions":{}}))
        return 0
    paths=_expand_csv_args(args.csv)
    try:
        result=analyze_files(paths,manifest_path=Path(args.manifest).resolve() if args.manifest else None,config_snapshots_path=Path(args.config_snapshots).resolve() if args.config_snapshots else None)
    except Exception as exc:
        result={"format":FORMAT,"status":"FAIL","fatal_error":f"{type(exc).__name__}: {exc}","commands_published_by_this_tool":0,"configuration_mutations_by_this_tool":0}
    if args.output:
        out=Path(args.output).expanduser().resolve(); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if args.human_output:
        out=Path(args.human_output).expanduser().resolve(); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(_human(result),encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 1 if result.get("status")=="FAIL" else 0

if __name__ == "__main__":
    raise SystemExit(main())
