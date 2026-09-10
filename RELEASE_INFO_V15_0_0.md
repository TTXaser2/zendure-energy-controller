# ZEC V15.0.0

## Release scope

V15.0.0 introduces a source-neutral primary-storage architecture while retaining the existing EVCC/MQTT path. The new third source profile is a native, strictly read-only Modbus/TCP template connection.

### Primary-storage sources

- existing `evcc_standard` source remains supported;
- existing user-defined `custom` MQTT source remains supported;
- new `modbus_template` source profile;
- no automatic EVCC ↔ Modbus fallback in V15.0.0;
- source/template/endpoint changes require a service restart;
- primary-storage integration remains independently enable/disable-able;
- observer mode is valid with integration enabled while Cross-Charge and Harvest are disabled.

### Native Modbus/TCP

- no new Python runtime dependency is added;
- the internal transport uses only Python standard-library networking;
- the transport exposes read-only Modbus FC03/FC04 only;
- there is no Modbus write API and no generic raw-request escape hatch;
- socket I/O runs in a background worker outside the controller cycle;
- persistent TCP connection with reconnect on transport/protocol failure;
- default polling interval for the first template: 1 s.

### First template: SMA Sunny Island

- template id: `sma_sunny_island`;
- default display name: `SMA Sunny Island`;
- power: register 30775, FC04, S32, 2 registers, W;
- SOC: register 30845, FC03, U32, 2 registers, %;
- default TCP port: 502;
- default Unit-ID: 3;
- host/IP remains installation-specific;
- capacity remains optional and is not invented from an undocumented register.

### Runtime / freshness / recovery

- complete Power+SOC polls are published atomically into the shared primary-storage state;
- native canonical ZEC power sign: positive = discharge, negative = charge;
- EVCC/custom MQTT sign configuration remains unchanged;
- source health is exposed separately as `STARTING`, `OK`, `DEGRADED`, `STALE`;
- a failed poll may produce `DEGRADED` while the last complete cached snapshot is still control-fresh;
- the existing `SECOND_BATTERY_STALE_TIMEOUT_SECONDS` remains the control-freshness authority;
- control freshness is monotonic-time-first, with wall-clock fallback only when required;
- no new control effect is inferred solely from Source Health.

### Settings / UI / diagnostics

- existing `SECOND_BATTERY_DISPLAY_NAME` is reused; no duplicate display-name key is introduced;
- configured name is used consistently; native template name is the fallback when the configured name is empty;
- Modbus template, host, port and Unit-ID are explicit settings;
- the Settings connection test uses draft values, is bounded and read-only, and does not persist or switch runtime source;
- status/readiness expose configured source profile and Source Health independently from Cross-Charge enablement;
- Graph Core V3 keeps the stable primary-storage identity; changing source does not split historical storage identity.

## Release identity

- Version: `15.0.0`
- Label: `V15.0.0`
- Build-ID: `v15.0.0-20260910`
- Planned package: `zendure_controller_v15_0_0.zip`
- Supported productive source: V14.1.4 / `v14.1.4-20260908` only

## Dependency decision

V15.0.0 intentionally adds no Modbus package dependency. The native V1 scope requires only FC03/FC04 and is implemented as a small internal read-only transport. If a future device/template requires broader Modbus functionality, the dependency decision must be reopened rather than expanding this transport into a general Modbus stack.

The pre-existing `paho-mqtt` dependency remains unchanged in `requirements.txt` and in the existing MQTT runtime contract.

## Safety boundary

The approved `controller_logic.py` delta is restricted to source-neutral primary-storage integration, monotonic freshness, availability/display validity and native Modbus sign normalization. AUTO, Harvest, Cross-Charge, NIGHT and Zendure command target calculations are not changed.

Native Modbus access is read-only. V15.0.0 does not write to the SMA Sunny Island.

## Field acceptance

Build PASS is not Productive PASS. After installation the release requires the supplied read-only V15 field-acceptance tool and real UI/source verification. When the native source is selected, field acceptance can explicitly require `--expect-primary-profile modbus_template`.

The separate V14.1.4 visual field acceptance remains pending in parallel and must not be silently discarded; its already identified UI findings must be recorded before the installed V14.1.4 state is replaced.
