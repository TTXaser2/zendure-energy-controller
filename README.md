# Zendure Energy Controller V12.12.1

**Build-ID:** `v12.12.1-20260810`

V12.12.1 ist der Quality-Fix für **Settings Help & Guided Configuration** auf Basis der produktiv validierten V12.12.0. Schwerpunkt sind fachlich tiefere RICH-Hilfen, verständliche Terminologie, ein Glossar, präziseres Suchranking und robuste Help-/Status-Interaktionen auf Desktop und Mobilgeräten. Regler-, Command-, Cross-Charge- und Measurement-V4-Logik bleiben unverändert.

## 1. Hilfequalität

Der Coverage-Vertrag aus V12.12.0 bleibt bestehen:

```text
Settings gesamt                       212
operative Settings                    171
Settings mit BASE-Hilfe               171 / 171
priorisierte Settings mit RICH-Hilfe   62 / 62
Kategorien mit Hilfe                    12 / 12
Abschnitte mit Hilfe                    69 / 69
```

Für alle 62 RICH-Settings sind die Kerninformationen jetzt konkret statt generisch: tatsächliche Wirksamkeitsbedingungen, Abhängigkeiten/Vorrangregeln und konkrete Risiko-/Sicherheitswirkung.

## 2. Terminologie und Glossar

Normale Benutzertexte verwenden bevorzugt verständliche deutsche Begriffe. Beispiele:

- Aktualität / Datenalter statt unkommentiertem `Freshness`;
- Freigabebedingung statt unkommentiertem `Eligibility`;
- Änderungsrisiko statt `Registry-Risikoklasse`;
- serverseitige Validierungsregel statt `Serververtrag`;
- vollständige 0-W-Zustandsneutralisierung mit Erklärung statt `Full-State-Neutralisierung`.

Das aktuelle Benutzerhandbuch besitzt ein eigenes Kapitel **Begriffe und Abkürzungen**. Interne technische Keys und Fachbegriffe dürfen im Expertenvertrag weiter sichtbar sein, werden aber benutzerseitig eingeordnet.

## 3. Help-/Validation-UX

- jedes neu geöffnete Help-Modal startet oben;
- Default-/Profil-Semantik wird als strukturierte Einordnung plus verfügbare Aktion dargestellt;
- Compound-Validation von Nachtstart/-ende bleibt auf dem logischen HH:MM-Feld und zeigt keine internen `Hour`-/`Minute`-Komponenten;
- `Warum?` führt bei Compoundfehlern zur logischen Setting-Hilfe;
- Suchranking priorisiert sichtbaren Titel, exakte Synonyme und Config-Key vor Freitexttreffern.

## 4. Status-Info und Mobile

`Controller & Schnittstellen` besitzt einen eigenen scrollbaren Info-Inhalt. Internes Scrollen schließt das Panel nicht mehr. Auf kleinen Viewports wird es als viewportnahes Panel mit explizitem Schließen und eigenem Scrollkontext dargestellt.

In den Settings ist auf Mobilgeräten der rechte Inhalt der vertikale Scroll-Owner. Globale Navigation, Settings-Kontextleiste und Change-Bar bleiben dadurch auch bei tiefem Scroll erreichbar.

## 5. Handbuch

Die generischen Dateien

```text
docs/Zendure_Energy_Controller_Handbuch.docx
docs/Zendure_Energy_Controller_Handbuch.pdf
```

wurden auf V12.12.1 aktualisiert. Das Handbuch besitzt 17 Seiten; die bisherigen fachlichen Seitenanker 4–14 bleiben stabil, das Glossar beginnt auf Seite 15.

## 6. Measurement-Vertrag

Produktiv bleibt **ZEC-MEASUREMENT-V4** maßgeblich:

```text
MEASUREMENT_SCHEMA_VERSION = 4
V4 Standard                = 246 Felder
V4 Extended                = 249 Felder
```

Der historische V3-Kompatibilitätspfad ist nicht Bestandteil dieses Releases.

## 7. No-Regression

V12.12.1 verändert insbesondere nicht:

- AUTO-, HOLD-, NIGHT- oder feste Regleralgorithmen;
- Harvest-Zielwertbildung und 0-W-Netzziel;
- Cross-Charge-Logik;
- SmartMode-/Command-/Readback-/Resync-Logik;
- Zendure Power Observation;
- Measurement-V4-Writer und -Contract;
- Excel-Lernsimulation.

## 8. Releasebelege

Siehe:

```text
README_INSTALLATION.md
BUILD_VALIDATION_V12_12_1.md
RELEASE_INFO_V12_12_1.md
TECHNICAL_NOTES_V12_12_1.md
ZEC_V12_12_1_RELEASE_REPORT.md
V12_12_0_TO_V12_12_1_CHANGED_FILES.txt
```
