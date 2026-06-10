# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""Small freshness/validity helpers for external controller data.

The controller deliberately keeps this model lightweight: it does not decide the
control mode. It gives every cycle a consistent vocabulary for diagnostics,
CSV/graph output and tests: available, fresh, valid, used_for_control and a
machine-readable reason.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DataStatus:
    name: str
    available: bool
    fresh: bool
    valid: bool
    used_for_control: bool = False
    age_s: Optional[int] = None
    reason: str = "OK"

    def as_prefixed_dict(self, prefix: str) -> Dict[str, Any]:
        return {
            f"{prefix}_available": self.available,
            f"{prefix}_fresh": self.fresh,
            f"{prefix}_valid": self.valid,
            f"{prefix}_used_for_control": self.used_for_control,
            f"{prefix}_age_s": self.age_s,
            f"{prefix}_reason": self.reason,
        }


def age_seconds(last_update_epoch: Optional[float], now_epoch: Optional[float] = None) -> Optional[int]:
    if last_update_epoch is None:
        return None
    now = time.time() if now_epoch is None else float(now_epoch)
    try:
        return max(0, int(now - float(last_update_epoch)))
    except Exception:
        return None


def timestamp_status(
    name: str,
    last_update_epoch: Optional[float],
    timeout_seconds: Any,
    *,
    has_value: bool = True,
    used_for_control: bool = False,
    now_epoch: Optional[float] = None,
    missing_reason: Optional[str] = None,
    stale_reason: Optional[str] = None,
) -> DataStatus:
    """Evaluate data freshness from a timestamp and timeout.

    `has_value` handles sources where a timestamp exists only after a successful
    update but the actual value can still be missing or invalid. A value is valid
    exactly when it is available and fresh.
    """
    now = time.time() if now_epoch is None else float(now_epoch)
    try:
        timeout = float(timeout_seconds)
    except Exception:
        timeout = 0.0

    age = age_seconds(last_update_epoch, now)
    available = bool(has_value) and last_update_epoch is not None
    fresh = bool(available and age is not None and age <= timeout)
    valid = bool(available and fresh)

    if not available:
        reason = missing_reason or f"{name.upper()}_MISSING"
    elif not fresh:
        reason = stale_reason or f"{name.upper()}_STALE"
    else:
        reason = "OK"

    return DataStatus(
        name=name,
        available=available,
        fresh=fresh,
        valid=valid,
        used_for_control=bool(used_for_control),
        age_s=age,
        reason=reason,
    )


def boolean_status(
    name: str,
    value: Any,
    *,
    used_for_control: bool = False,
    ok_reason: str = "OK",
    false_reason: Optional[str] = None,
) -> DataStatus:
    valid = bool(value)
    return DataStatus(
        name=name,
        available=True,
        fresh=valid,
        valid=valid,
        used_for_control=bool(used_for_control),
        age_s=None,
        reason=ok_reason if valid else (false_reason or f"{name.upper()}_INVALID"),
    )
