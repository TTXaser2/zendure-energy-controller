# Zendure Energy Controller V12.11.2-RC13 – Installation und Verifikation

## 1. Update installieren

Die Datei `zendure_controller_v12_11_2_rc13.zip` unverändert nach `/home/pi/Downloads/` kopieren:

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc13
```

Das Update-Skript erhält die produktive `config.json`, erzeugt ein Backup und installiert das Paket.

## 2. Neuer Default

RC13 ergänzt ausschließlich folgenden Expertenparameter:

```json
"COMMAND_EFFECT_TOLERANCE_PERCENT": 10
```

Bestehende Konfigurationen benötigen keine manuelle Migration. Fehlende Werte werden aus dem Default ergänzt.

Die Einstellung verändert nur die Command-Effect-Diagnose. Sie verändert weder Regler-Sollwerte noch Zendure-Gerätegrenzen.

## 3. Messdatenmigration

RC13 erweitert ZEC-MEASUREMENT-V4 additiv. Vorhandene RC10-, RC11- und RC12-Dateien werden nicht verändert. Bei einem älteren Header beginnt der Logger automatisch eine neue Datei mit:

```text
schema_rc13_<Sitzung>
```

Neue Felder:

```text
command_publish_event_id
command_publish_epoch_s
command_state_gate_state
command_state_retry_remaining_s
command_neutralization_episode_id
```

`command_publish_event` und `command_publish_fields` bleiben Last-Event-Snapshotfelder. Ein tatsächlich neuer Publish ist künftig eindeutig an einer neuen `command_publish_event_id` beziehungsweise `command_publish_epoch_s` und zyklusbezogen an `command_sent_flag=1` erkennbar.

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
APP_VERSION = "12.11.2-rc13"
APP_VERSION_LABEL = "V12.11.2-RC13"
```

## 5. Flash-Schutz und Gate prüfen

```bash
curl -fsS http://127.0.0.1:8080/status >/tmp/zec-rc13-status.json
python3 - <<'PY'
import json

with open('/tmp/zec-rc13-status.json', encoding='utf-8') as f:
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
    'command_state_gate_state',
    'command_state_retry_remaining_s',
    'command_publish_event_id',
    'command_publish_epoch_s',
    'command_neutralization_episode_id',
    'command_lifecycle_state',
    'command_effect_state_category',
):
    print(f'{key:45} {s.get(key, "-")}')
PY
```

Bei stabilem aktivem Regelbetrieb wird erwartet:

```text
zendure_flash_protection_active = true
zendure_command_smart_mode      = 1
zendure_command_state_complete  = true
command_state_gate_state        = READY
```

Nach Start oder Reconnect sind kurzzeitig zulässig:

```text
WAIT_SMART_MODE_READBACK
WAIT_FULL_STATE_READBACK
SAFETY_NEUTRALIZATION_WAITING
```

Während `WAIT_SMART_MODE_READBACK` darf RC13 keine nicht neutralen Limits senden.

## 6. Neutralization-Dedupe prüfen

Bei längeren MIN-SOC-, MAX-SOC- oder Safe-State-Phasen muss die `command_publish_event_id` nach dem initialen Nullbatch stabil bleiben. Wechselnde Reason-Texte dürfen die ID nicht erhöhen, solange der physische Zielzustand unverändert 0/0 bleibt.

Ein erneuter Nullbatch ist nur zulässig bei:

- Command-State-Verlust oder Reconnect,
- tatsächlicher Abweichung der rückgelesenen Limits,
- bestätigtem Neutralization-Mismatch,
- neuem vorherigem Lade-/Entladeintent,
- Ablauf des vorgesehenen Retry-/Recovery-Fensters.

## 7. Ladeendphase beobachten

Relevante Kategorien:

```text
COMMAND_TARGET_TRACKING_EFFECTIVE
COMMAND_PARTIALLY_EFFECTIVE
COMMAND_CHARGE_ACCEPTANCE_LIMITED
COMMAND_MISMATCH_CONFIRMED
```

`COMMAND_CHARGE_ACCEPTANCE_LIMITED` bestätigt nicht das Sollwerttracking. Die Kategorie bedeutet: Command-State und Laderichtung sind bestätigt, das Gerät beziehungsweise BMS nimmt bei hohem SOC aber weniger Leistung an. In diesem Zustand soll keine periodische Full-State-Resync-Serie entstehen.

## 8. Offgrid-Verifikation

RC13 verändert `gridOffMode` nicht. Die Trennung bleibt:

```text
Netzport:   gridInputPower / outputHomePower
Batterie:   outputPackPower / packInputPower
Offgrid:    gridOffPower
```

Der spätere produktive Offgrid-Test erfolgt separat mit ungefährlichem Verbraucher.

## 9. Journal beobachten

```bash
journalctl -u zendure-controller.service -f
```

Relevante Ereignisse:

```text
SMART_MODE_ENABLE_SENT
COMMAND_STATE_WAITING
FULL_STATE_COMMAND_SENT
COMMAND_LIMIT_UPDATED
FULL_STATE_NEUTRALIZATION_SENT
FULL_STATE_RESYNC_SENT
COMMAND_CHARGE_ACCEPTANCE_LIMITED
```

Ein Publish oder Resync ist kein Wirkungsnachweis. Rückgelesener Command-State und physische Wirkung bleiben getrennte Nachweise.

## 10. Rollback

Vor einem Rollback Diagnose sichern:

```bash
systemctl status zendure-controller.service --no-pager -l
journalctl -u zendure-controller.service -n 300 --no-pager
curl -fsS http://127.0.0.1:8080/status > /tmp/zec-status-before-rollback.json
```

Ein Rollback auf RC12 stellt die bestätigte Neutralisierungs-Publish-Flut und die fehlerhafte Gate-Signaturumschaltung wieder her. Er ist daher nur bei einer neuen RC13-Regression sinnvoll.
