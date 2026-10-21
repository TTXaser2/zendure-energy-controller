"""Release-blocking inventory: no operational help may fall back to a key/name placeholder."""
from settings_registry import iter_operational_settings
from settings_model import SECTION_SPECS
from settings_help import SHORT_HELP, S3_USER_GUIDANCE, PRIMARY_HELP_VNEXT, SECTION_PURPOSE_VNEXT


def test_every_operational_setting_has_authored_short_explanation():
    rows = tuple(iter_operational_settings())
    assert len(rows) >= 190
    for spec in rows:
        assert spec.key in SHORT_HELP or spec.key in S3_USER_GUIDANCE or spec.key in PRIMARY_HELP_VNEXT, spec.key
        assert 'Konfiguration für' not in spec.help.short_help
        assert len(spec.help.short_help) >= 45, spec.key


def test_every_section_has_real_user_facing_purpose():
    assert len(SECTION_SPECS) >= 74
    for key, section in SECTION_SPECS.items():
        assert key in SECTION_PURPOSE_VNEXT, key
        assert section.help_text == SECTION_PURPOSE_VNEXT[key]
        assert len(section.help_text) >= 90, key
        for boilerplate in ('zusammengehörige Parameter', 'Die Detailhilfe', 'Konfiguration für'):
            assert boilerplate not in section.help_text, key


def test_s3_and_primary_new_purpose_text_is_not_auto_generated():
    for spec in iter_operational_settings():
        if spec.key not in S3_USER_GUIDANCE and spec.key not in PRIMARY_HELP_VNEXT:
            continue
        assert 'Wirksamkeit nach Speichern:' not in spec.help.extended_help
        assert len(spec.help.extended_help) >= 145, spec.key


def test_reviewed_primary_and_storage_purposes_avoid_generic_technical_fallback():
    from settings_help import EXPLICIT_PURPOSE_VNEXT
    registry = {s.key:s for s in iter_operational_settings()}
    assert len(EXPLICIT_PURPOSE_VNEXT) >= 44
    for key, purpose in EXPLICIT_PURPOSE_VNEXT.items():
        assert key in registry
        assert len(purpose) >= 190, key
        assert registry[key].help.extended_help == purpose
        assert 'Wirksamkeit nach Speichern:' not in purpose


def test_interface_purposes_explain_source_priority_and_safety_without_generic_fallback():
    from settings_help import INTERFACE_PURPOSE_VNEXT
    rows = {s.key: s for s in iter_operational_settings()}
    keys = {s.key for s in rows.values() if s.category == 'Schnittstellen & Datenquellen'}
    assert set(INTERFACE_PURPOSE_VNEXT) == keys
    for key, purpose in INTERFACE_PURPOSE_VNEXT.items():
        assert len(purpose) >= 185, key
        assert rows[key].help.extended_help == purpose
        assert 'Wirksamkeit nach Speichern:' not in purpose


def test_all_operational_setting_purposes_are_individually_authored():
    from settings_help import (S3_USER_GUIDANCE, PRIMARY_HELP_VNEXT, EXPLICIT_PURPOSE_VNEXT,
        INTERFACE_PURPOSE_VNEXT, SYSTEM_PURPOSE_VNEXT, RICH_EXTENDED)
    authors = (S3_USER_GUIDANCE, PRIMARY_HELP_VNEXT, EXPLICIT_PURPOSE_VNEXT,
        INTERFACE_PURPOSE_VNEXT, SYSTEM_PURPOSE_VNEXT, RICH_EXTENDED)
    rows = tuple(iter_operational_settings())
    for row in rows:
        assert sum(row.key in mapping for mapping in authors) == 1, row.key
        purpose = row.help.extended_help
        assert len(purpose) >= 110, row.key
        assert 'Wirksamkeit nach Speichern:' not in purpose, row.key
        assert 'Konfiguration für' not in purpose, row.key
    assert len(rows) == 190

def test_no_placeholder_applicability_in_help_dialog():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / 'static/settings_v2.js').read_text()
    assert 'Die Einstellung wirkt gemäß der unten angegebenen Wirksamkeitsart' not in js
    assert 'Die Einstellung wirkt nur, wenn die zugehörige Aktivierungs-' not in js
    assert 'Saisonale Ladeverteilung' in (Path(__file__).resolve().parents[1] / 'settings_help.py').read_text()
