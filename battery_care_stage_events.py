# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pure provenance rules for observed Battery-Care controller stage changes.

Never create a historical transition from a PV shadow candidate, SOC threshold,
command ACK or uncompleted control cycle. The stage is command *intent*, not a
physical battery effect. Events are journaled only after distinct completed
controller cycles, and survive restarts via an SQLite stable-state cursor.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

REQUESTED = frozenset({"PV_PRIORITY_REQUESTED", "GRID_REQUESTED", "EMERGENCY_REQUESTED"})
STAGES = REQUESTED | {"RESERVE_POLICY", "STOP_HOLD", "NONE"}


def observed_care_stage(snapshot: Mapping[str, Any]) -> str | None:
    """Return a stage only for an independently completed controller cycle.

    ``None`` means no trustworthy sample, not a logged transition to NONE.
    """
    cycle = snapshot.get("loop_counter")
    complete = snapshot.get("care_completed_cycle_id")
    if type(cycle) is not int or cycle < 1 or type(complete) is not int or complete != cycle:
        return None
    dispatched = snapshot.get("care_dispatched_stage")
    watts = snapshot.get("care_dispatched_target_w")
    if (dispatched in REQUESTED and type(watts) is int and watts > 0
            and snapshot.get("care_policy_valid") is True):
        return str(dispatched)
    if (snapshot.get("care_policy_valid") is True
            and isinstance(snapshot.get("care_effective_discharge_floor_soc"), (int, float))
            and not isinstance(snapshot.get("care_effective_discharge_floor_soc"), bool)
            and math.isfinite(float(snapshot["care_effective_discharge_floor_soc"]))
            and 0 <= float(snapshot["care_effective_discharge_floor_soc"]) <= 100):
        return "RESERVE_POLICY"
    if snapshot.get("current_mode") == "STOP_HOLD":
        return "STOP_HOLD"
    return "NONE"


def stage_label(stage: str) -> str:
    return {
        "PV_PRIORITY_REQUESTED": "PV-Umlenkung angefordert",
        "GRID_REQUESTED": "Netzpflege angefordert",
        "EMERGENCY_REQUESTED": "Notladung angefordert",
        "RESERVE_POLICY": "Reserve-Policy gültig",
        "STOP_HOLD": "STOP-HOLD beobachtet",
        "NONE": "keine bestätigte Care-Anforderung",
    }.get(stage, "unbekannt")
