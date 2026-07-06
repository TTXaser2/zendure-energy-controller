# Technical Notes – V12.11.0-RC15

V12.11.0-RC15 is a UI interaction and graph time-axis polish release on top of V12.11.0-RC14.

## Scope

This release continues the mock-up-driven UI polish without changing control behavior.

### Status dashboard

- Refined the Zendure battery card typography:
  - SOC ring text is split into a large SOC value and a separate SOC label.
  - Lade-/Entladeleistung, Zustand and Kapazität use clearer spacing and hierarchy.
- Moved local status warnings into the responsible card:
  - Zendure MQTT freshness warnings are shown inside the Zendure card.
  - Grid-source warnings are shown inside the Netzleistungsquelle card.
  - Logging warnings are shown inside the Messdaten/Logging card.
- The global yellow warning strip is reserved for system-wide controller warnings.

### Chart interaction

- The SOC day chart on the status page now uses x-axis based non-intersect tooltip interaction.
- The modern graph page now uses x-axis based non-intersect tooltip interaction.
- Chart datasets use larger invisible hit radii, so tooltips are shown when the cursor is close to the x-position instead of requiring an exact line hit.

### Modern graph time axis

- `/graph-view-data` now separates the requested chart axis window from the available data points.
- `Letzte 24 Stunden` now always returns a true 24-hour axis window, even when measurement data contains gaps or only covers part of the interval.
- The graph payload includes axis metadata:
  - `axis_start_epoch_ms`
  - `axis_end_epoch_ms`
  - `axis_duration_hours`
  - `label`
  - `data_start_epoch_ms`
  - `data_end_epoch_ms`
- Long graph windows use date+time tick labels to make midnight crossings clearer.

## Not changed

- No change to AUTO control behavior.
- No change to night discharge control behavior.
- No change to Cross-Charge logic.
- No change to surplus-harvest logic.
- No change to Zendure MQTT command structure or topics.
- No change to Measurement-V4 schema.
- No change to the final Excel learning simulation.

## Tests

```bash
python3 -m py_compile *.py tools/*.py
bash -n tools/create_zec_analysis_package.sh
bash -n tools/collect_zec_trace.sh
bash -n tools/create_desktop_shortcuts.sh
bash -n tools/run_zec_analysis_package_interactive.sh
bash -n tools/collect_zec_crash_package.sh
python3 -m unittest discover -q
```

Result: 246 tests OK.
