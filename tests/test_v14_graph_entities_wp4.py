import json
import os
import sqlite3
from pathlib import Path

import pytest

from config_manager import ConfigManager, DEFAULT_CONFIG
from graph_core_v3 import (
    ENTITY_STABLE_CONTROLLED_STORAGE,
    ENTITY_STABLE_PRIMARY_STORAGE,
    EntityPersistenceBuilder,
    connect_graph_core,
    ensure_graph_entity,
)
from graph_core_v3_live import GraphCoreV3LiveSession
from graph_query_service import GraphQueryError, GraphQueryService, canonical_entity_series_catalog
from measurement_db import MeasurementDbWriter, ensure_schema
from state import ControllerState
from tools.rebuild_graph_core_v3 import rebuild
from web_ui import create_app


def _row(ts_ms: int, *, seq: int = 1, unit_count: int = 1, units=None, primary=True):
    row = {
        "epoch_s": ts_ms / 1000.0,
        "cycle_id": seq,
        "measurement_monotonic_ns": 10_000_000_000 + seq * 3_000_000_000,
        "grid_power_w": 100.0,
        "raw_grid_power_w": 101.0,
        "grid_power_valid": True,
        "zendure_actual_power_w": 95.0,
        "actual_zendure_power_valid": True,
        "zendure_soc_percent": 55.0,
        "soc_valid": True,
        "second_battery_power_w": 200.0 if primary else None,
        "second_battery_soc_percent": 70.0 if primary else None,
        "second_battery_data_valid": primary,
        "second_battery_valid": primary,
        "target_raw_w": 140.0,
        "target_after_power_limit_w": 130.0,
        "target_after_smoothing_w": 120.0,
        "target_after_ramp_w": 110.0,
        "target_final_w": 100.0,
        "target_final_reason": "AUTO_GRID_EXPORT",
        "operating_mode": "AUTO",
        "control_intent": "CHARGE",
        "command_lifecycle_state": "TRACKING",
        "command_effect_category": "COMMAND_TARGET_TRACKING_EFFECTIVE",
        "command_desired_sequence_id": seq,
        "command_desired_intent": "CHARGE",
        "command_desired_smart_mode": 1,
        "command_desired_ac_mode": "input",
        "command_desired_input_limit_w": 100.0,
        "command_desired_output_limit_w": 0.0,
        "command_desired_signed_target_w": 100.0,
        "command_publish_event_id": seq,
        "command_publish_epoch_s": ts_ms / 1000.0,
        "command_publish_monotonic_ns": 9_500_000_000 + seq * 3_000_000_000,
        "zendure_command_smart_mode": 1,
        "zendure_command_ac_mode": "input",
        "zendure_command_input_limit_w": 100.0,
        "zendure_command_output_limit_w": 0.0,
        "command_readback_matches_desired": 1,
        "command_readback_mismatch_fields": "",
        "command_resync_count": 0,
        "command_neutralization_episode_id": 0,
        "zendure_unit_count": unit_count,
        "_graph_entity_config": {
            "zendure_device_id": "ZE-AGGREGATE-1",
            "primary_display_name": "Hausspeicher",
            "primary_source_profile": "evcc_standard",
            "primary_integration_enabled": primary,
        },
    }
    if units is not None:
        row["zendure_units_json"] = json.dumps(units, separators=(",", ":"))
    else:
        row["zendure_units_json"] = json.dumps([{
            "unit_id": "primary",  # Current aggregate/logical placeholder, not a physical identity.
            "target_w": 100.0,
            "actual_power_w": 95.0,
            "soc_percent": 55.0,
        }])
    return row


def _v3(tmp_path: Path, rows):
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        GraphCoreV3LiveSession(run_id=(1 << 62) + 404).write_batch(conn, str(db), rows)
    finally:
        conn.close()
    return db


def _physical_units(ts_ms: int, *, include_b=True):
    units = [
        {
            "device_id": "UNIT-A-001",
            "display_name": "Zendure A",
            "actual_power_w": 60.0,
            "power_valid": 1,
            "soc_percent": 51.0,
            "soc_valid": 1,
            "target_w": 70.0,
            "target_valid": 1,
            "readback_target_w": 68.0,
            "readback_valid": 1,
        }
    ]
    if include_b:
        units.append({
            "device_id": "UNIT-B-002",
            "display_name": "Zendure B",
            "actual_power_w": 35.0,
            "power_valid": 1,
            "soc_percent": 58.0,
            "soc_valid": 1,
            "target_w": 30.0,
            "target_valid": 1,
            "readback_target_w": 29.0,
            "readback_valid": 1,
        })
    return units


def test_entity_series_catalog_has_stable_presentation_contract():
    catalog = {item["series_id"]: item for item in canonical_entity_series_catalog()}
    assert set(catalog) == {"power_w", "soc_percent", "target_w", "readback_target_w"}
    assert catalog["power_w"]["label_key"] == "graph.entity_series.power_w"
    assert catalog["power_w"]["temporal_type"] == "continuous"
    assert catalog["soc_percent"]["temporal_type"] == "continuous"
    assert catalog["target_w"]["temporal_type"] == "target"
    assert catalog["power_w"]["storage_scale"] == 10


def test_logical_storage_roles_do_not_duplicate_dense_entity_rows(tmp_path):
    start = 1_781_000_000_000
    db = _v3(tmp_path, [_row(start), _row(start + 3000, seq=2)])
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        entities = {r["stable_id"]: r for r in conn.execute("SELECT * FROM graph_entities")}
        assert ENTITY_STABLE_CONTROLLED_STORAGE in entities
        assert ENTITY_STABLE_PRIMARY_STORAGE in entities
        assert entities[ENTITY_STABLE_CONTROLLED_STORAGE]["storage_binding"] == "SYSTEM_ZENDURE"
        assert entities[ENTITY_STABLE_PRIMARY_STORAGE]["storage_binding"] == "SYSTEM_PRIMARY"
        assert entities[ENTITY_STABLE_PRIMARY_STORAGE]["display_name"] == "Hausspeicher"
        assert conn.execute("SELECT COUNT(*) FROM measurement_entity_raw").fetchone()[0] == 0
    finally:
        conn.close()


def test_current_primary_placeholder_is_not_promoted_to_physical_entity(tmp_path):
    db = _v3(tmp_path, [_row(1_781_000_100_000)])
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM graph_entities WHERE entity_type='ZENDURE_UNIT'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM measurement_entity_raw").fetchone()[0] == 0
    finally:
        conn.close()


def test_authoritative_two_unit_list_persists_separate_physical_rows_and_minute_aggregates(tmp_path):
    start = 1_781_000_200_000
    rows = [
        _row(start, unit_count=2, units=_physical_units(start)),
        _row(start + 3000, seq=2, unit_count=2, units=_physical_units(start + 3000)),
    ]
    db = _v3(tmp_path, rows)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        physical = conn.execute("SELECT * FROM graph_entities WHERE entity_type='ZENDURE_UNIT' ORDER BY source_identity").fetchall()
        assert [r["source_identity"] for r in physical] == ["UNIT-A-001", "UNIT-B-002"]
        assert all(str(r["stable_id"]).startswith("zendure-unit:") for r in physical)
        assert conn.execute("SELECT COUNT(*) FROM measurement_entity_raw").fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM measurement_entity_1min").fetchone()[0] == 2
        a = physical[0]
        minute = conn.execute("SELECT * FROM measurement_entity_1min WHERE entity_id=?", (a["entity_id"],)).fetchone()
        assert minute["power_dw_count"] == 2
        assert minute["power_dw_sum"] == 1200
        assert minute["soc_tenths_percent_count"] == 2
        assert minute["target_dw_count"] == 2
        assert minute["readback_target_dw_count"] == 2
    finally:
        conn.close()


def test_authoritative_disappearance_is_absent_not_fake_zero(tmp_path):
    start = 1_781_000_300_000
    first = _row(start, unit_count=2, units=_physical_units(start))
    second = _row(start + 3000, seq=2, unit_count=1, units=_physical_units(start + 3000, include_b=False))
    db = _v3(tmp_path, [first, second])
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        b = conn.execute("SELECT entity_id FROM graph_entities WHERE source_identity='UNIT-B-002'").fetchone()
        topo = conn.execute(
            "SELECT state,effective_from_ms FROM graph_topology_timeline WHERE entity_id=? AND role='CONTROLLED_STORAGE_MEMBER' ORDER BY effective_from_ms",
            (b["entity_id"],),
        ).fetchall()
        assert [(r["state"], r["effective_from_ms"]) for r in topo] == [("PRESENT", start), ("ABSENT", start + 3000)]
        values = conn.execute("SELECT power_dw FROM measurement_entity_raw WHERE entity_id=? ORDER BY ts_ms", (b["entity_id"],)).fetchall()
        assert [r[0] for r in values] == [350]
    finally:
        conn.close()


def test_non_authoritative_unit_list_does_not_infer_absence(tmp_path):
    start = 1_781_000_400_000
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        session = GraphCoreV3LiveSession(run_id=(1 << 62) + 405)
        session.write_batch(conn, str(db), [_row(start, unit_count=2, units=_physical_units(start))])
        # unit_count says two but only one identifiable unit is present -> partial/non-authoritative observation.
        partial = _row(start + 3000, seq=2, unit_count=2, units=_physical_units(start + 3000, include_b=False))
        session.write_batch(conn, str(db), [partial])
    finally:
        conn.close()
    conn = sqlite3.connect(db)
    try:
        b_id = conn.execute("SELECT entity_id FROM graph_entities WHERE source_identity='UNIT-B-002'").fetchone()[0]
        states = [r[0] for r in conn.execute(
            "SELECT state FROM graph_topology_timeline WHERE entity_id=? AND role='CONTROLLED_STORAGE_MEMBER' ORDER BY effective_from_ms", (b_id,)
        )]
        assert states == ["PRESENT"]
    finally:
        conn.close()


def test_identity_conflict_fails_closed(tmp_path):
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        entity_id = ensure_graph_entity(
            conn, stable_id="stable:x", entity_type="ZENDURE_UNIT", ts_ms=1000,
            identity_kind="DEVICE_ID", source_identity="X", storage_binding="ENTITY_TABLE",
        )
        assert entity_id > 0
        with pytest.raises(RuntimeError, match="ENTITY_IDENTITY_CONFLICT"):
            ensure_graph_entity(
                conn, stable_id="stable:x", entity_type="PRIMARY_STORAGE", ts_ms=2000,
                identity_kind="DEVICE_ID", source_identity="X", storage_binding="ENTITY_TABLE",
            )
    finally:
        conn.close()


def test_entity_aware_sparse_and_command_records_reference_logical_storage(tmp_path):
    start = 1_781_000_500_000
    db = _v3(tmp_path, [_row(start)])
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        controlled = conn.execute("SELECT entity_id FROM graph_entities WHERE stable_id=?", (ENTITY_STABLE_CONTROLLED_STORAGE,)).fetchone()[0]
        primary = conn.execute("SELECT entity_id FROM graph_entities WHERE stable_id=?", (ENTITY_STABLE_PRIMARY_STORAGE,)).fetchone()[0]
        pub = conn.execute("SELECT entity_id FROM graph_command_events WHERE event_type='PUBLISHED' LIMIT 1").fetchone()
        assert pub is not None and pub[0] == controlled
        assert conn.execute("SELECT COUNT(*) FROM graph_intervals WHERE entity_id=?", (controlled,)).fetchone()[0] > 0
        assert conn.execute("SELECT COUNT(*) FROM graph_intervals WHERE entity_id=?", (primary,)).fetchone()[0] > 0
    finally:
        conn.close()


def test_query_service_projects_logical_entities_and_marks_primary_commands_not_applicable(tmp_path):
    start = 1_781_000_600_000
    db = _v3(tmp_path, [_row(start), _row(start + 3000, seq=2)])
    service = GraphQueryService(cache_max_entries=0)
    catalog = service.entities(str(db))
    by_id = {x["stable_id"]: x for x in catalog["entities"]}
    assert by_id[ENTITY_STABLE_PRIMARY_STORAGE]["display_name"] == "Hausspeicher"
    assert by_id[ENTITY_STABLE_CONTROLLED_STORAGE]["available_series"] == ["power_w", "soc_percent", "target_w", "readback_target_w"]
    primary = service.entity_overview(
        str(db), start, start + 10_000,
        stable_ids=[ENTITY_STABLE_PRIMARY_STORAGE],
        series_ids=["power_w", "soc_percent", "target_w", "readback_target_w"],
    )["entities"][ENTITY_STABLE_PRIMARY_STORAGE]
    assert primary["series"]["power_w"] == [200.0, 200.0]
    assert primary["series"]["soc_percent"] == [70.0, 70.0]
    assert primary["not_applicable_series"] == ["target_w", "readback_target_w"]
    assert "target_w" not in primary["series"]


def test_query_service_reads_physical_entity_and_entity_coverage(tmp_path):
    start = 1_781_000_700_000
    db = _v3(tmp_path, [_row(start, unit_count=2, units=_physical_units(start))])
    service = GraphQueryService(cache_max_entries=0)
    entities = service.entities(str(db))["entities"]
    unit_a = next(x for x in entities if x.get("source_identity") == "UNIT-A-001")
    payload = service.entity_overview(
        str(db), start - 1, start + 10_000,
        stable_ids=[unit_a["stable_id"]], series_ids=["power_w", "soc_percent", "target_w", "readback_target_w"],
    )["entities"][unit_a["stable_id"]]
    assert payload["series"]["power_w"] == [60.0]
    assert payload["series"]["soc_percent"] == [51.0]
    assert payload["series"]["target_w"] == [70.0]
    assert payload["series"]["readback_target_w"] == [68.0]
    assert payload["topology_timeline"][-1]["state"] == "PRESENT"
    assert payload["topology_timeline"][-1]["role"] == "CONTROLLED_STORAGE_MEMBER"
    coverage = service.entity_coverage(str(db), stable_ids=[unit_a["stable_id"]])["entities"][unit_a["stable_id"]]["series"]
    assert coverage["power_w"]["available"] is True
    assert coverage["power_w"]["from_ms"] == start


def test_entity_overview_rejects_more_than_48_hours(tmp_path):
    start = 1_781_000_800_000
    db = _v3(tmp_path, [_row(start)])
    with pytest.raises(GraphQueryError, match="WINDOW_EXCEEDS_48H"):
        GraphQueryService(cache_max_entries=0).entity_overview(str(db), start, start + 49 * 60 * 60_000)


def test_entity_query_rejects_v2_without_mutation(tmp_path):
    db = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(db)
    ensure_schema(conn)
    conn.close()
    before = db.read_bytes()
    with pytest.raises(GraphQueryError, match="GRAPH_DB_NOT_V3"):
        GraphQueryService(cache_max_entries=0).entities(str(db))
    assert db.read_bytes() == before


def test_primary_not_applicable_when_integration_explicitly_disabled(tmp_path):
    start = 1_781_000_900_000
    row = _row(start, primary=False)
    row["_graph_entity_config"]["primary_source_profile"] = "evcc_standard"
    db = _v3(tmp_path, [row])
    conn = sqlite3.connect(db)
    try:
        primary_id = conn.execute("SELECT entity_id FROM graph_entities WHERE stable_id=?", (ENTITY_STABLE_PRIMARY_STORAGE,)).fetchone()[0]
        state = conn.execute(
            "SELECT state FROM graph_topology_timeline WHERE entity_id=? AND role='PRIMARY_STORAGE' ORDER BY effective_from_ms DESC LIMIT 1",
            (primary_id,),
        ).fetchone()[0]
        assert state == "NOT_APPLICABLE"
    finally:
        conn.close()


def test_topology_window_distinguishes_roles_for_same_entity(tmp_path):
    start = 1_781_001_000_000
    db = _v3(tmp_path, [_row(start)])
    conn = sqlite3.connect(db)
    try:
        entity_id = conn.execute("SELECT entity_id FROM graph_entities WHERE stable_id=?", (ENTITY_STABLE_CONTROLLED_STORAGE,)).fetchone()[0]
        conn.executemany(
            "INSERT INTO graph_topology_timeline(effective_from_ms,entity_id,entity_type,role,state,source,confidence) VALUES(?,?,?,?,?,?,?)",
            [
                (start - 30_000, entity_id, "ZENDURE_STORAGE", "ROLE_A", "PRESENT", "TEST", "OBSERVED"),
                (start - 20_000, entity_id, "ZENDURE_STORAGE", "ROLE_B", "NOT_APPLICABLE", "TEST", "OBSERVED"),
                (start - 10_000, entity_id, "ZENDURE_STORAGE", "ROLE_A", "ABSENT", "TEST", "OBSERVED"),
            ],
        )
        conn.commit()
    finally:
        conn.close()
    payload = GraphQueryService(cache_max_entries=0).overview(str(db), start, start + 1000, series_ids=["grid_power_w"])
    rows = [x for x in payload["topology_timeline"] if x.get("entity_id") == entity_id and x.get("role") in {"ROLE_A", "ROLE_B"}]
    assert {(r["role"], r["state"]) for r in rows} == {("ROLE_A", "ABSENT"), ("ROLE_B", "NOT_APPLICABLE")}


def test_web_api_routes_for_entity_queries_are_present(tmp_path):
    db = _v3(tmp_path, [_row(1_781_001_100_000)])
    cfg_path = tmp_path / "config.json"
    cfg = dict(DEFAULT_CONFIG)
    cfg["MEASUREMENT_DB_ENABLED"] = True
    cfg["MEASUREMENT_DB_PATH"] = str(db)
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    manager = ConfigManager(str(cfg_path))
    manager.load()
    app = create_app(manager, ControllerState())
    routes = {(getattr(route, "path", None), tuple(sorted(getattr(route, "methods", set())))) for route in app.routes}
    paths = {path for path, methods in routes if "GET" in methods}
    assert "/api/graph/v1/entities" in paths
    assert "/api/graph/v1/entity-overview" in paths
    assert "/api/graph/v1/entity-coverage" in paths


def test_offline_v4_rebuild_creates_logical_roles_but_no_invented_physical_units(tmp_path):
    source = tmp_path / "v4.csv"
    header = [
        "schema_version", "cycle_index", "measurement_epoch_ms", "config_control_hash", "operating_mode", "control_intent",
        "grid_power_w", "grid_power_raw_w", "grid_power_valid", "zendure_actual_power_w", "zendure_actual_power_valid",
        "zendure_soc_percent", "zendure_soc_valid", "second_battery_power_w", "second_battery_power_valid",
        "second_battery_soc_percent", "second_battery_soc_valid", "target_raw_w", "target_limited_w", "target_filtered_w",
        "target_step_limited_w", "target_final_w", "target_final_reason", "command_lifecycle_state", "command_desired_sequence_id",
        "command_desired_smart_mode", "command_desired_ac_mode", "command_desired_input_limit_w", "command_desired_output_limit_w",
        "command_desired_signed_target_w", "command_publish_event_id", "command_publish_epoch_s", "command_readback_matches_desired",
        "zendure_command_smart_mode", "zendure_command_ac_mode", "zendure_command_input_limit_w", "zendure_command_output_limit_w",
        "command_effect_category", "command_resync_count", "command_neutralization_episode_id", "zendure_unit_count",
    ]
    row = {
        "schema_version": 4, "cycle_index": 1, "measurement_epoch_ms": 1_781_001_200_000,
        "config_control_hash": "h", "operating_mode": "AUTO", "control_intent": "CHARGE",
        "grid_power_w": 100, "grid_power_raw_w": 101, "grid_power_valid": 1,
        "zendure_actual_power_w": 90, "zendure_actual_power_valid": 1, "zendure_soc_percent": 50, "zendure_soc_valid": 1,
        "second_battery_power_w": 200, "second_battery_power_valid": 1, "second_battery_soc_percent": 70, "second_battery_soc_valid": 1,
        "target_raw_w": 120, "target_limited_w": 115, "target_filtered_w": 110, "target_step_limited_w": 105,
        "target_final_w": 100, "target_final_reason": "AUTO_GRID_EXPORT", "command_lifecycle_state": "TRACKING",
        "command_desired_sequence_id": 1, "command_desired_smart_mode": 1, "command_desired_ac_mode": "input",
        "command_desired_input_limit_w": 100, "command_desired_output_limit_w": 0, "command_desired_signed_target_w": 100,
        "command_publish_event_id": 1, "command_publish_epoch_s": 1_781_001_200,
        "command_readback_matches_desired": 1, "zendure_command_smart_mode": 1, "zendure_command_ac_mode": "input",
        "zendure_command_input_limit_w": 100, "zendure_command_output_limit_w": 0,
        "command_effect_category": "COMMAND_TARGET_TRACKING_EFFECTIVE", "command_resync_count": 0,
        "command_neutralization_episode_id": 0, "zendure_unit_count": 1,
    }
    with source.open("w", encoding="utf-8", newline="") as fh:
        fh.write(";".join(header) + "\r\n")
        fh.write(";".join(str(row.get(k, "")) for k in header) + "\r\n")
    db = tmp_path / "rebuilt.sqlite3"
    rebuild(
        [source], db, reset=True, progress_every=0,
        entity_config={"DEVICE_ID": "ZE-CONTROL", "SECOND_BATTERY_DISPLAY_NAME": "Primärspeicher"},
    )
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM graph_entities WHERE stable_id IN (?,?)", (ENTITY_STABLE_CONTROLLED_STORAGE, ENTITY_STABLE_PRIMARY_STORAGE)).fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM graph_entities WHERE entity_type='ZENDURE_UNIT'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM measurement_entity_raw").fetchone()[0] == 0
        assert conn.execute("SELECT display_name FROM graph_entities WHERE stable_id=?", (ENTITY_STABLE_PRIMARY_STORAGE,)).fetchone()[0] == "Primärspeicher"
    finally:
        conn.close()


def _writer_config(db: Path):
    return {
        "MEASUREMENT_DB_ENABLED": True,
        "MEASUREMENT_DB_PATH": str(db),
        "MEASUREMENT_LOG_DIR": str(db.parent),
        "MEASUREMENT_LOG_FALLBACK_DIR": str(db.parent / "fallback"),
        "DEVICE_ID": "ZE-WRITER-1",
        "SECOND_BATTERY_DISPLAY_NAME": "Mein Primärspeicher",
        "SECOND_BATTERY_SOURCE_PROFILE": "evcc_standard",
        "SECOND_BATTERY_INTEGRATION_ENABLED": True,
    }


def test_measurement_db_writer_carries_entity_config_without_changing_v4_contract(tmp_path):
    import time
    db = tmp_path / "writer.sqlite3"
    writer = MeasurementDbWriter()
    try:
        writer.enqueue(_writer_config(db), _row(1_781_001_300_000))
        deadline = time.time() + 5
        while time.time() < deadline and int(writer.status().get("measurement_db_rows_written") or 0) < 1:
            time.sleep(0.02)
        assert int(writer.status().get("measurement_db_rows_written") or 0) == 1
    finally:
        writer.close()
    conn = sqlite3.connect(db)
    try:
        controlled = conn.execute("SELECT metadata_json FROM graph_entities WHERE stable_id=?", (ENTITY_STABLE_CONTROLLED_STORAGE,)).fetchone()[0]
        primary = conn.execute("SELECT display_name FROM graph_entities WHERE stable_id=?", (ENTITY_STABLE_PRIMARY_STORAGE,)).fetchone()[0]
        assert json.loads(controlled)["configured_device_id"] == "ZE-WRITER-1"
        assert primary == "Mein Primärspeicher"
    finally:
        conn.close()


def test_live_quality_aliases_are_preserved_in_raw_mask_and_sparse_entity_intervals(tmp_path):
    start = 1_781_001_400_000
    db = _v3(tmp_path, [_row(start)])
    conn = sqlite3.connect(db)
    try:
        flags = conn.execute("SELECT quality_flags FROM measurement_raw").fetchone()[0]
        # grid + Zendure power + Zendure SOC + primary power + primary SOC are all valid in the live naming surface.
        assert flags & 0b1
        assert flags & 0b10
        assert flags & 0b100
        assert flags & 0b1000
        assert flags & 0b10000
        primary_id = conn.execute("SELECT entity_id FROM graph_entities WHERE stable_id=?", (ENTITY_STABLE_PRIMARY_STORAGE,)).fetchone()[0]
        kinds = {r[0] for r in conn.execute("SELECT kind FROM graph_intervals WHERE entity_id=?", (primary_id,))}
        assert {"PRIMARY_POWER_DATA", "PRIMARY_SOC_DATA"}.issubset(kinds)
    finally:
        conn.close()


def test_explicit_authoritative_empty_unit_list_marks_previous_units_absent(tmp_path):
    start = 1_781_001_500_000
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        session = GraphCoreV3LiveSession(run_id=(1 << 62) + 406)
        session.write_batch(conn, str(db), [_row(start, unit_count=2, units=_physical_units(start))])
        session.write_batch(conn, str(db), [_row(start + 3000, seq=2, unit_count=0, units=[])])
    finally:
        conn.close()
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT e.source_identity,t.state FROM graph_entities e JOIN graph_topology_timeline t ON t.entity_id=e.entity_id "
            "WHERE e.entity_type='ZENDURE_UNIT' AND t.role='CONTROLLED_STORAGE_MEMBER' ORDER BY e.source_identity,t.effective_from_ms"
        ).fetchall()
        assert rows == [
            ("UNIT-A-001", "PRESENT"), ("UNIT-A-001", "ABSENT"),
            ("UNIT-B-002", "PRESENT"), ("UNIT-B-002", "ABSENT"),
        ]
    finally:
        conn.close()


def test_duplicate_physical_identity_list_is_not_authoritative_for_absence(tmp_path):
    start = 1_781_001_600_000
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        session = GraphCoreV3LiveSession(run_id=(1 << 62) + 407)
        session.write_batch(conn, str(db), [_row(start, unit_count=2, units=_physical_units(start))])
        duplicate = [_physical_units(start + 3000)[0], dict(_physical_units(start + 3000)[0])]
        session.write_batch(conn, str(db), [_row(start + 3000, seq=2, unit_count=2, units=duplicate)])
    finally:
        conn.close()
    conn = sqlite3.connect(db)
    try:
        b_id = conn.execute("SELECT entity_id FROM graph_entities WHERE source_identity='UNIT-B-002'").fetchone()[0]
        states = [r[0] for r in conn.execute(
            "SELECT state FROM graph_topology_timeline WHERE entity_id=? AND role='CONTROLLED_STORAGE_MEMBER' ORDER BY effective_from_ms", (b_id,)
        )]
        assert states == ["PRESENT"]
    finally:
        conn.close()


def test_controlled_storage_topology_records_unit_count_change_without_noncanonical_state(tmp_path):
    start = 1_781_001_700_000
    db = tmp_path / "graph.sqlite3"
    conn = connect_graph_core(db)
    try:
        session = GraphCoreV3LiveSession(run_id=(1 << 62) + 408)
        session.write_batch(conn, str(db), [_row(start, unit_count=1)])
        session.write_batch(conn, str(db), [_row(start + 3000, seq=2, unit_count=2, units=_physical_units(start + 3000))])
    finally:
        conn.close()
    conn = sqlite3.connect(db)
    try:
        entity_id = conn.execute("SELECT entity_id FROM graph_entities WHERE stable_id=?", (ENTITY_STABLE_CONTROLLED_STORAGE,)).fetchone()[0]
        rows = conn.execute(
            "SELECT state,unit_count FROM graph_topology_timeline WHERE entity_id=? AND role='CONTROLLED_STORAGE' ORDER BY effective_from_ms",
            (entity_id,),
        ).fetchall()
        assert rows == [("PRESENT", 1), ("PRESENT", 2)]
        assert conn.execute("SELECT COUNT(*) FROM graph_topology_timeline WHERE state='UNIT_COUNT'").fetchone()[0] == 0
    finally:
        conn.close()
