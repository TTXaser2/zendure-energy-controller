# Technical Notes – V12.11.0-RC16

V12.11.0-RC16 is a status/graph performance and UI refresh stabilization release on top of V12.11.0-RC15.

## Motivation

Field timing on the Raspberry Pi showed that the lightweight status endpoints were healthy, while historical graph endpoints were far too slow for interactive use:

- `/` around 0.8 s
- `/status` around 0.014 s
- `/soc-day-data` around 60 s
- `/graph-view-data?range=24h&resolution=1min` around 207 s

The bottleneck was server-side measurement history scanning before the first response byte, not network transfer.

## Changes

- Measurement-V4 graph reads for recent windows now use bounded recent file-tail reads instead of full historical CSV scans.
- `/graph-view-data` uses a stronger cache and single-flight guard for measurement-backed views.
- `/soc-day-data` uses a cache and single-flight guard; concurrent requests can receive stale cached data with the current live SOC point instead of starting another expensive scan.
- Frontend graph loads on the status and graph pages now have timeouts and user-visible fallback messages instead of endless `lädt…`.
- Modern graph page avoids overlapping auto-refresh requests while a previous graph request is still in flight.
- The status-page network mini-graph is now refreshed via `/grid-mini-sparkline` without a full page reload.
- `tools/collect_zec_trace.sh` now includes endpoint timing checks for `/`, `/status`, `/soc-day-data`, and `/graph-view-data?range=24h&resolution=1min`.

## Non-goals

- No change to AUTO regulation.
- No change to night-discharge behavior.
- No change to Cross-Charge protection.
- No change to remaining-surplus harvesting.
- No change to Zendure MQTT commands or topics.
- No change to the measurement schema.
- No change to the final Excel learning simulation.

## Expected effect

Cached graph requests should return quickly. Cold requests should be materially faster than RC15 because they only inspect bounded recent log tails for recent graph windows. If a cold rebuild is still in progress, additional browser requests avoid multiplying the load.
