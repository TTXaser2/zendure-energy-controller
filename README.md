# Zendure Energy Controller V12.11.4

**Build-ID:** `v12.11.4-20260807`

V12.11.4 ist ein eng begrenzter Bedienungs- und Diagnose-Bugfix auf Basis von V12.11.3. Der Release korrigiert die mobile Settings-Bedienung, die Ereignis-Reconciliation und kleinere Konsistenzprobleme der Settings-Oberfläche. Die energetische Regelung, die Zielwertbildung, der Command-Lifecycle und das Measurement-V4-Schema bleiben unverändert.

## 1. Korrekturen in V12.11.4

### 1.1 Mobile Settings-Navigation

- Der Burger-Button öffnet jetzt zuverlässig den Kategorien-Drawer.
- Der Drawer ist per Schaltfläche, Hintergrund, Kategorieauswahl und `Escape` schließbar.
- ARIA-Zustände werden korrekt aktualisiert.
- Die akzeptierte horizontal scrollbare globale Hauptnavigation bleibt unverändert erhalten.

### 1.2 Änderungsprüfung auf Mobilgeräten

- Das Vorschau-Modal besitzt einen eigenen vertikalen Scrollbereich.
- Der Seitenhintergrund bleibt bei geöffnetem Modal fixiert.
- Modal-Header und Aktionen bleiben erreichbar.
- Abbrechen, Schließen und erneutes Prüfen funktionieren ohne künstliche Zwischenänderung.

### 1.3 Kategorieposition

Ein normaler Klick auf eine Settings-Kategorie zeigt deren Inhalt jetzt immer von oben. Suchtreffer dürfen weiterhin gezielt zum gefundenen Feld springen.

### 1.4 Ereignis-Reconciliation

Bei gesundem Livezustand werden auch ältere offene MQTT- und Zendure-Telemetrieereignisse geschlossen, deren historische Dedupe-Schlüssel nicht mehr dem aktuellen Schlüssel entsprechen. Die Ereignisse werden nicht gelöscht, sondern auf `resolved` gesetzt.

### 1.5 Warnungsanzeige

Der Warnungszähler der globalen Kopfzeile berücksichtigt offene Warnungs- und Fehlergruppen konsistent mit der Betriebsereigniskarte.

### 1.6 Geschützter manueller Dienstneustart

Im Expertenmodus befindet sich unter **System & Diagnose** wieder eine dauerhaft erreichbare administrative Aktion **„Controller-Dienst neu starten“**. Sie verwendet ausschließlich den bestehenden geschützten Restart-Vertrag; es wird kein frei konfigurierbarer Shellbefehl eingeführt.

### 1.7 Responsive Korrekturen

- Der mobile Settings-Kontextkopf ist zweizeilig strukturiert.
- Unbeabsichtigtes horizontales Dokument-Overflow wird verhindert.
- Die globale Hauptnavigation bleibt als eigener horizontal scrollbarer Bereich erhalten.
- Die feste Änderungsleiste bleibt vollständig erreichbar.

## 2. Bestehender Settings-Vertrag

Die Settings-Oberfläche bietet weiterhin:

- zwölf fachliche Kategorien;
- Standard- und Expertenansicht derselben Konfiguration;
- Suche über Bezeichnung, Beschreibung und Config-Key;
- typisierte serverseitige Validierung;
- Vorschau mit Änderungsdiff vor dem Speichern;
- atomisches Speichern mit Dateirevisions-CAS;
- sichere Secret-Behandlung;
- Trennung von `configured`, `effective` und `pending`;
- Last-Good- und Recovery-Vertrag;
- gemeinsame globale Navigation mit Statusampel.

## 3. Sicherheitsabgrenzung

V12.11.4 verändert nicht:

- AUTO-, HOLD-, NIGHT- oder feste Modi;
- Harvest-Formeln und 0-W-Netzziel;
- MIN-/MAX-SOC-Schutzlogik;
- Cross-Charge;
- Smart-Mode-/Flash-Schutz;
- Command-State-Gate, Readback, Effect, Resync oder Late-Effect-Guard;
- lokale Zendure-API-Architektur;
- Measurement-V4-Header;
- SQLite-Graphstore;
- Excel-Lernsimulation.

Die geschützten Regler- und Commanddateien werden bei der Releasevalidierung bytegenau gegen V12.11.3 verglichen.

## 4. Installation

Siehe `README_INSTALLATION.md`.

## 5. Nächste geplante Entwicklungsschritte

Nicht Bestandteil dieses Bugfixes:

1. Settings-Hilfe, Abschnittserklärungen, Info-Modals und geführte Bedienung;
2. benannte Konfigurationsstände sowie sicherer Import/Export;
3. Graph-Redesign;
4. erweiterte Experten-/Diagnoseansicht;
5. Measurement-Storage-Härtung;
6. separater Simulationsdienst.

Diese Folgeblöcke werden erst nach eigener fachlicher Freigabe umgesetzt.
