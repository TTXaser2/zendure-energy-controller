from __future__ import annotations

import json
import os
import time
from pathlib import Path

from tools.v17_field_acceptance import (
    _resolve_install_report,
    _settings_surface_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def _settings_model(*, primary_enabled=True, unit_count=1):
    required = [
        {
            "key": "SECOND_BATTERY_INTEGRATION_ENABLED",
            "available": True,
            "editable": True,
            "applicable": True,
            "surface_state": "operational",
            "applicability_rule": None,
        },
        {
            "key": "SECOND_BATTERY_CAPACITY_WH",
            "available": True,
            "editable": True,
            "applicable": primary_enabled,
            "surface_state": "operational",
            "applicability_rule": {"key": "SECOND_BATTERY_INTEGRATION_ENABLED", "equals": True},
        },
        {
            "key": "SECOND_BATTERY_MAX_DISCHARGE_POWER_W",
            "available": True,
            "editable": True,
            "applicable": primary_enabled,
            "surface_state": "operational",
            "applicability_rule": {"key": "SECOND_BATTERY_INTEGRATION_ENABLED", "equals": True},
        },
    ]
    return {
        "categories": [{"sections": [{"settings": required}]}],
        "topology": {
            "zendure_unit_count": unit_count,
            "primary_storage_enabled": primary_enabled,
        },
    }


def test_settings_surface_contract_accepts_primary_controls_for_one_or_two_zendures():
    for units in (1, 2):
        for primary_enabled in (False, True):
            ok, evidence = _settings_surface_contract(
                _settings_model(primary_enabled=primary_enabled, unit_count=units)
            )
            assert ok is True
            assert evidence["topology"]["zendure_unit_count"] == units
            assert evidence["required"]["SECOND_BATTERY_CAPACITY_WH"]["applicable"] is primary_enabled


def test_settings_surface_contract_rejects_missing_required_or_target_only_leak():
    model = _settings_model()
    model["categories"][0]["sections"][0]["settings"] = model["categories"][0]["sections"][0]["settings"][1:]
    ok, evidence = _settings_surface_contract(model)
    assert ok is False
    assert evidence["required"]["SECOND_BATTERY_INTEGRATION_ENABLED"]["present"] is False

    model = _settings_model()
    model["categories"][0]["sections"][0]["settings"].append({"key": "HARVEST_SEASON_MODE"})
    ok, evidence = _settings_surface_contract(model)
    assert ok is False
    assert evidence["forbidden_present"] == ["HARVEST_SEASON_MODE"]


def test_report_discovery_prefers_latest_persistent_then_compatibility(tmp_path):
    old = tmp_path / "zec_v17_0_1_install_report_20260921_100000.json"
    new = tmp_path / "zec_v17_0_1_install_report_20260921_110000.json"
    old.write_text("{}\n", encoding="utf-8")
    new.write_text("{}\n", encoding="utf-8")
    now = time.time_ns()
    os.utime(old, ns=(now - 2_000_000, now - 2_000_000))
    os.utime(new, ns=(now - 1_000_000, now - 1_000_000))
    compat = tmp_path / "compat.json"
    compat.write_text("{}\n", encoding="utf-8")

    selected, mode = _resolve_install_report("", persistent_dir=tmp_path, compatibility_path=compat)
    assert selected == new
    assert mode == "persistent_latest"

    old.unlink(); new.unlink()
    selected, mode = _resolve_install_report("", persistent_dir=tmp_path, compatibility_path=compat)
    assert selected == compat
    assert mode == "compatibility_fallback"


def test_report_discovery_never_overrides_explicit_path(tmp_path):
    persistent = tmp_path / "zec_v17_0_1_install_report_20260921_120000.json"
    persistent.write_text("{}\n", encoding="utf-8")
    explicit = tmp_path / "chosen.json"
    selected, mode = _resolve_install_report(str(explicit), persistent_dir=tmp_path)
    assert selected == explicit
    assert mode == "explicit"


def test_installer_persists_report_atomically_and_keeps_tmp_as_compatibility_copy():
    script = (ROOT / "tools/install_zendure_controller.sh").read_text(encoding="utf-8")
    assert 'INSTALL_REPORT="$DOWNLOAD_DIR/zec_${VERSION}_install_report_${STAMP}.json"' in script
    assert 'INSTALL_REPORT_COMPAT="/tmp/zec_${VERSION}_install_report.json"' in script
    assert "os.replace(tmp,path)" in script
    assert "os.fsync(fh.fileno())" in script
    assert "Persistenter Installationsreport: $INSTALL_REPORT" in script
    assert "$DOWNLOAD_DIR ist nicht beschreibbar" in script


def test_install_report_contract_keeps_release_identity_and_real_backup_evidence_fields():
    script = (ROOT / "tools/install_zendure_controller.sh").read_text(encoding="utf-8")
    assert "'format':'ZEC_V16_2_0_INSTALL_REPORT_V1'" in script
    assert "'target':{'version':'$EXPECTED_TARGET_VERSION','build_id':'$EXPECTED_TARGET_BUILD_ID'}" in script
    assert "'release_backup':{'path':'$BACKUP','sha256':'$BACKUP_SHA256','size':int('$BACKUP_SIZE')}" in script
