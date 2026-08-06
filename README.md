# Zendure Energy Controller V12.11.2-RC20

**Freigegebene Build-ID:** `rc20-audit-fix6-20260806`

V12.11.2-RC20 ist der **Settings-Release** auf Basis von RC19. Dieser Quellstand ist der korrigierte Rebuild des zuvor auditierten und nicht freigegebenen RC20-Pakets. Er ersetzt die bisherige technisch gruppierte Einstellungsseite durch eine fachlich strukturierte, sichere und responsive Oberfläche und führt den dazu notwendigen Config-Runtime-Vertrag ein.

## 1. Neue Settings-Seite

Die neue Oberfläche unter `/settings` bietet:

- zwölf fachliche Kategorien statt historischer Python-/Schema-Gruppen;
- Standard- und Expertenansicht derselben Konfiguration;
- Suche über Bezeichnung, Beschreibung und Config-Key;
- abhängige Felder und klare Aktiv-/Inaktiv-Semantik;
- konfigurierten, tatsächlich wirksamen und Default-Wert getrennt;
- Wertebereich, Einheit, Wirkung, Risiko und Apply-Klasse;
- sichtbare Änderungsmarkierung;
- serverseitige Vorschau vor dem Speichern;
- alte/neue Werte, Validierungsissues, Bestätigungen und Restartbedarf;
- sichere Secret-Operationen `beibehalten`, `ersetzen`, `löschen`;
- mobile Navigation und responsive Karten.

## 2. Config-Runtime-Vertrag

RC20 trennt:

```text
configured = exakte Primär-/Nutzerwerte; bei Fehlern sichtbar, aber nicht wirksam
effective  = vollständig validierte, im laufenden Prozess tatsächlich wirksame Werte
pending    = gültige, aber neustartpflichtige Änderungen
```

Die Python-`SettingsRegistry` ist die einzige Schemaautorität. `config.json` bleibt die persistierte, manuell per SSH editierbare Nutzerkonfiguration.

Externe Änderungen werden als vollständige Whole-File-Transaktion verarbeitet:

```text
stat vorher
→ vollständige Datei lesen
→ stat nachher
→ strikt parsen und vollständig validieren
→ atomar übernehmen oder vollständig verwerfen
```

Es gibt kein Partial Apply, kein Clamp, keine stille Reparatur und keinen Default-Fallback für invalide vorhandene Werte.

## 3. Manuelle Recovery und Headless Mode

Die `config.json` bleibt bewusst manuell editierbar. Eine versehentliche Headless-Aktivierung kann durch:

```json
"HEADLESS_MODE": false
```

ohne Dienstneustart rückgängig gemacht werden, sofern die gesamte Datei valide ist.

Wird die Datei erst im laufenden Betrieb invalid, arbeitet der Controller mit dem letzten gültigen `effective` Snapshot weiter. Die fehlerhafte Datei bleibt unverändert zur Diagnose erhalten.

## 4. Sicheres Speichern

- exakte SHA256-Dateirevision als CAS;
- jede zwischenzeitliche Byteänderung verwirft offene Previews mit `409 Conflict`;
- atomisches Tempfile/`fsync`/`replace`/Verzeichnis-`fsync`;
- Dateimodus `0600`;
- unbekannte Erweiterungskeys bleiben erhalten;
- Secrets erscheinen weder in Modellen, Diffs noch Logs im Klartext;
- alte Schreibendpunkte sind deaktiviert und antworten mit `410 Gone`.

## 5. Last-Good und Startup-Recovery

Nach 300 Sekunden durchgehendem vollständigem Stable-Ready im normalen Betrieb kann die aktive Config asynchron und Single-Flight als Last-Good gefördert werden. Der Store nutzt zwei feste A/B-Slots und einen atomaren Current-Pointer.

Bei invalider oder fehlender Primärconfig:

```text
Recoverycandidate bestimmen
→ passive Quellen-/Freshness-Prüfung
→ bis zum vollständigen Preflight keine Gerätekommandos
→ danach Recovery Active
```

Es gibt keine automatischen Probecommands und keine automatische Pointerreparatur.

## 6. Neustartvertrag

Der freie Config-Key `SERVICE_RESTART_COMMAND` ist entfernt. Ein Neustart erfolgt ausschließlich über den root-eigenen Helper:

```text
/usr/local/sbin/zendure-controller-restart
```

Die Webaktion ist Session-, CSRF-, Origin-, expliziter Bestätigungs-, Single-Flight- und Cooldown-geschützt. Erfolg gilt erst nach `ready=true`, erwarteter Version und Build-ID.

## 7. Migration und Installation

RC20 unterstützt bewusst nur den exakten sequenziellen Übergang:

```text
V12.11.2-RC19 → V12.11.2-RC20
```

Das Update-Skript führt vor dem Stoppen des Produktivdienstes Syntax-, Test- und Migrationspreflight durch, erstellt ein vollständiges Rollback-Backup, migriert die Config eng begrenzt und wartet anschließend bis zu 90 Sekunden auf valides `/ready` mit `ready=true`.

## 8. Unverändert

RC20 verändert keine energetische Zielwertformel und keine bestehende Regelstrategie:

- AUTO, HOLD, NIGHT und feste Modi;
- RC17-Harvest und 0-W-Netzziel;
- Cross-Charge;
- Command-Lifecycle, Resync und Late-Effect-Guard;
- Smart-Mode-/Flash-Schutz;
- Offgrid-Semantik und read-only Gerätecaps;
- Measurement-V4-Header;
- lokale Zendure-API-Architektur;
- Excel-Lernsimulation.

Installation und Verifikation: `README_INSTALLATION.md`.


## 8. Fix 6 – gemeinsame Navigation, SOC-Grenzen und Ereignis-Reconciliation

- Status, Graph und Settings verwenden dieselbe globale Navigation mit live aktualisierter Statusampel.
- Erwartete MIN_SOC-/MAX_SOC-Grenzen werden als neutraler `HOLD` statt als Fehler-`SAFE_STATE` dargestellt.
- Alte offene MQTT-/Telemetrieereignisse werden bei stabil gesundem Livezustand vollständig auf `resolved` gesetzt; die Historie bleibt erhalten.
- Settings nutzt die verfügbare Breite, koppelt Label/Hilfe/Input/Metadaten vertikal, verwendet fachliche Icons und repariert den Preview-Abbruch.
- Das Storage-Inventar arbeitet persistent und inkrementell.
- Der Installer akzeptiert RC19 oder exakt RC20 Fix 5 als Quelle.
