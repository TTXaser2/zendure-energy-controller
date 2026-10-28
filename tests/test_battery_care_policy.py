# SPDX-License-Identifier: AGPL-3.0-or-later
"""Safety-oriented pure Battery Care policy tests; no hardware or MQTT."""
from datetime import date
import unittest

from battery_care_policy import (CareConfig, CareEpisode, CareObservation,
                                 CareStage, care_pv_absolute_target,
                                 decide_care, grid_stage_two_eligible, in_care_season)


CFG = CareConfig(True, "11-01", "02-28", 40, 30, 20, 250)


def observation(soc=35, token="x", *, today=date(2026, 12, 1), t=0.,
                manual="AUTO", safe=True, grid=0., primary=900.,
                primary_integrated=True, primary_fresh=True,
                floor=None, primary_soc=35, primary_soc_fresh=True,
                zpower=0., grid_fresh=True, zfresh=True):
    return CareObservation(today, soc, soc is not None, token, t, manual, safe,
                           grid_fresh, grid, zfresh, zpower, primary_integrated,
                           primary_fresh, primary, primary_soc_fresh, primary_soc,
                           floor is not None, floor, floor is not None)


def decide(obs, previous=CareEpisode(), config=CFG):
    return decide_care(config, obs, previous, normal_min_soc=15, max_charge_w=2400)


class TestBatteryCarePolicy(unittest.TestCase):
    def test_default_off_cannot_issue_command(self):
        d = decide(observation(soc=5), config=CareConfig())
        self.assertEqual(d.stage, CareStage.OFF)
        self.assertEqual(d.requested_charge_w, 0)

    def test_no_historical_threshold_defaults(self):
        cfg = CareConfig(enabled=True)
        self.assertIn('CARE_SOC_REQUIRED', cfg.validate(99, 2400))
        self.assertEqual(decide(observation(), config=cfg).stage, CareStage.PAUSED)

    def test_invalid_hysteresis_and_power(self):
        self.assertIn('CARE_SOC_ORDER_OR_HYSTERESIS',
                      CareConfig(True, '11-01', '02-28', 30, 29, 28, 250).validate(99, 2400))
        self.assertIn('CARE_GRID_CAP_INVALID',
                      CareConfig(True, '11-01', '02-28', 30, 20, 10, 2500).validate(99, 2400))

    def test_boundary_calendar_and_leap(self):
        for day in [date(2026, 11, 1), date(2026, 12, 31), date(2027, 1, 1), date(2027, 2, 28)]:
            self.assertTrue(in_care_season(day, '11-01', '02-28'))
        self.assertFalse(in_care_season(date(2026, 3, 1), '11-01', '02-28'))
        self.assertTrue(in_care_season(date(2024, 2, 29), '11-01', '03-01'))
        self.assertFalse(in_care_season(date(2024, 2, 29), '02-29', '03-01'))
        self.assertTrue(in_care_season(date(2026, 11, 1), '11-01', '11-01'))

    def test_out_of_season_zero_and_no_lower_floor(self):
        d = decide(observation(today=date(2026, 5, 1)))
        self.assertEqual((d.stage, d.requested_charge_w, d.effective_discharge_floor),
                         (CareStage.OUT_OF_SEASON, 0, None))
        d = decide_care(CFG, observation(), CareEpisode(), normal_min_soc=51, max_charge_w=2400)
        self.assertEqual(d.effective_discharge_floor, 51)

    def test_pv_absolute_candidate_no_double_count(self):
        self.assertEqual(care_pv_absolute_target(observation(grid=0., primary=900., zpower=0.), 2400), 900)
        self.assertEqual(care_pv_absolute_target(observation(grid=900., primary=900., zpower=900.), 2400), 900)
        self.assertEqual(care_pv_absolute_target(observation(grid=600., primary=600., zpower=0.), 2400), 0)
        self.assertEqual(care_pv_absolute_target(observation(grid=0., primary=-100., zpower=0.), 2400), 0)
        self.assertEqual(care_pv_absolute_target(observation(grid=0., primary=900., zpower=-100.), 2400), 0)
        self.assertEqual(care_pv_absolute_target(observation(grid=0., primary=900., primary_fresh=False), 2400), 0)

    def test_primary_not_integrated_does_not_invent_charge(self):
        obs = observation(primary_integrated=False, primary=None, primary_fresh=False, grid=-100.)
        self.assertEqual(care_pv_absolute_target(obs, 2400), 100)
        self.assertTrue(grid_stage_two_eligible(obs))

    def test_safety_and_manual_stop_absolute(self):
        for mode in ('STOP_HOLD', 'FIXED_CHARGE', 'FIXED_DISCHARGE'):
            d = decide(observation(soc=10, manual=mode))
            self.assertEqual((d.requested_charge_w, d.allow_emergency_cross_charge_exception), (0, False))
        self.assertEqual(decide(observation(soc=10, safe=False)).requested_charge_w, 0)
        self.assertEqual(decide(observation(soc=None)).requested_charge_w, 0)

    def test_emergency_immediate_even_with_primary_discharge(self):
        d = decide(observation(soc=20, primary=-800., t=0.))
        self.assertEqual(d.stage, CareStage.EMERGENCY_REQUESTED)
        self.assertEqual(d.requested_charge_w, 250)
        self.assertTrue(d.allow_emergency_cross_charge_exception)

    def test_regular_needs_two_distinct_confirmed_samples(self):
        d1 = decide(observation(soc=30, token='sample-1', t=10., primary=0., floor=35))
        self.assertNotEqual(d1.stage, CareStage.GRID_REQUESTED)
        dup = decide(observation(soc=30, token='sample-1', t=20., primary=0., floor=35), d1.episode)
        self.assertNotEqual(dup.stage, CareStage.GRID_REQUESTED)
        d2 = decide(observation(soc=30, token='sample-2', t=21., primary=0., floor=35), dup.episode)
        self.assertEqual(d2.stage, CareStage.GRID_REQUESTED)
        self.assertFalse(d2.allow_emergency_cross_charge_exception)

    def test_regular_latch_until_reserve_and_recovery(self):
        d1 = decide(observation(soc=30, token='1', t=10., primary=0., floor=35))
        d2 = decide(observation(soc=30, token='2', t=15., primary=0., floor=35), d1.episode)
        self.assertEqual(d2.stage, CareStage.GRID_REQUESTED)
        d3 = decide(observation(soc=35, token='3', t=18., primary=0., floor=35), d2.episode)
        self.assertEqual(d3.stage, CareStage.GRID_REQUESTED)
        d4 = decide(observation(soc=40, token='4', t=22., primary=0., floor=35), d3.episode)
        self.assertEqual(d4.stage, CareStage.GRID_REQUESTED)
        d5 = decide(observation(soc=40, token='5', t=25., primary=0., floor=35), d4.episode)
        self.assertEqual(d5.stage, CareStage.COMPLETED)
        self.assertEqual(d5.requested_charge_w, 0)

    def test_stage_two_primary_floor(self):
        self.assertFalse(grid_stage_two_eligible(observation(primary=-500., floor=20, primary_soc=30)))
        self.assertFalse(grid_stage_two_eligible(observation(primary=0., floor=20, primary_soc=30)))
        self.assertTrue(grid_stage_two_eligible(observation(primary=0., floor=40, primary_soc=30)))
        self.assertFalse(grid_stage_two_eligible(observation(primary=100., floor=None)))
        self.assertTrue(grid_stage_two_eligible(observation(primary=0., floor=None)))

    def test_known_primary_floor_stale_must_not_fallback_to_generic(self):
        obs = observation(primary=0., floor=30, primary_soc=28)
        self.assertTrue(grid_stage_two_eligible(obs))
        from dataclasses import replace
        self.assertFalse(grid_stage_two_eligible(replace(obs, primary_floor_fresh=False)))
        self.assertFalse(grid_stage_two_eligible(replace(obs, primary_soc_fresh=False)))
        self.assertFalse(grid_stage_two_eligible(replace(obs, grid_fresh=False)))
        self.assertTrue(grid_stage_two_eligible(replace(obs, primary_floor_supported=False)))

    def test_running_emergency_uses_original_incident_reserve(self):
        from dataclasses import replace
        original = decide(observation(soc=20, token="e1"))
        changed = replace(CFG, reserve_soc=35)
        # Current configuration lowered R from 40 to 35; no early resolve.
        d1 = decide(observation(soc=36, token="e2", t=4), original.episode, changed)
        self.assertEqual(d1.stage, CareStage.EMERGENCY_REQUESTED)
        self.assertEqual(d1.episode.target_reserve_soc, 40)
        d2 = decide(observation(soc=37, token="e3", t=8), d1.episode, changed)
        self.assertEqual(d2.stage, CareStage.EMERGENCY_REQUESTED)
        d3 = decide(observation(soc=40, token="e4", t=12), d2.episode, changed)
        self.assertEqual(d3.stage, CareStage.EMERGENCY_REQUESTED)
        d4 = decide(observation(soc=40, token="e5", t=15), d3.episode, changed)
        self.assertEqual(d4.stage, CareStage.COMPLETED)

    def test_max_soc_is_current_controller_limit_not_hardcoded_100(self):
        d = decide_care(CFG, observation(), CareEpisode(), normal_min_soc=15,
                        max_charge_w=2400, maximum_soc=35)
        self.assertEqual(d.stage, CareStage.PAUSED)
        self.assertEqual(d.reason, "invalid_care_configuration")

    def test_emergency_persists_after_end_of_season_until_target(self):
        before = decide(observation(soc=20, today=date(2027, 2, 28)))
        after = decide(observation(soc=25, today=date(2027, 3, 1), token='later'), before.episode)
        self.assertEqual(after.stage, CareStage.EMERGENCY_REQUESTED)
        self.assertEqual(after.requested_charge_w, 250)

    def test_stale_grid_blocks_pv_but_does_not_block_emergency(self):
        obs = observation(soc=35, grid_fresh=False)
        self.assertNotEqual(decide(obs).stage, CareStage.PV_PRIORITY)
        self.assertEqual(decide(observation(soc=10, grid_fresh=False)).stage,
                         CareStage.EMERGENCY_REQUESTED)


if __name__ == '__main__':
    unittest.main()
