# Build-Validierung – Zendure Energy Controller V12.11.4

**Version:** `12.11.4`  
**Build-ID:** `v12.11.4-20260807`  
**Basis:** `V12.11.3 / v12.11.3-20260806`

## 1. Test- und Collection-Gates

```text
unittest-Collection:                 652
pytest-Collection:                   652
Collectiondifferenz:                   0

unittest:                            652 bestanden
unittest mit ResourceWarning=Error:  652 bestanden
pytest:                              652 bestanden
pytest-Subtests:                     677 bestanden
ResourceWarnings:                      0
```

## 2. Syntax-Gates

```text
Python-Dateien:                       145 · PASS
JavaScript-Dateien:                     2 · PASS
Shell-Dateien:                          9 · PASS
JSON-Dateien:                           6 · PASS
```

## 3. Neue Regressionen

```text
Mobiler Drawer: öffnen/schließen/ARIA/Backdrop       PASS
Kategorieauswahl beginnt oben                         PASS
Suche behält gezielten Feldsprung                     PASS
Modal besitzt eigenen Scrollbereich                   PASS
Hintergrund bei Modal fixiert                         PASS
Bestätigungsaktion mobil erreichbar                   PASS
Abbruch und erneute Prüfung                           PASS
Kein Dokument-Horizontaloverflow                      PASS
Globale Navigation bleibt intern horizontal scrollbar PASS
Geschützter Restart in Expert/System                  PASS
Legacy-MQTT-/Telemetrieevents resolved                PASS
Andere Eventtypen bleiben unberührt                   PASS
Warnungsgruppen konsistent gezählt                    PASS
```

## 4. Dynamischer Browser-Smoke

Geprüft mit Chromium und einem mobilen Viewport `390 × 844`:

- Drawer und Backdrop;
- Kategorienwechsel mit Scroll-Reset;
- Expertmodus und administrative Restart-Aktion;
- langes Änderungsmodal;
- Background-Lock;
- erreichbarer Commit-Button;
- erneute Änderungsprüfung;
- kein Browser-Pageerror;
- kein ungewolltes Dokumentoverflow.

## 5. No-Regression-Vertrag

Folgende Dateien sind gegenüber V12.11.3 byteidentisch:

```text
controller_logic.py
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
measurement_v4.py
measurement_v4_contract.py
```

Damit wurden weder energetische Zielwerte noch Command-, Cross-Charge- oder Measurement-Verträge verändert.

## 6. Installervertrag

Unterstützte Ausgangsstände:

```text
V12.11.3 / v12.11.3-20260806
V12.11.2-RC20 / rc20-audit-fix6-20260806
V12.11.2-RC20 / rc20-audit-fix5-20260806
V12.11.2-RC19
```

Zielidentität:

```text
12.11.4 / v12.11.4-20260807
```

Preflight, vollständiges Backup, Root-Artefakttransaktion, idempotente Configmigration, finaler Testlauf, Installations-Abnahme und automatischer Rollback bleiben aktiv.

## 7. Exit-Gate

```text
BUILD EXIT-GATE: PASS
```

Freigegeben für die kontrollierte Installation. Die produktive Feldabnahme bleibt erforderlich.
