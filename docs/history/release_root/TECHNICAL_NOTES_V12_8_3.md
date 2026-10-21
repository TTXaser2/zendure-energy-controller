# Technische Notizen V12.8.4

V12.8.4 erweitert ausschließlich die Analyse-/Replay-Komponente. Der Live-Regelalgorithmus bleibt unverändert.

## Faire Reglerbewertung

Die Analyse trennt nun zwischen:

- Gesamtsystem-Abweichung über alle ausgewählten CSV-Dateien
- regelbarem Zeitfenster
- beeinflussbarer Restabweichung anhand verfügbarer Lade-/Entladereserve
- nicht beeinflussbarer Abweichung durch Safe-State, SOC-Grenzen, Stellgliedsättigung oder fehlende Reserve

Damit wird verhindert, dass z. B. Einspeisung bei MAX_SOC oder am Leistungslimit als Reglerfehler interpretiert wird.

## Neue Analyseblöcke

- Stellreserve / Sättigung
- Zendure Soll-/Ist-Folge
- Oszillation / Richtungswechsel
- Betriebszustandsmatrix
- Deadband-Erfolg
- MQTT-Kommandowirkung
- Handlungsempfehlungen

## Darstellung

Die Analyse-Seite besitzt eine In-Page-Navigation, eine Ampel-Kurzbewertung, Handlungsempfehlungen, einfache CSS-Balkendiagramme und weiterhin ausklappbare Begriffserklärungen. Es werden keine zusätzlichen JavaScript-Bibliotheken verwendet.

## Datenformate

Das technische Messdatenformat bleibt `ZEC-MEASUREMENT-V2` mit Semikolon-Trennzeichen und Dezimalpunkt. Die HTML-/Textdarstellung verwendet deutsche Dezimalkommas. JSON bleibt maschinenlesbar mit numerischen Werten.
