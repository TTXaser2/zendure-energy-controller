# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only 1-Hz status values, independent of control loop progression.

The sampling endpoints do not poll any external devices and never update the
controller state. They expose the newest measurements already received by the
respective background MQTT/Modbus/SMA receivers and their real sample ages.
"""
from __future__ import annotations

import time
import math
from typing import Any, Dict, Mapping, Optional


def _number(value: Any) -> Optional[float]:
    try:
        result = float(value) if value is not None else None
        return result if result is not None and math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _age(now: float, epoch: Any) -> Optional[float]:
    value = _number(epoch)
    if value is None or value <= 0 or value > now + 3.0:
        # Future/invalid device or wall timestamps cannot prove freshness.
        return None
    return round(max(0.0, now - value), 1)


def build_live_status(cfg: Mapping[str, Any], state: Any, *, sma_energy_meter_client: Any = None, shelly_sampler: Any = None) -> Dict[str, Any]:
    now = time.time()
    # Snapshot scalar telemetry with a SHORT state lock, no expensive DB or IO.
    with state.lock:
        grid_controller = _number(state.raw_grid_power)
        grid_controller_epoch = state.grid_power_sample_epoch
        primary_raw = _number(state.sma_battery_power)
        primary_source_profile = str(getattr(state, "primary_storage_source_profile", "") or "")
        primary_soc = state.sma_battery_soc
        primary_epoch = state.last_sma_battery_update_epoch
        zendure_power = _number(state.actual_zendure_system_signed_power)
        zendure_epoch = state.last_zendure_power_update_epoch
        zendure_soc = state.battery_soc
        soc_epoch = state.last_soc_update_epoch
        mode = str(state.current_mode or "")
        primary_enabled = bool(cfg.get("SECOND_BATTERY_INTEGRATION_ENABLED", False))
    meter_source = str(cfg.get("GRID_METER_SOURCE", "shelly_http") or "shelly_http")
    grid_epoch, grid_power, grid_observer = grid_controller_epoch, grid_controller, "controller_snapshot"
    if meter_source == "sma_energy_meter_udp" and sma_energy_meter_client is not None:
        try:
            reading = sma_energy_meter_client.snapshot()  # background RX only
            grid_epoch, grid_power, grid_observer = reading.last_received_epoch, reading.last_power_w, "sma_udp_receiver"
        except Exception:
            grid_epoch, grid_power, grid_observer = None, None, "sma_receiver_unavailable"
    elif meter_source == "shelly_http" and shelly_sampler is not None:
        try:
            reading = shelly_sampler.snapshot()
            grid_epoch, grid_power, grid_observer = reading.last_received_epoch, reading.last_power_w, "shelly_live_worker"
        except Exception:
            grid_epoch, grid_power, grid_observer = None, None, "shelly_worker_unavailable"
    grid_age = _age(now, grid_epoch)
    # Do not bypass the existing 30-kW physical plausibility protection when
    # reading the receiver directly (the old Speedwire parser is still pending).
    max_plausible = float(cfg.get("GRID_POWER_PLAUSIBILITY_MAX_ABS_W", 30000) or 30000)
    grid_power = _number(grid_power)
    grid_plausible = grid_power is not None and abs(grid_power) <= max_plausible
    grid_timeout = float(cfg.get("SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS", 15) if meter_source == "sma_energy_meter_udp" else cfg.get("SHELLY_STALE_TIMEOUT_SECONDS", 15))
    grid_fresh = bool(grid_plausible and grid_age is not None and grid_age <= grid_timeout)
    # Native Modbus is source-normalised as discharge-positive; display must be
    # CHARGE-positive, including when the main controller loop is in HOLD/NIGHT.
    sign = 1 if str(cfg.get("SECOND_BATTERY_SOURCE_PROFILE") or "") == "modbus_template" else cfg.get("SECOND_BATTERY_DISCHARGE_SIGN", cfg.get("EVCC_SMA_DISCHARGE_SIGN", 1))
    try:
        primary_power = _number(-float(sign) * primary_raw) if primary_raw is not None else None
    except (ValueError, TypeError):
        primary_power = None
    primary_age = _age(now, primary_epoch)
    primary_timeout = float(cfg.get("SECOND_BATTERY_STALE_TIMEOUT_SECONDS", cfg.get("EVCC_STALE_TIMEOUT_SECONDS", 30)) or 30)
    active_primary_profile = str(cfg.get("SECOND_BATTERY_SOURCE_PROFILE") or "evcc_standard")
    # Do not misattribute an older collector's sample to a newly selected
    # primary profile during live source migration.
    primary_source_matches = (not primary_source_profile or primary_source_profile == active_primary_profile)
    primary_fresh = bool(primary_enabled and primary_power is not None and primary_source_matches
                         and primary_age is not None and primary_age <= primary_timeout)
    zendure_age = _age(now, zendure_epoch)
    soc_age = _age(now, soc_epoch)
    zendure_power_fresh = bool(zendure_power is not None and zendure_age is not None
        and zendure_age <= float(cfg.get("ZENDURE_POWER_STALE_TIMEOUT_SECONDS", 15) or 15))
    zendure_soc_fresh = bool(_number(zendure_soc) is not None and soc_age is not None
        and soc_age <= float(cfg.get("SOC_STALE_TIMEOUT_SECONDS", 90) or 90))
    return {
        "server_epoch_ms": int(now * 1000), "controller_mode_observed": mode,
        "poll_interval_ms": 1000, "read_only": True,
        "grid": {
            "power_w": grid_power if grid_fresh else None,
            "last_value_w": grid_power,
            "sample_epoch": grid_epoch,
            "age_s": grid_age,
            "fresh": bool(grid_fresh), "valid": bool(grid_plausible),
            "plausible": bool(grid_plausible),
            "source": meter_source,
            "measurement_path": grid_observer,
            "controller_sample_age_s": _age(now, grid_controller_epoch),
        },
        "primary": {
            "present": primary_enabled,
            "power_w": primary_power if primary_fresh else None,
            "last_value_w": primary_power if primary_enabled else None,
            "soc_percent": _number(primary_soc) if primary_fresh else None,
            "age_s": primary_age if primary_enabled else None,
            "fresh": primary_fresh,
            "valid": bool(primary_fresh and _number(primary_soc) is not None),
            "source_matches_config": primary_source_matches,
            "measurement_path": str(cfg.get("SECOND_BATTERY_SOURCE_PROFILE") or "evcc_standard"),
            "max_charge_w": cfg.get("SECOND_BATTERY_MAX_CHARGE_POWER_W"),
            "max_discharge_w": cfg.get("SECOND_BATTERY_MAX_DISCHARGE_POWER_W"),
        },
        "zendure": {
            "power_w": zendure_power if zendure_power_fresh else None,
            "last_value_w": zendure_power,
            "age_s": zendure_age,
            "fresh": zendure_power_fresh,
            "valid": zendure_power is not None,
            "soc_percent": _number(zendure_soc) if zendure_soc_fresh else None,
            "soc_fresh": zendure_soc_fresh,
            "soc_age_s": soc_age,
            "max_charge_w": cfg.get("MAX_CHARGE_POWER_W"),
            "max_discharge_w": cfg.get("MAX_DISCHARGE_POWER_W"),
        },
    }
