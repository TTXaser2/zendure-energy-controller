# Übergabe Zendure Energy Controller – V12.11.2-RC20
## Korrigierter Settings-, Config-Runtime- und Recovery-Release

**Build-ID:** `rc20-audit-fix6-20260806`
**Direkt verwendete Basis:** übergebenes, auditidentisches RC20-Paket; dokumentierter Ursprung: V12.11.2-RC19 plus S1.0/S1.1
**Ausgangspunkt des Rebuilds:** auditierter RC20-Quellstand, altes Paket SHA256 `f401207efef3116aee558f709e0beffcc1880eddb91da513cc8f02c1b3bb785b`

## 1. Status

Der alte RC20-Auditstand bleibt nicht freigegeben. Der vorliegende Rebuild schließt alle sechs Blocker, fünf Major-Befunde sowie den Quality- und Dokumentationsbefund. Vollständige Zuordnung: `AUDIT_FIX_VERIFICATION_V12_11_2_RC20.md`.

## 2. Build-Ergebnis

```text
APP_VERSION:       12.11.2-rc20
APP_VERSION_LABEL: V12.11.2-RC20
APP_BUILD_ID:      rc20-audit-fix6-20260806
unittest:          635 bestanden
pytest:            635 bestanden
pytest-Subtests:   677 bestanden
ResourceWarnings:  0
```

Syntax-, JSON-, Registry-, Security-, Manifest-, Patch- und Paketgates sind in `BUILD_VALIDATION_V12_11_2_RC20.md` dokumentiert.

## 3. Installationsvertrag

- unterstützte Quellen: RC19 oder exakt RC20 Fix 5; Ziel: RC20 Fix 6;
- ZIP unter `/home/pi/Downloads/zendure_controller_v12_11_2_rc20.zip`;
- Installer aus dem entpackten neuen Paket starten;
- vollständiger SHA256-Source-Manifest-, Syntax-, Test- und Migrationspreflight vor Dienststopp;
- keine Node.js-Pflicht auf dem Raspberry Pi;
- Vorprüfungsfehler lassen Produktivdienste und `/opt/zendure-controller` unverändert;
- produktive Config, Unknown Keys, Secrets, Last-Good und Laufzeitdaten bleiben erhalten;
- automatische atomare Migration;
- vollständiges `/opt`-Backup plus exaktes Root-Artefakt-Backup;
- automatischer Rollback bei jedem Fehler nach Beginn der Transaktion;
- Erfolg erst nach `ready=true`, Version und Build-ID.

Die genauen Befehle stehen in `README_INSTALLATION.md` und in der externen Releaseübergabe.

## 4. Produktivabnahme

Nach Installation sind gemeinsame Navigation/Statusampel, Settings-Preview, Event-Reconciliation, MAX_SOC-/MIN_SOC-HOLD, StorageStatus, erste Last-Good-Promotion und unveränderte Harvest-/Cross-Charge-/Commandwirkung kontrolliert zu prüfen. Der aktuelle produktive Ausgangsstand kann RC20 Fix 5 sein.

## 5. Exit-Gate

**Release-Exit-Gate: PASS für kontrollierte Installation.**
Keine offenen P0/P1-Buildbefunde. Produktive Feldabnahme bleibt ausdrücklich offen.


## Installer-Hotfix Fix 4 (06.08.2026)

- Der Restart-Route-Test ist hostunabhängig und modelliert den fehlenden Helper explizit.
- Installer-Selbsttests setzen `ZEC_INSTALLER_PREFLIGHT=1`; echte Restart-Subprozesse sind damit technisch gesperrt.
- `ResourceWarning` wird im Preflight als Fehler behandelt.
- Laufzeitdaten unter `logs/` und SQLite-Artefakte sind vom Releasepaket ausgeschlossen.
- Event-Journal-Dateien der Installer-Selbsttests werden ausschließlich unter `/tmp/zec-installer-preflight-<PID>/` angelegt.

## Runtime-Hotfix Fix 5 (06.08.2026)

Der erste vollständige Produktivinstallationslauf deckte einen fehlenden Runtime-Startpfadtest auf. Das Readiness-Snapshot las einen historischen Alias statt des kanonischen Dataclass-Felds. Fix 5 schließt den Befund, prüft alle `ControllerState`-Attributlesungen statisch und validiert `/health` sowie `/ready` zusätzlich über einen echten lokalen HTTP-Start.


## UI-, Ereignis- und SOC-Recovery Fix 6 (06.08.2026)

- Status, Graph und Settings verwenden dieselbe globale Topbar und eine live aktualisierte Statusampel neben „Status“.
- Erwartete `MIN_SOC`-/`MAX_SOC`-Grenzen führen zu neutralem `HOLD` statt zu einem Fehler-`SAFE_STATE`; fehlende/stale Pflichtdaten bleiben fail-closed.
- Verwaiste offene MQTT-/Zendure-Telemetrieereignisse werden bei stabil gesundem Livezustand vollständig auf `resolved` gesetzt, ohne die Historie zu löschen.
- Settings nutzt die verfügbare Breite, ordnet Label/Hilfe/Input/Metadaten vertikal zu, verwendet zwölf fachliche Icons und erlaubt nach Preview-Abbruch eine erneute Prüfung.
- Das Storage-Inventar verwendet einen persistenten inkrementellen Cache und scannt nur neue oder geänderte Dateien.
- Unterstützte Installerquellen sind RC19 oder exakt RC20 Fix 5; Ziel ist `rc20-audit-fix6-20260806`.
