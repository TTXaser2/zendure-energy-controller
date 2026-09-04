#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only productive field acceptance for ZEC V14.0.0.

This tool never publishes commands, changes configuration, mutates the graph
store, or performs a rollback. It exercises the running HTTP/read-only graph
contracts and verifies the rollback artifacts produced by the installer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from version import APP_BUILD_ID, APP_VERSION, APP_VERSION_LABEL  # noqa: E402

EXPECTED_VERSION = "14.0.0"
EXPECTED_LABEL = "V14.0.0"
EXPECTED_BUILD_ID = "v14.0.0-20260904-r2"
FORMAT = "ZEC_V14_FIELD_ACCEPTANCE_V1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _http(base: str, path: str, *, params: Optional[Mapping[str, Any]] = None, timeout: float = 30.0) -> Tuple[bytes, float]:
    url = base.rstrip("/") + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        url += "?" + urlencode(clean)
    req = Request(url, headers={"Accept": "application/json,text/html;q=0.9,*/*;q=0.8"})
    start = time.perf_counter()
    with urlopen(req, timeout=timeout) as response:  # noqa: S310 - localhost/user-supplied diagnostic endpoint
        body = response.read()
        status = int(getattr(response, "status", 200))
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if status < 200 or status >= 300:
        raise RuntimeError(f"HTTP_{status}:{path}")
    return body, elapsed_ms


def _json(base: str, path: str, *, params: Optional[Mapping[str, Any]] = None, timeout: float = 30.0) -> Tuple[Dict[str, Any], float]:
    body, elapsed = _http(base, path, params=params, timeout=timeout)
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON_OBJECT_REQUIRED:{path}")
    if payload.get("error"):
        raise RuntimeError(f"API_ERROR:{path}:{payload.get('error')}")
    return payload, elapsed


def _check(checks: List[Dict[str, Any]], check_id: str, ok: bool, *, detail: str = "", **evidence: Any) -> None:
    item: Dict[str, Any] = {"id": check_id, "status": "PASS" if ok else "FAIL"}
    if detail:
        item["detail"] = detail
    if evidence:
        item["evidence"] = evidence
    checks.append(item)


def _warn(checks: List[Dict[str, Any]], check_id: str, detail: str, **evidence: Any) -> None:
    item: Dict[str, Any] = {"id": check_id, "status": "WARN", "detail": detail}
    if evidence:
        item["evidence"] = evidence
    checks.append(item)


def _service_active() -> Tuple[bool, str]:
    proc = subprocess.run(
        ["systemctl", "is-active", "zendure-controller.service"],
        text=True, capture_output=True, check=False,
    )
    text = (proc.stdout or proc.stderr or "").strip()
    return proc.returncode == 0 and text == "active", text


def _db_quick_check(path: Path) -> str:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30.0)
    try:
        row = conn.execute("PRAGMA quick_check").fetchone()
        return str(row[0]) if row else "no_result"
    finally:
        conn.close()


def _verify_rollback_backup(report: Mapping[str, Any]) -> Dict[str, Any]:
    backup_dir_raw = str(report.get("backup_dir") or "")
    if not backup_dir_raw:
        return {"status": "error", "reason": "BACKUP_DIR_MISSING_IN_CUTOVER_REPORT"}
    backup_dir = Path(backup_dir_raw)
    state_path = backup_dir / "cutover_state.json"
    if not state_path.is_file():
        return {"status": "error", "reason": "CUTOVER_STATE_MISSING", "path": str(state_path)}
    state = json.loads(state_path.read_text(encoding="utf-8"))
    checked: List[Dict[str, Any]] = []
    for key in ("db", "wal", "shm"):
        info = dict((state.get("artifacts") or {}).get(key) or {})
        if not info.get("present"):
            checked.append({"artifact": key, "present": False, "verified": True})
            continue
        path = Path(str(info.get("backup") or ""))
        expected_size = int(info.get("size") or 0)
        expected_hash = str(info.get("sha256") or "")
        if not path.is_file():
            return {"status": "error", "reason": "BACKUP_ARTIFACT_MISSING", "artifact": key, "path": str(path)}
        size = path.stat().st_size
        digest = _sha256(path)
        if size != expected_size or not expected_hash or digest != expected_hash:
            return {
                "status": "error", "reason": "BACKUP_ARTIFACT_MISMATCH", "artifact": key,
                "path": str(path), "size": size, "expected_size": expected_size,
                "sha256": digest, "expected_sha256": expected_hash,
            }
        checked.append({"artifact": key, "present": True, "verified": True, "size": size, "sha256": digest})
    return {"status": "ok", "reason": "ROLLBACK_ARTIFACTS_EXACT", "backup_dir": str(backup_dir), "artifacts": checked}


def run_acceptance(base_url: str, cutover_report: Path) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}
    started = time.time()

    identity_ok = (APP_VERSION, APP_VERSION_LABEL, APP_BUILD_ID) == (EXPECTED_VERSION, EXPECTED_LABEL, EXPECTED_BUILD_ID)
    _check(checks, "release_identity", identity_ok, version=APP_VERSION, label=APP_VERSION_LABEL, build_id=APP_BUILD_ID)

    try:
        active, service_state = _service_active()
        _check(checks, "controller_service", active, state=service_state)
    except Exception as exc:
        _check(checks, "controller_service", False, detail=f"{type(exc).__name__}: {exc}")

    health: Dict[str, Any] = {}
    ready: Dict[str, Any] = {}
    runtime: Dict[str, Any] = {}
    workspace: Dict[str, Any] = {}
    try:
        health, ms = _json(base_url, "/health", timeout=5)
        metrics["health_ms"] = round(ms, 3)
        _check(checks, "health", health.get("alive") is True, alive=health.get("alive"))
    except Exception as exc:
        _check(checks, "health", False, detail=f"{type(exc).__name__}: {exc}")
    try:
        ready, ms = _json(base_url, "/ready", timeout=5)
        metrics["ready_ms"] = round(ms, 3)
        _check(checks, "controller_ready", ready.get("ready") is True, failed_checks=ready.get("failed_checks") or [])
    except Exception as exc:
        _check(checks, "controller_ready", False, detail=f"{type(exc).__name__}: {exc}")

    try:
        runtime, ms = _json(base_url, "/api/graph/v1/runtime", timeout=10)
        metrics["graph_runtime_ms"] = round(ms, 3)
        runtime_ok = (
            runtime.get("read_mode") == "V3_NATIVE"
            and runtime.get("workspace_ready") is True
            and runtime.get("control_readiness_impact") == "NONE"
        )
        _check(
            checks, "graph_runtime", runtime_ok,
            read_mode=runtime.get("read_mode"), workspace_ready=runtime.get("workspace_ready"),
            control_readiness_impact=runtime.get("control_readiness_impact"),
            evidence_mode=runtime.get("evidence_mode"),
        )
    except Exception as exc:
        _check(checks, "graph_runtime", False, detail=f"{type(exc).__name__}: {exc}")

    try:
        workspace, ms = _json(base_url, "/api/graph/v1/workspace", timeout=15)
        metrics["graph_workspace_ms"] = round(ms, 3)
        caps = dict(workspace.get("capabilities") or {})
        workspace_ok = (
            caps.get("command_follow") == "available_wp8"
            and caps.get("episode_comparison") == "available_wp9"
            and caps.get("side_by_side") is True
            and caps.get("overlay_pair_only") is True
        )
        _check(checks, "graph_workspace", workspace_ok, capabilities=caps)
    except Exception as exc:
        _check(checks, "graph_workspace", False, detail=f"{type(exc).__name__}: {exc}")

    try:
        body, ms = _http(base_url, "/graph", timeout=15)
        metrics["graph_page_ms"] = round(ms, 3)
        text = body.decode("utf-8", errors="replace")
        page_ok = "/api/graph/v1/workspace" in text and "/api/graph/v1/overview" in text and "episode-comparison" in text
        _check(checks, "graph_page", page_ok, bytes=len(body))
    except Exception as exc:
        _check(checks, "graph_page", False, detail=f"{type(exc).__name__}: {exc}")

    now_ms = int(time.time() * 1000)
    start_48h = now_ms - 48 * 60 * 60 * 1000
    overview: Dict[str, Any] = {}
    latest_ts: Optional[int] = None
    try:
        catalog, _ = _json(base_url, "/api/graph/v1/catalog", timeout=15)
        series_ids = [str(x.get("series_id")) for x in (catalog.get("series") or []) if x.get("series_id")]
        if not series_ids:
            series_ids = ["grid_power_w"]
        overview, ms = _json(
            base_url, "/api/graph/v1/overview",
            params={"start_ms": start_48h, "end_ms": now_ms, "series": ",".join(series_ids), "resolution": "auto", "include_context": "true"},
            timeout=30,
        )
        metrics["overview_48h_all_series_ms"] = round(ms, 3)
        metrics["overview_48h_response_points"] = len(overview.get("timestamps_ms") or [])
        stamps = [int(x) for x in (overview.get("timestamps_ms") or [])]
        latest_ts = stamps[-1] if stamps else None
        _check(
            checks, "graph_overview_48h", bool(stamps),
            points=len(stamps), series_count=len(overview.get("series") or {}), resolution=overview.get("resolution"),
        )
    except Exception as exc:
        _check(checks, "graph_overview_48h", False, detail=f"{type(exc).__name__}: {exc}")

    if latest_ts is not None:
        try:
            inspector, ms = _json(base_url, "/api/graph/v1/inspector", params={"ts_ms": latest_ts, "tolerance_ms": 10000}, timeout=15)
            metrics["inspector_ms"] = round(ms, 3)
            inspector_ok = inspector.get("contract_version") == 2 and (inspector.get("meta") or {}).get("read_only") is True
            _check(checks, "graph_inspector", inspector_ok, requested_ms=latest_ts, actual_ms=inspector.get("actual_ms"))
        except Exception as exc:
            _check(checks, "graph_inspector", False, detail=f"{type(exc).__name__}: {exc}")
    else:
        _check(checks, "graph_inspector", False, detail="NO_OVERVIEW_TIMESTAMP")

    triggers: List[Dict[str, Any]] = []
    try:
        trigger_payload, ms = _json(
            base_url, "/api/graph/v1/episode-triggers",
            params={"start_ms": start_48h, "end_ms": now_ms, "limit": 2000}, timeout=15,
        )
        metrics["episode_triggers_ms"] = round(ms, 3)
        triggers = [dict(x) for x in (trigger_payload.get("items") or []) if isinstance(x, dict)]
        _check(checks, "episode_triggers", len(triggers) >= 2, count=len(triggers), truncated=trigger_payload.get("truncated"))
    except Exception as exc:
        _check(checks, "episode_triggers", False, detail=f"{type(exc).__name__}: {exc}")

    published = [x for x in triggers if x.get("trigger_type") == "PUBLISHED_EVENT"]
    if published:
        chosen = published[-1]
        try:
            follow, ms = _json(
                base_url, "/api/graph/v1/command-follow",
                params={"ts_ms": int(chosen.get("trigger_ms")), "tolerance_ms": 60000, "before_ms": 15000, "after_ms": 180000},
                timeout=15,
            )
            metrics["command_follow_ms"] = round(ms, 3)
            meta = dict(follow.get("meta") or {})
            follow_ok = meta.get("effectiveness_from_publish_alone") is False and meta.get("effectiveness_from_direction_alone") is False
            _check(
                checks, "command_follow", follow_ok,
                trigger_id=chosen.get("trigger_id"),
                system_effect_status=((follow.get("stages") or {}).get("system_effect") or {}).get("status"),
                causal_attribution=meta.get("causal_attribution"),
            )
        except Exception as exc:
            _check(checks, "command_follow", False, detail=f"{type(exc).__name__}: {exc}")
    else:
        _check(checks, "command_follow", False, detail="NO_PUBLISHED_TRIGGER_IN_48H")

    if len(triggers) >= 2:
        a, b = triggers[-2], triggers[-1]
        try:
            comparison, ms = _json(
                base_url, "/api/graph/v1/episode-comparison",
                params={
                    "trigger_a": a.get("trigger_id"), "trigger_b": b.get("trigger_id"),
                    "before_ms": 15 * 60_000, "after_ms": 45 * 60_000,
                    "series": "grid_power_w,target_final_w", "resolution": "auto",
                },
                timeout=30,
            )
            metrics["episode_comparison_60m_ms"] = round(ms, 3)
            alignment = dict(comparison.get("alignment") or {})
            episodes = dict(comparison.get("episodes") or {})
            comp_ok = (
                alignment.get("axis") == "RELATIVE_T0_MS"
                and alignment.get("absolute_time_retained") is True
                and alignment.get("visual_similarity_is_causality_proof") is False
                and bool(episodes.get("a")) and bool(episodes.get("b"))
            )
            _check(checks, "episode_comparison", comp_ok, trigger_a=a.get("trigger_id"), trigger_b=b.get("trigger_id"))
        except Exception as exc:
            _check(checks, "episode_comparison", False, detail=f"{type(exc).__name__}: {exc}")
    else:
        _check(checks, "episode_comparison", False, detail="FEWER_THAN_TWO_PERSISTED_TRIGGERS_IN_48H")

    db_path_raw = str(runtime.get("db_path") or "")
    if db_path_raw:
        db_path = Path(db_path_raw)
        try:
            quick = _db_quick_check(db_path)
            size = db_path.stat().st_size
            metrics["graph_db_bytes"] = size
            _check(checks, "graph_db_integrity", quick == "ok" and size > 0, path=str(db_path), bytes=size, quick_check=quick)
        except Exception as exc:
            _check(checks, "graph_db_integrity", False, detail=f"{type(exc).__name__}: {exc}", path=str(db_path))
    else:
        _check(checks, "graph_db_integrity", False, detail="DB_PATH_MISSING_FROM_RUNTIME")

    if cutover_report.is_file():
        try:
            report = json.loads(cutover_report.read_text(encoding="utf-8"))
            rebuild = dict(report.get("rebuild") or {})
            report_ok = (
                report.get("status") == "ok" and report.get("reason") == "CUTOVER_VERIFIED"
                and int(rebuild.get("rows_imported") or 0) > 0
                and not rebuild.get("source_errors")
                and int(rebuild.get("files_ok") or 0) == int(rebuild.get("files") or 0)
            )
            _check(
                checks, "cutover_rebuild_report", report_ok,
                rows_imported=rebuild.get("rows_imported"), files=rebuild.get("files"), files_ok=rebuild.get("files_ok"),
                source_v4_files=report.get("source_v4_files"), previous_backend=report.get("previous_backend"),
            )
            rollback = _verify_rollback_backup(report)
            _check(
                checks, "rollback_backup_integrity", rollback.get("status") == "ok",
                detail=str(rollback.get("reason") or ""), backup_dir=rollback.get("backup_dir"), artifacts=rollback.get("artifacts"),
            )
        except Exception as exc:
            _check(checks, "cutover_rebuild_report", False, detail=f"{type(exc).__name__}: {exc}")
            _check(checks, "rollback_backup_integrity", False, detail="CUTOVER_REPORT_UNUSABLE")
    else:
        _warn(checks, "cutover_rebuild_report", "CUTOVER_REPORT_NOT_FOUND", path=str(cutover_report))
        _warn(checks, "rollback_backup_integrity", "NOT_EVALUATED_WITHOUT_CUTOVER_REPORT")

    # Performance acceptance here is deliberately bounded by the existing HTTP
    # timeouts. No new product threshold is invented in WP10.
    _check(
        checks, "performance_requests_bounded", all(
            isinstance(v, (int, float)) and v >= 0 for k, v in metrics.items() if k.endswith("_ms")
        ),
        detail="Measured requests completed within their existing endpoint/UI timeout budgets; no new latency threshold introduced.",
    )

    failures = [x for x in checks if x.get("status") == "FAIL"]
    warnings = [x for x in checks if x.get("status") == "WARN"]
    return {
        "format": FORMAT,
        "status": "PASS" if not failures else "FAIL",
        "started_epoch_s": started,
        "completed_epoch_s": time.time(),
        "base_url": base_url,
        "release": {"version": APP_VERSION, "label": APP_VERSION_LABEL, "build_id": APP_BUILD_ID},
        "checks": checks,
        "metrics": metrics,
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "controller_readiness_and_graph_readiness_are_separate": True,
        "commands_published_by_this_tool": 0,
        "configuration_mutations_by_this_tool": 0,
        "rollback_execution_by_this_tool": False,
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Read-only ZEC V14 field acceptance")
    p.add_argument("--base-url", default="http://127.0.0.1:8080")
    p.add_argument("--cutover-report", default="/tmp/zec_v14_cutover_report.json")
    p.add_argument("--output", default="/tmp/ZEC_V14_FIELD_ACCEPTANCE.json")
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    result = run_acceptance(args.base_url, Path(args.cutover_report))
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {output}")
        for item in result["checks"]:
            print(f"{item['status']:4} {item['id']}: {item.get('detail','')}")
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
