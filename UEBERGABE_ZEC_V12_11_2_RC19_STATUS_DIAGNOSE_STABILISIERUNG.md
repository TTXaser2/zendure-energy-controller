# Übergabe Zendure Energy Controller – V12.11.2-RC19
## Status- und Diagnose-Stabilisierung

**Stand:** 31.07.2026  
**Basis:** finales V12.11.2-RC18-ZIP  
**Scope:** UI-/Diagnosekorrekturen; keine neue Regelstrategie

## 1. Anlass

Nach der RC18-Installation wurden in der modernen Statusseite folgende reale Inkonsistenzen beobachtet:

1. `DISCHARGE` zeigte „Einspeisung wird reduziert“, obwohl Netzbezug reduziert wurde.
2. `STOP_HOLD` zeigte „Netzleistung nahe 0 W“, obwohl lediglich Zendure manuell neutral gehalten wurde.
3. „Rest bis Max-SOC“ konnte in Early-Return-Modi einen alten Wert fortführen.
4. Ein manueller 2.400-W-Festwert mit 2.000-W-Gerätecap zeigte nur das wirksame Ziel und verwendete das angeforderte Ziel für die ETA.
5. Der asynchrone RC18-Local-API-Worker war im Backend vollständig vorhanden, aber in der modernen Oberfläche nur unzureichend sichtbar.
6. Das Update-Skript bezeichnete eine gültige `/ready`-Antwort mit `ready=false` als erfolgreichen Ready-Check.

## 2. Korrekturen

### 2.1 Modus- und Reason-Texte

```text
CHARGE     -> Einspeisung wird reduziert
DISCHARGE  -> Netzbezug wird reduziert
STOP_HOLD  -> Manueller Stopp – Zendure bleibt neutral
```

Die Ableitung erfolgt über exakte Modus-/Intent-/Pfadtokens.

### 2.2 Restkapazität

Die Restkapazität bis Max-SOC wird in der zentralen Housekeeping-Phase jedes Zyklus aktualisiert. Beispiel:

```text
Kapazität 5,28 kWh
SOC 80 %
Max-SOC 99 %
Rest = 5,28 × 19 % = ca. 1,00 kWh
```

### 2.3 Feste Modi

Die Statuskarte trennt künftig:

```text
Angefordert
Wirksames Ziel
Begrenzung
```

Die ETA basiert auf dem wirksamen Ziel. Zendure-Gerätecaps bleiben read-only.

### 2.4 Local API

Die Karte „Controller & Schnittstellen“ zeigt den Worker kompakt. Das Info-Popover enthält Versuch, Erfolg, Snapshotzustand, Request-/Apply-Timing, Fehler, Backoff und Quelle.

### 2.5 Installer

Der Ready-Check wartet maximal 90 Sekunden auf `ready=true` und gibt bei Timeout die letzte gültige Antwort aus.

## 3. Zusätzliche Findings der Vorabprüfung

Korrigiert wurden außerdem:

- falsches `effective_export_power_used_for_control` bei `DISCHARGE_CONTROL` durch Teilstringmatching;
- falsche Local-API-Einschränkung durch Textvergleich statt Zustandsbewertung.

## 4. Sicherheitsabgrenzung

Nicht geändert:

```text
Harvest-Formeln und Zustandsmaschine
AUTO/HOLD/NIGHT
Cross-Charge
Command-Lifecycle und MQTT-Publishsemantik
Resync und Late-Effect-Guard
smartMode-/Flash-Schutz
Offgrid
Configwerte und Defaults
Storage-Retention/Kompression
Measurement-V4-Header
Excel-Lernsimulation
```

## 5. Fixed-Discharge-Status

Der seit RC15 enthaltene Fehlerfix bleibt bestehen. RC19 verbessert Diagnose und ETA, ändert aber den Befehl nicht. Der kontrollierte produktive Abschlussnachweis umfasst weiterhin:

- Erreichen des Ziel-SOC;
- bestätigte 0/0-Neutralisierung;
- physisches Ende der Entladung;
- keine verspätete Altkommandowirkung;
- keine Publish-/Resync-Serie.

## 6. Produktivabnahme nach Installation

1. Version und `/ready=true` prüfen.
2. Local-API-Worker in „Controller & Schnittstellen“ sichtbar prüfen.
3. STOP_HOLD-Text und Restkapazität mit aktuellem SOC prüfen.
4. Fixed-Discharge nur bei ohnehin geplantem kontrolliertem Test prüfen:
   - Requested/Applied/Cap sichtbar;
   - ETA verwendet Applied;
   - sicherer Abschluss.
5. Keine zusätzlichen Commands, Resyncs, `acMode`- oder Richtungswechsel.
