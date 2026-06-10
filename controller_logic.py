# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import time
from datetime import datetime
from typing import Any, Dict, Optional

from config_manager import ConfigManager
from csv_logger import CsvRotatingLogger
from app_logger import RotatingAppLogger
from mqtt_bridge import MqttBridge
from shelly_client import ShellyClient
from measurement import classify_charge_acceptance
from state import ControllerState
from zendure_local_api import ZendureLocalApiClient, zendure_temp_to_celsius
from cross_charge import cross_charge_enabled, normalize_discharge_power_w, display_power_w


class ZendureController:
    def __init__(
        self,
        config_manager: ConfigManager,
        state: ControllerState,
        mqtt_bridge: MqttBridge,
        shelly_client: ShellyClient,
        csv_logger: CsvRotatingLogger,
        zendure_api_client: ZendureLocalApiClient,
        app_logger: RotatingAppLogger = None,
    ) -> None:
        self.config_manager = config_manager
        self.state = state
        self.mqtt = mqtt_bridge
        self.shelly = shelly_client
        self.csv_logger = csv_logger
        self.zendure_api = zendure_api_client
        self.app_logger = app_logger or RotatingAppLogger()
        self._running = True

    def log(self, message: str) -> None:
        cfg = self.config_manager.get()
        if cfg.get("DEBUG", False):
            print(message)
        self.app_logger.log(cfg, message)

    def run_forever(self) -> None:
        self.log("[CTRL] Hauptschleife gestartet")
        while self._running:
            loop_start = time.time()
            cfg, changed = self.config_manager.reload_if_needed()
            if changed:
                self.log("[CONFIG] Änderung geladen")
                self.mqtt.refresh_subscriptions()

            try:
                self.run_once(cfg)
                with self.state.lock:
                    self.state.consecutive_errors = 0
            except Exception as exc:
                with self.state.lock:
                    self.state.consecutive_errors += 1
                self.state.set_error(str(exc))
                self.log(f"[ERROR] {exc}")
                if self.state.consecutive_errors >= cfg.get("MAX_CONSECUTIVE_ERRORS", 5):
                    self.safe_state("Zu viele Fehler in Folge")

            self.finish_cycle(cfg, loop_start)
            time.sleep(float(cfg.get("INTERVAL_SECONDS", 2)))

    def run_once(self, cfg: Dict[str, Any]) -> None:
        now = time.time()
        with self.state.lock:
            self.state.loop_counter += 1
            self.state.reset_active_limiters()
            self.state.update_mode_duration()
            # Per-cycle contract flags are recalculated in finish_cycle().
            # Reset them here so early-return paths cannot keep stale
            # "used_for_control" information from the previous cycle.
            self.state.grid_power_used_for_control = False
            self.state.effective_export_power_used_for_control = False
            self.state.soc_used_for_control = False
            self.state.mqtt_command_path_used_for_control = False
            self.state.second_battery_data_used_for_control = False
            self.state.control_required_sources = []
            self.state.control_missing_required_sources = []
            self.state.control_data_quality = "not_evaluated"

        if cfg.get("MQTT_DISCONNECTED_SAFE_STATE", False) and not self.state.mqtt_connected:
            self.state.add_limiter("MQTT_DISCONNECTED")
            self.safe_state("MQTT getrennt")
            return

        # SOC-/Zendure-Telemetrie darf vor fest vorgegebenen Betriebsarten aktualisiert
        # werden, weil diese Betriebsarten ohne Netzanschlusspunktmessung funktionieren.
        # Shelly/UniMeter wird bewusst erst später gelesen: Nachtmodus sowie manuelle
        # Festladung/-entladung und Stop/Hold sollen bei fehlender Netzmessung nicht
        # unnötig in den Safe-State fallen.
        self.update_zendure_telemetry_from_local_api(cfg)
        # Per-cycle housekeeping: display/CSV metrics that are derived from
        # asynchronous MQTT/API raw values must be refreshed before any early
        # return path (manual modes, night mode, safe-state). Cross-charge
        # control metrics remain AUTO/grid-dependent and are refreshed later
        # after a valid grid measurement.
        self.update_cycle_display_metrics(cfg)

        manual_mode = str(cfg.get("MANUAL_MODE", "AUTO"))
        if manual_mode != "AUTO":
            self.handle_manual_mode(cfg, manual_mode)
            return

        if self.is_night_discharge_active(cfg):
            if not self.soc_is_fresh(cfg):
                self.state.add_limiter("SOC_STALE")
                self.safe_state("Nachtmodus blockiert: Zendure SOC fehlt oder ist veraltet")
                return
            self.handle_night_mode(cfg)
            return

        if not self.soc_is_fresh(cfg):
            self.state.add_limiter("SOC_STALE")
            self.safe_state("Zendure SOC fehlt oder ist veraltet")
            return

        if not self.read_grid_power(cfg):
            return
        self.update_cycle_display_metrics(cfg)
        self.update_cross_charge_control_metrics(cfg)

        grid_power = self.state.grid_power

        if self.sma_guard_blocks_existing_charge(cfg):
            return

        if abs(grid_power) <= cfg["DEADBAND_W"]:
            self.handle_deadband()
            return

        if grid_power > 0:
            self.handle_discharge(cfg, grid_power)
            return

        self.handle_charge(cfg, grid_power)

    def read_grid_power(self, cfg: Dict[str, Any]) -> bool:
        try:
            raw = self.shelly.read_grid_power(cfg)
            smoothed = self.state.update_power_history(raw, int(cfg["MOVING_AVERAGE_SAMPLES"]))
            now = time.time()
            now_text = datetime.now().strftime("%H:%M:%S")
            with self.state.lock:
                self.state.raw_grid_power = raw
                self.state.grid_power = smoothed
                self.state.current_rule_deviation = round(smoothed, 1)
                self.state.last_shelly_update_epoch = now
                self.state.last_shelly_update_time = now_text
                self.state.grid_power_valid = True
                self.state.grid_power_used_for_control = True
                self.state.grid_power_age_seconds = 0
            if cfg.get("LOG_VALUES", False):
                self.log(f"[GRID] Rohwert: {raw:.1f} W | Mittelwert: {smoothed:.1f} W")
            return True
        except Exception as exc:
            self.state.set_error(f"Shelly/Uni-Meter Fehler: {exc}")
            with self.state.lock:
                self.state.grid_power_used_for_control = False
                if self.state.last_shelly_update_epoch is not None:
                    self.state.grid_power_age_seconds = max(0, int(time.time() - self.state.last_shelly_update_epoch))
            with self.state.lock:
                last_update = self.state.last_shelly_update_epoch
            if cfg.get("SAFE_STATE_ON_SHELLY_ERROR", True):
                if last_update is None or time.time() - last_update > cfg.get("SHELLY_STALE_TIMEOUT_SECONDS", 15):
                    self.state.add_limiter("SHELLY_STALE")
                    self.safe_state("Shelly/Uni-Meter Daten veraltet")
                    return False
            raise


    def mqtt_soc_is_fresh(self, cfg: Dict[str, Any]) -> bool:
        with self.state.lock:
            soc = self.state.mqtt_battery_soc
            last_soc = self.state.last_mqtt_soc_update_epoch
        if soc is None or last_soc is None:
            return False
        return (time.time() - last_soc) <= cfg.get("SOC_STALE_TIMEOUT_SECONDS", 90)

    def zendure_power_is_fresh(self, cfg: Dict[str, Any]) -> bool:
        with self.state.lock:
            last_power = self.state.last_zendure_power_update_epoch
        if last_power is None:
            return False
        return (time.time() - last_power) <= cfg.get("ZENDURE_POWER_STALE_TIMEOUT_SECONDS", 90)

    def update_zendure_telemetry_from_local_api(self, cfg: Dict[str, Any]) -> None:
        """Use the local Zendure API as a read-only telemetry fallback.

        MQTT remains the primary source when it is fresh. The local API is
        polled periodically for diagnostics and temperature data. It updates
        the active SOC and actual power only if fallback-only mode is disabled
        or if MQTT telemetry is currently stale/missing.
        """
        if not self.zendure_api.should_poll(cfg):
            return

        try:
            report = self.zendure_api.fetch_report(cfg)
        except Exception as exc:
            with self.state.lock:
                self.state.last_local_api_error = str(exc)
                self.state.last_local_api_error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return

        now = time.time()
        now_text = datetime.now().strftime("%H:%M:%S")
        props = report.get("properties", {}) if isinstance(report, dict) else {}
        pack_data = report.get("packData", []) if isinstance(report, dict) else []
        first_pack = pack_data[0] if isinstance(pack_data, list) and pack_data else {}

        electric_level = self._safe_int(props.get("electricLevel"))
        pack_soc = self._safe_int(first_pack.get("socLevel"))
        priority = str(cfg.get("ZENDURE_LOCAL_API_SOC_PRIORITY", "properties_first"))
        if priority == "pack_first":
            api_soc = pack_soc if pack_soc is not None else electric_level
        else:
            api_soc = electric_level if electric_level is not None else pack_soc

        pack_input = self._safe_int(props.get("packInputPower"))
        output_home = self._safe_int(props.get("outputHomePower"))
        grid_input = self._safe_int(props.get("gridInputPower"))
        output_pack = self._safe_int(props.get("outputPackPower"))

        pack_metrics = []
        headunit_temp = zendure_temp_to_celsius(props.get("hyperTmp"))
        if headunit_temp is not None:
            pack_metrics.append({
                "pack_sn": str(report.get("sn", cfg.get("DEVICE_ID", "headunit"))) if isinstance(report, dict) else "headunit",
                "temperature_c": headunit_temp,
                "temperature_raw": props.get("hyperTmp"),
            })
        if isinstance(pack_data, list):
            for idx, pack in enumerate(pack_data):
                if not isinstance(pack, dict):
                    continue
                item = {"pack_sn": str(pack.get("sn", f"pack-{idx+1}"))}
                temp = zendure_temp_to_celsius(pack.get("maxTemp"))
                if temp is not None:
                    item["temperature_c"] = temp
                    item["temperature_raw"] = pack.get("maxTemp")
                if pack.get("power") is not None:
                    item["power_w"] = pack.get("power")
                if pack.get("socLevel") is not None:
                    item["soc_percent"] = pack.get("socLevel")
                if pack.get("state") is not None:
                    item["state"] = pack.get("state")
                pack_metrics.append(item)

        mqtt_fresh = self.mqtt_soc_is_fresh(cfg)
        fallback_only = bool(cfg.get("ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY", True))
        use_api_as_active_soc = bool(api_soc is not None and (not fallback_only or not mqtt_fresh))
        use_api_as_active_power = bool((pack_input is not None or output_home is not None or grid_input is not None or output_pack is not None) and (not fallback_only or not self.zendure_power_is_fresh(cfg)))

        with self.state.lock:
            self.state.local_api_electric_level = electric_level
            self.state.local_api_pack_soc_level = pack_soc
            self.state.local_api_soc = api_soc
            self.state.last_local_api_update_epoch = now
            self.state.last_local_api_update_time = now_text
            self.state.last_local_api_error = "none"
            self.state.last_local_api_error_time = "-"

            if use_api_as_active_soc:
                self.state.battery_soc = int(api_soc)
                self.state.last_soc_update_epoch = now
                self.state.last_soc_update_time = now_text
                self.state.zendure_telemetry_source = "Lokale API"
                self.state.zendure_local_api_fallback_active = fallback_only

            if use_api_as_active_power:
                self.state.update_zendure_headunit_power(
                    "Lokale API",
                    pack_input=pack_input,
                    output_home=output_home,
                    grid_input=grid_input,
                    output_pack=output_pack,
                )
                if not use_api_as_active_soc and not fallback_only:
                    self.state.zendure_telemetry_source = "Lokale API"

        if use_api_as_active_soc and fallback_only:
            self.state.add_limiter("ZENDURE_API_FALLBACK")

        if pack_metrics:
            self.state.update_zendure_battery_metrics("Lokale API", pack_metrics)

    def _safe_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(float(value))
        except Exception:
            return None

    def second_battery_data_is_fresh(self, cfg: Dict[str, Any]) -> bool:
        """Return True when the latest second-battery MQTT values are fresh."""
        with self.state.lock:
            last_evcc = self.state.last_sma_battery_update_epoch
        timeout = cfg.get("SECOND_BATTERY_STALE_TIMEOUT_SECONDS", cfg.get("EVCC_STALE_TIMEOUT_SECONDS", 30))
        return last_evcc is not None and (time.time() - last_evcc) <= timeout

    def update_second_battery_display_metrics(self, cfg: Dict[str, Any]) -> None:
        """Normalize second-battery values for UI/CSV/graph independent of AUTO.

        This method intentionally does not calculate Cross-Charge control values.
        It is safe to run in NIGHT_DISCHARGE, FIXED_CHARGE, FIXED_DISCHARGE,
        STOP_HOLD and Safe-State paths because it only derives display values
        from the most recent MQTT raw values.
        """
        if not cross_charge_enabled(cfg):
            with self.state.lock:
                self.state.sma_battery_discharge_power = 0.0
                self.state.sma_battery_display_power = 0.0
                self.state.second_battery_data_available = False
                self.state.second_battery_data_fresh = False
                self.state.second_battery_data_valid = False
                self.state.second_battery_validity_reason = "SECOND_BATTERY_DISABLED"
                self.state.second_battery_data_used_for_control = False
            return

        sign = cfg.get("SECOND_BATTERY_DISCHARGE_SIGN", cfg.get("EVCC_SMA_DISCHARGE_SIGN", 1))
        with self.state.lock:
            sma_power = self.state.sma_battery_power
            last_evcc = self.state.last_sma_battery_update_epoch

        fresh = self.second_battery_data_is_fresh(cfg)
        sma_discharge = normalize_discharge_power_w(sma_power, sign)
        sma_display_power = display_power_w(sma_power, sign)
        age_s = None if last_evcc is None else max(0, int(time.time() - last_evcc))

        with self.state.lock:
            self.state.sma_battery_discharge_power = sma_discharge
            self.state.sma_battery_display_power = sma_display_power
            self.state.second_battery_data_available = last_evcc is not None
            self.state.second_battery_data_fresh = fresh
            self.state.second_battery_data_valid = fresh
            self.state.second_battery_data_age_seconds = age_s
            if last_evcc is None:
                self.state.second_battery_validity_reason = "SECOND_BATTERY_MISSING"
            elif fresh:
                self.state.second_battery_validity_reason = "OK"
            else:
                self.state.second_battery_validity_reason = "SECOND_BATTERY_STALE"
            # This method only updates display metrics. AUTO/Grid-dependent
            # Cross-Charge code sets this flag to True when it actually uses
            # the values for a control decision.
            self.state.second_battery_data_used_for_control = False

    def update_cross_charge_control_metrics(self, cfg: Dict[str, Any]) -> None:
        """Update AUTO/grid-dependent Cross-Charge metrics.

        Requires a current grid measurement. It must not be called from fixed
        modes or night mode, because those modes deliberately do not depend on
        Shelly/UniMeter data.
        """
        with self.state.lock:
            grid_power = self.state.grid_power
            sma_discharge = self.state.sma_battery_discharge_power

        if not cross_charge_enabled(cfg):
            effective = max(0, int(-grid_power))
            with self.state.lock:
                self.state.effective_export_power = effective
                self.state.effective_export_power_valid = True
                self.state.effective_export_power_used_for_control = True
                self.state.second_battery_data_used_for_control = False
            return

        evcc_stale = not self.second_battery_data_is_fresh(cfg)
        if evcc_stale:
            self.state.add_limiter("EVCC_STALE")

        export_power = max(0.0, -grid_power)
        if evcc_stale and cfg.get("SECOND_BATTERY_STALE_BLOCK_CHARGE", cfg.get("EVCC_STALE_BLOCK_CHARGE", True)):
            effective = 0
        else:
            effective = max(0, int(export_power - sma_discharge - cfg.get("CROSS_CHARGE_RESERVE_W", 100)))

        with self.state.lock:
            self.state.effective_export_power = effective
            self.state.effective_export_power_valid = True
            self.state.effective_export_power_used_for_control = True
            self.state.second_battery_data_used_for_control = True

    def update_sma_metrics(self, cfg: Dict[str, Any]) -> None:
        """Backward-compatible wrapper for AUTO/Cross-Charge updates."""
        self.update_second_battery_display_metrics(cfg)
        self.update_cross_charge_control_metrics(cfg)

    def update_cycle_display_metrics(self, cfg: Dict[str, Any]) -> None:
        """Housekeeping for values that must be current on every cycle path."""
        self.update_second_battery_display_metrics(cfg)
        self.state.refresh_zendure_headunit_power()

    def mark_grid_not_used_for_control(self) -> None:
        with self.state.lock:
            self.state.grid_power_used_for_control = False

    def soc_is_fresh(self, cfg: Dict[str, Any]) -> bool:
        with self.state.lock:
            soc = self.state.battery_soc
            last_soc = self.state.last_soc_update_epoch
        if soc is None or last_soc is None:
            return False
        return (time.time() - last_soc) <= cfg.get("SOC_STALE_TIMEOUT_SECONDS", 90)

    def sma_guard_blocks_existing_charge(self, cfg: Dict[str, Any]) -> bool:
        if not cross_charge_enabled(cfg):
            return False

        with self.state.lock:
            last_input = self.state.last_input_power
            sma_discharge = self.state.sma_battery_discharge_power

        if last_input <= 0:
            return False

        if sma_discharge >= cfg.get("SMA_DISCHARGE_BLOCK_W", 80):
            self.state.add_limiter("SMA_DISCHARGE")
            self.ramp_down_charge(
                cfg,
                "Cross-Charge-Schutz: Zusatzbatterie entlädt während Zendure lädt -> Zendure-Ladung wird reduziert",
            )
            return True

        return False

    def safe_state(self, reason: str) -> None:
        with self.state.lock:
            need_force = (self.state.last_input_power != 0 or self.state.last_output_power != 0 or self.state.current_mode != "SAFE_STATE")
        self.mqtt.set_output_limit(0, force=need_force)
        self.mqtt.set_input_limit(0, force=need_force)
        with self.state.lock:
            self.state.last_output_power = 0
            self.state.last_input_power = 0
            self.state.current_target_power = 0
            self.state.last_target_before_smoothing = 0
            self.state.last_target_after_smoothing = 0
            self.state.last_target_after_ramp = 0
            self.state.safe_state_counter += 1
            self.state.control_reason = reason
            self.state.technical_control_path = "SAFE_STATE"
            self.state.last_control_action = "SAFE_STATE -> 0 W"
        self.state.set_mode("SAFE_STATE")
        self.state.add_event(f"Safe-State: {reason}")

    def handle_manual_mode(self, cfg: Dict[str, Any], manual_mode: str) -> None:
        if manual_mode == "STOP_HOLD":
            self.stop_hold("Manueller Modus Stop/Hold aktiv")
            return

        if manual_mode not in ("FIXED_DISCHARGE", "FIXED_CHARGE"):
            self.state.add_limiter("MANUAL_MODE_INVALID")
            self.stop_hold(f"Unbekannter manueller Modus: {manual_mode}")
            return

        if not self.soc_is_fresh(cfg):
            self.state.add_limiter("SOC_STALE")
            self.safe_state("Manueller Modus blockiert: Zendure SOC fehlt oder ist veraltet")
            return

        if manual_mode == "FIXED_DISCHARGE":
            self.handle_manual_fixed_discharge(cfg)
            return

        self.handle_manual_fixed_charge(cfg)

    def stop_hold(self, reason: str) -> None:
        with self.state.lock:
            need_force = (
                self.state.current_mode != "STOP_HOLD"
                or self.state.last_input_power != 0
                or self.state.last_output_power != 0
            )

        self.mqtt.set_output_limit(0, force=need_force)
        self.mqtt.set_input_limit(0, force=need_force)

        with self.state.lock:
            self.state.last_output_power = 0
            self.state.last_input_power = 0
            self.state.current_target_power = 0
            self.state.last_target_before_smoothing = 0
            self.state.last_target_after_smoothing = 0
            self.state.last_target_after_ramp = 0
            self.state.control_reason = reason
            self.state.technical_control_path = "MANUAL -> STOP_HOLD"
            self.state.last_control_action = "STOP_HOLD -> 0 W"

        self.state.set_mode("STOP_HOLD")

    def handle_manual_fixed_discharge(self, cfg: Dict[str, Any]) -> None:
        with self.state.lock:
            soc = self.state.battery_soc

        target_soc = max(
            int(cfg.get("MIN_SOC_PERCENT", 15)),
            int(cfg.get("MANUAL_FIXED_DISCHARGE_TARGET_SOC", cfg.get("MIN_SOC_PERCENT", 15))),
        )

        if soc is None or soc <= target_soc:
            self.complete_manual_mode(
                cfg,
                str(cfg.get("MANUAL_DISCHARGE_AFTER_TARGET", "AUTO")),
                f"Manuelle Entladung beendet: Ziel-SOC {target_soc} % erreicht",
            )
            return

        target = min(
            int(cfg.get("MANUAL_FIXED_DISCHARGE_POWER_W", 0)),
            int(cfg.get("MAX_DISCHARGE_POWER_W", 0)),
        )
        target = max(0, target)

        self.mqtt.set_ac_mode("Output mode")
        self.mqtt.set_input_limit(0)
        self.mqtt.set_output_limit(target)

        with self.state.lock:
            self.state.last_input_power = 0
            self.state.last_output_power = target
            self.state.current_target_power = target
            self.state.last_target_before_smoothing = target
            self.state.last_target_after_smoothing = target
            self.state.last_target_after_ramp = target
            self.state.control_reason = f"Manuelle feste Entladung bis {target_soc} % SOC"
            self.state.technical_control_path = "MANUAL -> FIXED_DISCHARGE -> OUTPUT"
            self.state.last_control_action = f"MANUAL_DISCHARGE -> {target} W"

        self.state.set_mode("MANUAL_FIXED_DISCHARGE")
        if cfg.get("LOG_MANUAL", False):
            self.log(f"[MANUAL] Feste Entladung: {target} W bis {target_soc} %")

    def handle_manual_fixed_charge(self, cfg: Dict[str, Any]) -> None:
        with self.state.lock:
            soc = self.state.battery_soc

        target_soc = min(
            int(cfg.get("MAX_SOC_PERCENT", 100)),
            int(cfg.get("MANUAL_FIXED_CHARGE_TARGET_SOC", cfg.get("MAX_SOC_PERCENT", 100))),
        )

        if soc is None or soc >= target_soc:
            self.complete_manual_mode(
                cfg,
                str(cfg.get("MANUAL_CHARGE_AFTER_TARGET", "AUTO")),
                f"Manuelle Beladung beendet: Ziel-SOC {target_soc} % erreicht",
            )
            return

        target = min(
            int(cfg.get("MANUAL_FIXED_CHARGE_POWER_W", 0)),
            int(cfg.get("MAX_CHARGE_POWER_W", 0)),
        )
        target = max(0, target)

        self.mqtt.set_ac_mode("Input mode")
        self.mqtt.set_output_limit(0)
        self.mqtt.set_input_limit(target)

        with self.state.lock:
            self.state.last_output_power = 0
            self.state.last_input_power = target
            self.state.current_target_power = target
            self.state.last_target_before_smoothing = target
            self.state.last_target_after_smoothing = target
            self.state.last_target_after_ramp = target
            self.state.control_reason = f"Manuelle feste Beladung bis {target_soc} % SOC"
            self.state.technical_control_path = "MANUAL -> FIXED_CHARGE -> INPUT"
            self.state.last_control_action = f"MANUAL_CHARGE -> {target} W"

        self.state.set_mode("MANUAL_FIXED_CHARGE")
        if cfg.get("LOG_MANUAL", False):
            self.log(f"[MANUAL] Feste Beladung: {target} W bis {target_soc} %")

    def complete_manual_mode(self, cfg: Dict[str, Any], after_target: str, reason: str) -> None:
        new_cfg = dict(cfg)
        new_cfg["MANUAL_MODE"] = "STOP_HOLD" if after_target == "STOP_HOLD" else "AUTO"
        self.config_manager.save(new_cfg)
        self.state.add_event(reason)

        if cfg.get("LOG_MANUAL", False):
            self.log(f"[MANUAL] {reason}; nächster Modus: {new_cfg['MANUAL_MODE']}")

        if new_cfg["MANUAL_MODE"] == "STOP_HOLD":
            self.stop_hold(reason + " -> Stop/Hold")
        else:
            self.stop_hold(reason + " -> Automatik ab nächstem Zyklus")

    def handle_deadband(self) -> None:
        self.state.add_limiter("DEADBAND")
        with self.state.lock:
            self.state.current_target_power = max(self.state.last_output_power, self.state.last_input_power)
            self.state.control_reason = "Innerhalb Totzone -> Leistung halten"
            self.state.technical_control_path = "GRID -> DEADBAND -> HOLD_POWER"
            self.state.last_control_action = f"HOLD -> {self.state.current_target_power} W"
        self.state.set_mode("HOLD")

    def handle_night_mode(self, cfg: Dict[str, Any]) -> None:
        with self.state.lock:
            soc = self.state.battery_soc
        if soc is None or soc <= cfg["MIN_SOC_PERCENT"]:
            self.state.add_limiter("MIN_SOC")
            self.safe_state("Nachtmodus blockiert: Zendure SOC zu niedrig")
            return

        target = int(cfg["NIGHT_DISCHARGE_POWER_W"])
        self.mqtt.set_ac_mode("Output mode")
        self.mqtt.set_input_limit(0)
        self.mqtt.set_output_limit(target)
        with self.state.lock:
            self.state.last_input_power = 0
            self.state.last_output_power = target
            self.state.current_target_power = target
            self.state.last_target_before_smoothing = target
            self.state.last_target_after_smoothing = target
            self.state.last_target_after_ramp = target
            self.state.control_reason = "Nachtmodus aktiv"
            self.state.technical_control_path = "NIGHT_MODE -> OUTPUT"
            self.state.last_control_action = f"NIGHT_DISCHARGE -> {target} W"
        self.state.set_mode("NIGHT_DISCHARGE")

    def handle_discharge(self, cfg: Dict[str, Any], grid_power: float) -> None:
        with self.state.lock:
            soc = self.state.battery_soc
            last_input = self.state.last_input_power
            last_output = self.state.last_output_power
            mode = self.state.current_mode
            mode_duration = self.state.last_mode_duration_seconds

        if soc is None or soc <= cfg["MIN_SOC_PERCENT"]:
            self.state.add_limiter("MIN_SOC")
            self.safe_state("Entladung blockiert: Zendure SOC zu niedrig")
            return

        if last_input > 0:
            self.ramp_down_charge(cfg, "Wechsel auf Entladung: Ladeleistung wird erst reduziert")
            return

        if mode == "CHARGE" and mode_duration < cfg.get("MODE_CHANGE_LOCK_SECONDS", 0):
            self.state.add_limiter("MODE_CHANGE_LOCK")
            self.handle_deadband()
            return

        raw_target = last_output + int(grid_power * cfg.get("CONTROL_GAIN", 0.30))
        target = max(0, min(raw_target, int(cfg["MAX_DISCHARGE_POWER_W"])))
        target_smoothed = self.smooth_transition(last_output, target, cfg)
        target_ramped = self.limit_power_step(last_output, target_smoothed, cfg)

        self.mqtt.set_ac_mode("Output mode")
        self.mqtt.set_input_limit(0)
        self.mqtt.set_output_limit(target_ramped)

        with self.state.lock:
            self.state.last_input_power = 0
            self.state.last_output_power = target_ramped
            self.state.current_target_power = target_ramped
            self.state.last_target_before_smoothing = raw_target
            self.state.last_target_after_smoothing = target_smoothed
            self.state.last_target_after_ramp = target_ramped
            self.state.control_reason = "Netzbezug erkannt -> Zendure entlädt"
            self.state.technical_control_path = "GRID -> DISCHARGE_CONTROL -> OUTPUT"
            self.state.last_control_action = f"DISCHARGE -> {target_ramped} W"
        self.state.set_mode("DISCHARGE")

        if cfg.get("LOG_CONTROL", False):
            self.log(f"[CTRL] Entladen: raw={raw_target} smooth={target_smoothed} ramp={target_ramped}")

    def handle_charge(self, cfg: Dict[str, Any], grid_power: float) -> None:
        with self.state.lock:
            soc = self.state.battery_soc
            last_input = self.state.last_input_power
            last_output = self.state.last_output_power
            effective = self.state.effective_export_power
            sma_discharge = self.state.sma_battery_discharge_power

        if soc is None or soc >= cfg["MAX_SOC_PERCENT"]:
            self.state.add_limiter("MAX_SOC")
            self.safe_state("Ladung blockiert: Zendure SOC zu hoch")
            return

        if last_output > 0:
            self.ramp_down_discharge(cfg, "Wechsel auf Ladung: Entladeleistung wird erst reduziert")
            return

        if sma_discharge >= cfg.get("SMA_DISCHARGE_BLOCK_W", 80):
            self.state.add_limiter("SMA_DISCHARGE")
            self.ramp_down_charge(cfg, "Cross-Charge-Schutz: Zusatzbatterie entlädt -> Zendure-Ladung blockiert")
            return

        if effective < cfg.get("MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W", 150):
            self.state.add_limiter("LOW_EFFECTIVE_SURPLUS")
            self.ramp_down_charge(cfg, "Keine sichere PV-Überschussladung nach Zusatzbatterie-/Cross-Charge-Abzug")
            return

        raw_target = last_input + int(effective * cfg.get("CONTROL_GAIN", 0.30))
        target = max(0, min(raw_target, int(cfg["MAX_CHARGE_POWER_W"])))
        target_smoothed = self.smooth_transition(last_input, target, cfg)
        target_ramped = self.limit_power_step(last_input, target_smoothed, cfg)

        self.mqtt.set_ac_mode("Input mode")
        self.mqtt.set_output_limit(0)
        self.mqtt.set_input_limit(target_ramped)

        with self.state.lock:
            self.state.last_output_power = 0
            self.state.last_input_power = target_ramped
            self.state.current_target_power = target_ramped
            self.state.last_target_before_smoothing = raw_target
            self.state.last_target_after_smoothing = target_smoothed
            self.state.last_target_after_ramp = target_ramped
            self.state.control_reason = "PV-Überschuss erkannt -> Zendure lädt"
            self.state.technical_control_path = "GRID -> CROSS_CHARGE -> CHARGE_CONTROL -> INPUT"
            self.state.last_control_action = f"CHARGE -> {target_ramped} W"
        self.state.set_mode("CHARGE")

        if cfg.get("LOG_CONTROL", False):
            self.log(f"[CTRL] Laden: effective={effective} raw={raw_target} smooth={target_smoothed} ramp={target_ramped}")

    def ramp_down_charge(self, cfg: Dict[str, Any], reason: str) -> None:
        with self.state.lock:
            last_input = self.state.last_input_power
        step = int(cfg.get("SMA_GUARD_RAMP_DOWN_W", cfg.get("MAX_POWER_STEP_W", 150)))
        target = max(0, last_input - step)
        self.mqtt.set_ac_mode("Input mode")
        self.mqtt.set_output_limit(0)
        self.mqtt.set_input_limit(target)
        with self.state.lock:
            self.state.last_output_power = 0
            self.state.last_input_power = target
            self.state.current_target_power = target
            self.state.last_target_before_smoothing = target
            self.state.last_target_after_smoothing = target
            self.state.last_target_after_ramp = target
            self.state.control_reason = reason
            self.state.technical_control_path = "GRID -> CROSS_CHARGE -> CHARGE_RAMP_DOWN"
            self.state.last_control_action = f"CHARGE_RAMP_DOWN -> {target} W"
        self.state.set_mode("BLOCKED_BY_SMA" if target == 0 else "CHARGE_RAMP_DOWN")

    def ramp_down_discharge(self, cfg: Dict[str, Any], reason: str) -> None:
        with self.state.lock:
            last_output = self.state.last_output_power
        target = max(0, last_output - int(cfg.get("MAX_POWER_STEP_W", 150)))
        self.mqtt.set_ac_mode("Output mode")
        self.mqtt.set_input_limit(0)
        self.mqtt.set_output_limit(target)
        with self.state.lock:
            self.state.last_input_power = 0
            self.state.last_output_power = target
            self.state.current_target_power = target
            self.state.last_target_before_smoothing = target
            self.state.last_target_after_smoothing = target
            self.state.last_target_after_ramp = target
            self.state.control_reason = reason
            self.state.technical_control_path = "GRID -> DISCHARGE_RAMP_DOWN"
            self.state.last_control_action = f"DISCHARGE_RAMP_DOWN -> {target} W"
        self.state.set_mode("HOLD" if target == 0 else "DISCHARGE_RAMP_DOWN")

    def smooth_transition(self, old_value: int, target_value: int, cfg: Dict[str, Any]) -> int:
        factor = float(cfg.get("SMOOTHING_FACTOR", 0.25))
        return int((old_value * (1 - factor)) + (target_value * factor))

    def limit_power_step(self, old_value: int, new_value: int, cfg: Dict[str, Any]) -> int:
        diff = new_value - old_value
        max_step = int(cfg.get("MAX_POWER_STEP_W", 150))
        if abs(diff) <= max_step:
            return new_value
        self.state.add_limiter("RAMP_LIMIT")
        return old_value + max_step if diff > 0 else old_value - max_step

    def is_night_discharge_active(self, cfg: Dict[str, Any]) -> bool:
        if not cfg.get("NIGHT_DISCHARGE_ENABLED", False):
            return False
        now = datetime.now()
        start = now.replace(hour=int(cfg["NIGHT_START_HOUR"]), minute=int(cfg["NIGHT_START_MINUTE"]), second=0, microsecond=0)
        end = now.replace(hour=int(cfg["NIGHT_END_HOUR"]), minute=int(cfg["NIGHT_END_MINUTE"]), second=0, microsecond=0)
        if end <= start:
            return now >= start or now <= end
        return start <= now <= end

    def determine_cycle_required_sources(self, cfg: Dict[str, Any]) -> list:
        """Return data sources required by the current mode/path.

        This is a diagnostic contract, not a second control algorithm. The mode
        handlers still perform the actual safety decisions. The returned list is
        used by the freshness/validity model to make the final decision path
        auditable in UI, CSV and tests.
        """
        with self.state.lock:
            mode = self.state.current_mode
            path = self.state.technical_control_path
            active_limiters = set(self.state.active_limiters)
            action = self.state.last_control_action

        required = []

        def require(source: str) -> None:
            if source not in required:
                required.append(source)

        if path.startswith("GRID") or "SHELLY_STALE" in active_limiters:
            require("grid")

        if (
            mode in {
                "CHARGE", "DISCHARGE", "CHARGE_RAMP_DOWN", "DISCHARGE_RAMP_DOWN",
                "BLOCKED_BY_SMA", "NIGHT_DISCHARGE", "MANUAL_FIXED_CHARGE",
                "MANUAL_FIXED_DISCHARGE",
            }
            or "SOC_STALE" in active_limiters
            or "MIN_SOC" in active_limiters
            or "MAX_SOC" in active_limiters
        ):
            require("soc")

        command_modes = {
            "SAFE_STATE", "STOP_HOLD", "CHARGE", "DISCHARGE", "CHARGE_RAMP_DOWN",
            "DISCHARGE_RAMP_DOWN", "BLOCKED_BY_SMA", "NIGHT_DISCHARGE",
            "MANUAL_FIXED_CHARGE", "MANUAL_FIXED_DISCHARGE",
        }
        if cfg.get("MQTT_DISCONNECTED_SAFE_STATE", False) or mode in command_modes:
            require("mqtt_command_path")

        if cross_charge_enabled(cfg) and (
            "CROSS_CHARGE" in path
            or "EVCC_STALE" in active_limiters
            or "SMA_DISCHARGE" in active_limiters
        ):
            require("second_battery")

        return required

    def update_charge_acceptance_diagnostic(self, cfg: Dict[str, Any]) -> None:
        result = classify_charge_acceptance(
            soc_percent=self.state.battery_soc,
            max_soc_percent=cfg.get("MAX_SOC_PERCENT", 100),
            target_charge_w=self.state.last_input_power,
            actual_charge_w=self.state.actual_zendure_system_charge_power,
            grid_power_w=self.state.grid_power,
            min_effective_target_w=max(100, int(cfg.get("MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W", 150)) // 2),
            export_threshold_w=max(80, int(cfg.get("DEADBAND_W", 80))),
        )
        with self.state.lock:
            self.state.charge_acceptance_state = result.get("state", "ok")
            self.state.charge_acceptance_reason = result.get("reason", "-")

    def finish_cycle(self, cfg: Dict[str, Any], loop_start: float) -> None:
        with self.state.lock:
            self.state.last_loop_duration_ms = int((time.time() - loop_start) * 1000)
            self.state.last_limit_reason = ", ".join(self.state.active_limiters) if self.state.active_limiters else "none"
            path = self.state.technical_control_path
            mode = self.state.current_mode
            self.state.grid_power_used_for_control = path.startswith("GRID")
            self.state.effective_export_power_used_for_control = path.startswith("GRID") and (
                "CHARGE" in path or "CROSS_CHARGE" in path
            )
            self.state.soc_used_for_control = (
                mode in {
                    "CHARGE", "DISCHARGE", "CHARGE_RAMP_DOWN", "DISCHARGE_RAMP_DOWN",
                    "BLOCKED_BY_SMA", "NIGHT_DISCHARGE", "MANUAL_FIXED_CHARGE",
                    "MANUAL_FIXED_DISCHARGE",
                }
                or any(limiter in self.state.active_limiters for limiter in ("SOC_STALE", "MIN_SOC", "MAX_SOC"))
            )
            command_modes = {
                "SAFE_STATE", "STOP_HOLD", "CHARGE", "DISCHARGE", "CHARGE_RAMP_DOWN",
                "DISCHARGE_RAMP_DOWN", "BLOCKED_BY_SMA", "NIGHT_DISCHARGE",
                "MANUAL_FIXED_CHARGE", "MANUAL_FIXED_DISCHARGE",
            }
            self.state.mqtt_command_path_used_for_control = mode in command_modes
            if not self.state.grid_power_used_for_control:
                self.state.effective_export_power_valid = False

        self.update_cycle_display_metrics(cfg)
        required_sources = self.determine_cycle_required_sources(cfg)
        self.state.set_control_source_requirements(required_sources)
        self.state.update_data_validity_model(cfg)
        self.update_charge_acceptance_diagnostic(cfg)
        self.state.record_graph_point(int(cfg.get("GRAPH_HISTORY_LIMIT", 300)))
        try:
            last_row = self.state.snapshot()["graph_history"][-1]
            self.csv_logger.log(cfg, last_row)
        except Exception as exc:
            self.state.set_error(f"CSV logging error: {exc}")
