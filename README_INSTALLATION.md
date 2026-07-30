# Zendure Energy Controller V12.11.2-RC17 – Installation und Verifikation

## 1. Voraussetzungen

- bestehende produktive RC16-Installation;
- RC17-ZIP unverändert unter `/home/pi/Downloads/`;
- produktive `config.json` bleibt außerhalb des ZIP und wird vom Update-Skript erhalten.

RC17 führt keine neuen Pflicht-Config-Keys und keine Config-Migration ein.

## 2. Prüfen und installieren

Die konkrete SHA256-Prüfsumme steht in der mitgelieferten externen `.sha256`-Datei und im Release-Manifest.

```bash
set -euo pipefail
cd /home/pi/Downloads
sha256sum -c zendure_controller_v12_11_2_rc17.zip.sha256
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc17
```

Das Update-Skript stoppt nur die zuvor aktiven ZEC-Dienste, erstellt ein Backup, erhält `config.json`, installiert RC17, führt Python-Syntaxchecks und Unit-Tests aus und startet die zuvor aktiven Dienste wieder.

## 3. Unmittelbare Verifikation

```bash
set -euo pipefail

grep -E 'APP_VERSION|APP_VERSION_LABEL' /opt/zendure-controller/version.py

for service in \
  zendure-controller.service \
  zendure-replay.service \
  zendure-status-preview.service
do
  printf '%-40s ' "$service"
  systemctl is-active "$service"
done

curl -fsS http://127.0.0.1:8080/ready | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/status > /tmp/zec-rc17-status.json

python3 - <<'PY'
import json
with open('/tmp/zec-rc17-status.json', encoding='utf-8') as f:
    s = json.load(f)
for key in (
    'current_mode',
    'battery_soc',
    'zendure_flash_protection_active',
    'zendure_command_smart_mode',
    'zendure_command_state_complete',
    'command_state_gate_state',
    'command_readback_matches_desired',
    'command_late_effect_guard_active',
    'rest_surplus_harvest_reason',
    'harvest_target_semantics',
    'harvest_reference_charge_w',
    'harvest_reference_charge_source',
    'harvest_reference_charge_confidence',
    'harvest_reference_charge_age_s',
    'harvest_reference_charge_valid',
    'harvest_reference_fallback_reason',
    'harvest_network_target_w',
    'harvest_total_available_charge_w',
    'harvest_primary_share_target_w',
    'harvest_zendure_share_target_w',
    'harvest_export_capture_target_w',
    'harvest_target_selected_by',
    'harvest_calculation_branch',
    'harvest_entry_min_export_w',
    'harvest_command_path_eligible',
    'harvest_command_path_block_reason',
    'harvest_profile_reserve_w',
):
    print(f'{key:48} {s.get(key, "<fehlt>")}')
PY

journalctl -u zendure-controller.service --since '-20 minutes' --no-pager | tail -n 200
```

Erwartet nach der Startphase:

```text
APP_VERSION = "12.11.2-rc17"
APP_VERSION_LABEL = "V12.11.2-RC17"
zendure_flash_protection_active = true
zendure_command_smart_mode = 1
zendure_command_state_complete = true
command_late_effect_guard_active = false im normalen Betrieb
harvest_profile_reserve_w = 0.0 bei aktiver RC17-Harvest-Rechnung
harvest_network_target_w = 0.0 bei aktiver RC17-Harvest-Rechnung
```

Außerhalb eines aktiven Harvest-Zweigs ist `harvest_target_semantics=NOT_APPLICABLE` korrekt.

## 4. Measurement V4

RC17 besitzt 238 Standardfelder. Ein vorhandener RC16-Header mit 228 Feldern wird erkannt und unverändert belassen; die neue Datei trägt `schema_rc17` im Namen. Ältere RC10–RC15-Header werden ebenfalls weiterhin erkannt und nicht verändert.

## 5. Produktivabnahme

Keine seltenen Fehlerzustände künstlich provozieren. Die Harvest-Branches werden anhand natürlicher Episoden getrennt bewertet:

```text
SMA_NEAR_LIMIT
HIGH_SMA_SOC
HIGH_SMA_SOC_SMA_NEAR_LIMIT
SMA_FULL_OR_IDLE
legitime Hold-Phase, sobald natürlich vorhanden
```

Je Episode sind nachzuweisen:

- Zustand und Reason;
- frische unabhängige Eingangsdaten;
- korrekte Branch-Rechnung und Auswahl;
- unveränderte Smoothing-/Step-/Cap-/Cross-Charge-Pipeline;
- Geräte-Readback und tatsächliche AC-Leistung;
- plausible SOC-/Energiebilanz;
- Restexportkonvergenz Richtung 0 W;
- keine Mismatch-, Resync- oder Same-State-Publish-Serie;
- keine zusätzlichen `acMode`-, 0-W- oder physischen Richtungswechsel.

Für ausreichend stationäre, nicht gecappte, nicht getaperte und nicht Cross-Charge-limitierte Episoden gelten als Auswertungsziele:

```text
Median |control_grid_power_w| <= max(DEADBAND_W, 100 W)
p95   |control_grid_power_w| <= max(2 × DEADBAND_W, 200 W)
```

## 6. Rollback

Das Update-Skript nennt den erzeugten Backup-Pfad. Bei einer neuen RC17-Regression kann auf das unmittelbar zuvor erzeugte RC16-Backup oder auf das unveränderte RC16-ZIP zurückgegangen werden.

RC16 bleibt eine technisch sichere Rückfallebene, enthält jedoch weiterhin die absichtliche Profilreserve und die unvollständige High-SOC-/Near-Limit-Export-Capture-Untergrenze. Es ist daher nicht der fachliche Zielstand.
