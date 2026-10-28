"""Battery Care compact card: dispatched intent != independently confirmed effect."""
import unittest

from state import ControllerState
from web_ui import build_status_view_payload
from status_page_v2 import render_status_page_v2


class CareCompactCardTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "MIN_SOC_PERCENT": 10, "MAX_SOC_PERCENT": 99,
            "MAX_CHARGE_POWER_W": 2400, "MAX_DISCHARGE_POWER_W": 2400,
            "SECOND_BATTERY_INTEGRATION_ENABLED": False,
            "MANUAL_MODE": "AUTO", "UI_MODE": "standard",
        }
        self.snap = {"battery_soc": 17, "current_mode": "AUTO",
                     "zendure_system_signed_power": 0}

    def payload(self, **kwargs):
        return build_status_view_payload(self.cfg, {**self.snap, **kwargs}, events=[])

    def test_hidden_with_default_off_and_out_of_season(self):
        for snap in (
            {},
            {"care_in_season": False, "care_policy_valid": True},
            {"care_in_season": True, "care_policy_valid": False},
        ):
            with self.subTest(snapshot=snap):
                care = self.payload(**snap)["zendure"]["care"]
                self.assertFalse(care["visible"])

    def test_valid_active_policy_is_only_protected_reserve(self):
        care = self.payload(care_in_season=True, care_policy_valid=True)["zendure"]["care"]
        self.assertTrue(care["visible"])
        self.assertEqual("Reserve geschützt", care["title"])
        self.assertNotIn("wirksam", care["detail"].lower())

    def test_calendar_visible_but_not_misreported_as_effective_in_stop(self):
        self.cfg.update(BATTERY_CARE_ENABLED=True,
                        BATTERY_CARE_SEASON_START_MM_DD="01-01",
                        BATTERY_CARE_SEASON_END_MM_DD="12-31",
                        BATTERY_CARE_RESERVE_SOC_PERCENT=22,
                        BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT=18,
                        BATTERY_CARE_EMERGENCY_SOC_PERCENT=14,
                        BATTERY_CARE_GRID_CHARGE_MAX_POWER_W=250,
                        MANUAL_MODE="STOP_HOLD")
        care = self.payload(care_in_season=False, care_policy_valid=False)["zendure"]["care"]
        self.assertTrue(care["visible"])
        self.assertEqual("Derzeit ausgesetzt", care["title"])
        self.assertEqual("Manueller Modus hat Vorrang", care["detail"])

    def test_only_command_owner_can_claim_dispatch(self):
        base = self.payload(care_pv_shadow_extra_w=900)
        self.assertFalse(base["zendure"]["care"]["visible"])
        for stage, expected in (
            ("PV_PRIORITY_REQUESTED", "PV-Vorrang angefordert"),
            ("GRID_REQUESTED", "Netzpflege angefordert"),
            ("EMERGENCY_REQUESTED", "Notladung angefordert"),
        ):
            with self.subTest(stage=stage):
                care = self.payload(care_dispatched_stage=stage, care_dispatched_target_w=400)["zendure"]["care"]
                self.assertEqual(expected, care["title"])
                self.assertEqual("Wirkung noch nicht bestätigt", care["detail"])
                self.assertEqual(400, care["dispatch_w"])

    def test_open_incident_outlasts_switch_off_and_is_priority(self):
        self.cfg["BATTERY_CARE_ENABLED"] = False
        events = [dict(event_type="battery_care_emergency_failure", status="open",
                       severity="warning", title="Battery Care: Notladung nicht erfolgreich")]
        payload = build_status_view_payload(self.cfg, self.snap, events=events)
        care = payload["zendure"]["care"]
        self.assertTrue(care["visible"])
        self.assertEqual("Ladung nicht wirksam", care["title"])
        self.assertEqual("bad", care["tone"])
        self.assertNotEqual("System OK", payload["system"]["label"])

    def test_multiple_open_incidents_but_resolved_excluded(self):
        events = [dict(event_type="battery_care_emergency_failure", status="open",
                       severity="warning", title="Battery Care: Notladung nicht erfolgreich") for _ in range(2)]
        events.append(dict(event_type="battery_care_emergency_failure", status="resolved",
                           severity="warning", title="historisch"))
        payload = build_status_view_payload(self.cfg, self.snap, events=events)
        self.assertEqual("2 offene Notladevorfälle", payload["zendure"]["care"]["detail"])

    def test_html_escaping_no_card_when_hidden(self):
        p = self.payload()
        html = render_status_page_v2(self.cfg, p, analysis_available=False, analysis_port=8081)
        self.assertIn('data-zec-care="status"', html)
        self.assertIn('role="group"', html)
        self.assertIn('data-zec-care="status" role="group" aria-label="Battery-Care-Status" hidden', html)
        p["zendure"]["care"] = dict(visible=True, title="<danger>", detail="& no effect", tone="bad")
        html = render_status_page_v2(self.cfg, p, analysis_available=False, analysis_port=8081)
        self.assertIn("Battery Care · &lt;danger&gt;", html)
        self.assertNotIn("Battery Care · <danger>", html)
        self.assertIn("&amp; no effect", html)

    def test_real_controller_dispatch_provenance_and_reset(self):
        from tests.test_battery_care_grid_live_dispatch import GridCareDispatchTests
        from battery_care_policy import CareStage
        fixture = GridCareDispatchTests()
        ctrl, cfg, state, _ = fixture.make()
        fixture.direct(ctrl, CareStage.EMERGENCY_REQUESTED, exception=True)
        self.assertTrue(ctrl._battery_care_grid_dispatch(cfg))
        self.assertEqual("EMERGENCY_REQUESTED", state.snapshot()["care_dispatched_stage"])
        self.assertEqual(250, state.snapshot()["care_dispatched_target_w"])
        # Controller cycle, not UI polling, is the authority for cleared intents.
        cfg["BATTERY_CARE_ENABLED"] = False
        ctrl.run_once(cfg)
        self.assertEqual("", state.snapshot()["care_dispatched_stage"])
        self.assertEqual(0, state.snapshot()["care_dispatched_target_w"])

    def test_real_pv_dispatch_provenance(self):
        from tests.test_battery_care_pv_live_dispatch import BatteryCarePvLiveDispatch
        fixture = BatteryCarePvLiveDispatch()
        ctrl, cfg, state, _ = fixture.make()
        fixture.proposal(ctrl, state, 650, 650)
        ctrl.run_once(cfg)
        self.assertEqual("PV_PRIORITY_REQUESTED", state.snapshot()["care_dispatched_stage"])
        self.assertGreater(state.snapshot()["care_dispatched_target_w"], 0)

    def test_snapshot_contains_truthful_dispatch_provenance(self):
        state = ControllerState()
        self.assertEqual("", state.snapshot()["care_dispatched_stage"])
        self.assertEqual(0, state.snapshot()["care_dispatched_target_w"])
        state.care_dispatched_stage = "EMERGENCY_REQUESTED"
        state.care_dispatched_target_w = 300
        self.assertEqual(300, state.snapshot()["care_dispatched_target_w"])


if __name__ == "__main__":
    unittest.main()
