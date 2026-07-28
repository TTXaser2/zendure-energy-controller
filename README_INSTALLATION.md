# Zendure Energy Controller V12.11.2-RC14 – Installation und Verifikation

## 1. Update installieren

Die Datei `zendure_controller_v12_11_2_rc14.zip` unverändert nach `/home/pi/Downloads/` kopieren:

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc14
```

Das Update-Skript erhält die produktive `config.json`, erzeugt ein Backup und installiert das Paket.

## 2. Konfiguration

RC14 ergänzt keinen neuen produktiven Einstellwert. Der bereits in RC13 eingeführte Parameter bleibt:

```json
"COMMAND_EFFECT_TOLERANCE_PERCENT": 10
```

Neu ist ausschließlich seine vollständige Reproduzierbarkeit:

- im Config-Control-Hash,
- in `zec_config_snapshots.json`,
- im Measurement-Manifest.

Eine manuelle Configmigration ist nicht erforderlich.

## 3. Messdatenrotation

RC14 erweitert ZEC-MEASUREMENT-V4 additiv. Vorhandene RC10-, RC11-, RC12- und RC13-Dateien werden nicht verändert. Bei einem älteren Header beginnt der Logger automatisch eine neue Datei mit:

```text
schema_rc14_<Sitzung>
```

Neue Felder:

```text
charge_acceptance_state
charge_acceptance_reason
command_effect_reference_w
```

Die RC13-Felder für Publish-Event-ID, Gate und Neutralisierungsepisode bleiben unverändert erhalten.

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
APP_VERSION = "12.11.2-rc14"
APP_VERSION_LABEL = "V12.11.2-RC14"
```

## 5. Statusfelder prüfen

```bash
curl -fsS http://127.0.0.1:8080/status >/tmp/zec-rc14-status.json
python3 - <<'PY'
import json

with open('/tmp/zec-rc14-status.json', encoding='utf-8') as f:
    s = json.load(f)

for key in (
    'zendure_flash_protection_active',
    'zendure_command_state_complete',
    'zendure_command_smart_mode',
    'zendure_command_ac_mode',
    'zendure_command_input_limit_w',
    'zendure_command_output_limit_w',
    'command_state_gate_state',
    'command_publish_event_id',
    'command_neutralization_episode_id',
    'charge_acceptance_state',
    'charge_acceptance_reason',
    'command_effect_reference_w',
    'command_lifecycle_state',
    'command_effect_state_category',
    'command_effect_state_reason',
):
    print(f'{key:45} {s.get(key, "-")}')
PY
```

Bei stabilem aktiven Betrieb wird weiterhin erwartet:

```text
zendure_flash_protection_active = true
zendure_command_smart_mode      = 1
zendure_command_state_complete  = true
```

`command_state_gate_state` ist ein Diagnose-/Last-Gate-State und nicht allein als globale Readiness-Aussage zu interpretieren.

## 6. Ladeendphase produktiv prüfen

Erwartete Kategorien:

```text
COMMAND_TARGET_TRACKING_EFFECTIVE
COMMAND_PARTIALLY_EFFECTIVE
COMMAND_CHARGE_ACCEPTANCE_LIMITED
COMMAND_MISMATCH_CONFIRMED
```

Bei natürlichem High-SOC-Taper muss RC14 ausgeben:

```text
command_effect_category = COMMAND_CHARGE_ACCEPTANCE_LIMITED
command_lifecycle_state = ACTIVE_ACCEPTANCE_LIMITED
command_effect_confirmed = false
```

Der Grund enthält einen der Subtypen:

```text
HIGH_SOC_CHARGE_LIMITED
HIGH_SOC_NOT_ACCEPTING
```

`command_effect_reference_w` zeigt den bestätigten Referenzwert. Die Kategorie bestätigt ausdrücklich weder exaktes Sollwerttracking noch das Netz-Systemziel.

Während einer solchen Ladeendepisode darf keine periodische `FULL_STATE_RESYNC_SENT`-Serie entstehen.

## 7. Niedrig-SOC-Recovery bleibt aktiv

Ein Fall wie:

```text
SOC 10 %
Soll/Readback +2.397 W
Ist 0 W
```

muss weiterhin zu Mismatch und – nach den bestehenden Timern/Cooldowns – zu einem Full-State-Resync führen. Eine High-SOC-Reklassifikation ist hierbei unzulässig.

## 8. Nacht- und Neutralisierungsregression

RC14 verändert diese Logik nicht. Weiterhin gilt:

- Nachtfenster-Exit: genau ein notwendiger Nullbatch,
- nach physischer 0-W-Bestätigung kein Nullspam,
- aktive Leistungsbefehle nur mit Flash-Schutz,
- Reason-Wechsel bei identischem Nullzustand erzeugt keinen neuen physischen Publish.

## 9. Journal beobachten

```bash
journalctl -u zendure-controller.service -f
```

Relevante Ereignisse/Kategorien:

```text
COMMAND_LIMIT_UPDATED
FULL_STATE_COMMAND_SENT
FULL_STATE_NEUTRALIZATION_SENT
FULL_STATE_RESYNC_SENT
COMMAND_CHARGE_ACCEPTANCE_LIMITED
HIGH_SOC_CHARGE_LIMITED
HIGH_SOC_NOT_ACCEPTING
```

Ein Publish oder Resync ist weiterhin kein Wirkungsnachweis.

## 10. Rollback

Vor einem Rollback Diagnose sichern:

```bash
systemctl status zendure-controller.service --no-pager -l
journalctl -u zendure-controller.service -n 300 --no-pager
curl -fsS http://127.0.0.1:8080/status > /tmp/zec-status-before-rollback.json
```

Rollbackbasis ist die vor der Installation erzeugte Sicherung beziehungsweise RC13. Ein Rollback auf RC13 stellt die bekannte falsche High-SOC-Mismatch-/Resync-Klassifikation wieder her und ist daher nur bei einer neuen RC14-Regression sinnvoll.
