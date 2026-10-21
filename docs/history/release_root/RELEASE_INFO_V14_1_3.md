# ZEC V14.1.3

## Release scope

V14.1.3 is the production polish and state-history repair release following the V14.1.2 Graph Interaction completion.

### Graph/Core fixes

- fixes the selection-zoom HTTP 422 by normalizing selected epoch values to integer milliseconds;
- persists `OPERATING_MODE` and `CONTROL_INTENT` into Graph Core before optional Measurement-V4 logging, so Graph Core remains independent from ongoing V4 logging;
- adds an idempotent, evidence-only suffix repair for missing historical `OPERATING_MODE` / `CONTROL_INTENT` intervals from existing Measurement V4;
- the repair never mutates numeric graph samples, command events, `CONTROL_REASON`, coverage or evidence and never bridges real V4 gaps;
- published commands have their own state/event lane instead of masquerading as operating-mode intervals.

### Status SOC responsiveness

- the Status SOC day path uses a lean V3 query that skips entity/coverage/evidence reads not consumed by that UI;
- duplicate Graph-runtime probing is avoided;
- the browser uses stale-while-revalidate session caching so the last valid day remains visible while refresh data arrives;
- returning to Status no longer requires a blocking Analyse-Service health probe on the critical render path.

### Graph workspace polish

- guided investigations are real workspace presets with distinct titles, series and default lane order;
- lanes can be collapsed and moved up/down, with local per-preset layout persistence;
- the desktop analysis workspace can use up to 2020 px width;
- explicit busy feedback and debounced free-series reload remove ambiguous multi-second waits;
- Command-Follow gains info help, legend, publish marker and hover cursor;
- period and t=0 episode comparison gain synchronized A/B/Delta hover;
- episode comparison uses a real `-before ... t=0 ... +after` axis and guided/filterable trigger selection;
- common evidence gaps are aggregated instead of repeated once per selected series;
- controller state lanes gain a separate Commands row and an external hover magnifier;
- Inspector density is reduced while preserving readability.

### Settings theme

- Settings-V2 legacy light-only controls are normalized to semantic theme tokens for complete dark-mode coverage.

## Release identity

- Version: `14.1.3`
- Label: `V14.1.3`
- Build-ID: `v14.1.3-20260906`
- Package: `zendure_controller_v14_1_3.zip`
- Supported productive source: V14.1.2 / `v14.1.2-20260905` only

## Safety boundary

`controller_logic.py` remains byte-identical to the protected baseline. No regulator, command, hardware-safety, retention, scheduler or VACUUM policy is changed by this release.
