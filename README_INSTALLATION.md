# Installation – Zendure Energy Controller V12.11.6

**Ziel-Build-ID:** `v12.11.6-20260808`

## 1. Normaler Ausgangsstand

Der reguläre Updatepfad ist:

```text
V12.11.5
APP_VERSION  = 12.11.5
APP_BUILD_ID = v12.11.5-20260807
```

Der Installer akzeptiert zusätzlich die bereits dokumentierten älteren Recovery-Quellen. Ein unbekannter Ausgangsstand wird vor jeder Produktivänderung abgelehnt.

Die bestehende Configmigration bleibt idempotent. Eine vorhandene produktive `config.json` wird nicht durch neue Defaultwerte ersetzt; insbesondere bleibt eine bereits konfigurierte Nachtleistung unverändert.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_11_6.zip
unzip -t zendure_controller_v12_11_6.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v12_11_6
unzip -q zendure_controller_v12_11_6.zip
chmod +x zendure_controller_v12_11_6/tools/update_zendure_controller.sh
bash zendure_controller_v12_11_6/tools/update_zendure_controller.sh v12_11_6
```

Node.js ist keine Produktivvoraussetzung. Ohne Node.js werden die buildseitig geprüften JavaScript-Dateien durch das SHA256-Source-Manifest abgesichert.

## 4. Erwarteter Ablauf

```text
Ausgangsstand erkannt: V12_11_5 ...
V12.11.6-Paket vor dem Stoppen des Produktivdienstes entpacken und prüfen...
Runtime-Readiness-Smoke-Test bestanden.
Paketpreflight und Config-Migrationspreflight bestanden.
Stoppe Dienste...
Erstelle vollständiges Rollback-Backup...
Kopiere V12.11.6-Dateien; config.json, Last-Good und Laufzeitdaten bleiben erhalten...
Führe idempotente bestehende Configmigration aus...
Finale lokale Prüfung im Installationsverzeichnis...
Runtime-Readiness-Smoke-Test bestanden.
Starte Controller...
Installations-Abnahme ...
Update abgeschlossen und Installations-Abnahme erfolgreich.
V12.11.6 erfolgreich installiert.
```

## 5. Unmittelbare Verifikation

```bash
grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' \
  /opt/zendure-controller/version.py

systemctl is-active zendure-controller.service

curl -fsS http://127.0.0.1:8080/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/ready  | python3 -m json.tool
```

Erwartet:

```text
APP_VERSION = "12.11.6"
APP_VERSION_LABEL = "V12.11.6"
APP_BUILD_ID = "v12.11.6-20260808"
Dienst = active
/health alive = true
/ready ready = true   (bevorzugter Normalfall)
```

## 6. V12.11.6 Feldabnahme

Settings:

```text
http://<PI-IP>:8080/settings
```

Prüfen:

1. Nachtbetrieb zeigt **Startzeit** vor **Endzeit**.
2. `25:30` eingeben und das Feld verlassen: sofortige rote Feldmeldung, ohne vorher **Änderungen prüfen** zu klicken.
3. Nach Korrektur kann unmittelbar weitergearbeitet werden.
4. Einen serverseitig ungültigen Mehrfeldfall prüfen: im blockierten Modal ist **Speichern nicht möglich** sichtbar deaktiviert und nicht anklickbar.
5. `Reserve-SOC für feste Nachtentladung`: bei gesetztem Wert lautet die semantische Rücksetzaktion **Reserve-SOC entfernen**, nicht generisch „Auf Default“.
6. Installationsabhängige Werte wie MQTT-Broker besitzen keinen generischen Default-Reset.
7. Feldfolgen in manuellen Profilen, SOC, Harvest, MQTT, Local API und Logging folgen der fachlichen Reihenfolge.
8. Expertenmodus → `System & Diagnose` → `Administrative Aktionen`: Controller-Neustart und Last-Good-Pointer verwenden ZEC-Modals, keine Browser-Systemprompts.
9. Ohne offenen Draft darf der Neustartdialog keine falsche Warnung vor ungespeicherten Änderungen anzeigen.
10. Statusseite → Info-Icon `Controller & Schnittstellen`: vier strukturierte Abschnitte, gut lesbare Kennzahlen und Erläuterungen.

Mobil zusätzlich auf mindestens einer Smartphonebreite:

- Kategorien-Drawer bleibt scrollbar und positionsstabil;
- keine horizontale Dokumentüberbreite;
- Modals bleiben vollständig bedienbar.

## 7. Measurement-V4-Kontrolle

Der Release ändert den Measurement-Vertrag nicht. Optionaler Check:

```bash
cd /opt/zendure-controller
python3 - <<'PY'
import json
from csv_logger import measurement_schema_version
with open('config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)
print('MEASUREMENT_SCHEMA_VERSION =', cfg.get('MEASUREMENT_SCHEMA_VERSION'))
print('effective schema           =', measurement_schema_version(cfg))
PY
```

Erwartet:

```text
MEASUREMENT_SCHEMA_VERSION = 4
effective schema           = 4
```

## 8. Backups und Rollback

Nach Beginn der Produktivtransaktion legt der Installer unter anderem an:

```text
/home/pi/zendure-controller-backup-<Zeitstempel>.tar.gz
/home/pi/config.pre-v12.11.6.<Zeitstempel>.json
/var/backups/zec-v12.11.6-root-artifacts-<Zeitstempel>
```

Diese Sicherungen bis zum Abschluss der Feldabnahme nicht löschen. Bei einem Installationsfehler nach dem Stoppen der Dienste verwendet das Skript den vorhandenen automatischen Rollbackpfad.

## 9. GitHub-Übernahme

Lokales Repository:

```text
C:\github\zendure-energy-controller
```

Das entpackte Release in das Repository spiegeln, `.git` und produktive `config.json` ausnehmen, anschließend `git status` und den Diff prüfen.

Vorschlag:

```text
Commit: Release V12.11.6
Tag:    v12.11.6
```
