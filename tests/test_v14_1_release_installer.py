from pathlib import Path

import version

ROOT = Path(__file__).resolve().parents[1]


def test_release_identity_is_unique_v14_1_3():
    assert version.APP_VERSION == "14.1.3"
    assert version.APP_VERSION_LABEL == "V14.1.3"
    assert version.APP_BUILD_ID == "v14.1.3-20260906"


def test_installer_is_exact_v14_1_2_to_v14_1_3():
    script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION="v14_1_3"' in script
    assert 'EXPECTED_SOURCE_VERSION="14.1.2"' in script
    assert 'EXPECTED_SOURCE_BUILD_ID="v14.1.2-20260905"' in script
    assert 'EXPECTED_TARGET_VERSION="14.1.3"' in script
    assert 'EXPECTED_TARGET_BUILD_ID="v14.1.3-20260906"' in script


def test_installer_preserves_v3_instead_of_rebuilding_it():
    script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    assert "v14_cutover.py rebuild" not in script
    assert "GRAPH_CUTOVER_COMPLETED" not in script
    assert "graph_core_v3_preserved" in script
    assert "v14_cutover.py verify" in script
    assert "--exclude 'logs/'" in script
    assert "--exclude '*.sqlite3'" in script


def test_installer_records_hash_verified_full_release_backup():
    script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    assert 'BACKUP_SHA256="$(sha256sum "$BACKUP"' in script
    assert 'INSTALL_REPORT="/tmp/zec_v14_1_3_install_report.json"' in script
    assert '"graph_core_v3_rebuilt": False' in script
    assert '"graph_core_v3_preserved": True' in script


def test_field_acceptance_targets_greenfield_release():
    tool = (ROOT / "tools" / "v14_field_acceptance.py").read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION = "14.1.3"' in tool
    assert 'EXPECTED_BUILD_ID = "v14.1.3-20260906"' in tool
    assert 'data-greenfield-contract="v14.1.3"' in tool
    assert '--install-report' in tool
    assert 'CUTOVER_REPORT_NOT_FOUND' not in tool


def test_installer_and_field_acceptance_verify_greenfield_assets_on_running_pi():
    installer = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    field = (ROOT / "tools" / "v14_field_acceptance.py").read_text(encoding="utf-8")
    for token in ('data-greenfield-contract="v14.1.3"', '/static/graph_v14_1.js', '/api/graph/v1/workspace'):
        assert token in installer
        assert token in field
    assert "graph_greenfield_assets" in field
    assert '"/graph-view-data" not in js_text' in field


def test_v14_1_3_installer_runs_targeted_state_backfill_inside_rollback_window():
    script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    assert "backfill_graph_control_states_v14_1_3.py" in script
    assert '--runtime-root "$TARGET"' in script
    assert '--apply --json >"$STATE_BACKFILL_REPORT"' in script
    assert "NO_V4_FILES" in script
    assert 'graph_control_state_backfill' in script
    # Full release backup must exist before any Graph-Core state mutation.
    assert script.index('echo "Erstelle vollständiges Rollback-Backup..."') < script.index('backfill_graph_control_states_v14_1_3.py')
    assert script.index('v14_cutover.py verify --config "$TARGET/config.json" --runtime-root "$TARGET" --json >/tmp/zec_v14_1_3_graph_verify_prebackfill.json') < script.index('backfill_graph_control_states_v14_1_3.py')
    assert script.index('backfill_graph_control_states_v14_1_3.py') < script.index('v14_cutover.py verify --config "$TARGET/config.json" --runtime-root "$TARGET" --json >/tmp/zec_v14_1_3_graph_verify_prestart.json')


def test_v14_1_3_field_acceptance_covers_state_status_soc_and_dark_mode_contracts():
    tool = (ROOT / "tools" / "v14_field_acceptance.py").read_text(encoding="utf-8")
    for marker in (
        'graph_control_state_intervals',
        'graph_control_state_backfill_report',
        'status_soc_day_v3',
        'settings_dark_mode_contract',
        'gfCommandCursorCard',
        'gfCompareHoverCard',
        'gfStateMagnifier',
        'Math.round(Number(start))',
    ):
        assert marker in tool
