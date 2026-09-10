# ZEC V14.1.4

## Release scope

V14.1.4 is the Graph/Status performance and UX-polish release following the productive V14.1.3 state-history repair release.

### Status SOC performance

- `storage_day_status()` binds numeric series once instead of repeatedly rematerializing them per point;
- operating-mode/control-reason interval assignment uses an overlap-safe sweep instead of scanning all intervals for every graph point;
- overlap semantics remain compatible: the latest active interval wins;
- the outer Status-SOC day cache keeps up to six recent day payloads instead of a single day key, while retaining separate TTL behavior for today and completed historical days.

### Graph workspace / UX polish

- explicit calendar-day presets are added alongside rolling-hour windows;
- Inspector density and workspace geometry are reduced without removing diagnostic content;
- the target pipeline is rendered as a visual sequence including intermediate stages and deltas;
- guided investigations enter busy state immediately and reset/reload more specifically;
- freely selected series can be reloaded incrementally instead of forcing a complete workspace refresh;
- period/episode comparison hover and controller-state magnifier behavior are refined;
- data-quality gaps are presented more compactly and precisely;
- graph tooltips use cursor-aware side flipping near the left/right plot edge so the tooltip does not cover the cursor/marker and investigated data point;
- Command-Follow uses the same non-obscuring tooltip positioning principle.

### Settings / status adjacency

- the V14.1.3 Settings dark-mode token normalization is retained unchanged after contract verification;
- the legacy Status SOC canvas already had edge-aware tooltip side switching and therefore required no redundant tooltip patch.

## Release identity

- Version: `14.1.4`
- Label: `V14.1.4`
- Build-ID: `v14.1.4-20260908`
- Package: `zendure_controller_v14_1_4.zip`
- Supported productive source: V14.1.3 / `v14.1.3-20260906` only

## Safety boundary

`controller_logic.py` remains byte-identical to the protected baseline. No live regulator, command, hardware-safety, Graph-Core retention or Measurement-V4 contract is changed by this release.
