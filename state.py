# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from measurement import derive_zendure_actual_power, signed_zendure_target_w
from translations import limiter_text, mode_label, path_label, technical_limiter_text
from version import APP_VERSION, CSV_SCHEMA


def power_flow_meaning(value: float, positive_label: str = "Netzbezug", negative_label: str = "Einspeisung", deadband: float = 1.0) -> str:
    if value > deadband:
        return positive_label
    if value < -deadband:
        return negative_label
    return "nahe 0 W"


def sma_power_meaning(value: float, deadband: float = 1.0) -> str:
    # Darstellungslogik: positive Werte bedeuten Ladung, negative Werte bedeuten Entladung.
    if value > deadband:
        return "zweite Batterie lädt"
    if value < -deadband:
        return "zweite Batterie entlädt"
    return "nahe 0 W"


@dataclass
class ControllerState:
    startup_epoch: float = field(default_factory=time.time)
    startup_time: datetime = field(default_factory=datetime.now)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    # Leistung / Regelung
    raw_grid_power: float = 0.0
    grid_power: float = 0.0
    current_rule_deviation: float = 0.0
    effective_export_power: int = 0
    last_input_power: int = 0
    last_output_power: int = 0
    # Zendure Headunit/System-Istleistung. Historisch wurden packInputPower
    # und outputHomePower direkt als "Laden/Entladen" dargestellt. In der
    # Praxis ist für die tatsächlich an der Headunit erreichte Ladeleistung
    # insbesondere gridInputPower relevant; daher führen wir die Rohsensoren
    # separat und berechnen daraus eine konsistente Systemleistung:
    # positiv = Ladung, negativ = Entladung.
    actual_zendure_charge_power: int = 0
    actual_zendure_discharge_power: int = 0
    actual_zendure_grid_input_power: int = 0
    actual_zendure_output_pack_power: int = 0
    actual_zendure_system_charge_power: int = 0
    actual_zendure_system_discharge_power: int = 0
    actual_zendure_system_signed_power: int = 0
    current_target_power: int = 0
    zendure_target_signed_power: int = 0
    last_target_before_smoothing: int = 0
    last_target_after_smoothing: int = 0
    last_target_after_ramp: int = 0

    # Modus / Diagnose
    current_mode: str = "STARTUP"
    previous_mode: str = "STARTUP"
    mode_change_epoch: float = field(default_factory=time.time)
    last_mode_change_time: str = "-"
    last_mode_duration_seconds: int = 0
    control_reason: str = "Systemstart"
    technical_control_path: str = "-"
    active_limiters: List[str] = field(default_factory=list)
    last_control_action: str = "-"
    last_limit_reason: str = "-"
    charge_acceptance_state: str = "ok"
    charge_acceptance_reason: str = "Keine relevante Ladeanforderung."

    # Kommunikation
    mqtt_connected: bool = False
    last_mqtt_command: str = "-"
    last_mqtt_command_skipped: str = "-"
    mqtt_commands_sent: int = 0
    consecutive_errors: int = 0
    last_error: str = "none"
    last_error_time: str = "-"
    safe_state_counter: int = 0
    last_loop_duration_ms: int = 0
    loop_counter: int = 0
    last_record_epoch: Optional[float] = None
    last_record_mqtt_commands_sent: int = 0

    # Zeitstempel / Staleness
    last_shelly_update_epoch: Optional[float] = None
    last_shelly_update_time: str = "-"
    last_soc_update_epoch: Optional[float] = None
    last_soc_update_time: str = "-"
    last_mqtt_soc_update_epoch: Optional[float] = None
    last_mqtt_soc_update_time: str = "-"
    last_mqtt_zendure_sensor_update_epoch: Optional[float] = None
    last_mqtt_zendure_sensor_update_time: str = "-"
    last_local_api_update_epoch: Optional[float] = None
    last_local_api_update_time: str = "-"
    last_local_api_error: str = "none"
    last_local_api_error_time: str = "-"
    last_sma_battery_update_epoch: Optional[float] = None
    last_sma_battery_update_time: str = "-"
    last_zendure_power_update_epoch: Optional[float] = None
    last_zendure_power_update_time: str = "-"

    # Batterie-Werte
    battery_soc: Optional[int] = None
    mqtt_battery_soc: Optional[int] = None
    local_api_soc: Optional[int] = None
    local_api_electric_level: Optional[int] = None
    local_api_pack_soc_level: Optional[int] = None
    zendure_telemetry_source: str = "none"
    zendure_local_api_fallback_active: bool = False
    sma_battery_power: float = 0.0
    # Normierte Darstellungsleistung: positiv = Laden, negativ = Entladen.
    sma_battery_display_power: float = 0.0
    sma_battery_soc: Optional[float] = None
    sma_battery_capacity_kwh: Optional[float] = None
    sma_battery_discharge_power: float = 0.0
    evcc_data_available: bool = False

    # Zendure Akkutemperaturen
    current_battery_temperature_c: Optional[float] = None
    highest_battery_temperature_c: Optional[float] = None
    highest_battery_temperature_time: str = "-"
    lowest_battery_temperature_c: Optional[float] = None
    lowest_battery_temperature_time: str = "-"
    zendure_pack_temperatures: List[Dict[str, Any]] = field(default_factory=list)
    zendure_battery_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Historien
    power_history: Deque[float] = field(default_factory=lambda: deque(maxlen=5))
    graph_history: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=300))
    event_history: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=50))
    mqtt_topic_diagnostics: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=200))

    def set_mode(self, new_mode: str) -> None:
        with self.lock:
            if new_mode != self.current_mode:
                self.previous_mode = self.current_mode
                self.current_mode = new_mode
                self.mode_change_epoch = time.time()
                self.last_mode_change_time = datetime.now().strftime("%H:%M:%S")
                self.add_event(f"Moduswechsel: {self.previous_mode} -> {new_mode}")
            self.last_mode_duration_seconds = int(time.time() - self.mode_change_epoch)

    def update_mode_duration(self) -> None:
        with self.lock:
            self.last_mode_duration_seconds = int(time.time() - self.mode_change_epoch)

    def add_event(self, text: str) -> None:
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            if self.event_history and self.event_history[-1].get("text") == text:
                self.event_history[-1]["time"] = timestamp
                self.event_history[-1]["count"] = int(self.event_history[-1].get("count", 1)) + 1
                return
            self.event_history.append({"time": timestamp, "text": text, "count": 1})

    def add_mqtt_diagnostic(self, topic: str, payload: str, limit: int = 200) -> None:
        with self.lock:
            if self.mqtt_topic_diagnostics.maxlen != limit:
                self.mqtt_topic_diagnostics = deque(self.mqtt_topic_diagnostics, maxlen=limit)
            self.mqtt_topic_diagnostics.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "topic": topic,
                "payload": payload[:500],
            })

    def set_error(self, message: str) -> None:
        with self.lock:
            self.last_error = message
            self.last_error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def mark_zendure_mqtt_sensor(self, now: float, now_text: str) -> None:
        with self.lock:
            self.last_mqtt_zendure_sensor_update_epoch = now
            self.last_mqtt_zendure_sensor_update_time = now_text

    def update_zendure_battery_metrics(self, source: str, battery_metrics: List[Dict[str, Any]]) -> None:
        """Merge Zendure battery/headunit metrics by serial number.

        MQTT and the local API are stored separately for temperature values. This
        avoids source ping-pong: a fresh MQTT temperature is not overwritten by a
        local-API diagnostic poll. The local API remains visible as diagnostic
        source, but the displayed temperature prefers MQTT while MQTT is fresh.
        """
        with self.lock:
            now_epoch = time.time()
            now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated = False

            def source_is_fresh(src_info: Dict[str, Any], timeout_seconds: int = 120) -> bool:
                epoch = src_info.get("update_epoch")
                if epoch is None:
                    return False
                try:
                    return (now_epoch - float(epoch)) <= timeout_seconds
                except Exception:
                    return False

            def select_temperature_source(entry: Dict[str, Any]) -> None:
                sources = entry.get("temperature_sources") or {}
                selected_name = None
                selected_info = None

                mqtt_info = sources.get("MQTT")
                if mqtt_info and source_is_fresh(mqtt_info):
                    selected_name = "MQTT"
                    selected_info = mqtt_info
                elif sources:
                    # Fallback: choose the newest source available.
                    selected_name, selected_info = max(
                        sources.items(),
                        key=lambda kv: float(kv[1].get("update_epoch") or 0.0),
                    )

                if selected_info:
                    entry["temperature_c"] = selected_info.get("temperature_c")
                    entry["temperature_source"] = selected_name
                    entry["temperature_raw"] = selected_info.get("raw_value")
                    entry["temperature_update_time"] = selected_info.get("update_time")

            for item in battery_metrics:
                pack_sn = str(item.get("pack_sn") or item.get("sn") or "unknown")
                if not pack_sn:
                    continue
                entry = self.zendure_battery_details.get(pack_sn, {
                    "pack_sn": pack_sn,
                    "temperature_c": None,
                    "temperature_source": "-",
                    "temperature_raw": None,
                    "temperature_update_time": "-",
                    "temperature_sources": {},
                    "power_w": None,
                    "power_source": "-",
                    "soc_percent": None,
                    "state": None,
                    "data_source": source,
                    "last_update_time": "-",
                    "highest_temperature_c": None,
                    "highest_temperature_time": "-",
                    "lowest_temperature_c": None,
                    "lowest_temperature_time": "-",
                })

                if "temperature_c" in item and item.get("temperature_c") is not None:
                    try:
                        temp_f = round(float(item.get("temperature_c")), 1)
                        raw_value = item.get("temperature_raw", item.get("raw_value", item.get("temperature_c")))
                        sources = entry.get("temperature_sources") or {}
                        sources[source] = {
                            "temperature_c": temp_f,
                            "raw_value": raw_value,
                            "update_time": now_text,
                            "update_epoch": now_epoch,
                        }
                        entry["temperature_sources"] = sources
                        select_temperature_source(entry)
                        selected_temp = entry.get("temperature_c")
                        if selected_temp is not None:
                            selected_temp = float(selected_temp)
                            if entry.get("highest_temperature_c") is None or selected_temp > float(entry.get("highest_temperature_c")):
                                entry["highest_temperature_c"] = selected_temp
                                entry["highest_temperature_time"] = now_text
                            if entry.get("lowest_temperature_c") is None or selected_temp < float(entry.get("lowest_temperature_c")):
                                entry["lowest_temperature_c"] = selected_temp
                                entry["lowest_temperature_time"] = now_text
                    except Exception:
                        pass

                if "power_w" in item and item.get("power_w") is not None:
                    try:
                        entry["power_w"] = int(float(item.get("power_w")))
                        entry["power_source"] = source
                    except Exception:
                        pass

                if "soc_percent" in item and item.get("soc_percent") is not None:
                    try:
                        entry["soc_percent"] = int(float(item.get("soc_percent")))
                    except Exception:
                        pass

                if "state" in item and item.get("state") is not None:
                    entry["state"] = str(item.get("state"))

                entry["data_source"] = source
                entry["last_update_time"] = now_text
                self.zendure_battery_details[pack_sn] = entry
                updated = True

            if updated:
                # Re-select displayed temperature for all batteries on every update,
                # so MQTT can expire and local API can take over without restart.
                for entry in self.zendure_battery_details.values():
                    select_temperature_source(entry)

                def sort_key(e: Dict[str, Any]) -> str:
                    sn = str(e.get("pack_sn", ""))
                    if sn == "headunit" or sn == str(getattr(self, "device_id", "")) or sn.startswith("HEC"):
                        return "0" + sn
                    return "1" + sn

                details = sorted(self.zendure_battery_details.values(), key=sort_key)
                self.zendure_pack_temperatures = [
                    {
                        "pack_sn": e.get("pack_sn"),
                        "temperature_c": e.get("temperature_c"),
                        "source": e.get("temperature_source") or e.get("data_source") or "-",
                        "temperature_raw": e.get("temperature_raw"),
                        "temperature_sources": e.get("temperature_sources", {}),
                        "highest_temperature_c": e.get("highest_temperature_c"),
                        "highest_temperature_time": e.get("highest_temperature_time"),
                        "lowest_temperature_c": e.get("lowest_temperature_c"),
                        "lowest_temperature_time": e.get("lowest_temperature_time"),
                    }
                    for e in details
                    if e.get("temperature_c") is not None
                ]
                current_values = [float(e["temperature_c"]) for e in details if e.get("temperature_c") is not None]
                if current_values:
                    self.current_battery_temperature_c = max(current_values)
                    if self.highest_battery_temperature_c is None or max(current_values) > self.highest_battery_temperature_c:
                        self.highest_battery_temperature_c = max(current_values)
                        self.highest_battery_temperature_time = now_text
                    if self.lowest_battery_temperature_c is None or min(current_values) < self.lowest_battery_temperature_c:
                        self.lowest_battery_temperature_c = min(current_values)
                        self.lowest_battery_temperature_time = now_text

    def update_zendure_temperature(self, source: str, pack_temperatures: List[Dict[str, Any]]) -> None:
        self.update_zendure_battery_metrics(source, pack_temperatures)

    def update_zendure_headunit_power(self, source: str, pack_input: Any = None, output_home: Any = None, grid_input: Any = None, output_pack: Any = None) -> None:
        """Update headunit power sensors and derive signed system power.

        Positive signed power means the Zendure system is charging; negative
        signed power means it is discharging. gridInputPower is preferred for
        real AC charging because inputLimit is only the requested limit.
        """
        with self.lock:
            def to_int(value: Any) -> Optional[int]:
                if value is None:
                    return None
                try:
                    return int(float(value))
                except Exception:
                    return None

            pi = to_int(pack_input)
            oh = to_int(output_home)
            gi = to_int(grid_input)
            op = to_int(output_pack)
            if pi is not None:
                self.actual_zendure_charge_power = pi
            if oh is not None:
                self.actual_zendure_discharge_power = oh
            if gi is not None:
                self.actual_zendure_grid_input_power = gi
            if op is not None:
                self.actual_zendure_output_pack_power = op

            derived = derive_zendure_actual_power(
                pack_input=self.actual_zendure_charge_power,
                output_home=self.actual_zendure_discharge_power,
                grid_input=self.actual_zendure_grid_input_power,
                output_pack=self.actual_zendure_output_pack_power,
                requested_input_limit=self.last_input_power,
                requested_output_limit=self.last_output_power,
            )
            self.actual_zendure_system_charge_power = derived["charge_power_w"]
            self.actual_zendure_system_discharge_power = derived["discharge_power_w"]
            self.actual_zendure_system_signed_power = derived["signed_power_w"]

            now = time.time()
            self.last_zendure_power_update_epoch = now
            self.last_zendure_power_update_time = datetime.now().strftime("%H:%M:%S")

    def reset_active_limiters(self) -> None:
        with self.lock:
            self.active_limiters = []
            self.last_limit_reason = "none"

    def add_limiter(self, limiter: str) -> None:
        with self.lock:
            if limiter not in self.active_limiters:
                self.active_limiters.append(limiter)
            self.last_limit_reason = ", ".join(self.active_limiters) if self.active_limiters else "none"

    def update_power_history(self, value: float, samples: int) -> float:
        with self.lock:
            if self.power_history.maxlen != samples:
                self.power_history = deque(self.power_history, maxlen=samples)
            self.power_history.append(value)
            return sum(self.power_history) / len(self.power_history)

    def ensure_graph_limit(self, limit: int) -> None:
        with self.lock:
            if self.graph_history.maxlen != limit:
                self.graph_history = deque(self.graph_history, maxlen=limit)

    def record_graph_point(self, graph_limit: int) -> None:
        with self.lock:
            self.ensure_graph_limit(graph_limit)
            now_dt = datetime.now()
            now_epoch = time.time()
            if self.last_record_epoch is None:
                dt_s = 0.0
            else:
                dt_s = max(0.0, now_epoch - self.last_record_epoch)
            self.last_record_epoch = now_epoch
            active_limiters = list(self.active_limiters)
            target_signed = signed_zendure_target_w(self.last_input_power, self.last_output_power)
            self.zendure_target_signed_power = target_signed
            mqtt_commands_in_cycle = max(0, int(self.mqtt_commands_sent) - int(self.last_record_mqtt_commands_sent))
            self.last_record_mqtt_commands_sent = int(self.mqtt_commands_sent)

            row = {
                # Schema / Zeitbasis
                "schema": CSV_SCHEMA,
                "controller_version": APP_VERSION,
                "date": now_dt.strftime("%Y-%m-%d"),
                "timestamp": now_dt.strftime("%H:%M:%S"),
                "datetime_local": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "epoch": round(now_epoch, 3),
                "dt_s": round(dt_s, 3),

                # Messwerte / signierte Hauptwerte
                "raw_grid_power_w": round(self.raw_grid_power, 1),
                "raw_grid_power_meaning": power_flow_meaning(self.raw_grid_power, "Netzbezug", "Einspeisung"),
                "grid_power_w": round(self.grid_power, 1),
                "grid_power_meaning": power_flow_meaning(self.grid_power, "Netzbezug", "Einspeisung"),
                "zendure_target_power_w": target_signed,
                "zendure_actual_power_w": self.actual_zendure_system_signed_power,
                "second_battery_power_w": round(self.sma_battery_display_power, 1),
                "second_battery_power_meaning": sma_power_meaning(self.sma_battery_display_power),

                # Kompatibilitäts-/UI-Aliasse im RAM-Graphen
                "raw_grid_power": round(self.raw_grid_power, 1),
                "grid_power": round(self.grid_power, 1),
                "charge_power": self.last_input_power,
                "discharge_power": self.last_output_power,
                "zendure_system_signed_power": self.actual_zendure_system_signed_power,
                "sma_battery_display_power": round(self.sma_battery_display_power, 1),
                "sma_battery_power": round(self.sma_battery_power, 1),

                # Zendure Rohsensoren / Diagnose
                "zendure_raw_grid_input_power_w": self.actual_zendure_grid_input_power,
                "zendure_raw_pack_input_power_w": self.actual_zendure_charge_power,
                "zendure_raw_output_home_power_w": self.actual_zendure_discharge_power,
                "zendure_raw_output_pack_power_w": self.actual_zendure_output_pack_power,
                "zendure_actual_charge_power_w": self.actual_zendure_system_charge_power,
                "zendure_actual_discharge_power_w": self.actual_zendure_system_discharge_power,
                "actual_zendure_charge_power": self.actual_zendure_charge_power,
                "actual_zendure_discharge_power": self.actual_zendure_discharge_power,
                "actual_zendure_grid_input_power": self.actual_zendure_grid_input_power,
                "actual_zendure_output_pack_power": self.actual_zendure_output_pack_power,
                "zendure_pack_power": self.actual_zendure_charge_power,
                "zendure_ac_home_power": self.actual_zendure_discharge_power,
                "zendure_telemetry_source": self.zendure_telemetry_source,
                "zendure_api_fallback_active": self.zendure_local_api_fallback_active,
                "battery_temperature_c": self.current_battery_temperature_c,

                # Zweitbatterie / Cross-Charge
                "second_battery_raw_power_w": round(self.sma_battery_power, 1),
                "second_battery_discharge_power_w": round(self.sma_battery_discharge_power, 1),
                "second_battery_soc_percent": self.sma_battery_soc,
                "second_battery_capacity_kwh": self.sma_battery_capacity_kwh,
                "sma_battery_power_meaning": sma_power_meaning(self.sma_battery_display_power),
                "sma_battery_discharge_power": round(self.sma_battery_discharge_power, 1),
                "effective_export_power_w": self.effective_export_power,
                "effective_export_power": self.effective_export_power,
                "effective_export_meaning": "Für Zendure-Ladung verfügbarer Überschuss nach Zusatzbatterie-Abzug und Sicherheitsreserve",

                # SOC / Modus / Reglerpfad
                "zendure_soc_percent": self.battery_soc,
                "soc": self.battery_soc,
                "sma_soc": self.sma_battery_soc,
                "mode": self.current_mode,
                "mode_label": mode_label(self.current_mode),
                "target_before_smoothing_w": self.last_target_before_smoothing,
                "target_after_smoothing_w": self.last_target_after_smoothing,
                "target_after_ramp_w": self.last_target_after_ramp,
                "target_before_smoothing": self.last_target_before_smoothing,
                "target_after_smoothing": self.last_target_after_smoothing,
                "target_after_ramp": self.last_target_after_ramp,
                "control_action": self.last_control_action,
                "limit_reason": self.last_limit_reason,
                "limit_label": limiter_text(active_limiters),
                "technical_limiters": technical_limiter_text(active_limiters),
                "technical_path": self.technical_control_path,
                "technical_path_label": path_label(self.technical_control_path),
                "control_reason": self.control_reason,

                # MQTT-Kommandodynamik / Diagnose
                "mqtt_commands_sent_total": self.mqtt_commands_sent,
                "mqtt_commands_sent_in_cycle": mqtt_commands_in_cycle,
                "mqtt_last_command": self.last_mqtt_command,
                "mqtt_last_command_skipped": self.last_mqtt_command_skipped,
                "last_mqtt_command": self.last_mqtt_command,
                "last_mqtt_command_skipped": self.last_mqtt_command_skipped,
                "loop_duration_ms": self.last_loop_duration_ms,
                "loop_counter": self.loop_counter,
                "last_error": self.last_error,
                "last_error_time": self.last_error_time,

                # High-SOC-Ladeannahme-Diagnose
                "charge_acceptance_state": self.charge_acceptance_state,
                "charge_acceptance_reason": self.charge_acceptance_reason,
            }
            self.graph_history.append(row)

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            now_epoch = time.time()

            def age_seconds(epoch_value: Optional[float]) -> Optional[int]:
                if epoch_value is None:
                    return None
                return max(0, int(now_epoch - epoch_value))

            return {
                "uptime_seconds": int(now_epoch - self.startup_epoch),
                "raw_grid_power": self.raw_grid_power,
                "grid_power": self.grid_power,
                "current_rule_deviation": self.current_rule_deviation,
                "effective_export_power": self.effective_export_power,
                "last_input_power": self.last_input_power,
                "last_output_power": self.last_output_power,
                "actual_zendure_charge_power": self.actual_zendure_charge_power,
                "actual_zendure_discharge_power": self.actual_zendure_discharge_power,
                "actual_zendure_grid_input_power": self.actual_zendure_grid_input_power,
                "actual_zendure_output_pack_power": self.actual_zendure_output_pack_power,
                "zendure_system_charge_power": self.actual_zendure_system_charge_power,
                "zendure_system_discharge_power": self.actual_zendure_system_discharge_power,
                "zendure_system_signed_power": self.actual_zendure_system_signed_power,
                "current_target_power": self.current_target_power,
                "zendure_target_signed_power": self.zendure_target_signed_power,
                "last_target_before_smoothing": self.last_target_before_smoothing,
                "last_target_after_smoothing": self.last_target_after_smoothing,
                "last_target_after_ramp": self.last_target_after_ramp,
                "current_mode": self.current_mode,
                "previous_mode": self.previous_mode,
                "last_mode_change_time": self.last_mode_change_time,
                "last_mode_duration_seconds": self.last_mode_duration_seconds,
                "control_reason": self.control_reason,
                "technical_control_path": self.technical_control_path,
                "active_limiters": list(self.active_limiters),
                "last_control_action": self.last_control_action,
                "last_limit_reason": self.last_limit_reason,
                "charge_acceptance_state": self.charge_acceptance_state,
                "charge_acceptance_reason": self.charge_acceptance_reason,
                "mqtt_connected": self.mqtt_connected,
                "last_mqtt_command": self.last_mqtt_command,
                "last_mqtt_command_skipped": self.last_mqtt_command_skipped,
                "mqtt_commands_sent": self.mqtt_commands_sent,
                "consecutive_errors": self.consecutive_errors,
                "last_error": self.last_error,
                "last_error_time": self.last_error_time,
                "safe_state_counter": self.safe_state_counter,
                "last_loop_duration_ms": self.last_loop_duration_ms,
                "loop_counter": self.loop_counter,
                "last_shelly_update_time": self.last_shelly_update_time,
                "last_shelly_update_age_seconds": age_seconds(self.last_shelly_update_epoch),
                "last_soc_update_time": self.last_soc_update_time,
                "last_soc_update_age_seconds": age_seconds(self.last_soc_update_epoch),
                "last_mqtt_soc_update_time": self.last_mqtt_soc_update_time,
                "last_mqtt_soc_update_age_seconds": age_seconds(self.last_mqtt_soc_update_epoch),
                "last_mqtt_zendure_sensor_update_time": self.last_mqtt_zendure_sensor_update_time,
                "last_mqtt_zendure_sensor_update_age_seconds": age_seconds(self.last_mqtt_zendure_sensor_update_epoch),
                "last_local_api_update_time": self.last_local_api_update_time,
                "last_local_api_update_age_seconds": age_seconds(self.last_local_api_update_epoch),
                "last_local_api_error": self.last_local_api_error,
                "last_local_api_error_time": self.last_local_api_error_time,
                "last_sma_battery_update_time": self.last_sma_battery_update_time,
                "last_sma_battery_update_age_seconds": age_seconds(self.last_sma_battery_update_epoch),
                "last_zendure_power_update_time": self.last_zendure_power_update_time,
                "last_zendure_power_update_age_seconds": age_seconds(self.last_zendure_power_update_epoch),
                "battery_soc": self.battery_soc,
                "mqtt_battery_soc": self.mqtt_battery_soc,
                "local_api_soc": self.local_api_soc,
                "local_api_electric_level": self.local_api_electric_level,
                "local_api_pack_soc_level": self.local_api_pack_soc_level,
                "zendure_telemetry_source": self.zendure_telemetry_source,
                "zendure_local_api_fallback_active": self.zendure_local_api_fallback_active,
                "current_battery_temperature_c": self.current_battery_temperature_c,
                "highest_battery_temperature_c": self.highest_battery_temperature_c,
                "highest_battery_temperature_time": self.highest_battery_temperature_time,
                "lowest_battery_temperature_c": self.lowest_battery_temperature_c,
                "lowest_battery_temperature_time": self.lowest_battery_temperature_time,
                "zendure_pack_temperatures": list(self.zendure_pack_temperatures),
                "zendure_battery_details": list(self.zendure_battery_details.values()),
                "sma_battery_power": self.sma_battery_power,
                "sma_battery_display_power": self.sma_battery_display_power,
                "sma_battery_soc": self.sma_battery_soc,
                "sma_battery_capacity_kwh": self.sma_battery_capacity_kwh,
                "sma_battery_discharge_power": self.sma_battery_discharge_power,
                "evcc_data_available": self.evcc_data_available,
                "graph_history": list(self.graph_history),
                "event_history": list(self.event_history),
                "mqtt_topic_diagnostics": list(self.mqtt_topic_diagnostics),
            }
