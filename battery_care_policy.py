# SPDX-License-Identifier: AGPL-3.0-or-later
"""Battery Care: side-effect-free policy and energy-balance primitives.

ZEC-BL-BATCARE-001, SPEC_FINAL 2026-10-25. These functions deliberately do
NOT send commands or bypass controller safety. Integration must go through
controller_logic's existing SmartMode/AC/limits/effect/resync owner.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum
from math import isfinite
from typing import Optional


class CareStage(str, Enum):
    OFF = "OFF"
    OUT_OF_SEASON = "OUT_OF_SEASON"
    RESERVE_PROTECTED = "RESERVE_PROTECTED"
    PV_PRIORITY = "PV_PRIORITY"
    GRID_WAITING = "GRID_WAITING"
    GRID_REQUESTED = "GRID_REQUESTED"
    EMERGENCY_REQUESTED = "EMERGENCY_REQUESTED"
    PAUSED = "PAUSED_DATA_OR_DEVICE"
    COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class CareConfig:
    enabled: bool = False
    season_start: Optional[str] = None
    season_end: Optional[str] = None
    reserve_soc: Optional[int] = None
    grid_trigger_soc: Optional[int] = None
    emergency_soc: Optional[int] = None
    grid_charge_cap_w: Optional[int] = None

    def validate(self, maximum_soc: int, maximum_charge_w: int) -> tuple[str, ...]:
        """No fallbacks for missing values; activation fails closed."""
        if not self.enabled:
            return ()
        issues = []
        if not valid_season_boundary(self.season_start) or not valid_season_boundary(self.season_end):
            issues.append("CARE_SEASON_REQUIRED")
        thresholds = (self.emergency_soc, self.grid_trigger_soc, self.reserve_soc)
        if any(not isinstance(x, int) or isinstance(x, bool) for x in thresholds):
            issues.append("CARE_SOC_REQUIRED")
        elif not (0 <= thresholds[0] < thresholds[1] < thresholds[2] <= maximum_soc
                  and thresholds[1] - thresholds[0] >= 2 and thresholds[2] - thresholds[1] >= 2):
            issues.append("CARE_SOC_ORDER_OR_HYSTERESIS")
        cap = self.grid_charge_cap_w
        if (not isinstance(cap, int) or isinstance(cap, bool) or
                cap <= 0 or cap > maximum_charge_w):
            issues.append("CARE_GRID_CAP_INVALID")
        return tuple(issues)


def valid_season_boundary(value: Optional[str]) -> bool:
    if not isinstance(value, str) or len(value) != 5 or value[2] != "-":
        return False
    try:
        mm, dd = value.split("-")
        if not (mm.isascii() and dd.isascii() and mm.isdecimal() and dd.isdecimal()):
            return False
        return date(2025, int(mm), int(dd)).strftime("%m-%d") == value
    except (ValueError, TypeError):
        return False


def in_care_season(today: date, start: Optional[str], end: Optional[str]) -> bool:
    """Inclusive cyclic MM-DD window, including leap days inside a window."""
    if not valid_season_boundary(start) or not valid_season_boundary(end):
        return False
    current = today.strftime("%m-%d")
    return (start <= current <= end) if start <= end else (current >= start or current <= end)


@dataclass(frozen=True)
class CareObservation:
    today: date
    soc: Optional[int]
    soc_fresh: bool
    soc_sample_id: Optional[str]
    monotonic_s: float
    manual_mode: str
    safety_ready: bool
    grid_fresh: bool = False
    grid_w: Optional[float] = None   # positive import, negative export
    zendure_power_fresh: bool = False
    zendure_power_w: Optional[float] = None  # positive charge
    primary_integrated: bool = False
    primary_power_fresh: bool = False
    primary_power_w: Optional[float] = None # positive charge
    primary_soc_fresh: bool = False
    primary_soc: Optional[int] = None
    primary_floor_fresh: bool = False
    primary_floor_soc: Optional[int] = None
    primary_floor_supported: bool = False


@dataclass(frozen=True)
class CareEpisode:
    active_level: int = 0  # 0 no grid episode; 2 regular; 3 emergency
    target_reserve_soc: Optional[int] = None
    last_soc_sample_id: Optional[str] = None
    confirmation_start_s: Optional[float] = None
    consecutive_low_samples: int = 0
    completed_sample_count: int = 0


@dataclass(frozen=True)
class CareDecision:
    stage: CareStage
    effective_discharge_floor: Optional[int]
    requested_charge_w: int
    pv_candidate_w: int
    allow_emergency_cross_charge_exception: bool
    reason: str
    episode: CareEpisode


def _fresh_number(value: Optional[float], fresh: bool) -> bool:
    return bool(fresh and value is not None and isinstance(value, (int, float))
                and not isinstance(value, bool) and isfinite(float(value)))


def care_pv_absolute_target(obs: CareObservation, max_charge_w: int) -> int:
    """Absolute PV redistribution, never add a baseline command a second time.

    Pp>0 charging primary, Pz>0 charging Zendure, G>0 import.
    Pp+Pz-G is an estimate, not evidence of independent PV production.
    """
    if not (_fresh_number(obs.grid_w, obs.grid_fresh) and
            _fresh_number(obs.zendure_power_w, obs.zendure_power_fresh)):
        return 0
    if obs.primary_integrated:
        if not _fresh_number(obs.primary_power_w, obs.primary_power_fresh):
            return 0
        if obs.primary_power_w < 0:  # do not transfer from discharging primary
            return 0
        primary_charge = max(0.0, obs.primary_power_w)
    else:
        primary_charge = 0.0
    if obs.zendure_power_w < 0:  # ambiguous/opposite actual direction
        return 0
    estimate = max(0., primary_charge + max(0., obs.zendure_power_w) - obs.grid_w)
    return int(min(max(0, max_charge_w), estimate))


def grid_stage_two_eligible(obs: CareObservation) -> bool:
    if not _fresh_number(obs.grid_w, obs.grid_fresh):
        return False
    if not obs.primary_integrated:
        return True
    if not _fresh_number(obs.primary_power_w, obs.primary_power_fresh):
        return False
    if obs.primary_power_w < -25:  # genuine primary discharge; not an economic gate for emergency
        return False
    if obs.primary_floor_supported:
        # A known Sunny-Island floor must not silently degrade to the generic
        # non-SMA neutral-window rule when the optional capability goes stale.
        return bool(obs.primary_floor_fresh and obs.primary_soc_fresh
                    and _fresh_number(obs.primary_soc, obs.primary_soc_fresh)
                    and _fresh_number(obs.primary_floor_soc, obs.primary_floor_fresh)
                    and obs.primary_soc <= obs.primary_floor_soc)
    # Other integrated topology: neutral (not demonstrably discharging).
    return abs(obs.primary_power_w) <= 25


def decide_care(config: CareConfig, obs: CareObservation, prev: CareEpisode,
                *, normal_min_soc: int, max_charge_w: int,
                regular_confirm_seconds: float = 3.0,
                maximum_soc: int = 100) -> CareDecision:
    """Return a requested policy intent, never proof of physical charging.

    Caller must apply device/command/hardware safety and power ramping. Manual
    STOP and fixed modes never receive an active Care charge target.
    """
    def done(stage: CareStage, reason: str, episode: CareEpisode = prev,
             floor: Optional[int] = None, watts: int = 0, pv: int = 0,
             exception: bool = False) -> CareDecision:
        return CareDecision(stage, floor, watts, pv, exception, reason, episode)

    if not config.enabled:
        return done(CareStage.OFF, "feature_disabled", CareEpisode())
    if config.validate(maximum_soc=maximum_soc, maximum_charge_w=max_charge_w):
        return done(CareStage.PAUSED, "invalid_care_configuration", CareEpisode())
    season = in_care_season(obs.today, config.season_start, config.season_end)
    # An already active emergency may finish after season end, never begin anew.
    if not season and prev.active_level != 3:
        return done(CareStage.OUT_OF_SEASON, "calendar_outside", CareEpisode())
    # A running episode keeps its original reserve despite a later change of
    # the configured R; reducing R must never silently complete a charge.
    episode_reserve = (prev.target_reserve_soc if prev.active_level in (2, 3)
                       and prev.target_reserve_soc is not None
                       else config.reserve_soc)
    floor = max(normal_min_soc, episode_reserve)
    if obs.manual_mode == "STOP_HOLD":
        return done(CareStage.PAUSED, "manual_stop", CareEpisode(), floor)
    if obs.manual_mode != "AUTO":
        return done(CareStage.PAUSED, "manual_mode_no_care_charge", CareEpisode(), floor)
    if not obs.safety_ready or not obs.soc_fresh or obs.soc is None or not obs.soc_sample_id:
        return done(CareStage.PAUSED, "missing_fresh_safety_or_soc", prev, floor)
    if not isfinite(obs.monotonic_s):
        return done(CareStage.PAUSED, "invalid_monotonic_time", prev, floor)

    distinct = obs.soc_sample_id != prev.last_soc_sample_id
    episode = prev
    if distinct:
        episode = replace(prev, last_soc_sample_id=obs.soc_sample_id)
    if obs.soc >= episode_reserve:
        count = prev.completed_sample_count + 1 if distinct else prev.completed_sample_count
        episode = replace(episode, completed_sample_count=count)
        # Avoid ending a previously requested grid charge after one SOC jump.
        if prev.active_level and count < 2:
            return done(CareStage.GRID_REQUESTED if prev.active_level == 2 else CareStage.EMERGENCY_REQUESTED,
                        "reserve_recovery_confirmation_pending", episode, floor,
                        min(config.grid_charge_cap_w, max_charge_w),
                        exception=prev.active_level == 3)
        return done(CareStage.COMPLETED, "reserve_recovered", CareEpisode(), floor)
    episode = replace(episode, completed_sample_count=0)
    if obs.soc <= config.emergency_soc or prev.active_level == 3:
        episode = replace(episode, active_level=3, target_reserve_soc=episode_reserve)
        return done(CareStage.EMERGENCY_REQUESTED, "emergency_low_soc", episode, floor,
                    min(config.grid_charge_cap_w, max_charge_w), exception=True)

    if prev.active_level == 2:
        if grid_stage_two_eligible(obs):
            return done(CareStage.GRID_REQUESTED, "regular_episode_latched", episode, floor,
                        min(config.grid_charge_cap_w, max_charge_w))
        return done(CareStage.GRID_WAITING, "primary_conditions_wait", episode, floor)

    if obs.soc <= config.grid_trigger_soc:
        if distinct:
            started = prev.confirmation_start_s if prev.confirmation_start_s is not None else obs.monotonic_s
            if obs.monotonic_s < started:
                started = obs.monotonic_s
                count = 1
            else:
                count = prev.consecutive_low_samples + 1
            episode = replace(episode, confirmation_start_s=started,
                              consecutive_low_samples=count)
        confirmed = bool(episode.consecutive_low_samples >= 2 and
                         episode.confirmation_start_s is not None and
                         obs.monotonic_s - episode.confirmation_start_s >= regular_confirm_seconds)
        if confirmed:
            episode = replace(episode, active_level=2,
                              target_reserve_soc=config.reserve_soc)
            if grid_stage_two_eligible(obs):
                return done(CareStage.GRID_REQUESTED, "regular_trigger_confirmed", episode, floor,
                            min(config.grid_charge_cap_w, max_charge_w))
            return done(CareStage.GRID_WAITING, "primary_conditions_wait", episode, floor)
    else:
        episode = replace(episode, confirmation_start_s=None, consecutive_low_samples=0)

    if not season:
        return done(CareStage.OUT_OF_SEASON, "emergency_window_ended", CareEpisode(), floor)
    if obs.soc < episode_reserve:
        if obs.grid_fresh and obs.zendure_power_fresh and obs.manual_mode == "AUTO":
            candidate = care_pv_absolute_target(obs, max_charge_w)
            if candidate > 0:
                return done(CareStage.PV_PRIORITY, "pv_reallocation_possible", episode, floor,
                            candidate, pv=candidate)
        return done(CareStage.RESERVE_PROTECTED, "waiting_for_usable_pv", episode, floor)
    return done(CareStage.RESERVE_PROTECTED, "reserve_protected", episode, floor)
