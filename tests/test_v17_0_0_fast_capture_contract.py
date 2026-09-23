import json
import sys
import types
import unittest
from pathlib import Path

if "paho" not in sys.modules:
    paho=types.ModuleType("paho"); pm=types.ModuleType("paho.mqtt"); pc=types.ModuleType("paho.mqtt.client")
    pc.CallbackAPIVersion=types.SimpleNamespace(VERSION2=object()); pc.Client=lambda *a,**k: types.SimpleNamespace()
    sys.modules["paho"]=paho; sys.modules["paho.mqtt"]=pm; sys.modules["paho.mqtt.client"]=pc

from config_manager import DEFAULT_CONFIG
from config_validator import validate_config_semantics
from measurement_v4 import CONTROL_SNAPSHOT_KEYS, build_config_snapshot, build_v4_row
from measurement_v4_contract import EXTENDED_HEADER, RC15_STANDARD_HEADER, RC16_STANDARD_HEADER, RC17_STANDARD_HEADER, STANDARD_HEADER, header_hash
from settings_registry import SETTINGS_BY_KEY, Applicability, SurfaceState, Visibility

class FastCaptureContractTests(unittest.TestCase):
    def test_setting_contract(self):
        spec=SETTINGS_BY_KEY["HARVEST_FAST_CAPTURE_MODE"]
        self.assertEqual("off",DEFAULT_CONFIG["HARVEST_FAST_CAPTURE_MODE"])
        self.assertEqual("off",spec.default_new_install)
        self.assertEqual(Visibility.EXPERT,spec.visibility)
        self.assertEqual(SurfaceState.OPERATIONAL,spec.surface_state)
        self.assertEqual(Applicability.PRIMARY_STORAGE_ENABLED,spec.applicability)
        self.assertEqual(("off","shadow","active"),tuple(spec.option_values))

    def test_active_validation_prerequisites_but_shadow_is_diagnostic(self):
        base=dict(DEFAULT_CONFIG)
        base.update({"HARVEST_FAST_CAPTURE_MODE":"shadow","REST_SURPLUS_HARVEST_ENABLED":False,"CROSS_CHARGE_ENABLED":False,"SECOND_BATTERY_INTEGRATION_ENABLED":False,"MAX_CHARGE_POWER_W":0})
        shadow_codes={x.code for x in validate_config_semantics(base) if x.severity=="ERROR"}
        self.assertNotIn("FAST_CAPTURE_ACTIVE_NEEDS_HARVEST",shadow_codes)
        active=dict(base); active["HARVEST_FAST_CAPTURE_MODE"]="active"
        codes={x.code for x in validate_config_semantics(active) if x.severity=="ERROR"}
        self.assertTrue({"FAST_CAPTURE_ACTIVE_NEEDS_HARVEST","FAST_CAPTURE_ACTIVE_NEEDS_CROSS_CHARGE","FAST_CAPTURE_ACTIVE_NEEDS_PRIMARY_STORAGE","FAST_CAPTURE_ACTIVE_NEEDS_PRIMARY_MAX_CHARGE","FAST_CAPTURE_ACTIVE_NEEDS_ZENDURE_MAX_CHARGE"}.issubset(codes))

    def test_measurement_current_header_additive_historical_headers_unchanged(self):
        self.assertEqual(273,len(STANDARD_HEADER)); self.assertEqual(276,len(EXTENDED_HEADER))
        self.assertEqual(238,len(RC17_STANDARD_HEADER)); self.assertEqual(228,len(RC16_STANDARD_HEADER)); self.assertEqual(217,len(RC15_STANDARD_HEADER))
        self.assertEqual("5a0c28b2f292a258",header_hash(STANDARD_HEADER)); self.assertEqual("192ccc890c2e1d80",header_hash(RC17_STANDARD_HEADER))
        for field in ("fast_capture_mode","fast_capture_overlay_w","fast_capture_observation_distinct","fast_capture_primary_max_charge_w"):
            self.assertIn(field,STANDARD_HEADER); self.assertNotIn(field,RC17_STANDARD_HEADER)

    def test_fast_mode_part_of_snapshot_and_row(self):
        self.assertIn("HARVEST_FAST_CAPTURE_MODE",CONTROL_SNAPSHOT_KEYS)
        cfg=dict(DEFAULT_CONFIG); cfg["HARVEST_FAST_CAPTURE_MODE"]="shadow"
        self.assertEqual("shadow",build_config_snapshot(cfg)["control_parameters"]["HARVEST_FAST_CAPTURE_MODE"])
        row=build_v4_row(cfg,{"epoch":1,"fast_capture_mode":"shadow","fast_capture_primary_state":"NEAR_LIMIT","fast_capture_overlay_w":123,"fast_capture_combined_target_w":523,"fast_capture_baseline_target_w":400,"fast_capture_observation_distinct":True,"fast_capture_primary_max_charge_w":2300})
        self.assertEqual("shadow",row["fast_capture_mode"]); self.assertEqual(123.0,row["fast_capture_overlay_w"]); self.assertEqual("1",row["fast_capture_observation_distinct"])

    def test_config_example_safe_off(self):
        data=json.loads((Path(__file__).parents[1]/"config.example.json").read_text(encoding="utf-8"))
        self.assertEqual("off",data["HARVEST_FAST_CAPTURE_MODE"])

if __name__=="__main__": unittest.main()
