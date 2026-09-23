import sys
import time
import types
import unittest

# Unit tests do not need a real broker client.
if "paho" not in sys.modules:
    paho = types.ModuleType("paho")
    paho_mqtt = types.ModuleType("paho.mqtt")
    paho_client = types.ModuleType("paho.mqtt.client")
    paho_client.CallbackAPIVersion = types.SimpleNamespace(VERSION2=object())
    paho_client.Client = lambda *args, **kwargs: types.SimpleNamespace()
    sys.modules["paho"] = paho
    sys.modules["paho.mqtt"] = paho_mqtt
    sys.modules["paho.mqtt.client"] = paho_client

from config_manager import DEFAULT_CONFIG
from controller_logic import ZendureController
from state import ControllerState


class DummyConfigManager:
    def __init__(self, cfg):
        self.cfg = dict(cfg)

    def get(self):
        return self.cfg


class DummyMqtt:
    pass


class DummyShelly:
    pass


class DummyCsv:
    pass


class DummyApi:
    pass


class DummyLogger:
    def log(self, *_args, **_kwargs):
        pass


def fast_cfg(mode="active", **overrides):
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(
        {
            "HARVEST_FAST_CAPTURE_MODE": mode,
            "MANUAL_MODE": "AUTO",
            "REST_SURPLUS_HARVEST_ENABLED": True,
            "CROSS_CHARGE_ENABLED": True,
            "SECOND_BATTERY_INTEGRATION_ENABLED": True,
            "SECOND_BATTERY_MAX_CHARGE_POWER_W": 2300,
            "MAX_CHARGE_POWER_W": 2400,
            "MAX_SOC_PERCENT": 100,
            "SHELLY_STALE_TIMEOUT_SECONDS": 30,
            "ZENDURE_COMMAND_STATE_FRESH_SECONDS": 30,
            "SMOOTHING_FACTOR": 0.25,
            "MAX_POWER_STEP_W": 150,
            "MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W": 150,
        }
    )
    cfg.update(overrides)
    return cfg


def make_controller(cfg):
    state = ControllerState()
    controller = ZendureController(
        DummyConfigManager(cfg),
        state,
        DummyMqtt(),
        DummyShelly(),
        DummyCsv(),
        DummyApi(),
        DummyLogger(),
    )
    return controller, state


def make_fast_ready(
    state,
    *,
    primary_soc=100.0,
    primary_power=10.0,
    effective_export=500,
    grid_power=-500.0,
    zendure_soc=70.0,
):
    now = time.time()
    with state.lock:
        state.battery_soc = zendure_soc
        state.last_soc_update_epoch = now
        state.grid_power = grid_power
        state.grid_power_valid = True
        state.grid_power_sample_epoch = now
        state.effective_export_power = int(effective_export)
        state.effective_export_power_valid = True
        state.sma_battery_soc = primary_soc
        state.sma_battery_display_power = primary_power
        state.last_sma_battery_update_epoch = now
        state.last_sma_battery_update_monotonic = time.monotonic()
        state.second_battery_data_valid = True
        state.second_battery_data_fresh = True
        state.actual_zendure_power_valid = True
        state.zendure_power_observation_direction = "IDLE"
        state.zendure_power_observation_confidence = "HIGH"
        state.zendure_power_observation_signed_w = 0
        state.zendure_power_observation_updated_epoch = now
        state.mqtt_connected = True
        state.mqtt_command_path_valid = True
        state.zendure_flash_protection_active = True
        state.zendure_command_state_complete = True
        state.command_state_gate_state = "READY"
        state.zendure_command_smart_mode = 1
        state.zendure_command_ac_mode = "Input mode"
        state.zendure_command_input_limit_w = 0
        state.zendure_command_output_limit_w = 0
        state.zendure_command_smart_mode_updated_epoch = now
        state.zendure_command_ac_mode_updated_epoch = now
        state.zendure_command_input_limit_updated_epoch = now
        state.zendure_command_output_limit_updated_epoch = now


def advance_observation(controller, state, seconds=3.0, *, effective_export=None, grid_power=None):
    controller._fast_capture_last_observation_monotonic = time.monotonic() - seconds
    now = time.time()
    with state.lock:
        state.grid_power_sample_epoch = now
        state.last_sma_battery_update_epoch = now
        state.last_soc_update_epoch = now
        state.zendure_power_observation_updated_epoch = now
        if effective_export is not None:
            state.effective_export_power = int(effective_export)
        if grid_power is not None:
            state.grid_power = float(grid_power)


class FastCaptureCoreTests(unittest.TestCase):
    def test_mode_off_is_target_identity(self):
        cfg = fast_cfg(mode="off")
        controller, state = make_controller(cfg)
        make_fast_ready(state)
        self.assertEqual(700, controller._fast_capture_step(cfg, -500.0, 700))
        self.assertEqual(0, state.fast_capture_overlay_w)
        self.assertFalse(state.fast_capture_active)

    def test_full_idle_requires_fifteen_seconds_distinct_fresh_evidence(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=100.0, primary_power=10.0, effective_export=600)
        controller._fast_capture_step(cfg, -600.0, 400)
        for _ in range(4):
            advance_observation(controller, state, 3.0)
            controller._fast_capture_step(cfg, -600.0, 400)
        self.assertEqual("RESERVE_UNKNOWN", state.fast_capture_primary_state)
        self.assertLess(state.fast_capture_full_idle_progress_s, 15.0)
        advance_observation(controller, state, 3.1)
        controller._fast_capture_step(cfg, -600.0, 400)
        self.assertEqual("FULL_IDLE", state.fast_capture_primary_state)

    def test_duplicate_observation_does_not_advance_full_idle(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=100.0, primary_power=10.0, effective_export=600)
        controller._fast_capture_step(cfg, -600.0, 400)
        controller._fast_capture_last_observation_monotonic = time.monotonic() - 5.0
        controller._fast_capture_step(cfg, -600.0, 400)
        self.assertEqual(0.0, state.fast_capture_full_idle_progress_s)
        self.assertFalse(state.fast_capture_observation_distinct)

    def test_near_limit_a400_attack_and_primary_reserve(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=80.0, primary_power=2200.0, effective_export=800)
        self.assertEqual(1000, controller._fast_capture_step(cfg, -800.0, 1000))
        advance_observation(controller, state, 1.0)
        combined = controller._fast_capture_step(cfg, -800.0, 1000)
        self.assertGreaterEqual(combined, 1390)
        self.assertLessEqual(combined, 1410)
        self.assertEqual("NEAR_LIMIT", state.fast_capture_primary_state)
        self.assertEqual(100, state.fast_capture_primary_reserve_w)
        self.assertTrue(state.fast_capture_attack_limited)

    def test_valid_100_to_149_w_export_is_not_suppressed_by_baseline_threshold(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=80.0, primary_power=2300.0, effective_export=120, grid_power=-120)
        controller._publish_signed_target = lambda target, **_kwargs: int(target)
        controller._fast_capture_step(cfg, -120.0, 0)
        advance_observation(controller, state, 1.0, effective_export=120, grid_power=-120)
        combined = controller._fast_capture_step(cfg, -120.0, 0)
        self.assertEqual(120, combined)
        self.assertEqual(120, state.fast_capture_overlay_w)

    def test_reserve_unknown_hard_zeros_existing_overlay(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=80.0, primary_power=1000.0, effective_export=800)
        controller._fast_capture_last_mode = "active"
        with state.lock:
            state.fast_capture_overlay_w = 300
            state.fast_capture_active = True
        combined = controller._fast_capture_step(cfg, -800.0, 500)
        self.assertEqual(500, combined)
        self.assertEqual(0, state.fast_capture_overlay_w)
        self.assertEqual("RESERVE_UNKNOWN", state.fast_capture_primary_state)

    def test_import_over_100_w_hard_aborts_overlay(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=80.0, primary_power=2200.0, effective_export=0, grid_power=150)
        controller._fast_capture_last_mode = "active"
        with state.lock:
            state.fast_capture_overlay_w = 350
            state.fast_capture_active = True
        combined = controller._fast_capture_step(cfg, 150.0, 500)
        self.assertEqual(500, combined)
        self.assertEqual(0, state.fast_capture_overlay_w)
        self.assertEqual("GRID_IMPORT_ABORT", state.fast_capture_forced_zero_reason)

    def test_shadow_runs_overlay_model_without_target_effect(self):
        cfg = fast_cfg(mode="shadow")
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=80.0, primary_power=2200.0, effective_export=800)
        controller._fast_capture_step(cfg, -800.0, 900)
        advance_observation(controller, state, 1.0)
        combined = controller._fast_capture_step(cfg, -800.0, 900)
        self.assertEqual(900, combined)
        self.assertGreater(state.fast_capture_overlay_w, 0)
        self.assertFalse(state.fast_capture_active)

    def test_gap_over_ten_seconds_resets_overlay(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=80.0, primary_power=2200.0, effective_export=800)
        controller._fast_capture_step(cfg, -800.0, 500)
        advance_observation(controller, state, 1.0)
        controller._fast_capture_step(cfg, -800.0, 500)
        self.assertGreater(state.fast_capture_overlay_w, 0)
        advance_observation(controller, state, 11.0)
        combined = controller._fast_capture_step(cfg, -800.0, 500)
        self.assertEqual(500, combined)
        self.assertEqual(0, state.fast_capture_overlay_w)

    def test_controlled_release_uses_r100_after_export_disappears(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=80.0, primary_power=2200.0, effective_export=800)
        controller._fast_capture_step(cfg, -800.0, 500)
        advance_observation(controller, state, 1.0)
        controller._fast_capture_step(cfg, -800.0, 500)
        self.assertGreaterEqual(state.fast_capture_overlay_w, 390)
        advance_observation(controller, state, 1.0, effective_export=0, grid_power=0)
        combined = controller._fast_capture_step(cfg, 0.0, 500)
        self.assertGreaterEqual(state.fast_capture_overlay_w, 290)
        self.assertLessEqual(state.fast_capture_overlay_w, 310)
        self.assertEqual(500 + state.fast_capture_overlay_w, combined)
        self.assertEqual("CONTROLLED_RELEASE_NO_EXPORT", state.fast_capture_block_reason)

    def test_stale_device_charge_limit_is_not_used_for_headroom(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state)
        with state.lock:
            state.zendure_device_charge_max_limit_w = 600
            state.zendure_device_charge_max_limit_updated_epoch = time.time() - 120
        self.assertEqual(2400, controller._fast_capture_effective_zendure_limit_w(cfg))
        with state.lock:
            state.zendure_device_charge_max_limit_updated_epoch = time.time()
        self.assertEqual(600, controller._fast_capture_effective_zendure_limit_w(cfg))

    def test_usable_soc_does_not_make_raw_80_percent_full_idle(self):
        cfg = fast_cfg()
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=80.0, primary_power=10.0, effective_export=600)
        with state.lock:
            state.primary_storage_current_discharge_floor_soc_percent = 20.0
            state.primary_storage_usable_soc_percent = 100.0
            state.primary_storage_usable_soc_valid = True
        controller._fast_capture_step(cfg, -600.0, 400)
        for _ in range(6):
            advance_observation(controller, state, 3.0)
            controller._fast_capture_step(cfg, -600.0, 400)
        self.assertNotEqual("FULL_IDLE", state.fast_capture_primary_state)
        self.assertEqual(0, state.fast_capture_overlay_w)

    def test_off_mode_matches_v17_0_1_baseline_matrix(self):
        cases = [
            (0, 600),
            (300, 300),
            (900, 500),
            (500, 100),
            (100, 0),
        ]
        for old_input, effective in cases:
            with self.subTest(old_input=old_input, effective=effective):
                cfg = fast_cfg(
                    mode="off",
                    REST_SURPLUS_HARVEST_ENABLED=False,
                    CROSS_CHARGE_ENABLED=False,
                )
                controller, state = make_controller(cfg)
                now = time.time()
                with state.lock:
                    state.battery_soc = 70
                    state.last_soc_update_epoch = now
                    state.last_input_power = old_input
                    state.last_output_power = 0
                    state.effective_export_power = effective
                    state.effective_export_power_valid = True
                controller._publish_signed_target = lambda target, **_kwargs: int(target)
                controller._apply_symmetric_cross_charge_limit = lambda _cfg, target: {
                    "target": int(target),
                    "active": False,
                }

                controller.handle_charge(cfg, -float(effective))

                if effective < cfg["MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W"]:
                    step = cfg.get("SMA_GUARD_RAMP_DOWN_W", cfg["MAX_POWER_STEP_W"])
                    expected = max(0, old_input - step)
                    self.assertEqual(expected, state.last_input_power)
                else:
                    raw = old_input + int(effective * cfg["CONTROL_GAIN"])
                    limited = max(0, min(raw, cfg["MAX_CHARGE_POWER_W"]))
                    smooth = int(
                        old_input * (1 - cfg["SMOOTHING_FACTOR"])
                        + limited * cfg["SMOOTHING_FACTOR"]
                    )
                    diff = smooth - old_input
                    max_step = cfg["MAX_POWER_STEP_W"]
                    expected = (
                        smooth
                        if abs(diff) <= max_step
                        else old_input + (max_step if diff > 0 else -max_step)
                    )
                    self.assertEqual(raw, state.last_target_before_smoothing)
                    self.assertEqual(limited, state.last_target_after_power_limit)
                    self.assertEqual(smooth, state.last_target_after_smoothing)
                    self.assertEqual(expected, state.last_input_power)
                self.assertEqual(0, state.fast_capture_overlay_w)
                self.assertFalse(state.fast_capture_active)

    def test_run_once_import_abort_does_not_reverse_direction_same_cycle(self):
        cfg = fast_cfg(mode="active", DEADBAND_W=50)
        controller, state = make_controller(cfg)
        make_fast_ready(
            state,
            primary_soc=80.0,
            primary_power=2200.0,
            effective_export=0,
            grid_power=150.0,
        )
        controller._fast_capture_last_mode = "active"
        with state.lock:
            state.fast_capture_baseline_target_w = 500
            state.fast_capture_overlay_w = 300
            state.fast_capture_active = True
            state.last_input_power = 800

        calls = []
        controller._timed_local_api_snapshot_apply_phase = lambda _cfg: None
        controller.update_sma_energy_meter_status = lambda _cfg: None
        controller.update_cycle_display_metrics = lambda _cfg: None
        controller.update_cross_charge_control_metrics = lambda _cfg: None
        controller.neutralize_ended_night_discharge_if_needed = lambda: False
        controller.is_night_discharge_active = lambda _cfg: False
        controller.soc_is_fresh = lambda _cfg: True
        controller.read_grid_power = lambda _cfg: True
        controller.update_rest_surplus_harvest_state = lambda _cfg, _grid: None
        controller.cross_charge_guard_corrects_existing_target = lambda _cfg: False
        controller.handle_charge = lambda _cfg, _grid: calls.append("charge")
        controller.handle_discharge = lambda _cfg, _grid: calls.append("discharge")

        controller.run_once(cfg)

        self.assertEqual(["charge"], calls)
        self.assertEqual(0, state.fast_capture_overlay_w)
        self.assertEqual("GRID_IMPORT_ABORT", state.fast_capture_forced_zero_reason)

    def test_active_baseline_isolated_from_previous_combined_target(self):
        cfg = fast_cfg(CONTROL_GAIN=0.30)
        controller, state = make_controller(cfg)
        make_fast_ready(state, primary_soc=80.0, primary_power=2200.0, effective_export=300, grid_power=-300)
        controller._fast_capture_last_mode = "active"
        controller._publish_signed_target = lambda target, **_kwargs: int(target)
        controller._apply_symmetric_cross_charge_limit = lambda _cfg, target: {
            "target": int(target), "active": False
        }
        with state.lock:
            state.last_input_power = 900  # previously commanded B+O
            state.fast_capture_baseline_target_w = 500
            state.fast_capture_overlay_w = 400
            state.fast_capture_active = True
        controller.handle_charge(cfg, -300.0)
        # Baseline raw is 500 + 0.3*300 = 590, smoothed from 500 -> 522.
        self.assertEqual(590, state.last_target_before_smoothing)
        self.assertEqual(522, state.fast_capture_baseline_target_w)


if __name__ == "__main__":
    unittest.main()
