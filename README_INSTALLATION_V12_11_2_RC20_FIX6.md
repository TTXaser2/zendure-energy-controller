# Installation – Zendure Energy Controller V12.11.2-RC20 Fix 6

**Ziel-Build-ID:** `rc20-audit-fix6-20260806`

## 1. Unterstützte Ausgangsstände

Der Installer akzeptiert ausschließlich:

```text
V12.11.2-RC19
oder
V12.11.2-RC20 mit APP_BUILD_ID=rc20-audit-fix5-20260806
```

Ein unbekannter RC20-Stand wird vor jeder Produktivänderung abgelehnt. Beim Übergang von Fix 5 ist die bereits migrierte Config zulässig; die RC19→RC20-Migration läuft idempotent und darf `no_op` ergeben.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_11_2_rc20.zip
unzip -t zendure_controller_v12_11_2_rc20.zip
```

Der SHA256 muss exakt dem Wert der aktuellen Releaseübergabe entsprechen.

## 3. Installieren

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v12_11_2_rc20
unzip -q zendure_controller_v12_11_2_rc20.zip
chmod +x zendure_controller_v12_11_2_rc20/tools/update_zendure_controller.sh
bash zendure_controller_v12_11_2_rc20/tools/update_zendure_controller.sh v12_11_2_rc20
```

Node.js ist keine Produktivvoraussetzung. Ohne Node.js werden die buildseitig geprüften JavaScript-Dateien über das SHA256-Source-Manifest verifiziert.

## 4. Erwarteter Ablauf

```text
Ausgangsstand erkannt: RC20_FIX5 ...
RC20-Paket vor dem Stoppen des Produktivdienstes entpacken und prüfen...
Runtime-Readiness-Smoke-Test bestanden.
Paketpreflight und Config-Migrationspreflight bestanden.
Stoppe Dienste...
Erstelle vollständiges Rollback-Backup...
Kopiere RC20-Dateien...
Führe exakte RC19->RC20-Configmigration aus...
Finale lokale Prüfung im Installationsverzeichnis...
Runtime-Readiness-Smoke-Test bestanden.
Starte Controller...
Update abgeschlossen und Ready-Check erfolgreich.
RC20 erfolgreich installiert und ready.
```

## 5. Unmittelbar verifizieren

```bash
grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' /opt/zendure-controller/version.py
systemctl is-active zendure-controller.service
curl -fsS http://127.0.0.1:8080/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/ready | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/status-view-data | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/storage/status | python3 -m json.tool
```

Erwartet:

```text
APP_VERSION = "12.11.2-rc20"
APP_VERSION_LABEL = "V12.11.2-RC20"
APP_BUILD_ID = "rc20-audit-fix6-20260806"
Dienst = active
/health alive = true
/ready ready = true
```

Bei 100 % Zendure-SOC beziehungsweise erreichtem `MAX_SOC_PERCENT` ist der korrekte Zustand:

```text
current_mode = HOLD
active_limiters enthält MAX_SOC
control_reason = Ladung beendet: Maximal-SOC erreicht
ready = true, sofern alle übrigen Gates gesund sind
```

`SAFE_STATE` bleibt für echte Daten-, Command- oder Laufzeitfehler reserviert.

## 6. UI-Abnahme

Browserseiten:

```text
http://<PI-IP>:8080/
http://<PI-IP>:8080/graph
http://<PI-IP>:8080/settings
```

Prüfen:

- identische globale Navigation auf Status, Graph und Settings;
- live roter/gelber/grüner Punkt neben „Status“;
- Settings-Kategorien mit eigenen Icons;
- breite Hauptfläche ohne unnötigen Außenrand;
- Label, Erklärung, Eingabe und Metadaten zusammenhängend linksbündig;
- „Änderungen prüfen“ nach Abbruch erneut möglich;
- Neustartaktion nur bei `pending_restart` sichtbar.

## 7. Alte offene Ereignisse

Alte MQTT-/Zendure-Telemetrieereignisse werden nicht gelöscht. Sobald der aktuelle Livezustand stabil gesund ist, werden sämtliche offenen Zeilen desselben Incident-Schlüssels auf `resolved` gesetzt. Damit bleibt die Historie auditierbar, während die Statusampel nur aktive Probleme signalisiert.

## 8. Backups

Der Installer gibt bei erfolgreichem Beginn der Produktivtransaktion die konkreten Pfade für:

```text
/opt-Gesamtbackup
Config-Backup
Root-Artefakt-Backup
```

aus. Diese Pfade bis zum Abschluss der Feldabnahme nicht löschen.
