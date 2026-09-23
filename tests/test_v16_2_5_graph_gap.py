from pathlib import Path

from graph_core_v3 import connect_graph_core
from graph_core_v3_live import GraphCoreV3LiveSession
from graph_query_service import GraphQueryService


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _row(ts_ms: int, seq: int = 1):
    return {
        "epoch_s": ts_ms / 1000.0,
        "cycle_id": seq,
        "grid_power_w": 100.0 + seq,
        "raw_grid_power_w": 101.0 + seq,
        "grid_power_valid": True,
        "zendure_actual_power_w": 90.0,
        "actual_zendure_power_valid": True,
        "zendure_soc_percent": 50.0,
        "soc_valid": True,
        "target_raw_w": 120.0,
        "target_after_power_limit_w": 115.0,
        "target_after_smoothing_w": 110.0,
        "target_after_ramp_w": 105.0,
        "target_final_w": 100.0,
        "operating_mode": "AUTO",
        "control_intent": "CHARGE",
        "command_desired_sequence_id": seq,
        "command_desired_signed_target_w": 100.0,
        "command_publish_event_id": seq,
        "command_publish_epoch_s": ts_ms / 1000.0,
        "zendure_command_ac_mode": "input",
        "zendure_command_input_limit_w": 100.0,
        "zendure_command_output_limit_w": 0.0,
        "zendure_unit_count": 1,
    }


def _live_db(tmp_path: Path, rows):
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        GraphCoreV3LiveSession(run_id=(1 << 62) + 1625).write_batch(conn, str(db), rows)
    finally:
        conn.close()
    return db


def test_real_gap_is_evidence_gap_but_normal_sampling_jitter_is_not(tmp_path):
    start = (1_790_000_000_000 // 60_000) * 60_000

    jitter_db = _live_db(tmp_path / "jitter", [_row(start + 1_000), _row(start + 4_000, 2)])
    jitter_segments = GraphQueryService(cache_max_entries=0).evidence(
        str(jitter_db), start + 1_000, start + 4_000,
        series_ids=["grid_power_w"], resolution="highres",
    )["series"]["grid_power_w"]
    assert [segment["status"] for segment in jitter_segments] == ["AVAILABLE"]

    gap_root = tmp_path / "gap"
    gap_root.mkdir()
    gap_db = _live_db(gap_root, [_row(start + 1_000), _row(start + 61_000, 2)])
    gap_segments = GraphQueryService(cache_max_entries=0).evidence(
        str(gap_db), start + 1_000, start + 61_000,
        series_ids=["grid_power_w"], resolution="highres",
    )["series"]["grid_power_w"]
    statuses = [segment["status"] for segment in gap_segments]
    assert statuses == ["AVAILABLE", "GAP", "AVAILABLE"]
    gap = gap_segments[1]
    assert gap["from_ms"] > start + 1_000
    assert gap["to_ms"] < start + 61_000


def test_frontend_inserts_null_breaks_from_evidence_without_synthetic_values():
    js = _text("static/graph_v14_1.js")
    assert "function gapAwareData" in js
    assert "if(status==='AVAILABLE')continue" in js
    assert "y:null,gfEvidenceGap:status" in js
    assert "spanGaps:false" in js
    assert "evidenceSegments:evidenceSegments(id)" in js
    # Main graph data remain the real overview values; the break is render-only.
    assert "const evidence=options.evidenceSegments||[],data=gapAwareData(timestamps,values,evidence)" in js


def test_gap_contract_is_used_by_main_command_and_comparison_charts():
    js = _text("static/graph_v14_1.js")
    assert "evidenceSegments:payload.evidence?.[id]||[]" in js
    assert "const [overviewA,overviewB,evidenceA,evidenceB]=await Promise.all" in js
    assert "evidence:evidenceA" in js and "evidence:evidenceB" in js
    assert "evidence:episodeA.evidence" in js and "evidence:episodeB.evidence" in js
    assert "function comparisonEvidenceSegments" in js
    assert "evidenceSegments:comparisonEvidenceSegments(source,id,{domain})" in js


def test_gap_breaks_only_when_non_available_interval_is_between_real_values():
    js = _text("static/graph_v14_1.js")
    assert "const hasBefore=valid.some(point=>point.x<from)" in js
    assert "hasAfter=valid.some(point=>point.x>to)" in js
    assert "if(!hasBefore||!hasAfter)continue" in js


def test_gap_interaction_never_substitutes_nearest_sample_inside_confirmed_gap():
    js = _text("static/graph_v14_1.js")
    assert "function evidenceGapAtSegments" in js
    assert "if(evidenceGapAtSegments(dataset?.gfEvidenceSegments||[],target))return null" in js
    assert "gfEvidenceSegments:evidence" in js
    assert "function commonEvidenceGapAt" in js
    assert "cursorGapHtml(ts" in js
    assert "const gap=commonEvidenceGapAt(selectedSeries(),state.cursorMs)" in js
    assert "renderInspectorGap(state.cursorMs,gap)" in js


def test_inspector_null_timestamp_does_not_turn_into_unix_epoch():
    js = _text("static/graph_v14_1.js")
    assert "actual=payload.actual_ms===null||payload.actual_ms===undefined?NaN:Number(payload.actual_ms)" in js
    assert "Number.isFinite(actual)?fmtTime(actual):'kein Punkt'" in js


def test_command_and_comparison_hover_are_gap_aware():
    js = _text("static/graph_v14_1.js")
    assert "nearestDatasetPoint(dataset,ts)" in js
    assert "const gaps=comparisonEvidenceSegments(source,id,{domain:'relative'})" in js
    assert "if(evidenceGapAtSegments(gaps,relMs))return null" in js
