"""User-facing S3 help is grounded in the deployed control/activation contracts."""
from pathlib import Path

from settings_help import S3_USER_GUIDANCE, build_section_specs
from settings_registry import iter_operational_settings

ROOT = Path(__file__).resolve().parents[1]


def test_s3_help_explains_actual_control_relationships():
    registry = {spec.key: spec for spec in iter_operational_settings()}
    assert len(S3_USER_GUIDANCE) == 11
    for key, texts in S3_USER_GUIDANCE.items():
        assert key in registry
        help_ = registry[key].help
        for field in ('short', 'purpose', 'when'):
            assert len(texts[field]) >= (70 if field == "when" else 105), f'{key}.{field} cannot be a generic placeholder'
            assert 'Konfiguration für' not in texts[field]
        assert help_.short_help == texts['short']
        assert help_.extended_help == texts['purpose']
        assert help_.when_help == texts['when']


def test_s3_activation_and_strategy_retain_separate_effects():
    registry = {spec.key: spec for spec in iter_operational_settings()}
    on = registry['HARVEST_SEASON_POLICY_ENABLED'].help
    mode = registry['HARVEST_SEASON_MODE'].help
    assert 'bisherige' in on.effect_disable.lower()
    assert 'Restüberschuss' in on.extended_help
    assert 'Tagesprofile' in on.extended_help
    assert {k for k, _ in mode.option_help} == {'parallel', 'sma_priority', 'calendar'}
    assert all(len(text) >= 70 for _, text in mode.option_help)


def test_s3_sections_have_visible_explanations_in_the_ui():
    sections = build_section_specs([
        ('Harvest / Restüberschuss', 'Saisonale Strategie'),
        ('Harvest / Restüberschuss', 'Tagesprofile'),
    ])
    for s in sections.values():
        assert len(s.help_text) >= 190
        assert 'zusammengehörige Parameter' not in s.help_text
    js = (ROOT / 'static/settings_v2.js').read_text()
    css = (ROOT / 'static/settings_v2.css').read_text()
    assert 'section-purpose' in js and 'section-purpose' in css
    assert 'Wozu dient diese Einstellung?' in js
    assert 'help-level rich' not in js
