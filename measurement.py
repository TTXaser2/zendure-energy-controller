# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

from typing import Any, Dict, Optional


def to_int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def signed_zendure_target_w(input_limit_w: Any, output_limit_w: Any) -> int:
    """Return requested Zendure power with storage sign convention.

    Positive values mean charging, negative values mean discharging.
    Output/discharge wins if both values are non-zero because the live
    controller never intentionally requests simultaneous charging and
    discharging; such a row indicates a transition/diagnostic state.
    """
    charge = max(0, to_int_or_none(input_limit_w) or 0)
    discharge = max(0, to_int_or_none(output_limit_w) or 0)
    if discharge > 0:
        return -discharge
    return charge


def derive_zendure_actual_power(
    pack_input: Any = None,
    output_home: Any = None,
    grid_input: Any = None,
    output_pack: Any = None,
    requested_input_limit: Any = None,
    requested_output_limit: Any = None,
) -> Dict[str, int]:
    """Derive the net grid-side Zendure AC effect from raw properties.

    Sign convention used by UI, CSV and scenario reconstruction:

    * positive = AC import through ``gridInputPower``;
    * negative = AC delivery through ``outputHomePower``.

    ``outputPackPower`` and ``packInputPower`` are battery-boundary flows and
    must never be reinterpreted from the requested command direction.  They are
    returned separately so high-SOC acceptance and off-grid diagnostics can use
    the correct physical boundary.  The requested limits are accepted only for
    API compatibility and are intentionally not used as direction evidence.
    """
    del requested_input_limit, requested_output_limit

    pack_discharge = max(0, to_int_or_none(pack_input) or 0)
    home_output = max(0, to_int_or_none(output_home) or 0)
    grid_import = max(0, to_int_or_none(grid_input) or 0)
    pack_charge = max(0, to_int_or_none(output_pack) or 0)

    signed_grid = int(grid_import - home_output)
    return {
        "charge_power_w": int(grid_import),
        "discharge_power_w": int(home_output),
        "signed_power_w": signed_grid,
        "battery_charge_power_w": int(pack_charge),
        "battery_discharge_power_w": int(pack_discharge),
        "battery_signed_power_w": int(pack_charge - pack_discharge),
    }


def classify_charge_acceptance(
    *,
    soc_percent: Any,
    max_soc_percent: Any,
    target_charge_w: Any,
    actual_charge_w: Any,
    grid_power_w: Any,
    min_effective_target_w: int = 100,
    export_threshold_w: int = 100,
) -> Dict[str, str]:
    """Lightweight diagnostic for high-SOC charging non-acceptance.

    This is intentionally diagnostic-only. It does not change the control
    decision. States:
    - ok: no evidence of charge acceptance issues.
    - suspect: target charge exists but actual charge is materially lower.
    - limited: high SOC and actual charge is clearly limited.
    - not_accepting: high SOC, target charge exists, export remains, almost no charge.
    """
    target = max(0, to_int_or_none(target_charge_w) or 0)
    actual = max(0, to_int_or_none(actual_charge_w) or 0)
    if target < min_effective_target_w:
        return {"state": "ok", "reason": "Keine relevante Ladeanforderung."}

    soc = to_int_or_none(soc_percent)
    max_soc = to_int_or_none(max_soc_percent)
    grid = float(grid_power_w or 0.0)
    ratio = actual / target if target else 1.0
    still_exporting = grid <= -abs(export_threshold_w)

    if soc is None or max_soc is None:
        if ratio < 0.35 and still_exporting:
            return {"state": "suspect", "reason": "Ladeanforderung wird deutlich unterschritten; SOC-Grenze unbekannt."}
        return {"state": "ok", "reason": "Keine belastbaren Hinweise auf Nichtannahme."}

    high_soc = soc >= max_soc - 2
    at_or_above_max = soc >= max_soc

    if at_or_above_max and ratio < 0.20:
        return {"state": "not_accepting", "reason": "SOC am/über Max-SOC; Ladeanforderung wird praktisch nicht angenommen."}
    if high_soc and ratio < 0.20 and still_exporting:
        return {"state": "not_accepting", "reason": "Hoher SOC, weiterhin Einspeisung, nahezu keine reale Ladeleistung."}
    if high_soc and ratio < 0.60:
        return {"state": "limited", "reason": "Hoher SOC; reale Ladeleistung bleibt deutlich unter Soll."}
    if ratio < 0.35 and still_exporting:
        return {"state": "suspect", "reason": "Ladeanforderung wird deutlich unterschritten und es bleibt Einspeisung."}
    if ratio < 0.70:
        return {"state": "suspect", "reason": "Reale Ladeleistung bleibt unter Soll; Beobachtung empfohlen."}
    return {"state": "ok", "reason": "Reale Ladeleistung passt ausreichend zur Ladeanforderung."}
