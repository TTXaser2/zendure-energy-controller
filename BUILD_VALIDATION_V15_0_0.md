# ZEC V15.0.0 – Build Validation

Status: **SOURCE GATES PASS – final package/fresh-extract gate pending**

## Identity

- Version: `15.0.0`
- Label: `V15.0.0`
- Build-ID: `v15.0.0-20260910`
- Productive upgrade source: V14.1.4 / `v14.1.4-20260908` only

## Functional source gates

- native Modbus core/transport/template tests: PASS;
- source-selection/settings/draft connection-test tests: PASS;
- protected primary-storage freshness/control boundary tests: PASS;
- status/readiness/diagnostic integration tests: PASS;
- historical regulator/safety regressions: PASS;
- alt-contract/registry remediation gate: **212 tests + 620 subtests PASS**;
- complete normal suite: **1024 tests + 692 subtests PASS** across **133 test files**;
- complete `ResourceWarning=error` suite: **1024 tests + 692 subtests PASS** across the same test-file set.

## Static gates

- Python `compileall`: PASS;
- Bash syntax: **10/10 PASS**;
- Browser JavaScript syntax: **3/3 PASS** (`status_v2.js`, `settings_v2.js`, `graph_v14_1.js`);
- Measurement V4: **246 Standard / 249 Extended unchanged**;
- native Modbus source maps to the existing Measurement source `SMA`; no V4 enum/schema expansion;
- `controller_logic.py` SHA256: `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`.

## Test-environment note

The engineering sandbox used for the complete suite does not contain the project's already-existing `paho-mqtt` package and cannot reach PyPI. Test collection therefore used an external minimal paho import shim located outside the working tree. The shim is not part of product sources, manifests, installer or release package and does not represent a new V15 dependency. The actual productive Pi already requires/uses the existing MQTT dependency contract.

## Registry contract

- Settings: **215**;
- Defaults: **186**;
- apply classes: **182 LIVE_NEXT_CYCLE / 13 RESTART_REQUIRED / 18 MIGRATION_ONLY / 1 PROTECTED_ACTION / 1 READ_ONLY**;
- effective order is contiguous `0..214`;
- validation-reference closure includes V15 `VAL-026`.

## Upgrade contract

V15.0.0 accepts only V14.1.4 / `v14.1.4-20260908`. Existing config, Last-Good state, configuration states, Measurement data and Graph Core V3 history are preserved. Existing EVCC/custom primary-storage configuration is retained; the update does not silently switch an installation to native Modbus.

## Safety boundary

The V14.1.4 protected controller baseline was intentionally changed only for the approved V15 source/freshness adapter boundary. The exact diff is retained as `validation/V15_0_0_CONTROLLER_LOGIC_DIFF_V14_1_4.patch`. No AUTO/Harvest/Cross-Charge/NIGHT target formula or Zendure command calculation is changed.

The final installer ZIP must still pass manifest, full-suite, ResourceWarning, syntax, release-identity and protected-diff gates from a clean fresh extraction before productive installation is authorized.
