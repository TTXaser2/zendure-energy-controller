# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""Small, in-memory command contract used by the live controller.

The contract deliberately contains no network, file or database operations.  It
separates the desired Zendure device state from MQTT publish attempts and from
physical effect verification.  A neutral 0 W state is an active command batch,
not the absence of a command.
"""

from dataclasses import dataclass
from typing import Dict


INTENT_CHARGE = "CHARGE"
INTENT_DISCHARGE = "DISCHARGE"
INTENT_NEUTRALIZE = "NEUTRALIZE"
INTENT_IDLE = "IDLE"

COMMAND_GATE_UNPROTECTED = "UNPROTECTED"
COMMAND_GATE_WAIT_SMART_MODE = "WAIT_SMART_MODE_READBACK"
COMMAND_GATE_WAIT_FULL_STATE = "WAIT_FULL_STATE_READBACK"
COMMAND_GATE_READY = "READY"
COMMAND_GATE_SAFETY_NEUTRALIZATION = "SAFETY_NEUTRALIZATION_WAITING"



@dataclass(frozen=True)
class DesiredCommandBatch:
    sequence_id: int
    intent: str
    smart_mode: int
    ac_mode: str
    input_limit_w: int
    output_limit_w: int
    signed_target_w: int
    reason: str
    safety_relevant: bool
    created_epoch: float

    @property
    def signature(self) -> str:
        return (
            f"{self.intent}|{self.smart_mode}|{self.ac_mode}|{self.input_limit_w}|"
            f"{self.output_limit_w}|{self.signed_target_w}|{self.reason}"
        )

    def as_dict(self) -> Dict[str, object]:
        return {
            "sequence_id": int(self.sequence_id),
            "intent": str(self.intent),
            "smart_mode": int(self.smart_mode),
            "ac_mode": str(self.ac_mode),
            "input_limit_w": int(self.input_limit_w),
            "output_limit_w": int(self.output_limit_w),
            "signed_target_w": int(self.signed_target_w),
            "reason": str(self.reason),
            "safety_relevant": bool(self.safety_relevant),
            "created_epoch": float(self.created_epoch),
        }


def intent_for_signed_target(signed_target_w: int, *, explicit_neutralize: bool = False) -> str:
    value = int(signed_target_w or 0)
    if value > 0:
        return INTENT_CHARGE
    if value < 0:
        return INTENT_DISCHARGE
    return INTENT_NEUTRALIZE if explicit_neutralize else INTENT_IDLE
