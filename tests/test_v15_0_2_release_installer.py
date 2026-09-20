from pathlib import Path
import version

ROOT = Path(__file__).resolve().parents[1]


def test_v15_0_2_identity_exact_upgrade_source_and_package_contract():
    assert version.APP_VERSION == "16.1.0"
    assert version.APP_VERSION_LABEL == "V16.1.0"
    assert version.APP_BUILD_ID == "v16.1.0-20260919"
    script = (ROOT / "tools/install_zendure_controller.sh").read_text(encoding="utf-8")
    for token in ('EXPECTED_VERSION_ARG="v16_1_0"','EXPECTED_SOURCE_VERSION="16.0.2"','EXPECTED_SOURCE_BUILD_ID="v16.0.2-20260917"','EXPECTED_TARGET_VERSION="16.1.0"','EXPECTED_TARGET_BUILD_ID="v16.1.0-20260919"','SOURCE_MANIFEST="V16_1_0_SOURCE_MANIFEST.sha256"','/tmp/zec_v16_1_0_install_report.json'):
        assert token in script

def test_v15_0_2_installer_probes_exact_visual_followup_contracts():
    script = (ROOT / "tools/install_zendure_controller.sh").read_text(encoding="utf-8")
    field = (ROOT / "tools/v16_field_acceptance.py").read_text(encoding="utf-8")
    css = (ROOT / "static/graph_v14_1.css").read_text(encoding="utf-8")
    for token in ("adaptiveDetailWindow","chartYRatioFromPointer","setHoverMsAt(ts,chartYRatioFromPointer(chart,event))"):
        assert token in field
    assert "top .10s ease-out" in css
    assert "min-height:112px" in css
    assert "graph_core_v3_preserved" in script
    assert "v14_cutover.py verify" in script
    assert "v14_cutover.py rebuild" not in script
    assert "pip install" not in script

def test_v15_0_2_field_acceptance_targets_visual_followup_release():
    tool = (ROOT / "tools/v15_field_acceptance.py").read_text(encoding="utf-8")
    for token in (
        'EXPECTED_VERSION = "15.0.3"',
        'EXPECTED_LABEL = "V15.0.3"',
        'EXPECTED_BUILD_ID = "v15.0.3-20260911"',
        'FORMAT = "ZEC_V15_0_3_FIELD_ACCEPTANCE_V1"',
        '/tmp/zec_v15_0_3_install_report.json',
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
