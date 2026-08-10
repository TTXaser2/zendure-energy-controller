# Installation – Zendure Energy Controller V12.12.1

**Ziel-Build-ID:** `v12.12.1-20260810`

## 1. Normaler Ausgangsstand

Der reguläre Updatepfad ist:

```text
V12.12.0
APP_VERSION  = 12.12.0
APP_BUILD_ID = v12.12.0-20260809
```

Der Installer akzeptiert zusätzlich die bereits dokumentierten kompatiblen Recovery-Ausgangsstände. Ein unbekannter Stand wird vor jeder Produktivänderung abgelehnt.

Eine vorhandene `config.json`, Last-Good-Slots und Laufzeitdaten bleiben erhalten. V12.12.1 ändert keine produktiven Nutzerwerte.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_12_1.zip
unzip -t zendure_controller_v12_12_1.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v12_12_1
unzip -q zendure_controller_v12_12_1.zip
chmod +x zendure_controller_v12_12_1/tools/update_zendure_controller.sh
bash zendure_controller_v12_12_1/tools/update_zendure_controller.sh v12_12_1
```

Node.js ist keine Produktivvoraussetzung. Ohne Node.js werden die buildseitig geprüften JavaScript-Dateien durch das Source-Manifest abgesichert.

## 4. Erwarteter Ablauf

```text
Ausgangsstand erkannt: V12_12_0 ...
V12.12.1-Paket vor dem Stoppen des Produktivdienstes entpacken und prüfen...
Runtime-Readiness-Smoke-Test bestanden.
Paketpreflight und Config-Migrationspreflight bestanden.
Stoppe Dienste...
Erstelle vollständiges Rollback-Backup...
Kopiere V12.12.1-Dateien; config.json, Last-Good und Laufzeitdaten bleiben erhalten...
Führe idempotente bestehende Configmigration aus...
Finale lokale Prüfung im Installationsverzeichnis...
Runtime-Readiness-Smoke-Test bestanden.
Starte Controller...
Installations-Abnahme ...
Update abgeschlossen und Installations-Abnahme erfolgreich.
V12.12.1 erfolgreich installiert.
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
APP_VERSION = "12.12.1"
APP_VERSION_LABEL = "V12.12.1"
APP_BUILD_ID = "v12.12.1-20260810"
Dienst = active
/health alive = true
/ready ready = true   (bevorzugter Normalfall)
```

## 6. Feldabnahme V12.12.1

Unter `http://<PI-IP>:8080/settings` bzw. auf der Statusseite mindestens prüfen:

1. RICH-Hilfe eines Harvest-/AUTO-Settings enthält konkrete Bedingungen und Risikoerklärung;
2. ein zweites `i`-Modal startet wieder am Anfang, auch wenn zuvor nach unten gescrollt wurde;
3. Default-/Profil-Semantik ist in getrennte Zeilen für Einordnung und Aktion gegliedert;
4. Suche nach `Totzone` und `Deadband` führt `Netz-Totzone um 0 W` als ersten Treffer;
5. ungültige Nachtzeit zeigt im Preview keinen technischen `Start Minute`-/`End Minute`-Eintrag;
6. `Controller & Schnittstellen` lässt sich bis zum letzten Eintrag intern scrollen und bleibt dabei offen;
7. auf dem Smartphone bleiben globale Navigation, Settings-Kontextleiste und Change-Bar auch bei tiefem Scroll erreichbar;
8. `/manual.pdf` zeigt die V12.12.1-Fassung einschließlich Glossar.

## 7. Handbuch

```text
/opt/zendure-controller/docs/Zendure_Energy_Controller_Handbuch.pdf
```

Die V12.12.1-Fassung besitzt 17 Seiten. Die fachlichen Settings-Anker 4–14 bleiben unverändert; das Glossar beginnt auf Seite 15.

## 8. Browserhinweis

Buildseitig wurden Desktop und mobile Viewports mit Chromium geprüft. Ein automatisierter WebKit-Lauf war in der Buildumgebung nicht möglich, weil kein WebKit-Enginepaket vorhanden war und dessen Nachinstallation wegen fehlender Netzwerk-/DNS-Erreichbarkeit scheiterte. Die reale iPhone-Feldabnahme ist deshalb für die beiden gemeldeten Mobile-Bugs ausdrücklich relevant.

## 9. Backups und Rollback

Nach Beginn der Produktivtransaktion legt der Installer unter anderem an:

```text
/home/pi/zendure-controller-backup-<Zeitstempel>.tar.gz
/home/pi/config.pre-v12.12.1.<Zeitstempel>.json
/var/backups/zec-v12.12.1-root-artifacts-<Zeitstempel>
```

Diese Sicherungen bis zum Abschluss der Feldabnahme nicht löschen. Bei einem echten Fehler nach dem Stoppen der Dienste verwendet das Skript den vorhandenen automatischen Rollbackpfad.

## 10. Git-Übernahme

```text
Commit: Release V12.12.1
Tag:    v12.12.1
```
