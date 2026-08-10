# Installation – Zendure Energy Controller V12.12.0

**Ziel-Build-ID:** `v12.12.0-20260809`

## 1. Normaler Ausgangsstand

Der reguläre Updatepfad ist:

```text
V12.11.7
APP_VERSION  = 12.11.7
APP_BUILD_ID = v12.11.7-20260808
```

Der Installer akzeptiert zusätzlich die bereits dokumentierten kompatiblen Recovery-Ausgangsstände. Ein unbekannter Stand wird vor jeder Produktivänderung abgelehnt.

Eine vorhandene `config.json`, Last-Good-Slots und Laufzeitdaten bleiben erhalten. V12.12.0 ändert keine produktiven Nutzerwerte allein aufgrund neuer Hilfemetadaten.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_12_0.zip
unzip -t zendure_controller_v12_12_0.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v12_12_0
unzip -q zendure_controller_v12_12_0.zip
chmod +x zendure_controller_v12_12_0/tools/update_zendure_controller.sh
bash zendure_controller_v12_12_0/tools/update_zendure_controller.sh v12_12_0
```

Node.js ist keine Produktivvoraussetzung. Ohne Node.js werden die buildseitig geprüften JavaScript-Dateien durch das Source-Manifest abgesichert.

## 4. Erwarteter Ablauf

```text
Ausgangsstand erkannt: V12_11_7 ...
V12.12.0-Paket vor dem Stoppen des Produktivdienstes entpacken und prüfen...
Runtime-Readiness-Smoke-Test bestanden.
Paketpreflight und Config-Migrationspreflight bestanden.
Stoppe Dienste...
Erstelle vollständiges Rollback-Backup...
Kopiere V12.12.0-Dateien; config.json, Last-Good und Laufzeitdaten bleiben erhalten...
Führe idempotente bestehende Configmigration aus...
Finale lokale Prüfung im Installationsverzeichnis...
Runtime-Readiness-Smoke-Test bestanden.
Starte Controller...
Installations-Abnahme ...
Update abgeschlossen und Installations-Abnahme erfolgreich.
V12.12.0 erfolgreich installiert.
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
APP_VERSION = "12.12.0"
APP_VERSION_LABEL = "V12.12.0"
APP_BUILD_ID = "v12.12.0-20260809"
Dienst = active
/health alive = true
/ready ready = true   (bevorzugter Normalfall)
```

## 6. Feldabnahme Settings Help

Unter:

```text
http://<PI-IP>:8080/settings
```

mindestens prüfen:

1. `i` an Kategorie, Abschnitt und Setting öffnet das ZEC-Hilfemodal;
2. `AUTO-Regelung → Netz-Totzone um 0 W` zeigt RICH-Hilfe und Handbuchanker;
3. Suche nach `Totzone`/`Deadband` findet dieselbe Einstellung;
4. im Standardmodus werden Expert-Settings nicht still durch Suche oder Abhängigkeiten offengelegt;
5. `Harvest / Restüberschuss` erklärt Profilwerte, Ratio-/W-Override und Schwellenzusammenhang;
6. Guided-Hinweise ändern keine Werte automatisch;
7. Preview-/Commit und serverseitige Validation funktionieren unverändert;
8. `/manual.pdf` öffnet die aktuelle V12.12.0-Fassung.

## 7. Handbuch

Der generische Handbuchlink zeigt auf:

```text
/opt/zendure-controller/docs/Zendure_Energy_Controller_Handbuch.pdf
```

Die V12.12.0-Fassung besitzt 14 Seiten. Settings-Hilfe verwendet verifizierte `#page=`-Anker.

## 8. Measurement-V4

V12.12.0 ändert den Measurement-Vertrag nicht. Optional:

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

Erwartet produktiv:

```text
MEASUREMENT_SCHEMA_VERSION = 4
effective schema           = 4
```

## 9. Backups und Rollback

Nach Beginn der Produktivtransaktion legt der Installer unter anderem an:

```text
/home/pi/zendure-controller-backup-<Zeitstempel>.tar.gz
/home/pi/config.pre-v12.12.0.<Zeitstempel>.json
/var/backups/zec-v12.12.0-root-artifacts-<Zeitstempel>
```

Diese Sicherungen bis zum Abschluss der Feldabnahme nicht löschen. Bei einem echten Fehler nach dem Stoppen der Dienste verwendet das Skript den vorhandenen automatischen Rollbackpfad.

## 10. Git-Übernahme

Vorschlag:

```text
Commit: Release V12.12.0
Tag:    v12.12.0
```
