import re
import unittest
import zipfile
from pathlib import Path

import settings_help
import settings_model
from settings_registry import SETTINGS, Visibility

ROOT = Path(__file__).resolve().parents[1]


def operational_settings():
    return [
        s for s in SETTINGS
        if s.visibility not in (Visibility.HIDDEN_MIGRATION, Visibility.HIDDEN_TRANSITION)
        and (s.release_stage == "S1" or s.origin == "RC19")
        and not s.lifecycle.startswith("remove_")
        and s.lifecycle not in ("reserved_inactive", "deployment_constant_not_config")
    ]


class V12121HelpMobileQualityTests(unittest.TestCase):
    def test_all_rich_settings_have_concrete_when_and_risk_text(self):
        rich = [s for s in operational_settings() if s.help.help_level == "rich"]
        self.assertEqual(62, len(rich))
        generic_when = "Die Einstellung wirkt nur, wenn die zugehörige Aktivierungs- oder Quellbedingung erfüllt ist."
        for spec in rich:
            self.assertTrue((spec.help.when_help or "").strip(), spec.key)
            self.assertNotEqual(generic_when, spec.help.when_help, spec.key)
            self.assertTrue((spec.help.risk_help or "").strip(), spec.key)
            self.assertNotIn("Registry-Risikoklasse", spec.help.risk_help, spec.key)

    def test_user_help_terminology_lint(self):
        banned = (
            "Registry-Risikoklasse",
            "Serververtrag",
            "Freshness-Grenze",
            "High-SOC-Eligibility",
            "Full-State-Neutralisierung",
        )
        for spec in operational_settings():
            h = spec.help
            user_texts = [
                h.short_help, h.extended_help, h.when_help, h.dependency_help,
                h.override_help, h.risk_help, h.formula_text,
                *h.search_terms, *(text for _, text in h.option_help),
            ]
            combined = " ".join(x for x in user_texts if x)
            for word in banned:
                self.assertNotIn(word.lower(), combined.lower(), f"{spec.key}: {word}")

    def test_glossary_is_modelled_and_linkable(self):
        self.assertEqual(15, settings_help.HANDBOOK_GLOSSARY.page)
        payload = settings_model._handbook_payload(settings_help.HANDBOOK_GLOSSARY)
        self.assertEqual("/manual.pdf#page=15", payload["url"])
        source = (ROOT / "settings_model.py").read_text(encoding="utf-8")
        self.assertIn('"glossary": _handbook_payload(HANDBOOK_GLOSSARY)', source)
        js = (ROOT / "static" / "settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("Begriffe & Abkürzungen", js)
        self.assertIn("app.model?.glossary", js)

    def test_default_profile_semantics_are_structured_not_concatenated(self):
        js = (ROOT / "static" / "settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("<b>Einordnung</b>", js)
        self.assertIn("<b>Verfügbare Aktion</b>", js)
        self.assertNotIn(" Verfügbare Aktion: ${s.default_ui.action}", js)

    def test_help_modal_scroll_is_reset_on_every_open(self):
        js = (ROOT / "static" / "settings_v2.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(js.count("helpBody.scrollTop = 0"), 2)
        self.assertIn("requestAnimationFrame(() => { helpBody.scrollTop = 0; })", js)

    def test_search_ranking_prioritizes_title_synonym_and_config_key(self):
        js = (ROOT / "static" / "settings_v2.js").read_text(encoding="utf-8")
        for token in (
            "score:0", "score:15", "score:20", "score:40", "score:60", "score:80",
            "Synonym", "Config-Key",
        ):
            self.assertIn(token, js)
        self.assertIn("a.match.score - b.match.score", js)

    def test_compound_validation_collapses_night_hour_minute_keys(self):
        js = (ROOT / "static" / "settings_v2.js").read_text(encoding="utf-8")
        self.assertIn("function logicalIssueTargets(keys)", js)
        self.assertIn("const id = `night:${kind}`", js)
        self.assertIn("startsWith('night:')", js)
        self.assertIn("openIssueHelp", js)
        # User-facing action labels must be logical compound labels, not component settings.
        self.assertNotIn("Start Minute</button>", js)
        self.assertNotIn("End Minute</button>", js)

    def test_status_info_popover_has_internal_scroll_and_explicit_mobile_close(self):
        js = (ROOT / "static" / "status_v2.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "status_v2.css").read_text(encoding="utf-8")
        html = (ROOT / "status_page_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("addEventListener('mouseenter'", js)
        self.assertNotIn("pop.addEventListener('mouseleave'", js)
        self.assertIn("is-mobile-panel", js)
        self.assertIn("zecInfoClose", js)
        self.assertIn("zec-info-popover-body", css)
        self.assertIn("overflow-y:auto", css)
        self.assertIn("overscroll-behavior:contain", css)
        self.assertIn('id="zecInfoClose"', html)

    def test_mobile_settings_use_internal_scroll_owner(self):
        css = (ROOT / "static" / "settings_v2.css").read_text(encoding="utf-8")
        self.assertIn("V12.12.1 mobile/iOS scroll owner", css)
        self.assertRegex(css, r"body\.zec-settings-v2\{height:100dvh;min-height:0;overflow:hidden;display:flex")
        self.assertRegex(css, r"\.settings-main\{height:100%;min-height:0;overflow-y:auto")
        self.assertIn("body.zec-settings-v2 .zec-topbar{position:relative", css)
        self.assertIn(".settings-contextbar{position:relative", css)

    def test_manual_contains_glossary_and_no_old_unexplained_terms(self):
        pdf = ROOT / "docs" / "Zendure_Energy_Controller_Handbuch.pdf"
        pages = len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes()))
        self.assertEqual(17, pages)
        docx = ROOT / "docs" / "Zendure_Energy_Controller_Handbuch.docx"
        with zipfile.ZipFile(docx) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", "ignore")
        for token in (
            "Benutzerhandbuch V12.13.0",
            "Begriffe und Abkürzungen",
            "SettingsRegistry",
            "hat nichts mit der Windows-Registry zu tun",
            "Aktualität / Datenalter",
            "Hysterese",
            "Sicherer Ausgangswert (Sentinel)",
            "Fallback / Rückfallpfad",
            "Gain / Reglerverstärkung",
            "Timeout / Zeitlimit",
        ):
            self.assertIn(token, xml)
        self.assertNotIn("Registry-Risikoklasse", xml)
        self.assertNotIn("Serververtrag", xml)

    def test_updater_accepts_v12_12_0_as_primary_source(self):
        script = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_SOURCE_V12121_VERSION="12.12.1"', script)
        self.assertIn('EXPECTED_SOURCE_V12121_BUILD_ID="v12.12.1-20260810"', script)
        self.assertIn('SOURCE_MODE="V12_12_1"', script)
        self.assertIn('EXPECTED_SOURCE_V12120_VERSION="12.12.0"', script)
        self.assertIn('EXPECTED_SOURCE_V12120_BUILD_ID="v12.12.0-20260809"', script)
        self.assertIn('SOURCE_MODE="V12_12_0"', script)
        self.assertIn('EXPECTED_TARGET_BUILD_ID="v12.13.0-20260811"', script)
        self.assertIn('EXPECTED_VERSION="v12_13_0"', script)


if __name__ == "__main__":
    unittest.main()
