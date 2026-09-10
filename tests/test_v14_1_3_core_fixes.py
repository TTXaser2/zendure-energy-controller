from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from unittest.mock import patch

from control_state_semantics import derive_control_state, project_graph_state_row
from csv_logger import CsvRotatingLogger
from graph_core_v3 import connect_graph_core
from graph_history_runtime import query_storage_day_history
from graph_query_service import GraphQueryService
from measurement_v4 import build_v4_row
from tools.backfill_graph_control_states_v14_1_3 import apply_repair, collect_repair_intervals

ROOT = Path(__file__).resolve().parents[1]


def _raw_state_row(**overrides):
    row = {
        "epoch_s": 1788700000.0,
        "cycle_id": 42,
        "mode": "AUTO",
        "target_final_w": 750,
        "target_final_reason": "PV-Überschuss erkannt -> Zendure lädt",
        "technical_limiters": "",
        "grid_power_w": -10,
        "zendure_actual_power_w": 700,
        "zendure_soc_percent": 55,
        "second_battery_power_w": 100,
        "second_battery_soc_percent": 70,
    }
    row.update(overrides)
    return row


def test_shared_control_state_projection_matches_measurement_v4_contract():
    raw = _raw_state_row()
    projected = project_graph_state_row(raw)
    v4 = build_v4_row({}, raw)
    assert projected["operating_mode"] == v4["operating_mode"]
    assert projected["control_intent"] == v4["control_intent"]
    assert projected["operating_mode"] == "AUTO"
    assert projected["control_intent"] == "CHARGE"


def test_graph_queue_gets_state_projection_even_when_v4_logging_is_off():
    raw = _raw_state_row(mode="HOLD", target_final_w=0)
    captured = {}

    class FakeV4:
        def log(self, _config, _row):
            return {"measurement_log_status": "disabled"}

    logger = CsvRotatingLogger()
    logger._v4_logger = FakeV4()

    def capture(_config, row):
        captured.update(row)
        return {"measurement_db_status": "queued"}

    with patch.object(logger, "_enqueue_measurement_db", side_effect=capture):
        status = logger.log({"MEASUREMENT_LOG_MODE": "off"}, raw)

    assert status["measurement_log_status"] == "disabled"
    assert status["measurement_db_status"] == "queued"
    assert captured["operating_mode"] == "HOLD"
    assert captured["control_intent"] == "HOLD"
    # The caller-owned raw controller row remains untouched.
    assert "operating_mode" not in raw
    assert "control_intent" not in raw


def _write_minimal_v4(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["measurement_epoch_ms", "operating_mode", "control_intent"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)


def test_state_backfill_repairs_only_missing_suffix_and_is_idempotent(tmp_path):
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        conn.execute(
            "INSERT INTO graph_intervals(kind,start_ms,end_ms,value_code,source,quality) VALUES(?,?,?,?,?,?)",
            ("OPERATING_MODE", 500, 1000, "HOLD", "OLD", "OBSERVED"),
        )
        conn.execute(
            "INSERT INTO graph_intervals(kind,start_ms,end_ms,value_code,source,quality) VALUES(?,?,?,?,?,?)",
            ("CONTROL_INTENT", 500, 1000, "HOLD", "OLD", "OBSERVED"),
        )
        conn.execute(
            "INSERT INTO graph_intervals(kind,start_ms,end_ms,value_code,source,quality) VALUES(?,?,?,?,?,?)",
            ("CONTROL_REASON", 500, 1500, "unchanged", "OLD", "OBSERVED"),
        )
        conn.execute(
            "INSERT INTO measurement_1min(bucket_start_ms,sample_count,first_ts_ms,last_ts_ms,quality_or) VALUES(?,?,?,?,?)",
            (0, 1, 500, 500, 0),
        )
        conn.commit()

        v4 = tmp_path / "zendure_measurements_v4_test.csv"
        _write_minimal_v4(v4, [
            {"measurement_epoch_ms": 900, "operating_mode": "HOLD", "control_intent": "HOLD"},
            {"measurement_epoch_ms": 1100, "operating_mode": "AUTO", "control_intent": "CHARGE"},
            {"measurement_epoch_ms": 1200, "operating_mode": "AUTO", "control_intent": "CHARGE"},
            {"measurement_epoch_ms": 1300, "operating_mode": "AUTO", "control_intent": "DISCHARGE"},
        ])

        collected = collect_repair_intervals(conn, [v4])
        assert collected["cutoffs_before_ms"] == {"OPERATING_MODE": 1000, "CONTROL_INTENT": 1000}
        assert len(collected["intervals"]["OPERATING_MODE"]) == 1
        assert len(collected["intervals"]["CONTROL_INTENT"]) == 2
        inserted = apply_repair(conn, collected, apply=True)
        assert inserted == {"OPERATING_MODE": 1, "CONTROL_INTENT": 2}

        # Numeric graph data and the already-correct reason timeline are untouched.
        assert conn.execute("SELECT COUNT(*) FROM measurement_1min").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM graph_intervals WHERE kind='CONTROL_REASON'").fetchone()[0] == 1

        again = collect_repair_intervals(conn, [v4])
        assert again["intervals"]["OPERATING_MODE"] == []
        assert again["intervals"]["CONTROL_INTENT"] == []
    finally:
        conn.close()


def test_state_backfill_does_not_bridge_real_v4_gap(tmp_path):
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        v4 = tmp_path / "zendure_measurements_v4_gap.csv"
        _write_minimal_v4(v4, [
            {"measurement_epoch_ms": 1000, "operating_mode": "AUTO", "control_intent": "CHARGE"},
            {"measurement_epoch_ms": 4000, "operating_mode": "AUTO", "control_intent": "CHARGE"},
            {"measurement_epoch_ms": 50_000, "operating_mode": "AUTO", "control_intent": "CHARGE"},
        ])
        collected = collect_repair_intervals(conn, [v4], max_gap_ms=10_000)
        mode = collected["intervals"]["OPERATING_MODE"]
        intent = collected["intervals"]["CONTROL_INTENT"]
        assert len(mode) == 2
        assert len(intent) == 2
        assert mode[0][2] == 4001
        assert mode[1][1] == 50_000
    finally:
        conn.close()


def test_runtime_hint_avoids_duplicate_runtime_probe():
    runtime = {"read_mode": "V3_NATIVE", "workspace_ready": True}
    with patch("graph_history_runtime.graph_history_runtime_status", side_effect=AssertionError("must not probe")):
        with patch("graph_history_runtime._v3_storage_day", return_value={"points": [], "runtime": runtime}) as v3:
            result = query_storage_day_history(
                {},
                __import__("datetime").datetime(2026, 9, 6),
                __import__("datetime").datetime(2026, 9, 7),
                runtime_hint=runtime,
                status_fast=True,
            )
    assert result["runtime"] == runtime
    assert v3.call_args.kwargs["runtime_hint"] == runtime


def test_status_soc_fast_path_is_deliberately_lean_source_contract():
    source = (ROOT / "graph_query_service.py").read_text(encoding="utf-8")
    body = source.split("    def storage_day_status(", 1)[1].split("    def evidence(", 1)[0]
    assert '"zendure_actual_power_w"' in body
    assert '"primary_soc_percent"' in body
    assert "kind IN ('OPERATING_MODE','CONTROL_REASON')" in body
    assert "self.coverage(" not in body
    assert "self.evidence(" not in body
    assert "self.entity_overview(" not in body
    assert "_query_events(" not in body


def test_status_soc_browser_uses_stale_while_revalidate_cache():
    js = (ROOT / "static/status_v2.js").read_text(encoding="utf-8")
    assert "zec:soc-day:v14.1.3:" in js
    assert "sessionStorage.getItem" in js
    assert "Gespeicherter Stand" in js
    assert "wird aktualisiert" in js
    assert "visibleSameDate" in js
    assert "String(socChart.payload?.date||'')===requestedDate" in js


def test_zoom_selection_uses_integer_epoch_ms_and_commands_have_own_lane():
    js = (ROOT / "static/graph_v14_1.js").read_text(encoding="utf-8")
    assert "start:Math.round(Number(start))" in js
    assert "end:Math.round(Number(end))" in js
    assert "gf-command-row" in js
    assert ">Commands</div>" in js
    # Published command events must no longer masquerade as operating mode.
    state_body = js.split("function renderStateTimeline", 1)[1].split("function renderInspector", 1)[0]
    assert "eventItems" in state_body
    assert "commandRow" in state_body


def test_settings_controller_logic_remains_outside_core_fix_scope():
    # Guard the architectural boundary in this block: state projection happens
    # before persistence, not by modifying controller_logic.py semantics.
    expected = "d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff"
    import hashlib
    digest = hashlib.sha256((ROOT / "controller_logic.py").read_bytes()).hexdigest()
    assert digest == expected
