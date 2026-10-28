# SPDX-License-Identifier: AGPL-3.0-or-later
"""CP19: watchdog-confirmed emergency incident write-through and failure modes."""
import json
import sqlite3
import tempfile
import time
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from operational_events import OperationalEventJournal
from tests.test_battery_care_command_incident_bridge import CareCommandIncidentBridgeTests


class EmergencyWriteThroughTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / 'events.db')
        self.snapshot = {
            'care_emergency_failure_confirmed': True,
            'care_emergency_failure_event_id': 'independent-effect-edge-1',
            'care_emergency_incident_reserve_soc': 40,
            'care_emergency_failure_reason': 'COMMAND_MISMATCH_CONFIRMED',
            'care_episode_id': 'emergency-12',
            'care_soc_percent': 19,
            'care_soc_fresh': True,
            'care_soc_sample_id': 'ingest-111',
        }
        self.journal = OperationalEventJournal(
            lambda: {'OPERATIONAL_EVENTS_DB_PATH': self.db}, None)

    def rows(self):
        with closing(self.journal._connect()) as conn:
            return conn.execute(
                "SELECT status,detail_json FROM operational_events "
                "WHERE event_type='battery_care_emergency_failure' ORDER BY id"
            ).fetchall()

    def test_write_through_exists_without_background_observer_and_survives_restart(self):
        self.assertTrue(self.journal.persist_confirmed_emergency_failure(self.snapshot))
        restarted = OperationalEventJournal(lambda: {'OPERATIONAL_EVENTS_DB_PATH': self.db}, None)
        self.assertEqual('open', self.rows()[0][0])
        values = json.loads(self.rows()[0][1])
        self.assertEqual(40, values['incident_reserve_soc'])
        self.assertEqual('independent-effect-edge-1', values['failure_event_id'])
        self.assertTrue(restarted.persist_confirmed_emergency_failure(self.snapshot))
        self.assertEqual(1, len(self.rows()))

    def test_no_db_for_ack_stale_intent_or_invalid_reserve(self):
        for data in (
            dict(self.snapshot, care_emergency_failure_confirmed=False),
            dict(self.snapshot, care_emergency_failure_event_id=''),
            dict(self.snapshot, care_emergency_incident_reserve_soc=None),
            dict(self.snapshot, care_emergency_incident_reserve_soc=True),
        ):
            self.assertFalse(self.journal.persist_confirmed_emergency_failure(data))
        self.assertFalse(Path(self.db).exists())

    def test_serialized_background_and_urgent_same_failure_id_never_double_insert(self):
        # Pre-create SQLite schema: race covers confirmed event insertion,
        # not first-boot journal_mode initialization by two threads.
        with closing(self.journal._connect()):
            pass
        started = threading.Barrier(3)
        errors = []
        def one(urgent):
            try:
                started.wait(timeout=5)
                if urgent:
                    self.journal.persist_confirmed_emergency_failure(self.snapshot)
                else:
                    with closing(self.journal._connect()) as conn:
                        self.journal._observe_battery_care_incident(conn, self.snapshot)
            except Exception as ex:
                errors.append(ex)
        t1=threading.Thread(target=one,args=(True,))
        t2=threading.Thread(target=one,args=(False,))
        t1.start();t2.start();started.wait(timeout=5)
        t1.join(timeout=5);t2.join(timeout=5)
        self.assertFalse(t1.is_alive() or t2.is_alive())
        self.assertEqual([], errors)
        self.assertEqual(1, len(self.rows()))

    def test_distinct_confirmed_failure_persists_while_previous_incident_is_open(self):
        self.assertTrue(self.journal.persist_confirmed_emergency_failure(self.snapshot))
        second = dict(self.snapshot, care_emergency_failure_event_id='second-independent-edge')
        self.assertTrue(self.journal.persist_confirmed_emergency_failure(second))
        self.assertEqual(2, len(self.rows()))
        self.assertEqual(["open", "open"], [row[0] for row in self.rows()])

    def test_locked_db_is_bounded_and_no_false_success(self):
        with closing(self.journal._connect()) as hold:
            hold.execute('BEGIN IMMEDIATE')
            start=time.monotonic()
            with self.assertRaises(sqlite3.OperationalError):
                self.journal.persist_confirmed_emergency_failure(self.snapshot)
            self.assertLess(time.monotonic()-start, 1.0)
            hold.rollback()
        self.assertTrue(self.journal.persist_confirmed_emergency_failure(self.snapshot))

    def test_real_watchdog_marks_unpersisted_failure_and_retries_same_id(self):
        fixture=CareCommandIncidentBridgeTests()
        fixture.setUp()
        try:
            ctrl, state = fixture.make()
            failing=OperationalEventJournal(lambda: {'OPERATIONAL_EVENTS_DB_PATH': self.db}, state)
            with patch.object(failing, 'persist_confirmed_emergency_failure', side_effect=sqlite3.OperationalError('locked')):
                ctrl._care_incident_write_through_journal=failing
                ctrl._mark_mismatch(target=250, actual_text='0 W', elapsed_s=120,tolerance_w=30)
            first_id=state.care_emergency_failure_event_id
            self.assertTrue(first_id)
            self.assertFalse(state.care_emergency_incident_persisted)
            self.assertEqual('EVENT_WRITE_FAILED:OperationalError',state.care_emergency_incident_persistence_error)
            self.assertFalse(Path(self.db).exists())
            ctrl._mark_mismatch(target=250, actual_text='0 W', elapsed_s=130,tolerance_w=30)
            self.assertEqual(first_id,state.care_emergency_failure_event_id)
            self.assertTrue(state.care_emergency_incident_persisted)
            self.assertEqual('',state.care_emergency_incident_persistence_error)
            self.assertEqual(1,len(self.rows()))
        finally:
            fixture.doCleanups()


if __name__ == '__main__':
    unittest.main()
