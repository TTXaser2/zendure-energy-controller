"""CP23: historically truthful seasonal SOC overlays and persisted incident markers."""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from config_manager import DEFAULT_CONFIG
from csv_logger import compute_config_control_hash
from graph_config_timeline import record_runtime_config
import web_ui

from battery_care_graph_history import care_day_lines, care_day_incidents


class CareGraphHistoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.day = '2026-12-03'
        self.config = {'OPERATIONAL_EVENTS_DB_PATH': str(self.root / 'operational.sqlite3')}

    def history(self, *minutes):
        return [dict(minute=m, mode="AUTO") for m in (minutes or (0, 660, 1440))]

    def seg(self, **overrides):
        row = dict(known=True, care_enabled=1, care_start='11-01', care_end='03-31',
                   care_r=35, care_n=28, care_e=20, min_soc=12,
                   start_minute=0, end_minute=1440)
        row.update(overrides)
        return row

    def test_summer_hides_winter_care_despite_enabled_true(self):
        self.assertEqual([], care_day_lines([self.seg()], '2026-07-03', self.history(0, 1)))

    def test_cross_year_window_includes_both_sides(self):
        self.assertEqual(35, care_day_lines([self.seg()], '2026-12-03', self.history(0, 1))[0]['auto_floor_soc'])
        self.assertEqual(35, care_day_lines([self.seg()], '2027-01-03', self.history(0, 1))[0]['auto_floor_soc'])

    def test_disabled_legacy_missing_or_invalid_care_are_not_inferred(self):
        for change in (dict(known=False), dict(care_enabled=None), dict(care_enabled=0),
                       dict(care_r=None), dict(care_start=None), dict(care_n=34),
                       dict(min_soc=None), dict(care_r=101), dict(care_e=27),
                       dict(care_n=float('nan'))):
            with self.subTest(change=change):
                self.assertEqual([], care_day_lines([self.seg(**change)], self.day, self.history(0, 1)))

    def test_history_transitions_never_use_current_values(self):
        lines = care_day_lines([self.seg(end_minute=660),
                                self.seg(start_minute=660, care_r=40)], self.day, self.history(0, 1, 2, 659, 660, 661))
        self.assertEqual([(0, 2, 35), (659, 660, 35), (660, 661, 40)],
                         [(x['start_minute'], x['end_minute'], x['reserve_soc']) for x in lines])
        self.assertTrue(all(not x['physical_effect_confirmed'] for x in lines))

    def test_effective_auto_floor_respects_higher_min_soc(self):
        lines = care_day_lines([self.seg(min_soc=45)], self.day, self.history(0, 1))
        self.assertEqual(45, lines[0]['auto_floor_soc'])
        self.assertEqual(35, lines[0]['reserve_soc'])
        self.assertEqual('configured_seasonal_auto_policy', lines[0]['kind'])

    def test_policy_line_requires_continuous_real_auto_mode_observations(self):
        self.assertEqual([], care_day_lines([self.seg()], self.day))
        self.assertEqual([], care_day_lines([self.seg()], self.day, [dict(minute=12, mode='AUTO')]))
        observed = [dict(minute=10, mode='AUTO'), dict(minute=11, mode='AUTO'),
                    dict(minute=12, mode='STOP'), dict(minute=13, mode='AUTO'),
                    dict(minute=14, mode='AUTO'), dict(minute=60, mode='AUTO'),
                    dict(minute=61, mode='AUTO')]
        self.assertEqual([(10, 11), (13, 14), (60, 61)],
                         [(r['start_minute'], r['end_minute'])
                          for r in care_day_lines([self.seg()], self.day, observed)])

    def test_missing_database_is_not_claimed_empty_event_history(self):
        self.assertEqual('not_recorded', care_day_incidents(self.config, self.day)['status'])

    def _write_events(self):
        db = sqlite3.connect(self.config['OPERATIONAL_EVENTS_DB_PATH'])
        try:
            db.execute('''CREATE TABLE operational_events(id INTEGER PRIMARY KEY,
                         event_type TEXT,started_at REAL,ended_at REAL,status TEXT)''')
            morning = datetime(2026, 12, 3, 8, 10, 30).timestamp()
            evening = datetime(2026, 12, 3, 19, 5, 0).timestamp()
            yesterday = (datetime(2026, 12, 3) - timedelta(days=1)).timestamp()
            db.executemany('INSERT INTO operational_events VALUES(?,?,?,?,?)', [
                (1, 'battery_care_emergency_failure', morning, evening, 'resolved'),
                (2, 'battery_care_emergency_failure', morning + 120, None, 'open'),
                (3, 'mqtt', morning + 240, None, 'open'),
                (4, 'battery_care_emergency_failure', yesterday, evening + 120, 'resolved'),
            ])
            db.commit()
        finally:
            db.close()

    def test_persisted_failures_and_recovery_only_not_mqtt_or_publish(self):
        self._write_events()
        result = care_day_incidents(self.config, self.day)
        self.assertEqual('recorded', result['status'])
        self.assertEqual([(1, 'failure_confirmed'), (2, 'failure_confirmed'),
                          (1, 'reserve_recovered'), (4, 'reserve_recovered')],
                         [(x['event_id'], x['kind']) for x in result['items']])
        self.assertAlmostEqual(490.5, result['items'][0]['minute'])
        self.assertEqual('persistent_operational_event', result['items'][0]['source'])

    def test_soc_day_api_preserves_historical_care_config_and_real_event_provenance(self):
        day = datetime(2026, 1, 5)
        ds = day.date().isoformat()
        dbpath = str(self.root / 'measurement.sqlite3')
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(MEASUREMENT_DB_ENABLED=True, MEASUREMENT_DB_PATH=dbpath,
                   OPERATIONAL_EVENTS_DB_PATH=self.config['OPERATIONAL_EVENTS_DB_PATH'],
                   BATTERY_CARE_ENABLED=True, BATTERY_CARE_SEASON_START_MM_DD='11-01',
                   BATTERY_CARE_SEASON_END_MM_DD='03-31',
                   BATTERY_CARE_RESERVE_SOC_PERCENT=35,
                   BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT=28,
                   BATTERY_CARE_EMERGENCY_SOC_PERCENT=20,
                   BATTERY_CARE_GRID_CHARGE_MAX_POWER_W=700,
                   MIN_SOC_PERCENT=12)
        conn = sqlite3.connect(dbpath)
        try:
            record_runtime_config(conn, int(day.timestamp() * 1000), cfg, compute_config_control_hash(cfg))
        finally:
            conn.close()
        points = [{'epoch_ms': int((day + timedelta(minutes=minute)).timestamp() * 1000),
                   'soc': 30, 'mode': 'AUTO'} for minute in (60, 61, 62)]
        with web_ui._storage_day_lock:
            web_ui._storage_day_cache.clear()
        with patch('web_ui.query_graph_points', return_value=(points, {'db_status': 'ok'})), \
             patch('web_ui.query_measurement_date_range', return_value={'available_from': ds}):
            actual = web_ui.build_storage_soc_day_payload(cfg, {'battery_soc': 30, 'current_mode': 'AUTO'}, ds)
        lines = actual['care_graph_lines']
        self.assertTrue(lines, 'historically recorded AUTO operation should permit a bounded care overlay')
        self.assertEqual(35, lines[0]['reserve_soc'])
        cfg['BATTERY_CARE_RESERVE_SOC_PERCENT'] = 42
        with patch('web_ui.query_graph_points', return_value=(points, {'db_status': 'ok'})), \
             patch('web_ui.query_measurement_date_range', return_value={'available_from': ds}):
            after = web_ui.build_storage_soc_day_payload(cfg, {'battery_soc': 30, 'current_mode': 'AUTO'}, ds)
        self.assertTrue(all(item['reserve_soc'] == 35 for item in after['care_graph_lines']),
                        "current settings must not rewrite past care history")

    def test_day_outside_known_incidents_has_no_fake_marker(self):
        self._write_events()
        self.assertEqual([], care_day_incidents(self.config, '2026-12-05')['items'])

    def test_malformed_event_db_is_explicitly_unavailable(self):
        Path(self.config['OPERATIONAL_EVENTS_DB_PATH']).write_text('not-sqlite')
        self.assertEqual('unavailable', care_day_incidents(self.config, self.day)['status'])


    def night_history(self, *minutes):
        return [dict(minute=m, mode='NIGHT_DISCHARGE') for m in minutes]

    def test_night_floor_respects_higher_historical_reserve(self):
        night = self.seg(night_start='22:00', night_end='06:00', reserve_soc=48)
        result = care_day_lines([night], self.day, self.night_history(1380, 1381))
        self.assertEqual(1, len(result))
        self.assertEqual('configured_seasonal_night_policy', result[0]['kind'])
        self.assertEqual(48, result[0]['night_floor_soc'])
        self.assertEqual(48, result[0]['effective_discharge_floor_soc'])
        self.assertFalse(result[0]['physical_effect_confirmed'])
        self.assertNotIn('auto_floor_soc', result[0])

    def test_night_floor_uses_care_reserve_if_night_stop_missing_or_lower(self):
        for night_stop in (None, 20):
            with self.subTest(night_stop=night_stop):
                result = care_day_lines([self.seg(night_start='21:00', night_end='06:00',
                                                   reserve_soc=night_stop)],
                                         self.day, self.night_history(1320, 1321))
                self.assertEqual(35, result[0]['night_floor_soc'])
        result = care_day_lines([self.seg(night_start='21:00', night_end='06:00',
                                           reserve_soc=25, min_soc=42)],
                                self.day, self.night_history(1320, 1321))
        self.assertEqual(42, result[0]['night_floor_soc'])

    def test_night_line_requires_real_night_mode_and_window(self):
        seg = self.seg(night_start='22:00', night_end='06:00', reserve_soc=41)
        self.assertEqual([], [row for row in care_day_lines([seg], self.day, self.history(1370, 1371)) if row['kind']=='configured_seasonal_night_policy'])
        self.assertEqual([], care_day_lines([seg], self.day, self.night_history(600, 601)))
        self.assertEqual([], care_day_lines([seg], self.day, self.night_history(1320)))
        self.assertEqual([], care_day_lines([seg], self.day, self.night_history(1300, 1301)))

    def test_cross_midnight_night_windows_do_not_draw_daylight(self):
        seg = self.seg(night_start='22:00', night_end='06:00', reserve_soc=43)
        result = care_day_lines([seg], self.day,
                                self.night_history(120, 121, 600, 601, 1320, 1321))
        self.assertEqual([(120, 121), (1320, 1321)],
                         [(r['start_minute'], r['end_minute']) for r in result])

    def test_daytime_night_window_is_respected_without_fabricating_night(self):
        seg = self.seg(night_start='10:00', night_end='12:00', reserve_soc=43)
        result = care_day_lines([seg], self.day, self.night_history(600, 601, 780, 781))
        self.assertEqual([(600, 601)], [(r['start_minute'], r['end_minute']) for r in result])

    def test_night_mode_gaps_stop_synthetic_policy_lines(self):
        seg = self.seg(night_start='20:00', night_end='05:00', reserve_soc=43)
        points = [dict(minute=m, mode=mode) for m, mode in [
            (1300, 'NIGHT_DISCHARGE'), (1301, 'NIGHT_DISCHARGE'), (1302, 'STOP'),
            (1303, 'NIGHT_DISCHARGE'), (1304, 'NIGHT_DISCHARGE'),
            (1310, 'NIGHT_DISCHARGE'), (1311, 'NIGHT_DISCHARGE')]]
        result = care_day_lines([seg], self.day, points)
        self.assertEqual([(1300, 1301), (1303, 1304), (1310, 1311)],
                         [(r['start_minute'], r['end_minute']) for r in result])

    def test_invalid_historical_night_window_proves_no_night_line(self):
        for start, end in [('10:00', '10:00'), ('25:00', '06:00'),
                           ('22:90', '06:00'), ('', '06:00'), ('22:00', None)]:
            with self.subTest(start=start, end=end):
                seg = self.seg(night_start=start, night_end=end)
                self.assertEqual([], care_day_lines([seg], self.day,
                                                     self.night_history(1380, 1381)))

    def test_historical_night_changes_do_not_project_new_floor_backward(self):
        segments = [self.seg(start_minute=0, end_minute=1320, night_start='21:00',
                             night_end='06:00', reserve_soc=40),
                    self.seg(start_minute=1320, end_minute=1440, night_start='21:00',
                             night_end='06:00', reserve_soc=47)]
        result = care_day_lines(segments, self.day, self.night_history(1318, 1319, 1320, 1321))
        self.assertEqual([(1318, 1320, 40), (1320, 1321, 47)],
                         [(r['start_minute'], r['end_minute'], r['night_floor_soc']) for r in result])

    def test_day_api_contains_historical_night_floor_from_recorded_mode(self):
        day = datetime(2026, 1, 5)
        day_string = day.date().isoformat()
        dbpath = str(self.root / 'night_measurement.sqlite3')
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(MEASUREMENT_DB_ENABLED=True, MEASUREMENT_DB_PATH=dbpath,
                   OPERATIONAL_EVENTS_DB_PATH=self.config['OPERATIONAL_EVENTS_DB_PATH'],
                   BATTERY_CARE_ENABLED=True, BATTERY_CARE_SEASON_START_MM_DD='11-01',
                   BATTERY_CARE_SEASON_END_MM_DD='03-31',
                   BATTERY_CARE_RESERVE_SOC_PERCENT=35,
                   BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT=28,
                   BATTERY_CARE_EMERGENCY_SOC_PERCENT=20,
                   BATTERY_CARE_GRID_CHARGE_MAX_POWER_W=700,
                   NIGHT_DISCHARGE_STOP_SOC_PERCENT=46,
                   NIGHT_START_HOUR=22, NIGHT_START_MINUTE=0,
                   NIGHT_END_HOUR=6, NIGHT_END_MINUTE=0,
                   MIN_SOC_PERCENT=12)
        conn = sqlite3.connect(dbpath)
        try:
            record_runtime_config(conn, int(day.timestamp() * 1000), cfg,
                                  compute_config_control_hash(cfg))
        finally:
            conn.close()
        points = [{'epoch_ms': int((day + timedelta(minutes=minute)).timestamp() * 1000),
                   'soc': 39, 'mode': 'NIGHT_DISCHARGE'} for minute in (1380, 1381, 1382)]
        with web_ui._storage_day_lock:
            web_ui._storage_day_cache.clear()
        with patch('web_ui.query_graph_points', return_value=(points, {'db_status': 'ok'})), \
             patch('web_ui.query_measurement_date_range', return_value={'available_from': day_string}):
            result = web_ui.build_storage_soc_day_payload(cfg, {'battery_soc': 39}, day_string)
        self.assertEqual(46, result['care_graph_lines'][0]['night_floor_soc'])
        cfg['NIGHT_DISCHARGE_STOP_SOC_PERCENT'] = 50
        with patch('web_ui.query_graph_points', return_value=(points, {'db_status': 'ok'})), \
             patch('web_ui.query_measurement_date_range', return_value={'available_from': day_string}):
            result_after = web_ui.build_storage_soc_day_payload(cfg, {'battery_soc': 39}, day_string)
        self.assertEqual(46, result_after['care_graph_lines'][0]['night_floor_soc'])


if __name__ == '__main__':
    unittest.main()
