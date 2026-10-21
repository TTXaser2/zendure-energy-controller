# ZEC V15.0.1

## Release scope

V15.0.1 is a focused bugfix and UX-hardening release on the productive V15.0.0 source. It bundles the confirmed V14.1.4 visual-field findings with the guided-settings findings observed after the V15.0.0 primary-storage rollout.

### Graph / analysis UX fixes

- `Zeitlupe` replaced by the unambiguous user-facing `Detailausschnitt` (10-minute zoom around the cursor);
- the detail view follows the single global analysis cursor, including hover originating from the power/SOC charts;
- persistent detail panel removes hover-induced layout flicker;
- state/event parent timeline receives a time axis and visible detail-window location;
- long state/reason text wraps inside its card;
- comparison A/B/Delta value panel remains layout-stable and can focus matching overlay pairs;
- Command-Follow uses a fixed value panel outside its mini-chart instead of obscuring the cursor with a floating tooltip;
- calendar toolbar gains day-back/day-forward navigation and the explicit label `Vorgestern & Gestern`;
- toolbar loading/status space is reserved to avoid button shifting;
- target-pipeline stages use distinct color/dash encodings with the final controller target visually emphasized.

### Settings / primary-storage UX fixes

- source-specific primary-storage configuration is ordered directly after the source selector;
- source selection immediately shows a contextual guidance card and jump action to the relevant parameters;
- Modbus `Template` is presented as `Gerät / Modell`; internally stable template IDs remain unchanged;
- Port and Unit-ID are explained as device-profile defaults and remain expert parameters;
- the draft-value Modbus connection test remains read-only and directly associated with the Modbus connection settings;
- help explains that additional device profiles are versioned ZEC release content, not freely editable register templates;
- dark-mode contrast is corrected for the discard/secondary action and preview/field warning/error states.

## No-regression / safety boundary

- no AUTO, Harvest, Cross-Charge, NIGHT or Zendure command calculation changes;
- no Modbus transport/register/freshness changes;
- `controller_logic.py` remains byte-identical to V15.0.0;
- no new configuration keys;
- Graph Core V3 storage/history identity and the Greenfield workspace API contract remain unchanged;
- Measurement V4 schema remains unchanged.

## Release identity

- Version: `15.0.1`
- Label: `V15.0.1`
- Build-ID: `v15.0.1-20260911`
- Planned package: `zendure_controller_v15_0_1.zip`
- Supported productive source: V15.0.0 / `v15.0.0-20260910` only

## Field acceptance

Build PASS is not Productive PASS. After installation, run the supplied read-only `tools/v15_field_acceptance.py` against the V15.0.1 install report and repeat the visual checks for the confirmed UI findings. Native Modbus may remain the active primary-storage source during this acceptance.
