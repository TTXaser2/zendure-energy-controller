# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import re
import unittest

from tools.replay_report import TERM_HELP, charts_html, high_soc_table


VERSION_REFERENCE_RE = re.compile(r"\b(?:[Ss]eit|[Aa]b)\s+V?\d+\.\d+(?:\.\d+)?|\bV\d+\.\d+(?:\.\d+)?\b")


class V12821HelpTextTests(unittest.TestCase):
    def test_chart_and_term_help_texts_describe_current_state_without_version_history(self):
        offenders = {key: text for key, text in TERM_HELP.items() if VERSION_REFERENCE_RE.search(text)}
        self.assertEqual({}, offenders)

    def test_night_discharge_help_describes_current_semantics(self):
        html = charts_html({
            "fair_regulator_quality": {},
            "deadband": {},
            "operating_state_matrix": [
                {"mode": "NIGHT_DISCHARGE", "seconds": 120, "percent": 50},
            ],
            "command_efficiency": {},
        })
        self.assertIn("Ein erreichter Nachtmodus-Reserve-SOC pausiert nur diese feste Basisentladung", html)
        self.assertNotIn("Seit V12", html)
        self.assertNotIn("Ab V12", html)

    def test_high_soc_table_has_no_version_history_in_user_visible_text(self):
        html = high_soc_table({
            "time_at_min_soc_seconds": 0,
            "time_at_max_soc_seconds": 0,
            "charge_acceptance_states": {"ok": 1},
        })
        self.assertIn("High-SOC-Ladeannahme ist eine leichte Zusatzdiagnose", html)
        self.assertIsNone(VERSION_REFERENCE_RE.search(html))


if __name__ == "__main__":
    unittest.main()
