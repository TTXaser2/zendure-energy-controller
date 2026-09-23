import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location("fast_analysis",ROOT/"tools"/"fast_capture_field_analysis.py")
fa=importlib.util.module_from_spec(spec); spec.loader.exec_module(fa)
from measurement_v4_contract import STANDARD_HEADER

def base_row(ms,mode="shadow",state="NEAR_LIMIT",baseline=500,desired=300,overlay=100,combined=600):
    row={k:"" for k in STANDARD_HEADER}
    row.update({
        "schema_version":"4","measurement_epoch_ms":str(ms),"config_control_hash":"abc","grid_power_w":"-300",
        "zendure_actual_power_w":"600","zendure_actual_power_valid":"1","zendure_actual_power_fresh":"1",
        "second_battery_power_w":"2200","second_battery_power_valid":"1","second_battery_power_fresh":"1",
        "target_final_w":str(baseline if mode=="shadow" else combined),"target_changed_by_power_limit":"0","target_changed_by_cross_charge":"0","target_changed_by_soc_limit":"0","target_changed_by_mode":"0","target_changed_by_safe_state":"0",
        "control_cross_charge_detected":"0","command_effect_category":"COMMAND_TARGET_TRACKING_EFFECTIVE","command_readback_matches_desired":"1",
        "fast_capture_mode":mode,"fast_capture_active":"1" if mode=="active" and overlay>0 else "0","fast_capture_primary_state":state,
        "fast_capture_block_reason":"","fast_capture_baseline_target_w":str(baseline),"fast_capture_desired_overlay_w":str(desired),"fast_capture_overlay_w":str(overlay),"fast_capture_combined_target_w":str(combined),
        "fast_capture_primary_reserve_w":"100","fast_capture_full_idle_progress_s":"0","fast_capture_observation_dt_s":"1","fast_capture_observation_distinct":"1","fast_capture_attack_limited":"1","fast_capture_release_limited":"0","fast_capture_forced_zero_reason":"","fast_capture_activation_count":"1","fast_capture_forced_zero_count":"0","fast_capture_effective_zendure_limit_w":"2400","fast_capture_primary_max_charge_w":"2300",
    })
    return row

class FastFieldAnalysisTests(unittest.TestCase):
    def _write(self,rows):
        td=tempfile.TemporaryDirectory(); root=Path(td.name); csvp=root/"m.csv"
        with csvp.open("w",encoding="utf-8",newline="") as h:
            w=csv.DictWriter(h,fieldnames=STANDARD_HEADER,delimiter=";"); w.writeheader(); w.writerows(rows)
        manifest=root/"zec_measurement_manifest.json"; manifest.write_text(json.dumps({"schema_version":4,"files":[{"schema_version":4,"file_name":"m.csv"}]}),encoding="utf-8")
        snaps=root/"zec_config_snapshots.json"; snaps.write_text(json.dumps({"schema_version":4,"snapshots":[{"controller_version":"17.0.1","config_control_hash":"abc"}]}),encoding="utf-8")
        return td,csvp,manifest,snaps

    def test_describe_read_only_strategy(self):
        d=fa.describe_contract(); self.assertTrue(d["read_only"]); self.assertEqual("A400_R100",d["strategy"]); self.assertEqual(0,d["commands_published"])

    def test_shadow_math_no_target_mutation(self):
        td,csv,manifest,snaps=self._write([base_row(1000,overlay=0,combined=500),base_row(2000,overlay=300,combined=800,desired=300)])
        try:
            result=fa.analyze_files([csv],manifest_path=manifest,config_snapshots_path=snaps)
            self.assertNotEqual("FAIL",result["status"]); self.assertEqual("PASS",result["dimensions"]["calculation"]["shadow_mutation"]["status"])
        finally: td.cleanup()

    def test_active_episode_physical_effect_pass(self):
        rows=[base_row(i*1000,mode="active",overlay=o,combined=500+o,desired=500) for i,o in enumerate((0,300,500,500),start=1)]
        td,csv,manifest,snaps=self._write(rows)
        try:
            result=fa.analyze_files([csv],manifest_path=manifest,config_snapshots_path=snaps)
            self.assertEqual("PASS",result["dimensions"]["physical_effect"]["status"]); self.assertNotEqual("FAIL",result["status"])
        finally: td.cleanup()

    def test_a400_violation_fails(self):
        td,csv,manifest,snaps=self._write([base_row(1000,mode="active",overlay=0,combined=500),base_row(2000,mode="active",overlay=900,combined=1400,desired=900)])
        try:
            result=fa.analyze_files([csv],manifest_path=manifest,config_snapshots_path=snaps)
            self.assertEqual("FAIL",result["dimensions"]["calculation"]["status"]); self.assertTrue(any(x["code"]=="A400_EXCEEDED" for x in result["issues"]))
        finally: td.cleanup()

    def test_no_natural_episode_not_evaluable(self):
        row=base_row(1000,mode="off",state="RESERVE_UNKNOWN",desired=0,overlay=0,combined=500)
        td,csv,manifest,snaps=self._write([row])
        try: self.assertEqual("NOT_EVALUABLE",fa.analyze_files([csv],manifest_path=manifest,config_snapshots_path=snaps)["status"])
        finally: td.cleanup()

if __name__=="__main__": unittest.main()
