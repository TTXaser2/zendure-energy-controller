import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

import version
from graph_core_v3 import connect_graph_core
from measurement_db import detect_measurement_db_backend, ensure_schema
from tools import v14_cutover

ROOT = Path(__file__).resolve().parents[1]


def _write_v4(path: Path, rows):
    header = [
        "schema_version", "cycle_index", "measurement_epoch_ms", "config_control_hash",
        "operating_mode", "control_intent", "grid_power_w", "grid_power_raw_w", "grid_power_valid",
        "pv_power_w", "pv_power_valid", "house_power_w", "house_power_valid",
        "zendure_actual_power_w", "zendure_actual_power_valid", "zendure_soc_percent", "zendure_soc_valid",
        "second_battery_power_w", "second_battery_power_valid", "second_battery_soc_percent", "second_battery_soc_valid",
        "control_grid_power_w", "control_grid_power_smoothed_w", "control_grid_power_smoothed_valid",
        "target_raw_w", "target_limited_w", "target_filtered_w", "target_step_limited_w", "target_final_w", "target_final_reason",
        "target_changed_by_deadband", "target_changed_by_smoothing", "target_changed_by_step_limit", "target_changed_by_soc_limit",
        "target_changed_by_power_limit", "target_changed_by_cross_charge", "target_changed_by_mode", "target_changed_by_safe_state",
        "zendure_power_observation_direction", "zendure_power_observation_confidence",
        "command_lifecycle_state", "command_desired_sequence_id", "command_desired_smart_mode", "command_desired_ac_mode",
        "command_desired_input_limit_w", "command_desired_output_limit_w", "command_desired_signed_target_w",
        "command_publish_event_id", "command_publish_epoch_s", "command_readback_matches_desired", "command_readback_mismatch_fields",
        "zendure_command_smart_mode", "zendure_command_ac_mode", "zendure_command_input_limit_w", "zendure_command_output_limit_w",
        "command_effect_category", "command_effect_reference_w", "command_effect_reason", "command_resync_count",
        "command_neutralization_episode_id", "zendure_unit_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(";".join(header) + "\r\n")
        for row in rows:
            fh.write(";".join(str(row.get(key, "")) for key in header) + "\r\n")


def _row(ts_ms: int, cycle: int, *, grid: int = 100):
    return {
        "schema_version": 4,
        "cycle_index": cycle,
        "measurement_epoch_ms": ts_ms,
        "config_control_hash": "hash-a",
        "operating_mode": "AUTO",
        "control_intent": "CHARGE",
        "grid_power_w": grid,
        "grid_power_raw_w": grid,
        "grid_power_valid": 1,
        "zendure_actual_power_w": 90,
        "zendure_actual_power_valid": 1,
        "zendure_soc_percent": 50,
        "zendure_soc_valid": 1,
        "second_battery_power_w": 0,
        "second_battery_power_valid": 1,
        "second_battery_soc_percent": 70,
        "second_battery_soc_valid": 1,
        "control_grid_power_w": grid,
        "control_grid_power_smoothed_w": grid,
        "control_grid_power_smoothed_valid": 1,
        "target_raw_w": 120,
        "target_limited_w": 115,
        "target_filtered_w": 110,
        "target_step_limited_w": 105,
        "target_final_w": 100,
        "target_final_reason": "AUTO_GRID_EXPORT",
        "zendure_power_observation_direction": "CHARGE",
        "zendure_power_observation_confidence": "HIGH",
        "command_lifecycle_state": "ACTIVE_EFFECTIVE",
        "command_desired_sequence_id": cycle,
        "command_desired_smart_mode": 1,
        "command_desired_ac_mode": "input",
        "command_desired_input_limit_w": 100,
        "command_desired_output_limit_w": 0,
        "command_desired_signed_target_w": 100,
        "command_publish_event_id": cycle,
        "command_publish_epoch_s": ts_ms / 1000.0,
        "command_readback_matches_desired": 1,
        "zendure_command_smart_mode": 1,
        "zendure_command_ac_mode": "input",
        "zendure_command_input_limit_w": 100,
        "zendure_command_output_limit_w": 0,
        "command_effect_category": "COMMAND_TARGET_TRACKING_EFFECTIVE",
        "command_effect_reference_w": 90,
        "command_resync_count": 0,
        "command_neutralization_episode_id": 0,
        "zendure_unit_count": 1,
    }


def _fixture(tmp_path: Path, *, existing_backend: str = "v2"):
    logs = tmp_path / "logs"
    logs.mkdir()
    db = logs / "zec_measurements.sqlite3"
    cfg = {
        "MEASUREMENT_DB_ENABLED": True,
        "MEASUREMENT_DB_PATH": str(db),
        "MEASUREMENT_LOG_DIR": str(logs),
        "MEASUREMENT_LOG_FALLBACK_DIR": str(tmp_path / "fallback"),
        "SECOND_BATTERY_DISPLAY_NAME": "Hausspeicher",
    }
    config = tmp_path / "config.json"
    config.write_text(json.dumps(cfg), encoding="utf-8")
    source = logs / "zendure_measurements_20260904.csv"
    start = 1_788_500_000_000
    _write_v4(source, [_row(start, 1), _row(start + 3000, 2, grid=150)])
    if existing_backend == "v2":
        conn = sqlite3.connect(db)
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO measurement_raw(ts_ms,grid_power_w,raw_grid_power_w,zendure_target_power_w,zendure_actual_power_w,pv_power_w,house_power_w,soc_percent,mode,control_reason,data_status,source,soc_valid,grid_valid,safe_state_active,cross_charge_limited,night_window_active,night_reserve_active,primary_soc_percent,primary_power_w) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (start - 60000, 1, 1, 3, 2, 7, 8, 4, "OLD", "OLD", "ok", "old", 1, 1, 0, 0, 0, 0, 5, 6),
        )
        conn.commit()
        conn.close()
    elif existing_backend == "v3":
        conn = connect_graph_core(db)
        conn.execute(
            "INSERT INTO measurement_raw(ts_ms,run_id,cycle_index,grid_power_dw) VALUES(?,?,?,?)",
            (start - 60000, 1, 1, 9990),
        )
        conn.commit()
        conn.close()
    return config, db, source, start


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_identity_and_installer_cutover_contract_are_v14():
    assert version.APP_VERSION == "14.0.0"
    assert version.APP_VERSION_LABEL == "V14.0.0"
    assert version.APP_BUILD_ID == "v14.0.0-20260904-r2"
    script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION="v14_0_0"' in script
    assert 'EXPECTED_SOURCE_VERSION="13.0.3"' in script
    assert 'EXPECTED_SOURCE_BUILD_ID="v13.0.3-20260814"' in script
    assert 'EXPECTED_TARGET_VERSION="14.0.0"' in script
    assert 'EXPECTED_TARGET_BUILD_ID="v14.0.0-20260904-r2"' in script
    assert "V14_0_0_SOURCE_MANIFEST.sha256" in script
    assert "tools/v14_cutover.py preflight" in script
    assert "tools/v14_cutover.py rebuild" in script
    assert "tools/v14_cutover.py verify" in script
    assert "collect_zec_install_diagnostics.sh" in script
    assert "verify_build_test_evidence" in script
    assert 'verify_source_manifest_at "$TARGET"' in script
    assert "python3 -m unittest discover" not in script
    assert "python3 -m pytest" not in script
    assert "pytest" not in (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    field = (ROOT / "tools" / "v14_field_acceptance.py").read_text(encoding="utf-8")
    assert "commands_published_by_this_tool" in field
    assert "configuration_mutations_by_this_tool" in field
    assert "/api/graph/v1/command-follow" in field
    assert "/api/graph/v1/episode-comparison" in field
    assert "rollback_backup_integrity" in field
    assert "no new latency threshold introduced" in field.lower()


def test_preflight_requires_measurement_v4_and_keeps_readiness_separate(tmp_path):
    config, db, source, _ = _fixture(tmp_path)
    result = v14_cutover.preflight(config)
    assert result["status"] == "ok"
    assert result["db_backend"] == "v2"
    assert result["v4_file_count"] == 1
    assert result["controller_readiness_impact"] == "NONE"
    source.unlink()
    result = v14_cutover.preflight(config)
    assert result["status"] == "error"
    assert "NO_V4_FILES" in result["reasons"]
    assert detect_measurement_db_backend(str(db))["backend"] == "v2"


def test_cutover_rebuilds_v3_from_v4_and_restore_is_byte_exact_for_old_db(tmp_path):
    config, db, _source, start = _fixture(tmp_path)
    old_hash = _sha256(db)
    backup = tmp_path / "cutover-backup"
    result = v14_cutover.rebuild_and_cutover(config, backup)
    assert result["status"] == "ok", result
    assert result["previous_backend"] == "v2"
    assert detect_measurement_db_backend(str(db))["backend"] == "v3"
    assert result["verify"]["runtime"]["read_mode"] == "V3_NATIVE"
    assert result["verify"]["runtime"]["workspace_ready"] is True
    conn = sqlite3.connect(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM measurement_raw").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM measurement_raw WHERE ts_ms=?", (start - 60000,)).fetchone()[0] == 0
    finally:
        conn.close()
    restored = v14_cutover.restore(backup)
    assert restored["status"] == "ok"
    assert _sha256(db) == old_hash
    assert detect_measurement_db_backend(str(db))["backend"] == "v2"


def test_restore_rejects_tampered_graph_backup(tmp_path):
    config, db, _source, _start = _fixture(tmp_path)
    backup = tmp_path / "backup"
    result = v14_cutover.rebuild_and_cutover(config, backup)
    assert result["status"] == "ok", result
    state = json.loads((backup / "cutover_state.json").read_text(encoding="utf-8"))
    db_info = state["artifacts"]["db"]
    assert db_info["backup_verified"] is True
    assert len(db_info["sha256"]) == 64
    backup_db = Path(db_info["backup"])
    backup_db.write_bytes(backup_db.read_bytes() + b"tamper")
    restored = v14_cutover.restore(backup)
    assert restored["status"] == "error"
    assert restored["reason"] == "BACKUP_ARTIFACT_VERIFY_FAILED"
    assert detect_measurement_db_backend(str(db))["backend"] == "v3"


def test_existing_v3_engineering_rows_are_not_accepted_as_productive_truth(tmp_path):
    config, db, _source, start = _fixture(tmp_path, existing_backend="v3")
    result = v14_cutover.rebuild_and_cutover(config, tmp_path / "backup")
    assert result["status"] == "ok", result
    conn = sqlite3.connect(db)
    try:
        timestamps = [row[0] for row in conn.execute("SELECT ts_ms FROM measurement_raw ORDER BY ts_ms")]
    finally:
        conn.close()
    assert timestamps == [start, start + 3000]


def test_post_activation_verification_failure_restores_original_db(tmp_path, monkeypatch):
    config, db, _source, _start = _fixture(tmp_path)
    old_hash = _sha256(db)
    real_verify = v14_cutover.verify

    def fail_verify(config_path):
        # The candidate has already been activated when this callback is used.
        assert detect_measurement_db_backend(str(db))["backend"] == "v3"
        return {"status": "error", "reason": "INJECTED_VERIFY_FAILURE"}

    monkeypatch.setattr(v14_cutover, "verify", fail_verify)
    result = v14_cutover.rebuild_and_cutover(config, tmp_path / "backup")
    monkeypatch.setattr(v14_cutover, "verify", real_verify)
    assert result["status"] == "error"
    assert result["activated_before_error"] is True
    assert result["rollback"]["status"] == "ok"
    assert _sha256(db) == old_hash
    assert detect_measurement_db_backend(str(db))["backend"] == "v2"


def test_corrupt_v4_source_cannot_replace_existing_database(tmp_path):
    config, db, source, _start = _fixture(tmp_path)
    old_hash = _sha256(db)
    source.write_bytes(source.read_bytes().replace(b"AUTO", b"AU\x00TO", 1))
    result = v14_cutover.rebuild_and_cutover(config, tmp_path / "backup")
    assert result["status"] == "error"
    assert result["activated_before_error"] is False
    assert _sha256(db) == old_hash
    assert detect_measurement_db_backend(str(db))["backend"] == "v2"


def test_install_diagnostics_never_copy_raw_config_and_document_redaction():
    script = (ROOT / "tools" / "collect_zec_install_diagnostics.sh").read_text(encoding="utf-8")
    assert "config.redacted.json" in script
    assert "SETTINGS_BY_KEY" in script
    assert "is_secret" in script
    assert "Raw config.json is intentionally NOT included" in script
    assert "safe_copy /opt/zendure-controller/config.json" not in script
    assert "/api/graph/v1/runtime" in script
    assert "/ready" in script


def test_installer_rollback_restores_external_graphstore_and_collects_diagnostics():
    script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    diagnostics_idx = script.index('collect_install_diagnostics "v14-install-failure"')
    graph_restore_idx = script.index('v14_cutover.py" restore')
    target_restore_idx = script.index('sudo rm -rf "$TARGET"')
    assert diagnostics_idx < graph_restore_idx < target_restore_idx
    assert "GRAPH_CUTOVER_COMPLETED" in script
    assert "Graph-History-Readiness" in script
    assert "control_readiness_impact" in script


def test_no_retention_scheduler_or_vacuum_policy_is_introduced_by_wp10():
    script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8").lower()
    cutover = (ROOT / "tools" / "v14_cutover.py").read_text(encoding="utf-8").lower()
    combined = script + "\n" + cutover
    assert "vacuum" not in combined
    assert "retention-scheduler" not in combined
    assert "retention_scheduler" not in combined
