# Zendure Energy Controller V12.11.5

**Build-ID:** `v12.11.5-20260807`

V12.11.5 ist ein eng begrenzter **Settings-UX-Bugfix** auf Basis der verifizierten V12.11.4-Quelle. Die energetische Regelung, Zielwertbildung, Command-Safety und der Measurement-V4-Vertrag bleiben unverändert.

## 1. Korrekturen in V12.11.5

### 1.1 Desktop-Settings als feste Scroll-Shell

- Globale Navigation, Settings-Kontextkopf, Kategorienbereich und Change-Set-Leiste bleiben stationär.
- Die rechte Settings-Inhaltsfläche ist der primäre vertikale Scrollbereich.
- Die Kategorienleiste scrollt nur bei eigenem Überlauf.
- Ein normaler Kategoriewechsel beginnt am Anfang der Kategorie; Suchtreffer dürfen weiterhin gezielt zu einem Feld springen.
- Unbeabsichtigtes horizontales Dokumentscrollen bleibt unterbunden.

### 1.2 Nachtfenster als zwei logische Zeitfelder

Im Standard- und Expertenmodus erscheinen genau zwei fachliche Eingaben:

```text
Startzeit des Nachtmodus  HH:MM
Endzeit des Nachtmodus    HH:MM
```

Der bestehende technische Config-Vertrag bleibt unverändert:

```text
NIGHT_START_HOUR
NIGHT_START_MINUTE
NIGHT_END_HOUR
NIGHT_END_MINUTE
```

Eine geänderte logische Uhrzeit wird im Preview-/Save-Payload paarweise atomar übertragen. Im Änderungsdiff wird das Nachtfenster logisch zusammengefasst. Über-Mitternacht-Zeiträume bleiben zulässig.

### 1.3 Semantische Preview-Validierung

Ein fachlich blockierter Server-Preview mit:

```text
HTTP 422
status = blocked
issues[]
```

wird nicht mehr als Netzwerk-/Transportfehler dargestellt. Die UI:

- zeigt die vollständigen Validierungsprobleme;
- markiert betroffene Settings;
- bietet den Sprung zum betreffenden Feld;
- behält den Draft unverändert;
- sperrt Speichern, solange der Preview blockiert ist;
- erlaubt nach Korrektur sofort erneut **Änderungen prüfen**.

409-Konflikte und 403-Sicherheitsfehler erhalten eigene verständliche Meldungen; unerwartete Fehler werden ohne rohe Exceptiontexte gekapselt.

### 1.4 Mobiler Kategorien-Drawer

- Der Body wird beim geöffneten Drawer positionsstabil gesperrt.
- Der Drawer besitzt einen eigenen vertikalen Scrollbereich.
- Overscroll-Chaining wird begrenzt, ohne eine globale `touchmove`-Sperre einzuführen.
- Backdrop, `Escape` und Kategorieauswahl schließen den Drawer.
- Die globale mobile Hauptnavigation bleibt separat horizontal scrollbar.

### 1.5 Last-Good-Reparatur nur im Experten-Adminbereich

Die Aktion befindet sich ausschließlich unter:

```text
Experte
→ System & Diagnose
→ Administrative Aktionen
→ Last-Good-Konfigurationsspeicher
```

Die serverseitige fail-closed Auswahl- und Revalidierungslogik bleibt unverändert. Das Frontend wählt keinen Slot und verändert durch diese Aktion keine normalen Settings.

### 1.6 Sichtbarkeitsgerechte Kategorien und Empty-State

Kategoriezähler berücksichtigen nur im aktuellen Modus tatsächlich sichtbare logische Settings. Hat eine Kategorie im Standardmodus ausschließlich Expertenparameter, erscheint ein erklärender Empty-State mit Anzahl der ausgeblendeten Expertenparameter und der Aktion **Expertenmodus anzeigen**.

## 2. Bestehender Settings-Vertrag

Unverändert erhalten bleiben unter anderem:

- zwölf fachliche Kategorien;
- Standardmodus und Expertenmodus als Superset;
- Suche über Bezeichnung, Beschreibung und Config-Key;
- typisierte serverseitige ValidationEngine;
- Preview vor Commit;
- atomisches Speichern mit Revision/CAS;
- sichere Secret-Behandlung;
- `configured` / `effective` / `pending_restart`;
- Last-Good-A/B-Store und Recovery-Verträge;
- geschützte administrative Aktionen.

## 3. Sicherheits- und No-Regression-Abgrenzung

V12.11.5 verändert nicht:

- AUTO-, HOLD-, NIGHT- oder feste Modi;
- Harvest-Formeln und 0-W-Netzziel;
- MIN-/MAX-SOC-Schutzlogik;
- Cross-Charge;
- Smart-Mode-/Flash-Schutz;
- Command-State-Gate, Readback, Effect, Resync oder Late-Effect-Guard;
- lokale Zendure-API-Architektur;
- Measurement-V4-Header und -Semantik;
- SQLite-Graphstore;
- Excel-Lernsimulation.

Die geschützten Regler-/Command-/Measurementdateien werden im Releasegate bytegenau gegen V12.11.4 geprüft.

## 4. Installation und Validierung

Siehe:

```text
README_INSTALLATION.md
BUILD_VALIDATION_V12_11_5.md
RELEASE_INFO_V12_11_5.md
TECHNICAL_NOTES_V12_11_5.md
```

## 5. Nicht Bestandteil dieses Bugfixes

Unverändert spätere Entwicklungsblöcke sind insbesondere:

1. redaktioneller Ausbau der Settings-Hilfe und Info-Modals;
2. benannte Konfigurationsstände sowie Import/Export;
3. Graph-Redesign;
4. erweiterte Experten-/Diagnoseansicht;
5. Measurement-Storage-Härtung;
6. separater Simulationsdienst.

Diese Punkte benötigen jeweils einen eigenen fachlichen Scope und eine eigene Buildfreigabe.
