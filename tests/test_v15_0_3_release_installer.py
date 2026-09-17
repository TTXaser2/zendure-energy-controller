from pathlib import Path
import version

ROOT = Path(__file__).resolve().parents[1]


def test_v15_0_3_identity_exact_upgrade_source_and_datasheet_contract():
    assert version.APP_VERSION == "16.0.1"
    assert version.APP_VERSION_LABEL == "V16.0.1"
    assert version.APP_BUILD_ID == "v16.0.1-20260915"
    script = (ROOT / "tools/install_zendure_controller.sh").read_text(encoding="utf-8")
    for token in (
        'EXPECTED_VERSION_ARG="v16_0_1"',
        'EXPECTED_SOURCE_VERSION="15.0.3"',
        'EXPECTED_SOURCE_BUILD_ID="v15.0.3-20260911"',
        'EXPECTED_TARGET_VERSION="16.0.1"',
        'EXPECTED_TARGET_BUILD_ID="v16.0.1-20260915"',
        'SOURCE_MANIFEST="V16_0_1_SOURCE_MANIFEST.sha256"',
        '/tmp/zec_v16_0_1_install_report.json',
        'validate_release_datasheet.py',
        '--preflight-only',
        'CLEAN_FRESH_INSTALL',
        'SUPPORTED_UPDATE',
    ):
        assert token in script
    assert 'SOURCE_MODE="V15_0_2"' not in script


def test_v15_0_3_field_acceptance_checks_installed_datasheet():
    tool = (ROOT / "tools/v15_field_acceptance.py").read_text(encoding="utf-8")
    for token in (
        'EXPECTED_VERSION = "15.0.3"',
        'EXPECTED_LABEL = "V15.0.3"',
        'EXPECTED_BUILD_ID = "v15.0.3-20260911"',
        'FORMAT = "ZEC_V15_0_3_FIELD_ACCEPTANCE_V1"',
        'release_datasheet',
        'validate_release_datasheet',
    ):
        assert token in tool
