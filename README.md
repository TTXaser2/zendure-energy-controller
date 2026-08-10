# Zendure Energy Controller V12.12.0

**Build-ID:** `v12.12.0-20260809`

V12.12.0 ist der Entwicklungsblock **Settings Help & Guided Configuration** auf Basis der vollständig validierten V12.11.7. Schwerpunkt ist eine registry-native, fachlich strukturierte Hilfe für sämtliche operativen Settings sowie deterministische, nicht selbsttätig verändernde Konfigurationshinweise. Regler-, Command-, Cross-Charge- und Measurement-V4-Logik bleiben unverändert.

## 1. Registry-native Hilfe

Die SettingsRegistry bleibt Schemaautorität und trägt nun zusätzlich die Hilfedomäne. Für die produktive Settings-Oberfläche gilt:

```text
Settings gesamt                       212
operative Settings                    171
Settings mit BASE-Hilfe               171 / 171
priorisierte Settings mit RICH-Hilfe   62 / 62
Kategorien mit Hilfe                    12 / 12
Abschnitte mit Hilfe                    69 / 69
```

Die Hilfe umfasst je nach Setting unter anderem:

- Kurzbeschreibung und Zeitpunkt der Wirkung;
- Wirkung beim Erhöhen/Verringern bzw. Ein-/Ausschalten;
- Abhängigkeiten, Gating und Overrides;
- Wertebereich und serverseitigen Validierungsvertrag;
- Risiko-/Sicherheitswirkung;
- Formel und Rechenbeispiel;
- Default-/Profil-Semantik;
- Apply-/Restart-Wirkung;
- Handbuchanker;
- im Expertenmodus zusätzlich technischen Vertrag, Config-Key und Validatoren.

## 2. Guided Configuration

V12.12.0 kann deterministische Konstellationen direkt einordnen, ändert aber **niemals selbstständig Settings**. Beispiele:

- Setting ist aufgrund einer deaktivierten Funktion aktuell ohne Wirkung;
- ein positiver absoluter Harvest-W-Wert übersteuert den zugehörigen Ratio-Wert;
- ein Profil leitet Topics automatisch ab;
- auffällige Kombinationen aus AUTO-Gain, Totzone, Schrittweite oder Glättung;
- Nachtmodus aktiviert, aber feste Leistung 0 W;
- Harvest-Bestätigungszeiten im Verhältnis zum Regelintervall;
- zu kurze Zweitbatterie-Freshness oder fehlender Resync-Cooldown.

Clientseitige Hinweise ersetzen niemals Preview/Validation. Sicherheits-, Laufzeit-, Netzwerk- und Integritätsentscheidungen bleiben serverseitig authoritative.

## 3. Suche und Navigation

Die Settings-Suche berücksichtigt zusätzlich:

- Hilfetexte;
- Synonyme;
- Abschnittsnamen;
- Abhängigkeiten;
- Formeln und fachliche Begriffe;
- technische Config-Keys im zulässigen Sichtbarkeitsmodus.

Standardmodus bleibt Standardmodus: Such- und Hilfenavigation legt keine Expert-Settings unbemerkt offen. Bei einer Beziehung zu einem Expert-Setting wird der Moduswechsel ausdrücklich angeboten.

## 4. Fachlich vertiefte Bereiche

RICH-Hilfe ist insbesondere für folgende Bereiche vollständig hinterlegt:

1. manuelle Betriebsarten;
2. Leistungs- und SOC-Grenzen;
3. AUTO-Regelung;
4. Nachtbetrieb;
5. Harvest / Restüberschuss;
6. Cross-Charge-Schutz;
7. Kommandowirkung & Resync.

Harvest-Hilfe erklärt unter anderem `Floor ≤ Restart ≤ Near-Limit ≤ Pmax`, Ratio-/W-Overrides, Entry-/Hold-Semantik und die Delta-/Absolutziel-Unterscheidung. Command-Hilfe trennt Publish, Richtungsreaktion, Sollwerttracking und Systemziel.

## 5. Aktuelles Handbuch

Die generischen Dateien

```text
docs/Zendure_Energy_Controller_Handbuch.docx
docs/Zendure_Energy_Controller_Handbuch.pdf
```

wurden für V12.12.0 vollständig neu erstellt. Das PDF besitzt 14 Seiten; die Settings-Hilfe verlinkt nur auf tatsächlich verifizierte Seitenanker. Alte anlagenbezogene Pseudodefaults wurden nicht übernommen.

## 6. Measurement-Vertrag

Produktiv bleibt **ZEC-MEASUREMENT-V4** maßgeblich:

```text
MEASUREMENT_SCHEMA_VERSION = 4
V4 Standard                = 246 Felder
V4 Extended                = 249 Felder
```

Der historische V3-Kompatibilitätspfad ist nicht Bestandteil dieses Releases und bleibt ein separater Folgeblock.

## 7. No-Regression

V12.12.0 verändert insbesondere nicht:

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
BUILD_VALIDATION_V12_12_0.md
RELEASE_INFO_V12_12_0.md
TECHNICAL_NOTES_V12_12_0.md
ZEC_V12_12_0_RELEASE_REPORT.md
SPEZIFIKATION_ZEC_V12_12_0_SETTINGS_HELP_GUIDED_CONFIGURATION_V1.0.md
V12_12_0_SETTINGS_HELP_INVENTORY.csv
```
