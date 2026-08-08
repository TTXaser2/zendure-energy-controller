# Installation – Zendure Energy Controller V12.11.7

**Ziel-Build-ID:** `v12.11.7-20260808`

## 1. Normaler Ausgangsstand

Der reguläre Updatepfad ist:

```text
V12.11.6
APP_VERSION  = 12.11.6
APP_BUILD_ID = v12.11.6-20260808
```

Der Installer akzeptiert zusätzlich die bereits dokumentierten kompatiblen Recovery-Ausgangsstände. Ein unbekannter Stand wird vor jeder Produktivänderung abgelehnt.

Eine vorhandene produktive `config.json`, Last-Good-Slots und Laufzeitdaten bleiben erhalten. Der neue First-Install-/Defaultvertrag wird **nicht** als Migration auf bestehende Nutzerwerte angewandt.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_11_7.zip
unzip -t zendure_controller_v12_11_7.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v12_11_7
unzip -q zendure_controller_v12_11_7.zip
chmod +x zendure_controller_v12_11_7/tools/update_zendure_controller.sh
bash zendure_controller_v12_11_7/tools/update_zendure_controller.sh v12_11_7
```

Node.js ist keine Produktivvoraussetzung. Ohne Node.js werden die buildseitig geprüften JavaScript-Dateien durch das SHA256-Source-Manifest abgesichert.

## 4. Erwarteter Ablauf

```text
Ausgangsstand erkannt: V12_11_6 ...
V12.11.7-Paket vor dem Stoppen des Produktivdienstes entpacken und prüfen...
Runtime-Readiness-Smoke-Test bestanden.
Paketpreflight und Config-Migrationspreflight bestanden.
Stoppe Dienste...
Erstelle vollständiges Rollback-Backup...
Kopiere V12.11.7-Dateien; config.json, Last-Good und Laufzeitdaten bleiben erhalten...
Führe idempotente bestehende Configmigration aus...
Finale lokale Prüfung im Installationsverzeichnis...
Runtime-Readiness-Smoke-Test bestanden.
Starte Controller...
Installations-Abnahme ...
Update abgeschlossen und Installations-Abnahme erfolgreich.
V12.11.7 erfolgreich installiert.
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
APP_VERSION = "12.11.7"
APP_VERSION_LABEL = "V12.11.7"
APP_BUILD_ID = "v12.11.7-20260808"
Dienst = active
/health alive = true
/ready ready = true   (bevorzugter Normalfall einer bestehenden Installation)
```

## 6. Feldabnahme auf bestehender Installation

Unter:

```text
http://<PI-IP>:8080/settings
```

prüfen:

1. vorhandene produktive Werte sind unverändert;
2. MQTT-Broker, Geräte-/Anlagenwerte, Leistungs- und SOC-Grenzen besitzen keinen generischen Defaultreset;
3. ein echter technischer Produktdefault wie `DEADBAND_W` besitzt weiterhin **Auf Default setzen**;
4. sichere Sentinels werden ausdrücklich als sicherer Ausgangszustand, nicht als Betriebswertempfehlung bezeichnet;
5. optionale/abgeleitete Werte behalten semantische Aktionen wie **Reserve-SOC entfernen** bzw. **Automatische Berechnung verwenden**;
6. Preview/Commit funktioniert weiterhin mit Revision/CAS und serverseitiger Validation.

Ein produktives System mit vorhandener `config.json` darf **nicht** in `FIRST_INSTALL_SETUP` wechseln.

## 7. First-Install-Vertrag

Nur für eine echte Neuinstallation ohne `config.json`:

```text
startup_mode = FIRST_INSTALL_SETUP
control_allowed = false
```

Die UI verlangt die anlagenrelevanten Pflichtwerte. Erst ein vollständig validierter und bestätigter erster Commit erzeugt die kanonische `config.json`. Bis dahin werden keine produktiven Steuerkommandos aufgrund der unvollständigen Setupwerte freigegeben.

## 8. Measurement-V4-Kontrolle

V12.11.7 ändert den Measurement-Vertrag nicht. Optional:

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
/home/pi/config.pre-v12.11.7.<Zeitstempel>.json
/var/backups/zec-v12.11.7-root-artifacts-<Zeitstempel>
```

Diese Sicherungen bis zum Abschluss der Feldabnahme nicht löschen. Bei einem Installationsfehler nach dem Stoppen der Dienste verwendet das Skript den bestehenden automatischen Rollbackpfad.

## 10. GitHub-Übernahme

Lokales Repository:

```text
C:\github\zendure-energy-controller
```

Vorschlag:

```text
Commit: Release V12.11.7
Tag:    v12.11.7
```
