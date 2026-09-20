from pathlib import Path

import version

ROOT = Path(__file__).resolve().parents[1]


def test_latest_release_identity_is_v15_0_2():
    assert version.APP_VERSION == "16.1.0"
    assert version.APP_VERSION_LABEL == "V16.1.0"
    assert version.APP_BUILD_ID == "v16.1.0-20260919"


def test_installer_is_exact_v15_0_0_to_v15_0_2():
    script = (ROOT / "tools" / "install_zendure_controller.sh").read_text(encoding="utf-8")
    for token in ('EXPECTED_VERSION_ARG="v16_1_0"','EXPECTED_SOURCE_VERSION="16.0.2"','EXPECTED_SOURCE_BUILD_ID="v16.0.2-20260917"','EXPECTED_TARGET_VERSION="16.1.0"','EXPECTED_TARGET_BUILD_ID="v16.1.0-20260919"'):
        assert token in script

def test_installer_preserves_v3_instead_of_rebuilding_it():
    script = (ROOT / "tools" / "install_zendure_controller.sh").read_text(encoding="utf-8")
    assert "v14_cutover.py rebuild" not in script
    assert "GRAPH_CUTOVER_COMPLETED" not in script
    assert "graph_core_v3_preserved" in script
    assert "v14_cutover.py verify" in script
    assert "--exclude 'logs/'" in script
    assert "--exclude '*.sqlite3'" in script


def test_installer_records_hash_verified_full_release_backup():
    script = (ROOT / "tools" / "install_zendure_controller.sh").read_text(encoding="utf-8")
    assert 'BACKUP_SHA256="$(sha256sum "$BACKUP"' in script
    assert 'INSTALL_REPORT="/tmp/zec_v16_1_0_install_report.json"' in script
    assert "'graph_core_v3_rebuilt': False" in script
    assert "'graph_core_v3_preserved': True" in script

def test_field_acceptance_targets_greenfield_release():
    tool = (ROOT / "tools" / "v15_field_acceptance.py").read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION = "15.0.3"' in tool
    assert 'EXPECTED_BUILD_ID = "v15.0.3-20260911"' in tool
    assert 'data-greenfield-contract="v14.1.4"' in tool
    assert '--install-report' in tool
    assert 'CUTOVER_REPORT_NOT_FOUND' not in tool


def test_installer_and_field_acceptance_verify_greenfield_assets_on_running_pi():
    installer = (ROOT / "tools" / "install_zendure_controller.sh").read_text(encoding="utf-8")
    field = (ROOT / "tools" / "v16_field_acceptance.py").read_text(encoding="utf-8")
    page = (ROOT / "graph_ui" / "page.py").read_text(encoding="utf-8")
    assert 'data-greenfield-contract="v14.1.4"' in page
    for token in ('data-greenfield-contract="v14.1.4"','/static/graph_v14_1.js','/api/graph/v1/workspace'):
        assert token in field
    assert "graph_greenfield_assets" in field
    assert 'v14_cutover.py verify' in installer

def test_latest_installer_does_not_rerun_historical_v14_1_3_state_backfill():
    script = (ROOT / "tools" / "install_zendure_controller.sh").read_text(encoding="utf-8")
    assert "backfill_graph_control_states_v14_1_3.py" not in script
    assert "COMPLETED_IN_SOURCE_RELEASE_V14_1_3" in script
    assert 'graph_verify_prestart.json' in script
    assert 'tools/v14_cutover.py verify --config "$TARGET/config.json" --runtime-root "$TARGET"' in script
    assert "'graph_core_v3_rebuilt': False" in script
    assert "'graph_core_v3_preserved': True" in script

def test_latest_field_acceptance_covers_state_status_soc_and_dark_mode_contracts():
    tool = (ROOT / "tools" / "v15_field_acceptance.py").read_text(encoding="utf-8")
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
