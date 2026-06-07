# Technische Notizen V12.8.6

V12.8.6 ist eine gezielte Hotfix-Version für Ablauf-/Housekeeping-Probleme im Live-Controller. Ausgangspunkt war eine Beobachtung im Nachtmodus: Über EVCC/MQTT kamen aktuelle Werte der SMA-Zweitbatterie an, die Statusseite zeigte jedoch weiterhin einen alten Entladewert.

## 1. Ziel

Die Version adressiert eine Fehlerklasse, bei der Rohwerte zwar aktualisiert werden, abgeleitete Anzeige-/CSV-/Graph-Werte aber durch frühe Rücksprünge in `run_once()` veralten konnten.

Betroffene Pfade:

- `NIGHT_DISCHARGE`
- `STOP_HOLD`
- `FIXED_DISCHARGE`
- `FIXED_CHARGE`
- Safe-State-Pfade vor der normalen AUTO-Regelung

## 2. Änderungen

### 2.1 Per-cycle Housekeeping

Es wurde ein zyklisches Housekeeping für abgeleitete Werte ergänzt:

- Zweitbatterie-Anzeigewert wird unabhängig vom AUTO-Zweig aktualisiert.
- Zweitbatterie-Entladewert wird aus dem aktuellen MQTT-Rohwert neu berechnet.
- Zendure-Istleistung wird am Zyklusende aus den zuletzt bekannten Rohsensoren und den aktuellen Soll-Limits erneut abgeleitet.

Damit werden UI, Graph und CSV nicht mehr durch alte Ableitungen aus früheren AUTO-Zyklen verfälscht.

### 2.2 Trennung von Anzeige und Cross-Charge-Regelmetrik

Die bisherige `update_sma_metrics()`-Logik wurde fachlich getrennt:

- Anzeige-/CSV-Ableitung der Zweitbatterie: läuft in allen Modi.
- Cross-Charge-/effective-export-Berechnung: läuft nur im AUTO-Zweig nach gültiger Netzleistungsmessung.

Dadurch bleibt Nachtentladung weiterhin unabhängig von Shelly/UniMeter, während SMA-/EVCC-Anzeigen trotzdem aktuell bleiben.

### 2.3 Freshness-/Validitätsflags

Zusätzliche interne Flags und CSV-/Graph-Felder wurden ergänzt:

- `grid_power_valid`
- `grid_power_used_for_control`
- `grid_power_age_s`
- `second_battery_data_fresh`
- `second_battery_used_for_control`
- `second_battery_age_s`
- `effective_export_power_valid`

Diese Felder helfen, zwischen „Wert vorhanden“, „Wert frisch“ und „Wert wurde wirklich für die Regelentscheidung verwendet“ zu unterscheiden.

### 2.4 Thread-Schutz für Zweitbatterie-MQTT-Werte

Die Aktualisierung der Zweitbatterie-Rohwerte aus MQTT erfolgt nun unter dem zentralen `state.lock`.

## 3. Tests

Neue Tests in `tests/test_v12_8_6_housekeeping.py` prüfen:

- Nachtentladung aktualisiert die SMA-/Zweitbatterie-Anzeige trotz frühem Return.
- Stop/Hold aktualisiert die Zweitbatterie-Anzeige auch ohne frischen Zendure-SOC.
- AUTO/Cross-Charge verwendet die aktualisierte Zweitbatterie erst nach gültiger Grid-Messung.
- Zendure-Istleistung wird nach Sollwertänderung im Zyklusfinale neu abgeleitet.

## 4. Bewusst nicht enthalten

V12.8.6 ist kein großer Architekturumbau. Der nächste Entwicklungsblock bleibt wichtig:

- weitere State-/Mode-Matrix-Dokumentation
- konsequente Invarianten-Tests für alle Regelpfade
- stärkere Trennung von Rohwerten, Normalisierung, Regelwerten und Kommandos
- später ggf. größere Refaktorierung des Controller-Zyklus

