"""Stage-1 differential/physical energy guard; no device publishers."""
import unittest

from battery_care_pv_allocation import PvSnapshot, PvMemory, allocate_care_pv


def frame(n=1, **override):
    params = dict(monotonic_s=3.0*n, grid_w=0., grid_sample=f'g{n}',
                  zendure_signed_w=0., zendure_sample=f'z{n}',
                  primary_integrated=True, primary_signed_w=900.,
                  primary_sample=f'p{n}', grid_fresh=True, zendure_fresh=True,
                  primary_fresh=True, direction_independent=True, command_ready=True)
    params.update(override)
    return PvSnapshot(**params)


class StageOneAllocatorTests(unittest.TestCase):
    def test_primary_900_to_zendure_900_is_absolute_not_doubled(self):
        x = allocate_care_pv(frame(1), PvMemory(), care_eligible=True, normal_baseline_w=0,
                             max_charge_w=2400)
        self.assertEqual(0, x.absolute_target_w)
        for n in range(2, 9):
            x = allocate_care_pv(frame(n), x.memory, care_eligible=True,
                                 normal_baseline_w=0, max_charge_w=2400)
        self.assertEqual(900, x.absolute_target_w)
        y = allocate_care_pv(frame(9, grid_w=0, zendure_signed_w=900,
                                   primary_signed_w=0), x.memory,
                             care_eligible=True, normal_baseline_w=0, max_charge_w=2400)
        self.assertEqual(900, y.pv_balance_estimate_w)
        self.assertEqual(900, y.absolute_target_w)
        self.assertFalse(y.physical_effect_proven)

    def test_same_balance_but_import_forces_backoff(self):
        prev = PvMemory(extra_target_w=900, last_monotonic_s=3,
                        last_sample_key=('g1','z1','p1'), observed_frames=3)
        x = allocate_care_pv(frame(2, grid_w=900, zendure_signed_w=900), prev,
                             care_eligible=True, normal_baseline_w=0, max_charge_w=2400)
        self.assertEqual(900, x.pv_balance_estimate_w)
        self.assertEqual(0, x.care_extra_w)
        self.assertEqual('CARE_IMPORT_BACKOFF', x.reason)

    def test_primary_grid_charge_not_mistaken_for_pv(self):
        x = allocate_care_pv(frame(2, grid_w=600, primary_signed_w=600), PvMemory(),
                             care_eligible=True, normal_baseline_w=0, max_charge_w=2400)
        self.assertEqual(0, x.pv_balance_estimate_w)

    def test_repeat_samples_or_one_stale_source_cannot_attack(self):
        x = allocate_care_pv(frame(), PvMemory(), care_eligible=True,
                             normal_baseline_w=0, max_charge_w=2400)
        x = allocate_care_pv(frame(2, primary_sample='p1'), x.memory,
                             care_eligible=True, normal_baseline_w=0, max_charge_w=2400)
        self.assertEqual(0, x.care_extra_w)
        x = allocate_care_pv(frame(3, primary_fresh=False), x.memory,
                             care_eligible=True, normal_baseline_w=0, max_charge_w=2400)
        self.assertEqual('SOURCE_STALE', x.reason)

    def test_import_reduction_preserves_ordinary_baseline(self):
        x = allocate_care_pv(frame(2, grid_w=500, zendure_signed_w=700),
                             PvMemory(extra_target_w=650), care_eligible=True,
                             normal_baseline_w=250, max_charge_w=2400)
        self.assertEqual(250, x.absolute_target_w)

    def test_disabled_and_outside_scope_no_care_or_persistent_memory(self):
        x = allocate_care_pv(frame(), PvMemory(extra_target_w=800), care_eligible=False,
                             normal_baseline_w=200, max_charge_w=2400)
        self.assertEqual(200, x.absolute_target_w)
        self.assertEqual(0, x.memory.extra_target_w)

    def test_ambiguous_or_opposite_direction_fail_closed(self):
        for kwargs in ({'direction_independent':False}, {'zendure_signed_w':-100.},
                       {'primary_signed_w':-100.}, {'command_ready':False}):
            with self.subTest(kwargs=kwargs):
                x = allocate_care_pv(frame(**kwargs), PvMemory(extra_target_w=500),
                                     care_eligible=True, normal_baseline_w=100,
                                     max_charge_w=2400)
                self.assertEqual(100, x.absolute_target_w)

    def test_gap_restarts_attack_and_power_cap(self):
        x = allocate_care_pv(frame(10), PvMemory(extra_target_w=300,
                               last_monotonic_s=3., last_sample_key=('g1','z1','p1'),
                               observed_frames=2), care_eligible=True,
                             normal_baseline_w=500, max_charge_w=600)
        self.assertEqual(500, x.absolute_target_w)
        self.assertEqual(0, x.care_extra_w)

    def test_stage_one_does_not_double_fast_or_baseline(self):
        start = allocate_care_pv(frame(1, grid_w=-200, primary_signed_w=100), PvMemory(),
                                 care_eligible=True, normal_baseline_w=300, max_charge_w=2400)
        x = allocate_care_pv(frame(2, grid_w=-200, primary_signed_w=100), start.memory,
                             care_eligible=True, normal_baseline_w=300, max_charge_w=2400)
        self.assertEqual(300, x.absolute_target_w)  # total=300, not 300+300

    def test_backoff_requires_recovery_frame_before_new_attack(self):
        mem = PvMemory(extra_target_w=850, observed_frames=3,
                       last_sample_key=('g1','z1','p1'), last_monotonic_s=3)
        hit = allocate_care_pv(frame(2, grid_w=500, zendure_signed_w=500), mem,
                               care_eligible=True, normal_baseline_w=0, max_charge_w=2400)
        self.assertEqual(0, hit.care_extra_w)
        first = allocate_care_pv(frame(3), hit.memory, care_eligible=True,
                                 normal_baseline_w=0, max_charge_w=2400)
        self.assertEqual('IMPORT_RECOVERY_CONFIRMING', first.reason)
        self.assertEqual(0, first.care_extra_w)
        retry = allocate_care_pv(frame(4), first.memory, care_eligible=True,
                                 normal_baseline_w=0, max_charge_w=2400)
        self.assertEqual('CARE_PV_ATTACK', retry.reason)
        self.assertGreater(retry.care_extra_w, 0)

    def test_import_backoff_waits_for_new_nonimport_sample(self):
        mem = PvMemory(extra_target_w=500, observed_frames=3,
                       last_sample_key=('g1','z1','p1'),last_monotonic_s=3)
        x = allocate_care_pv(frame(2, grid_w=400, zendure_signed_w=400), mem,
                             care_eligible=True,normal_baseline_w=0,max_charge_w=2400)
        self.assertTrue(x.memory.import_backoff)
        y = allocate_care_pv(frame(3, grid_w=30), x.memory,care_eligible=True,
                             normal_baseline_w=0,max_charge_w=2400)
        self.assertEqual(0, y.care_extra_w)

if __name__ == '__main__':
    unittest.main()
