from __future__ import annotations

import json
import tempfile
from contextlib import contextmanager
from pathlib import Path

from config_manager import ConfigManager, DEFAULT_CONFIG
from settings_model import build_settings_model
from settings_registry import Applicability, SurfaceState, get_setting
from settings_runtime import parse_full_candidate

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def _manager(*, primary_enabled: bool):
    with tempfile.TemporaryDirectory() as tempdir:
        path = Path(tempdir) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg.update({
            "DEVICE_ID": "TESTDEVICE",
            "HEADLESS_MODE": False,
            "SECOND_BATTERY_INTEGRATION_ENABLED": primary_enabled,
            "SECOND_BATTERY_SOURCE_PROFILE": "modbus_template",
            "SECOND_BATTERY_MODBUS_TEMPLATE": "sma_sunny_island",
        })
        path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        manager = ConfigManager(str(path))
        manager.load()
        yield manager


def _entries(model):
    return {
        item["key"]: item
        for category in model["categories"]
        for section in category["sections"]
        for item in section["settings"]
    }


def test_product_surface_is_explicit_and_fail_closed_for_later_target_settings():
    operational = {
        "SECOND_BATTERY_INTEGRATION_ENABLED",
        "SECOND_BATTERY_CAPACITY_WH",
        "SECOND_BATTERY_MAX_DISCHARGE_POWER_W",
    }
    target_only = {
        "HARVEST_SEASON_MODE",
        "MEASUREMENT_DB_MAINTENANCE_MODE",
        "MEASUREMENT_LOG_MAINTENANCE_MODE",
    }
    for key in operational:
        assert get_setting(key).surface_state is SurfaceState.OPERATIONAL
    for key in target_only:
        assert get_setting(key).surface_state is SurfaceState.TARGET_ONLY


def test_primary_activation_remains_visible_while_subordinate_fields_follow_applicability():
    with _manager(primary_enabled=False) as manager:
        disabled = _entries(build_settings_model(manager, {"zendure_battery_details": [{}]}))
        assert disabled["SECOND_BATTERY_INTEGRATION_ENABLED"]["available"] is True
        assert disabled["SECOND_BATTERY_INTEGRATION_ENABLED"]["applicable"] is True
        assert disabled["SECOND_BATTERY_INTEGRATION_ENABLED"]["applicability"] == Applicability.ALWAYS.value
        for key in ("SECOND_BATTERY_CAPACITY_WH", "SECOND_BATTERY_MAX_DISCHARGE_POWER_W"):
            assert disabled[key]["available"] is True
            assert disabled[key]["applicable"] is False
            assert disabled[key]["applicability_rule"] == {
                "key": "SECOND_BATTERY_INTEGRATION_ENABLED", "equals": True
            }

    with _manager(primary_enabled=True) as manager:
        enabled = _entries(build_settings_model(manager, {"zendure_battery_details": [{}]}))
        for key in ("SECOND_BATTERY_CAPACITY_WH", "SECOND_BATTERY_MAX_DISCHARGE_POWER_W"):
            assert enabled[key]["available"] is True
            assert enabled[key]["applicable"] is True
            assert enabled[key]["editable"] is True


def test_target_only_s3_s4_s6_s7_settings_stay_out_of_model_for_any_topology():
    forbidden = {
        "HARVEST_SEASON_MODE",
        "MEASUREMENT_DB_MAINTENANCE_MODE",
        "MEASUREMENT_DB_1MIN_RETENTION_MODE",
        "MEASUREMENT_LOG_MAINTENANCE_MODE",
        "MEASUREMENT_LOG_COMPRESSION_MIN_AGE_MINUTES",
    }
    for enabled in (False, True):
        for unit_count in (1, 2):
            snapshot = {"zendure_battery_details": [{} for _ in range(unit_count)]}
            with _manager(primary_enabled=enabled) as manager:
                model = build_settings_model(manager, snapshot)
                keys = set(_entries(model))
                assert forbidden.isdisjoint(keys)
                assert model["topology"]["zendure_unit_count"] == unit_count
                assert model["topology"]["primary_storage_enabled"] is enabled
                assert not any(key.startswith("SECOND_ZENDURE_") for key in keys)


def test_first_install_persistence_uses_same_surface_authority():
    cfg = dict(DEFAULT_CONFIG)
    cfg["DEVICE_ID"] = "TESTDEVICE"
    cfg["SECOND_BATTERY_INTEGRATION_ENABLED"] = True
    cfg["SECOND_BATTERY_CAPACITY_WH"] = 13000
    cfg["SECOND_BATTERY_MAX_DISCHARGE_POWER_W"] = 4600
    result = parse_full_candidate(cfg, new_install=True)
    assert not [issue for issue in result.issues if issue.blocking]
    assert result.persisted["SECOND_BATTERY_INTEGRATION_ENABLED"] is True
    assert result.persisted["SECOND_BATTERY_CAPACITY_WH"] == 13000
    assert result.persisted["SECOND_BATTERY_MAX_DISCHARGE_POWER_W"] == 4600
    assert "HARVEST_SEASON_MODE" not in result.persisted
    assert "MEASUREMENT_DB_MAINTENANCE_MODE" not in result.persisted
    assert "MEASUREMENT_LOG_MAINTENANCE_MODE" not in result.persisted


def test_browser_applicability_uses_current_draft_and_re_renders_after_toggle():
    js = (ROOT / "static/settings_v2.js").read_text(encoding="utf-8")
    assert "function applicabilityVisible(s)" in js
    assert "const value = currentValue(dep);" in js
    assert "if (!applicabilityVisible(s)) return false;" in js
    assert "scheduleRenderAfterInput();" in js
