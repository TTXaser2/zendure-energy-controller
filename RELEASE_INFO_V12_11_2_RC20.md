# Release Info – Zendure Energy Controller V12.11.2-RC20

**Build-ID:** `rc20-audit-fix6-20260806`

## Zweck

RC20 liefert das Settings-Redesign und den sicheren Config-Runtime-, Preview-/Commit-, Restart-, Last-Good- und Recovery-Unterbau. Dieser Build ist der korrigierte Rebuild des zuvor auditierten, nicht freigegebenen RC20-Pakets.

Der Build enthält zusätzlich den Installer-Hotfix vom 06.08.2026: Node.js ist keine Produktivvoraussetzung, JavaScript-Artefakte werden ohne Node über das Source-Manifest verifiziert, Vorprüfungsfehler greifen nicht in Dienste ein und der ERR-Handler wird nicht mehr doppelt aus einem Subprozess ausgelöst.

## Sichtbare Neuerungen

- zwölf fachliche Settings-Kategorien;
- Standard- und Expertenansicht derselben Konfiguration;
- rechter Such-Drawer auf Desktop, Vollbildsuche mobil;
- mobile aufklappbare Kategorien;
- configured, effective, Default, Wertebereich, Wirkung und Risiko je Setting;
- dynamische Abhängigkeiten und Einzelreset;
- serverseitige Änderungsprüfung vor dem Speichern;
- sichere Secret-Operationen `keep`, `replace`, `clear`;
- Header mit Version, Build-ID/Ready-Status, Configquelle und Handbuchzugang;
- geschützte Pointer-Repair- und Dienstneustart-Aktionen.

## Runtime- und Sicherheitsdelta

- Whole-File-Parsing ohne Clamp oder stille Reparatur;
- atomisches Speichern mit Datei- und Verzeichnis-`fsync`;
- SHA256-File-Revision, Typed-Revision und CAS;
- Unknown-Key-Erhalt;
- strikte configured/effective/pending-restart-Trennung;
- Startup-Recovery mit sichtbar erhaltener invalider Primärconfig;
- Last-Good-A/B-Store mit Dateityp-, `0600`- und `pi:pi`-Prüfung;
- Last-Good-Promotion erst nach 300 s vollständigem Stable-Ready, asynchron und Single-Flight;
- vollständiges Ready-/Recovery-Gate einschließlich Command-, Readback-, Guard-, Lifecycle- und unabhängiger Leistungstelemetrie;
- O(1)-StorageStatus mit asynchronem Inventarrefresh;
- exakter Installer-Rollback einschließlich Restart-Helper und sudoers-Fragment;
- eindeutige Laufzeitkennung `rc20-audit-fix6-20260806`.

## Migration RC19→RC20

Der Installer akzeptiert `12.11.2-rc19` oder exakt `12.11.2-rc20` mit Build-ID `rc20-audit-fix5-20260806` als Ausgangsstand. Vor jedem Dienststopp erfolgen Identitäts-, Test- und Config-Preflights; die Migration ist idempotent.

Die S1.7-Matrix ist explizit und idempotent:

- `ZENDURE_BATTERY_CAPACITY_KWH` → `ZENDURE_BATTERY_CAPACITY_WH`, danach Entfernung des Legacykeys;
- `SMA_DISCHARGE_BLOCK_W` → `CROSS_CHARGE_SIGNIFICANT_W`, sofern konfliktfrei, danach Entfernung;
- sechs nachweislich wirkungslose Legacykeys werden entfernt;
- vier noch produktiv gelesene Kompatibilitätskeys bleiben bewusst bis S2 erhalten;
- unbekannte Erweiterungskeys und Secretwerte bleiben unangetastet.

## Nicht-Ziele

Fix 6 verändert keine energetische Zielwertformel und keine Harvest-, Cross-Charge-, Command- oder MQTT-Strategie. Es korrigiert ausschließlich die Zustandsklassifikation bereits erreichter MIN_SOC-/MAX_SOC-Grenzen von Fehler-`SAFE_STATE` zu neutralem `HOLD`; echte Datenfehler bleiben fail-closed. Last-Good-Promotion und Storage-Inventarisierung erzeugen keine Gerätekommandos.


## Installer-Hotfix Fix 4 (06.08.2026)

- Der Restart-Route-Test ist hostunabhängig und modelliert den fehlenden Helper explizit.
- Installer-Selbsttests setzen `ZEC_INSTALLER_PREFLIGHT=1`; echte Restart-Subprozesse sind damit technisch gesperrt.
- `ResourceWarning` wird im Preflight als Fehler behandelt.
- Laufzeitdaten unter `logs/` und SQLite-Artefakte sind vom Releasepaket ausgeschlossen.
- Event-Journal-Dateien der Installer-Selbsttests werden ausschließlich unter `/tmp/zec-installer-preflight-<PID>/` angelegt.

## Runtime-Hotfix Fix 5 (06.08.2026)

- `readiness_snapshot()` verwendet das kanonische Feld `second_battery_data_valid`.
- Ein AST-Vertrag verhindert künftig undeklarierte `ControllerState`-Attributlesungen.
- `/health` und `/ready` werden mit einem frischen Runtime-State direkt und über einen echten lokalen HTTP-Start geprüft.
- Der Installer führt denselben Runtime-Readiness-Smoke vor dem Dienststopp und erneut nach dem Kopieren aus.
- Der zweite Testlauf im Installationsverzeichnis nutzt ebenfalls den Preflight-Guard und behandelt `ResourceWarning` als Fehler.


## UI-, Ereignis- und SOC-Recovery Fix 6 (06.08.2026)

- Status, Graph und Settings verwenden dieselbe globale Topbar und eine live aktualisierte Statusampel neben „Status“.
- Erwartete `MIN_SOC`-/`MAX_SOC`-Grenzen führen zu neutralem `HOLD` statt zu einem Fehler-`SAFE_STATE`; fehlende/stale Pflichtdaten bleiben fail-closed.
- Verwaiste offene MQTT-/Zendure-Telemetrieereignisse werden bei stabil gesundem Livezustand vollständig auf `resolved` gesetzt, ohne die Historie zu löschen.
- Settings nutzt die verfügbare Breite, ordnet Label/Hilfe/Input/Metadaten vertikal zu, verwendet zwölf fachliche Icons und erlaubt nach Preview-Abbruch eine erneute Prüfung.
- Das Storage-Inventar verwendet einen persistenten inkrementellen Cache und scannt nur neue oder geänderte Dateien.
- Unterstützte Installerquellen sind RC19 oder exakt RC20 Fix 5; Ziel ist `rc20-audit-fix6-20260806`.
