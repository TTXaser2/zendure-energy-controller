# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pure Battery Care stage-1 PV allocator; no device/command authority.

The caller must provide independently measured AC values and the separate,
ordinary AUTO baseline. In particular, *neither* last published Care target
nor Fast Capture overlay is a permissible baseline. Integration is permitted
only through the controller's existing safety and command lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from typing import Optional


@dataclass(frozen=True)
class PvSnapshot:
    monotonic_s: float
    grid_w: Optional[float]
    grid_sample: Optional[str]
    zendure_signed_w: Optional[float]
    zendure_sample: Optional[str]
    primary_integrated: bool
    primary_signed_w: Optional[float] = None
    primary_sample: Optional[str] = None
    grid_fresh: bool = False
    zendure_fresh: bool = False
    primary_fresh: bool = False
    # A fresh independent AC observation must not inherit intent as its sign.
    direction_independent: bool = False
    command_ready: bool = False


@dataclass(frozen=True)
class PvMemory:
    extra_target_w: int = 0
    last_monotonic_s: Optional[float] = None
    last_sample_key: Optional[tuple[str, ...]] = None
    import_backoff: bool = False
    # Two independent frames are required before initiating a positive extra.
    observed_frames: int = 0


@dataclass(frozen=True)
class PvAllocation:
    # Absolute final request BEFORE the existing hardware and command guards.
    absolute_target_w: int
    baseline_target_w: int
    care_extra_w: int
    pv_balance_estimate_w: Optional[int]
    reason: str
    memory: PvMemory
    # Explicit: request is a mathematical candidate, NOT physical efficacy.
    physical_effect_proven: bool = False


def _valid_w(value: Optional[float]) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and isfinite(float(value))


def allocate_care_pv(
    sample: PvSnapshot,
    previous: PvMemory,
    *,
    care_eligible: bool,
    normal_baseline_w: int,
    max_charge_w: int,
    attack_w_per_s: float = 50.0,
    import_abort_w: float = 100.0,
    max_gap_s: float = 10.0,
) -> PvAllocation:
    """Absolute source-neutral PV estimate + bounded Care-only arbitration.

    When unexpectedly importing, remove the *additional Care portion*
    without altering the separately computed conventional baseline. An
    unchanged algebraic total cannot sustain Care import against this guard.
    """
    limit = max(0, int(max_charge_w))
    baseline = max(0, min(limit, int(normal_baseline_w)))

    def answer(extra: int, reason: str, mem: PvMemory, estimate: Optional[int] = None):
        actual_extra = max(0, min(limit - baseline, int(extra)))
        return PvAllocation(baseline + actual_extra, baseline, actual_extra, estimate, reason,
                            replace(mem, extra_target_w=actual_extra))

    if not care_eligible:
        return answer(0, "CARE_NOT_ELIGIBLE", PvMemory())
    if not sample.command_ready or not sample.direction_independent:
        return answer(0, "COMMAND_OR_DIRECTION_UNCERTAIN", PvMemory())
    if not sample.grid_fresh or not sample.zendure_fresh or (
        sample.primary_integrated and not sample.primary_fresh
    ):
        return answer(0, "SOURCE_STALE", PvMemory())
    if not _valid_w(sample.grid_w) or not _valid_w(sample.zendure_signed_w) or (
        sample.primary_integrated and not _valid_w(sample.primary_signed_w)
    ):
        return answer(0, "SOURCE_INVALID", PvMemory())
    if float(sample.zendure_signed_w) < 0 or (
        sample.primary_integrated and float(sample.primary_signed_w) < 0
    ):
        return answer(0, "OPPOSITE_PHYSICAL_FLOW", PvMemory())
    seqs = (sample.grid_sample, sample.zendure_sample) + (
        (sample.primary_sample,) if sample.primary_integrated else ()
    )
    if any(not s for s in seqs):
        return answer(0, "SAMPLE_ID_MISSING", PvMemory())
    if not isfinite(sample.monotonic_s):
        return answer(0, "CLOCK_INVALID", PvMemory())

    total = max(0.0, (float(sample.primary_signed_w) if sample.primary_integrated else 0.0)
                + float(sample.zendure_signed_w) - float(sample.grid_w))
    estimate = min(limit, int(total))
    # Import is an explicit veto for new Care power and a fast release for an
    # existing Care addition. Ordinary baseline remains a separate authority.
    if float(sample.grid_w) > import_abort_w:
        mem = replace(previous, import_backoff=True,
                      last_monotonic_s=sample.monotonic_s,
                      last_sample_key=tuple(seqs))
        return answer(0, "CARE_IMPORT_BACKOFF", mem, estimate)
    # No Care attack while residual import remains: observe at least a new
    # nonimporting sample before attempting a fresh increase.
    if previous.import_backoff:
        if float(sample.grid_w) > 0:
            mem = replace(previous, last_monotonic_s=sample.monotonic_s,
                          last_sample_key=tuple(seqs), observed_frames=0)
            return answer(0, "WAIT_FOR_NONIMPORT", mem, estimate)
        # A single nonimport frame after a Care-induced import may reflect
        # source skew or momentary load relief. First re-establish an
        # independent complete AC balance and only then allow a new attack.
        distinct_recovery = (previous.last_sample_key is not None and
                             all(a != b for a, b in zip(seqs, previous.last_sample_key)))
        if not distinct_recovery or previous.last_monotonic_s is None or (
            sample.monotonic_s <= previous.last_monotonic_s or
            sample.monotonic_s - previous.last_monotonic_s > max_gap_s
        ):
            mem = replace(previous, last_monotonic_s=sample.monotonic_s,
                          last_sample_key=tuple(seqs), observed_frames=0)
            return answer(0, "IMPORT_RECOVERY_WAIT_DISTINCT", mem, estimate)
        mem = PvMemory(0, sample.monotonic_s, tuple(seqs), False, 1)
        return answer(0, "IMPORT_RECOVERY_CONFIRMING", mem, estimate)

    previous_time = previous.last_monotonic_s
    dt = sample.monotonic_s - previous_time if previous_time is not None else 0.0
    gap = previous_time is None or dt <= 0 or dt > max_gap_s
    distinct = tuple(seqs) != previous.last_sample_key
    # Require all constituent measurement sequences to advance. Re-reading
    # the same primary/Zendure sample while grid updates is not a new energy
    # balance and cannot authorize an upward Care ramp.
    all_advanced = bool(previous.last_sample_key is not None and distinct and
                        all(a != b for a, b in zip(seqs, previous.last_sample_key)))
    frames = (1 if distinct else previous.observed_frames) if gap else (
        min(3, previous.observed_frames + 1) if all_advanced else previous.observed_frames
    )
    mem = PvMemory(previous.extra_target_w if not gap else 0,
                   sample.monotonic_s if distinct or gap else previous_time,
                   tuple(seqs) if distinct or gap else previous.last_sample_key,
                   False, frames)
    if gap or not all_advanced or frames < 2:
        return answer(0 if gap else previous.extra_target_w,
                      "WAIT_DISTINCT_FRESH_BALANCE", mem, estimate)

    # Candidate is an ABSOLUTE total, never baseline + estimated PV power.
    desired_extra = max(0, estimate - baseline)
    if desired_extra > previous.extra_target_w:
        extra = min(desired_extra, previous.extra_target_w + int(attack_w_per_s * dt))
        return answer(extra, "CARE_PV_ATTACK", mem, estimate)
    # Falling measured available energy is released immediately; import guard
    # above takes precedence even when T is falsely unchanged.
    return answer(desired_extra, "CARE_PV_RELEASE_OR_HOLD", mem, estimate)
