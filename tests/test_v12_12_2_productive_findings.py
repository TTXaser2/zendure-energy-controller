import csv
import json
import inspect
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

import types
if "paho" not in sys.modules:
    paho = types.ModuleType("paho")
    paho_mqtt = types.ModuleType("paho.mqtt")
    paho_client = types.ModuleType("paho.mqtt.client")
    paho_client.CallbackAPIVersion = types.SimpleNamespace(VERSION2=object())
    paho_client.Client = lambda *args, **kwargs: types.SimpleNamespace(
        on_message=None, on_connect=None, on_disconnect=None,
        username_pw_set=lambda *a, **k: None, connect=lambda *a, **k: None,
        loop_start=lambda *a, **k: None, subscribe=lambda *a, **k: None,
        publish=lambda *a, **k: types.SimpleNamespace(rc=0),
    )
    sys.modules["paho"] = paho
    sys.modules["paho.mqtt"] = paho_mqtt
    sys.modules["paho.mqtt.client"] = paho_client

from config_manager import DEFAULT_CONFIG
import ZendureController as main_module
from instance_owner import INSTANCE_LOCK_EXIT_CODE, InstanceLockHeldError, acquire_instance_lock
from csv_logger import CsvRotatingLogger
from measurement_v4 import MeasurementV4Logger
from tests.test_measurement_v4_writer import base_config as measurement_config, base_row as measurement_row
from tests.test_operation_priority import DummyConfigManager, RecordingMqtt, OkShelly, NoopCsv, NoopZendureApi, NoopLogger
from tests.test_v12_10_rc6_cross_charge import state_with_second_battery
from controller_logic import ZendureController


class SingleInstanceOwnerTests(unittest.TestCase):
    def _try_lock_subprocess(self, lock_path: str, cwd: str, hold_s: float = 0.0):
        code = textwrap.dedent(f"""
            import sys,time
            sys.path.insert(0,{str(Path(__file__).resolve().parents[1])!r})
            from instance_owner import acquire_instance_lock, InstanceLockHeldError, INSTANCE_LOCK_EXIT_CODE
            try:
                owner=acquire_instance_lock({lock_path!r}, build_id='test-build')
            except InstanceLockHeldError:
                print('HELD')
                raise SystemExit(INSTANCE_LOCK_EXIT_CODE)
            print('OWNER', flush=True)
            time.sleep({hold_s!r})
            owner.close()
        """)
        return subprocess.run([sys.executable, "-c", code], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_same_and_different_cwd_second_start_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            lock_path = os.path.join(tmp, "owner.lock")
            owner = acquire_instance_lock(lock_path, build_id="owner")
            try:
                for cwd in (tmp, other):
                    result = self._try_lock_subprocess(lock_path, cwd)
                    self.assertEqual(INSTANCE_LOCK_EXIT_CODE, result.returncode, result.stderr)
                    self.assertIn("HELD", result.stdout)
            finally:
                owner.close()

    def test_default_lock_path_is_absolute_and_cwd_independent(self):
        from instance_owner import INSTANCE_LOCK_PATH
        self.assertEqual('/opt/zendure-controller/zendure_controller.instance.lock', INSTANCE_LOCK_PATH)
        self.assertTrue(os.path.isabs(INSTANCE_LOCK_PATH))

    def test_clean_owner_release_allows_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path=os.path.join(tmp,'owner.lock')
            first=acquire_instance_lock(lock_path,build_id='first')
            first.close()
            second=acquire_instance_lock(lock_path,build_id='second')
            try:
                self.assertEqual('second',second.build_id)
            finally:
                second.close()

    def test_nearly_simultaneous_starts_have_exactly_one_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "owner.lock")
            script = textwrap.dedent(f"""
                import sys,time
                sys.path.insert(0,{str(Path(__file__).resolve().parents[1])!r})
                from instance_owner import acquire_instance_lock, InstanceLockHeldError, INSTANCE_LOCK_EXIT_CODE
                try:
                    owner=acquire_instance_lock({lock_path!r}, build_id='race')
                except InstanceLockHeldError:
                    print('HELD', flush=True); raise SystemExit(INSTANCE_LOCK_EXIT_CODE)
                print('OWNER', flush=True); time.sleep(0.5); owner.close()
            """)
            p1=subprocess.Popen([sys.executable,"-c",script],cwd=tmp,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            p2=subprocess.Popen([sys.executable,"-c",script],cwd=tmp,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out1,err1=p1.communicate(timeout=5); out2,err2=p2.communicate(timeout=5)
            owners=sum('OWNER' in out for out in (out1,out2))
            held=sum('HELD' in out for out in (out1,out2))
            self.assertEqual((1,1),(owners,held),(out1,err1,out2,err2))

    def test_hard_process_death_releases_kernel_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path=os.path.join(tmp,"owner.lock")
            script=textwrap.dedent(f"""
                import os,sys,time
                sys.path.insert(0,{str(Path(__file__).resolve().parents[1])!r})
                from instance_owner import acquire_instance_lock
                owner=acquire_instance_lock({lock_path!r}, build_id='crash')
                print('OWNER', flush=True)
                time.sleep(30)
            """)
            proc=subprocess.Popen([sys.executable,"-c",script],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertEqual('OWNER',proc.stdout.readline().strip())
            proc.kill(); proc.wait(timeout=5)
            proc.stdout.close(); proc.stderr.close()
            owner=acquire_instance_lock(lock_path, build_id='recovery')
            owner.close()

    def test_rejected_main_starts_before_runtime_imports(self):
        exc=InstanceLockHeldError('/opt/zendure-controller/zendure_controller.instance.lock', {'pid':123})
        imported=[]
        real_import=__import__
        def spy_import(name,*args,**kwargs):
            imported.append(name)
            return real_import(name,*args,**kwargs)
        with mock.patch.object(main_module,'acquire_instance_lock',side_effect=exc), \
             mock.patch('builtins.__import__',side_effect=spy_import), \
             self.assertRaises(SystemExit) as cm:
            main_module.main()
        self.assertEqual(INSTANCE_LOCK_EXIT_CODE, cm.exception.code)
        runtime_modules={'uvicorn','app_logger','config_manager','controller_logic','csv_logger','mqtt_bridge','shelly_client','sma_energy_meter','state','web_ui','zendure_local_api'}
        self.assertTrue(runtime_modules.isdisjoint(imported), imported)


class HarvestMonotonicObservationTests(unittest.TestCase):
    def cfg(self, **overrides):
        cfg=dict(DEFAULT_CONFIG)
        cfg.update({
            'REST_SURPLUS_HARVEST_ENABLED':True,'CROSS_CHARGE_ENABLED':True,
            'SECOND_BATTERY_MAX_CHARGE_POWER_W':2300,'REST_SURPLUS_MIN_EXPORT_W':80,
            'REST_SURPLUS_ENTRY_CONFIRM_SECONDS':30,'HARVEST_HIGH_SMA_SOC_ENABLED':False,
            'INTERVAL_SECONDS':3,'GRID_METER_SOURCE':'shelly_http','SHELLY_STALE_TIMEOUT_SECONDS':15,
            'SECOND_BATTERY_STALE_TIMEOUT_SECONDS':30,'MAX_SOC_PERCENT':99,
        }); cfg.update(overrides); return cfg

    def make(self,cfg):
        state=state_with_second_battery(+2250,soc=50)
        state.battery_soc=50
        state.second_battery_data_valid=True; state.second_battery_data_fresh=True
        ctrl=ZendureController(DummyConfigManager(cfg),state,RecordingMqtt(),OkShelly(-100),NoopCsv(),NoopZendureApi(),NoopLogger())
        return ctrl,state

    def observe(self,state,seq):
        state.grid_power_sample_epoch=1000.0+seq
        state.last_sma_battery_update_epoch=2000.0+seq

    def test_nominal_30_seconds_matches_previous_ten_cycle_behavior(self):
        cfg=self.cfg(); ctrl,state=self.make(cfg)
        times=[100+3*i for i in range(10)]
        with mock.patch('controller_logic.time.monotonic',side_effect=times):
            for i in range(10):
                self.observe(state,i); ctrl.update_rest_surplus_harvest_state(cfg,-100)
                if i<9:self.assertFalse(state.rest_surplus_harvest_active)
        self.assertTrue(state.rest_surplus_harvest_active)
        self.assertEqual(30.0,state.rest_surplus_entry_progress_s)

    def test_identical_observation_does_not_advance(self):
        cfg=self.cfg(); ctrl,state=self.make(cfg); self.observe(state,1)
        with mock.patch('controller_logic.time.monotonic',side_effect=[100,103,106]):
            ctrl.update_rest_surplus_harvest_state(cfg,-100)
            first=state.rest_surplus_entry_progress_s
            ctrl.update_rest_surplus_harvest_state(cfg,-100)
            ctrl.update_rest_surplus_harvest_state(cfg,-100)
        self.assertEqual(first,state.rest_surplus_entry_progress_s)

    def test_jitter_uses_monotonic_elapsed_time(self):
        cfg=self.cfg(REST_SURPLUS_ENTRY_CONFIRM_SECONDS=14); ctrl,state=self.make(cfg)
        with mock.patch('controller_logic.time.monotonic',side_effect=[100,104,106,111]):
            for i in range(4): self.observe(state,i); ctrl.update_rest_surplus_harvest_state(cfg,-100)
        self.assertEqual(14.0,state.rest_surplus_entry_progress_s)
        self.assertTrue(state.rest_surplus_harvest_active)

    def test_long_stall_breaks_entry_continuity_instead_of_crediting_stall(self):
        cfg=self.cfg(); ctrl,state=self.make(cfg)
        with mock.patch('controller_logic.time.monotonic',side_effect=[100,103,106,140]):
            for i in range(4): self.observe(state,i); ctrl.update_rest_surplus_harvest_state(cfg,-100)
        self.assertEqual(3.0,state.rest_surplus_entry_progress_s)
        self.assertFalse(state.rest_surplus_harvest_active)

    def test_hold_advances_only_on_distinct_observations(self):
        cfg=self.cfg(HARVEST_HIGH_SMA_SOC_EXIT_PERCENT=40, HARVEST_HIGH_SMA_SOC_HOLD_SECONDS=9)
        ctrl,state=self.make(cfg)
        state.rest_surplus_harvest_active=True
        state.rest_surplus_harvest_reason='SMA_NEAR_LIMIT'
        state.rest_surplus_hold_remaining_s=9.0
        self.observe(state,1)
        with mock.patch('controller_logic.time.monotonic',side_effect=[100,103]):
            ctrl.update_rest_surplus_harvest_state(cfg,0)
            after_fresh=state.rest_surplus_hold_remaining_s
            ctrl.update_rest_surplus_harvest_state(cfg,0)
        self.assertEqual(6.0,after_fresh)
        self.assertEqual(after_fresh,state.rest_surplus_hold_remaining_s)

    def test_long_stall_does_not_consume_full_hold_duration(self):
        cfg=self.cfg(HARVEST_HIGH_SMA_SOC_EXIT_PERCENT=40, HARVEST_HIGH_SMA_SOC_HOLD_SECONDS=9)
        ctrl,state=self.make(cfg)
        state.rest_surplus_harvest_active=True
        state.rest_surplus_harvest_reason='SMA_NEAR_LIMIT'
        state.rest_surplus_hold_remaining_s=9.0
        with mock.patch('controller_logic.time.monotonic',side_effect=[100,140]):
            self.observe(state,1); ctrl.update_rest_surplus_harvest_state(cfg,0)
            self.observe(state,2); ctrl.update_rest_surplus_harvest_state(cfg,0)
        self.assertEqual(3.0,state.rest_surplus_hold_remaining_s)
        self.assertTrue(state.rest_surplus_harvest_active)

    def test_wall_clock_jumps_do_not_change_entry_progress(self):
        cfg=self.cfg(); ctrl,state=self.make(cfg)
        with mock.patch('controller_logic.time.monotonic',side_effect=[100,103,106]), \
             mock.patch('controller_logic.time.time',side_effect=[9999999999,-9999999999,1234567890]):
            for i in range(3):
                self.observe(state,i); ctrl.update_rest_surplus_harvest_state(cfg,-100)
        self.assertEqual(9.0,state.rest_surplus_entry_progress_s)

    def test_reset_discards_old_observation_timing_state(self):
        cfg=self.cfg(); ctrl,state=self.make(cfg)
        with mock.patch('controller_logic.time.monotonic',side_effect=[100,103,1000]):
            self.observe(state,1); ctrl.update_rest_surplus_harvest_state(cfg,-100)
            self.observe(state,2); ctrl.update_rest_surplus_harvest_state(cfg,-100)
            self.assertEqual(6.0,state.rest_surplus_entry_progress_s)
            ctrl._reset_rest_surplus_harvest('TEST_RESET')
            self.observe(state,3); ctrl.update_rest_surplus_harvest_state(cfg,-100)
        self.assertEqual(3.0,state.rest_surplus_entry_progress_s)

    def test_reset_clears_sticky_current_limiter_reason(self):
        cfg=self.cfg(); ctrl,state=self.make(cfg)
        state.harvest_limiter_reason='EXPORT_CAPTURE'
        ctrl._reset_rest_surplus_harvest('DISABLED')
        self.assertEqual('',state.harvest_limiter_reason)
        self.assertEqual('NOT_APPLICABLE',state.harvest_target_semantics)


class MeasurementManifestLifecycleTests(unittest.TestCase):
    def _manifest(self,tmp):
        return json.loads(Path(tmp,'zec_measurement_manifest.json').read_text(encoding='utf-8'))

    def _csv_rows(self,path):
        with open(path,newline='',encoding='utf-8') as f:
            return len(list(csv.DictReader(f,delimiter=';')))

    def test_clean_close_sets_closed_time_and_exact_row_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=measurement_config(tmp); logger=CsvRotatingLogger()
            logger.log(cfg,measurement_row()); r2=measurement_row();r2['cycle_id']=2;r2['epoch_s']+=3;logger.log(cfg,r2)
            logger.close(); m=self._manifest(tmp); e=m['files'][0]; path=Path(tmp,e['file_name'])
            self.assertTrue(e['closed_time_utc'])
            self.assertEqual(self._csv_rows(path),e['row_count'])

    def test_open_file_is_distinguishable_from_cleanly_closed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=measurement_config(tmp); logger=CsvRotatingLogger();logger.log(cfg,measurement_row())
            e=self._manifest(tmp)['files'][0]
            self.assertEqual('',e.get('closed_time_utc',''))
            logger.close()


    def test_manifest_finalizer_uses_in_memory_row_count_without_file_scan(self):
        src=inspect.getsource(MeasurementV4Logger._finalize_manifest)
        self.assertIn('_row_counts',src)
        self.assertNotIn('open(',src)
        self.assertNotIn('read_text(',src)

    def test_size_rotation_marks_new_file_reason_and_closes_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=measurement_config(tmp); cfg['MEASUREMENT_LOG_MAX_BYTES']=1
            logger=CsvRotatingLogger(); logger.log(cfg,measurement_row())
            r2=measurement_row();r2['cycle_id']=2;r2['epoch_s']+=3;logger.log(cfg,r2);logger.close()
            entries=self._manifest(tmp)['files']
            self.assertGreaterEqual(len(entries),2)
            self.assertEqual('SERVICE_START',entries[0]['rotation_reason'])
            self.assertTrue(entries[0]['closed_time_utc'])
            self.assertTrue(any(e['rotation_reason']=='SIZE_LIMIT' for e in entries[1:]))
            for e in entries:
                self.assertEqual(self._csv_rows(Path(tmp,e['file_name'])),e['row_count'])
                self.assertTrue(e['closed_time_utc'])


class UiFieldFixContractTests(unittest.TestCase):

    def test_status_diagnostics_expose_instance_owner(self):
        from web_ui import build_health_payload, build_ready_payload
        snap={
            'instance_owner_active':True,
            'instance_owner_pid':4242,
            'instance_owner_build_id':'v12.13.0-20260811',
            'instance_owner_since_utc':'2026-08-10T12:00:00Z',
            'instance_owner_lock_path':'/opt/zendure-controller/zendure_controller.instance.lock',
        }
        health=build_health_payload(snap)
        self.assertEqual(True,health['instance_owner']['active'])
        self.assertEqual(4242,health['instance_owner']['pid'])
        self.assertEqual('v12.13.0-20260811',health['instance_owner']['build_id'])
        self.assertNotIn('lock_path',health['instance_owner'])

    def test_desktop_info_panel_is_click_pinned_not_hover_lifecycle(self):
        js=Path('static/status_v2.js').read_text(encoding='utf-8')
        self.assertNotIn("addEventListener('mouseenter'",js)
        self.assertNotIn("pop.addEventListener('mouseleave'",js)
        self.assertIn("addEventListener('click'",js)

    def test_mobile_soc_details_are_docked_outside_canvas(self):
        html=Path('status_page_v2.py').read_text(encoding='utf-8')
        js=Path('static/status_v2.js').read_text(encoding='utf-8')
        self.assertIn('storageSocMobileDetails',html)
        self.assertIn('showSocDetails',js)
        self.assertIn("this.mobileQuery.matches",js)


if __name__=='__main__': unittest.main()
