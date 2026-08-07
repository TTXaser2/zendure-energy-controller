# Installation – Zendure Energy Controller V12.11.4

**Ziel-Build-ID:** `v12.11.4-20260807`

## 1. Unterstützte Ausgangsstände

Der Installer akzeptiert ausschließlich:

```text
V12.11.3 mit APP_BUILD_ID=v12.11.3-20260806
oder
V12.11.2-RC20 mit APP_BUILD_ID=rc20-audit-fix6-20260806
oder
V12.11.2-RC20 mit APP_BUILD_ID=rc20-audit-fix5-20260806
oder
V12.11.2-RC19
```

Ein unbekannter Ausgangsstand wird vor jeder Produktivänderung abgelehnt. Die bestehende RC19→RC20-Configmigration läuft idempotent und darf bei bereits migrierten Installationen `no_op` ergeben.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_11_4.zip
unzip -t zendure_controller_v12_11_4.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

Das Update-Skript muss aus dem neu entpackten Paket gestartet werden:

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v12_11_4
unzip -q zendure_controller_v12_11_4.zip
chmod +x zendure_controller_v12_11_4/tools/update_zendure_controller.sh
bash zendure_controller_v12_11_4/tools/update_zendure_controller.sh v12_11_4
```

Node.js ist keine Produktivvoraussetzung. Ohne Node.js werden die buildseitig geprüften JavaScript-Dateien über das SHA256-Source-Manifest verifiziert.

## 4. Erwarteter Ablauf

```text
Ausgangsstand erkannt: V12_11_3 ...
V12.11.4-Paket vor dem Stoppen des Produktivdienstes entpacken und prüfen...
Runtime-Readiness-Smoke-Test bestanden.
Paketpreflight und Config-Migrationspreflight bestanden.
Stoppe Dienste...
Erstelle vollständiges Rollback-Backup...
Kopiere V12.11.4-Dateien...
Führe idempotente bestehende Configmigration aus...
Finale lokale Prüfung im Installationsverzeichnis...
Runtime-Readiness-Smoke-Test bestanden.
Starte Controller...
Installations-Abnahme ...
Update abgeschlossen und Installations-Abnahme erfolgreich.
V12.11.4 erfolgreich installiert.
```

Der Installer bevorzugt `ready=true`. Ein ausschließlich stabiler, sicherer Limit-Readback-Übergang darf nach dem bestehenden V12.11.3-Abnahmevertrag ebenfalls ohne Rollback akzeptiert werden. Echte Daten-, Command-, Guard- oder Controllerfehler bleiben harte Rollbackgründe.

## 5. Unmittelbare Verifikation

```bash
grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' \
  /opt/zendure-controller/version.py

systemctl is-active zendure-controller.service

curl -fsS http://127.0.0.1:8080/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/ready  | python3 -m json.tool
```

Erwartete Paketidentität:

```text
APP_VERSION = "12.11.4"
APP_VERSION_LABEL = "V12.11.4"
APP_BUILD_ID = "v12.11.4-20260807"
Dienst = active
/health alive = true
```

## 6. UI-Abnahme

Browserseiten:

```text
http://<PI-IP>:8080/
http://<PI-IP>:8080/graph
http://<PI-IP>:8080/settings
```

Auf Mobilgeräten prüfen:

1. Burger öffnet das Kategorienmenü.
2. Auswahl einer Kategorie schließt den Drawer und beginnt am Kategorienanfang.
3. Suche funktioniert weiterhin und springt zum Treffer.
4. Ein längeres Änderungsmodal lässt sich intern scrollen.
5. Der Hintergrund bleibt währenddessen fixiert.
6. Bestätigungsaktionen sind erreichbar.
7. Nach Abbruch ist „Änderungen prüfen“ erneut möglich.
8. Kein unbeabsichtigtes horizontales Dokumentscrollen; die globale Navigationszeile bleibt separat horizontal scrollbar.

Auf Desktop im Expertenmodus prüfen:

```text
System & Diagnose
→ Administrative Aktionen
→ Controller-Dienst neu starten
```

Die Aktion nur testweise ausführen, wenn ein kontrollierter Dienstneustart gewünscht ist.

## 7. Ereignis-Reconciliation

Bei aktuell gesunder MQTT- und Zendure-Telemetrie sollten alte Meldungen wie:

```text
MQTT-Verbindung getrennt
Zendure-Telemetrie nicht aktuell
```

nicht mehr als `open` erscheinen. Sie bleiben als `resolved` in der Historie erhalten.

## 8. Backups und Rollback

Nach Beginn der Produktivtransaktion gibt der Installer konkrete Pfade aus für:

```text
/opt-Gesamtbackup
Config-Backup
Root-Artefakt-Backup
```

Diese Sicherungen bis zum Abschluss der Feldabnahme nicht löschen. Bei einem Installationsfehler stellt das Skript Installationsverzeichnis, systemd-/Helper-Artefakte und vorherigen Dienstzustand automatisch wieder her.

## 9. GitHub-Übernahme

Lokales Repository:

```text
C:\github\zendure-energy-controller
```

Das entpackte Paket in das Repository spiegeln, ohne `.git` und ohne produktive `config.json`:

```powershell
robocopy "C:\Temp\zendure_controller_v12_11_4" "C:\github\zendure-energy-controller" /MIR /XD .git /XF config.json
```

Danach:

```text
git status prüfen
Commit: Release V12.11.4
Tag: v12.11.4
Push origin
```
