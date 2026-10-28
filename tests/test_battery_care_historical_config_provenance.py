"""CP22: durable Care-config provenance for historical SOC timelines."""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from csv_logger import compute_config_control_hash
from graph_config_timeline import (
    backfill_entries, build_day_segments, ensure_graph_config_schema,
    overlay_from_parameters, query_timeline_rows, record_runtime_config,
)


class HistoricalBatteryCareConfigProvenanceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / 'measurement.sqlite3'
        self.config = {'MEASUREMENT_DB_ENABLED': True, 'MEASUREMENT_DB_PATH': str(self.db)}
        self.day = datetime(2026, 1, 5)
        self.start = int(self.day.timestamp() * 1000)

    def _base(self):
        return {
            'MIN_SOC_PERCENT': 12, 'MAX_SOC_PERCENT': 95,
            'NIGHT_DISCHARGE_STOP_SOC_PERCENT': 18,
            'BATTERY_CARE_ENABLED': True,
            'BATTERY_CARE_SEASON_START_MM_DD': '11-01',
            'BATTERY_CARE_SEASON_END_MM_DD': '03-31',
            'BATTERY_CARE_RESERVE_SOC_PERCENT': 35,
            'BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT': 28,
            'BATTERY_CARE_EMERGENCY_SOC_PERCENT': 20,
            'BATTERY_CARE_GRID_CHARGE_MAX_POWER_W': 700,
        }

    def _segments(self):
        return build_day_segments(self.config, self.day, self.day + timedelta(days=1))[0]

    def test_additive_schema_migration_keeps_pre_care_rows_unknown(self):
        conn = sqlite3.connect(self.db)
        conn.execute('''CREATE TABLE graph_config_timeline (
            effective_from_ms INTEGER PRIMARY KEY, config_control_hash TEXT NOT NULL,
            known INTEGER NOT NULL, min_soc REAL, max_soc REAL, reserve_soc REAL,
            night_start TEXT, night_end TEXT, source TEXT NOT NULL)''')
        conn.execute('INSERT INTO graph_config_timeline VALUES(?,?,?,?,?,?,?,?,?)',
                     (self.start, 'precare', 1, 12, 95, 18, '', '', 'historical'))
        conn.commit()
        conn.close()
        # A graph read must not mutate an old DB just to display the day.
        rows, meta = query_timeline_rows(self.config, self.day, self.day + timedelta(days=1))
        self.assertEqual('hit', meta['timeline_status'])
        self.assertEqual('precare', rows[0]['config_control_hash'])
        self.assertIsNone(rows[0]['care_enabled'])
        self.assertIsNone(rows[0]['care_r'])
        conn = sqlite3.connect(self.db)
        ensure_graph_config_schema(conn)
        ensure_graph_config_schema(conn)  # idempotent
        columns = [r[1] for r in conn.execute('PRAGMA table_info(graph_config_timeline)')]
        for key in ('care_enabled', 'care_start', 'care_end', 'care_r', 'care_n', 'care_e'):
            self.assertIn(key, columns)
            self.assertIsNone(conn.execute(f'SELECT {key} FROM graph_config_timeline').fetchone()[0])
        conn.close()
        segments = self._segments()
        self.assertTrue(segments[0]['known'])  # existing legacy boundaries still valid
        self.assertIsNone(segments[0]['care_r'])  # but Care history NOT retroactively known

    def test_all_seven_care_keys_change_control_hash(self):
        base = self._base()
        prior = compute_config_control_hash(base)
        variants = {
            'BATTERY_CARE_ENABLED': False,
            'BATTERY_CARE_SEASON_START_MM_DD': '10-15',
            'BATTERY_CARE_SEASON_END_MM_DD': '04-15',
            'BATTERY_CARE_RESERVE_SOC_PERCENT': 37,
            'BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT': 29,
            'BATTERY_CARE_EMERGENCY_SOC_PERCENT': 18,
            'BATTERY_CARE_GRID_CHARGE_MAX_POWER_W': 500,
        }
        for key, value in variants.items():
            with self.subTest(key=key):
                self.assertNotEqual(prior, compute_config_control_hash(dict(base, **{key: value})))

    def test_config_only_care_transition_creates_distinct_graph_segments(self):
        before = self._base()
        after = dict(before, BATTERY_CARE_RESERVE_SOC_PERCENT=40)
        conn = sqlite3.connect(self.db)
        self.assertTrue(record_runtime_config(conn, self.start, before))
        self.assertFalse(record_runtime_config(conn, self.start, before))
        self.assertTrue(record_runtime_config(conn, self.start + 3600 * 1000, after))
        conn.close()
        segments = self._segments()
        self.assertEqual(2, len(segments))
        self.assertEqual([35, 40], [s['care_r'] for s in segments])
        self.assertEqual([True, True], [bool(s['care_enabled']) for s in segments])
        self.assertEqual([12, 12], [s['min_soc'] for s in segments])
        self.assertEqual(60, segments[1]['start_minute'])
        self.assertEqual('11-01', segments[1]['care_start'])
        self.assertEqual(20, segments[1]['care_e'])

    def test_legacy_snapshot_may_be_known_for_old_limits_but_care_unknown(self):
        legacy = {'MIN_SOC_PERCENT': 11, 'MAX_SOC_PERCENT': 99,
                  'NIGHT_DISCHARGE_STOP_SOC_PERCENT': 16}
        conn = sqlite3.connect(self.db)
        backfill_entries(conn, [(self.start, 'oldhash')], {'oldhash': legacy})
        conn.close()
        segments = self._segments()
        self.assertEqual(11, segments[0]['min_soc'])
        self.assertIsNone(segments[0]['care_enabled'])
        for k in ('care_start', 'care_end', 'care_r', 'care_n', 'care_e'):
            self.assertIsNone(segments[0][k])

    def test_missing_historical_snapshot_never_inherits_today_care(self):
        conn = sqlite3.connect(self.db)
        backfill_entries(conn, [(self.start, 'unknown')], {})
        conn.close()
        segments = self._segments()
        self.assertFalse(segments[0]['known'])
        self.assertIsNone(segments[0]['care_r'])

    def test_disabled_care_is_distinct_from_missing_provenance(self):
        on = self._base()
        off = dict(on, BATTERY_CARE_ENABLED=False)
        conn = sqlite3.connect(self.db)
        record_runtime_config(conn, self.start, on)
        record_runtime_config(conn, self.start + 120000, off)
        conn.close()
        segments = self._segments()
        self.assertEqual([1, 0], [s['care_enabled'] for s in segments])
        self.assertTrue(all(s['care_r'] == 35 for s in segments))
        self.assertNotEqual(None, segments[1]['care_enabled'])

    def test_historical_days_are_not_augmented_with_current_config(self):
        conn = sqlite3.connect(self.db)
        backfill_entries(conn, [(self.start, 'old')], {'old': {'MIN_SOC_PERCENT': 9}})
        conn.close()
        segments, _ = build_day_segments(
            self.config, self.day, self.day + timedelta(days=1),
            current_effective_config=self._base(), now_dt=self.day + timedelta(days=5)
        )
        self.assertEqual(1, len(segments))
        self.assertIsNone(segments[0]['care_r'])

    def test_care_unknown_for_non_boolean_snapshot_enabled(self):
        for value in (None, 'true', 1, 0, 'False'):
            with self.subTest(value=value):
                overlay = overlay_from_parameters({'BATTERY_CARE_ENABLED': value})
                self.assertIsNone(overlay['care_enabled'])
        self.assertEqual(0, overlay_from_parameters({'BATTERY_CARE_ENABLED': False})['care_enabled'])


if __name__ == '__main__':
    unittest.main()
