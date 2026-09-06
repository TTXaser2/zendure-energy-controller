# Installation – Zendure Energy Controller V14.1.3

**Release:** `V14.1.3`  
**Build-ID:** `v14.1.3-20260906`

## Supported source

This installer accepts **only** the verified productive source:

- Version `14.1.2`
- Build-ID `v14.1.2-20260905`

It does not support downgrade, skip-update or alternate source identities.

## Install

Place the exact package in `/home/pi/Downloads` and verify its SHA256 against the value supplied with the final release. Then run:

```bash
cd /home/pi/Downloads
unzip -t zendure_controller_v14_1_3.zip
rm -rf zendure_controller_v14_1_3
unzip -q zendure_controller_v14_1_3.zip
chmod +x zendure_controller_v14_1_3/tools/update_zendure_controller.sh
bash zendure_controller_v14_1_3/tools/update_zendure_controller.sh v14_1_3
```

## Installer behavior

The installer performs package/source-manifest and build-evidence preflight before stopping the productive service. It then:

1. creates a complete hash-recorded rollback backup;
2. preserves `config.json`, Last-Good files, config states, logs, SQLite databases and runtime data;
3. runs the idempotent common config migration;
4. verifies the existing Graph Core V3 database before mutation;
5. runs the **targeted V14.1.3 state suffix repair** for `OPERATING_MODE` and `CONTROL_INTENT` when Measurement-V4 evidence is available;
6. skips that historical repair without failing the upgrade when no V4 source exists;
7. verifies Graph Core V3 again after the repair;
8. installs sources/services, starts ZEC and checks controller readiness, Graph V3 readiness and the delivered V14.1.3 UI contracts.

The Graph Core database is **preserved**; there is no V4-to-V3 rebuild.

## Productive field acceptance

After a successful install:

```bash
cd /opt/zendure-controller
python3 tools/v14_field_acceptance.py \
  --base-url http://127.0.0.1:8080 \
  --install-report /tmp/zec_v14_1_3_install_report.json \
  --output /tmp/ZEC_V14_1_3_FIELD_ACCEPTANCE.json \
  --json
```

The field tool is read-only: it publishes no commands, changes no configuration and performs no rollback.
