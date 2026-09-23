from __future__ import annotations

from pathlib import Path

from state import ControllerState
from status_page_v2 import render_status_page_v2
from web_ui import build_status_view_payload

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
        "SECOND_BATTERY_MAX_DISCHARGE_POWER_W": 2300,
        "UI_MODE": "standard",
    }
    cfg.update(overrides)
    return cfg


def _snap(**overrides):
    snap = {
        "battery_soc": 63,
        "zendure_system_signed_power": -399,
        "actual_zendure_system_signed_power": -399,
        "sma_battery_soc": 55,
        "sma_battery_display_power": -180,
        "second_battery_data_valid": True,
        "second_battery_data_fresh": True,
        "primary_storage_current_discharge_floor_supported": True,
        "primary_storage_current_discharge_floor_soc_percent": 20,
        "primary_storage_current_discharge_floor_valid": True,
        "primary_storage_current_discharge_floor_fresh": True,
        "primary_storage_usable_soc_percent": 43.75,
        "primary_storage_usable_soc_valid": True,
    }
    snap.update(overrides)
    return snap


def test_storage_remaining_is_a_right_hand_detail_row_and_meter_stays_left():
    payload = build_status_view_payload(_cfg(), _snap())
    html = render_status_page_v2(_cfg(), payload, analysis_available=False, analysis_port=8081)

    z_layout = html.index('<div class="zec-storage-layout zec-storage-layout-single">')
    z_meter = html.index('data-zec-row="zendure.power_meter"', z_layout)
    z_details = html.index('<div class="zec-storage-details">', z_layout)
    z_remaining = html.index('data-zec-row="zendure.remaining"', z_layout)
    assert z_meter < z_details < z_remaining
    assert 'class="zec-detail-row zec-remaining-row" data-zec-row="zendure.remaining"' in html
    assert 'class="zec-detail-row zec-remaining-row" data-zec-row="primary.remaining"' in html
    assert 'class="zec-remaining-metric"' not in html


def test_storage_cards_use_auto_height_readable_meter_and_height_neutral_warning_chip():
    css = (ROOT / "static/status_v2.css").read_text(encoding="utf-8")
    assert ".zec-card.zec-zendure-card,.zec-card.zec-primary-card{height:auto;min-height:300px;overflow:visible}" in css
    assert ".zec-power-meter-head{flex-direction:column;align-items:flex-start" in css
    assert ".zec-warning-chip{height:24px" in css
    assert ".zec-info-popover.is-warning-panel" in css
    assert ".zec-inline-warning summary{" not in css

    snap = _snap(
        command_effect_state_category="COMMAND_CHARGE_ACCEPTANCE_LIMITED",
        command_effect_state_reason="HIGH_SOC_CHARGE_LIMITED: reale Ladeleistung bleibt deutlich unter Soll.",
    )
    payload = build_status_view_payload(_cfg(), snap)
    assert payload["zendure"]["command_warning_title"] == "Ladeannahme begrenzt"
    html = render_status_page_v2(_cfg(), payload, analysis_available=False, analysis_port=8081)
    assert '<button type="button" class="zec-warning-chip" data-zec-warning="zendure"' in html
    assert 'data-info-title="Ladeannahme begrenzt"' in html
    assert 'data-info-text="HIGH_SOC_CHARGE_LIMITED:' in html
    assert '<details class="zec-inline-warning"' not in html
    header = html[html.index('<article class="zec-card zec-zendure-card"'):html.index('{primary_card}') if '{primary_card}' in html else html.index('data-card="source"')]
    assert header.index('class="zec-warning-chip"') < header.index('{zendure_body}') if '{zendure_body}' in header else True


def test_status_js_keeps_warning_chip_live_and_reuses_non_layout_popover():
    js = (ROOT / "static/status_v2.js").read_text(encoding="utf-8")
    assert 'const zwChip = $(\'[data-zec-warning="zendure"]\');' in js
    assert "zwChip.dataset.infoTitle = zwTitle" in js
    assert "zwChip.dataset.infoText = zwText" in js
    assert "$$('.zec-info-button,.zec-warning-chip')" in js
    assert "pop.classList.toggle('is-warning-panel'" in js
    assert "infoPopoverController=setupInfoPopovers()" in js


def test_controller_state_snapshot_carries_productive_instance_owner_evidence():
    state = ControllerState()
    state.instance_owner_active = True
    state.instance_owner_pid = 4242
    state.instance_owner_build_id = "v17.0.1-test"
    state.instance_owner_since_utc = "2026-09-22T00:00:00Z"
    state.instance_owner_lock_path = "/opt/zendure-controller/zendure_controller.instance.lock"

    snap = state.snapshot()
    assert snap["instance_owner_active"] is True
    assert snap["instance_owner_pid"] == 4242
    assert snap["instance_owner_build_id"] == "v17.0.1-test"
    assert snap["instance_owner_since_utc"] == "2026-09-22T00:00:00Z"
    assert snap["instance_owner_lock_path"].endswith("zendure_controller.instance.lock")

    payload = build_status_view_payload(_cfg(), snap)
    assert payload["diag"]["instance_owner_active"] is True
    assert payload["diag"]["instance_owner_pid"] == 4242
    assert payload["diag"]["instance_owner_build_id"] == "v17.0.1-test"


def test_mobile_settings_contract_prevents_unreachable_horizontal_content():
    css = (ROOT / "static/settings_v2.css").read_text(encoding="utf-8")
    assert "V16.2.5 mobile Settings: no unreachable horizontal content" in css
    assert "touch-action:pan-y pinch-zoom" in css
    assert "body.zec-settings-v2 .setting-control{grid-template-columns:minmax(0,1fr)}" in css
    assert "body.zec-settings-v2 .unit{min-width:0;width:max-content;max-width:100%" in css
    assert "body.zec-settings-v2 .field-issue" in css
    assert "overflow-wrap:anywhere" in css
