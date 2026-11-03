#!/usr/bin/env python3
"""Synthetic offline smoke/contract tests, no production Pi / no MQTT."""
import csv
import importlib.util
import json
import sqlite3
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'tools' / 'zec_battery_care_7d_readonly.py'
spec = importlib.util.spec_from_file_location('batterycare', MODULE)
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)


class ExtractorTests(unittest.TestCase):
    def test_policy_window(self):
        row = {'care_start': '10-15', 'care_end': '03-15'}
        ts = lambda y,m,d: int(datetime(y,m,d,tzinfo=timezone.utc).timestamp()*1000)
        self.assertTrue(bc.in_care_season(ts(2026,11,2), row))
        self.assertFalse(bc.in_care_season(ts(2026,7,2), row))
        self.assertIsNone(bc.in_care_season(ts(2026,7,2), {'care_start':'', 'care_end':''}))

    def test_full_synthetic_readonly_and_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            logs = root / 'logs'; logs.mkdir()
            (root/'config.json').write_text(json.dumps({'MEASUREMENT_LOG_DIR':'logs'}))
            measurement = logs / 'zec_measurements.sqlite3'
            start = int(datetime(2026,10,29,4,49,0,tzinfo=timezone.utc).timestamp()*1000)
            conn = sqlite3.connect(measurement)
            conn.executescript('''
               CREATE TABLE measurement_raw (ts_ms INTEGER PRIMARY KEY, grid_power_w REAL,
                    zendure_target_power_w REAL, zendure_actual_power_w REAL, soc_percent REAL,
                    mode TEXT, control_reason TEXT, soc_valid INTEGER, grid_valid INTEGER,
                    primary_soc_percent REAL, primary_power_w REAL, safe_state_active INTEGER,
                    cross_charge_limited INTEGER, night_window_active INTEGER, night_reserve_active INTEGER,
                    config_control_hash TEXT);
               CREATE TABLE graph_config_timeline (effective_from_ms INTEGER PRIMARY KEY,
                    config_control_hash TEXT, known INTEGER, min_soc REAL, max_soc REAL,
                    reserve_soc REAL, night_start TEXT, night_end TEXT, care_enabled INTEGER,
                    care_start TEXT, care_end TEXT, care_r REAL, care_n REAL, care_e REAL, source TEXT);
            ''')
            conn.execute('INSERT INTO graph_config_timeline VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                         (start-10000,'hash01',1,10,99,35,'22:00','05:30',1,'10-15','03-15',17,13,10,'runtime'))
            for t, soc, target, power, reason in (
                (0, 18,-697,-676,'AUTO_GRID_IMPORT'),
                (3, 17,0,-675,'Battery Care: geschützte saisonale Reserve erreicht'),
                (6, 17,0,-675,'Battery Care: geschützte saisonale Reserve erreicht'),
                (9, 17,0,0,'Battery Care: geschützte saisonale Reserve erreicht'),
                (12,17,0,0,'Battery Care: geschützte saisonale Reserve erreicht')):
                conn.execute('INSERT INTO measurement_raw VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                             (start+t*1000,12,target,power,soc,'HOLD',reason,1,1,80,0,0,0,0,0,'hash01'))
            conn.commit(); conn.close()
            ev = sqlite3.connect(logs/'zec_operational_events.sqlite3')
            ev.execute('''CREATE TABLE operational_events(id INTEGER PRIMARY KEY, event_type TEXT,
                severity TEXT,title TEXT,started_at REAL,ended_at REAL,status TEXT,
                occurrence_count INTEGER,detail_json TEXT)''')
            ev.execute('INSERT INTO operational_events VALUES (1,?,?,?,?,?,?,?,?)',
                       ('battery_care_stage_transition','info','Battery Care: Stufenwechsel',start/1000,
                        start/1000,'resolved',1,'{"stage_to":"RESERVE_POLICY","secret":"omit_me"}'))
            ev.commit(); ev.close()
            v4 = logs / 'zendure_measurements_v4_20261029T044900Z.csv'
            with v4.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['schema_version','measurement_epoch_ms','zendure_soc_percent',
                                                'zendure_actual_power_valid', 'zendure_actual_power_w'],delimiter=';')
                w.writeheader()
                w.writerow({'schema_version':4,'measurement_epoch_ms':start,'zendure_soc_percent':18,
                            'zendure_actual_power_valid':1,'zendure_actual_power_w':-676})
            outs = root/'Downloads'
            result = bc.main(['--root',str(root),'--output-dir',str(outs),
                              '--from','2026-10-29T05:40','--until','2026-10-29T06:00'])
            # The test timestamps above are UTC and local Berlin is +1 in October after DST.
            # Time window local 05:40-06:00 covers 04:49 UTC.
            self.assertEqual(result,0)
            archives=list(outs.glob('*.zip'))
            self.assertEqual(len(archives),1)
            with zipfile.ZipFile(archives[0]) as z:
                self.assertIsNone(z.testzip())
                reportname=next(x for x in z.namelist() if x.endswith('/report.json'))
                report=json.loads(z.read(reportname))
                self.assertEqual(report['sqlite_graph']['rows'],5)
                self.assertEqual(report['v4']['rows_selected'],1)
                self.assertEqual(report['events']['types']['battery_care_stage_transition'],1)
                self.assertEqual(report['sqlite_graph']['reserve_graph_candidates'], {'GRAPH_NEUTRALITY_CANDIDATE':1})
                extracted=z.read(next(x for x in z.namelist() if x.endswith('/care_and_context_events.csv')))
                self.assertNotIn(b'omit_me',extracted)
            # Source SQLite tables and user config remain bytewise untouched.
            check=sqlite3.connect(measurement)
            self.assertEqual(check.execute('SELECT count(*) FROM measurement_raw').fetchone()[0],5)
            check.close()


if __name__=='__main__':
    unittest.main()

class CorrectedExtractorTests(unittest.TestCase):
    def test_file_selection_window_not_mtime_or_historical_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); logs=root/'logs'; logs.mkdir()
            for d in range(1,30):
                for h in range(0,24):
                    (logs/f'z endure').write_text('') if False else None
                    (logs/f'zendure_measurements_v4_202610{d:02d}T{h:02d}0000Z.csv').touch()
            # 696 inventory files, only 2 time-relevant + predecessor
            start=int(datetime(2026,10,29,8,tzinfo=timezone.utc).timestamp()*1000)
            end=int(datetime(2026,10,29,10,tzinfo=timezone.utc).timestamp()*1000)
            warnings=[]
            files, stats=bc.discover_v4(root,{},[],[],warnings,start,end)
            self.assertEqual(stats['files_discovered'],696)
            self.assertEqual(stats['files_eligible'],3)
            self.assertEqual(stats['files_selected'],3)
            self.assertFalse(stats['file_selection_truncated'])
            self.assertEqual([bc.timestamped_filename(p) for p in files], sorted(bc.timestamped_filename(p) for p in files))

    def test_sqlite_sparse_fallback_has_v4_nonzero_energy_not_false_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); logs=root/'logs'; logs.mkdir()
            (root/'config.json').write_text('{}')
            start=int(datetime(2026,11,1,8,tzinfo=timezone.utc).timestamp()*1000)
            db=sqlite3.connect(logs/'zec_measurements.sqlite3')
            db.execute('CREATE TABLE measurement_raw (ts_ms INTEGER PRIMARY KEY, soc_percent REAL, soc_valid INTEGER, zendure_actual_power_w REAL, grid_power_w REAL, grid_valid INTEGER)')
            for i in range(3): db.execute('INSERT INTO measurement_raw (ts_ms) VALUES (?)',(start+3000*i,))
            db.commit();db.close()
            fields=['schema_version','measurement_epoch_ms','zendure_soc_percent','zendure_soc_valid','zendure_soc_fresh','grid_power_w','grid_power_valid','grid_power_fresh','zendure_actual_power_w','zendure_actual_power_valid','zendure_actual_power_fresh']
            with (logs/'zendure_measurements_v4_20261101T080000Z.csv').open('w',newline='') as handle:
                w=csv.DictWriter(handle,fieldnames=fields,delimiter=';');w.writeheader()
                for i in range(3):
                    w.writerow(dict(schema_version='4',measurement_epoch_ms=start+i*3000,
                        zendure_soc_percent=19,zendure_soc_valid=1,zendure_soc_fresh=1,
                        grid_power_w=100,grid_power_valid=1,grid_power_fresh=1,
                        zendure_actual_power_w=900,zendure_actual_power_valid=1,zendure_actual_power_fresh=1))
            outs=root/'out'
            self.assertEqual(bc.main(['--root',str(root),'--output-dir',str(outs),'--from','2026-11-01T08:55','--until','2026-11-01T09:10']),0)
            with zipfile.ZipFile(next(outs.glob('*.zip'))) as z:
                report=json.loads(z.read(next(n for n in z.namelist() if n.endswith('report.json'))))
                self.assertFalse(report['sqlite_core_usable'])
                self.assertEqual(report['daily_recalculation']['daily_source'],'V4_VALID_FRESH')
                self.assertIn('SQLITE_CORE_DATA_EMPTY',','.join(report['warnings']))
                d=list(csv.DictReader(__import__('io').StringIO(z.read(next(n for n in z.namelist() if n.endswith('daily_summary.csv'))).decode())))
                self.assertEqual(len(d),1)
                self.assertEqual(d[0]['v4_samples'],'3')
                self.assertGreater(float(d[0]['observed_charge_kwh']),0.001)
                self.assertGreater(float(d[0]['observed_grid_import_kwh']),0)

    def test_no_valid_daily_source_no_fabricated_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); logs=root/'logs'; logs.mkdir()
            start=int(datetime(2026,11,1,8,tzinfo=timezone.utc).timestamp()*1000)
            db=sqlite3.connect(logs/'zec_measurements.sqlite3')
            db.execute('CREATE TABLE measurement_raw (ts_ms INTEGER PRIMARY KEY)')
            db.execute('INSERT INTO measurement_raw VALUES (?)',(start,));db.commit();db.close()
            outs=root/'out'
            bc.main(['--root',str(root),'--output-dir',str(outs),'--from','2026-11-01T08:55','--until','2026-11-01T09:10'])
            with zipfile.ZipFile(next(outs.glob('*.zip'))) as z:
                r=json.loads(z.read(next(n for n in z.namelist() if n.endswith('report.json'))))
                self.assertEqual(r['daily_recalculation']['daily_source'],'NOT_EVALUABLE')
                self.assertIn('SQLITE_CORE_COLUMNS_MISSING',','.join(r['warnings']))
                daily=z.read(next(n for n in z.namelist() if n.endswith('daily_summary.csv')))
                self.assertEqual(daily.decode().splitlines(),['date,source,status'])
