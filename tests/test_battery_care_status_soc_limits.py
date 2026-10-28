"""Two persistent SOC limits for both cards; no unverified primary upper limit."""
import unittest
from web_ui import build_status_view_payload
from status_page_v2 import render_status_page_v2


class StorageSocLimitCardTests(unittest.TestCase):
    def config(self):
        return {"MIN_SOC_PERCENT":10,"MAX_SOC_PERCENT":99,
                "MAX_CHARGE_POWER_W":2400,"MAX_DISCHARGE_POWER_W":2400,
                "SECOND_BATTERY_CAPACITY_WH":15000,"SECOND_BATTERY_INTEGRATION_ENABLED":True}

    def sample(self,power=200):
        return {"battery_soc":35,"zendure_system_signed_power":power,
                "sma_battery_soc":65,"sma_battery_display_power":power,
                "second_battery_data_valid":True,"second_battery_data_fresh":True,
                "primary_storage_current_discharge_floor_supported":True,
                "primary_storage_current_discharge_floor_valid":True,
                "primary_storage_current_discharge_floor_fresh":True,
                "primary_storage_current_discharge_floor_soc_percent":25}

    def test_both_cards_always_show_both_known_boundaries(self):
        for signed in (150,-150,0):
            with self.subTest(power=signed):
                payload=build_status_view_payload(self.config(),self.sample(signed))
                self.assertEqual("Lade-/Entladegrenze",payload['zendure']['soc_limit_label'])
                self.assertEqual("99 % / 10 %",payload['zendure']['soc_limit_text'])
                self.assertEqual("— / 25 %",payload['primary']['soc_limit_text'])
                html=render_status_page_v2(self.config(),payload,analysis_available=False,analysis_port=8081)
                self.assertIn('data-zec-row="zendure.soc_limit"><span',html)
                self.assertIn('data-zec-row="primary.soc_limit"><span',html)

    def test_primary_upper_only_when_explicitly_fresh_and_valid(self):
        sample=self.sample()
        sample.update(primary_storage_charge_upper_soc_percent=94,
                      primary_storage_charge_upper_soc_valid=True,
                      primary_storage_charge_upper_soc_fresh=True)
        value=build_status_view_payload(self.config(),sample)['primary']
        self.assertEqual("94 % / 25 %",value['soc_limit_text'])
        self.assertEqual("29 % · 4,35 kWh",value['remaining_text'])
        sample['primary_storage_charge_upper_soc_fresh']=False
        value=build_status_view_payload(self.config(),sample)['primary']
        self.assertEqual("— / 25 %",value['soc_limit_text'])
        self.assertEqual("—",value['remaining_text'])

    def test_care_reserve_not_fake_when_only_setting_enabled(self):
        cfg=self.config()
        cfg.update(BATTERY_CARE_ENABLED=True,BATTERY_CARE_RESERVE_SOC_PERCENT=40)
        val=build_status_view_payload(cfg,self.sample())['zendure']
        self.assertEqual("99 % / 10 %",val['soc_limit_text'])
        val=build_status_view_payload(cfg,dict(self.sample(),care_in_season=True,
             care_policy_valid=True,care_effective_discharge_floor_soc=40))['zendure']
        self.assertEqual("99 % / 40 %",val['soc_limit_text'])

    def test_no_primary_floor_is_unknown_not_a_claimed_zero(self):
        snap=self.sample()
        snap['primary_storage_current_discharge_floor_fresh']=False
        payload=build_status_view_payload(self.config(),snap)
        self.assertEqual("— / —",payload['primary']['soc_limit_text'])
        self.assertEqual("—",payload['primary']['remaining_text'])

if __name__ == '__main__':unittest.main()
