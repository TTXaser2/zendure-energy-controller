# Installation – Zendure Energy Controller V14.1.4

**Release:** `V14.1.4`  
**Build-ID:** `v14.1.4-20260908`

## Supported source

This installer accepts **only** the verified productive source:

- Version `14.1.3`
- Build-ID `v14.1.3-20260906`

It does not support downgrade, skip-update or alternate source identities.

## Install

Place the exact package in `/home/pi/Downloads` and verify its SHA256 against the value supplied with the final release. Then run:

```bash
cd /home/pi/Downloads
unzip -t zendure_controller_v14_1_4.zip
rm -rf zendure_controller_v14_1_4
unzip -q zendure_controller_v14_1_4.zip
chmod +x zendure_controller_v14_1_4/tools/update_zendure_controller.sh
bash zendure_controller_v14_1_4/tools/update_zendure_controller.sh v14_1_4
```

## Installer behavior

The installer performs package/source-manifest and build-evidence preflight before stopping the productive service. It then:

1. creates a complete hash-recorded rollback backup;
2. preserves `config.json`, Last-Good files, config states, logs, SQLite databases and runtime data;
3. runs the idempotent common config migration;
4. verifies the existing Graph Core V3 database before installation;
5. installs the V14.1.4 status/graph performance and UX changes without rebuilding or historically mutating Graph Core V3;
6. verifies Graph Core V3 again in the final installed tree;
7. starts ZEC and checks controller readiness, Graph V3 readiness and the delivered V14.1.4 UI contracts.

The historical `OPERATING_MODE`/`CONTROL_INTENT` repair belongs to V14.1.3 and is **not rerun** by the V14.1.4 updater.

## Productive field acceptance

After a successful install:

```bash
cd /opt/zendure-controller
python3 tools/v14_field_acceptance.py \
  --base-url http://127.0.0.1:8080 \
  --install-report /tmp/zec_v14_1_4_install_report.json \
  --output /tmp/ZEC_V14_1_4_FIELD_ACCEPTANCE.json \
  --json
```

The field tool is read-only: it publishes no commands, changes no configuration and performs no rollback.
