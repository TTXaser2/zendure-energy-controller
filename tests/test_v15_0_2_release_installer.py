from pathlib import Path
import version

ROOT = Path(__file__).resolve().parents[1]


def test_v15_0_2_identity_exact_upgrade_source_and_package_contract():
    assert version.APP_VERSION == "15.0.2"
    assert version.APP_VERSION_LABEL == "V15.0.2"
    assert version.APP_BUILD_ID == "v15.0.2-20260911"
    script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
    for token in (
        'EXPECTED_VERSION="v15_0_2"',
        'EXPECTED_SOURCE_VERSION="15.0.1"',
        'EXPECTED_SOURCE_BUILD_ID="v15.0.1-20260911"',
        'EXPECTED_TARGET_VERSION="15.0.2"',
        'EXPECTED_TARGET_BUILD_ID="v15.0.2-20260911"',
        'SOURCE_MODE="V15_0_1"',
        'V15_0_2_SOURCE_MANIFEST.sha256',
        '/tmp/zec_v15_0_2_install_report.json',
    ):
        assert token in script


def test_v15_0_2_installer_probes_exact_visual_followup_contracts():
    script = (ROOT / "tools/update_zendure_controller.sh").read_text(encoding="utf-8")
    for token in (
        "adaptiveDetailWindow",
        "chartYRatioFromPointer",
        "setHoverMsAt(ts,chartYRatioFromPointer(chart,event))",
        "top .10s ease-out",
        "min-height:112px",
        "graph_core_v3_preserved",
        "v14_cutover.py verify",
    ):
        assert token in script
    assert "v14_cutover.py rebuild" not in script
    assert "pip install" not in script


def test_v15_0_2_field_acceptance_targets_visual_followup_release():
    tool = (ROOT / "tools/v15_field_acceptance.py").read_text(encoding="utf-8")
    for token in (
        'EXPECTED_VERSION = "15.0.2"',
        'EXPECTED_LABEL = "V15.0.2"',
        'EXPECTED_BUILD_ID = "v15.0.2-20260911"',
        'FORMAT = "ZEC_V15_0_2_FIELD_ACCEPTANCE_V1"',
        '/tmp/zec_v15_0_2_install_report.json',
        "adaptiveDetailWindow",
        "chartYRatioFromPointer",
        "top .10s ease-out",
        "min-height:112px",
    ):
        assert token in tool
    assert "commands_published_by_this_tool" in tool
    assert "configuration_mutations_by_this_tool" in tool


def test_v15_0_2_remains_read_only_modbus_and_greenfield_contract_compatible():
    graph_page = (ROOT / "graph_ui/page.py").read_text(encoding="utf-8")
    assert 'data-greenfield-contract="v14.1.4"' in graph_page
    modbus = (ROOT / "primary_storage_modbus.py").read_text(encoding="utf-8")
    assert "FC_READ_HOLDING_REGISTERS = 3" in modbus
    assert "FC_READ_INPUT_REGISTERS = 4" in modbus
    assert "write_register" not in modbus
