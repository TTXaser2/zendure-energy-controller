# SPDX-License-Identifier: AGPL-3.0-or-later
"""Source-age and AC-direction gate for ZEC Battery Care grid policy.

No commands, network reads or new sensor owner. All values come from the
existing controller read-only state, with independent timestamps and validity.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Optional
from battery_care_policy import CareObservation


@dataclass(frozen=True)
class GridInputs:
    today: date
    now_epoch: float
    monotonic_s: float
    manual_mode: str
    soc: Optional[int]
    soc_epoch: Optional[float]
    soc_timeout_s: float
    grid_w: Optional[float]
    grid_epoch: Optional[float]
    grid_valid: bool
    device_power_w: Optional[float]
    device_power_epoch: Optional[float]
    device_power_valid: bool
    device_power_direction: str
    command_ready: bool
    primary_integrated: bool
    primary_power_w: Optional[float] = None
    primary_soc: Optional[float] = None
    primary_epoch: Optional[float] = None
    primary_valid: bool = False
    primary_floor_supported: bool = False
    primary_floor_soc: Optional[float] = None
    primary_floor_epoch: Optional[float] = None
    primary_floor_valid: bool = False


def _valid_fresh(value: Optional[float], epoch: Optional[float],
                 *, now: float, timeout: float) -> bool:
    try:
        return bool(value is not None and epoch is not None
                    and not isinstance(value, bool)
                    and isfinite(float(value)) and isfinite(float(epoch))
                    and 0 <= now - float(epoch) <= timeout)
    except (ValueError, TypeError, OverflowError):
        return False


def observe_grid_policy(i: GridInputs) -> CareObservation:
    """Fail-closed on uncorrelated AC data; emergency still needs safe device.

    A primary floor capability that *exists but is stale* is distinguishable
    from a primary that simply has no such capability.
    """
    soc_fresh = _valid_fresh(i.soc, i.soc_epoch, now=i.now_epoch,
                             timeout=max(0., i.soc_timeout_s))
    grid_fresh = bool(i.grid_valid and _valid_fresh(
        i.grid_w, i.grid_epoch, now=i.now_epoch, timeout=15.0))
    device_fresh = bool(i.device_power_valid
                        and i.device_power_direction.upper() in
                        {'CHARGE', 'DISCHARGE', 'NEUTRAL'}
                        and _valid_fresh(i.device_power_w, i.device_power_epoch,
                                         now=i.now_epoch, timeout=15.0))
    primary_fresh = bool(i.primary_integrated and i.primary_valid
                         and _valid_fresh(i.primary_power_w, i.primary_epoch,
                                          now=i.now_epoch, timeout=15.0))
    primary_soc_fresh = bool(primary_fresh and i.primary_soc is not None
                             and isfinite(float(i.primary_soc)))
    floor_fresh = bool(i.primary_floor_supported and i.primary_floor_valid
                       and _valid_fresh(i.primary_floor_soc, i.primary_floor_epoch,
                                        now=i.now_epoch, timeout=30.0))
    return CareObservation(
        today=i.today, soc=int(i.soc) if soc_fresh else None,
        soc_fresh=soc_fresh,
        soc_sample_id=(f"SOC:{i.soc_epoch}" if soc_fresh else None),
        monotonic_s=i.monotonic_s, manual_mode=i.manual_mode,
        # An active grid request is not authorized on stale/ambiguous grid,
        # Zendure AC direction or command-state evidence.
        safety_ready=bool(i.command_ready and grid_fresh and device_fresh),
        grid_fresh=grid_fresh, grid_w=i.grid_w,
        zendure_power_fresh=device_fresh, zendure_power_w=i.device_power_w,
        primary_integrated=i.primary_integrated,
        primary_power_fresh=primary_fresh, primary_power_w=i.primary_power_w,
        primary_soc_fresh=primary_soc_fresh,
        primary_soc=(int(i.primary_soc) if primary_soc_fresh else None),
        primary_floor_fresh=floor_fresh,
        primary_floor_soc=(int(i.primary_floor_soc) if floor_fresh else None),
        primary_floor_supported=i.primary_floor_supported,
    )
