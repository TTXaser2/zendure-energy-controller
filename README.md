# Zendure Energy Controller V12.11.6

**Build-ID:** `v12.11.6-20260808`

V12.11.6 ist ein **Settings-/Status-UX-Qualitätsrelease** auf Basis der vollständig validierten V12.11.5. Die energetische Regellogik, Command-Safety, Cross-Charge- und Measurement-V4-Schicht bleiben unverändert.

## 1. Hauptänderungen

### 1.1 Sofortige Eingabevalidierung

Eindeutig lokal prüfbare Fehler werden bereits beim Verlassen eines geänderten Feldes angezeigt:

- Zahlenformat;
- Min-/Max-Grenzen;
- `HH:MM` mit gültigem Bereich `00:00–23:59`;
- Enum-Werte;
- ganzzahlige optionale Overrides und SMA-IDs.

Komplexe Mehrfeld-, Runtime- und Sicherheitsregeln bleiben serverseitig authoritative und werden weiterhin spätestens über **Änderungen prüfen** validiert.

Ein blockierter Preview stellt **Speichern nicht möglich** optisch und funktional eindeutig deaktiviert dar.

### 1.2 Logische Feldreihenfolge

Die Settings-Seite folgt nun fachlicher statt historischer Registry-Reihenfolge. Beispiele:

```text
Nachtfenster:            Start → Ende
SOC-Schutz:              Min-SOC → Max-SOC
Feste Profile:           Leistung → Ziel-SOC → Folgeverhalten
Harvest-Schwellen:       Floor → Restart → Near-Limit
Harvest-Tagesprofil:     Morgen → Mittag → Nachmittag
MQTT:                    Broker → Port → Benutzer → Passwort
Local API:               Aktivierung → IP → Nutzung → Polling/Timeout/Backoff
Datei-Logging:           Aktivierung → Pfad/Datei → Rotation
```

Roh wirkende Harvest-Config-Keys erhalten benutzerverständliche Bezeichnungen; der technische Key bleibt im Expertenmodus sichtbar.

### 1.3 Sichere Default-Semantik

Die UI unterscheidet nun ausdrücklich:

1. **echten Produktdefault** → `Default: …` + **Auf Default setzen**;
2. **bewusst nicht gesetzt** → semantische Entfernen-Aktion;
3. **automatisch/abgeleitet** → **Automatische Berechnung verwenden**;
4. **installations-/hardwareabhängig** → kein generischer Reset;
5. **Referenz-/schutzrelevanter Ausgangswert** → wird angezeigt, aber nicht als universelle Empfehlung angeboten.

Für neue beziehungsweise unvollständige Installationen sind folgende feste Leistungsprofile nun konservativ `0 W`:

```text
NIGHT_DISCHARGE_POWER_W           0 W
MANUAL_FIXED_DISCHARGE_POWER_W    0 W
MANUAL_FIXED_CHARGE_POWER_W       0 W
```

Die zugehörigen Modi bleiben deaktiviert beziehungsweise werden bei Aktivierung ohne bewusst gesetzte positive Leistung durch die bestehende Validation blockiert. Historische Migrationswerte (`400/400/800 W`) bleiben im Registry-Vertrag erhalten; bestehende `config.json`-Werte werden durch das Update nicht überschrieben.

### 1.4 Administrative Aktionen im ZEC-Modal

Native Browser-`confirm()`-Dialoge wurden von der Settings-Seite entfernt.

- **Controller-Dienst neu starten** verwendet ein strukturiertes ZEC-Modal und warnt nur dann vor ungespeicherten Änderungen, wenn tatsächlich ein Draft vorhanden ist.
- **Last-Good-Pointer reparieren** zeigt nach serverseitigem Preview Zielslot, Generation, typed Revision, Config-Hash und Manifest-Hash strukturiert an. Die fail-closed Serverlogik bleibt unverändert.

### 1.5 Strukturierter Info-Popover „Controller & Schnittstellen“

Der bisherige Fließtext ist in vier lesbare Abschnitte gegliedert:

```text
Aktueller Regelzyklus
Statistik · jüngste Durchläufe
Lokale Zendure-API
Einordnung
```

Kennzahlen werden als Label-/Wert-Raster dargestellt; Erläuterungen bleiben vollständig erhalten. Desktopbreite maximal 560 px, mit internem Scrollen bei Bedarf und responsiver Einspaltigkeit auf kleinen Displays.

## 2. Measurement-Vertrag

Produktiv bleibt **ZEC-MEASUREMENT-V4** maßgeblich:

```text
MEASUREMENT_SCHEMA_VERSION = 4
V4 Standard                = 246 Felder
V4 Extended                = 249 Felder
```

Die historische Konstante `version.CSV_SCHEMA = "ZEC-MEASUREMENT-V3"` gehört weiterhin ausschließlich zum Legacy-V3-Kompatibilitätspfad und ist **nicht** die aktive Measurement-Schemaauswahl. Die separate V3-Legacy-Bereinigung ist bewusst nicht Bestandteil von V12.11.6.

## 3. No-Regression-Abgrenzung

V12.11.6 verändert insbesondere nicht:

- AUTO-, HOLD-, NIGHT- oder feste Regleralgorithmen;
- Harvest-Formeln und 0-W-Netzziel;
- Cross-Charge;
- Smart-Mode-/Flash-Schutz;
- Command-State, Readback, Effect, Resync und Late-Effect-Guard;
- Zendure Power Observation;
- Measurement-V4-Writer und -Contract;
- SQLite-Graphstore;
- Excel-Lernsimulation.

Die geschützten Regler-/Command-/Measurementdateien werden im Releasegate bytegenau gegen V12.11.5 geprüft.

## 4. Installation und Validierung

Siehe:

```text
README_INSTALLATION.md
BUILD_VALIDATION_V12_11_6.md
RELEASE_INFO_V12_11_6.md
TECHNICAL_NOTES_V12_11_6.md
ZEC_V12_11_6_RELEASE_REPORT.md
```

## 5. Bewusst spätere Blöcke

Nicht Bestandteil von V12.11.6:

1. V4-only-Runtime / Entfernung des produktiven V3-Schreibpfads;
2. Measurement-Storage-Härtung;
3. benannte Konfigurationsstände sowie Import/Export;
4. Graph-Redesign;
5. weitergehende Experten-/Diagnoseansicht;
6. separater Simulationsdienst.
