import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

from config_manager import ConfigManager, DEFAULT_CONFIG
from config_validator import validate_config_semantics
from cross_charge import second_battery_mqtt_source_enabled, second_battery_topics
from primary_storage_source import (
    primary_storage_integration_enabled,
    primary_storage_source_label,
    resolved_primary_storage_display_name,
)
from settings_registry import ApplyClass, get_setting
from settings_validation import validate_candidate
from state import ControllerState
from web_ui import create_app, second_battery_name


def _endpoint(app, path, method):
    method = method.upper()
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Route {method} {path} missing")


def _request(path, *, body=None, csrf="x" * 40):
    data = json.dumps(body or {}).encode("utf-8")
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": data, "more_body": False}

    headers = [
        (b"host", b"testserver"),
        (b"origin", b"http://testserver"),
        (b"content-length", str(len(data)).encode()),
        (b"cookie", f"zec_settings_csrf={csrf}".encode()),
        (b"x-csrf-token", csrf.encode()),
    ]
    return Request({
        "type": "http", "method": "POST", "scheme": "http",
        "server": ("testserver", 80), "client": ("127.0.0.1", 1234),
        "path": path, "query_string": b"", "headers": headers,
    }, receive)


def _modbus_cfg(**overrides):
    cfg = dict(DEFAULT_CONFIG)
    cfg.update({
        "SECOND_BATTERY_INTEGRATION_ENABLED": True,
        "SECOND_BATTERY_SOURCE_PROFILE": "modbus_template",
        "SECOND_BATTERY_MODBUS_TEMPLATE": "sma_sunny_island",
        "SECOND_BATTERY_MODBUS_HOST": "192.0.2.20",
        "SECOND_BATTERY_MODBUS_PORT": 502,
        "SECOND_BATTERY_MODBUS_UNIT_ID": 3,
        "CROSS_CHARGE_ENABLED": False,
        "REST_SURPLUS_HARVEST_ENABLED": False,
    })
    cfg.update(overrides)
    return cfg


def test_registry_exposes_native_modbus_as_restart_required_source():
    source = get_setting("SECOND_BATTERY_SOURCE_PROFILE")
    assert source.apply_class is ApplyClass.RESTART_REQUIRED
    assert ("modbus_template", "Direkt per Modbus") in source.options
    for key in (
        "SECOND_BATTERY_MODBUS_TEMPLATE", "SECOND_BATTERY_MODBUS_HOST",
        "SECOND_BATTERY_MODBUS_PORT", "SECOND_BATTERY_MODBUS_UNIT_ID",
    ):
        assert get_setting(key).apply_class is ApplyClass.RESTART_REQUIRED


def test_modbus_integration_is_independent_of_cross_charge_and_has_no_mqtt_topics():
    cfg = _modbus_cfg()
    assert primary_storage_integration_enabled(cfg) is True
    assert second_battery_mqtt_source_enabled(cfg) is False
    assert second_battery_topics(cfg) == {"power": "", "soc": "", "capacity": ""}
    assert primary_storage_source_label(cfg) == "Direkt per Modbus"


def test_display_name_resolution_user_then_template_then_generic():
    cfg = _modbus_cfg(SECOND_BATTERY_DISPLAY_NAME="Hausspeicher")
    assert resolved_primary_storage_display_name(cfg) == "Hausspeicher"
    assert second_battery_name(cfg) == "Hausspeicher"
    cfg["SECOND_BATTERY_DISPLAY_NAME"] = ""
    assert resolved_primary_storage_display_name(cfg) == "SMA Sunny Island"
    cfg["SECOND_BATTERY_SOURCE_PROFILE"] = "evcc_standard"
    assert resolved_primary_storage_display_name(cfg) == "Primärspeicher"


def test_settings_validation_accepts_complete_modbus_and_blocks_missing_host():
    good = _modbus_cfg()
    assert not [i for i in validate_candidate(good) if i.code == "VAL-026"]
    bad = dict(good, SECOND_BATTERY_MODBUS_HOST="")
    issues = validate_candidate(bad)
    assert any(i.code == "VAL-026" and i.blocking for i in issues)


def test_semantic_validator_accepts_observer_mode_and_rejects_invalid_modbus_endpoint():
    good = _modbus_cfg()
    codes = {i.code for i in validate_config_semantics(good)}
    assert "SECOND_BATTERY_MODBUS_CONFIG_INVALID" not in codes
    assert "HARVEST_NEEDS_CROSS_CHARGE" not in codes
    bad = dict(good, SECOND_BATTERY_MODBUS_PORT=70000)
    codes = {i.code for i in validate_config_semantics(bad)}
    assert "SECOND_BATTERY_MODBUS_CONFIG_INVALID" in codes


def test_existing_evcc_and_custom_profiles_remain_mqtt_sources():
    evcc = dict(DEFAULT_CONFIG, SECOND_BATTERY_INTEGRATION_ENABLED=True, SECOND_BATTERY_SOURCE_PROFILE="evcc_standard")
    assert second_battery_mqtt_source_enabled(evcc) is True
    assert second_battery_topics(evcc)["power"].endswith("/power")
    custom = dict(DEFAULT_CONFIG, SECOND_BATTERY_INTEGRATION_ENABLED=True, SECOND_BATTERY_SOURCE_PROFILE="custom", SECOND_BATTERY_POWER_TOPIC="home/primary/power")
    assert second_battery_mqtt_source_enabled(custom) is True
    assert second_battery_topics(custom)["power"] == "home/primary/power"


def test_config_manager_legacy_migration_infers_integration_without_changing_source_profile():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "config.json"
        legacy = dict(DEFAULT_CONFIG)
        legacy.pop("SECOND_BATTERY_INTEGRATION_ENABLED", None)
        legacy["CROSS_CHARGE_ENABLED"] = True
        legacy["SECOND_BATTERY_SOURCE_PROFILE"] = "evcc_standard"
        path.write_text(json.dumps(legacy), encoding="utf-8")
        mgr = ConfigManager(str(path))
        loaded = mgr.load()
        assert loaded["SECOND_BATTERY_INTEGRATION_ENABLED"] is True
        assert loaded["SECOND_BATTERY_SOURCE_PROFILE"] == "evcc_standard"


def test_draft_connection_test_is_read_only_and_uses_only_allowed_draft_values():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "config.json"
        cfg = dict(DEFAULT_CONFIG)
        cfg["DEVICE_ID"] = "TESTDEVICE"
        cfg["HEADLESS_MODE"] = False
        path.write_text(json.dumps(cfg), encoding="utf-8")
        mgr = ConfigManager(str(path))
        mgr.load()
        app = create_app(mgr, ControllerState())
        route = _endpoint(app, "/settings/primary-storage-modbus-test", "POST")
        before = mgr.configured_revision()
        captured = {}

        def fake_probe(candidate):
            captured.update(candidate)
            return {
                "status": "ok", "read_only": True, "device": "SMA Sunny Island",
                "endpoint": "192.0.2.44:1502", "unit_id": 7,
                "power_w": -1234, "soc_percent": 82, "response_time_ms": 8.5,
                "function_codes": [4, 3],
            }

        body = {"draft": {
            "SECOND_BATTERY_MODBUS_TEMPLATE": "sma_sunny_island",
            "SECOND_BATTERY_MODBUS_HOST": "192.0.2.44",
            "SECOND_BATTERY_MODBUS_PORT": 1502,
            "SECOND_BATTERY_MODBUS_UNIT_ID": 7,
            "DEADBAND_W": 999,
        }}
        with patch("web_ui.probe_primary_storage_modbus", side_effect=fake_probe):
            response = asyncio.run(route(_request("/settings/primary-storage-modbus-test", body=body)))
        assert response.status_code == 200
        payload = json.loads(response.body)
        assert payload["read_only"] is True
        assert payload["runtime_unchanged"] is True
        assert payload["settings_saved"] is False
        assert captured["SECOND_BATTERY_MODBUS_HOST"] == "192.0.2.44"
        assert captured["SECOND_BATTERY_MODBUS_PORT"] == 1502
        assert captured["SECOND_BATTERY_MODBUS_UNIT_ID"] == 7
        assert captured["DEADBAND_W"] == cfg["DEADBAND_W"]
        assert mgr.configured_revision() == before


def test_settings_javascript_contains_read_only_modbus_test_contract():
    script = (Path(__file__).resolve().parents[1] / "static/settings_v2.js").read_text(encoding="utf-8")
    assert "/settings/primary-storage-modbus-test" in script
    assert "Verbindung testen" in script
    assert "read-only" in script.lower()
