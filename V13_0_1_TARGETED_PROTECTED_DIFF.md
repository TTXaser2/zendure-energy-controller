# V13.0.1 – Targeted Protected Diff / No-Regression-Nachweis

Vergleichsbasis: final ausgeliefertes V13.0.0.

## Byteidentische geschützte Produktionspfade

Die folgenden Dateien bleiben in V13.0.1 byteidentisch zu V13.0.0:

```text
controller_logic.py
cross_charge.py
command_lifecycle.py
instance_owner.py
measurement_v4.py
measurement_v4_contract.py
measurement.py
measurement_db.py
csv_logger.py
state.py
mqtt_bridge.py
zendure_power_observation.py
config_bundle.py
config_states.py
graph_config_timeline.py
tools/backfill_graph_config_timeline.py
settings_registry.py
settings_runtime.py
settings_service.py
settings_apply_policy.py
web_ui.py
static/status_v2.js
static/settings_v2.js
```

Damit verändert der Hotfix weder die produktive Regelalgorithmik noch die V13.0.0-Konfigurationsstands-/Graphhistorienimplementierung.

## Bewusst geänderte Produktionsdateien

```text
version.py
tools/evaluate_installation_readiness.py
tools/update_zendure_controller.sh
```

Alle weiteren Änderungen betreffen Release-/Installationsdokumentation und Test-Erwartungen/Regressionstests für die neue Patch-Version.
