# ZEC V14.1.4 – Build Validation

Status: **SOURCE FREEZE PASS – final package/fresh-extract gate pending**

## Identity

- Version: `14.1.4`
- Label: `V14.1.4`
- Build-ID: `v14.1.4-20260908`
- Productive upgrade source: V14.1.3 / `v14.1.3-20260906`

## Functional source gates

- focused Status-SOC performance block: PASS;
- focused Graph/UX polish block: PASS;
- release/installer/field-acceptance regression block: PASS;
- complete normal suite: **992 tests + 679 subtests PASS** across **128 test files**;
- complete `ResourceWarning=error` suite: **992 tests + 679 subtests PASS** across the same test-file set.

## Static gates

- Python `compileall`: PASS;
- Bash syntax: **10/10 PASS**;
- Browser JavaScript syntax: **3/3 PASS** (`status_v2.js`, `settings_v2.js`, `graph_v14_1.js`);
- Measurement V4: **246 Standard / 249 Extended unchanged**;
- protected `controller_logic.py` SHA256: `56f854bbe5bbecc9a7ce305af3915bd461615cc425e444b0c3e427c38e4184b1`.

## Status-SOC performance evidence

A same-runtime synthetic source-level benchmark with 1,440 timestamps and 2,880 state/reason intervals measured the isolated `GraphQueryService.storage_day_status()` mapping path at:

- V14.1.3 median: **203.793 ms**;
- V14.1.4 median: **3.265 ms**;
- median speedup: approximately **62.4x**.

This benchmark validates the algorithmic elimination of repeated list materialization and per-point full interval rescans. It is not a Raspberry-Pi end-to-end HTTP latency claim; the real Pi field acceptance remains required.

## Upgrade contract

V14.1.4 accepts only V14.1.3 / `v14.1.3-20260906`. Graph Core V3 is preserved and verified; the completed V14.1.3 historical state backfill is not re-run. Config, Last-Good, configuration states and runtime graph data remain preserved by the installer contract.

## Safety boundary

`controller_logic.py` remains byte-identical. No regulator, command, battery/hardware-safety, retention, scheduler or VACUUM policy is changed by V14.1.4.

The final installer ZIP must still pass manifest, test, ResourceWarning, syntax and protected-source gates from a clean Fresh-Extract before productive installation is authorized.
