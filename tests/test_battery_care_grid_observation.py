# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import replace
from datetime import date
import unittest

from battery_care_grid_observation import GridInputs, observe_grid_policy
from battery_care_policy import CareConfig, CareEpisode, CareStage, decide_care, grid_stage_two_eligible


CFG = CareConfig(True, "11-01", "02-28", 40, 30, 20, 250)


def source(**kwargs):
    data = dict(today=date(2026, 12, 1), now_epoch=1000., monotonic_s=10.,
                manual_mode="AUTO", soc=20, soc_epoch=999., soc_timeout_s=90.,
                grid_w=100., grid_epoch=999., grid_valid=True,
                device_power_w=0., device_power_epoch=999.,
                device_power_valid=True, device_power_direction="NEUTRAL",
                command_ready=True, primary_integrated=False)
    data.update(kwargs)
    return GridInputs(**data)


class GridObservationContract(unittest.TestCase):
    def decision(self, inputs):
        return decide_care(CFG, observe_grid_policy(inputs), CareEpisode(),
                           normal_min_soc=15, max_charge_w=2400)

    def test_clean_no_primary_emergency(self):
        obs = observe_grid_policy(source())
        self.assertTrue(obs.safety_ready)
        self.assertTrue(grid_stage_two_eligible(obs))
        self.assertEqual(self.decision(source()).stage, CareStage.EMERGENCY_REQUESTED)

    def test_only_source_sample_advances_confirmation(self):
        obs = observe_grid_policy(source(soc=30))
        self.assertEqual(obs.soc_sample_id, "SOC:999.0")
        self.assertEqual(obs.soc_sample_id, observe_grid_policy(source(soc=30, monotonic_s=25)).soc_sample_id)

    def test_safety_fail_closed_for_stale_and_ambiguous_evidence(self):
        for change in ({'grid_epoch':900.}, {'grid_valid':False}, {'device_power_epoch':900.},
                       {'device_power_direction':'CONFLICT'}, {'command_ready':False},
                       {'soc_epoch':900.}, {'soc_epoch':1100.}):
            with self.subTest(change=change):
                self.assertEqual(self.decision(source(**change)).requested_charge_w, 0)

    def test_known_primary_floor_must_be_fresh(self):
        x = source(soc=30, primary_integrated=True, primary_power_w=0.,
                   primary_soc=28., primary_epoch=999., primary_valid=True,
                   primary_floor_supported=True, primary_floor_soc=30.,
                   primary_floor_epoch=999., primary_floor_valid=True)
        self.assertTrue(grid_stage_two_eligible(observe_grid_policy(x)))
        self.assertFalse(grid_stage_two_eligible(observe_grid_policy(
            replace(x, primary_floor_epoch=900.))))
        self.assertFalse(grid_stage_two_eligible(observe_grid_policy(
            replace(x, primary_floor_valid=False))))
        self.assertFalse(grid_stage_two_eligible(observe_grid_policy(
            replace(x, primary_soc=35.))))
        self.assertFalse(grid_stage_two_eligible(observe_grid_policy(
            replace(x, primary_power_w=-500.))))

    def test_unknown_primary_requires_neutral_and_fresh_power(self):
        x = source(soc=30, primary_integrated=True, primary_power_w=0.,
                   primary_soc=60., primary_epoch=999., primary_valid=True)
        self.assertTrue(grid_stage_two_eligible(observe_grid_policy(x)))
        self.assertFalse(grid_stage_two_eligible(observe_grid_policy(
            replace(x, primary_power_w=250.))))
        self.assertFalse(grid_stage_two_eligible(observe_grid_policy(
            replace(x, primary_epoch=900.))))

    def test_emergency_is_not_primary_economic_gate(self):
        x = source(primary_integrated=True, primary_power_w=-900.,
                   primary_epoch=999., primary_valid=True)
        obs = observe_grid_policy(x)
        self.assertFalse(grid_stage_two_eligible(obs))
        d = self.decision(x)
        self.assertEqual(d.stage, CareStage.EMERGENCY_REQUESTED)
        self.assertTrue(d.allow_emergency_cross_charge_exception)


if __name__ == '__main__':
    unittest.main()
