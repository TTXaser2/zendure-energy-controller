# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from config_manager import ConfigManager
from csv_logger import CsvRotatingLogger
from app_logger import RotatingAppLogger
from mqtt_bridge import MqttBridge
from shelly_client import ShellyClient
from sma_energy_meter import SmaEnergyMeterClient
from measurement import classify_charge_acceptance
from command_lifecycle import (
    DesiredCommandBatch,
    INTENT_CHARGE,
    INTENT_DISCHARGE,
    INTENT_IDLE,
    INTENT_NEUTRALIZE,
    COMMAND_GATE_UNPROTECTED,
    COMMAND_GATE_WAIT_SMART_MODE,
    COMMAND_GATE_WAIT_FULL_STATE,
    COMMAND_GATE_READY,
    COMMAND_GATE_SAFETY_NEUTRALIZATION,
    intent_for_signed_target,
)
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
        sma_energy_meter_client: Optional[SmaEnergyMeterClient] = None,
    ) -> None:
        self.config_manager = config_manager
        self.state = state
        self.mqtt = mqtt_bridge
        self.shelly = shelly_client
        self.sma_energy_meter = sma_energy_meter_client or SmaEnergyMeterClient()
        self.csv_logger = csv_logger
        self.zendure_api = zendure_api_client
        self.app_logger = app_logger or RotatingAppLogger()
        self._running = True
        self._cycle_timing_parts: Dict[str, int] = {}
        # After a controller/service restart the Zendure inverter may still obey
        # a previously sent limit, while the in-memory command state starts at
        # 0 W.  If the first AUTO decision falls into HOLD/DEADBAND, publish one
        # explicit neutral command so UI, state and physical device cannot drift.
        self._startup_deadband_neutralized = False
        self._last_sma_diag_log_epoch = 0.0
        self._last_sma_diag_key = None
        self._last_sma_large_gap_epoch = None
        self._last_zendure_mqtt_status = ""
        self._mqtt_uncertain_since_epoch: Optional[float] = None
        self._mqtt_uncertain_cycles: int = 0
        self._mqtt_uncertain_had_hard_loss: bool = False
        self._last_resync_signature: str = ""
        self._last_resync_epoch: float = 0.0
        # RC11 command lifecycle.  The legacy target fields remain for test and
        # analysis compatibility, but timer continuity is now intent based.
        self._command_effect_watch_target: int = 0
        self._command_effect_watch_start_epoch: Optional[float] = None
        self._command_effect_watch_intent: str = INTENT_IDLE
        self._command_tracking_mismatch_start_epoch: Optional[float] = None
        self._command_effect_telemetry_pause_epoch: Optional[float] = None
        self._command_effect_last_resend_epoch: float = 0.0
        self._neutralization_last_resend_epoch: float = 0.0
        self._last_command_effect_log_epoch: float = 0.0
        self._command_sequence_id: int = 0
        self._desired_command_batch: Optional[DesiredCommandBatch] = None
        self._last_non_neutral_ac_mode: str = "Output mode"
        self._command_state_verification_signature: str = ""
        self._command_state_verification_epoch: float = 0.0
        self._neutralization_physical_signature: str = ""
        self._neutralization_confirmed_signature: str = ""
        self._command_effect_last_charge_soc: Optional[float] = None
        # RC14 high-SOC charge-acceptance episode state.  The fields are
        # intentionally scalar so the Pi never accumulates an unbounded sample
        # history.  They are reset whenever the charge intent/static command
        # contract no longer applies.
        self._charge_acceptance_zero_since_epoch: Optional[float] = None
        self._charge_acceptance_zero_cycles: int = 0
        self._charge_acceptance_last_positive_w: Optional[int] = None
        self._charge_acceptance_taper_steps: int = 0
        self._last_published_intent: str = INTENT_IDLE
        # RC15 late-effect guard. A confirmed active-command mismatch may leave a
        # device-side command queued or delayed. Before neutral/opposite intent is
        # allowed, establish 0/0 read-back plus independent physical neutrality.
        self._late_effect_guard_active: bool = False
        self._late_effect_guard_previous_intent: str = INTENT_IDLE
        self._late_effect_guard_pending_intent: str = INTENT_IDLE
        self._late_effect_guard_pending_target_w: int = 0
        self._late_effect_guard_pending_reason: str = ""
        self._late_effect_guard_started_monotonic: Optional[float] = None
        self._late_effect_guard_first_neutral_monotonic: Optional[float] = None
        self._late_effect_guard_neutral_observation_count: int = 0
        self._late_effect_guard_last_observation_signature: str = ""
        self._last_physical_non_neutral_direction: str = ""

    def log(self, message: str) -> None:
        cfg = self.config_manager.get()
        if cfg.get("DEBUG", False):
            print(message)
        self.app_logger.log(cfg, message)

    def _timed_phase(self, name: str, func, *args, **kwargs):
        started = time.perf_counter_ns()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
            self._cycle_timing_parts[name] = float(self._cycle_timing_parts.get(name, 0.0)) + elapsed_ms

    def _timed_local_api_phase(self, cfg: Dict[str, Any]):
        """Measure the optional local API only when a real poll was attempted.

        ``should_poll()`` can skip most controller cycles because of its polling
        interval or backoff.  Recording those cheap no-op calls as 0,0 ms is
        misleading in the operations dashboard.  ``fetch_report()`` updates
        ``last_poll_epoch`` before every actual request, including failed ones,
        so comparing the timestamp is a side-effect-free execution marker.
        """
        before = getattr(self.zendure_api, "last_poll_epoch", None)
        result = self._timed_phase("zendure_local_api_ms", self.update_zendure_telemetry_from_local_api, cfg)
        after = getattr(self.zendure_api, "last_poll_epoch", None)
        if after == before:
            self._cycle_timing_parts.pop("zendure_local_api_ms", None)
        return result

    def _timed_control_phase(self, func, *args, **kwargs):
        """Measure controller decision work excluding actual MQTT setter calls.

        MQTT setters are measured independently.  Subtracting their nested time
        keeps the visible "Regelentscheidung" value non-overlapping without
        changing the existing handler/control flow.
        """
        mqtt_before = float(self._cycle_timing_parts.get("mqtt_command_path_ms", 0.0))
        started = time.perf_counter_ns()
        try:
            return func(*args, **kwargs)
        finally:
            total_ms = (time.perf_counter_ns() - started) / 1_000_000.0
            mqtt_after = float(self._cycle_timing_parts.get("mqtt_command_path_ms", 0.0))
            exclusive_ms = max(0.0, total_ms - max(0.0, mqtt_after - mqtt_before))
            self._cycle_timing_parts["control_decision_ms"] = float(
                self._cycle_timing_parts.get("control_decision_ms", 0.0)
            ) + exclusive_ms

    def _timed_command_effect_phase(self, func, *args, **kwargs):
        mqtt_before = float(self._cycle_timing_parts.get("mqtt_command_path_ms", 0.0))
        started = time.perf_counter_ns()
        try:
            return func(*args, **kwargs)
        finally:
            total_ms = (time.perf_counter_ns() - started) / 1_000_000.0
            mqtt_after = float(self._cycle_timing_parts.get("mqtt_command_path_ms", 0.0))
            exclusive_ms = max(0.0, total_ms - max(0.0, mqtt_after - mqtt_before))
            self._cycle_timing_parts["command_effect_monitor_ms"] = float(
                self._cycle_timing_parts.get("command_effect_monitor_ms", 0.0)
            ) + exclusive_ms

    def _timed_mqtt_setter(self, func, *args, **kwargs):
        return self._timed_phase("mqtt_command_path_ms", func, *args, **kwargs)

    @staticmethod
    def _publish_result(value: Any) -> bool:
        # Real MqttBridge setters return bool in RC11.  Older test doubles return
        # None; treat that as an attempted publish to preserve compatibility.
        return True if value is None else bool(value)

    def _mqtt_set_smart_mode(self, enabled: bool = True, force: bool = False) -> bool:
        setter = getattr(self.mqtt, "set_smart_mode", None)
        if setter is None:
            # Compatibility path for historical unit-test doubles. Production
            # MqttBridge always implements the verified smartMode contract.
            return False
        try:
            result = self._timed_mqtt_setter(setter, enabled, force=force)
        except TypeError:
            result = self._timed_mqtt_setter(setter, enabled)
        return self._publish_result(result)

    def _mqtt_set_ac_mode(self, mode: str, force: bool = False) -> bool:
        try:
            result = self._timed_mqtt_setter(self.mqtt.set_ac_mode, mode, force=force)
        except TypeError:
            result = self._timed_mqtt_setter(self.mqtt.set_ac_mode, mode)
        return self._publish_result(result)

    def _mqtt_set_input_limit(self, watts: int, force: bool = False) -> bool:
        try:
            result = self._timed_mqtt_setter(self.mqtt.set_input_limit, watts, force=force)
        except TypeError:
            result = self._timed_mqtt_setter(self.mqtt.set_input_limit, watts)
        return self._publish_result(result)

    def _mqtt_set_output_limit(self, watts: int, force: bool = False) -> bool:
        try:
            result = self._timed_mqtt_setter(self.mqtt.set_output_limit, watts, force=force)
        except TypeError:
            result = self._timed_mqtt_setter(self.mqtt.set_output_limit, watts)
        return self._publish_result(result)

    def _ensure_command_lifecycle_attrs(self) -> None:
        defaults = {
            "_command_effect_watch_target": 0,
            "_command_effect_watch_start_epoch": None,
            "_command_effect_watch_intent": INTENT_IDLE,
            "_command_tracking_mismatch_start_epoch": None,
            "_command_effect_telemetry_pause_epoch": None,
            "_command_effect_last_resend_epoch": 0.0,
            "_neutralization_last_resend_epoch": 0.0,
            "_last_command_effect_log_epoch": 0.0,
            "_command_sequence_id": 0,
            "_desired_command_batch": None,
            "_last_non_neutral_ac_mode": "Output mode",
            "_command_state_verification_signature": "",
            "_command_state_verification_epoch": 0.0,
            "_neutralization_physical_signature": "",
            "_neutralization_confirmed_signature": "",
            "_command_effect_last_charge_soc": None,
            "_charge_acceptance_zero_since_epoch": None,
            "_charge_acceptance_zero_cycles": 0,
            "_charge_acceptance_last_positive_w": None,
            "_charge_acceptance_taper_steps": 0,
            "_last_published_intent": INTENT_IDLE,
            "_late_effect_guard_active": False,
            "_late_effect_guard_previous_intent": INTENT_IDLE,
            "_late_effect_guard_pending_intent": INTENT_IDLE,
            "_late_effect_guard_pending_target_w": 0,
            "_late_effect_guard_pending_reason": "",
            "_late_effect_guard_started_monotonic": None,
            "_late_effect_guard_first_neutral_monotonic": None,
            "_late_effect_guard_neutral_observation_count": 0,
            "_late_effect_guard_last_observation_signature": "",
            "_last_physical_non_neutral_direction": "",
            "_last_resync_signature": "",
            "_last_resync_epoch": 0.0,
            "_last_zendure_mqtt_status": "",
            "_mqtt_uncertain_since_epoch": None,
            "_mqtt_uncertain_cycles": 0,
            "_mqtt_uncertain_had_hard_loss": False,
        }
        for name, value in defaults.items():
            if not hasattr(self, name):
                setattr(self, name, value)

    def _reset_charge_acceptance_episode(self) -> None:
        self._charge_acceptance_zero_since_epoch = None
        self._charge_acceptance_zero_cycles = 0
        self._charge_acceptance_last_positive_w = None
        self._charge_acceptance_taper_steps = 0
        with self.state.lock:
            self.state.command_effect_reference_w = 0

    def _unresolved_active_command_mismatch(self) -> bool:
        """Return True only for an active mismatch that can still take effect late."""
        with self.state.lock:
            if self.state.command_not_effective_active:
                return True
            lifecycle = str(self.state.command_lifecycle_state or "")
            resync_reason = str(self.state.command_resync_reason or "")
        return bool(
            lifecycle == "RECOVERY_VERIFYING"
            and resync_reason.startswith("RESYNC_AFTER_CONFIRMED_MISMATCH")
        )

    def _set_late_effect_pending(self, intent: str, target_w: int, reason: str) -> None:
        self._late_effect_guard_pending_intent = str(intent or INTENT_IDLE)
        self._late_effect_guard_pending_target_w = int(target_w or 0)
        self._late_effect_guard_pending_reason = str(reason or "")
        with self.state.lock:
            self.state.command_late_effect_guard_pending_intent = self._late_effect_guard_pending_intent
            self.state.command_late_effect_guard_pending_target_w = self._late_effect_guard_pending_target_w

    def _reset_late_effect_neutral_confirmation(self) -> None:
        self._late_effect_guard_first_neutral_monotonic = None
        self._late_effect_guard_neutral_observation_count = 0
        self._late_effect_guard_last_observation_signature = ""

    def _late_effect_guard_duration_s(self) -> float:
        if not self._late_effect_guard_active or self._late_effect_guard_started_monotonic is None:
            return 0.0
        return max(0.0, time.monotonic() - float(self._late_effect_guard_started_monotonic))

    def _update_late_effect_guard_state(self, *, reason: Optional[str] = None) -> None:
        with self.state.lock:
            self.state.command_late_effect_guard_active = bool(self._late_effect_guard_active)
            self.state.command_late_effect_guard_previous_intent = (
                self._late_effect_guard_previous_intent if self._late_effect_guard_active else ""
            )
            self.state.command_late_effect_guard_pending_intent = (
                self._late_effect_guard_pending_intent if self._late_effect_guard_active else ""
            )
            self.state.command_late_effect_guard_pending_target_w = (
                int(self._late_effect_guard_pending_target_w) if self._late_effect_guard_active else 0
            )
            self.state.command_late_effect_guard_duration_s = round(self._late_effect_guard_duration_s(), 1)
            if reason is not None:
                self.state.command_late_effect_guard_reason = str(reason)
            elif not self._late_effect_guard_active:
                self.state.command_late_effect_guard_reason = ""

    def _ensure_late_effect_guard_neutralization(self) -> None:
        """Send only volatile zero limits; retain the current AC mode."""
        neutral = self._new_command_batch(
            0,
            reason="LATE_EFFECT_GUARD_NEUTRALIZATION",
            explicit_neutralize=True,
            ac_mode=self._last_non_neutral_ac_mode,
            safety_relevant=True,
        )
        self._publish_command_batch(
            neutral,
            force=True,
            publish_kind="late_effect_guard",
        )
        self._startup_deadband_neutralized = True

    def _activate_late_effect_guard(self, previous_intent: str, pending_intent: str, target_w: int, reason: str) -> None:
        self._late_effect_guard_active = True
        self._late_effect_guard_previous_intent = str(previous_intent)
        self._late_effect_guard_started_monotonic = time.monotonic()
        self._reset_late_effect_neutral_confirmation()
        self._set_late_effect_pending(pending_intent, target_w, reason)
        with self.state.lock:
            self.state.command_late_effect_guard_activation_count += 1
            self.state.command_lifecycle_state = "LATE_EFFECT_NEUTRALIZING"
            self.state.command_effect_category = "COMMAND_NEUTRALIZATION_PENDING"
            self.state.command_effect_confirmed = False
        self._update_late_effect_guard_state(
            reason=(
                f"Unaufgelöster {previous_intent}-Mismatch: sicherer 0/0-Zustand wird vor "
                f"Folgeintent {pending_intent} bestätigt."
            )
        )
        self.state.add_event(
            f"Late-Effect-Guard aktiviert: {previous_intent} -> {pending_intent}"
        )
        self._ensure_late_effect_guard_neutralization()

    def _late_effect_guard_blocks(self, requested_intent: str, target_w: int, reason: str) -> bool:
        """Activate/maintain the guard and retain only the latest follow-up intent."""
        self._ensure_command_lifecycle_attrs()
        requested_intent = str(requested_intent or INTENT_IDLE)
        if self._late_effect_guard_active:
            self._set_late_effect_pending(requested_intent, target_w, reason)
            if requested_intent in {INTENT_CHARGE, INTENT_DISCHARGE}:
                with self.state.lock:
                    self.state.command_late_effect_guard_blocked_command_count += 1
            self._update_late_effect_guard_state()
            return True

        previous = self._desired_command_batch
        if previous is None or previous.intent not in {INTENT_CHARGE, INTENT_DISCHARGE}:
            return False
        if requested_intent == previous.intent:
            return False
        if requested_intent not in {INTENT_NEUTRALIZE, INTENT_CHARGE, INTENT_DISCHARGE}:
            return False
        if not self._unresolved_active_command_mismatch():
            return False

        self._activate_late_effect_guard(
            previous.intent,
            requested_intent,
            target_w,
            reason,
        )
        if requested_intent in {INTENT_CHARGE, INTENT_DISCHARGE}:
            with self.state.lock:
                self.state.command_late_effect_guard_blocked_command_count += 1
        return True

    def _release_late_effect_guard(self, observation_text: str) -> None:
        duration = self._late_effect_guard_duration_s()
        previous_intent = self._late_effect_guard_previous_intent
        self._late_effect_guard_active = False
        self._late_effect_guard_previous_intent = INTENT_IDLE
        self._late_effect_guard_started_monotonic = None
        self._reset_late_effect_neutral_confirmation()
        with self.state.lock:
            self._clear_command_not_effective_locked()
            self.state.command_mismatch_resolution = "LATE_EFFECT_GUARD_RELEASED"
            self.state.command_neutralization_active = False
            self.state.command_neutralization_since_epoch = None
            self.state.command_neutralization_since_time = "-"
            self.state.command_lifecycle_state = "LATE_EFFECT_GUARD_RELEASED"
            self.state.command_effect_category = "COMMAND_NEUTRALIZATION_CONFIRMED"
            self.state.command_effect_reason = (
                f"Late-Effect-Guard nach {duration:.1f} s freigegeben; 0/0-Readback und "
                f"physische Neutralität ({observation_text}) stabil bestätigt."
            )
            self.state.command_effect_confirmed = True
            self.state.command_effect_confirmed_time = datetime.now().strftime("%H:%M:%S")
            self.state.command_effect_confirmed_reason = self.state.command_effect_reason
            self.state.command_late_effect_guard_duration_s = round(duration, 1)
        self._update_late_effect_guard_state(reason="")
        self.state.add_event(
            f"Late-Effect-Guard freigegeben: vorheriger Intent {previous_intent}, Dauer {duration:.1f} s"
        )

    def _resend_late_effect_guard_neutralization(self, reason: str) -> None:
        neutral = self._new_command_batch(
            0,
            reason="LATE_EFFECT_GUARD_NEUTRALIZATION",
            explicit_neutralize=True,
            ac_mode=self._last_non_neutral_ac_mode,
            safety_relevant=True,
        )
        self._publish_command_batch(
            neutral,
            force=True,
            publish_kind="late_effect_guard_resync",
        )
        now_text = datetime.now().strftime("%H:%M:%S")
        with self.state.lock:
            self.state.command_resync_count += 1
            self.state.command_resync_last_time = now_text
            self.state.command_resync_reason = str(reason)
            self.state.command_lifecycle_state = "LATE_EFFECT_NEUTRALIZING"
            self.state.command_effect_category = "COMMAND_RECOVERY_VERIFYING"
            self.state.command_effect_reason = (
                "Late-Effect-Guard: 0-W-Neutralisierung erneut gesendet; Readback und physische Wirkung werden weiter geprüft."
            )
        self.state.add_event(f"Late-Effect-Guard Neutralisierungs-Resync: {reason}")
        self.log(f"[COMMAND_RESYNC] target=0W reason={reason}")

    def _evaluate_late_effect_guard(
        self,
        cfg: Dict[str, Any],
        observation: Dict[str, Any],
        *,
        absolute_tolerance_w: int,
        actual_text: str,
        now_epoch: float,
    ) -> bool:
        """Evaluate the guard with monotonic time and distinct power samples."""
        if not self._late_effect_guard_active:
            return False

        snapshot = self._command_state_snapshot(cfg)
        readback_zero = bool(
            snapshot.get("complete")
            and snapshot.get("smart_mode") == 1
            and int(snapshot.get("input_limit_w") or 0) == 0
            and int(snapshot.get("output_limit_w") or 0) == 0
        )
        direction = str(observation.get("direction") or "UNKNOWN")
        magnitude = int(observation.get("magnitude") or 0)
        physical_neutral = bool(
            observation.get("valid")
            and direction != "CONFLICT"
            and magnitude <= int(absolute_tolerance_w)
        )

        duration_s = self._late_effect_guard_duration_s()
        with self.state.lock:
            self.state.command_late_effect_guard_duration_s = round(duration_s, 1)
            self.state.command_neutralization_active = True
            if self.state.command_neutralization_since_epoch is None:
                self.state.command_neutralization_since_epoch = now_epoch
                self.state.command_neutralization_since_time = datetime.now().strftime("%H:%M:%S")
            power_epoch = (
                self.state.zendure_power_observation_updated_epoch
                if self.state.zendure_power_observation_updated_epoch is not None
                else self.state.last_zendure_power_update_epoch
            )

        if readback_zero and physical_neutral:
            signature = str(power_epoch or "")
            if signature and signature != self._late_effect_guard_last_observation_signature:
                self._late_effect_guard_last_observation_signature = signature
                if self._late_effect_guard_first_neutral_monotonic is None:
                    self._late_effect_guard_first_neutral_monotonic = time.monotonic()
                    self._late_effect_guard_neutral_observation_count = 1
                else:
                    self._late_effect_guard_neutral_observation_count += 1

            stable_elapsed_s = (
                max(0.0, time.monotonic() - float(self._late_effect_guard_first_neutral_monotonic))
                if self._late_effect_guard_first_neutral_monotonic is not None
                else 0.0
            )
            if self._late_effect_guard_neutral_observation_count >= 2 and stable_elapsed_s >= 6.0:
                self._neutralization_confirmed_signature = self._neutralization_physical_signature
                self._release_late_effect_guard(actual_text)
                return True

            with self.state.lock:
                self._clear_command_not_effective_locked()
                self.state.command_lifecycle_state = "LATE_EFFECT_NEUTRAL_STABILIZING"
                self.state.command_effect_category = "COMMAND_NEUTRALIZATION_PENDING"
                self.state.command_effect_reason = (
                    f"Late-Effect-Guard: 0/0 und {actual_text} bestätigt; "
                    f"{self._late_effect_guard_neutral_observation_count}/2 frische Beobachtungen, "
                    f"{stable_elapsed_s:.1f}/6.0 s stabil."
                )
                self.state.command_effect_confirmed = False
            self._update_late_effect_guard_state()
            return True

        self._reset_late_effect_neutral_confirmation()
        reason_parts = []
        if not readback_zero:
            reason_parts.append("0/0-Readback noch nicht frisch bestätigt")
        if not physical_neutral:
            reason_parts.append(f"physische Neutralität fehlt ({actual_text}, Richtung {direction})")
        reason_text = "; ".join(reason_parts) or "Neutralitätsnachweis ausstehend"
        with self.state.lock:
            self.state.command_lifecycle_state = "LATE_EFFECT_NEUTRALIZING"
            self.state.command_effect_category = "COMMAND_NEUTRALIZATION_PENDING"
            self.state.command_effect_reason = f"Late-Effect-Guard: {reason_text}."
            self.state.command_effect_confirmed = False
        self._update_late_effect_guard_state(reason=reason_text)

        timeout_s = max(5, int(cfg.get("COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS", 30) or 30))
        if duration_s >= timeout_s:
            self._mark_mismatch(
                target=0,
                actual_text=actual_text,
                elapsed_s=int(duration_s),
                tolerance_w=absolute_tolerance_w,
                neutral=True,
            )
            retry_s = max(5, int(cfg.get("COMMAND_RESYNC_COOLDOWN_SECONDS", 120) or 120))
            if now_epoch - self._neutralization_last_resend_epoch >= retry_s:
                if self._resync_permitted(0, "RESYNC_AFTER_LATE_EFFECT_GUARD_MISMATCH", cfg, confirmed_mismatch=True):
                    self._resend_late_effect_guard_neutralization(
                        f"RESYNC_AFTER_LATE_EFFECT_GUARD_MISMATCH_{int(duration_s)}s"
                    )
                    self._neutralization_last_resend_epoch = now_epoch
        return True

    def _update_command_readback_diagnostics(self, cfg: Dict[str, Any]) -> None:
        batch = self._desired_command_batch
        if batch is None or batch.intent == INTENT_IDLE:
            matches = False
            code = "NOT_EVALUABLE"
        else:
            snapshot = self._command_state_snapshot(cfg)
            if not snapshot.get("complete"):
                matches = False
                code = "NOT_EVALUABLE"
            else:
                mismatches = []
                if snapshot.get("smart_mode") != batch.smart_mode:
                    mismatches.append("SMART_MODE")
                if snapshot.get("ac_mode") != batch.ac_mode:
                    mismatches.append("AC_MODE")
                if int(snapshot.get("input_limit_w") or 0) != int(batch.input_limit_w):
                    mismatches.append("INPUT_LIMIT")
                if int(snapshot.get("output_limit_w") or 0) != int(batch.output_limit_w):
                    mismatches.append("OUTPUT_LIMIT")
                matches = not mismatches
                code = "NONE" if matches else mismatches[0] if len(mismatches) == 1 else "MULTIPLE"
        with self.state.lock:
            self.state.command_readback_matches_desired = bool(matches)
            self.state.command_readback_mismatch_fields = code

    def _confirmed_charge_reference(self, cfg: Dict[str, Any], target_w: int) -> Tuple[int, Dict[str, Any]]:
        """Return the fresh, statically confirmed charge reference for RC14.

        The volatile controller target and the device read-back may legitimately
        differ for a few seconds under cloud-driven regulation.  Acceptance
        classification therefore confirms only the static command invariants
        and uses the smaller positive value as the physically acknowledged
        reference.  No requested direction is used to reinterpret telemetry.
        """
        snapshot = self._command_state_snapshot(cfg)
        target = max(0, int(target_w or 0))
        readback = max(0, int(snapshot.get("input_limit_w") or 0))
        min_target_w = max(1, int(cfg.get("COMMAND_EFFECT_MIN_TARGET_W", 120) or 120))
        static_confirmed = bool(
            target > 0
            and snapshot.get("complete")
            and snapshot.get("smart_mode") == 1
            and snapshot.get("ac_mode") == "Input mode"
            and int(snapshot.get("output_limit_w") or 0) == 0
            and readback >= min_target_w
        )
        reference = min(target, readback) if static_confirmed else 0
        with self.state.lock:
            self.state.command_effect_reference_w = int(reference)
        return int(reference), snapshot

    def request_stop(self) -> None:
        self._running = False

    def close(self) -> None:
        try:
            self.csv_logger.close()
        except Exception:
            pass
        try:
            self.sma_energy_meter.stop()
        except Exception:
            pass

    def run_forever(self) -> None:
        self.log("[CTRL] Hauptschleife gestartet")
        while self._running:
            loop_start = time.time()
            loop_perf_start = time.perf_counter_ns()
            self._cycle_timing_parts = {}
            reload_started = time.perf_counter_ns()
            cfg, changed = self.config_manager.reload_if_needed()
            self._cycle_timing_parts["config_reload_ms"] = (time.perf_counter_ns() - reload_started) / 1_000_000.0
            if changed:
                self.log("[CONFIG] Änderung geladen")
                self._timed_phase("mqtt_refresh_subscriptions_ms", self.mqtt.refresh_subscriptions)

            run_once_started = time.perf_counter_ns()
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
            finally:
                self._cycle_timing_parts["run_once_ms"] = (time.perf_counter_ns() - run_once_started) / 1_000_000.0

            finish_started = time.perf_counter_ns()
            self.finish_cycle(cfg, loop_start)
            self._cycle_timing_parts["finish_cycle_ms"] = (time.perf_counter_ns() - finish_started) / 1_000_000.0
            total_ms = (time.perf_counter_ns() - loop_perf_start) / 1_000_000.0
            self._cycle_timing_parts["cycle_total_without_sleep_ms"] = total_ms
            leaf_keys = (
                "config_reload_ms", "mqtt_refresh_subscriptions_ms",
                "zendure_local_api_ms", "sma_energy_meter_ms",
                "grid_control_read_ms", "grid_display_read_ms",
                "cycle_display_metrics_ms", "cross_charge_metrics_ms",
                "control_decision_ms", "mqtt_command_path_ms",
                "command_effect_monitor_ms", "charge_acceptance_diag_ms",
                "graph_snapshot_ms", "measurement_logging_ms",
            )
            attributed_ms = sum(float(self._cycle_timing_parts.get(key, 0.0)) for key in leaf_keys)
            self._cycle_timing_parts["other_cycle_work_ms"] = max(0.0, total_ms - attributed_ms)
            # A residual is useful for completeness of the hierarchy, but it
            # is not a directly measured phase and must therefore never be
            # presented as the "slowest measured section".
            measured_parts = {
                key: float(self._cycle_timing_parts.get(key, 0.0))
                for key in leaf_keys
                if float(self._cycle_timing_parts.get(key, 0.0)) > 0.0
            }
            slowest = max(measured_parts.items(), key=lambda item: item[1]) if measured_parts else ("none", 0)
            self.state.set_cycle_timing(self._cycle_timing_parts, slowest[0], float(slowest[1]), total_ms)
            warn_ms = int(cfg.get("SLOW_CYCLE_WARN_MS", 5000))
            detail_ms = int(cfg.get("TIMING_DETAIL_LOG_MS", 2000))
            if total_ms >= warn_ms:
                self.log(f"[TIMING] slow_cycle total_ms={total_ms} slowest={slowest[0]}:{slowest[1]}ms details={self._cycle_timing_parts}")
            elif detail_ms > 0 and total_ms >= detail_ms:
                self.log(f"[TIMING] cycle_detail total_ms={total_ms} slowest={slowest[0]}:{slowest[1]}ms details={self._cycle_timing_parts}")
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
            self._reset_rest_surplus_harvest("MQTT_DISCONNECTED")
            self.state.add_limiter("MQTT_DISCONNECTED")
            self.safe_state("MQTT getrennt")
            return

        # SOC-/Zendure-Telemetrie darf vor fest vorgegebenen Betriebsarten aktualisiert
        # werden, weil diese Betriebsarten ohne Netzanschlusspunktmessung funktionieren.
        # Grid/Shelly-kompatible HTTP-/SMA-Daten werden für die Statusseite in festen Modi zusätzlich
        # best-effort aktualisiert, aber nicht als Pflichtquelle für diese Modi benutzt.
        self._timed_local_api_phase(cfg)
        self._timed_phase("sma_energy_meter_ms", self.update_sma_energy_meter_status, cfg)
        # Per-cycle housekeeping: display/CSV metrics that are derived from
        # asynchronous MQTT/API raw values must be refreshed before any early
        # return path (manual modes, night mode, safe-state). Cross-charge
        # control metrics remain AUTO/grid-dependent and are refreshed later
        # after a valid grid measurement.
        self._timed_phase("cycle_display_metrics_ms", self.update_cycle_display_metrics, cfg)

        night_active = self.is_night_discharge_active(cfg)
        if not night_active:
            night_exit_neutralized = self.neutralize_ended_night_discharge_if_needed()
            if not night_exit_neutralized:
                self.state.reset_night_discharge_stop_reason()

        manual_mode = str(cfg.get("MANUAL_MODE", "AUTO"))
        if manual_mode != "AUTO":
            self._reset_rest_surplus_harvest("MODE_CHANGED")
            self._timed_phase("grid_display_read_ms", self.refresh_grid_power_for_display, cfg)
            self._timed_control_phase(self.handle_manual_mode, cfg, manual_mode)
            return

        if night_active:
            self._reset_rest_surplus_harvest("MODE_CHANGED")
            if not self.soc_is_fresh(cfg):
                self._timed_phase("grid_display_read_ms", self.refresh_grid_power_for_display, cfg)
                self.state.add_limiter("SOC_STALE")
                self.safe_state("Nachtmodus blockiert: Zendure SOC fehlt oder ist veraltet")
                return
            if self.night_reserve_soc_reached(cfg):
                # Der Nachtmodus-Reserve-SOC pausiert nur die feste Nacht-Basisentladung.
                # Danach darf die normale AUTO-Regelung im selben Nachtfenster weiterlaufen,
                # damit Lastspitzen bis zum globalen MIN_SOC abgefangen werden können.
                if not self.pause_fixed_night_discharge_for_reserve_soc(cfg):
                    return
            else:
                self._timed_phase("grid_display_read_ms", self.refresh_grid_power_for_display, cfg)
                self._timed_control_phase(self.handle_night_mode, cfg)
                return

        if not self.soc_is_fresh(cfg):
            self.state.add_limiter("SOC_STALE")
            self.safe_state("Zendure SOC fehlt oder ist veraltet")
            return

        if not self._timed_phase("grid_control_read_ms", self.read_grid_power, cfg):
            return
        self._timed_phase("cycle_display_metrics_ms", self.update_cycle_display_metrics, cfg)
        self._timed_phase("cross_charge_metrics_ms", self.update_cross_charge_control_metrics, cfg)

        grid_power = self.state.grid_power
        self.update_rest_surplus_harvest_state(cfg, grid_power)

        if self.cross_charge_guard_corrects_existing_target(cfg):
            return

        if abs(grid_power) <= cfg["DEADBAND_W"]:
            # High-SOC/Parallel-Harvest darf im Deadband weiter allokieren:
            # Wenn der Primärspeicher stark lädt, aber am Netzanschlusspunkt schon
            # nahe 0 W erreicht ist, soll Zendure kontrolliert Ladeleistung
            # übernehmen dürfen, statt in HOLD bei einem alten Ziel zu verharren.
            if self._rest_surplus_is_active() and bool(cfg.get("HARVEST_HIGH_SMA_SOC_ENABLED", True)):
                self._timed_control_phase(self.handle_charge, cfg, grid_power)
                return
            self._timed_control_phase(self.handle_deadband, cfg)
            return

        if grid_power > 0:
            self._timed_control_phase(self.handle_discharge, cfg, grid_power)
            return

        self._timed_control_phase(self.handle_charge, cfg, grid_power)

    def update_sma_energy_meter_status(self, cfg: Dict[str, Any]) -> None:
        """Keep the passive SMA direct source listener and status snapshot current."""
        try:
            self.sma_energy_meter.ensure_started(cfg)
            snap = self.sma_energy_meter.snapshot()
            with self.state.lock:
                self.state.sma_energy_meter_enabled = snap.enabled
                self.state.sma_energy_meter_running = snap.running
                self.state.sma_energy_meter_power_w = snap.last_power_w
                self.state.sma_energy_meter_consumption_power_w = snap.last_consumption_power_w
                self.state.sma_energy_meter_feedin_power_w = snap.last_feedin_power_w
                self.state.sma_energy_meter_last_epoch = snap.last_received_epoch
                self.state.sma_energy_meter_susy_id = snap.last_susy_id
                self.state.sma_energy_meter_serial_number = snap.last_serial_number
                self.state.sma_energy_meter_packet_count = snap.packet_count
                self.state.sma_energy_meter_decode_count = snap.decode_count
                self.state.sma_energy_meter_ignored_count = snap.ignored_count
                self.state.sma_energy_meter_error_count = snap.error_count
                self.state.sma_energy_meter_last_error = snap.last_error
                self.state.sma_energy_meter_group = snap.configured_group
                self.state.sma_energy_meter_port = snap.configured_port
                self.state.sma_energy_meter_interface = snap.configured_interface
                self.state.sma_energy_meter_resolved_interface_ip = snap.resolved_interface_ip
                self.state.sma_energy_meter_configured_susy_id = snap.configured_susy_id
                self.state.sma_energy_meter_configured_serial = snap.configured_serial
                self.state.sma_energy_meter_selected_device_key = snap.selected_device_key
                self.state.sma_energy_meter_selected_device_matched = snap.selected_device_matched
                self.state.sma_energy_meter_detected_device_count = snap.detected_device_count
                self.state.sma_energy_meter_devices_json = snap.devices_json
                self.state.sma_energy_meter_socket_mode = snap.configured_socket_mode
                self.state.sma_energy_meter_effective_socket_mode = snap.effective_socket_mode
                self.state.sma_energy_meter_bind_address = snap.bind_address
                self.state.sma_energy_meter_bind_mode = snap.bind_mode
                self.state.sma_energy_meter_reuseaddr_enabled = snap.reuseaddr_enabled
                self.state.sma_energy_meter_reuseport_requested = snap.reuseport_requested
                self.state.sma_energy_meter_reuseport_supported = snap.reuseport_supported
                self.state.sma_energy_meter_reuseport_enabled = snap.reuseport_enabled
                self.state.sma_energy_meter_reuseport_error = snap.reuseport_error
                self.state.sma_energy_meter_multicast_if_set = snap.multicast_if_set
                self.state.sma_energy_meter_packet_rate_per_min = snap.packet_rate_per_min
                self.state.sma_energy_meter_packet_gap_warn_s = snap.packet_gap_warn_s
                self.state.sma_energy_meter_last_packet_gap_s = snap.last_packet_gap_s
                self.state.sma_energy_meter_max_packet_gap_s = snap.max_packet_gap_s
                self.state.sma_energy_meter_last_large_gap_s = snap.last_large_gap_s
                self.state.sma_energy_meter_last_large_gap_age_seconds = (
                    max(0, int(time.time() - snap.last_large_gap_epoch)) if snap.last_large_gap_epoch is not None else None
                )
            self._log_sma_diagnostics_if_needed(cfg, snap)
        except Exception as exc:
            with self.state.lock:
                self.state.sma_energy_meter_error_count += 1
                self.state.sma_energy_meter_last_error = str(exc)

    def _log_sma_diagnostics_if_needed(self, cfg: Dict[str, Any], snap) -> None:
        """Write compact SMA coexistence diagnostics to runtime log when enabled.

        Requires FILE_LOG_ENABLED=true to persist in zendure_runtime.log. DEBUG=true
        additionally mirrors the line to stdout via self.log().
        """
        if not snap.enabled:
            return
        if not cfg.get("SMA_ENERGY_METER_LOG_DIAGNOSTICS", False):
            return
        now = time.time()
        interval_s = max(10, int(cfg.get("SMA_ENERGY_METER_LOG_INTERVAL_SECONDS", 60) or 60))
        diag_key = (
            snap.enabled, snap.running, snap.configured_socket_mode, snap.effective_socket_mode,
            snap.bind_address, snap.bind_mode, snap.reuseport_enabled, snap.resolved_interface_ip,
            snap.configured_serial, snap.configured_susy_id,
        )
        gap_epoch = snap.last_large_gap_epoch
        should_log = False
        if diag_key != self._last_sma_diag_key:
            should_log = True
            self._last_sma_diag_key = diag_key
        if gap_epoch is not None and gap_epoch != self._last_sma_large_gap_epoch:
            should_log = True
            self._last_sma_large_gap_epoch = gap_epoch
        if now - float(self._last_sma_diag_log_epoch or 0.0) >= interval_s:
            should_log = True
        if not should_log:
            return
        self._last_sma_diag_log_epoch = now
        age = snap.age_s
        parts = [
            "[SMA_DIAG]",
            f"enabled={int(bool(snap.enabled))}",
            f"running={int(bool(snap.running))}",
            f"source={cfg.get('GRID_METER_SOURCE', '')}",
            f"socket_mode={snap.configured_socket_mode}",
            f"effective_socket_mode={snap.effective_socket_mode}",
            f"bind={snap.bind_address or '-'}:{snap.configured_port}",
            f"bind_mode={snap.bind_mode or '-'}",
            f"group={snap.configured_group}",
            f"iface={snap.configured_interface or '-'}",
            f"iface_ip={snap.resolved_interface_ip or '-'}",
            f"reuseaddr={int(bool(snap.reuseaddr_enabled))}",
            f"reuseport_requested={int(bool(snap.reuseport_requested))}",
            f"reuseport_supported={int(bool(snap.reuseport_supported))}",
            f"reuseport_enabled={int(bool(snap.reuseport_enabled))}",
            f"multicast_if={int(bool(snap.multicast_if_set))}",
            f"packets={snap.packet_count}",
            f"decoded={snap.decode_count}",
            f"ignored={snap.ignored_count}",
            f"errors={snap.error_count}",
            f"rate_per_min={snap.packet_rate_per_min}",
            f"age_s={age if age is not None else '-'}",
            f"last_gap_s={snap.last_packet_gap_s if snap.last_packet_gap_s is not None else '-'}",
            f"max_gap_s={snap.max_packet_gap_s if snap.max_packet_gap_s is not None else '-'}",
            f"large_gap_s={snap.last_large_gap_s if snap.last_large_gap_s is not None else '-'}",
            f"selected={snap.selected_device_key or '-'}",
            f"detected_devices={snap.detected_device_count}",
            f"last_error={str(snap.last_error).replace(' ', '_')}",
        ]
        if snap.reuseport_error:
            parts.append(f"reuseport_error={str(snap.reuseport_error).replace(' ', '_')}")
        self.log(" ".join(parts))

    def read_grid_power(self, cfg: Dict[str, Any], *, for_control: bool = True) -> bool:
        """Read the configured grid power source.

        Default remains the Shelly-compatible HTTP source.  RC2 adds an optional direct SMA
        Energy Meter / Sunny Home Manager UDP source.  The direct SMA listener
        is cached/asynchronous, so this read never waits for a fresh UDP packet.

        for_control=True keeps the historical AUTO safety behavior: stale grid
        data may move AUTO into Safe-State. for_control=False is a best-effort
        telemetry refresh for UI/CSV/status in modes that deliberately do not
        require grid data, e.g. fixed night discharge or STOP/HOLD. A display
        refresh must never stop those modes.
        """
        source = str(cfg.get("GRID_METER_SOURCE", "shelly_http") or "shelly_http")
        if source == "sma_energy_meter_udp":
            source_label = "SMA Home Manager direkt"
            source_display = "SMA Home Manager direkt (UDP)"
        else:
            source_label = "Shelly-kompatible HTTP-Quelle"
            source_display = "Shelly-kompatible HTTP-Quelle"
        stale_timeout_key = "SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS" if source == "sma_energy_meter_udp" else "SHELLY_STALE_TIMEOUT_SECONDS"
        limiter_code = "SMA_GRID_STALE" if source == "sma_energy_meter_udp" else "SHELLY_STALE"
        try:
            if source == "sma_energy_meter_udp":
                raw = self.sma_energy_meter.read_grid_power(cfg)
            else:
                raw = self.shelly.read_grid_power(cfg)
            plausibility_limit = float(cfg.get("GRID_POWER_PLAUSIBILITY_MAX_ABS_W", 30000) or 30000)
            if plausibility_limit > 0 and abs(float(raw)) > plausibility_limit:
                raise RuntimeError(
                    f"Netzleistungswert unplausibel: {float(raw):.1f} W überschreitet absolute Grenze {plausibility_limit:.0f} W"
                )
            smoothed = self.state.update_power_history(raw, int(cfg["MOVING_AVERAGE_SAMPLES"]))
            now = time.time()
            now_text = datetime.now().strftime("%H:%M:%S")
            with self.state.lock:
                self.state.raw_grid_power = raw
                self.state.grid_power = smoothed
                self.state.current_rule_deviation = round(smoothed, 1)
                self.state.last_shelly_update_epoch = now
                self.state.last_shelly_update_time = now_text
                self.state.grid_meter_source = source
                self.state.raw_grid_source = source_display
                self.state.grid_power_valid = True
                self.state.grid_power_used_for_control = bool(for_control)
                self.state.grid_power_age_seconds = 0
                self.state.grid_power_validity_reason = "OK"
            if cfg.get("LOG_VALUES", False):
                suffix = "Regelung" if for_control else "Anzeige"
                self.log(f"[GRID/{suffix}/{source_label}] Rohwert: {raw:.1f} W | Mittelwert: {smoothed:.1f} W")
            return True
        except Exception as exc:
            self.state.set_error(f"{source_label} Fehler: {exc}")
            with self.state.lock:
                self.state.grid_meter_source = source
                self.state.raw_grid_source = source_display
                self.state.grid_power_used_for_control = False
                if self.state.last_shelly_update_epoch is not None:
                    self.state.grid_power_age_seconds = max(0, int(time.time() - self.state.last_shelly_update_epoch))
                exc_text = str(exc)
                if "unplausibel" in exc_text.lower():
                    self.state.grid_rejected_count_since_start += 1
                    self.state.grid_last_rejected_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.state.grid_last_rejected_reason = "unplausibler Messwert"
                    try:
                        self.state.grid_last_rejected_value_w = float(raw)
                    except Exception:
                        self.state.grid_last_rejected_value_w = None
                self.state.grid_power_validity_reason = exc_text if "unplausibel" in exc_text.lower() else f"{source_label} nicht aktuell"
            with self.state.lock:
                last_update = self.state.last_shelly_update_epoch
            if not for_control:
                return False
            if cfg.get("SAFE_STATE_ON_SHELLY_ERROR", True):
                if last_update is None or time.time() - last_update > cfg.get(stale_timeout_key, 15):
                    self.state.add_limiter(limiter_code)
                    self.safe_state(f"{source_label} Netzleistungsdaten nicht aktuell")
                    return False
            raise

    def refresh_grid_power_for_display(self, cfg: Dict[str, Any]) -> bool:
        """Best-effort grid telemetry refresh for status/CSV.

        This is intentionally separate from the AUTO control read. It keeps the
        status page alive in fixed night discharge and STOP/HOLD, but a failed
        read must not make those modes depend on grid data.
        """
        return self.read_grid_power(cfg, for_control=False)


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
        grid_off = self._safe_int(props.get("gridOffPower"))
        solar_input = self._safe_int(props.get("solarInputPower"))

        # Command/configuration read-back is orthogonal to the telemetry fallback
        # decision.  The local API is read-only and provides a second source for
        # flash protection, current AC mode, limits and device-side safety caps.
        for property_name in (
            "smartMode", "acMode", "inputLimit", "outputLimit",
            "inverseMaxPower", "chargeMaxLimit", "gridOffMode",
        ):
            if property_name in props:
                self.state.update_zendure_command_property(property_name, props.get(property_name), "Lokale API", now)

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
        use_api_as_active_power = bool((
            pack_input is not None or output_home is not None or grid_input is not None
            or output_pack is not None or grid_off is not None or solar_input is not None
        ) and (not fallback_only or not self.zendure_power_is_fresh(cfg)))

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
                    grid_off=grid_off,
                    solar_input=solar_input,
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
        Shelly-compatible HTTP grid data.
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
            # RC6: effective export is the real export candidate. Symmetric
            # Cross-Charge reduction is applied later to the signed Zendure target
            # in both directions. Do not pre-subtract one direction here, otherwise
            # the target would be reduced twice.
            effective = max(0, int(export_power))

        with self.state.lock:
            self.state.effective_export_power = effective
            self.state.effective_export_power_valid = True
            self.state.effective_export_power_used_for_control = True
            self.state.second_battery_data_used_for_control = True

    def update_sma_metrics(self, cfg: Dict[str, Any]) -> None:
        """Backward-compatible wrapper for AUTO/Cross-Charge updates."""
        self.update_second_battery_display_metrics(cfg)
        self._timed_phase("cross_charge_metrics_ms", self.update_cross_charge_control_metrics, cfg)

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
        # Backward-compatible method name kept for older tests; RC6 uses the
        # symmetric implementation for both battery-flow directions.
        return self.cross_charge_guard_corrects_existing_target(cfg)


    def _cross_charge_thresholds(self, cfg: Dict[str, Any]) -> tuple:
        try:
            engage = int(float(cfg.get("CROSS_CHARGE_SIGNIFICANT_W", cfg.get("SMA_DISCHARGE_BLOCK_W", 80))))
        except Exception:
            engage = 80
        engage = max(0, engage)
        release = max(20, int(engage / 2)) if engage > 0 else 0
        return engage, release

    def _apply_symmetric_cross_charge_limit(self, cfg: Dict[str, Any], target_signed_w: int) -> Dict[str, Any]:
        """Return a corrected signed Zendure target for AUTO/HOLD Cross-Charge protection.

        Sign convention: target >0 charges Zendure, target <0 discharges Zendure.
        second_battery_display_power >0 means the second battery charges, <0 discharges.
        The protection reduces a conflicting Zendure target proportionally, but never
        reverses direction by itself.
        """
        original = int(target_signed_w or 0)
        result = {
            "target": original,
            "active": False,
            "limited": False,
            "blocked": False,
            "reason": "",
            "direction": "",
        }

        if not cross_charge_enabled(cfg) or original == 0:
            with self.state.lock:
                self.state.cross_charge_guard_latched = False
                self.state.cross_charge_last_direction = ""
            return result

        with self.state.lock:
            second_power = float(self.state.sma_battery_display_power or 0.0)
            valid = bool(self.state.second_battery_data_valid and self.state.second_battery_data_fresh)
            was_latched = bool(self.state.cross_charge_guard_latched)

        if not valid or second_power == 0 or (second_power * original) >= 0:
            with self.state.lock:
                self.state.cross_charge_guard_latched = False
                self.state.cross_charge_last_direction = ""
            return result

        engage, release = self._cross_charge_thresholds(cfg)
        magnitude = abs(second_power)
        active = magnitude >= engage or (was_latched and magnitude >= release)
        if not active:
            with self.state.lock:
                self.state.cross_charge_guard_latched = False
                self.state.cross_charge_last_direction = ""
            return result

        corrected = original + int(round(second_power))
        if original > 0:
            corrected = max(0, min(original, corrected))
            direction = "SECOND_BATTERY_DISCHARGES_ZENDURE_CHARGES"
            phrase = "Zusatzbatterie entlädt, Zendure-Ladung wird reduziert"
        else:
            corrected = min(0, max(original, corrected))
            direction = "SECOND_BATTERY_CHARGES_ZENDURE_DISCHARGES"
            phrase = "Zusatzbatterie lädt, Zendure-Entladung wird reduziert"

        blocked = corrected == 0
        if blocked:
            phrase = phrase.replace("wird reduziert", "wurde auf 0 W neutralisiert")

        with self.state.lock:
            self.state.cross_charge_guard_latched = True
            self.state.cross_charge_last_direction = direction
        self.state.add_limiter("CROSS_CHARGE")
        result.update({
            "target": int(corrected),
            "active": True,
            "limited": int(corrected) != original,
            "blocked": bool(blocked),
            "reason": "Cross-Charge-Schutz: " + phrase,
            "direction": direction,
        })
        return result

    def _zendure_mqtt_uncertain_for_active_command(self, status: str, live_confirmed: bool) -> bool:
        status = str(status or "").upper()
        return (not live_confirmed) or status in {
            "ZENDURE_MQTT_AFTER_BROKER_RESTART_NO_LIVE_UPDATES",
            "ZENDURE_MQTT_RETAINED_ONLY",
            "ZENDURE_MQTT_STALE",
            "ZENDURE_MQTT_PARTIAL_STALE",
            "ZENDURE_MQTT_NO_LIVE",
            "ZENDURE_MQTT_UNKNOWN",
        }

    def _mark_active_command_mqtt_uncertain(self, signed_target_w: int, status: str, live_confirmed: bool) -> None:
        if int(signed_target_w or 0) == 0:
            return
        if not self._zendure_mqtt_uncertain_for_active_command(status, live_confirmed):
            return
        now = time.time()
        with self.state.lock:
            self.state.command_uncertain_mqtt_active = True
            if self.state.command_uncertain_mqtt_since_epoch is None:
                self.state.command_uncertain_mqtt_since_epoch = now
                self.state.command_uncertain_mqtt_since_time = datetime.now().strftime("%H:%M:%S")
            self.state.command_uncertain_mqtt_status = str(status or "UNKNOWN")
            self.state.command_uncertain_mqtt_target_w = int(signed_target_w or 0)
            self.state.command_uncertain_mqtt_reason = (
                f"Aktiver Sollwert {int(signed_target_w)} W wurde bei unsicherem Zendure-MQTT-Zustand "
                f"({status or 'UNKNOWN'}) gesendet/angefordert. Falls keine Gerätewirkung sichtbar ist: "
                "MQTT in der Zendure-App erneut speichern/aktivieren; ZEC sendet bei Recovery automatisch erneut."
            )

    def _smart_mode_contract_supported(self) -> bool:
        return callable(getattr(self.mqtt, "set_smart_mode", None))

    def _command_state_snapshot(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        max_age_s = max(5, int(cfg.get("ZENDURE_COMMAND_STATE_FRESH_SECONDS", 30) or 30))
        snapshotter = getattr(self.state, "zendure_command_state_snapshot", None)
        if callable(snapshotter):
            return snapshotter(max_age_s=max_age_s)
        return {
            "smart_mode": None,
            "ac_mode": "",
            "input_limit_w": None,
            "output_limit_w": None,
            "inverse_max_power_w": None,
            "charge_max_limit_w": None,
            "flash_protection_active": False,
            "complete": False,
            "reason": "Command-State-Readback nicht verfügbar.",
        }

    def _clamp_signed_target_to_device_limits(self, signed_target_w: int, cfg: Dict[str, Any]) -> int:
        """Apply config and read-only Zendure device caps without writing them."""
        target = int(signed_target_w or 0)
        snapshot = self._command_state_snapshot(cfg)
        if target > 0:
            limits = [max(0, int(cfg.get("MAX_CHARGE_POWER_W", target) or 0))]
            device_limit = snapshot.get("charge_max_limit_w")
            if device_limit is not None and int(device_limit) > 0:
                limits.append(int(device_limit))
            clamped = min([target] + limits)
            if clamped != target:
                self.state.add_limiter("ZENDURE_DEVICE_CHARGE_LIMIT")
            return max(0, int(clamped))
        if target < 0:
            magnitude = abs(target)
            limits = [max(0, int(cfg.get("MAX_DISCHARGE_POWER_W", magnitude) or 0))]
            device_limit = snapshot.get("inverse_max_power_w")
            if device_limit is not None and int(device_limit) > 0:
                limits.append(int(device_limit))
            clamped = min([magnitude] + limits)
            if clamped != magnitude:
                self.state.add_limiter("ZENDURE_DEVICE_DISCHARGE_LIMIT")
            return -max(0, int(clamped))
        return 0

    @staticmethod
    def _command_state_matches_batch(snapshot: Dict[str, Any], batch: DesiredCommandBatch) -> bool:
        return bool(
            snapshot.get("complete")
            and snapshot.get("smart_mode") == 1
            and snapshot.get("ac_mode") == batch.ac_mode
            and int(snapshot.get("input_limit_w") or 0) == int(batch.input_limit_w)
            and int(snapshot.get("output_limit_w") or 0) == int(batch.output_limit_w)
        )

    @staticmethod
    def _command_static_invariants_match(snapshot: Dict[str, Any], batch: DesiredCommandBatch) -> bool:
        if not snapshot.get("complete") or snapshot.get("smart_mode") != 1:
            return False
        if snapshot.get("ac_mode") != batch.ac_mode:
            return False
        if batch.intent == INTENT_CHARGE:
            return int(snapshot.get("output_limit_w") or 0) == 0
        if batch.intent == INTENT_DISCHARGE:
            return int(snapshot.get("input_limit_w") or 0) == 0
        if batch.intent == INTENT_NEUTRALIZE:
            return int(snapshot.get("input_limit_w") or 0) == 0 and int(snapshot.get("output_limit_w") or 0) == 0
        return False

    def _mark_command_state_waiting(self, batch: DesiredCommandBatch, event: str, fields: Tuple[str, ...]) -> None:
        with self.state.lock:
            self.state.command_lifecycle_state = "COMMAND_STATE_VERIFYING"
            self.state.command_effect_category = "COMMAND_STATE_VERIFYING"
            self.state.command_effect_reason = (
                "Zendure-Command-State wird rückgelesen; dynamische Limitänderung wartet auf "
                "bestätigtes smartMode=1 und konsistente Modus-/Gegenlimitwerte."
            )
            self.state.command_effect_confirmed = False
            self.state.command_publish_event = event
            self.state.command_publish_fields = ",".join(fields)
            if fields:
                self.state.command_publish_last_time = datetime.now().strftime("%H:%M:%S")

    def _record_desired_command_batch(
        self,
        batch: DesiredCommandBatch,
        published_fields: Tuple[str, ...],
        *,
        forced: bool,
        publish_event: Optional[str] = None,
    ) -> None:
        self._ensure_command_lifecycle_attrs()
        previous = self._desired_command_batch
        intent_changed = previous is None or previous.intent != batch.intent
        physical_state_changed = bool(
            previous is None
            or previous.intent != batch.intent
            or previous.smart_mode != batch.smart_mode
            or previous.ac_mode != batch.ac_mode
            or previous.input_limit_w != batch.input_limit_w
            or previous.output_limit_w != batch.output_limit_w
            or previous.signed_target_w != batch.signed_target_w
        )
        mismatch_resolution_event = ""

        # A new safety intent supersedes an old mismatch; it is not proof that
        # the old active command recovered.
        with self.state.lock:
            if previous is not None and previous.intent != batch.intent and self.state.command_not_effective_active:
                if self._late_effect_guard_active and batch.intent == INTENT_NEUTRALIZE:
                    resolution = "MISMATCH_HANDOFF_TO_LATE_EFFECT_GUARD"
                    mismatch_resolution_event = "Vorheriger Kommando-Mismatch an Late-Effect-Guard übergeben"
                elif batch.intent == INTENT_NEUTRALIZE and batch.safety_relevant:
                    resolution = "MISMATCH_SUPERSEDED_BY_SAFETY_NEUTRALIZATION"
                    mismatch_resolution_event = "Vorheriger Kommando-Mismatch durch sicherheitsrelevante Neutralisierung beendet"
                else:
                    resolution = "MISMATCH_ABORTED_BY_INTENT_CHANGE"
                    mismatch_resolution_event = "Vorheriger Kommando-Mismatch durch legitimen Intentwechsel beendet"
                self._clear_command_not_effective_locked()
                self.state.command_mismatch_resolution = resolution

        self._desired_command_batch = batch
        if batch.intent in {INTENT_CHARGE, INTENT_DISCHARGE}:
            self._last_non_neutral_ac_mode = batch.ac_mode
            if intent_changed:
                self._command_effect_last_resend_epoch = 0.0

        now_epoch = time.time()
        now_text = datetime.fromtimestamp(now_epoch).strftime("%H:%M:%S")
        neutral_signature = f"{batch.ac_mode}|0|0" if batch.intent == INTENT_NEUTRALIZE else ""
        previous_neutral_signature = (
            f"{previous.ac_mode}|0|0"
            if previous is not None and previous.intent == INTENT_NEUTRALIZE
            else ""
        )
        new_neutral_episode = bool(
            batch.intent == INTENT_NEUTRALIZE
            and batch.safety_relevant
            and neutral_signature != previous_neutral_signature
        )

        with self.state.lock:
            self.state.command_desired_sequence_id = batch.sequence_id
            self.state.command_desired_intent = batch.intent
            self.state.command_desired_smart_mode = batch.smart_mode
            self.state.command_desired_ac_mode = batch.ac_mode
            self.state.command_desired_input_limit_w = batch.input_limit_w
            self.state.command_desired_output_limit_w = batch.output_limit_w
            self.state.command_desired_signed_target_w = batch.signed_target_w
            self.state.command_desired_reason = batch.reason
            self.state.command_desired_safety_relevant = batch.safety_relevant
            self.state.command_publish_event = publish_event or (
                "FULL_STATE_RESYNC_SENT" if forced and published_fields
                else "COMMAND_BATCH_PUBLISHED" if published_fields
                else "COMMAND_BATCH_DEDUPED"
            )
            self.state.command_publish_fields = ",".join(published_fields)
            if published_fields:
                self.state.command_publish_last_time = now_text
                self.state.command_publish_event_id += 1
                self.state.command_publish_epoch_s = now_epoch
            if physical_state_changed or (forced and published_fields):
                self.state.command_effect_confirmed = False

            if batch.intent == INTENT_NEUTRALIZE and batch.safety_relevant:
                # Reasons may change while the physical zero state stays exactly
                # the same. Keep one physical episode and its confirmation.
                confirmed_same_episode = bool(
                    neutral_signature == self._neutralization_confirmed_signature
                    and self.state.command_effect_category == "COMMAND_NEUTRALIZATION_CONFIRMED"
                    and self.state.command_effect_confirmed
                )
                self.state.command_neutralization_reason = batch.reason
                self._neutralization_physical_signature = neutral_signature
                if new_neutral_episode:
                    self.state.command_neutralization_episode_id += 1
                    self._neutralization_confirmed_signature = ""
                    self._neutralization_last_resend_epoch = 0.0
                    self.state.command_neutralization_active = True
                    self.state.command_neutralization_since_epoch = batch.created_epoch
                    self.state.command_neutralization_since_time = now_text
                    self.state.command_lifecycle_state = "NEUTRALIZATION_OBSERVING"
                    self.state.command_effect_category = "COMMAND_NEUTRALIZATION_PENDING"
                    self.state.command_effect_reason = f"Neutralisierung wird auf netzseitige physische Wirkung geprüft: {batch.reason}."
                elif not confirmed_same_episode:
                    self.state.command_neutralization_active = True
                    if self.state.command_neutralization_since_epoch is None:
                        self.state.command_neutralization_since_epoch = batch.created_epoch
                        self.state.command_neutralization_since_time = now_text
                # A confirmed same physical episode remains confirmed and is not
                # reopened merely because MIN_SOC becomes SAFE_STATE, etc.
            elif batch.intent in {INTENT_CHARGE, INTENT_DISCHARGE}:
                self._neutralization_physical_signature = ""
                self._neutralization_confirmed_signature = ""
                self.state.command_neutralization_active = False
                self.state.command_neutralization_since_epoch = None
                self.state.command_neutralization_since_time = "-"
                self.state.command_neutralization_reason = ""

        if mismatch_resolution_event:
            self.state.add_event(mismatch_resolution_event)

    def _set_command_state_gate(self, gate_state: str, *, retry_s: int = 0, now: Optional[float] = None) -> None:
        epoch = time.time() if now is None else float(now)
        remaining = 0.0
        if retry_s > 0 and self._command_state_verification_epoch > 0:
            remaining = max(0.0, float(retry_s) - (epoch - self._command_state_verification_epoch))
        with self.state.lock:
            self.state.command_state_gate_state = str(gate_state)
            self.state.command_state_retry_remaining_s = round(remaining, 1)

    def _gate_retry_allowed(self, phase: str, intent: str, *, retry_s: int, now: float) -> bool:
        # Exact watt changes are deliberately excluded. A cloud-driven sequence
        # +1800 -> +2100 -> +1950 W remains one CHARGE gate episode.
        signature = f"{phase}|{intent}"
        allowed = bool(
            self._command_state_verification_signature != signature
            or (now - self._command_state_verification_epoch) >= retry_s
        )
        if allowed:
            self._command_state_verification_signature = signature
            self._command_state_verification_epoch = now
        return allowed

    def _publish_command_batch(
        self,
        batch: DesiredCommandBatch,
        *,
        force: bool = False,
        publish_kind: str = "normal",
    ) -> Tuple[str, ...]:
        """Publish the minimum safe Zendure command set (RC13 contract).

        Non-neutral dynamic control is impossible until smartMode=1 is freshly
        read back. A single, intent-based gate enforces the retry interval even
        when the exact watt target changes every controller cycle. Safety zero
        commands remain possible, but at most once per retry window until their
        read-back/effect is confirmed.
        """
        cfg = self.config_manager.get() if self.config_manager is not None else {}
        published = []
        smart_supported = self._smart_mode_contract_supported()

        # Compatibility path for historical test doubles only.
        if not smart_supported:
            if batch.intent == INTENT_CHARGE:
                if self._mqtt_set_ac_mode(batch.ac_mode, force=force): published.append("ac_mode")
                if self._mqtt_set_output_limit(0, force=force): published.append("output_limit")
                if self._mqtt_set_input_limit(batch.input_limit_w, force=force): published.append("input_limit")
            elif batch.intent == INTENT_DISCHARGE:
                if self._mqtt_set_ac_mode(batch.ac_mode, force=force): published.append("ac_mode")
                if self._mqtt_set_input_limit(0, force=force): published.append("input_limit")
                if self._mqtt_set_output_limit(batch.output_limit_w, force=force): published.append("output_limit")
            elif batch.intent == INTENT_NEUTRALIZE:
                if publish_kind not in {"late_effect_guard", "late_effect_guard_resync"} and self._mqtt_set_ac_mode(batch.ac_mode, force=force):
                    published.append("ac_mode")
                if self._mqtt_set_input_limit(0, force=force): published.append("input_limit")
                if self._mqtt_set_output_limit(0, force=force): published.append("output_limit")
            event = (
                "FULL_STATE_RESYNC_SENT" if publish_kind == "resync" and published
                else "LATE_EFFECT_GUARD_NEUTRALIZATION_RESYNC_SENT" if publish_kind == "late_effect_guard_resync" and published
                else "LATE_EFFECT_GUARD_NEUTRALIZATION_SENT" if publish_kind == "late_effect_guard" and published
                else "FULL_STATE_NEUTRALIZATION_SENT" if publish_kind == "neutralization" and published
                else None
            )
            self._record_desired_command_batch(batch, tuple(published), forced=force, publish_event=event)
            return tuple(published)

        snapshot = self._command_state_snapshot(cfg)
        previous = self._desired_command_batch
        intent_changed = previous is None or previous.intent != batch.intent
        now = time.time()
        retry_s = max(5, int(cfg.get("ZENDURE_COMMAND_STATE_RETRY_SECONDS", 30) or 30))
        smart_retry_s = max(5, int(cfg.get("ZENDURE_SMART_MODE_RETRY_SECONDS", retry_s) or retry_s))
        flash_active = bool(snapshot.get("flash_protection_active") and snapshot.get("smart_mode") == 1)
        complete = bool(snapshot.get("complete"))
        state_matches = self._command_state_matches_batch(snapshot, batch)
        static_matches = self._command_static_invariants_match(snapshot, batch)

        def publish_full_state(*, include_smart: bool, event: str, include_ac_mode: bool = True) -> Tuple[str, ...]:
            if include_smart and self._mqtt_set_smart_mode(True, force=True):
                published.append("smart_mode")
            if include_ac_mode and self._mqtt_set_ac_mode(batch.ac_mode, force=True):
                published.append("ac_mode")
            if batch.intent == INTENT_CHARGE:
                if self._mqtt_set_output_limit(0, force=True): published.append("output_limit")
                if self._mqtt_set_input_limit(batch.input_limit_w, force=True): published.append("input_limit")
            elif batch.intent == INTENT_DISCHARGE:
                if self._mqtt_set_input_limit(0, force=True): published.append("input_limit")
                if self._mqtt_set_output_limit(batch.output_limit_w, force=True): published.append("output_limit")
            else:
                if self._mqtt_set_input_limit(0, force=True): published.append("input_limit")
                if self._mqtt_set_output_limit(0, force=True): published.append("output_limit")
            self._record_desired_command_batch(batch, tuple(published), forced=force, publish_event=event)
            return tuple(published)

        # Safety neutralisation is the only write path allowed before fresh flash
        # protection. It is strictly rate-limited and never changes off-grid mode.
        if batch.intent == INTENT_NEUTRALIZE:
            # A confirmed physical mismatch must remain recovery-capable even
            # when the command read-back already says 0/0. In that case the
            # resync deliberately republishes the full neutral state.
            if state_matches and publish_kind not in {"resync", "late_effect_guard", "late_effect_guard_resync"}:
                self._set_command_state_gate(COMMAND_GATE_READY, now=now)
                self._command_state_verification_signature = ""
                self._command_state_verification_epoch = 0.0
                self._record_desired_command_batch(
                    batch, tuple(), forced=False,
                    publish_event="NEUTRALIZATION_REASON_UPDATED" if previous and previous.intent == INTENT_NEUTRALIZE and previous.reason != batch.reason else "COMMAND_BATCH_DEDUPED",
                )
                return tuple()

            phase = COMMAND_GATE_SAFETY_NEUTRALIZATION
            can_retry = self._gate_retry_allowed(phase, INTENT_NEUTRALIZE, retry_s=retry_s, now=now)
            self._set_command_state_gate(phase, retry_s=retry_s, now=now)
            if not can_retry:
                self._record_desired_command_batch(batch, tuple(), forced=False, publish_event="COMMAND_STATE_WAITING")
                return tuple()

            event = (
                "FULL_STATE_RESYNC_SENT" if publish_kind == "resync"
                else "LATE_EFFECT_GUARD_NEUTRALIZATION_RESYNC_SENT" if publish_kind == "late_effect_guard_resync"
                else "LATE_EFFECT_GUARD_NEUTRALIZATION_SENT" if publish_kind == "late_effect_guard"
                else "FULL_STATE_NEUTRALIZATION_SENT"
            )
            result = publish_full_state(
                include_smart=not flash_active,
                include_ac_mode=publish_kind not in {"late_effect_guard", "late_effect_guard_resync"},
                event=event,
            )
            self._set_command_state_gate(phase, retry_s=retry_s, now=now)
            return result

        if batch.intent not in {INTENT_CHARGE, INTENT_DISCHARGE}:
            self._set_command_state_gate(COMMAND_GATE_UNPROTECTED, now=now)
            self._record_desired_command_batch(batch, tuple(), forced=False, publish_event="COMMAND_BATCH_DEDUPED")
            return tuple()

        # Hard gate: stale smartMode=1 is not sufficient. Only a fresh read-back
        # may unlock active limits, including force/resync paths.
        if not flash_active:
            phase = COMMAND_GATE_WAIT_SMART_MODE
            can_retry = self._gate_retry_allowed(phase, batch.intent, retry_s=smart_retry_s, now=now)
            if can_retry and self._mqtt_set_smart_mode(True, force=True):
                published.append("smart_mode")
            self._set_command_state_gate(phase, retry_s=smart_retry_s, now=now)
            event = "SMART_MODE_ENABLE_SENT" if published else "COMMAND_STATE_WAITING"
            self._record_desired_command_batch(batch, tuple(published), forced=False, publish_event=event)
            self._mark_command_state_waiting(batch, event, tuple(published))
            return tuple(published)

        # Once smartMode is protected, one full state is allowed per real retry
        # window until all four properties are freshly consistent.
        need_full_state = bool(force or publish_kind == "resync" or intent_changed or not complete or not static_matches)
        if need_full_state:
            phase = COMMAND_GATE_WAIT_FULL_STATE
            can_retry = self._gate_retry_allowed(phase, batch.intent, retry_s=retry_s, now=now)
            if not can_retry:
                self._set_command_state_gate(phase, retry_s=retry_s, now=now)
                self._record_desired_command_batch(batch, tuple(), forced=False, publish_event="COMMAND_STATE_WAITING")
                self._mark_command_state_waiting(batch, "COMMAND_STATE_WAITING", tuple())
                return tuple()
            event = "FULL_STATE_RESYNC_SENT" if publish_kind == "resync" else "FULL_STATE_COMMAND_SENT"
            result = publish_full_state(include_smart=False, event=event)
            self._set_command_state_gate(phase, retry_s=retry_s, now=now)
            return result

        # READY: same direction and confirmed static invariants. Only the active
        # volatile limit may change at high frequency.
        self._command_state_verification_signature = ""
        self._command_state_verification_epoch = 0.0
        self._set_command_state_gate(COMMAND_GATE_READY, now=now)
        if state_matches:
            self._record_desired_command_batch(batch, tuple(), forced=False, publish_event="COMMAND_BATCH_DEDUPED")
            return tuple()
        if batch.intent == INTENT_CHARGE:
            if self._mqtt_set_input_limit(batch.input_limit_w, force=False):
                published.append("input_limit")
        else:
            if self._mqtt_set_output_limit(batch.output_limit_w, force=False):
                published.append("output_limit")
        event = "COMMAND_LIMIT_UPDATED" if published else "COMMAND_BATCH_DEDUPED"
        self._record_desired_command_batch(batch, tuple(published), forced=False, publish_event=event)
        return tuple(published)

    def _new_command_batch(
        self,
        signed_target_w: int,
        *,
        reason: str,
        explicit_neutralize: bool = False,
        ac_mode: Optional[str] = None,
        safety_relevant: bool = False,
    ) -> DesiredCommandBatch:
        signed_target_w = int(signed_target_w or 0)
        if signed_target_w != 0:
            signed_target_w = self._clamp_signed_target_to_device_limits(
                signed_target_w,
                self.config_manager.get() if self.config_manager is not None else {},
            )
        intent = intent_for_signed_target(signed_target_w, explicit_neutralize=explicit_neutralize)
        if intent == INTENT_CHARGE:
            resolved_mode = "Input mode"
            input_limit = signed_target_w
            output_limit = 0
        elif intent == INTENT_DISCHARGE:
            resolved_mode = "Output mode"
            input_limit = 0
            output_limit = abs(signed_target_w)
        else:
            resolved_mode = ac_mode or self._last_non_neutral_ac_mode or "Output mode"
            input_limit = 0
            output_limit = 0
        resolved_reason = str(reason or "COMMAND_TARGET")
        previous = self._desired_command_batch
        same_desired_state = bool(
            previous is not None
            and previous.intent == intent
            and previous.smart_mode == 1
            and previous.ac_mode == resolved_mode
            and previous.input_limit_w == int(input_limit)
            and previous.output_limit_w == int(output_limit)
            and previous.signed_target_w == signed_target_w
            and previous.reason == resolved_reason
            and previous.safety_relevant == bool(safety_relevant)
        )
        if same_desired_state:
            sequence_id = previous.sequence_id
        else:
            self._command_sequence_id += 1
            sequence_id = self._command_sequence_id
        return DesiredCommandBatch(
            sequence_id=sequence_id,
            intent=intent,
            smart_mode=1,
            ac_mode=resolved_mode,
            input_limit_w=int(input_limit),
            output_limit_w=int(output_limit),
            signed_target_w=signed_target_w,
            reason=resolved_reason,
            safety_relevant=bool(safety_relevant),
            created_epoch=time.time(),
        )

    def _publish_signed_target(
        self,
        signed_target_w: int,
        *,
        force_zero: bool = False,
        force: bool = False,
        reason: str = "",
    ) -> int:
        signed_target_w = int(signed_target_w or 0)
        if signed_target_w != 0:
            signed_target_w = self._clamp_signed_target_to_device_limits(
                signed_target_w,
                self.config_manager.get() if self.config_manager is not None else {},
            )
        requested_intent = intent_for_signed_target(
            signed_target_w,
            explicit_neutralize=(signed_target_w == 0),
        )
        resolved_reason = reason or ("ACTIVE_SIGNED_TARGET" if signed_target_w else "NEUTRAL_TARGET")
        if self._late_effect_guard_blocks(requested_intent, signed_target_w, resolved_reason):
            return 0
        with self.state.lock:
            mqtt_status = self.state.zendure_mqtt_overall_status
            live_confirmed = bool(self.state.zendure_mqtt_live_confirmed)
        self._mark_active_command_mqtt_uncertain(signed_target_w, mqtt_status, live_confirmed)
        explicit_neutralize = signed_target_w == 0 and (force_zero or force)
        previous = self._desired_command_batch
        same_neutral_episode = bool(
            explicit_neutralize
            and previous is not None
            and previous.intent == INTENT_NEUTRALIZE
            and previous.input_limit_w == 0
            and previous.output_limit_w == 0
        )
        batch = self._new_command_batch(
            signed_target_w,
            reason=resolved_reason,
            explicit_neutralize=explicit_neutralize,
            safety_relevant=explicit_neutralize,
        )
        if batch.intent != INTENT_IDLE:
            publish_kind = "neutralization" if batch.intent == INTENT_NEUTRALIZE else "normal"
            self._publish_command_batch(
                batch,
                force=(force or (force_zero and not same_neutral_episode)),
                publish_kind=publish_kind,
            )
        return int(batch.signed_target_w)

    def _publish_neutralization(
        self,
        reason: str,
        *,
        ac_mode: Optional[str] = None,
        force: Optional[bool] = None,
    ) -> None:
        if self._late_effect_guard_blocks(INTENT_NEUTRALIZE, 0, reason):
            self._startup_deadband_neutralized = True
            return
        previous = self._desired_command_batch
        new_episode = not (
            previous is not None
            and previous.intent == INTENT_NEUTRALIZE
            and previous.input_limit_w == 0
            and previous.output_limit_w == 0
            and previous.ac_mode == (ac_mode or self._last_non_neutral_ac_mode or "Output mode")
        )
        batch = self._new_command_batch(
            0,
            reason=reason,
            explicit_neutralize=True,
            ac_mode=ac_mode,
            safety_relevant=True,
        )
        self._publish_command_batch(
            batch,
            force=(new_episode if force is None else bool(force)),
            publish_kind="neutralization",
        )
        # Any explicit safety neutralisation also satisfies the restart-only
        # deadband guard; do not send a second physical zero batch in the same
        # transition cycle.
        self._startup_deadband_neutralized = True

    def _force_resend_signed_target(self, signed_target_w: int, reason: str) -> None:
        signed_target_w = int(signed_target_w or 0)
        desired = self._desired_command_batch
        if desired is None or desired.signed_target_w != signed_target_w:
            if signed_target_w == 0:
                desired = self._new_command_batch(
                    0,
                    reason="RECOVERY_NEUTRALIZATION",
                    explicit_neutralize=True,
                    ac_mode=self._last_non_neutral_ac_mode,
                    safety_relevant=True,
                )
            else:
                desired = self._new_command_batch(signed_target_w, reason="RECOVERY_ACTIVE_TARGET")
        self._publish_command_batch(desired, force=True, publish_kind="resync")
        now_text = datetime.now().strftime("%H:%M:%S")
        with self.state.lock:
            self.state.command_resync_count += 1
            self.state.command_resync_last_time = now_text
            self.state.command_resync_reason = str(reason or "COMMAND_RESYNC")
            # Resync sent is not recovery confirmed.  Keep an existing mismatch
            # open until physical telemetry proves the desired state.
            self.state.command_lifecycle_state = "RECOVERY_VERIFYING"
            self.state.command_effect_category = "COMMAND_RECOVERY_VERIFYING"
            self.state.command_effect_reason = "Full-State-Kommandoabgleich ausgeführt; physische Wirkung wird weiter geprüft."
        self.state.add_event(f"Zendure Command-Resync ausgeführt: {signed_target_w} W ({reason})")
        self.log(f"[COMMAND_RESYNC] target={signed_target_w}W reason={reason}")

    def _current_signed_target(self) -> int:
        with self.state.lock:
            if self.state.last_input_power > 0 and self.state.last_output_power <= 0:
                return int(self.state.last_input_power)
            if self.state.last_output_power > 0 and self.state.last_input_power <= 0:
                return -int(self.state.last_output_power)
        return 0

    def _hard_mqtt_loss_status(self, status: str) -> bool:
        status = str(status or "").upper()
        return status in {
            "ZENDURE_MQTT_NO_LIVE",
            "ZENDURE_MQTT_RETAINED_ONLY",
            "ZENDURE_MQTT_AFTER_BROKER_RESTART_NO_LIVE_UPDATES",
            "ZENDURE_MQTT_UNKNOWN",
        }

    def _clear_command_not_effective_locked(self) -> None:
        self.state.command_not_effective_active = False
        self.state.command_not_effective_since_epoch = None
        self.state.command_not_effective_since_time = "-"
        self.state.command_not_effective_duration_s = 0
        self.state.command_not_effective_reason = ""
        if "COMMAND_NOT_EFFECTIVE" in self.state.active_limiters:
            self.state.active_limiters = [x for x in self.state.active_limiters if x != "COMMAND_NOT_EFFECTIVE"]
            self.state.last_limit_reason = ", ".join(self.state.active_limiters) if self.state.active_limiters else "none"

    def _set_command_effect_state(self, category: str, reason: str, lifecycle: Optional[str] = None) -> None:
        with self.state.lock:
            self.state.command_effect_category = str(category or "")
            self.state.command_effect_reason = str(reason or "")
            if lifecycle:
                self.state.command_lifecycle_state = str(lifecycle)

    def _resync_permitted(self, target: int, reason: str, cfg: Dict[str, Any], *, confirmed_mismatch: bool = False) -> bool:
        """Deduplicate only redundant resyncs, never required recovery."""
        self._ensure_command_lifecycle_attrs()
        now = time.time()
        cooldown_s = max(0, int(cfg.get("COMMAND_RESYNC_COOLDOWN_SECONDS", 120) or 0))
        desired_signature = self._desired_command_batch.signature if self._desired_command_batch is not None else str(int(target))
        signature = f"{desired_signature}|{reason}"
        if cooldown_s > 0 and signature == self._last_resync_signature and (now - self._last_resync_epoch) < cooldown_s:
            if not confirmed_mismatch:
                with self.state.lock:
                    self.state.command_resync_suppressed_count += 1
                    self.state.command_resync_suppressed_last_time = datetime.now().strftime("%H:%M:%S")
                    self.state.command_resync_suppressed_reason = "RESYNC_SUPPRESSED_COOLDOWN"
                return False
            # The caller separately enforces the resend interval. A confirmed
            # mismatch must never become permanently unrecoverable through dedupe.
            return True
        self._last_resync_signature = signature
        self._last_resync_epoch = now
        return True

    def _command_power_observation(self, now: float, cfg: Dict[str, Any]) -> Dict[str, Any]:
        actual_timeout_s = max(1, int(cfg.get("ZENDURE_POWER_STALE_TIMEOUT_SECONDS", 90) or 90))
        with self.state.lock:
            obs_epoch = self.state.zendure_power_observation_updated_epoch
            obs_signed = self.state.zendure_power_observation_signed_w
            obs_magnitude = int(self.state.zendure_power_observation_magnitude_w or 0)
            obs_direction = str(self.state.zendure_power_observation_direction or "UNKNOWN")
            obs_confidence = str(self.state.zendure_power_observation_confidence or "NONE")
            obs_reason = str(self.state.zendure_power_observation_reason or "")
            legacy_actual = int(self.state.actual_zendure_system_signed_power or 0)
            legacy_valid = bool(self.state.actual_zendure_power_valid and self.state.last_zendure_power_update_epoch is not None)
            legacy_epoch = self.state.last_zendure_power_update_epoch

        if obs_epoch is not None:
            age_s = max(0.0, now - float(obs_epoch))
            return {
                "signed": int(obs_signed) if obs_signed is not None else None,
                "magnitude": obs_magnitude,
                "direction": obs_direction,
                "confidence": obs_confidence,
                "reason": obs_reason,
                "valid": age_s <= actual_timeout_s,
                "age_s": age_s,
                "source": "independent_observation",
            }

        # Compatibility fallback for old tests and installations before the first
        # raw telemetry refresh.  Production observations supersede it immediately.
        age_s = max(0.0, now - float(legacy_epoch)) if legacy_epoch is not None else None
        return {
            "signed": legacy_actual if legacy_valid else None,
            "magnitude": abs(legacy_actual),
            "direction": "CHARGE" if legacy_actual > 0 else "DISCHARGE" if legacy_actual < 0 else "NEUTRAL",
            "confidence": "LEGACY",
            "reason": "Legacy signed power fallback; independent raw observation not available yet.",
            "valid": bool(legacy_valid and age_s is not None and age_s <= actual_timeout_s),
            "age_s": age_s,
            "source": "legacy_fallback",
        }

    def _resume_effect_timers_after_telemetry_pause(self, now: float) -> None:
        if self._command_effect_telemetry_pause_epoch is None:
            return
        paused_s = max(0.0, now - self._command_effect_telemetry_pause_epoch)
        if self._command_effect_watch_start_epoch is not None:
            self._command_effect_watch_start_epoch += paused_s
        if self._command_tracking_mismatch_start_epoch is not None:
            self._command_tracking_mismatch_start_epoch += paused_s
        with self.state.lock:
            if self.state.command_neutralization_since_epoch is not None:
                self.state.command_neutralization_since_epoch += paused_s
        self._command_effect_telemetry_pause_epoch = None

    def _mark_mismatch(self, *, target: int, actual_text: str, elapsed_s: int, tolerance_w: int, neutral: bool = False) -> None:
        now = time.time()
        with self.state.lock:
            self.state.command_mismatch_resolution = ""
            self.state.command_not_effective_active = True
            if self.state.command_not_effective_since_epoch is None:
                start = self.state.command_neutralization_since_epoch if neutral else (
                    self._command_tracking_mismatch_start_epoch or self._command_effect_watch_start_epoch or now
                )
                self.state.command_not_effective_since_epoch = start
                self.state.command_not_effective_since_time = datetime.fromtimestamp(start).strftime("%H:%M:%S")
            self.state.command_not_effective_duration_s = elapsed_s
            if neutral:
                reason = (
                    f"Neutralisierung auf 0 W seit {elapsed_s} s nicht bestätigt; beobachtete Leistung {actual_text}. "
                    "Full-State-Neutralisierung wird recoveryfähig erneut gesendet."
                )
                category = "COMMAND_NEUTRALIZATION_MISMATCH"
            else:
                direction = "Ladung" if target > 0 else "Entladung"
                reason = (
                    f"Soll {target:+d} W ({direction}) wird seit {elapsed_s} s nicht ausreichend verfolgt; "
                    f"Istbeobachtung {actual_text}, Toleranz {tolerance_w} W."
                )
                category = "COMMAND_MISMATCH_CONFIRMED"
            self.state.command_not_effective_reason = reason
            self.state.command_effect_category = category
            self.state.command_effect_reason = reason
            self.state.command_lifecycle_state = "MISMATCH_CONFIRMED"
            self.state.command_effect_confirmed = False
            self.state.add_limiter("COMMAND_NOT_EFFECTIVE")

    def update_command_effect_monitor(self, cfg: Dict[str, Any]) -> None:
        """Intent-based, neutralisation-aware, non-blocking command monitor."""
        self._ensure_command_lifecycle_attrs()
        target = self._current_signed_target()
        now = time.time()
        with self.state.lock:
            status = str(self.state.zendure_mqtt_overall_status or "")
            live_confirmed = bool(self.state.zendure_mqtt_live_confirmed)
            uncertainty_active = bool(self.state.command_uncertain_mqtt_active)
            neutral_active = bool(self.state.command_neutralization_active)
            desired_intent = str(self.state.command_desired_intent or INTENT_IDLE)

        if desired_intent == INTENT_IDLE:
            desired_intent = intent_for_signed_target(target)
        if desired_intent != INTENT_CHARGE or target <= 0:
            self._reset_charge_acceptance_episode()

        # Production dynamic control is not effect-evaluable until the volatile
        # smartMode contract and the four command-state properties have been
        # freshly read back.  This avoids diagnosing a command which was
        # deliberately held back to protect the device flash. Neutralisation is
        # still observed independently at the grid boundary.
        if desired_intent in {INTENT_CHARGE, INTENT_DISCHARGE} and self._smart_mode_contract_supported():
            command_snapshot = self._command_state_snapshot(cfg)
            if not command_snapshot.get("flash_protection_active") or not command_snapshot.get("complete"):
                self._reset_charge_acceptance_episode()
                with self.state.lock:
                    self.state.command_lifecycle_state = "COMMAND_STATE_VERIFYING"
                    self.state.command_effect_category = "COMMAND_STATE_VERIFYING"
                    self.state.command_effect_reason = str(command_snapshot.get("reason") or "Zendure-Command-State wird rückgelesen.")
                    self.state.command_effect_confirmed = False
                return

        if neutral_active or (target == 0 and uncertainty_active):
            desired_intent = INTENT_NEUTRALIZE
            if not neutral_active:
                with self.state.lock:
                    self.state.command_neutralization_active = True
                    self.state.command_neutralization_reason = "UNSICHERER_NEUTRALER_COMMAND_STATE"
                    self.state.command_neutralization_since_epoch = now
                    self.state.command_neutralization_since_time = datetime.now().strftime("%H:%M:%S")

        mqtt_uncertain = self._zendure_mqtt_uncertain_for_active_command(status, live_confirmed)
        hard_loss = self._hard_mqtt_loss_status(status)
        previous_status = self._last_zendure_mqtt_status
        if mqtt_uncertain:
            if self._mqtt_uncertain_since_epoch is None:
                self._mqtt_uncertain_since_epoch = now
                self._mqtt_uncertain_cycles = 0
                self._mqtt_uncertain_had_hard_loss = False
            self._mqtt_uncertain_cycles += 1
            self._mqtt_uncertain_had_hard_loss = self._mqtt_uncertain_had_hard_loss or hard_loss
        uncertainty_duration_s = max(0, int(now - self._mqtt_uncertain_since_epoch)) if self._mqtt_uncertain_since_epoch is not None else 0
        recovered_to_ok = bool(previous_status) and previous_status != "ZENDURE_MQTT_OK" and status == "ZENDURE_MQTT_OK" and live_confirmed
        long_stale_s = max(3, int(cfg.get("COMMAND_RESYNC_STALE_MIN_SECONDS", 30) or 30))
        stale_cycles_min = max(1, int(cfg.get("COMMAND_RESYNC_STALE_MIN_CYCLES", 3) or 3))
        robust_uncertainty = (
            uncertainty_active
            or self._mqtt_uncertain_had_hard_loss
            or uncertainty_duration_s >= long_stale_s
            or self._mqtt_uncertain_cycles >= stale_cycles_min
            or bool(cfg.get("COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS", False))
        )
        recovery_resync_sent = False
        if desired_intent != INTENT_IDLE and recovered_to_ok and robust_uncertainty:
            reason = "RESYNC_AFTER_RECONNECT" if self._mqtt_uncertain_had_hard_loss else "RESYNC_AFTER_LONG_STALE"
            if self._resync_permitted(target, reason, cfg):
                self._force_resend_signed_target(target, reason)
                self._command_effect_last_resend_epoch = now
                recovery_resync_sent = True
        if recovered_to_ok or not mqtt_uncertain:
            self._mqtt_uncertain_since_epoch = None
            self._mqtt_uncertain_cycles = 0
            self._mqtt_uncertain_had_hard_loss = False
        self._last_zendure_mqtt_status = status

        observation = self._command_power_observation(now, cfg)
        telemetry_valid = bool(status == "ZENDURE_MQTT_OK" and live_confirmed and observation["valid"])
        if not telemetry_valid:
            self._reset_charge_acceptance_episode()
            if self._command_effect_telemetry_pause_epoch is None:
                self._command_effect_telemetry_pause_epoch = now
            with self.state.lock:
                self.state.command_lifecycle_state = (
                    "LATE_EFFECT_NEUTRALIZING" if self._late_effect_guard_active else "TELEMETRY_UNCERTAIN"
                )
                self.state.command_effect_category = "COMMAND_TELEMETRY_UNCERTAIN"
                self.state.command_effect_reason = (
                    f"{'Late-Effect-Guard wartet; ' if self._late_effect_guard_active else ''}"
                    f"Wirksamkeit pausiert: MQTT={status or 'UNKNOWN'}, live={live_confirmed}, "
                    f"Leistungsbeobachtung={observation['direction']}/{observation['confidence']}."
                )
                self.state.command_effect_confirmed = False
            if self._late_effect_guard_active:
                self._reset_late_effect_neutral_confirmation()
                self._update_late_effect_guard_state(reason="Telemetrie für Neutralitätsnachweis nicht frisch")
            return
        self._resume_effect_timers_after_telemetry_pause(now)

        physical_direction = str(observation.get("direction") or "")
        if physical_direction in {"CHARGE", "DISCHARGE"}:
            if (
                self._last_physical_non_neutral_direction
                and self._last_physical_non_neutral_direction != physical_direction
            ):
                with self.state.lock:
                    self.state.physical_power_direction_change_count += 1
            self._last_physical_non_neutral_direction = physical_direction

        absolute_tolerance_w = max(10, int(cfg.get("COMMAND_EFFECT_TOLERANCE_W", 80) or 80))
        tolerance_percent = max(0.0, float(cfg.get("COMMAND_EFFECT_TOLERANCE_PERCENT", 10) or 0.0))
        tolerance_w = max(absolute_tolerance_w, int(round(abs(target) * tolerance_percent / 100.0)))
        threshold_w = max(30, int(cfg.get("COMMAND_EFFECT_MIN_W", 80) or 80))
        signed_actual = observation["signed"]
        magnitude = int(observation["magnitude"] or 0)
        actual_text = (
            f"{int(signed_actual):+d} W ({observation['confidence']})"
            if signed_actual is not None
            else f"{magnitude} W, Richtung {observation['direction']}"
        )

        if self._evaluate_late_effect_guard(
            cfg,
            observation,
            absolute_tolerance_w=absolute_tolerance_w,
            actual_text=actual_text,
            now_epoch=now,
        ):
            return

        if desired_intent == INTENT_NEUTRALIZE:
            with self.state.lock:
                start_epoch = self.state.command_neutralization_since_epoch
                reason = self.state.command_neutralization_reason or "Neutralisierung"
            if start_epoch is None:
                start_epoch = now
                with self.state.lock:
                    self.state.command_neutralization_since_epoch = now
                    self.state.command_neutralization_since_time = datetime.now().strftime("%H:%M:%S")
            if magnitude <= absolute_tolerance_w:
                was_mismatch = bool(self.state.command_not_effective_active)
                with self.state.lock:
                    self._clear_command_not_effective_locked()
                    self.state.command_neutralization_active = False
                    self.state.command_neutralization_since_epoch = None
                    self.state.command_neutralization_since_time = "-"
                    self.state.command_lifecycle_state = "RECOVERED" if was_mismatch else "NEUTRALIZATION_CONFIRMED"
                    self.state.command_effect_category = "COMMAND_NEUTRALIZATION_CONFIRMED"
                    self.state.command_effect_reason = f"Neutraler Gerätezustand mit {actual_text} bestätigt."
                    self.state.command_effect_confirmed = True
                    self.state.command_effect_confirmed_time = datetime.now().strftime("%H:%M:%S")
                    self.state.command_effect_confirmed_reason = self.state.command_effect_reason
                    self._neutralization_confirmed_signature = self._neutralization_physical_signature
                    self.state.command_uncertain_mqtt_active = False
                    self.state.command_uncertain_mqtt_reason = ""
                    self.state.command_uncertain_mqtt_status = ""
                    self.state.command_uncertain_mqtt_target_w = 0
                    self.state.command_uncertain_mqtt_since_epoch = None
                    self.state.command_uncertain_mqtt_since_time = "-"
                if was_mismatch:
                    self.state.add_event("Zendure-Neutralisierung physisch wiederhergestellt")
                return
            elapsed_s = max(0, int(now - float(start_epoch)))
            timeout_s = max(5, int(cfg.get("COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS", 30) or 30))
            if elapsed_s < timeout_s:
                self._set_command_effect_state(
                    "COMMAND_NEUTRALIZATION_PENDING",
                    f"Neutralisierung '{reason}' wird geprüft: {actual_text}; {elapsed_s}/{timeout_s} s.",
                    "NEUTRALIZATION_OBSERVING",
                )
                return
            self._mark_mismatch(target=0, actual_text=actual_text, elapsed_s=elapsed_s, tolerance_w=absolute_tolerance_w, neutral=True)
            retry_s = max(5, int(cfg.get("COMMAND_RESYNC_COOLDOWN_SECONDS", 120) or 120))
            if now - self._neutralization_last_resend_epoch >= retry_s:
                if self._resync_permitted(0, "RESYNC_AFTER_NEUTRALIZATION_MISMATCH", cfg, confirmed_mismatch=True):
                    self._force_resend_signed_target(0, f"RESYNC_AFTER_NEUTRALIZATION_MISMATCH_{elapsed_s}s")
                    self._neutralization_last_resend_epoch = now
            return

        if signed_actual is None and magnitude >= threshold_w:
            self._reset_charge_acceptance_episode()
            if self._command_effect_telemetry_pause_epoch is None:
                self._command_effect_telemetry_pause_epoch = now
            category = (
                "COMMAND_POWER_DIRECTION_CONFLICT"
                if observation["direction"] == "CONFLICT"
                else "COMMAND_POWER_DIRECTION_AMBIGUOUS"
            )
            with self.state.lock:
                # Loss of directional observability is not physical recovery.
                # Preserve any already confirmed mismatch until a later
                # independent observation proves the desired state.
                self.state.command_lifecycle_state = "TELEMETRY_UNCERTAIN"
                self.state.command_effect_category = category
                self.state.command_effect_reason = (
                    f"Leistungsbetrag {magnitude} W ist sichtbar, die physische Richtung ist "
                    f"{observation['direction']} ({observation['reason']}). Die Sollrichtung wird nicht als Beweis verwendet."
                )
                self.state.command_effect_confirmed = False
            return

        if desired_intent not in {INTENT_CHARGE, INTENT_DISCHARGE} or target == 0:
            self._command_effect_watch_intent = INTENT_IDLE
            self._command_effect_watch_target = 0
            self._command_effect_watch_start_epoch = None
            self._command_tracking_mismatch_start_epoch = None
            with self.state.lock:
                self._clear_command_not_effective_locked()
                self.state.command_lifecycle_state = "IDLE"
                self.state.command_effect_category = "COMMAND_IDLE"
                self.state.command_effect_reason = "Kein aktiver Command-Effect-Watch."
                self.state.command_effect_confirmed = False
            return

        min_target_w = max(0, int(cfg.get("COMMAND_EFFECT_MIN_TARGET_W", 120) or 120))
        if abs(target) < min_target_w:
            self._reset_charge_acceptance_episode()
            self._command_effect_watch_intent = desired_intent
            self._command_effect_watch_target = target
            self._command_effect_watch_start_epoch = None
            self._command_tracking_mismatch_start_epoch = None
            with self.state.lock:
                self._clear_command_not_effective_locked()
                self.state.command_lifecycle_state = "ACTIVE_BELOW_DIAGNOSTIC_THRESHOLD"
                self.state.command_effect_category = "COMMAND_BELOW_DIAGNOSTIC_THRESHOLD"
                self.state.command_effect_reason = f"Sollwert {target:+d} W liegt unter der Diagnosegrenze {min_target_w} W; Wirkung nicht belastbar bewertet."
                self.state.command_effect_confirmed = False
            return

        if (
            self._command_effect_watch_intent == INTENT_IDLE
            and self._command_effect_watch_start_epoch is not None
            and self._command_effect_watch_target != 0
            and intent_for_signed_target(self._command_effect_watch_target) == desired_intent
        ):
            self._command_effect_watch_intent = desired_intent

        if desired_intent != self._command_effect_watch_intent:
            self._command_effect_watch_intent = desired_intent
            self._command_effect_watch_start_epoch = now
            self._command_tracking_mismatch_start_epoch = None
            with self.state.lock:
                self._clear_command_not_effective_locked()
                if recovery_resync_sent:
                    self.state.command_lifecycle_state = "RECOVERY_VERIFYING"
                    self.state.command_effect_category = "COMMAND_RECOVERY_VERIFYING"
                    self.state.command_effect_reason = "Full-State-Kommandoabgleich ausgeführt; Richtungsreaktion und Sollwerttracking werden geprüft."
                else:
                    self.state.command_lifecycle_state = "ACTIVE_OBSERVING"
                    self.state.command_effect_category = "COMMAND_PENDING"
                    self.state.command_effect_reason = f"Neuer {desired_intent}-Intent; Reaktionszeit läuft."
        elif self._command_effect_watch_start_epoch is None:
            # Compatibility with tests/old in-memory state that predate the intent field.
            self._command_effect_watch_start_epoch = now
        self._command_effect_watch_target = target

        same_direction = (
            signed_actual is not None
            and ((target > 0 and int(signed_actual) >= threshold_w) or (target < 0 and int(signed_actual) <= -threshold_w))
        )
        tracking = same_direction and abs(int(target) - int(signed_actual)) <= tolerance_w
        if target > 0:
            reference_w, command_snapshot = self._confirmed_charge_reference(cfg, target)
        else:
            reference_w, command_snapshot = 0, self._command_state_snapshot(cfg)
            with self.state.lock:
                self.state.command_effect_reference_w = 0
        timeout_s = max(10, int(cfg.get("COMMAND_EFFECT_TIMEOUT_SECONDS", 90) or 90))
        resend_s = max(timeout_s, int(cfg.get("COMMAND_EFFECT_FORCE_RESEND_SECONDS", 120) or 120))

        if tracking:
            with self.state.lock:
                tracking_soc = self.state.battery_soc
            tracking_high_soc = bool(
                target > 0
                and reference_w >= min_target_w
                and tracking_soc is not None
                and float(tracking_soc) >= float(int(cfg.get("MAX_SOC_PERCENT", 100) or 100) - 10)
            )
            if tracking_high_soc:
                observed_tracking_w = max(0, int(signed_actual or 0))
                previous_positive = self._charge_acceptance_last_positive_w
                if previous_positive is not None and observed_tracking_w <= previous_positive - 10:
                    self._charge_acceptance_taper_steps += 1
                self._charge_acceptance_last_positive_w = observed_tracking_w
                self._charge_acceptance_zero_since_epoch = None
                self._charge_acceptance_zero_cycles = 0
            else:
                self._reset_charge_acceptance_episode()
            was_mismatch = bool(self.state.command_not_effective_active)
            self._command_tracking_mismatch_start_epoch = None
            self._command_effect_watch_start_epoch = None
            with self.state.lock:
                self._clear_command_not_effective_locked()
                self.state.command_uncertain_mqtt_active = False
                self.state.command_uncertain_mqtt_reason = ""
                self.state.command_uncertain_mqtt_status = ""
                self.state.command_uncertain_mqtt_target_w = 0
                self.state.command_uncertain_mqtt_since_epoch = None
                self.state.command_uncertain_mqtt_since_time = "-"
                self.state.command_lifecycle_state = "RECOVERED" if was_mismatch else "ACTIVE_EFFECTIVE"
                self.state.command_effect_category = "COMMAND_TARGET_TRACKING_EFFECTIVE"
                self.state.command_effect_reason = f"Soll {target:+d} W und unabhängige Istbeobachtung {int(signed_actual):+d} W liegen innerhalb {tolerance_w} W."
                confirmation_is_new = not bool(self.state.command_effect_confirmed)
                self.state.command_effect_confirmed = True
                if confirmation_is_new:
                    self.state.command_effect_confirmed_time = datetime.now().strftime("%H:%M:%S")
                self.state.command_effect_confirmed_reason = self.state.command_effect_reason
            if was_mismatch:
                self.state.add_event("Zendure-Kommandowirkung wiederhergestellt")
            return

        # RC14: High-SOC charge acceptance is evaluated against the fresh,
        # statically confirmed device command state.  Exact equality with the
        # latest cloud-driven target is deliberately not required; the smaller
        # of current target and positive read-back limit is the reference.
        with self.state.lock:
            acceptance_state = str(self.state.charge_acceptance_state or "ok")
            acceptance_reason = str(self.state.charge_acceptance_reason or "-")
            battery_charge_w = int(self.state.zendure_battery_charge_power_w or 0)
            battery_discharge_w = int(self.state.zendure_battery_discharge_power_w or 0)
            soc_percent = self.state.battery_soc
            current_grid_power = float(self.state.grid_power or 0.0)
        previous_charge_soc = self._command_effect_last_charge_soc
        soc_non_falling = bool(
            soc_percent is not None
            and (previous_charge_soc is None or float(soc_percent) >= float(previous_charge_soc) - 1.0)
        )
        if target > 0 and soc_percent is not None:
            self._command_effect_last_charge_soc = float(soc_percent)
        elif target <= 0:
            self._command_effect_last_charge_soc = None

        max_soc_percent = int(cfg.get("MAX_SOC_PERCENT", 100) or 100)
        high_soc = bool(
            soc_percent is not None
            and float(soc_percent) >= float(max_soc_percent - 10)
        )
        static_charge_state_confirmed = bool(
            desired_intent == INTENT_CHARGE
            and reference_w >= min_target_w
            and command_snapshot.get("complete")
            and command_snapshot.get("smart_mode") == 1
            and command_snapshot.get("ac_mode") == "Input mode"
            and int(command_snapshot.get("output_limit_w") or 0) == 0
        )
        no_battery_discharge = battery_discharge_w < 20
        no_direction_conflict = observation.get("direction") not in {"DISCHARGE", "CONFLICT"}
        common_acceptance_invariants = bool(
            target > 0
            and high_soc
            and static_charge_state_confirmed
            and soc_non_falling
            and no_battery_discharge
            and no_direction_conflict
            and acceptance_state in {"limited", "not_accepting"}
        )

        observed_charge_w = max(
            0,
            int(signed_actual) if signed_actual is not None and int(signed_actual) > 0 else 0,
            battery_charge_w,
        )
        if common_acceptance_invariants and observed_charge_w >= 20:
            previous_positive = self._charge_acceptance_last_positive_w
            if previous_positive is not None and observed_charge_w <= previous_positive - 10:
                self._charge_acceptance_taper_steps += 1
            self._charge_acceptance_last_positive_w = observed_charge_w
            self._charge_acceptance_zero_since_epoch = None
            self._charge_acceptance_zero_cycles = 0
        elif common_acceptance_invariants and observed_charge_w < 20:
            if self._charge_acceptance_zero_since_epoch is None:
                self._charge_acceptance_zero_since_epoch = now
                self._charge_acceptance_zero_cycles = 1
            else:
                self._charge_acceptance_zero_cycles += 1
        else:
            self._reset_charge_acceptance_episode()

        limited_while_charging = bool(
            common_acceptance_invariants
            and observation.get("direction") == "CHARGE"
            and signed_actual is not None
            and int(signed_actual) >= 20
            and battery_charge_w >= 20
        )

        zero_elapsed_s = (
            max(0.0, now - float(self._charge_acceptance_zero_since_epoch))
            if self._charge_acceptance_zero_since_epoch is not None else 0.0
        )
        at_or_above_max = bool(
            soc_percent is not None and float(soc_percent) >= float(max_soc_percent)
        )
        below_max_independent_support = bool(
            current_grid_power <= -max(80, int(cfg.get("DEADBAND_W", 80) or 80))
            or self._charge_acceptance_taper_steps >= 2
            or zero_elapsed_s >= 10.0
        )
        zero_not_accepting_candidate = bool(
            common_acceptance_invariants
            and observation.get("direction") == "NEUTRAL"
            and observed_charge_w < 20
            and battery_charge_w < 20
            and (
                acceptance_state == "not_accepting"
                or (not at_or_above_max and acceptance_state == "limited" and self._charge_acceptance_taper_steps >= 2)
            )
            and (at_or_above_max or below_max_independent_support)
        )
        zero_not_accepting_confirmed = bool(
            zero_not_accepting_candidate
            and self._charge_acceptance_zero_cycles >= 3
            and zero_elapsed_s >= 6.0
        )

        if zero_not_accepting_candidate and not zero_not_accepting_confirmed:
            # A short, bounded confirmation window prevents a known BMS stop at
            # Max-SOC from entering the 90/120-s mismatch/resync chain.
            self._command_tracking_mismatch_start_epoch = None
            self._command_effect_watch_start_epoch = now
            with self.state.lock:
                self._clear_command_not_effective_locked()
                self.state.command_lifecycle_state = "ACTIVE_ACCEPTANCE_VERIFYING"
                self.state.command_effect_category = "COMMAND_PENDING"
                self.state.command_effect_reason = (
                    f"HIGH_SOC_NOT_ACCEPTING wird bestätigt: Referenz +{reference_w} W, "
                    f"netzseitig {actual_text}, Batterie +{battery_charge_w} W; "
                    f"{self._charge_acceptance_zero_cycles}/3 Zyklen, {zero_elapsed_s:.1f}/6.0 s."
                )
                self.state.command_effect_confirmed = False
            return

        if limited_while_charging or zero_not_accepting_confirmed:
            was_mismatch = bool(self.state.command_not_effective_active)
            self._command_tracking_mismatch_start_epoch = None
            self._command_effect_watch_start_epoch = now
            subtype = "HIGH_SOC_CHARGE_LIMITED" if limited_while_charging else "HIGH_SOC_NOT_ACCEPTING"
            with self.state.lock:
                self._clear_command_not_effective_locked()
                if was_mismatch:
                    self.state.command_mismatch_resolution = "MISMATCH_RECLASSIFIED_AS_CHARGE_ACCEPTANCE_LIMITED"
                self.state.command_lifecycle_state = "ACTIVE_ACCEPTANCE_LIMITED"
                self.state.command_effect_category = "COMMAND_CHARGE_ACCEPTANCE_LIMITED"
                self.state.command_effect_reason = (
                    f"{subtype}: statischer Lade-Command-State und Referenz +{reference_w} W sind bestätigt; "
                    f"netzseitig {actual_text}, Batterie +{battery_charge_w} W. {acceptance_reason}"
                )
                self.state.command_effect_confirmed = False
            if was_mismatch:
                self.state.add_event("Kommando-Mismatch als geräteseitige High-SOC-Ladebegrenzung reklassifiziert")
            return

        if same_direction:
            if self._command_tracking_mismatch_start_epoch is None:
                self._command_tracking_mismatch_start_epoch = now
            mismatch_start = self._command_tracking_mismatch_start_epoch
            elapsed_s = max(0, int(now - float(mismatch_start)))
            if elapsed_s < timeout_s:
                with self.state.lock:
                    self._clear_command_not_effective_locked()
                    self.state.command_lifecycle_state = "ACTIVE_OBSERVING"
                    self.state.command_effect_category = "COMMAND_PARTIALLY_EFFECTIVE"
                    self.state.command_effect_reason = (
                        f"Richtung reagiert, Sollwerttracking noch unzureichend: Soll {target:+d} W, Ist {int(signed_actual):+d} W; "
                        f"{elapsed_s}/{timeout_s} s."
                    )
                    self.state.command_effect_confirmed = False
                return
            self._mark_mismatch(target=target, actual_text=actual_text, elapsed_s=elapsed_s, tolerance_w=tolerance_w)
            mismatch_elapsed = elapsed_s
        else:
            start = self._command_effect_watch_start_epoch or now
            elapsed_s = max(0, int(now - float(start)))
            if elapsed_s < timeout_s:
                with self.state.lock:
                    self._clear_command_not_effective_locked()
                    if recovery_resync_sent:
                        self.state.command_lifecycle_state = "RECOVERY_VERIFYING"
                        self.state.command_effect_category = "COMMAND_RECOVERY_VERIFYING"
                        self.state.command_effect_reason = (
                            f"Full-State-Kommandoabgleich ausgeführt; Soll {target:+d} W, Istbeobachtung {actual_text}; "
                            f"Richtungsreaktion {elapsed_s}/{timeout_s} s ausstehend."
                        )
                    else:
                        self.state.command_lifecycle_state = "ACTIVE_OBSERVING"
                        self.state.command_effect_category = "COMMAND_PENDING"
                        self.state.command_effect_reason = (
                            f"Soll {target:+d} W, Istbeobachtung {actual_text}; Richtungsreaktion {elapsed_s}/{timeout_s} s ausstehend."
                        )
                    self.state.command_effect_confirmed = False
                return
            self._mark_mismatch(target=target, actual_text=actual_text, elapsed_s=elapsed_s, tolerance_w=tolerance_w)
            mismatch_elapsed = elapsed_s

        if now - self._last_command_effect_log_epoch >= 120:
            self._last_command_effect_log_epoch = now
            self.log(f"[COMMAND_EFFECT] category=COMMAND_MISMATCH_CONFIRMED target={target}W actual={actual_text} elapsed_s={mismatch_elapsed} mqtt={status}")

        if mismatch_elapsed >= resend_s and now - self._command_effect_last_resend_epoch >= max(1, resend_s):
            if self._resync_permitted(target, "RESYNC_AFTER_CONFIRMED_MISMATCH", cfg, confirmed_mismatch=True):
                self._force_resend_signed_target(target, f"RESYNC_AFTER_CONFIRMED_MISMATCH_{mismatch_elapsed}s")
                self._command_effect_last_resend_epoch = now

    def _store_signed_target(self, signed_target_w: int, reason: str, path: str, action_prefix: str) -> None:
        signed_target_w = int(signed_target_w or 0)
        input_power = max(0, signed_target_w)
        output_power = max(0, -signed_target_w)
        with self.state.lock:
            self.state.last_input_power = input_power
            self.state.last_output_power = output_power
            self.state.current_target_power = max(input_power, output_power)
            self.state.last_target_after_ramp = max(input_power, output_power)
            self.state.control_reason = reason
            self.state.technical_control_path = path
            self.state.last_control_action = f"{action_prefix} -> {signed_target_w} W"

    def cross_charge_guard_corrects_existing_target(self, cfg: Dict[str, Any]) -> bool:
        """Reduce an already active AUTO/HOLD target when the second battery moves opposite."""
        with self.state.lock:
            if self.state.last_input_power > 0 and self.state.last_output_power <= 0:
                current = int(self.state.last_input_power)
            elif self.state.last_output_power > 0 and self.state.last_input_power <= 0:
                current = -int(self.state.last_output_power)
            else:
                current = 0
        correction = self._apply_symmetric_cross_charge_limit(cfg, current)
        if not correction.get("active") or int(correction.get("target", current)) == current:
            return False
        new_target = int(correction["target"])
        new_target = self._publish_signed_target(new_target, force_zero=(new_target == 0), reason=("CROSS_CHARGE_NEUTRALIZATION" if new_target == 0 else "CROSS_CHARGE_HOLD_CORRECTION"))
        self._store_signed_target(
            new_target,
            correction.get("reason") or "Cross-Charge-Schutz aktiv",
            "GRID -> CROSS_CHARGE -> HOLD_CORRECTED",
            "CROSS_CHARGE",
        )
        self.state.set_mode("HOLD" if new_target == 0 else ("CHARGE" if new_target > 0 else "DISCHARGE"))
        return True


    def _rest_surplus_max_charge_w(self, cfg: Dict[str, Any]) -> Optional[int]:
        value = self._optional_int(cfg.get("SECOND_BATTERY_MAX_CHARGE_POWER_W"))
        return value if value is not None and value > 0 else None

    def _cfg_float(self, cfg: Dict[str, Any], key: str, default: float) -> float:
        try:
            value = cfg.get(key, default)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    def _cfg_optional_w(self, cfg: Dict[str, Any], key: str) -> Optional[int]:
        value = self._optional_int(cfg.get(key))
        return value if value is not None and value >= 0 else None

    def _profile_clock_minutes(self) -> int:
        now = datetime.now()
        return now.hour * 60 + now.minute

    def _harvest_time_profile(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        if not bool(cfg.get("HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED", True)):
            return {
                "name": "default",
                "share": self._cfg_float(cfg, "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY", 0.50),
                "reserve_w": 0,
                "entry_confirm_s": int(cfg.get("HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS", 30) or 30),
            }
        minutes = self._profile_clock_minutes()
        if 9 * 60 + 30 <= minutes < 11 * 60 + 30:
            return {"name": "morning", "share": self._cfg_float(cfg, "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING", 0.60), "reserve_w": 0, "entry_confirm_s": 60}
        if 11 * 60 + 30 <= minutes < 14 * 60 + 30:
            return {"name": "midday", "share": self._cfg_float(cfg, "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY", 0.50), "reserve_w": 0, "entry_confirm_s": 30}
        if 14 * 60 + 30 <= minutes < 18 * 60:
            return {"name": "afternoon", "share": self._cfg_float(cfg, "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON", 0.35), "reserve_w": 0, "entry_confirm_s": 15}
        return {"name": "default", "share": self._cfg_float(cfg, "HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY", 0.50), "reserve_w": 0, "entry_confirm_s": int(cfg.get("HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS", 30) or 30)}

    def _primary_threshold_w(self, cfg: Dict[str, Any], absolute_key: str, ratio_key: str, fallback_ratio: float) -> int:
        max_charge = self._rest_surplus_max_charge_w(cfg) or 0
        explicit = self._cfg_optional_w(cfg, absolute_key)
        if explicit is not None and explicit > 0:
            return int(explicit)
        ratio = self._cfg_float(cfg, ratio_key, fallback_ratio)
        return max(0, int(round(max_charge * ratio))) if max_charge > 0 else 0

    def _rest_surplus_thresholds(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        max_charge = self._rest_surplus_max_charge_w(cfg) or 0
        margin = max(0, int(cfg.get("SECOND_BATTERY_CHARGE_SATURATION_MARGIN_W", 100) or 100))
        min_export = max(1, int(cfg.get("REST_SURPLUS_MIN_EXPORT_W", 80) or 80))
        entry_confirm_s = max(1, int(cfg.get("REST_SURPLUS_ENTRY_CONFIRM_SECONDS", 30) or 30))
        saturation = self._primary_threshold_w(cfg, "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_W", "HARVEST_PRIMARY_CHARGE_NEAR_LIMIT_RATIO", 0.95)
        if saturation <= 0 and max_charge > 0:
            saturation = max(0, max_charge - margin)
        critical_floor = self._primary_threshold_w(cfg, "HARVEST_PRIMARY_CHARGE_FLOOR_W", "HARVEST_PRIMARY_CHARGE_FLOOR_RATIO", 0.30)
        restart = self._primary_threshold_w(cfg, "HARVEST_PRIMARY_CHARGE_RESTART_W", "HARVEST_PRIMARY_CHARGE_RESTART_RATIO", 0.85)
        high_min_export = max(1, int(cfg.get("HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W", 300) or 300))
        profile = self._harvest_time_profile(cfg)
        high_entry_confirm_s = max(1, int(profile.get("entry_confirm_s") or cfg.get("HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS", 30) or 30))
        return {
            "max_charge": max_charge,
            "margin": margin,
            "min_export": min_export,
            "entry_confirm_s": entry_confirm_s,
            "saturation": saturation,
            "critical_floor": critical_floor,
            "restart": restart,
            "high_enabled": bool(cfg.get("HARVEST_HIGH_SMA_SOC_ENABLED", True)),
            "high_enter_soc": float(cfg.get("HARVEST_HIGH_SMA_SOC_ENTER_PERCENT", 75) or 75),
            "high_exit_soc": float(cfg.get("HARVEST_HIGH_SMA_SOC_EXIT_PERCENT", 70) or 70),
            "high_min_export": high_min_export,
            "high_entry_confirm_s": high_entry_confirm_s,
            "high_hold_s": max(0, int(cfg.get("HARVEST_HIGH_SMA_SOC_HOLD_SECONDS", 180) or 180)),
            "full_soc": float(cfg.get("HARVEST_SMA_FULL_SOC_PERCENT", 98) or 98),
            "profile": profile,
        }

    def _reset_rest_surplus_harvest(self, reason: str) -> None:
        with self.state.lock:
            self.state.rest_surplus_harvest_active = False
            self.state.rest_surplus_harvest_eligible = False
            self.state.rest_surplus_entry_progress_s = 0.0
            self.state.rest_surplus_hold_remaining_s = 0.0
            self.state.rest_surplus_exit_reason = str(reason or "")
            self.state.rest_surplus_harvest_reason = "NONE"
            self.state.rest_surplus_harvest_block_reason = str(reason or "")
            self.state.harvest_target_semantics = "NOT_APPLICABLE"
            self.state.harvest_reference_charge_w = 0.0
            self.state.harvest_reference_charge_source = "NONE"
            self.state.harvest_reference_charge_confidence = "NONE"
            self.state.harvest_reference_charge_age_s = None
            self.state.harvest_reference_charge_valid = False
            self.state.harvest_reference_fallback_reason = ""
            self.state.harvest_profile_reserve_w = 0.0
            self.state.harvest_candidate_delta_w = 0.0
            self.state.harvest_candidate_absolute_w = 0.0
            self.state.harvest_input_time_skew_s = None
            self.state.harvest_network_target_w = 0.0
            self.state.harvest_total_available_charge_w = 0.0
            self.state.harvest_primary_share_target_w = 0.0
            self.state.harvest_zendure_share_target_w = 0.0
            self.state.harvest_export_capture_target_w = 0.0
            self.state.harvest_target_selected_by = "NOT_APPLICABLE"
            self.state.harvest_calculation_branch = "NOT_APPLICABLE"
            self.state.harvest_entry_min_export_w = 0.0
            self.state.harvest_command_path_eligible = False
            self.state.harvest_command_path_block_reason = ""

    def _update_harvest_capacity_diagnostics(self, cfg: Dict[str, Any]) -> None:
        with self.state.lock:
            primary_soc = self.state.sma_battery_soc
            primary_capacity = self.state.sma_battery_capacity_kwh
            zendure_soc = self.state.battery_soc
        zendure_capacity = self._cfg_float(cfg, "ZENDURE_BATTERY_CAPACITY_KWH", 0.0)
        if zendure_capacity <= 0:
            try:
                zendure_capacity_wh = cfg.get("ZENDURE_BATTERY_CAPACITY_WH")
                if zendure_capacity_wh not in (None, ""):
                    zendure_capacity = max(0.0, float(zendure_capacity_wh) / 1000.0)
            except Exception:
                zendure_capacity = 0.0
        max_soc = self._cfg_float(cfg, "MAX_SOC_PERCENT", 100.0)
        primary_remaining = None
        zendure_remaining = None
        try:
            if primary_capacity is not None and primary_soc is not None:
                primary_remaining = max(0.0, float(primary_capacity) * max(0.0, max_soc - float(primary_soc)) / 100.0)
        except Exception:
            primary_remaining = None
        try:
            if zendure_capacity > 0 and zendure_soc is not None:
                zendure_remaining = max(0.0, float(zendure_capacity) * max(0.0, max_soc - float(zendure_soc)) / 100.0)
        except Exception:
            zendure_remaining = None
        with self.state.lock:
            self.state.harvest_capacity_mode = str(cfg.get("HARVEST_CAPACITY_WEIGHTING_MODE", "diagnostic") or "diagnostic")
            self.state.primary_remaining_capacity_kwh = primary_remaining
            self.state.zendure_remaining_capacity_kwh = zendure_remaining

    def update_rest_surplus_harvest_state(self, cfg: Dict[str, Any], grid_power: float) -> None:
        """Update Entry/Stay diagnostics for Basis- and High-SOC Restüberschuss-Ernte."""
        thresholds = self._rest_surplus_thresholds(cfg)
        profile = thresholds.get("profile") or {}
        export_w = max(0.0, -float(grid_power or 0.0))
        self._update_harvest_capacity_diagnostics(cfg)
        with self.state.lock:
            second_power = float(self.state.sma_battery_display_power or 0.0)
            second_soc = self.state.sma_battery_soc
            second_valid = bool(self.state.second_battery_data_valid and self.state.second_battery_data_fresh)
            zendure_soc = self.state.battery_soc
            active = bool(self.state.rest_surplus_harvest_active)
            current_reason = self.state.rest_surplus_harvest_reason or "NONE"
        # RC17: the strategic total T is only valid after an independent
        # Zendure AC reference has been validated in the target calculation.
        # Never substitute last_input_power or another desired/read-back value.
        charge_pressure = 0.0

        with self.state.lock:
            self.state.second_battery_charge_pressure_w = round(charge_pressure, 1)
            self.state.second_battery_charge_saturation_threshold_w = float(thresholds["saturation"])
            self.state.rest_surplus_export_w = round(export_w, 1)
            self.state.harvest_primary_floor_w = float(thresholds["critical_floor"])
            self.state.harvest_primary_restart_w = float(thresholds["restart"])
            self.state.harvest_primary_near_limit_w = float(thresholds["saturation"])
            self.state.harvest_primary_target_share = float(profile.get("share", 0.50) or 0.50)
            self.state.rest_surplus_harvest_profile = str(profile.get("name", "default") or "default")
            self.state.harvest_target_semantics = "NOT_APPLICABLE"
            self.state.harvest_reference_charge_w = 0.0
            self.state.harvest_reference_charge_source = "NONE"
            self.state.harvest_reference_charge_confidence = "NONE"
            self.state.harvest_reference_charge_age_s = None
            self.state.harvest_reference_charge_valid = False
            self.state.harvest_reference_fallback_reason = ""
            self.state.harvest_profile_reserve_w = 0.0
            self.state.harvest_candidate_delta_w = 0.0
            self.state.harvest_candidate_absolute_w = 0.0
            self.state.harvest_input_time_skew_s = None
            self.state.harvest_network_target_w = 0.0
            self.state.harvest_total_available_charge_w = 0.0
            self.state.harvest_primary_share_target_w = 0.0
            self.state.harvest_zendure_share_target_w = 0.0
            self.state.harvest_export_capture_target_w = 0.0
            self.state.harvest_target_selected_by = "NOT_APPLICABLE"
            self.state.harvest_calculation_branch = "NOT_APPLICABLE"
            self.state.harvest_entry_min_export_w = 0.0
            self.state.harvest_command_path_eligible = False
            self.state.harvest_command_path_block_reason = ""

        if not bool(cfg.get("REST_SURPLUS_HARVEST_ENABLED", False)):
            self._reset_rest_surplus_harvest("DISABLED")
            return
        if thresholds["max_charge"] <= 0:
            self._reset_rest_surplus_harvest("MISSING_SECOND_BATTERY_MAX_CHARGE_POWER")
            return
        if not cross_charge_enabled(cfg):
            self._reset_rest_surplus_harvest("CROSS_CHARGE_DISABLED")
            return
        if not second_valid:
            self._reset_rest_surplus_harvest("SECOND_BATTERY_DATA_INVALID")
            return
        if zendure_soc is None or float(zendure_soc) >= float(cfg.get("MAX_SOC_PERCENT", 100)):
            self._reset_rest_surplus_harvest("MAX_SOC_LIMIT")
            return
        if not self.state.mqtt_connected and cfg.get("MQTT_DISCONNECTED_SAFE_STATE", False):
            self._reset_rest_surplus_harvest("MQTT_DISCONNECTED")
            return

        soc_ok = second_soc is not None and float(second_soc) >= float(thresholds["high_enter_soc"])
        soc_stay_ok = second_soc is not None and float(second_soc) >= float(thresholds["high_exit_soc"])
        full_soc = second_soc is not None and float(second_soc) >= float(thresholds["full_soc"])

        near_limit = bool(second_power >= thresholds["saturation"] and export_w >= thresholds["min_export"])
        high_soc_parallel = bool(
            thresholds["high_enabled"]
            and soc_ok
            and (export_w >= thresholds["high_min_export"] or second_power >= thresholds["restart"])
            and second_power >= thresholds["critical_floor"]
        )
        full_or_idle = bool(
            thresholds["high_enabled"]
            and full_soc
            and export_w >= thresholds["high_min_export"]
        )

        eligible_now = bool(near_limit or high_soc_parallel or full_or_idle)
        if full_or_idle:
            reason = "SMA_FULL_OR_IDLE"
        elif near_limit and high_soc_parallel:
            reason = "HIGH_SMA_SOC_SMA_NEAR_LIMIT"
        elif high_soc_parallel:
            reason = "HIGH_SMA_SOC"
        elif near_limit:
            reason = "SMA_NEAR_LIMIT"
        else:
            reason = "NONE"

        entry_confirm_s = thresholds["high_entry_confirm_s"] if reason in {"HIGH_SMA_SOC", "HIGH_SMA_SOC_SMA_NEAR_LIMIT", "SMA_FULL_OR_IDLE"} else thresholds["entry_confirm_s"]
        step_s = max(1.0, float(cfg.get("INTERVAL_SECONDS", 3) or 3))
        with self.state.lock:
            self.state.rest_surplus_harvest_eligible = eligible_now
            self.state.rest_surplus_harvest_reason = reason if eligible_now or active else "NONE"
            self.state.rest_surplus_harvest_block_reason = "" if eligible_now else ("SOC_BELOW_EXIT" if active and not soc_stay_ok else "NOT_ELIGIBLE")
            if eligible_now:
                self.state.rest_surplus_entry_progress_s = min(float(entry_confirm_s), float(self.state.rest_surplus_entry_progress_s or 0.0) + step_s)
                self.state.rest_surplus_hold_remaining_s = float(thresholds["high_hold_s"])
                if self.state.rest_surplus_entry_progress_s >= entry_confirm_s:
                    self.state.rest_surplus_harvest_active = True
                    self.state.rest_surplus_exit_reason = ""
                    self.state.rest_surplus_harvest_reason = reason
            elif active and soc_stay_ok and float(self.state.rest_surplus_hold_remaining_s or 0.0) > 0.0:
                self.state.rest_surplus_hold_remaining_s = max(0.0, float(self.state.rest_surplus_hold_remaining_s or 0.0) - step_s)
                self.state.rest_surplus_harvest_reason = current_reason if current_reason != "NONE" else "EXPORT_HOLD"
                self.state.rest_surplus_harvest_block_reason = "EXPORT_HOLD"
            elif active and not soc_stay_ok:
                self.state.rest_surplus_harvest_active = False
                self.state.rest_surplus_entry_progress_s = 0.0
                self.state.rest_surplus_hold_remaining_s = 0.0
                self.state.rest_surplus_exit_reason = "HIGH_SMA_SOC_EXIT"
                self.state.rest_surplus_harvest_reason = "NONE"
            elif active:
                # Aktiver High-SOC-Harvest bleibt diagnostisch im letzten Grund,
                # damit handle_charge die Primär-Floor/Share-Rückregelung ausführen
                # kann. Kein blindes Watt-Halten bei BELOW_FLOOR/RESTART_WAIT.
                if thresholds.get("high_enabled"):
                    self.state.rest_surplus_harvest_reason = current_reason if current_reason != "NONE" else "EXPORT_HOLD"
                    self.state.rest_surplus_harvest_block_reason = "PRIMARY_BAND_LIMIT"
                else:
                    self.state.rest_surplus_harvest_reason = current_reason
                    self.state.rest_surplus_harvest_block_reason = "NOT_ELIGIBLE"
            elif not active:
                self.state.rest_surplus_entry_progress_s = max(0.0, float(self.state.rest_surplus_entry_progress_s or 0.0) - step_s)

    def _rest_surplus_is_active(self) -> bool:
        with self.state.lock:
            return bool(self.state.rest_surplus_harvest_active)


    def _harvest_command_path_diagnostics(self) -> Tuple[bool, str]:
        """Return command-path readiness for diagnostics only.

        RC17 deliberately does not add a second control gate.  The existing
        command pipeline remains authoritative for publish/recovery decisions.
        """
        with self.state.lock:
            mqtt_connected = bool(self.state.mqtt_connected)
            command_path_valid = bool(self.state.mqtt_command_path_valid)
            command_path_reason = str(self.state.mqtt_command_path_validity_reason or "")
            flash_active = bool(self.state.zendure_flash_protection_active)
            flash_reason = str(self.state.zendure_flash_protection_reason or "")
            state_complete = bool(self.state.zendure_command_state_complete)
            state_reason = str(self.state.zendure_command_state_reason or "")
            gate_state = str(self.state.command_state_gate_state or "")

        if not mqtt_connected:
            return False, "MQTT_DISCONNECTED"
        if not command_path_valid:
            return False, command_path_reason or "MQTT_COMMAND_PATH_INVALID"
        if not flash_active:
            return False, flash_reason or "FLASH_PROTECTION_NOT_CONFIRMED"
        if not state_complete:
            return False, state_reason or "COMMAND_STATE_INCOMPLETE"
        if gate_state not in {"", COMMAND_GATE_READY}:
            return False, gate_state
        return True, ""

    def _harvest_physical_reference(self, cfg: Dict[str, Any], now: float) -> Dict[str, Any]:
        """Validate the independent Zendure AC grid-port observation.

        The returned charge value is physical evidence only.  Desired target,
        command read-back, pack power, off-grid power and SMA power are never
        accepted as substitutes.
        """
        evidence_max_age_s = 15.0
        with self.state.lock:
            grid_valid = bool(self.state.grid_power_valid)
            grid_epoch = self.state.last_shelly_update_epoch
            obs_epoch = self.state.zendure_power_observation_updated_epoch
            obs_signed = self.state.zendure_power_observation_signed_w
            obs_direction = str(self.state.zendure_power_observation_direction or "UNKNOWN").upper()
            obs_confidence = str(self.state.zendure_power_observation_confidence or "NONE").upper()
            grid_input_epoch = self.state.actual_zendure_grid_input_update_epoch
            output_home_epoch = self.state.actual_zendure_output_home_update_epoch

        reference_age_s = max(0.0, now - float(obs_epoch)) if obs_epoch is not None else None
        input_time_skew_s = (
            abs(float(grid_epoch) - float(obs_epoch))
            if grid_epoch is not None and obs_epoch is not None else None
        )
        grid_stale_timeout_s = max(1.0, float(
            cfg.get(
                "SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS"
                if str(cfg.get("GRID_METER_SOURCE", "shelly_http")) == "sma_energy_meter_udp"
                else "SHELLY_STALE_TIMEOUT_SECONDS",
                15,
            ) or 15
        ))
        grid_age_s = max(0.0, now - float(grid_epoch)) if grid_epoch is not None else None

        result = {
            "valid": False,
            "charge_w": 0.0,
            "source": "NONE",
            "confidence": "NONE",
            "age_s": reference_age_s,
            "fallback_reason": "",
            "input_time_skew_s": input_time_skew_s,
        }

        if not grid_valid or grid_epoch is None or grid_age_s is None or grid_age_s > grid_stale_timeout_s:
            result["fallback_reason"] = "GRID_SOURCE_INVALID"
        elif obs_epoch is None:
            result["fallback_reason"] = "REFERENCE_VALUE_MISSING"
        elif reference_age_s is None or reference_age_s > evidence_max_age_s:
            result["fallback_reason"] = "REFERENCE_STALE"
        elif input_time_skew_s is None or input_time_skew_s > evidence_max_age_s:
            result["fallback_reason"] = "INPUT_TIME_SKEW"
        elif obs_direction == "CONFLICT":
            result["fallback_reason"] = "REFERENCE_CONFLICT"
        elif obs_direction == "DISCHARGE":
            result["fallback_reason"] = "REFERENCE_DISCHARGE"
        elif obs_direction == "UNKNOWN":
            result["fallback_reason"] = "REFERENCE_UNKNOWN"
        elif obs_signed is None:
            result["fallback_reason"] = "REFERENCE_VALUE_MISSING"
        elif obs_direction == "CHARGE" and obs_confidence == "HIGH" and float(obs_signed) > 0:
            result.update({
                "valid": True,
                "charge_w": float(obs_signed),
                "source": "ZENDURE_GRID_PORT_OBSERVATION",
                "confidence": "HIGH",
            })
        elif obs_direction == "NEUTRAL" and obs_confidence == "MEDIUM":
            grid_input_fresh = (
                grid_input_epoch is not None
                and (now - float(grid_input_epoch)) <= evidence_max_age_s
            )
            output_home_fresh = (
                output_home_epoch is not None
                and (now - float(output_home_epoch)) <= evidence_max_age_s
            )
            if grid_input_fresh and output_home_fresh:
                result.update({
                    "valid": True,
                    "charge_w": 0.0,
                    "source": "ZENDURE_GRID_PORT_NEUTRAL",
                    "confidence": "MEDIUM",
                })
            else:
                result["fallback_reason"] = "REFERENCE_VALUE_MISSING"
        else:
            result["fallback_reason"] = "REFERENCE_UNKNOWN"
        return result

    def _rest_surplus_charge_pressure_target(self, cfg: Dict[str, Any], grid_power: float, last_input: int) -> Dict[str, Any]:
        """Return the RC17 Harvest target with separated share/capture diagnostics."""
        thresholds = self._rest_surplus_thresholds(cfg)
        profile = thresholds.get("profile") or {}
        export_w = max(0.0, -float(grid_power or 0.0))
        now = time.time()

        with self.state.lock:
            second_power = float(self.state.sma_battery_display_power or 0.0)
            reason = str(self.state.rest_surplus_harvest_reason or "NONE")
            effective_export = float(self.state.effective_export_power or 0.0)

        reference = self._harvest_physical_reference(cfg, now)
        command_path_eligible, command_path_block_reason = self._harvest_command_path_diagnostics()

        target_semantics = "NOT_APPLICABLE"
        target_selected_by = "NOT_APPLICABLE"
        calculation_branch = reason if reason in {
            "SMA_NEAR_LIMIT", "HIGH_SMA_SOC", "HIGH_SMA_SOC_SMA_NEAR_LIMIT",
            "SMA_FULL_OR_IDLE"
        } else ("EXPORT_HOLD_EXPORT_CAPTURE" if reason == "EXPORT_HOLD" else "NOT_APPLICABLE")
        limiter = ""
        fallback_reason = str(reference.get("fallback_reason") or "")
        reference_valid = bool(reference.get("valid"))
        reference_charge_w = float(reference.get("charge_w") or 0.0)
        reference_source = str(reference.get("source") or "NONE")
        reference_confidence = str(reference.get("confidence") or "NONE")
        reference_age_s = reference.get("age_s")
        input_time_skew_s = reference.get("input_time_skew_s")

        share = max(0.0, min(1.0, float(profile.get("share", 0.50) or 0.50)))
        floor_w = float(thresholds.get("critical_floor", 0) or 0)
        restart_w = float(thresholds.get("restart", 0) or 0)
        sma_max_w = float(thresholds.get("max_charge", 0) or 0)
        profile_share_unclamped_w = 0.0
        primary_share_unclamped_w = 0.0
        primary_share_target_w = 0.0
        zendure_share_target_w = 0.0
        export_capture_target_w = 0.0
        total_available_charge_w = 0.0
        candidate_absolute_w = 0.0
        candidate_delta_w = export_w

        if reference_valid:
            sma_charge_w = max(0.0, second_power)
            total_available_charge_w = sma_charge_w + reference_charge_w + export_w
            export_capture_target_w = reference_charge_w + export_w

            if reason in {"HIGH_SMA_SOC", "HIGH_SMA_SOC_SMA_NEAR_LIMIT"}:
                profile_share_unclamped_w = share * total_available_charge_w
                primary_share_unclamped_w = max(floor_w, profile_share_unclamped_w)
                primary_share_target_w = min(sma_max_w, primary_share_unclamped_w)
                zendure_share_target_w = max(0.0, total_available_charge_w - primary_share_target_w)
                raw_candidate = max(zendure_share_target_w, export_capture_target_w)
                target_semantics = "ABSOLUTE_SHARE_OR_EXPORT_CAPTURE"
                if abs(zendure_share_target_w - export_capture_target_w) < 0.5:
                    target_selected_by = "BOTH_EQUAL"
                elif zendure_share_target_w > export_capture_target_w:
                    target_selected_by = "STRATEGIC_SHARE"
                else:
                    target_selected_by = "EXPORT_CAPTURE"
                if second_power < floor_w and second_power >= 0:
                    limiter = "PRIMARY_FLOOR_LIMIT"
                elif primary_share_target_w > floor_w:
                    limiter = "PRIMARY_SHARE_LIMIT"
                if reason == "HIGH_SMA_SOC" and restart_w > 0 and second_power < restart_w:
                    limiter = limiter or "PRIMARY_RESTART_WAIT"
            elif reason in {"SMA_NEAR_LIMIT", "SMA_FULL_OR_IDLE", "EXPORT_HOLD"}:
                raw_candidate = export_capture_target_w
                target_semantics = "ABSOLUTE_EXPORT_CAPTURE"
                target_selected_by = "EXPORT_CAPTURE"
                limiter = "EXPORT_CAPTURE"
            else:
                # Unknown/stale origin reason: keep recovery possible without
                # reusing a desired/read-back value as physical evidence.
                raw_candidate = export_capture_target_w
                target_semantics = "ABSOLUTE_EXPORT_CAPTURE"
                target_selected_by = "EXPORT_CAPTURE"
                calculation_branch = "EXPORT_HOLD_EXPORT_CAPTURE"
                limiter = "EXPORT_CAPTURE"

            candidate_absolute_w = export_capture_target_w
        else:
            raw_candidate = float(last_input or 0) + effective_export * float(cfg.get("CONTROL_GAIN", 0.30) or 0.30)
            target_semantics = "INCREMENTAL_FALLBACK"
            target_selected_by = "INCREMENTAL_FALLBACK"
            calculation_branch = "INCREMENTAL_FALLBACK"
            limiter = "INCREMENTAL_FALLBACK"
            fallback_reason = fallback_reason or "INCREMENTAL_FALLBACK"

        candidate = max(0, int(round(raw_candidate)))
        with self.state.lock:
            self.state.second_battery_charge_pressure_w = round(total_available_charge_w, 1)
            self.state.harvest_primary_required_w = round(primary_share_target_w, 1)
            self.state.harvest_primary_share_reserve_w = round(profile_share_unclamped_w, 1)
            self.state.harvest_candidate_raw_w = round(max(0.0, raw_candidate), 1)
            self.state.harvest_candidate_after_primary_w = float(candidate)
            self.state.harvest_target_semantics = target_semantics
            self.state.harvest_reference_charge_w = round(reference_charge_w, 1)
            self.state.harvest_reference_charge_source = reference_source
            self.state.harvest_reference_charge_confidence = reference_confidence
            self.state.harvest_reference_charge_age_s = reference_age_s
            self.state.harvest_reference_charge_valid = reference_valid
            self.state.harvest_reference_fallback_reason = fallback_reason
            self.state.harvest_profile_reserve_w = 0.0
            self.state.harvest_candidate_delta_w = round(candidate_delta_w, 1)
            self.state.harvest_candidate_absolute_w = round(candidate_absolute_w, 1)
            self.state.harvest_input_time_skew_s = input_time_skew_s
            self.state.harvest_limiter_reason = limiter
            self.state.harvest_network_target_w = 0.0
            self.state.harvest_total_available_charge_w = round(total_available_charge_w, 1)
            self.state.harvest_primary_share_target_w = round(primary_share_target_w, 1)
            self.state.harvest_zendure_share_target_w = round(zendure_share_target_w, 1)
            self.state.harvest_export_capture_target_w = round(export_capture_target_w, 1)
            self.state.harvest_target_selected_by = target_selected_by
            self.state.harvest_calculation_branch = calculation_branch
            self.state.harvest_entry_min_export_w = float(
                thresholds.get("high_min_export")
                if reason in {"HIGH_SMA_SOC", "HIGH_SMA_SOC_SMA_NEAR_LIMIT", "SMA_FULL_OR_IDLE"}
                else thresholds.get("min_export", 0)
            )
            self.state.harvest_command_path_eligible = command_path_eligible
            self.state.harvest_command_path_block_reason = command_path_block_reason
        return {
            "target": candidate,
            "reason": reason,
            "charge_pressure_w": total_available_charge_w,
            "primary_required_w": primary_share_target_w,
            "limiter": limiter,
            "target_semantics": target_semantics,
            "target_selected_by": target_selected_by,
            "reference_valid": reference_valid,
            "fallback_reason": fallback_reason,
        }

    def _rest_surplus_should_reduce_in_hold(self, cfg: Dict[str, Any]) -> bool:
        if not self._rest_surplus_is_active():
            return False
        thresholds = self._rest_surplus_thresholds(cfg)
        if thresholds["critical_floor"] <= 0:
            return False
        with self.state.lock:
            second_power = float(self.state.sma_battery_display_power or 0.0)
            last_input = int(self.state.last_input_power or 0)
        return last_input > 0 and second_power < thresholds["critical_floor"]

    def safe_state(self, reason: str) -> None:
        self._reset_rest_surplus_harvest("SAFE_STATE")
        with self.state.lock:
            neutral_mode = "Output mode" if self.state.last_output_power > 0 else ("Input mode" if self.state.last_input_power > 0 else self._last_non_neutral_ac_mode)
        self._publish_neutralization(f"SAFE_STATE:{reason}", ac_mode=neutral_mode)
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

    def stop_hold(self, reason: str, technical_path: str = "MANUAL -> STOP_HOLD", action: str = "STOP_HOLD -> 0 W") -> None:
        with self.state.lock:
            neutral_mode = "Output mode" if self.state.last_output_power > 0 else ("Input mode" if self.state.last_input_power > 0 else self._last_non_neutral_ac_mode)

        self._publish_neutralization(f"STOP_HOLD:{reason}", ac_mode=neutral_mode)

        with self.state.lock:
            self.state.last_output_power = 0
            self.state.last_input_power = 0
            self.state.current_target_power = 0
            self.state.last_target_before_smoothing = 0
            self.state.last_target_after_smoothing = 0
            self.state.last_target_after_ramp = 0
            self.state.control_reason = reason
            self.state.technical_control_path = technical_path
            self.state.last_control_action = action

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

        applied_signed = self._publish_signed_target(-target, reason="MANUAL_FIXED_DISCHARGE")
        target = max(0, -int(applied_signed))

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

        applied_signed = self._publish_signed_target(target, reason="MANUAL_FIXED_CHARGE")
        target = max(0, int(applied_signed))

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

    def handle_deadband(self, cfg: Optional[Dict[str, Any]] = None) -> None:
        self.state.add_limiter("DEADBAND")
        if cfg is not None and self._rest_surplus_should_reduce_in_hold(cfg):
            self.ramp_down_charge(cfg, "Restüberschuss-Ernte: Primärspeicher-Ladung unter kritischem Bereich, Ladeziel wird reduziert")
            return
        with self.state.lock:
            if self.state.last_input_power > 0 and self.state.last_output_power <= 0:
                signed_target = int(self.state.last_input_power)
            elif self.state.last_output_power > 0 and self.state.last_input_power <= 0:
                signed_target = -int(self.state.last_output_power)
            else:
                signed_target = 0

        correction = self._apply_symmetric_cross_charge_limit(cfg or {}, signed_target) if cfg is not None else {"target": signed_target, "active": False}
        final_signed = int(correction.get("target", signed_target))
        if correction.get("active") and final_signed != signed_target:
            final_signed = self._publish_signed_target(final_signed, force_zero=(final_signed == 0), reason=("CROSS_CHARGE_NEUTRALIZATION" if final_signed == 0 else "DEADBAND_CROSS_CHARGE"))
            reason = correction.get("reason") or "Cross-Charge-Schutz aktiv"
            path = "GRID -> DEADBAND -> CROSS_CHARGE -> HOLD_POWER"
            self._startup_deadband_neutralized = True
        elif final_signed == 0 and not self._startup_deadband_neutralized:
            # RC8 targeted restart guard: one forced neutral 0/0 command in AUTO
            # deadband after service start.  This is deliberately cheap and does
            # not add recurring health checks to the live cycle.
            self._publish_signed_target(0, force_zero=True, reason="STARTUP_DEADBAND_NEUTRALIZATION")
            reason = "Innerhalb Totzone -> Startzustand neutralisiert"
            path = "GRID -> DEADBAND -> STARTUP_NEUTRALIZE -> HOLD_POWER"
            self._startup_deadband_neutralized = True
        else:
            reason = "Innerhalb Totzone -> Leistung halten"
            path = "GRID -> DEADBAND -> HOLD_POWER"

        with self.state.lock:
            self.state.last_input_power = max(0, final_signed)
            self.state.last_output_power = max(0, -final_signed)
            self.state.current_target_power = max(self.state.last_output_power, self.state.last_input_power)
            self.state.last_target_after_ramp = self.state.current_target_power
            self.state.control_reason = reason
            self.state.technical_control_path = path
            self.state.last_control_action = f"HOLD -> {final_signed} W"
        self.state.set_mode("HOLD")

    def _optional_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        try:
            return int(float(value))
        except Exception:
            return None

    def _effective_night_stop_soc(self, cfg: Dict[str, Any]) -> Optional[int]:
        min_soc = int(cfg["MIN_SOC_PERCENT"])
        configured_stop_soc = self._optional_int(cfg.get("NIGHT_DISCHARGE_STOP_SOC_PERCENT"))
        return max(min_soc, configured_stop_soc) if configured_stop_soc is not None else None

    def night_reserve_soc_reached(self, cfg: Dict[str, Any]) -> bool:
        with self.state.lock:
            soc = self.state.battery_soc
        effective_stop_soc = self._effective_night_stop_soc(cfg)
        with self.state.lock:
            self.state.night_discharge_stop_soc_percent = effective_stop_soc
        if soc is None:
            return False
        return effective_stop_soc is not None and soc <= effective_stop_soc

    def neutralize_ended_night_discharge_if_needed(self) -> bool:
        """Neutralize a fixed night-discharge target when the night window ends.

        The fixed night-discharge command is an explicit output limit. If the
        time window ends while this command is still the effective command, it
        must be cleared once so HOLD/deadband cannot keep the old discharge
        target alive. After neutralization the AUTO path may continue normally
        in the same cycle and issue a new command if grid conditions require it.
        """
        with self.state.lock:
            previous_mode = self.state.current_mode
            previous_path = self.state.technical_control_path
            previous_output = self.state.last_output_power
        if previous_mode != "NIGHT_DISCHARGE" and previous_path != "NIGHT_MODE -> OUTPUT":
            return False
        if int(previous_output or 0) <= 0:
            return False

        self._publish_neutralization("NIGHT_WINDOW_ENDED", ac_mode="Output mode")
        with self.state.lock:
            self.state.last_input_power = 0
            self.state.last_output_power = 0
            self.state.current_target_power = 0
            self.state.last_target_before_smoothing = 0
            self.state.last_target_after_smoothing = 0
            self.state.last_target_after_ramp = 0
            self.state.control_reason = "Nachtfenster beendet: feste Nachtentladung neutralisiert"
            self.state.technical_control_path = "NIGHT_MODE -> WINDOW_ENDED -> NEUTRALIZED"
            self.state.last_control_action = "NIGHT_WINDOW_ENDED -> NEUTRALIZE_FIXED_NIGHT_DISCHARGE"
            self.state.night_discharge_stop_reason = "NIGHT_WINDOW_ENDED"
        self.state.set_mode("HOLD")
        return True

    def pause_fixed_night_discharge_for_reserve_soc(self, cfg: Dict[str, Any]) -> bool:
        with self.state.lock:
            soc = self.state.battery_soc
            previous_mode = self.state.current_mode
            previous_path = self.state.technical_control_path
        min_soc = int(cfg["MIN_SOC_PERCENT"])
        effective_stop_soc = self._effective_night_stop_soc(cfg)
        with self.state.lock:
            self.state.night_discharge_stop_soc_percent = effective_stop_soc

        if soc is None or soc <= min_soc:
            self.state.add_limiter("MIN_SOC")
            self.safe_state("Nachtmodus blockiert: Zendure SOC zu niedrig")
            return False

        self.state.add_limiter("NIGHT_RESERVE_SOC")
        with self.state.lock:
            self.state.night_discharge_stop_reason = "NIGHT_RESERVE_SOC"

        # Falls unmittelbar zuvor die feste Nachtentladung aktiv war, muss diese
        # einmalig auf 0 W gesetzt werden. Danach läuft der normale AUTO-Zweig weiter
        # und darf bei realem Netzbezug wieder geregelt entladen. In Folgezyklen darf
        # eine bereits laufende AUTO-Entladung nicht wieder auf 0 W zurückgesetzt werden.
        if previous_mode == "NIGHT_DISCHARGE" or previous_path == "NIGHT_MODE -> OUTPUT":
            self._publish_neutralization("NIGHT_RESERVE_SOC", ac_mode="Output mode")
            with self.state.lock:
                self.state.last_input_power = 0
                self.state.last_output_power = 0
                self.state.current_target_power = 0
                self.state.last_target_before_smoothing = 0
                self.state.last_target_after_smoothing = 0
                self.state.last_target_after_ramp = 0
                self.state.control_reason = f"Feste Nachtentladung pausiert: Reserve-SOC {effective_stop_soc} % erreicht; AUTO-Regelung bleibt aktiv"
                self.state.technical_control_path = "NIGHT_MODE -> RESERVE_SOC -> AUTO"
                self.state.last_control_action = "NIGHT_RESERVE_SOC -> PAUSE_FIXED_NIGHT_DISCHARGE"
            self.state.set_mode("HOLD")

        return True

    def handle_night_mode(self, cfg: Dict[str, Any]) -> None:
        with self.state.lock:
            soc = self.state.battery_soc
        min_soc = int(cfg["MIN_SOC_PERCENT"])
        effective_stop_soc = self._effective_night_stop_soc(cfg)
        with self.state.lock:
            self.state.night_discharge_stop_soc_percent = effective_stop_soc

        if soc is None or soc <= min_soc:
            self.state.add_limiter("MIN_SOC")
            self.safe_state("Nachtmodus blockiert: Zendure SOC zu niedrig")
            return

        target = int(cfg["NIGHT_DISCHARGE_POWER_W"])
        applied_signed = self._publish_signed_target(-target, reason="NIGHT_DISCHARGE")
        target = max(0, -int(applied_signed))
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
            self.state.night_discharge_stop_reason = "none"
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
            self.handle_deadband(cfg)
            return

        raw_target = last_output + int(grid_power * cfg.get("CONTROL_GAIN", 0.30))
        target = max(0, min(raw_target, int(cfg["MAX_DISCHARGE_POWER_W"])))
        target_smoothed = self.smooth_transition(last_output, target, cfg)
        target_ramped = self.limit_power_step(last_output, target_smoothed, cfg)

        signed_before_cross = -int(target_ramped)
        correction = self._apply_symmetric_cross_charge_limit(cfg, signed_before_cross)
        signed_final = int(correction.get("target", signed_before_cross))
        final_output = max(0, -signed_final)

        signed_final = self._publish_signed_target(signed_final, force_zero=(signed_final == 0 and correction.get("active")), reason=("CROSS_CHARGE_NEUTRALIZATION" if signed_final == 0 and correction.get("active") else "AUTO_DISCHARGE"))
        final_output = max(0, -signed_final)

        with self.state.lock:
            self.state.last_input_power = max(0, signed_final)
            self.state.last_output_power = final_output
            self.state.current_target_power = max(self.state.last_input_power, self.state.last_output_power)
            self.state.last_target_before_smoothing = raw_target
            self.state.last_target_after_smoothing = target_smoothed
            self.state.last_target_after_ramp = self.state.current_target_power
            self.state.control_reason = correction.get("reason") if correction.get("active") else "Netzbezug erkannt -> Zendure entlädt"
            self.state.technical_control_path = "GRID -> CROSS_CHARGE -> DISCHARGE_CONTROL -> OUTPUT" if correction.get("active") else "GRID -> DISCHARGE_CONTROL -> OUTPUT"
            self.state.last_control_action = f"DISCHARGE -> {signed_final} W"
        self.state.set_mode("HOLD" if signed_final == 0 and correction.get("active") else "DISCHARGE")

        if cfg.get("LOG_CONTROL", False):
            self.log(f"[CTRL] Entladen: raw={raw_target} smooth={target_smoothed} ramp={target_ramped} final={signed_final}")

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

        harvest_active = self._rest_surplus_is_active()
        thresholds = self._rest_surplus_thresholds(cfg)
        export_w = max(0.0, -float(grid_power or 0.0))
        with self.state.lock:
            second_power = float(self.state.sma_battery_display_power or 0.0)
        harvest_near_saturation = bool(harvest_active and second_power >= thresholds.get("saturation", 0) and export_w > 0)

        if not harvest_active and effective < cfg.get("MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W", 150):
            self.state.add_limiter("LOW_EFFECTIVE_SURPLUS")
            self.ramp_down_charge(cfg, "Keine sichere PV-Überschussladung nach Zusatzbatterie-/Cross-Charge-Abzug")
            return

        if harvest_active:
            self.state.add_limiter("REST_SURPLUS_HARVEST")
            harvest_target = self._rest_surplus_charge_pressure_target(cfg, grid_power, int(last_input or 0))
            harvest_reason = str(harvest_target.get("reason") or "NONE")
            if harvest_reason in {"SMA_NEAR_LIMIT", "HIGH_SMA_SOC", "HIGH_SMA_SOC_SMA_NEAR_LIMIT", "SMA_FULL_OR_IDLE", "EXPORT_HOLD"}:
                raw_target = int(harvest_target.get("target", 0))
                if raw_target <= 0 and export_w >= thresholds.get("min_export", 80):
                    # RC17 latch recovery remains branch-correct.  With a valid
                    # physical reference, the helper already returned C+E or
                    # max(share, C+E).  With uncertain evidence it returned the
                    # incremental fallback.  Never replace that by naked E when
                    # C may already be positive.
                    raw_target = int(harvest_target.get("target", 0))
                    with self.state.lock:
                        self.state.harvest_limiter_reason = "LATCH_RECOVERY"
                semantics = str(harvest_target.get("target_semantics") or "")
                selected = str(harvest_target.get("target_selected_by") or "")
                if semantics == "INCREMENTAL_FALLBACK":
                    control_reason = (
                        f"Restüberschuss-Ernte: {harvest_reason} mit inkrementellem AUTO-Fallback "
                        f"({harvest_target.get('fallback_reason') or 'Referenz unsicher'})"
                    )
                else:
                    control_reason = (
                        f"Restüberschuss-Ernte: {harvest_reason}, 0-W-Netzziel, "
                        f"Auswahl {selected or 'EXPORT_CAPTURE'}"
                    )
            elif harvest_near_saturation:
                # Defensive compatibility path; normally SMA_NEAR_LIMIT is now
                # handled by the unified physical-reference calculation above.
                raw_target = int(harvest_target.get("target", 0))
                control_reason = "Restüberschuss-Ernte: Primärspeicher nahe Ladegrenze, 0-W-Netzziel"
            else:
                # RC1: kein blindes 0-W-Halten mehr, wenn echter Export im aktiven
                # Harvest-State vorhanden ist. Ohne gültigen High-SOC-/Near-Limit-
                # Grund darf normale AUTO-Exportregelung wieder entscheiden.
                if export_w >= thresholds.get("min_export", 80):
                    raw_target = last_input + int(effective * cfg.get("CONTROL_GAIN", 0.30))
                    with self.state.lock:
                        self.state.rest_surplus_exit_reason = "LATCH_RECOVERY_TO_AUTO_GRID_EXPORT"
                        self.state.rest_surplus_harvest_active = False
                        self.state.rest_surplus_harvest_reason = "LATCH_RECOVERY"
                    control_reason = "Restüberschuss-Ernte: Latch-Recovery, AUTO_GRID_EXPORT übernimmt"
                else:
                    raw_target = last_input
                    control_reason = "Restüberschuss-Ernte: Ladeziel wird gehalten; kein bestätigter Export-/High-SOC-Grund"
        else:
            raw_target = last_input + int(effective * cfg.get("CONTROL_GAIN", 0.30))
            control_reason = "PV-Überschuss erkannt -> Zendure lädt"
        target = max(0, min(raw_target, int(cfg["MAX_CHARGE_POWER_W"])))
        target_smoothed = self.smooth_transition(last_input, target, cfg)
        target_ramped = self.limit_power_step(last_input, target_smoothed, cfg)

        signed_before_cross = int(target_ramped)
        correction = self._apply_symmetric_cross_charge_limit(cfg, signed_before_cross)
        signed_final = int(correction.get("target", signed_before_cross))
        final_input = max(0, signed_final)

        signed_final = self._publish_signed_target(signed_final, force_zero=(signed_final == 0 and correction.get("active")), reason=("CROSS_CHARGE_NEUTRALIZATION" if signed_final == 0 and correction.get("active") else "AUTO_CHARGE"))
        final_input = max(0, signed_final)

        with self.state.lock:
            self.state.last_output_power = max(0, -signed_final)
            self.state.last_input_power = final_input
            self.state.current_target_power = max(self.state.last_input_power, self.state.last_output_power)
            self.state.last_target_before_smoothing = raw_target
            self.state.last_target_after_smoothing = target_smoothed
            self.state.last_target_after_ramp = self.state.current_target_power
            self.state.control_reason = correction.get("reason") if correction.get("active") else control_reason
            if correction.get("active"):
                self.state.technical_control_path = "GRID -> CROSS_CHARGE -> CHARGE_CONTROL -> INPUT"
            elif harvest_active:
                self.state.technical_control_path = "GRID -> REST_SURPLUS_HARVEST -> CHARGE_CONTROL -> INPUT"
            else:
                self.state.technical_control_path = "GRID -> CHARGE_CONTROL -> INPUT"
            self.state.last_control_action = f"CHARGE -> {signed_final} W"
        self.state.set_mode("HOLD" if signed_final == 0 and correction.get("active") else "CHARGE")

        if cfg.get("LOG_CONTROL", False):
            self.log(f"[CTRL] Laden: effective={effective} raw={raw_target} smooth={target_smoothed} ramp={target_ramped} final={signed_final}")

    def ramp_down_charge(self, cfg: Dict[str, Any], reason: str) -> None:
        with self.state.lock:
            last_input = self.state.last_input_power
        step = int(cfg.get("SMA_GUARD_RAMP_DOWN_W", cfg.get("MAX_POWER_STEP_W", 150)))
        target = max(0, last_input - step)
        target = max(0, self._publish_signed_target(target, force_zero=(target == 0), reason="CHARGE_RAMP_DOWN"))
        if self._rest_surplus_is_active():
            self.state.add_limiter("REST_SURPLUS_HARVEST")
            with self.state.lock:
                self.state.rest_surplus_exit_reason = "TARGET_ZERO" if target == 0 else "GRID_IMPORT_REDUCE"
                if target == 0:
                    self.state.rest_surplus_harvest_active = False
                    self.state.rest_surplus_entry_progress_s = 0.0
        with self.state.lock:
            self.state.last_output_power = 0
            self.state.last_input_power = target
            self.state.current_target_power = target
            self.state.last_target_before_smoothing = target
            self.state.last_target_after_smoothing = target
            self.state.last_target_after_ramp = target
            self.state.control_reason = reason
            self.state.technical_control_path = "GRID -> CHARGE_RAMP_DOWN"
            self.state.last_control_action = f"CHARGE_RAMP_DOWN -> {target} W"
        self.state.set_mode("HOLD" if target == 0 else "CHARGE_RAMP_DOWN")

    def ramp_down_discharge(self, cfg: Dict[str, Any], reason: str) -> None:
        with self.state.lock:
            last_output = self.state.last_output_power
        target = max(0, last_output - int(cfg.get("MAX_POWER_STEP_W", 150)))
        applied_signed = self._publish_signed_target(-target, force_zero=(target == 0), reason="DISCHARGE_RAMP_DOWN")
        target = max(0, -int(applied_signed))
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
            or "NIGHT_RESERVE_SOC" in active_limiters
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
            "REST_SURPLUS_HARVEST" in path
            or "CROSS_CHARGE" in path
            or "EVCC_STALE" in active_limiters
            or "SMA_DISCHARGE" in active_limiters
        ):
            require("second_battery")

        return required

    def update_charge_acceptance_diagnostic(self, cfg: Dict[str, Any]) -> None:
        target_w = max(0, int(self.state.last_input_power or 0))
        reference_w, _ = self._confirmed_charge_reference(cfg, target_w)
        result = classify_charge_acceptance(
            soc_percent=self.state.battery_soc,
            max_soc_percent=cfg.get("MAX_SOC_PERCENT", 100),
            target_charge_w=reference_w or target_w,
            actual_charge_w=self.state.zendure_battery_charge_power_w,
            grid_power_w=self.state.grid_power,
            min_effective_target_w=max(1, int(cfg.get("COMMAND_EFFECT_MIN_TARGET_W", 120) or 120)),
            export_threshold_w=max(80, int(cfg.get("DEADBAND_W", 80))),
        )
        with self.state.lock:
            self.state.charge_acceptance_state = result.get("state", "ok")
            self.state.charge_acceptance_reason = result.get("reason", "-")


    def _format_measurement_fallback_event(self, status: Dict[str, Any]) -> str:
        """Format a compact runtime-log line for measurement storage fallback events.

        This is operational logger diagnostics, intentionally kept out of the
        ZEC-MEASUREMENT-V3 row schema.
        """
        parts = [
            "[MEASUREMENT_LOG] fallback_to_sd",
            f"count={status.get('measurement_fallback_count_since_start', '')}",
            f"primary_path={status.get('measurement_primary_path', '')}",
            f"mountpoint={status.get('measurement_primary_mountpoint', '')}",
            f"exists={status.get('measurement_primary_exists', '')}",
            f"is_mount={status.get('measurement_primary_is_mount', '')}",
            f"writable={status.get('measurement_primary_writable', '')}",
            f"free_mb={status.get('measurement_primary_free_mb', '')}",
            f"failure_reason={status.get('measurement_primary_failure_reason', '')}",
            f"exception={status.get('measurement_primary_exception', '')}",
            f"fallback_path={status.get('measurement_log_path', '')}",
        ]
        return " ".join(str(part).replace("\n", " ") for part in parts)

    def finish_cycle(self, cfg: Dict[str, Any], loop_start: float) -> None:
        with self.state.lock:
            self.state.last_loop_duration_ms = round((time.time() - loop_start) * 1000.0, 3)
            self.state.last_limit_reason = ", ".join(self.state.active_limiters) if self.state.active_limiters else "none"
            path = self.state.technical_control_path
            mode = self.state.current_mode
            self.state.grid_power_used_for_control = path.startswith("GRID")
            self.state.effective_export_power_used_for_control = path.startswith("GRID") and (
                "CHARGE" in path or "CROSS_CHARGE" in path or "REST_SURPLUS_HARVEST" in path
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

        self._timed_phase("cycle_display_metrics_ms", self.update_cycle_display_metrics, cfg)
        required_sources = self.determine_cycle_required_sources(cfg)
        self.state.set_control_source_requirements(required_sources)
        self.state.update_data_validity_model(cfg)
        self._update_command_readback_diagnostics(cfg)
        self._update_late_effect_guard_state()
        self._timed_phase("charge_acceptance_diag_ms", self.update_charge_acceptance_diagnostic, cfg)
        self._timed_command_effect_phase(self.update_command_effect_monitor, cfg)
        self._timed_phase("graph_snapshot_ms", self.state.record_graph_point, int(cfg.get("GRAPH_HISTORY_LIMIT", 300)))
        try:
            last_row = self.state.snapshot()["graph_history"][-1]
            log_status = self._timed_phase("measurement_logging_ms", self.csv_logger.log, cfg, last_row)
            if log_status.get("measurement_fallback_event"):
                self.app_logger.log(cfg, self._format_measurement_fallback_event(log_status))
            self.state.set_measurement_log_status(log_status)
        except Exception as exc:
            self.state.set_error(f"Messdaten-Logging pausiert: {exc}")
            self.state.set_measurement_log_status({
                "measurement_log_status": "error",
                "measurement_log_status_reason": str(exc),
            })
