"""CP25: persisted transitions from distinct completed controller cycles only."""
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from battery_care_graph_history import care_day_incidents
from battery_care_stage_events import observed_care_stage
from operational_events import OperationalEventJournal


class _State:
    def snapshot(self):
        return {}


class CareStageTransitionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = str(Path(tmp.name) / 'events.sqlite3')
        self.cfg = {'OPERATIONAL_EVENTS_DB_PATH': self.db}
        self.journal = OperationalEventJournal(lambda: self.cfg, _State())
        self.conn = self.journal._connect()
        self.addCleanup(self.conn.close)

    def sample(self, stage='NONE', cycle=1, **changes):
        active = stage not in ('NONE', 'STOP_HOLD')
        s = dict(loop_counter=cycle, care_completed_cycle_id=cycle,
                 care_dispatched_stage=stage if stage.endswith('REQUESTED') else '',
                 care_dispatched_target_w=400 if stage.endswith('REQUESTED') else 0,
                 care_policy_valid=active,
                 care_effective_discharge_floor_soc=35 if active else None,
                 current_mode='STOP_HOLD' if stage=='STOP_HOLD' else ('CHARGE' if stage.endswith('REQUESTED') else 'HOLD'))
        s.update(changes)
        return s

    def observe(self, stage, cycle, **changes):
        self.journal._observe_battery_care_stage(self.conn, self.sample(stage, cycle, **changes))

    def rows(self):
        return self.conn.execute("SELECT id,detail_json FROM operational_events "
                                 "WHERE event_type='battery_care_stage_transition' ORDER BY id").fetchall()

    def test_shadow_ack_or_uncompleted_cycle_cannot_start_transition(self):
        sample = self.sample('PV_PRIORITY_REQUESTED', 1, care_completed_cycle_id=0)
        self.assertIsNone(observed_care_stage(sample))
        self.journal._observe_battery_care_stage(self.conn, sample)
        self.journal._observe_battery_care_stage(self.conn,
             self.sample('NONE', 1, care_pv_shadow_extra_w=500, care_completed_cycle_id=0))
        self.assertEqual([], self.rows())
        self.assertEqual('NONE', observed_care_stage(self.sample('NONE', 1, care_pv_shadow_extra_w=500)))

    def test_distinct_completed_cycles_debounce_and_no_duplicate_poll(self):
        self.observe('PV_PRIORITY_REQUESTED', 1)
        for _ in range(8):
            self.observe('PV_PRIORITY_REQUESTED', 1)
        self.assertEqual([], self.rows())
        self.observe('PV_PRIORITY_REQUESTED', 2)
        self.assertEqual(1, len(self.rows()))
        info = json.loads(self.rows()[0][1]); self.assertEqual('PV_PRIORITY_REQUESTED', info['stage_to'])
        self.assertEqual('NONE', info['stage_from'])
        self.assertEqual('distinct_completed_controller_cycles', info['source'])
        self.assertFalse(info['physical_effect_confirmed'])
        for c in (2, 3, 3, 4):
            self.observe('PV_PRIORITY_REQUESTED', c)
        self.assertEqual(1, len(self.rows()))

    def test_multiple_requested_stages_and_stop_are_true_transitions(self):
        for i, stage in enumerate(('PV_PRIORITY_REQUESTED', 'PV_PRIORITY_REQUESTED',
                                  'GRID_REQUESTED', 'GRID_REQUESTED',
                                  'EMERGENCY_REQUESTED', 'EMERGENCY_REQUESTED',
                                  'RESERVE_POLICY', 'RESERVE_POLICY',
                                  'STOP_HOLD', 'STOP_HOLD'), 1):
            self.observe(stage, i)
        values = [json.loads(x[1]) for x in self.rows()]
        self.assertEqual(['PV_PRIORITY_REQUESTED','GRID_REQUESTED','EMERGENCY_REQUESTED',
                          'RESERVE_POLICY','STOP_HOLD'], [v['stage_to'] for v in values])
        self.assertEqual('EMERGENCY_REQUESTED', values[3]['stage_from'])
        self.assertEqual('STOP_HOLD', values[-1]['observed_mode'])
        self.assertEqual(0, values[-1]['requested_power_w'])

    def test_restart_same_stage_does_not_double_record_and_exit_is_persisted(self):
        self.observe('EMERGENCY_REQUESTED', 1)
        self.observe('EMERGENCY_REQUESTED', 2)
        other = OperationalEventJournal(lambda: self.cfg, _State())
        other_conn = other._connect(); self.addCleanup(other_conn.close)
        for c in (1,2,3):
            other._observe_battery_care_stage(other_conn, self.sample('EMERGENCY_REQUESTED',c))
        self.assertEqual(1, len(self.rows()))
        for c in (4,5):
            other._observe_battery_care_stage(other_conn, self.sample('NONE',c))
        self.assertEqual(2,len(self.rows()))
        self.assertEqual('NONE',json.loads(self.rows()[-1][1])['stage_to'])

    def test_idle_or_stop_without_prior_care_never_creates_marker(self):
        for c in (1,2,3): self.observe('NONE',c)
        for c in (4,5): self.observe('STOP_HOLD',c)
        self.assertEqual([],self.rows())

    def test_one_cycle_flap_does_not_create_illusive_stage_marker(self):
        for c, stage in enumerate(('PV_PRIORITY_REQUESTED','NONE',
                                    'PV_PRIORITY_REQUESTED','NONE'), 1):
            self.observe(stage,c)
        self.assertEqual([],self.rows())

    def test_stage_event_visible_in_historical_graph_and_not_physical_effect(self):
        instant = datetime(2026,12,3,10,34,15).timestamp()
        with patch('operational_events.time.time', return_value=instant):
            self.observe('GRID_REQUESTED',1); self.observe('GRID_REQUESTED',2)
        markers = care_day_incidents(self.cfg,'2026-12-03')
        self.assertEqual('recorded',markers['status'])
        self.assertEqual(1,len(markers['items']))
        marker=markers['items'][0]
        self.assertEqual('stage_transition',marker['kind'])
        self.assertEqual('GRID_REQUESTED',marker['stage_to'])
        self.assertFalse(marker['physical_effect_confirmed'])
        self.assertAlmostEqual(634.25,marker['minute'])

    def test_changed_effective_reserve_during_same_stage_is_event_once(self):
        self.observe('RESERVE_POLICY',1); self.observe('RESERVE_POLICY',2)
        self.observe('RESERVE_POLICY',3,care_effective_discharge_floor_soc=41)
        self.observe('RESERVE_POLICY',4,care_effective_discharge_floor_soc=41)
        self.observe('RESERVE_POLICY',5,care_effective_discharge_floor_soc=41)
        details=[json.loads(row[1]) for row in self.rows()]
        self.assertEqual(2,len(details))
        self.assertEqual(('RESERVE_POLICY','RESERVE_POLICY'),
                         (details[-1]['stage_from'],details[-1]['stage_to']))
        self.assertEqual((35.0,41.0),
                         (details[-1]['floor_from_soc'],details[-1]['floor_to_soc']))

    def test_corrupt_event_metadata_must_not_become_marker(self):
        t=datetime(2026,12,3,10).timestamp()
        self.conn.execute('INSERT INTO operational_events(event_type,severity,title,detail,started_at,ended_at,status,detail_json) '
                          'VALUES (?,?,?,?,?,?,?,?)',
                          ('battery_care_stage_transition','info','fake','fake',t,t,'resolved',
                           json.dumps({'stage_from':'NONE','stage_to':'EMERGENCY_REQUESTED','physical_effect_confirmed':True})))
        self.conn.commit()
        self.assertEqual([],care_day_incidents(self.cfg,'2026-12-03')['items'])


if __name__ == '__main__':
    unittest.main()
