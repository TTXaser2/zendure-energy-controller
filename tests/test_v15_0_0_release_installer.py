from pathlib import Path

import version

ROOT = Path(__file__).resolve().parents[1]


def test_v15_release_identity_and_exact_source():
    assert version.APP_VERSION == "15.0.0"
    assert version.APP_VERSION_LABEL == "V15.0.0"
    assert version.APP_BUILD_ID == "v15.0.0-20260910"
    script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
    for token in (
        'EXPECTED_VERSION="v15_0_0"',
        'EXPECTED_SOURCE_VERSION="14.1.4"',
        'EXPECTED_SOURCE_BUILD_ID="v14.1.4-20260908"',
        'EXPECTED_TARGET_VERSION="15.0.0"',
        'EXPECTED_TARGET_BUILD_ID="v15.0.0-20260910"',
        'SOURCE_MODE="V14_1_4"',
        'V15_0_0_SOURCE_MANIFEST.sha256',
        '/tmp/zec_v15_0_0_install_report.json',
    ):
        assert token in script


def test_v15_installer_preserves_config_runtime_and_graph_core_v3():
    script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
    assert "v14_cutover.py rebuild" not in script
    assert "graph_core_v3_preserved" in script
    assert "v14_cutover.py verify" in script
    assert "--exclude 'config.json'" in script
    assert "--exclude 'logs/'" in script
    assert "--exclude '*.sqlite3'" in script
    assert "migrate_config_to_current.py" in script
    assert "pip install" not in script
    assert "pymodbus" not in script.lower()
    assert "pymodbustcp" not in script.lower()


def test_v15_field_acceptance_can_require_native_modbus_profile():
    tool = (ROOT / "tools/v15_field_acceptance.py").read_text(encoding="utf-8")
    for token in (
        'EXPECTED_VERSION = "15.0.0"',
        'EXPECTED_BUILD_ID = "v15.0.0-20260910"',
        '--expect-primary-profile',
        '"modbus_template"',
        '"modbus_tcp"',
        'primary_storage_source_expected',
        '/tmp/zec_v15_0_0_install_report.json',
    ):
        assert token in tool
    assert "commands_published_by_this_tool" in tool
    assert "configuration_mutations_by_this_tool" in tool


def test_v15_keeps_v14_graph_contract_without_rebuild():
    installer = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
    field = (ROOT / "tools/v15_field_acceptance.py").read_text(encoding="utf-8")
    for text in (installer, field):
        assert 'data-greenfield-contract="v14.1.4"' in text
        assert '/static/graph_v14_1.js' in text
        assert '/api/graph/v1/workspace' in text
