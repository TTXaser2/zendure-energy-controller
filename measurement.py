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
    """Derive signed Zendure AC/system power from raw headunit sensors.

    Sign convention used by the controller UI, CSV and analysis:
    - positive values mean charging,
    - negative values mean discharging.

    Zendure raw sensors are not perfectly named from the external system point
    of view. In particular, packInputPower / pack power can be positive while
    the battery is discharging internally into the headunit. Therefore explicit
    AC output sensors and the currently requested output limit are used to
    disambiguate night/fixed discharge. Raw values are still preserved in state
    and CSV for diagnostics.
    """
    pi = to_int_or_none(pack_input)
    oh = to_int_or_none(output_home)
    gi = to_int_or_none(grid_input)
    op = to_int_or_none(output_pack)
    requested_in = max(0, to_int_or_none(requested_input_limit) or 0)
    requested_out = max(0, to_int_or_none(requested_output_limit) or 0)

    charge_candidates = [0]
    discharge_candidates = [0]

    # AC/grid-side input is the strongest evidence for real external charging.
    if gi is not None:
        charge_candidates.append(max(0, gi))

    # AC/home output and outputPack are strong evidence for external/internal
    # discharge.
    for value in (oh, op):
        if value is not None:
            discharge_candidates.append(max(0, value))

    # packInputPower is ambiguous on SolarFlow AC+: during night discharge the
    # pack can report a positive internal pack -> headunit power. Use the active
    # request to classify this value.
    if pi is not None:
        if requested_out > 0 and requested_in <= 0 and max(discharge_candidates) <= 0:
            discharge_candidates.append(max(0, pi))
        elif requested_out > 0 and requested_in <= 0 and max(0, pi) >= max(discharge_candidates) * 0.5:
            discharge_candidates.append(max(0, pi))
        else:
            charge_candidates.append(max(0, pi))

    charge = max(charge_candidates)
    discharge = max(discharge_candidates)

    if requested_out > 0 and requested_in <= 0 and discharge > 0:
        signed = -discharge
        charge = 0
    elif requested_in > 0 and requested_out <= 0 and charge > 0:
        signed = charge
        discharge = 0
    else:
        signed = charge if charge >= discharge else -discharge

    return {
        "charge_power_w": int(charge),
        "discharge_power_w": int(discharge),
        "signed_power_w": int(signed),
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
