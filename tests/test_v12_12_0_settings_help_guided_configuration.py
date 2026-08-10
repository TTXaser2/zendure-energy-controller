import json
import re
import unittest
from pathlib import Path

import settings_help
import settings_model
from settings_registry import (
    SETTINGS,
    SETTINGS_BY_KEY,
    DefaultClass,
    Visibility,
)

ROOT = Path(__file__).resolve().parents[1]


def operational_settings():
    out = []
    for spec in SETTINGS:
        if spec.visibility in (Visibility.HIDDEN_MIGRATION, Visibility.HIDDEN_TRANSITION):
            continue
        if spec.release_stage != "S1" and spec.origin != "RC19":
            continue
        if spec.lifecycle.startswith("remove_") or spec.lifecycle in ("reserved_inactive", "deployment_constant_not_config"):
            continue
        out.append(spec)
    return out


class V12120SettingsHelpContractTests(unittest.TestCase):
    def test_registry_help_coverage_and_depth(self):
        ops = operational_settings()
        self.assertEqual(212, len(SETTINGS))
        self.assertEqual(171, len(ops))
        self.assertEqual(12, len({s.category for s in ops}))
        self.assertEqual(69, len({(s.category, s.section) for s in ops}))
        self.assertEqual(62, sum(s.help.help_level == "rich" for s in ops))
        self.assertTrue(all(s.help.short_help.strip() for s in ops))
        self.assertTrue(all(s.help.extended_help.strip() for s in ops))
        self.assertTrue(all(s.help.handbook_ref is not None for s in ops))

    def test_category_and_section_help_complete(self):
        ops = operational_settings()
        categories = {s.category for s in ops}
        sections = {(s.category, s.section) for s in ops}
        self.assertEqual(categories, set(settings_model.CATEGORY_SPECS))
        self.assertEqual(sections, set(settings_model.SECTION_SPECS))
        self.assertTrue(all(settings_model.CATEGORY_SPECS[c].help_text.strip() for c in categories))
        self.assertTrue(all(settings_model.SECTION_SPECS[s].help_text.strip() for s in sections))

    def test_dependencies_target_existing_registry_keys(self):
        for spec in operational_settings():
            for dep in spec.help.dependencies:
                self.assertIn(dep.key, SETTINGS_BY_KEY, f"{spec.key} -> {dep.key}")
                self.assertIn(dep.relation, {
                    "REQUIRES", "ENABLES", "GATES", "LIMITS", "OVERRIDES",
                    "OVERRIDDEN_BY", "PAIRED_WITH", "SOURCE_FOR", "DIAGNOSTIC_ONLY",
                    "RESTART_COUPLED",
                })

    def test_very_high_operational_settings_have_risk_and_dependencies_or_effect_context(self):
        for spec in operational_settings():
            if spec.risk != "very_high":
                continue
            h = spec.help
            self.assertTrue(h.risk_help, spec.key)
            contextual = bool(h.dependencies or h.dependency_help or h.effect_increase or h.effect_decrease or h.effect_enable or h.effect_disable or h.option_help)
            self.assertTrue(contextual, spec.key)

    def test_default_classes_are_not_misrepresented_in_help(self):
        for spec in operational_settings():
            combined = " ".join(filter(None, [spec.help.short_help, spec.help.extended_help, spec.help.risk_help])).lower()
            if spec.default_class is DefaultClass.INSTALLATION:
                self.assertNotIn("empfohlener wert", combined, spec.key)
                self.assertNotIn("empfehlungswert", combined, spec.key)
            if spec.default_class is DefaultClass.SAFE_SENTINEL:
                self.assertNotIn("empfohlener betriebswert", combined, spec.key)
            if spec.default_class is DefaultClass.PROFILE_PRESET:
                self.assertNotIn("universeller default", combined, spec.key)

    def test_night_help_describes_fixed_power_and_reserve_followup(self):
        power = SETTINGS_BY_KEY["NIGHT_DISCHARGE_POWER_W"].help
        reserve = SETTINGS_BY_KEY["NIGHT_DISCHARGE_STOP_SOC_PERCENT"].help
        self.assertIn("nicht fortlaufend", power.extended_help)
        self.assertIn("Einspeisung", power.extended_help)
        self.assertIn("eigenen Anlage", power.extended_help)
        self.assertIn("AUTO-Regelung", reserve.extended_help)
        self.assertIn("pausiert", reserve.extended_help)

    def test_harvest_help_preserves_entry_and_override_semantics(self):
        rest = SETTINGS_BY_KEY["REST_SURPLUS_MIN_EXPORT_W"].help
        ratio = SETTINGS_BY_KEY["HARVEST_PRIMARY_CHARGE_FLOOR_RATIO"].help
        absolute = SETTINGS_BY_KEY["HARVEST_PRIMARY_CHARGE_FLOOR_W"].help
        self.assertIn("Eintrittsschwelle", rest.short_help)
        self.assertIn("kein gewünschter", rest.short_help)
        self.assertIn("OVERRIDDEN_BY", {d.relation for d in ratio.dependencies})
        self.assertIn("übersteuert", ratio.override_help)
        self.assertIn("OVERRIDES", {d.relation for d in absolute.dependencies})
        self.assertIn("Floor <= Restart <= Near-Limit <=", ratio.formula_text)

    def test_auto_formula_and_example_are_deterministic(self):
        gain = SETTINGS_BY_KEY["CONTROL_GAIN"].help
        smoothing = SETTINGS_BY_KEY["SMOOTHING_FACTOR"].help
        self.assertEqual("raw_target = previous_target + effective_grid_deviation × CONTROL_GAIN", gain.formula_text)
        self.assertEqual("rohes Ziel = 750 W", gain.example.result)
        self.assertIn("old × (1 - factor) + target × factor", smoothing.formula_text)

    def test_cross_charge_help_matches_current_positive_contract_and_hysteresis(self):
        spec = SETTINGS_BY_KEY["CROSS_CHARGE_SIGNIFICANT_W"]
        self.assertIn("größer als 0 W", spec.help.short_help)
        self.assertIn("max(20 W, engage_threshold / 2)", spec.help.formula_text)
        self.assertNotIn("0 bedeutet", spec.validation_text)

    def test_command_help_separates_publish_threshold_and_tracking(self):
        min_target = SETTINGS_BY_KEY["COMMAND_EFFECT_MIN_TARGET_W"].help
        tol_w = SETTINGS_BY_KEY["COMMAND_EFFECT_TOLERANCE_W"].help
        tol_pct = SETTINGS_BY_KEY["COMMAND_EFFECT_TOLERANCE_PERCENT"].help
        category = settings_model.CATEGORY_SPECS["Kommandowirkung & Resync"].help_text
        combined = " ".join((min_target.short_help, min_target.extended_help, tol_w.formula_text or "", tol_pct.formula_text or "", category)).lower()
        self.assertIn("diagnose", combined)
        self.assertIn("keine mindestleistung des geräts", combined)
        self.assertIn("max(", combined)
        self.assertIn("publish", combined)
        self.assertIn("kein", combined)

    def test_search_terms_include_required_synonyms(self):
        deadband = {x.lower() for x in SETTINGS_BY_KEY["DEADBAND_W"].help.search_terms}
        self.assertTrue({"deadband", "totzone", "nullzone"}.issubset(deadband))

    def test_model_projects_redaction_safe_help_and_validator_ids(self):
        source = (ROOT / "settings_model.py").read_text(encoding="utf-8")
        self.assertIn('"validator_ids": list(spec.validator_ids)', source)
        self.assertIn('"help": _help_payload(spec)', source)
        # Help payload itself must never project a configured secret value.
        payload = settings_model._help_payload(SETTINGS_BY_KEY["MQTT_PASSWORD"])
        self.assertNotIn("configured", payload)
        self.assertNotIn("effective", payload)

    def test_handbook_refs_point_to_existing_verified_page_range(self):
        pdf = ROOT / "docs" / "Zendure_Energy_Controller_Handbuch.pdf"
        self.assertTrue(pdf.is_file())
        data = pdf.read_bytes()
        pages = len(re.findall(rb"/Type\s*/Page\b", data))
        self.assertEqual(17, pages)
        for spec in operational_settings():
            ref = spec.help.handbook_ref
            self.assertGreaterEqual(ref.page, 1)
            self.assertLessEqual(ref.page, pages)
            self.assertEqual(f"/manual.pdf#page={ref.page}", settings_model._handbook_payload(ref)["url"])

    def test_current_generic_manual_has_no_old_house_specific_pseudodefaults(self):
        # Search DOCX XML because PDF text encoding is implementation-specific.
        import zipfile
        docx = ROOT / "docs" / "Zendure_Energy_Controller_Handbuch.docx"
        with zipfile.ZipFile(docx) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", "ignore")
        self.assertNotIn("192.168.0.40", xml)
        self.assertNotIn("MAX_CHARGE_POWER_W = 2100", xml)
        self.assertNotIn("MAX_DISCHARGE_POWER_W = 2100", xml)
        self.assertIn("Benutzerhandbuch V12.12.1", xml)

    def test_ui_contains_help_modal_search_guidance_and_preview_help_contract(self):
        js = (ROOT / "static" / "settings_v2.js").read_text(encoding="utf-8")
        html = (ROOT / "web_ui.py").read_text(encoding="utf-8")
        css = (ROOT / "static" / "settings_v2.css").read_text(encoding="utf-8")
        for token in ("openSettingHelp", "openCategoryHelp", "openSectionHelp", "categoryGuidance", "data-issue-help", "effective_source", "search_terms"):
            self.assertIn(token, js)
        self.assertIn('id="helpModal"', html)
        self.assertIn('aria-modal="true"', html)
        self.assertIn("help-backdrop", css)
        self.assertIn("body.help-open", css)

    def test_guidance_thresholds_are_existing_specified_thresholds(self):
        js = (ROOT / "static" / "settings_v2.js").read_text(encoding="utf-8")
        for snippet in (
            "n('DEADBAND_W') < 20", "n('CONTROL_GAIN') > .5", "n('MAX_POWER_STEP_W') > 300",
            "n('MOVING_AVERAGE_SAMPLES') > 30", "n('INTERVAL_SECONDS') <= 1",
            "n('SMOOTHING_FACTOR') >= .8", "n(key) < 2*interval", "n(key) > 180",
            "n('SECOND_BATTERY_STALE_TIMEOUT_SECONDS') < 5",
            "n('ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS') >= .75*interval",
        ):
            self.assertIn(snippet, js)


if __name__ == "__main__":
    unittest.main()
