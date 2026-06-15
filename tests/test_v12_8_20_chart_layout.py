# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import unittest

from tools.replay_report import (
    KNOWN_MQTT_EFFECT_STATES,
    KNOWN_OPERATING_STATES,
    charts_html,
    missing_chart_help_keys,
)


class V12820ChartLayoutTests(unittest.TestCase):
    def test_all_known_chart_states_have_explicit_help_text(self):
        missing = missing_chart_help_keys(KNOWN_OPERATING_STATES | KNOWN_MQTT_EFFECT_STATES)
        self.assertEqual([], missing)

    def test_hold_state_has_visible_specific_info_text(self):
        html = charts_html({
            "fair_regulator_quality": {},
            "deadband": {},
            "operating_state_matrix": [
                {"mode": "HOLD", "seconds": 106, "percent": 0.8},
            ],
            "command_efficiency": {},
        })
        self.assertIn("HOLD", html)
        self.assertIn("Allgemeiner Haltezustand", html)

    def test_chart_row_value_is_separate_from_bar_width_area(self):
        html = charts_html({
            "fair_regulator_quality": {},
            "deadband": {},
            "operating_state_matrix": [
                {"mode": "AUTO_CHARGE", "seconds": 2298, "percent": 16.7},
            ],
            "command_efficiency": {
                "improved_count": 37, "improved_percent": 27.4,
                "neutral_count": 75, "no_effect_percent": 55.6,
                "worse_count": 23, "worse_percent": 17.0,
                "unknown_count": 0,
            },
        })
        self.assertIn("class='barvalue'", html)
        self.assertIn("aria-label='AUTO_CHARGE: 38 min 18 s / 16,7 %'", html)
        self.assertLess(html.index("aria-label='AUTO_CHARGE"), html.index("38 min 18 s / 16,7 %</b>"))
        self.assertIn("Automatikbetrieb mit Ladeanforderung", html)


if __name__ == "__main__":
    unittest.main()
