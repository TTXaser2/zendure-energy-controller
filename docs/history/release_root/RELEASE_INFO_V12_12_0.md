# Release Info – Zendure Energy Controller V12.12.0

**Version:** `12.12.0`  
**Label:** `V12.12.0`  
**Build-ID:** `v12.12.0-20260809`

## Zweck

V12.12.0 implementiert **Settings Help & Guided Configuration** auf Basis von V12.11.7. Der Release erweitert die SettingsRegistry um strukturierte Hilfemetadaten, stellt Kategorie-/Abschnitts-/Setting-Hilfe bereit, erweitert die Settings-Suche und zeigt deterministische Konfigurationshinweise ohne automatische Wertänderungen.

## Abdeckung

```text
SettingsRegistry gesamt              212
operative Settings                   171
BASE-Hilfe                           171 / 171
RICH-Hilfe priorisierte Settings      62 / 62
Kategorien                             12 / 12
Abschnitte                             69 / 69
```

## Priorisierte RICH-Bereiche

- Betriebsart und manuelle Steuerung
- Leistungsgrenzen & SOC-Schutz
- AUTO-Regelung
- Nachtbetrieb
- Harvest / Restüberschuss
- Cross-Charge-Schutz
- Kommandowirkung & Resync

## Wichtige fachliche Punkte

- Nachtleistung wird als fester anlagenspezifischer Wert erklärt, nicht als netzleistungsnachgeführte Regelung.
- Harvest dokumentiert Ratio-/W-Override, Hysterese, Entry/Hold und `Floor ≤ Restart ≤ Near-Limit ≤ Pmax`.
- AUTO-Hilfe erklärt Totzone, Gain, Glättung und Stellschritt einschließlich Formeln/Beispielen.
- Command-Hilfe trennt Publish, Richtungsreaktion, Sollwerttracking und Systemziel.
- `CROSS_CHARGE_SIGNIFICANT_W`-Hilfs-/Validierungstext entspricht dem bereits gültigen Serververtrag `> 0 W`; keine Cross-Charge-Logik wurde geändert.

## Handbuch

Das generische Benutzerhandbuch wurde als aktuelle V12.12.0-Fassung neu erstellt:

```text
docs/Zendure_Energy_Controller_Handbuch.docx
docs/Zendure_Energy_Controller_Handbuch.pdf
```

PDF: 14 Seiten. Die Settings-Hilfe verlinkt auf verifizierte Seitenanker.

## No-Regression

Nicht verändert wurden die geschützten Regler-/Command-/Measurementdateien sowie die Excel-Lernsimulation. Measurement V4 bleibt produktiver Vertrag.

## Nicht Bestandteil

- produktiver V3-Legacy-Cleanup
- Regler-/Harvest-/Cross-Charge-Algorithmusänderungen
- Measurement-Storage-Härtung
- benannte Konfigurationsstände / Import / Export
- Graph-Redesign
