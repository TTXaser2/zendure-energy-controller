# Zendure Energy Controller V17.0.1

**Build-ID:** `v17.0.1-20260922`  
**Status:** **RELEASE FREEZE / TECHNICAL BUILD GATES PENDING**

## Scope

V17.0.1 introduces the explicitly approved Fast Capture A400/R100 controller layer on top of the V16.2.5 baseline:

- Fast Capture for `FULL_IDLE` and `NEAR_LIMIT` with A400 attack / R100 controlled release;
- strict baseline/overlay separation so Fast Capture never feeds itself through the ordinary controller baseline;
- `off | shadow | active` product contract via the expert setting `HARVEST_FAST_CAPTURE_MODE`;
- fail-closed runtime gates for freshness, command readiness, Safety, Cross-Charge and mode conflicts;
- additive Measurement-V4 evidence and read-only `tools/fast_capture_field_analysis.py` for state, calculation, physical effect and recovery validation;
- release-specific `tools/v17_field_acceptance.py` which validates the V17 runtime contract without inventing a Fast PASS when no natural episode exists;
- graph evidence-gap interactions no longer present nearest samples from outside a confirmed gap as if measured inside it;
- active storage warnings use a height-neutral header chip and an out-of-flow detail surface instead of growing the card row in the collapsed state.

## Safety boundaries

Fast Capture remains subordinate to existing Safety, command/readback, Cross-Charge and device-limit contracts. `RESERVE_UNKNOWN` never receives an active overlay. Raw primary-storage SOC remains authoritative for Fast Capture; the diagnostic Sunny-Island discharge-floor/usable-SOC capability has no Fast-Capture controller effect.

## Rollout contract

Technical Build PASS alone does not authorize immediate active control. After the real V16.2.5 -> V17.0.1 update, Fast Capture starts from the safe `off` sentinel. Productive validation proceeds through `shadow`, read-only field analysis and an explicit later authorization before bounded `active` operation.
