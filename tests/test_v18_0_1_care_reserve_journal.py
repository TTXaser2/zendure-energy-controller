"""Episode journal differentiates dispatch intent from neutralization evidence."""
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from operational_events import OperationalEventJournal

class _State:
    def snapshot(self):return {}

class CareReserveJournalTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.cfg={'OPERATIONAL_EVENTS_DB_PATH':str(Path(tmp.name)/'events.db')}
        self.journal=OperationalEventJournal(lambda:self.cfg,_State())
        self.conn=self.journal._connect();self.addCleanup(self.conn.close)

    def snap(self,**kwargs):
        s=dict(care_completed_cycle_id=1,care_policy_valid=True,
               care_effective_discharge_floor_soc=20,battery_soc=20,
               current_mode='HOLD',target_power_limit_reason='BATTERY_CARE_RESERVE',
               command_desired_signed_target_w=0,command_readback_matches_desired=False,
               actual_zendure_power_valid=True,actual_zendure_system_signed_power=-600,
               command_effect_category='COMMAND_NEUTRALIZATION_OBSERVING')
        s.update(kwargs);return s

    def observe(self,**kwargs):
        self.journal._observe_care_reserve_reached(self.conn,self.snap(**kwargs))

    def rows(self):
        return self.conn.execute("SELECT status,title,detail_json FROM operational_events WHERE event_type='battery_care_reserve_reached'").fetchall()

    def test_one_request_no_spam_confirmation_later(self):
        self.observe()
        for i in range(2,10):self.observe(care_completed_cycle_id=i)
        self.assertEqual(1,len(self.rows()))
        self.assertEqual('open',self.rows()[0][0]);self.assertFalse(json.loads(self.rows()[0][2])['physical_effect_confirmed'])
        self.observe(care_completed_cycle_id=11,command_readback_matches_desired=True,
                     actual_zendure_system_signed_power=0,command_effect_category='COMMAND_NEUTRALIZATION_CONFIRMED')
        self.assertEqual('resolved',self.rows()[0][0]);self.assertTrue(json.loads(self.rows()[0][2])['physical_effect_confirmed'])

    def test_readback_mismatch_and_stale_physical_keep_unconfirmed(self):
        self.observe()
        self.observe(care_completed_cycle_id=2,actual_zendure_system_signed_power=0,
                     command_effect_category='COMMAND_NEUTRALIZATION_CONFIRMED')
        self.observe(care_completed_cycle_id=3,command_readback_matches_desired=True,
                     actual_zendure_system_signed_power=0,actual_zendure_power_valid=False,
                     command_effect_category='COMMAND_NEUTRALIZATION_CONFIRMED')
        self.assertEqual('open',self.rows()[0][0])

    def test_recovery_second_episode_and_restart_dedupe(self):
        self.observe()
        other=OperationalEventJournal(lambda:self.cfg,_State())
        other._observe_care_reserve_reached(self.conn,self.snap(care_completed_cycle_id=2))
        self.assertEqual(1,len(self.rows()))
        self.observe(care_completed_cycle_id=3,care_policy_valid=False)
        self.observe(care_completed_cycle_id=4)
        self.assertEqual(2,len(self.rows()))

    def test_no_event_for_soc_above_floor_stale_or_non_care(self):
        self.observe(battery_soc=21)
        self.observe(care_policy_valid=False)
        self.observe(current_mode='SAFE_STATE')
        self.observe(command_desired_signed_target_w=-300)
        self.assertEqual(0,len(self.rows()))

if __name__=='__main__':unittest.main()
