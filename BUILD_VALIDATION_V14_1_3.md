# ZEC V14.1.3 – Build Validation

Status: **SOURCE FREEZE PASS – package/fresh-extract gate pending**

## Identity

- Version: `14.1.3`
- Label: `V14.1.3`
- Build-ID: `v14.1.3-20260906`
- Productive upgrade source: V14.1.2 / `v14.1.2-20260905`

## Functional source gates

- focused V14.1.3 Core/State/SOC/422 block: PASS;
- V14.1.3 Graph/Polish target block: PASS;
- adjacent Settings/Config/V14 Graph regression block: PASS;
- release/installer/field-acceptance target block: **119 tests + 10 subtests PASS**;
- complete normal suite: **982 tests + 679 subtests PASS** across **126 test files**;
- complete `ResourceWarning=error` suite: **982 tests + 679 subtests PASS** across the same test-file set.

## Static gates

- Python `compileall`: PASS;
- Bash syntax: **10/10 PASS**;
- Browser JavaScript syntax: **3/3 PASS** (`status_v2.js`, `settings_v2.js`, `graph_v14_1.js`);
- Measurement V4: **246 Standard / 249 Extended unchanged**;
- protected `controller_logic.py` SHA256: `56f854bbe5bbecc9a7ce305af3915bd461615cc425e444b0c3e427c38e4184b1`.

## Upgrade and repair contract

V14.1.3 accepts only V14.1.2 / `v14.1.2-20260905`. The existing Graph Core V3 database is preserved, verified before mutation, and verified again after the targeted state repair. The repair only fills evidence-backed missing suffix intervals for `OPERATING_MODE` and `CONTROL_INTENT`; it does not rebuild Graph Core, alter numeric graph samples, command events, `CONTROL_REASON`, coverage or evidence. If no Measurement-V4 source is present, historical repair is skipped and the live V14.1.3 state writer remains fully functional.

## Source delta from V14.1.2

- added files: **14**;
- changed files: **45**;
- removed files: **0**.

Exact paths are recorded in `validation/V14_1_3_SOURCE_DIFF_V14_1_2.txt`.

The final installer ZIP must still pass the same gates from a clean Fresh-Extract before Productive installation is authorized.
