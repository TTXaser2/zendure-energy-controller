# ZEC V15.0.1 – Build Validation

Status: **SOURCE/RELEASE GATES PASS – final package/fresh-extract gate pending**

## Identity

- Version: `15.0.1`
- Label: `V15.0.1`
- Build-ID: `v15.0.1-20260911`
- Productive upgrade source: V15.0.0 / `v15.0.0-20260910` only

## Implemented source blocks

- Graph/analysis visual-field fixes: targeted regression **78 PASS**;
- Settings/primary-storage guidance and dark-mode fixes: targeted regression **128 PASS + 620 subtests**;
- Release/installer identity gate: **98 PASS + 10 subtests**;
- no changes to `controller_logic.py` from V15.0.0;
- no Modbus core/protocol/freshness changes;
- no new settings/config keys.

## Complete source gates

- complete normal suite: **1042 tests + 692 subtests PASS** across **136 Python test files**;
- complete `ResourceWarning=error` suite: **1042 tests + 692 subtests PASS** across the same test-file set;
- Python `compileall`: PASS;
- Browser JavaScript syntax: **3/3 PASS** (`status_v2.js`, `settings_v2.js`, `graph_v14_1.js`);
- Bash syntax: **10/10 PASS**;
- Measurement V4: **246 Standard / 249 Extended unchanged**;
- `controller_logic.py` SHA256: `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`, byte-identical to V15.0.0.

## Test-environment note

The engineering sandbox does not contain the project's pre-existing `paho-mqtt` package and cannot reach PyPI. Full-suite collection therefore used the same external minimal paho import shim as the V15.0.0 build. The shim is outside the working tree and is not included in source manifests, installer or release artifacts. V15.0.1 adds no runtime dependency.

## Safety / no-regression boundary

- AUTO, Harvest, Cross-Charge, NIGHT and Zendure command target calculations are unchanged;
- native Modbus transport, template registers, source-health and freshness behavior are unchanged from V15.0.0;
- Graph Core V3 storage/history identity and Greenfield workspace API contract are unchanged;
- Measurement V4 schema is unchanged.

The final installer ZIP must still pass manifest, full-suite, ResourceWarning, syntax, release-identity and protected-source gates from a clean fresh extraction before TECHNICAL BUILD PASS is declared.
