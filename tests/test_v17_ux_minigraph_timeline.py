"""V17 UX mini graph uses bounded actual-time history; no fabricated live samples."""
from pathlib import Path
import unittest
from unittest.mock import patch

from web_ui import build_grid_mini_payload
from status_page_v2 import render_status_page_v2

ROOT = Path(__file__).resolve().parents[1]


class TestMiniGridTimeline(unittest.TestCase):
    def test_timestamped_5_and_15_minute_windows(self):
        now = 1_800_000_000.0
        rows = [
            {'epoch_s': now-1700, 'raw_grid_power_w': 12, 'grid_power_valid': True},
            {'epoch_s': now-600, 'raw_grid_power_w': 20, 'grid_power_valid': True},
            {'epoch_s': now-100, 'raw_grid_power_w': -9, 'grid_power_valid': True},
            {'epoch_s': now-10, 'raw_grid_power_w': 4, 'grid_power_valid': True},
        ]
        snap = {'graph_history': rows}
        five = build_grid_mini_payload(snap, window_minutes=5, now_epoch=now)
        fifteen = build_grid_mini_payload(snap, window_minutes=15, now_epoch=now)
        self.assertEqual([r['value'] for r in five['points']], [-9, 4])
        self.assertEqual([r['value'] for r in fifteen['points']], [20, -9, 4])
        self.assertEqual(five['refresh_interval_s'], 3)
        self.assertEqual(fifteen['to_ms'] - fifteen['from_ms'], 900_000)

    def test_invalid_samples_do_not_turn_into_valid_lines(self):
        now = 1_800_000_000.0
        result = build_grid_mini_payload({'graph_history': [
            {'epoch_s':now-6, 'raw_grid_power_w':30, 'grid_power_valid': False},
            {'epoch_s':now-3, 'raw_grid_power_w':-8, 'grid_power_valid': True},
        ]}, now_epoch=now)
        self.assertIsNone(result['points'][0]['value'])
        self.assertEqual(result['points'][1]['value'], -8)
        self.assertTrue(result['coverage_partial'])

    def test_60_minute_db_history_plus_fresh_controller_tail(self):
        now=1_800_000_000.0
        older={'epoch_ms':int((now-3000)*1000),'value':123}
        result=build_grid_mini_payload({'graph_history':[
            {'epoch_s':now-5,'raw_grid_power_w':-10,'grid_power_valid':True}
        ]},window_minutes=60, history_points=[older],now_epoch=now)
        self.assertEqual(len(result['points']),2)
        self.assertEqual(result['source'],'graph_v3_1min+controller_ram')
        self.assertEqual(result['points'][0]['value'],123)
        self.assertEqual(result['points'][-1]['value'],-10)
        self.assertEqual(result['from_ms'],int((now-3600)*1000))

    def test_no_db_60_minute_coverage_honest_and_input_bounded(self):
        now=1_800_000_000.0
        snap={'graph_history':[{'epoch_s':now-i*3, 'raw_grid_power_w':i}
                               for i in reversed(range(1200))]}
        result=build_grid_mini_payload(snap, window_minutes=60, now_epoch=now)
        self.assertTrue(result['coverage_partial'])
        self.assertLessEqual(result['count'],450)
        self.assertEqual(result['source'],'controller_ram')

    def test_invalid_range_rejected(self):
        with self.assertRaises(ValueError):
            build_grid_mini_payload({},window_minutes=999)

    def test_browser_controls_and_time_geometry_contract(self):
        js=(ROOT/'static/status_v2.js').read_text(encoding='utf-8')
        css=(ROOT/'static/status_v2.css').read_text(encoding='utf-8')
        py=(ROOT/'status_page_v2.py').read_text(encoding='utf-8')
        self.assertIn("apiUrl('/grid-mini-data?window_minutes=15'),3000",js)
        self.assertIn("const x=ms=>",js)
        self.assertIn("ms-previous>",js)
        self.assertIn('data-grid-mini-range="60"',py)
        self.assertIn('aria-pressed',py)
        self.assertIn('.zec-mini-chart-caption',css)
        self.assertNotIn("neuester: ${fmtPower(values.at(-1))}",js)

class TestV1712MiniMinuteSemantics(unittest.TestCase):
    def test_minute_mean_true_samples_and_outlier_range(self):
        now=1_800_000_020.0
        # A whole previous minute, where a short high spike must remain in raw evidence.
        minute=int((now-120)//60)*60
        samples=[20,-200,80]
        snap={'graph_history':[{'epoch_s':minute+2+i*3,'raw_grid_power_w':v}
                               for i,v in enumerate(samples)]}
        p=build_grid_mini_payload(snap,window_minutes=60,now_epoch=now)
        self.assertEqual(p['display_resolution_s'],60)
        self.assertEqual(p['count'],1)
        self.assertAlmostEqual(p['points'][0]['value'],sum(samples)/3)
        self.assertEqual(p['points'][0]['min_raw_w'],-200)
        self.assertEqual(p['points'][0]['max_raw_w'],80)
        self.assertEqual([r['value'] for r in p['raw_points']],samples)
        self.assertEqual(p['points'][0]['sample_count'],3)

    def test_historical_minute_never_passes_as_original_measurement(self):
        now=1_800_000_020.0
        minute=int((now-1800)//60)*60000
        p=build_grid_mini_payload({},window_minutes=60,history_points=[{'epoch_ms':minute,'value':-7}],now_epoch=now)
        self.assertEqual(p['points'][0]['origin'],'graph_v3_1min')
        self.assertEqual(p['points'][0]['interval_end_ms']-p['points'][0]['interval_start_ms'],60000)
        self.assertIsNone(p['points'][0]['min_raw_w'])
        self.assertFalse(p['raw_points'])

    def test_ram_precedence_and_stale_samples_conservative(self):
        now=1_800_000_020.0
        minute=int((now-120)//60)*60
        snap={'graph_history':[{'epoch_s':minute+3,'raw_grid_power_w':99,'grid_power_fresh':False},
                               {'epoch_s':minute+6,'raw_grid_power_w':-30,'grid_power_valid':True}]}
        p=build_grid_mini_payload(snap,window_minutes=60,history_points=[{'epoch_ms':int(minute*1000),'value':200}],now_epoch=now)
        self.assertEqual(p['count'],1)
        self.assertEqual(p['points'][0]['value'],-30)
        self.assertTrue(p['points'][0]['partial_interval'])
        self.assertEqual(p['points'][0]['sample_count'],1)

    def test_missing_minute_is_not_synthesized(self):
        now=1_800_000_020.0
        a=int((now-1200)//60)*60000
        b=a+180000
        p=build_grid_mini_payload({},window_minutes=60,history_points=[{'epoch_ms':a,'value':4},{'epoch_ms':b,'value':-9}],now_epoch=now)
        self.assertEqual([r['epoch_ms'] for r in p['points']],[a,b])

    def test_raw_5_and_15_are_not_aggregated(self):
        now=1_800_000_020.0
        snap={'graph_history':[{'epoch_s':now-9,'raw_grid_power_w':10},{'epoch_s':now-6,'raw_grid_power_w':25}]}
        for minutes in (5,15):
            p=build_grid_mini_payload(snap,window_minutes=minutes,now_epoch=now)
            self.assertEqual([r['value'] for r in p['points']],[10,25])
            self.assertIsNone(p['display_resolution_s'])
            self.assertEqual(p['raw_points'],[])

    def test_grid_footer_uses_natural_height_and_no_clipping(self):
        css=(ROOT/'static/status_v2.css').read_text()
        self.assertIn('.zec-card.zec-grid-card{height:auto;min-height:300px;overflow:visible}',css)
        self.assertIn('.zec-grid-card .zec-card-footer>span:last-child{min-width:0;overflow-wrap:anywhere;white-space:normal}',css)
        js=(ROOT/'static/status_v2.js').read_text()
        self.assertIn('1-Min.-Werte',js)
        self.assertIn('Originalmessung',js)
