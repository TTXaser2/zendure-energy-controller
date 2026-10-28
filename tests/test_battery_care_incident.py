"""Battery Care emergency non-effect must persist until measured reserve recovery."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operational_events import OperationalEventJournal


class BatteryCareIncidentContractTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.path = str(Path(self.td.name) / "events.sqlite3")
        self.j = self.journal()
        self.conn = self.j._connect()
        self.addCleanup(self.conn.close)
        self.failure = {
            "care_emergency_failure_confirmed": True,
            "care_emergency_failure_event_id": "failure-a",
            "care_emergency_incident_reserve_soc": 23,
            "care_emergency_failure_reason": "COMMAND_MISMATCH_CONFIRMED",
            "care_episode_id": "episode-a",
            "care_soc_percent": 9,
            "care_soc_fresh": True,
            "care_soc_sample_id": "telemetry-001",
        }

    def journal(self):
        return OperationalEventJournal(lambda: {"OPERATIONAL_EVENTS_DB_PATH": self.path},
                                       type("S", (), {"snapshot": lambda self: {}})())

    def rows(self):
        return self.conn.execute(
            "SELECT id,status,detail_json FROM operational_events WHERE event_type='battery_care_emergency_failure' ORDER BY id"
        ).fetchall()

    def test_no_incident_from_ack_readback_or_pending_and_no_invented_target(self):
        self.j._observe_battery_care_incident(self.conn, {"care_emergency_requested": True,
                                                          "care_command_readback_matches": True})
        self.assertEqual([], self.rows())
        self.j._observe_battery_care_incident(self.conn,
                                             dict(self.failure,care_emergency_incident_reserve_soc=None))
        self.assertEqual([], self.rows())

    def test_persists_across_care_off_stop_season_restart_unchanged_reserve(self):
        self.j._observe_battery_care_incident(self.conn, self.failure)
        self.assertEqual("open", self.rows()[0][1])
        self.j = self.journal()  # new process object sharing persistent event DB
        for snap in ({"care_enabled":False}, {"manual_mode":"STOP_HOLD"},
                     {"care_in_season":False,"care_soc_percent":22,"care_soc_fresh":True,
                      "care_soc_sample_id":"two"},
                     {"care_enabled":True,"care_reserve_soc":10,"care_soc_fresh":False}):
            self.j._observe_battery_care_incident(self.conn, snap)
            self.assertEqual("open", self.rows()[0][1])
        detail=json.loads(self.rows()[0][2])
        self.assertEqual(23,detail["incident_reserve_soc"])
        self.assertEqual("COMMAND_MISMATCH_CONFIRMED", detail["initial_failure_reason"])

    def test_same_soc_sample_and_transient_jump_are_not_recovery(self):
        self.j._observe_battery_care_incident(self.conn,self.failure)
        high={"care_soc_percent":23,"care_soc_fresh":True,"care_soc_sample_id":"new-01"}
        with patch("operational_events.time.monotonic", return_value=100):
            self.j._observe_battery_care_incident(self.conn,high)
        with patch("operational_events.time.monotonic", return_value=110):
            self.j._observe_battery_care_incident(self.conn,high)
        self.assertEqual("open",self.rows()[0][1])
        self.j._observe_battery_care_incident(self.conn,{"care_soc_percent":22,
                                                         "care_soc_fresh":True,"care_soc_sample_id":"new-02"})
        with patch("operational_events.time.monotonic", return_value=120):
            self.j._observe_battery_care_incident(self.conn,dict(high,care_soc_sample_id="new-03"))
        self.assertEqual("open",self.rows()[0][1])

    def test_only_two_distinct_fresh_samples_over_time_resolve_and_keep_history(self):
        self.j._observe_battery_care_incident(self.conn,self.failure)
        a={"care_soc_percent":23,"care_soc_fresh":True,"care_soc_sample_id":"new-01"}
        b=dict(a,care_soc_sample_id="new-02")
        with patch("operational_events.time.monotonic",return_value=100):
            self.j._observe_battery_care_incident(self.conn,a)
        with patch("operational_events.time.monotonic",return_value=102):
            self.j._observe_battery_care_incident(self.conn,b)
        self.assertEqual("open",self.rows()[0][1])
        with patch("operational_events.time.monotonic",return_value=104):
            self.j._observe_battery_care_incident(self.conn,b)
        rows=self.rows()
        self.assertEqual(1,len(rows))
        self.assertEqual("resolved",rows[0][1])
        d=json.loads(rows[0][2])
        self.assertEqual(23,d["incident_reserve_soc"])
        self.assertEqual(23,d["recovery_reserve_soc"])
        self.assertEqual(9,d["min_observed_soc"])
        self.assertGreaterEqual(d["recovery_observation_count"],2)
        # The original level-triggered flag must never reopen a closed alarm.
        self.j._observe_battery_care_incident(self.conn,self.failure)
        self.assertEqual(1,len(self.rows()))
        self.j._observe_battery_care_incident(self.conn, dict(self.failure,
             care_episode_id="episode-b",care_emergency_failure_event_id="failure-b"))
        rows=self.rows()
        self.assertEqual(["resolved","open"],[r[1] for r in rows])

    def test_positive_charge_below_target_keeps_warning_open(self):
        self.j._observe_battery_care_incident(self.conn,self.failure)
        self.j._observe_battery_care_incident(self.conn,{
            "care_physical_charge_confirmed":True,
            "care_soc_percent":16,"care_soc_fresh":True,"care_soc_sample_id":"new-02"})
        self.assertEqual("open", self.rows()[0][1])
        self.assertTrue(json.loads(self.rows()[0][2])["charging_restored"])
        self.assertTrue(any(x["event_type"]=="battery_care_emergency_failure" and x["status"]=="open"
                            for x in self.j.list_recent(days=1)))

    def test_bad_soc_and_stale_sample_never_resolve(self):
        self.j._observe_battery_care_incident(self.conn,self.failure)
        for soc in (float("nan"),101,-1,None):
            self.j._observe_battery_care_incident(self.conn,
                 {"care_soc_percent":soc,"care_soc_fresh":True,"care_soc_sample_id":"new-01"})
        self.j._observe_battery_care_incident(self.conn,
             {"care_soc_percent":90,"care_soc_fresh":False,"care_soc_sample_id":"new-02"})
        self.assertEqual("open",self.rows()[0][1])

    def test_observer_has_no_spontaneous_failure_when_care_fields_missing(self):
        self.j._observe(self.conn,{})
        self.assertEqual([],self.rows())

if __name__ == '__main__':
    unittest.main()
