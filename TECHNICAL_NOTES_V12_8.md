# Technische Notizen V12.8

## Ziel

V12.8 erweitert die Analysebasis aus V12.7, ohne den Live-Regelalgorithmus zu verändern. Der Schwerpunkt liegt auf Bewertung von Reglerqualität, Cross-Charge-Verhalten und Datenqualität.

## Analyse-Weboberfläche

Der optionale Dienst bleibt getrennt vom Live-Regler:

```text
zendure-controller.service  -> Live-Regelung, Port 8080
zendure-replay.service      -> Analyse, Port 8090
```

Der Live-Regler importiert keine Analyse-Module aus `tools/`.

## Mehrdatei-Analyse

Die Analyse kann mehrere CSV-Dateien im Schema `ZEC-MEASUREMENT-V2` zusammenführen. Die Dateien werden nach Zeitstempel sortiert, offensichtliche Duplikate werden entfernt und jede Datei wird einzeln gegen das aktuelle Schema validiert.

Schutzgrenzen:

```text
max_files:        10
max_total_bytes:  50 MB
max_rows:         500.000
```

Bei Überschreitung bricht die Analyse mit einer verständlichen Fehlermeldung ab.

## Datenqualität

V12.8 wertet aus:

```text
Messpunkte
Analysezeitraum
avg/median/min/max dt_s
Datenlücken
fehlende Netzwerte
fehlende Zendure-SOC-Werte
fehlende Zendure-Istleistungswerte
SAFE_STATE-Zeiten
```

## Reglerqualität

Neue Kennzahlen:

```text
mittlere absolute Netzabweichung
Median der absoluten Netzabweichung
95%-Perzentil der absoluten Netzabweichung
Zeit im Zielband
Zeit mit relevantem Netzbezug
Zeit mit relevanter Einspeisung
MQTT-Kommandos pro Stunde
Moduswechsel pro Stunde
Sollwertsprünge
Sollwert-Richtungswechsel
Regelgüte nach Betriebsmodus
```

## Cross-Charge

V12.8 erweitert die Cross-Charge-Auswertung:

```text
Blockade-Ereignisse
Blockade-Zeit
kritische Überschneidung: Zusatzbatterie entlädt + Zendure lädt
max./durchschnittliche SMA-Entladeleistung während Überschneidung
max./durchschnittliche Zendure-Ladung während Überschneidung
verhinderte oder reduzierte Zendure-Ladung grob geschätzt
Ampelbewertung grün/gelb/rot
Ereignisliste
```

## High-SOC

High-SOC-Ladeannahme bleibt in V12.8 bewusst nur eine leichte Diagnose. Der Fokus liegt nicht auf dem letzten Prozent Batteriekapazität, sondern auf Reglerqualität und Cross-Charge-Verhalten.

## UI-Korrekturen

- Der Link von der Hauptoberfläche zur Analyse nutzt den aktuellen Hostnamen des Browsers und ist nicht mehr fest auf `127.0.0.1` gesetzt.
- Die Analyseoberfläche enthält einen Rücklink zur normalen Controller-Weboberfläche.
- Die Diagnoseboxen auf der Statusseite sind in der gewünschten Reihenfolge sortiert.
- Der Kurzverlauf-Graph hat eine feste Höhe, damit der Diagnosebereich beim Auto-Refresh nicht springt.

## Bewusst nicht umgesetzt

Nicht Bestandteil von V12.8:

```text
Umstellung auf SQLite/Datenbankdatei
dauerhaftes historisches Betriebsprotokoll über Logrotationen hinweg
automatische Parameteroptimierung
Simulation alternativer Regelparameter
tiefe High-SOC-Spezialanalyse
Änderungen am Live-Regelalgorithmus
```
