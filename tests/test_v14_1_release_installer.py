from pathlib import Path

import version

ROOT = Path(__file__).resolve().parents[1]


def test_release_identity_is_unique_v14_1_2():
    assert version.APP_VERSION == "14.1.2"
    assert version.APP_VERSION_LABEL == "V14.1.2"
    assert version.APP_BUILD_ID == "v14.1.2-20260905"


def test_installer_is_exact_v14_1_1_to_v14_1_2():
    script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION="v14_1_2"' in script
    assert 'EXPECTED_SOURCE_VERSION="14.1.1"' in script
    assert 'EXPECTED_SOURCE_BUILD_ID="v14.1.1-20260905"' in script
    assert 'EXPECTED_TARGET_VERSION="14.1.2"' in script
    assert 'EXPECTED_TARGET_BUILD_ID="v14.1.2-20260905"' in script


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
    assert 'INSTALL_REPORT="/tmp/zec_v14_1_2_install_report.json"' in script
    assert '"graph_core_v3_rebuilt": False' in script
    assert '"graph_core_v3_preserved": True' in script


def test_field_acceptance_targets_greenfield_release():
    tool = (ROOT / "tools" / "v14_field_acceptance.py").read_text(encoding="utf-8")
    assert 'EXPECTED_VERSION = "14.1.2"' in tool
    assert 'EXPECTED_BUILD_ID = "v14.1.2-20260905"' in tool
    assert 'data-greenfield-contract="v14.1.2"' in tool
    assert '--install-report' in tool
    assert 'CUTOVER_REPORT_NOT_FOUND' not in tool


def test_installer_and_field_acceptance_verify_greenfield_assets_on_running_pi():
    installer = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    field = (ROOT / "tools" / "v14_field_acceptance.py").read_text(encoding="utf-8")
    for token in ('data-greenfield-contract="v14.1.2"', '/static/graph_v14_1.js', '/api/graph/v1/workspace'):
        assert token in installer
        assert token in field
    assert "graph_greenfield_assets" in field
    assert '"/graph-view-data" not in js_text' in field
