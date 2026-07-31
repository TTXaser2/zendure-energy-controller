# Zendure Energy Controller V12.11.2-RC19 – Installation und Verifikation

## 1. Voraussetzungen

- bestehende produktive RC18-Installation;
- `zendure_controller_v12_11_2_rc19.zip` unverändert unter `/home/pi/Downloads/`;
- produktive `config.json` bleibt außerhalb des ZIP und wird vom Update-Skript erhalten.

RC19 führt keine neuen Config-Keys und keine Configmigration ein.

## 2. Prüfen und installieren

Den in der Releaseübergabe genannten SHA256-Wert direkt mit der lokalen Datei vergleichen:

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_11_2_rc19.zip
```

Erst bei exakt passendem Hash:

```bash
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc19
```

Das Update-Skript erstellt ein Backup, erhält `config.json`, führt Syntax- und Unit-Tests aus, startet die zuvor aktiven ZEC-Dienste wieder und wartet maximal 90 Sekunden auf `/ready` mit `ready=true`.

## 3. Unmittelbare Verifikation

```bash
grep -E 'APP_VERSION|APP_VERSION_LABEL' /opt/zendure-controller/version.py

systemctl is-active zendure-controller.service

curl -fsS http://127.0.0.1:8080/ready | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/status > /tmp/zec-rc19-status.json

python3 - <<'PY'
import json

with open('/tmp/zec-rc19-status.json', encoding='utf-8') as handle:
    status = json.load(handle)

for key in (
    'current_mode',
    'battery_soc',
    'zendure_flash_protection_active',
    'zendure_command_smart_mode',
    'zendure_command_state_complete',
    'command_state_gate_state',
    'command_late_effect_guard_active',
    'target_raw_w',
    'target_after_power_limit_w',
    'target_final_w',
    'target_power_limit_reason',
    'zendure_remaining_capacity_kwh',
    'zendure_local_api_worker_state',
    'zendure_local_api_snapshot_sequence',
    'zendure_local_api_success_sequence',
    'zendure_local_api_last_success_age_s',
    'zendure_local_api_snapshot_valid',
    'zendure_local_api_snapshot_stale',
    'zendure_local_api_request_duration_ms',
    'zendure_local_api_snapshot_apply_ms',
    'zendure_local_api_consecutive_errors',
    'zendure_local_api_backoff_remaining_s',
    'zendure_local_api_latest_error_code',
):
    print(f'{key:52} {status.get(key, "<fehlt>")}')
PY

journalctl -u zendure-controller.service \
  --since '-20 minutes' \
  --no-pager \
  | tail -n 250
```

Erwartet nach der Startphase:

```text
APP_VERSION = "12.11.2-rc19"
APP_VERSION_LABEL = "V12.11.2-RC19"
ready = true
zendure_flash_protection_active = true
zendure_command_smart_mode = 1
zendure_command_state_complete = true
Local-API-Snapshot gültig/frisch, sofern Worker aktiviert
```

## 4. UI-Verifikation

Auf der modernen Statusseite prüfen:

1. `DISCHARGE` zeigt „Netzbezug wird reduziert“.
2. `STOP_HOLD` zeigt „Manueller Stopp – Zendure bleibt neutral“.
3. „Rest bis Max-SOC“ passt zu aktuellem SOC, Max-SOC und Kapazität.
4. „Controller & Schnittstellen“ zeigt Local API und API-Hintergrundworker.
5. Das Info-Popover enthält Request-/Apply-Dauer, Snapshot, Fehlerfolge, Backoff und Quelle.

## 5. Feste Modi

Nur im Rahmen eines ohnehin kontrolliert geplanten Tests prüfen:

```text
Angefordert
Wirksames Ziel
Begrenzung
```

Beispiel bei 2.400 W Anforderung und 2.000 W read-only Gerätecap:

```text
Angefordert:     −2,40 kW Entladen
Wirksames Ziel:  −2,00 kW Entladen
Begrenzung:      Zendure-Gerätecap inverseMaxPower = 2.000 W
```

Die ETA muss mit 2.000 W rechnen. Nach Ziel-SOC sind 0/0-Readback und physisch beendete Entladung zu bestätigen.

## 6. Measurement V4

Keine Headerrotation gegenüber RC18:

```text
Standard: 246 Felder · 7842bfef39d47f93
Extended: 249 Felder · 8f61d07e66428a6e
```

## 7. Rollback

Das Update-Skript nennt den erzeugten Backup-Pfad. Bei einer RC19-Regression kann auf dieses RC18-Backup oder auf das unveränderte RC18-ZIP zurückgegangen werden.
