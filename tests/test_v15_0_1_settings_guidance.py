from pathlib import Path

from settings_help import CATEGORY_HELP_TEXT, SECTION_ORDER_OVERRIDES
from settings_registry import get_setting

ROOT = Path(__file__).resolve().parents[1]


def text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_primary_storage_sections_guide_active_source_immediately_after_selector():
    order = SECTION_ORDER_OVERRIDES["Primärspeicher & SMA"]
    assert order[:6] == (
        "Integration & Status",
        "Integration & Identität",
        "Anbindung",
        "Gerät & Verbindung · Modbus",
        "MQTT-Datenquelle · EVCC Standard",
        "MQTT-Datenquelle · Benutzerdefiniert",
    )
    assert "modbus" in CATEGORY_HELP_TEXT["Primärspeicher & SMA"].lower()
    assert "Verbindungsparameter" in CATEGORY_HELP_TEXT["Primärspeicher & SMA"]


def test_modbus_template_is_presented_as_device_model_without_changing_key_or_contract():
    template = get_setting("SECOND_BATTERY_MODBUS_TEMPLATE")
    host = get_setting("SECOND_BATTERY_MODBUS_HOST")
    port = get_setting("SECOND_BATTERY_MODBUS_PORT")
    unit = get_setting("SECOND_BATTERY_MODBUS_UNIT_ID")
    assert template.label == "Gerät / Modell"
    assert template.section == "Gerät & Verbindung · Modbus"
    assert host.section == template.section
    assert port.section == template.section
    assert unit.section == template.section
    assert template.options == (("sma_sunny_island", "SMA Sunny Island"),)
    assert template.apply_class.value == "restart_required"
    assert port.visibility.value == "expert"
    assert unit.visibility.value == "expert"


def test_settings_ui_has_contextual_source_guide_and_direct_jump():
    js = text("static/settings_v2.js")
    assert "function primarySourceGuideHtml()" in js
    assert "Direkt per Modbus ausgewählt" in js
    assert "Noch erforderlich:" in js
    assert "Port und Unit-ID sind Geräteprofil-Defaults" in js
    assert 'data-primary-source-jump=' in js
    assert "Zu den Quellen-Einstellungen" in js
    assert "targetForSettingKey(key)" in js
    assert "Verbindung testen" in js
    assert "ausschließlich lesend" in js


def test_source_guide_covers_evcc_custom_and_modbus_without_new_config_keys():
    js = text("static/settings_v2.js")
    assert "EVCC ausgewählt" in js
    assert "Benutzerdefiniertes MQTT ausgewählt" in js
    assert "Direkt per Modbus ausgewählt" in js
    assert "SECOND_BATTERY_EVCC_BASE_TOPIC" in js
    assert "SECOND_BATTERY_POWER_TOPIC" in js
    assert "SECOND_BATTERY_SOC_TOPIC" in js
    assert "SECOND_BATTERY_MODBUS_HOST" in js


def test_dark_mode_fixes_discard_button_and_preview_issue_contrast():
    css = text("static/settings_v2.css")
    dark = 'html[data-theme="dark"] body.zec-settings-v2'
    assert f"{dark} .discard-btn" in css
    assert "background:var(--panel2)" in css
    assert f"{dark} .field-issue.error" in css
    assert f"{dark} .field-issue.warning" in css
    assert f"{dark} .issue-list li.error" in css
    assert f"{dark} .issue-list li.warning" in css
    assert "#fecaca" in css
    assert "#fde68a" in css


def test_help_explains_device_profiles_are_release_managed_not_user_registers():
    help_py = text("settings_help.py")
    assert "Weitere Geräteprofile werden versioniert mit ZEC-Releases ausgeliefert" in help_py
    assert "Register sind nicht frei editierbar" in help_py
