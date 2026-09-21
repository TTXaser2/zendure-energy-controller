from __future__ import annotations

from datetime import datetime as RealDateTime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

import web_ui
from settings_registry import get_setting
from tools.v16_field_acceptance import _expected_update_source
from web_ui import build_status_view_payload
from status_page_v2 import render_status_page_v2
from version import APP_BUILD_ID, APP_VERSION, APP_VERSION_LABEL

ROOT = Path(__file__).resolve().parents[1]


def _cfg(**overrides):
    cfg = {
        "MAX_SOC_PERCENT": 99,
        "MIN_SOC_PERCENT": 10,
        "ZENDURE_BATTERY_CAPACITY_WH": 5000,
        "MAX_CHARGE_POWER_W": 2400,
        "MAX_DISCHARGE_POWER_W": 2100,
        "SECOND_BATTERY_INTEGRATION_ENABLED": True,
        "SECOND_BATTERY_SOURCE_PROFILE": "modbus_template",
        "SECOND_BATTERY_MODBUS_TEMPLATE": "sma_sunny_island",
        "SECOND_BATTERY_DISPLAY_NAME": "SMA Sunny Island",
        "SECOND_BATTERY_CAPACITY_WH": 13000,
        "SECOND_BATTERY_MAX_CHARGE_POWER_W": 4600,
        "SECOND_BATTERY_MAX_DISCHARGE_POWER_W": 4600,
    }
    cfg.update(overrides)
    return cfg


def _snap(zendure_power=1200, primary_power=2300):
    return {
        "battery_soc": 50,
        "zendure_system_signed_power": zendure_power,
        "actual_zendure_system_signed_power": zendure_power,
        "sma_battery_soc": 60,
        "sma_battery_display_power": primary_power,
        "second_battery_data_valid": True,
        "second_battery_data_fresh": True,
        "primary_storage_current_discharge_floor_supported": True,
        "primary_storage_current_discharge_floor_soc_percent": 20,
        "primary_storage_current_discharge_floor_valid": True,
        "primary_storage_current_discharge_floor_fresh": True,
        "primary_storage_usable_soc_percent": 50,
        "primary_storage_usable_soc_valid": True,
    }


def test_release_identity_is_v16_2_3():
    assert (APP_VERSION, APP_VERSION_LABEL, APP_BUILD_ID) == ("16.2.3", "V16.2.3", "v16.2.3-20260921")


def test_directional_remaining_energy_and_power_bars_charge():
    payload = build_status_view_payload(_cfg(), _snap())
    z = payload["zendure"]
    p = payload["primary"]
    assert z["remaining_label"] == "Noch ladbar"
    assert z["remaining"] == pytest.approx(2.45)
    assert z["remaining_text"] == "49 % · 2,45 kWh"
    assert z["soc_limit_label"] == "Ladegrenze"
    assert z["soc_limit_text"] == "99 %"
    assert z["power_meter_direction"] == "charge"
    assert z["power_meter_percent"] == pytest.approx(50.0)
    assert z["power_meter_text"] == "1,20 kW / 2,40 kW max"
    assert p["remaining_label"] == "Noch ladbar"
    assert p["remaining_text"] == "40 % · 5,20 kWh"
    assert p["power_meter_direction"] == "charge"
    assert p["power_meter_percent"] == pytest.approx(50.0)
    assert p["power_meter_text"] == "2,30 kW / 4,60 kW max"


def test_directional_remaining_energy_and_power_bars_discharge():
    payload = build_status_view_payload(_cfg(), _snap(zendure_power=-1050, primary_power=-2300))
    z = payload["zendure"]
    p = payload["primary"]
    assert z["remaining_label"] == "Noch entladbar"
    assert z["remaining_text"] == "40 % · 2,00 kWh"
    assert z["soc_limit_label"] == "Entladegrenze"
    assert z["soc_limit_text"] == "10 %"
    assert z["power_meter_direction"] == "discharge"
    assert z["power_meter_percent"] == pytest.approx(50.0)
    assert z["power_meter_text"] == "1,05 kW / 2,10 kW max"
    assert p["remaining_label"] == "Noch entladbar"
    assert p["remaining_text"] == "40 % · 5,20 kWh"
    assert p["soc_limit_label"] == "Entladegrenze"
    assert p["soc_limit_text"] == "20 %"
    assert p["power_meter_direction"] == "discharge"
    assert p["power_meter_percent"] == pytest.approx(50.0)
    assert p["power_meter_text"] == "2,30 kW / 4,60 kW max"
    assert z["actual"] == "−1,05 kW"
    assert p["actual"] == "−2,30 kW"


def test_missing_primary_metadata_disables_only_affected_status_elements():
    cfg = _cfg(SECOND_BATTERY_CAPACITY_WH=None, SECOND_BATTERY_MAX_DISCHARGE_POWER_W=None)
    snap = _snap(primary_power=-2300)
    snap["second_battery_capacity_kwh"] = None
    payload = build_status_view_payload(cfg, snap)["primary"]
    assert payload["remaining_visible"] is True
    assert payload["power_meter_visible"] is False
    assert payload["remaining_text"] == "40 %"
    assert payload["discharge_floor_text"] == "20 %"
    assert payload["usable_soc_text"].startswith("50 %")


def test_primary_runtime_capacity_precedes_manual_fallback():
    snap = _snap(primary_power=2300)
    snap["second_battery_capacity_kwh"] = 10.0
    payload = build_status_view_payload(_cfg(SECOND_BATTERY_CAPACITY_WH=13000), snap)["primary"]
    assert payload["capacity_kwh"] == 10.0
    assert payload["remaining_text"] == "40 % · 4,00 kWh"


def test_new_primary_technical_settings_are_optional_and_diagnostic():
    cap = get_setting("SECOND_BATTERY_CAPACITY_WH")
    discharge = get_setting("SECOND_BATTERY_MAX_DISCHARGE_POWER_W")
    assert cap.default_new_install is None and cap.minimum == 100 and cap.maximum == 100000
    assert discharge.default_new_install is None and discharge.minimum == 300 and discharge.maximum == 10000
    assert discharge.label == "Maximale Entladeleistung Primärspeicher"
    assert "keine Reglerwirkung" in cap.apply_text
    assert "keine Reglerwirkung" in discharge.apply_text


def test_storage_cards_share_common_standard_information_contract():
    cfg = _cfg(UI_MODE="standard")
    payload = build_status_view_payload(cfg, _snap(zendure_power=-1050, primary_power=-2300))
    html = render_status_page_v2(cfg, payload, analysis_available=False, analysis_port=8081)
    assert html.count('class="zec-detail-row zec-actual-row"') == 2
    assert 'data-zec="zendure.soc_limit_label">Entladegrenze<' in html
    assert 'data-zec="primary.soc_limit_label">Entladegrenze<' in html
    assert 'data-zec-row="primary.usable_soc"' not in html
    assert 'SMA Entlade-Untergrenze</span>' not in html
    assert 'data-storage-expert="primary"' not in html


def test_primary_strategy_remains_available_through_expert_info_without_card_overflow_rows():
    cfg = _cfg(UI_MODE="expert")
    payload = build_status_view_payload(cfg, _snap())
    payload["primary"]["line"] = "Speicherstrategie: Primärspeicher hat Vorrang"
    payload["primary"]["harvest_calculation"] = "0-W-Netzziel: Test"
    html = render_status_page_v2(cfg, payload, analysis_available=False, analysis_port=8081)
    assert 'data-storage-expert="primary"' in html
    assert 'Harmonisierung:' in html
    assert 'Harvest-Rechnung:' in html
    assert 'class="zec-detail-row zec-harmony-row' not in html
    assert 'data-zec="primary.harvest_calculation"' not in html


def test_status_css_top_aligns_storage_and_has_directional_power_meter():
    css = (ROOT / "static/status_v2.css").read_text(encoding="utf-8")
    assert ".zec-storage-layout{display:grid" in css
    assert "align-items:start" in css
    assert ".zec-power-meter.is-discharge .zec-power-meter-track{justify-content:flex-end}" in css
    assert ".zec-power-meter.is-discharge .zec-power-meter-track i{background:var(--zec-amber)}" in css
    assert ".zec-detail-row.zec-actual-row" in css
    assert "font-size:17px" in css


def test_mobile_settings_commit_bar_stays_fixed_after_search_edit():
    css = (ROOT / "static/settings_v2.css").read_text(encoding="utf-8")
    js = (ROOT / "static/settings_v2.js").read_text(encoding="utf-8")
    assert "V16.2.0 mobile search/edit commit-bar hardening" in css
    assert "z-index:160!important" in css
    assert "safe-area-inset-bottom" in css
    assert "body.zec-settings-v2.search-open .save-bar" in css
    assert "document.body.classList.remove('search-open')" in js


def test_client_soc_day_cache_rejects_today_role_mismatch_and_now_is_conditional():
    js = (ROOT / "static/status_v2.js").read_text(encoding="utf-8")
    assert "zec:soc-day:v16.2" in js
    assert "Boolean(payload?.is_today)!==roleToday" in js
    assert "if(p.is_today)entries.push" in js
    assert "if(p.is_today){const now=new Date()" in js


def test_server_day_cache_identity_contains_today_history_role():
    source = (ROOT / "web_ui.py").read_text(encoding="utf-8")
    assert 'day_role = "today" if is_today else "history"' in source
    assert "|{day_role}" in source
    assert 'bool(entry.get("payload", {}).get("is_today")) != is_today' in source


def test_midnight_rebuilds_previous_day_instead_of_reusing_partial_today_cache():
    cfg = {"STATUS_PRIMARY_STORAGE_PRESENT": False}
    snap = {"battery_soc": 50, "zendure_system_signed_power": 0, "current_mode": "AUTO"}
    calls = []

    class BeforeMidnight(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 20, 23, 50, 0)

    class AfterMidnight(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 21, 0, 5, 0)

    def fake_history(_cfg, day_start, _day_end, **_kwargs):
        calls.append(day_start.date().isoformat())
        return {
            "points": [{"minute": 60, "time": "01:00", "zendure_soc": 50}],
            "source": "graph_core_v3_1min",
            "runtime": {"read_mode": "V3_NATIVE"},
            "zendure_unit_count": 1,
            "unit_labels": ["Zendure"],
            "primary_storage_present": False,
            "available_from": "2026-09-20",
            "available_to": "2026-09-21",
            "config_segments": [], "config_timeline": {},
        }

    with web_ui._storage_day_lock:
        web_ui._storage_day_cache.clear(); web_ui._storage_day_cache_entries.clear()
    with patch("web_ui.graph_history_runtime_status", return_value={"read_mode": "V3_NATIVE"}), \
         patch("web_ui.query_storage_day_history", side_effect=fake_history), \
         patch("web_ui.datetime", BeforeMidnight):
        first = web_ui.build_storage_soc_day_payload(cfg, snap, "2026-09-20")
    assert first["is_today"] is True and first["cache_status"] == "rebuilt"

    with patch("web_ui.graph_history_runtime_status", return_value={"read_mode": "V3_NATIVE"}), \
         patch("web_ui.query_storage_day_history", side_effect=fake_history), \
         patch("web_ui.datetime", AfterMidnight):
        second = web_ui.build_storage_soc_day_payload(cfg, snap, "2026-09-20")
    assert second["is_today"] is False
    assert second["cache_status"] == "rebuilt"
    assert calls == ["2026-09-20", "2026-09-20"]


def test_field_tool_derives_supported_update_source_from_installer_contract():
    assert _expected_update_source() == {"version": "16.2.0", "build_id": "v16.2.0-20260920"}
