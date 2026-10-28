# SPDX-License-Identifier: AGPL-3.0-or-later
"""CP20: distinct concurrent emergency-failure IDs and per-incident recovery."""
import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from operational_events import OperationalEventJournal


class BatteryCareMultiIncidentTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = str(Path(tmp.name) / 'events.sqlite3')
        self.j = self.journal()

    def journal(self):
        return OperationalEventJournal(lambda: {'OPERATIONAL_EVENTS_DB_PATH': self.path}, None)

    def failure(self, name, reserve):
        return dict(care_emergency_failure_confirmed=True,
                    care_emergency_failure_event_id=name,
                    care_emergency_incident_reserve_soc=reserve,
                    care_emergency_failure_reason='COMMAND_MISMATCH_CONFIRMED',
                    care_episode_id='episode-' + name,
                    care_soc_percent=15, care_soc_fresh=True,
                    care_soc_sample_id='initial')

    def sample(self, soc, label, fresh=True):
        return dict(care_soc_percent=soc, care_soc_fresh=fresh,
                    care_soc_sample_id=label)

    def rows(self):
        with closing(self.j._connect()) as c:
            return [(row[0], row[1], json.loads(row[2])) for row in c.execute(
                "SELECT id,status,detail_json FROM operational_events "
                "WHERE event_type='battery_care_emergency_failure' ORDER BY id")]

    def test_two_open_incidents_keep_distinct_immutable_reserves(self):
        self.assertTrue(self.j.persist_confirmed_emergency_failure(self.failure('a', 24)))
        self.assertTrue(self.j.persist_confirmed_emergency_failure(self.failure('b', 41)))
        rows = self.rows()
        self.assertEqual(['open', 'open'], [r[1] for r in rows])
        self.assertEqual(['a', 'b'], [r[2]['failure_event_id'] for r in rows])
        self.assertEqual([24, 41], [r[2]['incident_reserve_soc'] for r in rows])
        self.assertEqual(2, len([e for e in self.j.list_recent(days=1)
                                 if e['event_type']=='battery_care_emergency_failure' and e['status']=='open']))
        # Idempotent same-edge watchdog retry; no new row, no changed original R.
        self.assertTrue(self.j.persist_confirmed_emergency_failure(self.failure('a', 24)))
        self.assertEqual(2, len(self.rows()))

    def test_one_recovers_at_24_while_second_remains_open_until_41(self):
        self.j.persist_confirmed_emergency_failure(self.failure('a', 24))
        self.j.persist_confirmed_emergency_failure(self.failure('b', 41))
        with closing(self.j._connect()) as conn:
            with patch('operational_events.time.monotonic', return_value=100):
                self.j._observe_battery_care_incident(conn, self.sample(25, 'fresh-1'))
        with closing(self.j._connect()) as conn:
            with patch('operational_events.time.monotonic', return_value=104):
                self.j._observe_battery_care_incident(conn, self.sample(25, 'fresh-2'))
        statuses = [r[1] for r in self.rows()]
        self.assertEqual(['resolved', 'open'], statuses)
        self.assertEqual(24, self.rows()[0][2]['recovery_reserve_soc'])
        with closing(self.j._connect()) as conn:
            with patch('operational_events.time.monotonic', return_value=110):
                self.j._observe_battery_care_incident(conn, self.sample(41, 'fresh-3'))
            with patch('operational_events.time.monotonic', return_value=114):
                self.j._observe_battery_care_incident(conn, self.sample(41, 'fresh-4'))
        self.assertEqual(['resolved', 'resolved'], [r[1] for r in self.rows()])
        self.assertEqual(41, self.rows()[1][2]['recovery_reserve_soc'])

    def test_recovery_independent_clocks_no_repeated_or_stale_soc(self):
        self.j.persist_confirmed_emergency_failure(self.failure('a', 25))
        self.j.persist_confirmed_emergency_failure(self.failure('b', 50))
        with closing(self.j._connect()) as conn:
            with patch('operational_events.time.monotonic', return_value=100):
                self.j._observe_battery_care_incident(conn, self.sample(26, 'ingest-1'))
            with patch('operational_events.time.monotonic', return_value=110):
                self.j._observe_battery_care_incident(conn, self.sample(26, 'ingest-1'))
            self.assertEqual(['open', 'open'], [r[1] for r in self.rows()])
            # Stale data destroys only candidates, never resolves.
            self.j._observe_battery_care_incident(conn, self.sample(88, 'ingest-2', False))
            with patch('operational_events.time.monotonic', return_value=120):
                self.j._observe_battery_care_incident(conn, self.sample(26, 'ingest-3'))
            with patch('operational_events.time.monotonic', return_value=125):
                self.j._observe_battery_care_incident(conn, self.sample(26, 'ingest-4'))
        self.assertEqual(['resolved', 'open'], [r[1] for r in self.rows()])

    def test_new_observer_restart_does_not_inherit_candidate_samples(self):
        self.j.persist_confirmed_emergency_failure(self.failure('a', 20))
        self.j.persist_confirmed_emergency_failure(self.failure('b', 35))
        with closing(self.j._connect()) as conn:
            with patch('operational_events.time.monotonic', return_value=100):
                self.j._observe_battery_care_incident(conn, self.sample(50, 'before-restart'))
        self.j = self.journal()
        with closing(self.j._connect()) as conn:
            with patch('operational_events.time.monotonic', return_value=200):
                self.j._observe_battery_care_incident(conn, self.sample(50, 'after-restart'))
            self.assertEqual(['open', 'open'], [r[1] for r in self.rows()])
            with patch('operational_events.time.monotonic', return_value=204):
                self.j._observe_battery_care_incident(conn, self.sample(50, 'second-after'))
        self.assertEqual(['resolved', 'resolved'], [r[1] for r in self.rows()])

    def test_reused_id_changed_reserve_is_not_marked_successful(self):
        self.assertTrue(self.j.persist_confirmed_emergency_failure(self.failure('same', 35)))
        self.assertFalse(self.j.persist_confirmed_emergency_failure(self.failure('same', 25)))
        self.assertEqual([35], [r[2]['incident_reserve_soc'] for r in self.rows()])
        self.assertEqual(1, len(self.rows()))

    def test_resolved_old_id_never_reopened_and_new_id_remains_independent(self):
        self.j.persist_confirmed_emergency_failure(self.failure('a', 20))
        with closing(self.j._connect()) as conn:
            with patch('operational_events.time.monotonic', return_value=100):
                self.j._observe_battery_care_incident(conn, self.sample(30, 's-1'))
            with patch('operational_events.time.monotonic', return_value=104):
                self.j._observe_battery_care_incident(conn, self.sample(30, 's-2'))
        self.assertTrue(self.j.persist_confirmed_emergency_failure(self.failure('a', 20)))
        self.assertTrue(self.j.persist_confirmed_emergency_failure(self.failure('c', 50)))
        self.assertEqual(['resolved', 'open'], [r[1] for r in self.rows()])

    def test_legacy_cp19_row_not_duplicated_and_second_new_id_inserted(self):
        with closing(self.j._connect()) as conn:
            self.j._add(conn, 'battery_care_emergency_failure', 'error', 'Legacy failure', 'legacy',
                        dedupe_key='battery_care_emergency_failure', open_event=True,
                        values=dict(failure_event_id='legacy', incident_reserve_soc=26),
                        dedupe_window_s=0.0)
        self.assertTrue(self.j.persist_confirmed_emergency_failure(self.failure('legacy', 26)))
        self.assertTrue(self.j.persist_confirmed_emergency_failure(self.failure('new', 42)))
        self.assertEqual(2, len(self.rows()))
        self.assertEqual(['legacy', 'new'], [r[2]['failure_event_id'] for r in self.rows()])

    def test_urgent_and_background_different_id_race_both_persist(self):
        self.j.persist_confirmed_emergency_failure(self.failure('original', 22))
        barrier = threading.Barrier(3)
        errors = []
        outcomes = []
        def writer(name, reserve):
            try:
                barrier.wait(timeout=4)
                outcomes.append(self.j.persist_confirmed_emergency_failure(self.failure(name, reserve)))
            except Exception as ex:
                errors.append(ex)
        a = threading.Thread(target=writer, args=('new-a', 33))
        b = threading.Thread(target=writer, args=('new-b', 44))
        a.start();b.start();barrier.wait(timeout=4)
        a.join(timeout=4); b.join(timeout=4)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertEqual([], errors)
        self.assertEqual([True, True], sorted(outcomes))
        self.assertEqual(3, len(self.rows()))

    def test_compact_status_warns_two_distinct_incidents(self):
        import time
        from config_manager import DEFAULT_CONFIG
        from state import ControllerState
        from web_ui import build_status_view_payload
        self.j.persist_confirmed_emergency_failure(self.failure('a', 24))
        self.j.persist_confirmed_emergency_failure(self.failure('b', 41))
        state = ControllerState()
        with state.lock:
            state.battery_soc = 15
            state.last_soc_update_epoch = time.time()
        snap = state.snapshot()
        snap.update({'current_mode': 'HOLD', 'grid_power_valid': True,
                     'raw_grid_power': 0, 'second_battery_data_valid': True,
                     'zendure_mqtt_overall_status': 'ZENDURE_MQTT_OK',
                     'zendure_command_state_complete': True})
        events = self.j.list_recent(days=1)
        payload = build_status_view_payload(dict(DEFAULT_CONFIG), snap, events=events)
        self.assertEqual(2, payload['events']['open_count'])
        self.assertEqual('bad', payload['system']['kind'])
        self.assertEqual('Fehler 2', payload['system']['label'])
        care_warnings = [w for w in payload['system']['warnings']
                         if 'Battery Care: Notladung nicht erfolgreich' in w]
        self.assertEqual(1, len(care_warnings))
        self.assertIn('2 offene Vorfälle', care_warnings[0])
        self.assertEqual(2, len([e for e in payload['events']['items']
                                 if e['event_type']=='battery_care_emergency_failure']))
        self.assertTrue(any('24 %' in e['detail'] for e in payload['events']['items']))
        self.assertTrue(any('41 %' in e['detail'] for e in payload['events']['items']))

    def test_no_false_writes_on_acks_or_unconfirmed_state(self):
        self.assertFalse(self.j.persist_confirmed_emergency_failure(
            {'care_emergency_failure_confirmed': False,
             'care_emergency_failure_event_id':'n',
             'care_emergency_incident_reserve_soc':30}))
        self.assertFalse(Path(self.path).exists())


if __name__ == '__main__':
    unittest.main()
