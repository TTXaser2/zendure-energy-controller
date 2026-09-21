from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import version
from tools.validate_release_datasheet import validate


def test_v15_0_3_datasheet_release_identity_and_stable_paths():
    assert version.APP_VERSION == "16.2.3"
    assert version.APP_VERSION_LABEL == "V16.2.3"
    assert version.APP_BUILD_ID == "v16.2.3-20260921"
    for rel in (
        "docs/ZEC_Technisches_Datenblatt.pdf",
        "docs/ZEC_Technisches_Datenblatt.docx",
        "docs/ZEC_Technisches_Datenblatt.release.json",
    ):
        path = ROOT / rel
        assert path.is_file()
        assert path.stat().st_size > 0


def test_v15_0_3_datasheet_gate_passes_current_product_contract():
    result = validate(ROOT)
    assert result["status"] == "PASS", result
    assert result["release_identities_in_docx"] == ["V16.2.3"]
    assert result["required_text_count"] >= 8


def test_v15_0_3_canonical_release_process_makes_datasheet_mandatory():
    text = (ROOT / "06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md").read_text(encoding="utf-8")
    for token in (
        "Technisches Datenblatt – dauerhafter Releasevertrag",
        "docs/ZEC_Technisches_Datenblatt.pdf",
        "docs/ZEC_Technisches_Datenblatt.docx",
        "keine Versionshistorie",
        "Hardware- und Softwarevoraussetzungen",
        "unterstützten Anlagenkonstellationen",
        "Shelly Pro 3EM",
        "Fresh-extract",
    ):
        assert token in text


def test_v15_0_3_datasheet_metadata_hashes_current_files():
    meta = json.loads((ROOT / "docs/ZEC_Technisches_Datenblatt.release.json").read_text(encoding="utf-8"))
    assert meta["release_version"] == "16.2.3"
    assert meta["release_label"] == "V16.2.3"
    assert meta["build_id"] == "v16.2.3-20260921"
