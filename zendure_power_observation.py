# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""Independent Zendure power-flow observation for SolarFlow AC devices.

The zenSDK property names describe different electrical boundaries and must not
be collapsed into one ambiguous value:

* ``gridInputPower``: AC power imported through the grid-connected port.
* ``outputHomePower``: AC power exported through the grid-connected/home port.
* ``outputPackPower``: power flowing into the battery pack (charging).
* ``packInputPower``: power flowing out of the battery pack (discharging).
* ``gridOffPower``: load supplied through the off-grid/backup outlet.

The live controller command controls the grid-connected AC port.  Therefore the
primary ``direction``/``signed_power_w`` fields intentionally describe only the
grid-side command effect.  Battery flow and off-grid load are returned as
separate orthogonal observations.  This prevents an off-grid load from being
misclassified as failed neutralisation or as export to the house.
"""

from typing import Any, Dict, Optional


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _non_negative(value: Optional[int]) -> int:
    return max(0, int(value or 0))


def _flow_direction(charge_w: int, discharge_w: int, threshold_w: int) -> tuple[str, str, Optional[int], int, str]:
    charge_active = charge_w >= threshold_w
    discharge_active = discharge_w >= threshold_w
    magnitude = max(charge_w, discharge_w)

    if charge_active and discharge_active:
        return (
            "CONFLICT",
            "NONE",
            None,
            magnitude,
            "Gleichzeitig belastbare Leistungsflüsse in beide Richtungen gemeldet.",
        )
    if charge_active:
        return ("CHARGE", "HIGH", charge_w, charge_w, "Belastbarer Ladefluss bestätigt.")
    if discharge_active:
        return ("DISCHARGE", "HIGH", -discharge_w, discharge_w, "Belastbarer Entladefluss bestätigt.")
    return (
        "NEUTRAL",
        "MEDIUM",
        0,
        magnitude,
        f"Beide Richtungen liegen unter {threshold_w} W.",
    )


def derive_zendure_power_observation(
    *,
    pack_input: Any = None,
    output_home: Any = None,
    grid_input: Any = None,
    output_pack: Any = None,
    grid_off: Any = None,
    solar_input: Any = None,
    evidence_threshold_w: int = 20,
) -> Dict[str, object]:
    """Return separated grid-side, battery-side and off-grid observations.

    Sign conventions:

    * grid-side signed power: ``+`` AC import/charging request, ``-`` export to
      the house/grid-connected port;
    * battery signed power: ``+`` battery charging, ``-`` battery discharging;
    * off-grid power: separate non-negative load, never folded into either
      command-effect direction.
    """

    threshold = max(1, int(evidence_threshold_w or 20))
    pack_discharge_w = _non_negative(_int_or_none(pack_input))
    home_output_w = _non_negative(_int_or_none(output_home))
    grid_import_w = _non_negative(_int_or_none(grid_input))
    pack_charge_w = _non_negative(_int_or_none(output_pack))
    offgrid_w = _non_negative(_int_or_none(grid_off))
    solar_w = _non_negative(_int_or_none(solar_input))

    grid_direction, grid_confidence, grid_signed, grid_magnitude, grid_reason = _flow_direction(
        grid_import_w,
        home_output_w,
        threshold,
    )
    battery_direction, battery_confidence, battery_signed, battery_magnitude, battery_reason = _flow_direction(
        pack_charge_w,
        pack_discharge_w,
        threshold,
    )

    if grid_direction == "CHARGE":
        grid_reason = "gridInputPower bestätigt AC-Bezug am netzgekoppelten Port."
    elif grid_direction == "DISCHARGE":
        grid_reason = "outputHomePower bestätigt Abgabe am netzgekoppelten Port."
    elif grid_direction == "NEUTRAL":
        grid_reason = f"gridInputPower und outputHomePower liegen unter {threshold} W."
    else:
        grid_reason = "gridInputPower und outputHomePower melden gleichzeitig relevante Gegenflüsse."

    if battery_direction == "CHARGE":
        battery_reason = "outputPackPower bestätigt Batterieladung."
    elif battery_direction == "DISCHARGE":
        battery_reason = "packInputPower bestätigt Batterieentladung."
    elif battery_direction == "NEUTRAL":
        battery_reason = f"outputPackPower und packInputPower liegen unter {threshold} W."
    else:
        battery_reason = "outputPackPower und packInputPower melden gleichzeitig relevante Gegenflüsse."

    # Coarse power-balance residual for diagnostics only.  A positive residual
    # means more source power than explicitly observed sinks; a negative value
    # means more sinks than sources.  Conversion losses and staggered MQTT
    # updates make this unsuitable as a control input.
    balance_residual = (
        grid_import_w
        + pack_discharge_w
        + solar_w
        - home_output_w
        - pack_charge_w
        - offgrid_w
    )

    return {
        # Backward-compatible primary command-effect observation: grid side.
        "direction": grid_direction,
        "confidence": grid_confidence,
        "signed_power_w": grid_signed,
        "magnitude_w": int(grid_magnitude),
        "charge_evidence_w": int(grid_import_w),
        "discharge_evidence_w": int(home_output_w),
        "reason": grid_reason,
        # Explicit grid-side fields.
        "grid_direction": grid_direction,
        "grid_confidence": grid_confidence,
        "grid_signed_power_w": grid_signed,
        "grid_magnitude_w": int(grid_magnitude),
        "grid_import_power_w": int(grid_import_w),
        "grid_output_power_w": int(home_output_w),
        "grid_reason": grid_reason,
        # Explicit battery-side fields.
        "battery_direction": battery_direction,
        "battery_confidence": battery_confidence,
        "battery_signed_power_w": battery_signed,
        "battery_magnitude_w": int(battery_magnitude),
        "battery_charge_power_w": int(pack_charge_w),
        "battery_discharge_power_w": int(pack_discharge_w),
        "battery_reason": battery_reason,
        # Off-grid is deliberately orthogonal.
        "offgrid_power_w": int(offgrid_w),
        "offgrid_active": bool(offgrid_w >= threshold),
        "solar_input_power_w": int(solar_w),
        "power_balance_residual_w": int(balance_residual),
    }
