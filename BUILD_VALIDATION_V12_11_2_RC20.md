# Build Validation – Zendure Energy Controller V12.11.2-RC20 Fix 6

**Build-ID:** `rc20-audit-fix6-20260806`  
**Direkte Basis:** produktiv installierbarer RC20 Fix 5 (`rc20-audit-fix5-20260806`)  
**Ziel:** gemeinsame UI-Navigation, Settings-Layoutkorrektur, Event-Reconciliation, korrekte SOC-Grenzmodellierung und inkrementelles Storage-Inventar.

## 1. Test- und Collection-Gates

```text
unittest-Collection:                 635
pytest-Collection:                   635
Collectiondifferenz:                   0

unittest:                            635 bestanden
unittest mit ResourceWarning=Error:  635 bestanden
pytest:                              635 bestanden
pytest-Subtests:                     677 bestanden
ResourceWarnings:                      0
```

## 2. Syntax- und Runtime-Gates

```text
python3 -m py_compile *.py tools/*.py      PASS
node --check static/status_v2.js          PASS
node --check static/settings_v2.js        PASS
bash -n tools/update_zendure_controller.sh PASS
FastAPI/TestClient HTTP-Smoke              PASS
Settings-Playwright-Smoke                  PASS
Graph-Playwright-Smoke                     PASS
Browser-Pageerrors                         0
```

Geprüfte HTTP-Routen:

```text
/                         200
/settings                 200
/graph                    200
/status-view-data         200
/health                   200
/ready                    200
/storage/status           200
```

## 3. Regelungs- und Recovery-Gates

```text
MAX_SOC bei validem SOC                  HOLD, nicht SAFE_STATE
MIN_SOC bei validem SOC                  HOLD, nicht SAFE_STATE
Fehlender/staler SOC                     SAFE_STATE bleibt aktiv
SOC-Grenzneutralisierung                 0 W, Limiter/Grund erhalten
SAFE_STATE-Zähler bei SOC-Grenze         unverändert
Readiness bei gesundem MAX_SOC-HOLD      nicht blockiert
```

AST-Differenz gegenüber Fix 5 in `controller_logic.py`:

```text
Geänderte Methoden:
- ZendureController.handle_charge
- ZendureController.handle_discharge
- ZendureController.handle_night_mode
- ZendureController.pause_fixed_night_discharge_for_reserve_soc

Neue Methode:
- ZendureController.soc_limit_hold

Weitere Reglerfunktionen geändert: 0
```

## 4. Event- und Statusgates

```text
Mehrere verwaiste offene Zeilen je Dedupe-Key     vollständig geschlossen
Gesunder MQTT-Livezustand nach Neustart           alte offene MQTT-Events resolved
Gesunde Zendure-Telemetrie nach Stabilitätsfenster alte offene Telemetrie-Events resolved
Aktives Error-Event                                globaler Status rot/bad
Aktive Warnung                                     globaler Status gelb/warn
Historie                                           bleibt erhalten; keine Löschung
```

## 5. UI-Gates

```text
Status/Graph/Settings verwenden dieselbe Topbar    PASS
Live-Statuspunkt neben „Status“ auf allen Seiten   PASS
Settings-Hauptfläche nutzt verfügbare Breite       PASS
Label/Hilfe/Input/Metadaten vertikal gekoppelt      PASS
12 fachliche Kategorie-Icons                       PASS
Preview-Abbruch ermöglicht erneute Prüfung         PASS
Restart nur bei pending_restart sichtbar           PASS
Desktop- und Mobile-Rendering                      PASS
Graph graphRequestInFlight deklariert               PASS
localStorage-Zugriff fail-safe                      PASS
```

## 6. Storage-Gates

```text
GET /storage/status                               O(1)-Snapshot
Persistenter Inventory-Cache                      PASS
Manifestdaten für bekannte Dateien                PASS
Unveränderte Dateien bei Folgelauf wiederverwendet PASS
Nur neue/geänderte unbekannte Dateien gescannt     PASS
Atomisches Cache-Write mit fsync                   PASS
```

## 7. Installervertrag

Der Installer akzeptiert exakt:

```text
12.11.2-rc19
oder
12.11.2-rc20 / rc20-audit-fix5-20260806
```

Zielidentität:

```text
12.11.2-rc20 / rc20-audit-fix6-20260806
```

Preflight, Backup, Root-Artefakttransaktion, Migration, finaler Testlauf, Ready-/Versions-/Build-ID-Nachweis und automatischer Rollback bleiben aktiv.

## 8. Exit-Gate

**BUILD EXIT-GATE: PASS.**  
Freigegeben für den kontrollierten Übergang von RC20 Fix 5 auf RC20 Fix 6 sowie weiterhin für den direkten RC19→Fix-6-Pfad. Die produktive Feldabnahme bleibt erforderlich.
