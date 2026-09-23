# Technical Notes V17.0.1

## Fast Capture A400/R100

The ordinary ZEC charge target remains the strategic baseline `B`. Fast Capture produces an independent overlay `O`; only the combined target enters the existing downstream device-limit, Cross-Charge and safe command pipeline. The baseline state never stores the Fast overlay, preventing recursive amplification through `last_input_power`.

Fast Capture is eligible only for the primary-storage states `FULL_IDLE` and `NEAR_LIMIT`. `RESERVE_UNKNOWN`, stale or ambiguous input data, non-ready command state, Safety/STOP/manual/night conflicts and Cross-Charge conflicts suppress active Fast effect. A confirmed import above the configured safety threshold hard-zeros the overlay. Attack is limited to 400 W/s and controlled release to 100 W/s using fresh/distinct observation time.

`HARVEST_FAST_CAPTURE_MODE=off|shadow|active` is the sole product setting. `shadow` calculates and records the candidate state without changing the final controller target or command stream. No user-facing attack/release tuning is exposed in this release.

## Evidence and field verification

Measurement V4 carries additive Fast-Capture state, baseline, overlay, reserve/headroom and observation evidence. `tools/fast_capture_field_analysis.py` is read-only and evaluates episodes on four independent levels: state, calculation, physical effect and recovery. `tools/v17_field_acceptance.py` validates release/runtime/tool compatibility immediately after installation; absent natural Fast episodes remain `NOT_EVALUABLE`, never synthetic PASS.

## Graph gap interaction follow-up

Confirmed evidence gaps suppress nearest-sample cursor/tooltip/inspector values while the pointer is inside the gap. The visual series break remains render-only and no synthetic measurement is created. `actual_ms=null` is rendered as a gap/empty state rather than Unix epoch 1970. Command-follow and comparison hover use the same evidence-aware rule.

## Height-neutral active warnings

Storage-card warnings remain persistently visible as a compact header chip. Details are rendered outside the normal card flow using the existing anchored popover on desktop and the mobile panel/bottom-sheet behavior on small screens. The collapsed warning therefore does not enlarge the storage-card row.

## Deployment boundary

The supported real update source is exclusively V16.2.5 / `v16.2.5-20260922`. The target is V17.0.1 / `v17.0.1-20260922`. Build, package, installer, datasheet, full-regression and fresh-extract gates must pass before the release receives TECHNICAL BUILD PASS.

## V17.0.1 Packaging hotfix

V17.0.1 supersedes the withdrawn V17.0.0 package. V17.0.0 was rejected by the real installer preflight before productive mutation because the distributed ZIP lacked the canonical `zendure_controller_v17_0_0/` archive root. V17.0.1 adds `tools/release_package.py`; its build/verify gate enforces the exact archive root consumed by `package_preflight()` and rejects rootless packages.
