# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import paho.mqtt.client as mqtt

from state import ControllerState
from app_logger import RotatingAppLogger
from zendure_local_api import zendure_temp_to_celsius
from cross_charge import cross_charge_enabled, parse_second_battery_value, second_battery_subscription_topics, second_battery_topics


class MqttBridge:
    def __init__(self, state: ControllerState, config_getter: Callable[[], Dict[str, Any]], app_logger: Optional[RotatingAppLogger] = None) -> None:
        self.state = state
        self.config_getter = config_getter
        self.client = self._build_client()
        self.last_sent_values: Dict[str, Any] = {}
        self._connected_once = False
        self.app_logger = app_logger or RotatingAppLogger()

        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect


    def log(self, message: str) -> None:
        cfg = self.config_getter()
        if cfg.get("DEBUG", False):
            print(message)
        self.app_logger.log(cfg, message)

    def _build_client(self):
        try:
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except Exception:
            return mqtt.Client()

    def topics(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        cfg = config or self.config_getter()
        device_id = cfg["DEVICE_ID"]
        second_topics = second_battery_topics(cfg)
        return {
            "output_limit": f"Zendure/number/{device_id}/outputLimit/set",
            "input_limit": f"Zendure/number/{device_id}/inputLimit/set",
            "ac_mode": f"Zendure/select/{device_id}/acMode/set",
            "battery_soc": f"Zendure/sensor/{device_id}/electricLevel",
            "pack_input_power": f"Zendure/sensor/{device_id}/packInputPower",
            "output_home_power": f"Zendure/sensor/{device_id}/outputHomePower",
            "grid_input_power": f"Zendure/sensor/{device_id}/gridInputPower",
            "output_pack_power": f"Zendure/sensor/{device_id}/outputPackPower",
            "hyper_tmp": f"Zendure/sensor/{device_id}/hyperTmp",
            "pack_max_temp_wildcard": "Zendure/sensor/+/maxTemp",
            "pack_power_wildcard": "Zendure/sensor/+/power",
            "pack_soc_wildcard": "Zendure/sensor/+/socLevel",
            "pack_state_wildcard": "Zendure/sensor/+/state",
            "second_battery_power": second_topics.get("power", ""),
            "second_battery_soc": second_topics.get("soc", ""),
            "second_battery_capacity": second_topics.get("capacity", ""),
        }

    def start(self) -> None:
        cfg = self.config_getter()
        if cfg.get("MQTT_USER"):
            self.client.username_pw_set(cfg.get("MQTT_USER"), cfg.get("MQTT_PASSWORD", ""))

        self.client.connect(cfg["MQTT_BROKER"], int(cfg["MQTT_PORT"]), 60)
        self.client.loop_start()
        self.refresh_subscriptions()

    def refresh_subscriptions(self) -> None:
        cfg = self.config_getter()
        topics = self.topics(cfg)
        for key in ("battery_soc", "pack_input_power", "output_home_power", "grid_input_power", "output_pack_power", "hyper_tmp", "pack_max_temp_wildcard", "pack_power_wildcard", "pack_soc_wildcard", "pack_state_wildcard"):
            self.client.subscribe(topics[key])

        if cross_charge_enabled(cfg):
            for topic in sorted(second_battery_subscription_topics(cfg)):
                self.client.subscribe(topic)

        if cfg.get("MQTT_TOPIC_DIAGNOSTIC_ENABLED", False):
            diagnostic_filter = str(cfg.get("MQTT_TOPIC_DIAGNOSTIC_FILTER", "Zendure/#")).strip()
            if diagnostic_filter:
                self.client.subscribe(diagnostic_filter)

    def on_connect(self, client, userdata, flags, reason_code=None, properties=None):
        with self.state.lock:
            self.state.mqtt_connected = True
        self.refresh_subscriptions()
        self.log("[MQTT] Verbunden")

    def on_disconnect(self, client, userdata, flags=None, reason_code=None, properties=None):
        with self.state.lock:
            self.state.mqtt_connected = False
        self.log("[MQTT] Verbindung getrennt")

    def on_message(self, client, userdata, msg) -> None:
        cfg = self.config_getter()
        topics = self.topics(cfg)
        topic = msg.topic
        payload = msg.payload.decode(errors="replace").strip()
        now = time.time()
        now_text = datetime.now().strftime("%H:%M:%S")

        if cfg.get("MQTT_TOPIC_DIAGNOSTIC_ENABLED", False):
            try:
                limit = int(cfg.get("MQTT_TOPIC_DIAGNOSTIC_HISTORY_LIMIT", 200))
                self.state.add_mqtt_diagnostic(topic, payload, limit)
            except Exception:
                pass

        try:
            with self.state.lock:
                if topic.startswith("Zendure/sensor/"):
                    self.state.mark_zendure_mqtt_sensor(now, now_text)

                if topic == topics["battery_soc"]:
                    self.state.battery_soc = int(float(payload))
                    self.state.mqtt_battery_soc = self.state.battery_soc
                    self.state.last_soc_update_epoch = now
                    self.state.last_soc_update_time = now_text
                    self.state.last_mqtt_soc_update_epoch = now
                    self.state.last_mqtt_soc_update_time = now_text
                    self.state.zendure_telemetry_source = "MQTT"
                    self.state.zendure_local_api_fallback_active = False
                    if cfg.get("LOG_SOC", False):
                        self.log(f"[SOC] Zendure MQTT: {self.state.battery_soc} %")

                elif topic == topics["pack_input_power"]:
                    self.state.update_zendure_headunit_power("MQTT", pack_input=payload)

                elif topic == topics["output_home_power"]:
                    self.state.update_zendure_headunit_power("MQTT", output_home=payload)

                elif topic == topics["grid_input_power"]:
                    self.state.update_zendure_headunit_power("MQTT", grid_input=payload)

                elif topic == topics["output_pack_power"]:
                    self.state.update_zendure_headunit_power("MQTT", output_pack=payload)

                elif topic == topics["hyper_tmp"]:
                    temp = zendure_temp_to_celsius(payload)
                    if temp is not None:
                        self.state.update_zendure_temperature("MQTT", [{"pack_sn": cfg.get("DEVICE_ID", "headunit"), "temperature_c": temp, "temperature_raw": payload}])

                elif topic.startswith("Zendure/sensor/") and topic.endswith("/maxTemp"):
                    parts = topic.split("/")
                    pack_sn = parts[-2] if len(parts) >= 3 else "unknown"
                    temp = zendure_temp_to_celsius(payload)
                    if temp is not None:
                        self.state.update_zendure_temperature("MQTT", [{"pack_sn": pack_sn, "temperature_c": temp, "temperature_raw": payload}])

                elif topic.startswith("Zendure/sensor/") and topic.endswith("/power"):
                    parts = topic.split("/")
                    pack_sn = parts[-2] if len(parts) >= 3 else "unknown"
                    self.state.update_zendure_battery_metrics("MQTT", [{"pack_sn": pack_sn, "power_w": payload}])

                elif topic.startswith("Zendure/sensor/") and topic.endswith("/socLevel"):
                    parts = topic.split("/")
                    pack_sn = parts[-2] if len(parts) >= 3 else "unknown"
                    self.state.update_zendure_battery_metrics("MQTT", [{"pack_sn": pack_sn, "soc_percent": payload}])

                elif topic.startswith("Zendure/sensor/") and topic.endswith("/state"):
                    parts = topic.split("/")
                    pack_sn = parts[-2] if len(parts) >= 3 else "unknown"
                    self.state.update_zendure_battery_metrics("MQTT", [{"pack_sn": pack_sn, "state": payload}])

                elif cross_charge_enabled(cfg):
                    second_topics = second_battery_topics(cfg)
                    updated_second_battery = False
                    if topic == second_topics.get("power"):
                        value = parse_second_battery_value("power", payload, cfg)
                        if value is not None:
                            with self.state.lock:
                                self.state.sma_battery_power = float(value)
                            updated_second_battery = True
                    if topic == second_topics.get("soc"):
                        value = parse_second_battery_value("soc", payload, cfg)
                        if value is not None:
                            with self.state.lock:
                                self.state.sma_battery_soc = float(value)
                            updated_second_battery = True
                    if topic == second_topics.get("capacity"):
                        value = parse_second_battery_value("capacity", payload, cfg)
                        if value is not None:
                            with self.state.lock:
                                self.state.sma_battery_capacity_kwh = float(value)
                            updated_second_battery = True
                    if updated_second_battery:
                        self._mark_evcc(now, now_text)

        except Exception as exc:
            self.state.set_error(f"MQTT parse error on {topic}: {exc}")
            self.log(f"[MQTT] Fehler auf {topic}: {exc}")

    def _mark_evcc(self, now: float, now_text: str) -> None:
        with self.state.lock:
            self.state.evcc_data_available = True
            self.state.last_sma_battery_update_epoch = now
            self.state.last_sma_battery_update_time = now_text

    def publish(self, topic: str, value: Any, force: bool = False, numeric: bool = True) -> bool:
        cfg = self.config_getter()
        min_change = int(cfg.get("MIN_COMMAND_CHANGE_W", 0))
        old = self.last_sent_values.get(topic)

        if not force and old is not None:
            if numeric:
                try:
                    numeric_value = float(value)
                    numeric_old = float(old)
                    if numeric_value == numeric_old:
                        with self.state.lock:
                            self.state.last_mqtt_command_skipped = f"{topic.split('/')[-2]} -> {value}"
                        return False
                    if abs(numeric_value - numeric_old) < min_change and numeric_value != 0.0:
                        with self.state.lock:
                            self.state.last_mqtt_command_skipped = f"{topic.split('/')[-2]} -> {value}"
                        return False
                except Exception:
                    pass
            elif str(value) == str(old):
                return False

        if cfg.get("LOG_MQTT", False):
            self.log(f"[MQTT] {topic} -> {value}")

        self.client.publish(topic, str(value), retain=False)
        self.last_sent_values[topic] = value
        with self.state.lock:
            self.state.last_mqtt_command = f"{topic.split('/')[-2]} -> {value}"
            self.state.mqtt_commands_sent += 1
        return True

    def set_ac_mode(self, mode: str) -> None:
        self.publish(self.topics()["ac_mode"], mode, force=False, numeric=False)

    def set_input_limit(self, watts: int, force: bool = False) -> None:
        self.publish(self.topics()["input_limit"], int(watts), force=force, numeric=True)

    def set_output_limit(self, watts: int, force: bool = False) -> None:
        self.publish(self.topics()["output_limit"], int(watts), force=force, numeric=True)
