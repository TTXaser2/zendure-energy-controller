# Technical Notes – Zendure Energy Controller V12.12.0

## 1. Help-Domain

Neue Datei `settings_help.py` kapselt immutable Hilfsmodelle und die fachlichen Hilfemetadaten. Die SettingsRegistry bleibt Schemaautorität; `settings_model.py` projiziert Registry + Help-Domain in das Webmodell.

Strukturierte Setting-Hilfe umfasst je nach Level:

```text
short / extended
Wirkung erhöhen / verringern / ein / aus
Dependencies mit Relation
Override-Semantik
Risiko
Formel
Beispiel
Option-Hilfe
Suchbegriffe/Synonyme
Evidence-/Validator-Referenzen
Handbuchanker
```

## 2. Coverage-Vertrag

V12.12.0 erzwingt per Regressionstest:

```text
212 Registry-Settings
171 operative Settings mit BASE-Hilfe
62 priorisierte operative Settings mit RICH-Hilfe
12 Kategorien mit Hilfe
69 operative Abschnitte mit Hilfe
```

## 3. Search

`settings_v2.js` durchsucht zusätzlich Bezeichnung, Config-Key, Kategorie, Abschnitt, Beschreibung, Help-Text, Formeln, Overrides, Suchbegriffe, Dependencies und Option-Hilfe. Die Sichtbarkeitsregeln des aktuellen Standard-/Expertenmodus bleiben erhalten.

Der Search-Drawer wurde über die sticky Settings-Chrome gehoben (`z-index`), damit der Schließen-Button und die Suchergebnisse nicht von der Contextbar überlagert werden.

## 4. Guided Configuration

Guided Configuration ist rein deterministisch und read-only gegenüber der Config. Es schreibt keine Werte und ersetzt die serverseitige Preview-/ValidationEngine nicht.

Verwendet werden nur bereits fachlich vorhandene Schwellen/Beziehungen, unter anderem:

- AUTO: Totzone/Gain/Step, Mittelwertfenster, Intervall/Glättung, Mindeständerung;
- Harvest: Entry-Confirm relativ zum Regelintervall, Restexportschwelle, Step/Glättung;
- Cross-Charge: Zweitbatterie-Freshness;
- Command: Resync-Cooldown;
- Nacht: Leistung vs. Aktivierung/Maxleistung sowie Reserve vs. SOC-Grenzen;
- Local API: Timeoutrelation zum Regelintervall.

## 5. Preview-Hilfe

Blocking Issues behalten ihre serverseitige Autorität. Im Preview können betroffene Settings über `Warum?` direkt in die fachliche Hilfe verzweigen. Mehrere betroffene Keys werden einzeln navigierbar dargestellt; `effective_source` wird als wirksame Quelle erklärt.

## 6. Handbuch

Das aktuelle Handbuch wurde neu erzeugt und umfasst 14 verifizierte Seiten:

1. Titel
2. Settings / Hilfe / Guided Configuration
3. First Install / Defaultsemantik
4. Manuelle Modi
5. Leistungs- und SOC-Grenzen
6. AUTO-Regelung
7. Nachtbetrieb
8. Primärspeicher & SMA
9. Harvest / Restüberschuss
10. Cross-Charge
11. Kommandowirkung & Resync
12. Geräte & Schnittstellen
13. Measurement V4 / Storage
14. System & Diagnose

Die DOCX-Ausgabe wurde vollständig gerendert und jede Seite visuell geprüft. Das daraus erzeugte PDF wurde separat gerendert und auf 14 Seiten verifiziert.

## 7. Registry-Korrektur

Nur Hilfs-/Validierungstext von `CROSS_CHARGE_SIGNIFICANT_W` wurde an den bereits geltenden Validatorvertrag angepasst:

```text
bei aktivem Cross-Charge > 0 W
```

Die geschützte Datei `cross_charge.py` ist unverändert.

## 8. Version / Installer

Zielidentität:

```text
APP_VERSION       = 12.12.0
APP_VERSION_LABEL = V12.12.0
APP_BUILD_ID      = v12.12.0-20260809
```

Regulärer Installer-Ausgangsstand ist V12.11.7 / `v12.11.7-20260808`. Ältere ausdrücklich unterstützte Recovery-Ausgangsstände bleiben erhalten.
