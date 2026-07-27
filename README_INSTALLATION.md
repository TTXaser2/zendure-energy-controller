# Zendure Energy Controller V12.11.2-RC12 – Installation und Verifikation

## 1. Update installieren

Die Datei `zendure_controller_v12_11_2_rc12.zip` unverändert nach `/home/pi/Downloads/` kopieren:

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc12
```

Das Update-Skript erhält die produktive `config.json`, erzeugt ein Backup und installiert das Paket.

## 2. Neue Defaults

RC12 ergänzt folgende Expertenparameter:

```json
"ZENDURE_COMMAND_STATE_FRESH_SECONDS": 30,
"ZENDURE_SMART_MODE_RETRY_SECONDS": 30,
"ZENDURE_COMMAND_STATE_RETRY_SECONDS": 30
```

Bestehende Konfigurationen benötigen keine manuelle Migration. Fehlende Werte werden aus den Defaults ergänzt.

Bedeutung:

- Command-Readbacks gelten standardmäßig 30 Sekunden als frisch.
- Ein nicht bestätigtes `smartMode=1` wird höchstens einmal pro Retry-Fenster angefordert.
- Ein vollständiger Command-State wird bei ausbleibender Rücklesung höchstens einmal pro Retry-Fenster erneut gesetzt.

## 3. Messdatenmigration

RC12 erweitert ZEC-MEASUREMENT-V4 additiv. Vorhandene RC10- und RC11-Dateien werden nicht verändert. Der Logger beginnt automatisch eine neue Datei mit:

```text
schema_rc12_<Sitzung>
```

Ein manueller CSV-Umbau ist nicht erforderlich.

## 4. Dienst und Version prüfen

```bash
systemctl status zendure-controller.service --no-pager -l

echo
echo "=== Ready-Status ==="
curl -fsS http://127.0.0.1:8080/ready | python3 -m json.tool

echo
echo "=== Installierte Version ==="
grep -E 'APP_VERSION|APP_VERSION_LABEL' /opt/zendure-controller/version.py
```

Erwartet:

```text
APP_VERSION = "12.11.2-rc12"
APP_VERSION_LABEL = "V12.11.2-RC12"
```

## 5. Flash-Schutz und Command-State prüfen

Nach dem Start darf ein aktiver Lade- oder Entladebefehl erst ausgeführt werden, wenn `smartMode=1` und der vollständige Command-State rückgelesen wurden.

```bash
curl -fsS http://127.0.0.1:8080/status >/tmp/zec-rc12-status.json
python3 - <<'PY'
import json

with open('/tmp/zec-rc12-status.json', encoding='utf-8') as f:
    s = json.load(f)

for key in (
    'zendure_flash_protection_active',
    'zendure_flash_protection_reason',
    'zendure_command_state_complete',
    'zendure_command_state_reason',
    'zendure_command_smart_mode',
    'zendure_command_ac_mode',
    'zendure_command_input_limit_w',
    'zendure_command_output_limit_w',
    'zendure_device_inverse_max_power_w',
    'zendure_device_charge_max_limit_w',
    'zendure_grid_off_mode',
    'zendure_offgrid_power_w',
    'command_lifecycle_state',
    'command_effect_state_category',
):
    print(f'{key:45} {s.get(key, "-")}')
PY
```

Bei aktivem dynamischem Regelbetrieb wird erwartet:

```text
zendure_flash_protection_active = true
zendure_command_smart_mode      = 1
zendure_command_state_complete  = true
```

Unmittelbar nach Start oder Reconnect kann kurzzeitig `COMMAND_STATE_VERIFYING` erscheinen. Währenddessen hält RC12 aktive dynamische Limitänderungen zurück, anstatt unbestätigt in den potenziell persistenten Gerätepfad zu schreiben.

## 6. Offgrid-Verifikation

Ohne angeschlossene Offgrid-Last gilt normalerweise:

```text
zendure_offgrid_power_w = 0
```

Bei später genutzter Notstromsteckdose müssen die Diagnosewerte getrennt bleiben:

```text
Netzport:   gridInputPower / outputHomePower
Batterie:   outputPackPower / packInputPower
Offgrid:    gridOffPower
```

Eine Batterieentladung ausschließlich für den Offgrid-Ausgang darf eine netzseitig bestätigte 0-W-Neutralisierung nicht als Fehler markieren.

## 7. Journal beobachten

```bash
journalctl -u zendure-controller.service -f
```

Relevante Zustände:

```text
SMART_MODE_ENABLE_SENT
COMMAND_STATE_WAITING
FULL_STATE_COMMAND_SENT
COMMAND_LIMIT_UPDATED
FULL_STATE_NEUTRALIZATION_SENT
FULL_STATE_RESYNC_SENT
COMMAND_CHARGE_ACCEPTANCE_LIMITED
```

`FULL_STATE_RESYNC_SENT` ist kein Wirkungsnachweis. Erst die nachfolgende physische Telemetrie darf eine Recovery bestätigen.

## 8. Betriebsregeln bis zur Produktivvalidierung

- Zendure-App nicht parallel für Modus- oder Leistungsänderungen verwenden.
- `gridOffMode`, `inverseMaxPower`, `chargeMaxLimit`, `socSet` und `minSoc` nicht durch externe Automationen verändern.
- Nach einem Zendure-Geräteneustart prüfen, dass RC12 `smartMode=1` erneut bestätigt.
- Offgrid-Steckdose zunächst nicht mit kritischer Infrastruktur produktiv belasten, bevor ein kontrollierter Test mit ungefährlichem Verbraucher erfolgt ist.

## 9. Rollback

Vor einem Rollback Diagnose sichern:

```bash
systemctl status zendure-controller.service --no-pager -l
journalctl -u zendure-controller.service -n 300 --no-pager
curl -fsS http://127.0.0.1:8080/status > /tmp/zec-status-before-rollback.json
```

Ein Rollback auf RC11 entfernt die automatische Überwachung und Wiederherstellung von `smartMode=1`. Nach einem Rollback muss der Flash-Schutz daher erneut manuell geprüft werden.
