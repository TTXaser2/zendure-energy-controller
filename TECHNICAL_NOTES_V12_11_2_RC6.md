# Zendure Energy Controller V12.11.2-RC6

## Zweck

RC6 ist ein eng abgegrenzter UI-/Diagnose-Hotfix auf Basis von V12.11.2-RC5. Der Live-Regelalgorithmus und der MQTT-Kommandopfad wurden nicht verändert.

## Änderungen

### Statusseite

- Unterer Operations-Bereich auf breiten Desktop-Ansichten als vier Karten in einer Reihe.
- Responsive Staffelung:
  - breite Desktop-Ansicht: 4 Spalten,
  - mittlere Breite: 2 × 2,
  - Mobilansicht: 1 Spalte.
- Die Karten werden nicht künstlich auf die Höhe der Ereigniskarte gestreckt.

### Historische Statusseite

- `/status_old` liefert wieder eine funktionsfähige Referenzseite.
- Die nicht mehr vorhandenen historischen Einbettungen für SOC-Graph und Ereignisfeld werden bewusst nicht rekonstruiert.
- Stattdessen zeigt die Referenzseite sichere Verweise auf die aktuelle Statusseite beziehungsweise den separaten alten Graphen.
- Dadurch besteht keine neue Abhängigkeit zwischen Legacy-UI und moderner Statusarchitektur.

### Controller- und Schnittstellenkarte

Technische Rohcodes werden in der sichtbaren Karte in verständliche deutsche Texte übersetzt, unter anderem:

- `ZENDURE_MQTT_OK` → `Aktuell`
- `no_command` → `Noch kein relevantes Kommando`
- `finish_cycle_ms` → `Zyklusabschluss`
- `active` → `Aktiv`
- `queued` → `Aktiv · asynchron`
- `internal_sd` → `Interner Systemdatenträger`

Rohwerte bleiben im ViewModel diagnostisch verfügbar, werden aber nicht als primäre Bedienoberfläche angezeigt.

Der Zendure-Kommandoabgleich benennt weiterhin ausdrücklich den Abgleich von AC-Modus sowie Lade- und Entladelimits.

### Betriebsereignisse

- Semantikfehler der RC5-Deduplizierung behoben: Ein erneut auftretender Vorfall aktualisiert Titel, Schweregrad, Status und Endzeit gemeinsam.
- Ein kürzlich behobener Vorfall kann bei erneutem Auftreten korrekt wieder geöffnet werden.
- Beim Wiederöffnen beginnt die sichtbare Dauer am Beginn des aktuellen Vorfalls; die Anzahl zusammengefasster Vorkommnisse bleibt erhalten.
- Flatternde Ereignisse derselben Kategorie werden innerhalb eines begrenzten 30-Minuten-Fensters zusammengefasst.
- Bereits von RC5 gespeicherte widersprüchliche Telemetrie-Einträge werden bei der Anzeige semantisch normalisiert und für die Darstellung verdichtet. Die historische Datenbank wird dabei nicht destruktiv umgeschrieben.
- Die UI bezeichnet den Zähler als `Vorkommnisse zusammengefasst` statt missverständlich als Wiederholungen.

## Sicherheitsabgrenzung

Unverändert gegenüber RC5:

- AUTO-Regelung
- NIGHT_DISCHARGE
- FIXED-Modi
- Harvest-Logik
- Cross-Charge-Schutz
- Safe-State
- MQTT-Kommandostruktur
- Command-Resync-Entscheidung
- CSV-/Measurement-Schema

Das Betriebsjournal bleibt ein separater Best-Effort-Diagnosethread. Es kann weder einen Sollwert festhalten noch eine MQTT-Sendung, einen Kommandoabgleich oder einen Reglerzyklus verhindern. Es entstehen keine neuen Latches, Race Conditions oder Prioritätsumkehrungen im Steuerpfad.

## Validierung

- Python-Syntaxprüfung für Hauptmodule und Tools
- JavaScript-Syntaxprüfung für `static/status_v2.js`
- vollständige Unit-Test-Suite
- Route-Test: `/status_old` rendert ohne HTTP-500-Ursache
- Browser-Layoutprüfung:
  - 2048 × 1152: vier Karten in einer Reihe
  - 1366 × 1000: 2 × 2
  - 390 × 844: einspaltig
- sichtbare Klartextprüfung für MQTT-Status, Kommandowirkung und langsamsten Timing-Abschnitt
