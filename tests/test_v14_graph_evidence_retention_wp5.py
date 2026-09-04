import json
import sqlite3
from pathlib import Path

import pytest

from graph_core_v3 import connect_graph_core
from graph_core_v3_live import GraphCoreV3LiveSession
from graph_evidence import (
    EVIDENCE_AVAILABLE,
    EVIDENCE_GAP,
    EVIDENCE_NOT_INSTRUMENTED,
    EVIDENCE_PURGED,
    RetentionError,
    purge_highres,
    record_instrumentation,
)
from graph_query_service import GraphQueryService
from tools.rebuild_graph_core_v3 import rebuild


def _row(ts, seq=1, units=None):
    row = {
        "epoch_s": ts / 1000.0,
        "cycle_id": seq,
        "grid_power_w": 100.0,
        "raw_grid_power_w": 101.0,
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
        "command_publish_epoch_s": ts / 1000.0,
        "zendure_command_ac_mode": "input",
        "zendure_command_input_limit_w": 100.0,
        "zendure_command_output_limit_w": 0.0,
        "zendure_unit_count": len(units) if units is not None else 1,
    }
    if units is not None:
        row["zendure_units_json"] = json.dumps(units, separators=(",", ":"))
    return row


def _unit(device_id="UNIT-A"):
    return {
        "device_id": device_id,
        "actual_power_w": 60.0,
        "power_valid": 1,
        "soc_percent": 51.0,
        "soc_valid": 1,
        "target_w": 70.0,
        "target_valid": 1,
        "readback_target_w": 68.0,
        "readback_valid": 1,
    }


def _live_db(tmp_path, rows):
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        GraphCoreV3LiveSession(run_id=(1 << 62) + 505).write_batch(conn, str(db), rows)
    finally:
        conn.close()
    return db


def _write_v4(path: Path, rows, *, corrupt_after_first=False):
    keys = sorted({"schema_version", "cycle_index", "measurement_epoch_ms"} | {k for row in rows for k in row})
    normalized = []
    for i, row in enumerate(rows, 1):
        d = dict(row)
        d["schema_version"] = 4
        d["cycle_index"] = d.pop("cycle_id", i)
        d["measurement_epoch_ms"] = int(float(d.pop("epoch_s")) * 1000)
        normalized.append(d)
    with path.open("wb") as fh:
        fh.write((";".join(keys) + "\r\n").encode())
        for idx, row in enumerate(normalized):
            line = ";".join(str(row.get(k, "")) for k in keys) + "\r\n"
            fh.write(line.encode())
            if corrupt_after_first and idx == 0:
                fh.write(b"\x00BROKEN\r\n")
                break


def test_wp5_schema_contains_availability_instrumentation_and_retention_audit_columns(tmp_path):
    conn = connect_graph_core(tmp_path / "x.sqlite3")
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"graph_availability_segments", "graph_instrumentation_timeline"}.issubset(tables)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(graph_retention_ledger)")}
        assert {"operation_id", "stable_entity_id", "details_json"}.issubset(cols)
    finally:
        conn.close()


def test_live_writer_records_compact_available_evidence(tmp_path):
    start = 1_782_000_000_000
    db = _live_db(tmp_path, [_row(start), _row(start + 3000, 2)])
    payload = GraphQueryService(cache_max_entries=0).evidence(str(db), start, start + 3000,
                                                               series_ids=["grid_power_w"], resolution="highres")
    segment = payload["series"]["grid_power_w"][0]
    assert (segment["from_ms"], segment["to_ms"], segment["status"]) == (start, start + 3000, EVIDENCE_AVAILABLE)


def test_live_evidence_does_not_bridge_real_gap(tmp_path):
    start = (1_782_000_020_000 // 60_000) * 60_000
    db = _live_db(tmp_path, [_row(start + 1000), _row(start + 61_000, 2)])
    segments = GraphQueryService(cache_max_entries=0).evidence(
        str(db), start, start + 61_000, series_ids=["grid_power_w"], resolution="highres"
    )["series"]["grid_power_w"]
    available = [x for x in segments if x["status"] == EVIDENCE_AVAILABLE]
    assert len(available) == 2
    assert available[0]["from_ms"] == available[0]["to_ms"] == start + 1000
    assert available[1]["from_ms"] == available[1]["to_ms"] == start + 61_000
    assert any(x["status"] == EVIDENCE_GAP for x in segments)


def test_one_minute_evidence_represents_full_bucket(tmp_path):
    start = 1_782_000_040_000
    db = _live_db(tmp_path, [_row(start)])
    bucket = (start // 60000) * 60000
    row = GraphQueryService(cache_max_entries=0).evidence(
        str(db), bucket, bucket + 59_999, series_ids=["grid_power_w"], resolution="1min"
    )["series"]["grid_power_w"][0]
    assert (row["from_ms"], row["to_ms"], row["status"]) == (bucket, bucket + 59_999, EVIDENCE_AVAILABLE)


def test_evidence_distinguishes_not_instrumented_and_gap(tmp_path):
    db = tmp_path / "e.sqlite3"; conn = connect_graph_core(db); start = 1_782_000_100_000
    try:
        record_instrumentation(conn, series_id="grid_power_w", effective_from_ms=start + 1000, source="TEST")
        conn.execute("INSERT INTO graph_availability_segments(series_id,resolution,from_ms,to_ms,status,source,quality) VALUES(?,?,?,?,?,?,?)",
                     ("grid_power_w", "highres", start + 2000, start + 3000, EVIDENCE_AVAILABLE, "TEST", "OBSERVED"))
        conn.commit()
    finally: conn.close()
    segments = GraphQueryService(cache_max_entries=0).evidence(str(db), start, start + 5000,
                                                               series_ids=["grid_power_w"])["series"]["grid_power_w"]
    assert segments[0]["status"] == EVIDENCE_NOT_INSTRUMENTED
    assert any(x["status"] == EVIDENCE_AVAILABLE for x in segments)
    assert segments[-1]["status"] == EVIDENCE_GAP


def test_retention_fails_closed_when_longterm_series_bucket_missing(tmp_path):
    start = 1_782_000_200_000; db = _live_db(tmp_path, [_row(start), _row(start + 3000, 2)]); conn = connect_graph_core(db)
    try:
        conn.execute("DELETE FROM measurement_1min"); conn.commit()
        with pytest.raises(RetentionError, match="RETENTION_LONGTERM_COVERAGE_INCOMPLETE"):
            purge_highres(conn, from_ms=start, to_ms=start + 3000, operation_id="op-a", reason="TEST")
        assert conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM graph_retention_ledger").fetchone()[0] == 0
    finally: conn.close()


def test_retention_delete_and_ledger_are_atomic_and_keep_1min(tmp_path):
    start = (1_782_000_300_000 // 60000) * 60000
    db = _live_db(tmp_path, [_row(start + 1000), _row(start + 4000, 2), _row(start + 61_000, 3)]); conn = connect_graph_core(db)
    try:
        before = conn.execute("SELECT COUNT(*) FROM measurement_1min").fetchone()[0]
        result = purge_highres(conn, from_ms=start, to_ms=start + 59_999, operation_id="op-b", reason="TEST_PURGE")
        assert result["system_rows_deleted"] == 2
        assert conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM measurement_1min").fetchone()[0] == before
        assert tuple(conn.execute("SELECT action,data_class,operation_id FROM graph_retention_ledger").fetchone()) == ("PURGE", "SYSTEM_HIGHRES", "op-b")
    finally: conn.close()


def test_retention_operation_is_idempotent(tmp_path):
    start=1_782_000_400_000; db=_live_db(tmp_path,[_row(start)]); conn=connect_graph_core(db)
    try:
        first=purge_highres(conn,from_ms=start,to_ms=start,operation_id="same",reason="TEST")
        second=purge_highres(conn,from_ms=start,to_ms=start,operation_id="same",reason="TEST")
        assert first["status"] == "ok" and second["status"] == "already_applied"
        assert conn.execute("SELECT COUNT(*) FROM graph_retention_ledger WHERE operation_id='same'").fetchone()[0] == 1
    finally: conn.close()


def test_retention_operation_id_conflict_fails_closed(tmp_path):
    start=1_782_000_500_000; db=_live_db(tmp_path,[_row(start),_row(start+60_000,2)]); conn=connect_graph_core(db)
    try:
        purge_highres(conn,from_ms=start,to_ms=start,operation_id="conflict",reason="TEST")
        with pytest.raises(RetentionError,match="RETENTION_OPERATION_ID_CONFLICT"):
            purge_highres(conn,from_ms=start+60_000,to_ms=start+60_000,operation_id="conflict",reason="TEST")
    finally: conn.close()


def test_evidence_marks_purged_range_not_gap(tmp_path):
    start=1_782_000_600_000; db=_live_db(tmp_path,[_row(start),_row(start+3000,2)]); conn=connect_graph_core(db)
    try: purge_highres(conn,from_ms=start,to_ms=start+3000,operation_id="purged",reason="TEST")
    finally: conn.close()
    segments=GraphQueryService(cache_max_entries=0).evidence(str(db),start,start+3000,series_ids=["grid_power_w"])["series"]["grid_power_w"]
    assert len(segments)==1 and segments[0]["status"]==EVIDENCE_PURGED


def test_rebuild_reapplies_system_retention_from_previous_v3(tmp_path):
    start=1_782_000_700_000; old=_live_db(tmp_path,[_row(start),_row(start+3000,2)]); conn=connect_graph_core(old)
    try: purge_highres(conn,from_ms=start,to_ms=start+3000,operation_id="r1",reason="TEST")
    finally: conn.close()
    src=tmp_path/"v4.csv"; _write_v4(src,[_row(start),_row(start+3000,2)]); new=tmp_path/"new.sqlite3"
    result=rebuild([src],new,legacy_db=old,reset=True,progress_every=0)
    assert result["retention_rows_copied"]==1
    conn=sqlite3.connect(new)
    try:
        assert conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0]==0
        assert conn.execute("SELECT COUNT(*) FROM measurement_1min").fetchone()[0]==1
    finally: conn.close()


def test_rebuild_reapplies_physical_entity_retention_by_stable_identity(tmp_path):
    start=1_782_000_800_000; rows=[_row(start,units=[_unit()]),_row(start+3000,2,units=[_unit()])]
    old=_live_db(tmp_path,rows); conn=connect_graph_core(old)
    try:
        entity_id=conn.execute("SELECT entity_id FROM graph_entities WHERE source_identity='UNIT-A'").fetchone()[0]
        purge_highres(conn,from_ms=start,to_ms=start+3000,operation_id="er1",reason="TEST",entity_ids=[entity_id])
    finally: conn.close()
    src=tmp_path/"entity_v4.csv"; _write_v4(src,rows); new=tmp_path/"entity_new.sqlite3"
    result=rebuild([src],new,legacy_db=old,reset=True,progress_every=0)
    assert result["retention_rows_copied"]>=2
    conn=sqlite3.connect(new)
    try:
        eid=conn.execute("SELECT entity_id FROM graph_entities WHERE source_identity='UNIT-A'").fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM measurement_entity_raw WHERE entity_id=?",(eid,)).fetchone()[0]==0
        assert conn.execute("SELECT COUNT(*) FROM measurement_entity_1min WHERE entity_id=?",(eid,)).fetchone()[0]==1
    finally: conn.close()


def test_structurally_bad_v4_file_does_not_leave_partial_current_file(tmp_path):
    start=1_782_000_900_000; src=tmp_path/"bad.csv"; _write_v4(src,[_row(start)],corrupt_after_first=True); db=tmp_path/"bad.sqlite3"
    with pytest.raises(Exception): rebuild([src],db,reset=True,batch_size=1,progress_every=0)
    conn=sqlite3.connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0]==0
        assert conn.execute("SELECT COUNT(*) FROM graph_command_events").fetchone()[0]==0
    finally: conn.close()


def test_coverage_keeps_legacy_segments_and_adds_wp5_evidence(tmp_path):
    start=1_782_001_000_000; db=_live_db(tmp_path,[_row(start)]); conn=sqlite3.connect(db)
    try:
        conn.execute("INSERT INTO graph_series_coverage(series_id,from_ms,to_ms,source,quality) VALUES(?,?,?,?,?)",
                     ("grid_power_w",start-1000,start+1000,"MEASUREMENT_V4","OBSERVED_NON_NULL_SPAN")); conn.commit()
    finally: conn.close()
    item=GraphQueryService(cache_max_entries=0).coverage(str(db),series_ids=["grid_power_w"])["series"]["grid_power_w"]
    assert item["from_ms"]==start-1000 and item["segments"][0]["source"]=="MEASUREMENT_V4" and item["evidence_segments"]


def test_wp5_web_evidence_route_present():
    from web_ui import create_app
    from config_manager import ConfigManager, DEFAULT_CONFIG
    from state import ControllerState
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"config.json"; path.write_text(json.dumps(DEFAULT_CONFIG),encoding="utf-8")
        manager=ConfigManager(str(path)); manager.load(); app=create_app(manager,ControllerState())
        assert "/api/graph/v1/evidence" in {getattr(r,"path","") for r in app.routes}


def test_coverage_uses_wp5_availability_without_measurement_raw_scan(tmp_path):
    start=1_782_001_100_000; db=_live_db(tmp_path,[_row(start),_row(start+3000,2)])
    conn=sqlite3.connect(db); conn.row_factory=sqlite3.Row; statements=[]; conn.set_trace_callback(statements.append)
    try:
        from graph_query_service import query_series_coverage
        payload=query_series_coverage(conn,["grid_power_w","target_final_w"])
    finally: conn.close()
    assert payload["grid_power_w"]["available"] and payload["target_final_w"]["available"]
    assert [x for x in statements if "measurement_raw" in x.lower() and "select" in x.lower()] == []


def test_coverage_excludes_highres_range_marked_purged_by_retention(tmp_path):
    start=(1_782_001_200_000//60_000)*60_000
    db=_live_db(tmp_path,[_row(start+1000),_row(start+61_000,2)]); conn=connect_graph_core(db)
    try: purge_highres(conn,from_ms=start,to_ms=start+59_999,operation_id="coverage-purge",reason="TEST")
    finally: conn.close()
    item=GraphQueryService(cache_max_entries=0).coverage(str(db),series_ids=["grid_power_w"])["series"]["grid_power_w"]
    assert item["available"] is True
    assert item["from_ms"] == start + 61_000
    assert all(int(seg["from_ms"]) > start + 59_999 for seg in item["segments"])
    assert any(seg["status"] == EVIDENCE_PURGED for seg in item["evidence_segments"])
