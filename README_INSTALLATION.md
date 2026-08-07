# Installation – Zendure Energy Controller V12.11.5

**Ziel-Build-ID:** `v12.11.5-20260807`

## 1. Unterstützte Ausgangsstände

Der Installer akzeptiert ausschließlich die ausdrücklich freigegebenen Quellidentitäten:

```text
V12.11.4 mit APP_BUILD_ID=v12.11.4-20260807
oder
V12.11.3 mit APP_BUILD_ID=v12.11.3-20260806
oder
V12.11.2-RC20 mit APP_BUILD_ID=rc20-audit-fix6-20260806
oder
V12.11.2-RC20 mit APP_BUILD_ID=rc20-audit-fix5-20260806
oder
V12.11.2-RC19
```

Für den normalen V12.11.4→V12.11.5-Pfad ist ausschließlich die erste Zeile relevant. Ein unbekannter Ausgangsstand wird **vor jeder Produktivänderung** abgelehnt. Die bestehende RC19→RC20-Configmigration bleibt idempotent und darf bei bereits migrierten Installationen `no_op` ergeben.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_11_5.zip
unzip -t zendure_controller_v12_11_5.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

Das Update-Skript muss aus dem neu entpackten V12.11.5-Paket gestartet werden:

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v12_11_5
unzip -q zendure_controller_v12_11_5.zip
chmod +x zendure_controller_v12_11_5/tools/update_zendure_controller.sh
bash zendure_controller_v12_11_5/tools/update_zendure_controller.sh v12_11_5
```

Node.js ist keine Produktivvoraussetzung. Ohne Node.js werden die buildseitig geprüften JavaScript-Dateien über das SHA256-Source-Manifest abgesichert.

## 4. Erwarteter Ablauf

```text
Ausgangsstand erkannt: V12_11_4 ...
V12.11.5-Paket vor dem Stoppen des Produktivdienstes entpacken und prüfen...
Runtime-Readiness-Smoke-Test bestanden.
Paketpreflight und Config-Migrationspreflight bestanden.
Stoppe Dienste...
Erstelle vollständiges Rollback-Backup...
Kopiere V12.11.5-Dateien...
Führe idempotente bestehende Configmigration aus...
Finale lokale Prüfung im Installationsverzeichnis...
Runtime-Readiness-Smoke-Test bestanden.
Starte Controller...
Installations-Abnahme ...
Update abgeschlossen und Installations-Abnahme erfolgreich.
V12.11.5 erfolgreich installiert.
```

Der Installer bevorzugt `ready=true`. Ein ausschließlich stabiler, sicherer Limit-Readback-Übergang darf nach dem bestehenden Abnahmevertrag ebenfalls ohne Rollback akzeptiert werden. Echte Daten-, Command-, Guard- oder Controllerfehler bleiben harte Rollbackgründe.

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
APP_VERSION = "12.11.5"
APP_VERSION_LABEL = "V12.11.5"
APP_BUILD_ID = "v12.11.5-20260807"
Dienst = active
/health alive = true
```

## 6. V12.11.5 Feldabnahme – Settings

Browserseite:

```text
http://<PI-IP>:8080/settings
```

### Desktop

1. Globale Navigation, Settings-Kontextkopf und Change-Set-Leiste bleiben beim Scrollen stationär.
2. Primär scrollt nur die rechte Settings-Inhaltsfläche; die Kategorienleiste bei eigenem Überlauf separat.
3. Normaler Kategoriewechsel beginnt am Kategorienanfang.
4. Suche darf weiterhin gezielt zu einem Treffer springen.
5. Es gibt kein unbeabsichtigtes horizontales Dokumentscrollen.
6. Im Nachtbetrieb erscheinen genau zwei logische Zeitfelder `Startzeit` und `Endzeit` im Format `HH:MM`.
7. Ein absichtlich ungültiger Mehrfeldfall – beispielsweise `MIN_SOC_PERCENT > MAX_SOC_PERCENT` – erscheint als fachlich blockierter Preview mit Issues und Sprung zum Feld, nicht als HTTP-/Netzwerkfehler.
8. Nach Korrektur kann **Änderungen prüfen** ohne künstliche Zwischenänderung erneut ausgeführt werden.
9. Im Standardmodus zeigt `Kommandowirkung & Resync` bei ausschließlich ausgeblendeten Expertenparametern den Empty-State und sichtbaren Count `0`.
10. Im Expertenmodus sind dort die Expertenparameter sichtbar.

### Administrative Aktion

Nur im Expertenmodus prüfen:

```text
System & Diagnose
→ Administrative Aktionen
→ Last-Good-Konfigurationsspeicher
```

Die Last-Good-Aktion darf **nicht** in der globalen Change-Set-Leiste erscheinen. Sie nur ausführen, wenn tatsächlich eine Pointer-Reparatur erforderlich und beabsichtigt ist.

### Mobil

Auf mindestens einem Smartphone beziehungsweise einer vergleichbaren Browserbreite prüfen:

1. Burger öffnet den Kategorien-Drawer.
2. Der Hintergrund bleibt positionsstabil gesperrt.
3. Der Drawer selbst lässt sich vertikal scrollen.
4. Backdrop, `Escape` oder Kategorieauswahl schließen den Drawer.
5. Nach dem Schließen wird die vorherige Hintergrundposition wiederhergestellt.
6. Die globale Hauptnavigation bleibt separat horizontal scrollbar.

## 7. Backups und Rollback

Nach Beginn der Produktivtransaktion gibt der Installer konkrete Pfade aus für:

```text
/opt-Gesamtbackup
/home/pi/config.pre-v12.11.5.<Zeitstempel>.json
/var/backups/zec-v12.11.5-root-artifacts-<Zeitstempel>
```

Diese Sicherungen bis zum Abschluss der Feldabnahme nicht löschen. Tritt während der Installation nach dem Stoppen der Dienste ein Fehler auf, führt das Skript den vorgesehenen **automatischen Rollback** von Installationsverzeichnis, Root-/systemd-Artefakten und Dienstzustand durch.

Für einen später bewusst ausgelösten manuellen Rückbau nicht lediglich einzelne Dateien überschreiben, sondern das vom Installer erzeugte vollständige Rollback-Backup verwenden.

## 8. GitHub-Übernahme

Lokales Repository:

```text
C:\github\zendure-energy-controller
```

Das entpackte Paket in das Repository spiegeln, ohne `.git` und ohne produktive `config.json`:

```powershell
robocopy "C:\Temp\zendure_controller_v12_11_5" "C:\github\zendure-energy-controller" /MIR /XD .git /XF config.json
```

Danach:

```text
git status prüfen
Commit: Release V12.11.5
Tag: v12.11.5
Push origin
```
