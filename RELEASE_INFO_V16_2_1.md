# ZEC V16.2.1

## Zweck

V16.2.1 ist ein rückwärtskompatibler Bugfix-/UI-Härtungsrelease auf Basis des real feldabgenommenen V16.2.0. Er schließt die nach der V16.2.0-Feldabnahme sichtbare Speicherstatuskarten-Regression und vereinheitlicht die Darstellung beider Speicher, ohne die Regelstrategie zu verändern.

## Funktionsumfang

- gemeinsamer Standardvertrag für Zendure- und Primärspeicherkarte: SOC, prominent signierte Istleistung, Zustand, relevante Lade-/Entladegrenze, verbleibender SOC-Abstand und richtungsabhängiger Leistungsbalken;
- die Istleistung bleibt oben rechts als große signierte Zahl sichtbar; die Richtung wird dort nicht zusätzlich ausgeschrieben;
- Laden wird mit grünem Balken von links nach rechts, Entladen mit orangefarbenem Balken von rechts nach links visualisiert;
- der Leistungsbalken zeigt konkrete Leistung relativ zur konfigurierten maximalen Lade-/Entladeleistung, nicht eine zusätzliche Prozentzahl;
- `Noch ladbar` / `Noch entladbar` zeigt den absoluten SOC-Abstand zur relevanten Grenze in Prozentpunkten und – bei belastbarer Kapazität – zusätzlich in kWh;
- für die kWh-Berechnung hat eine reale/source-seitige Primärspeicher-Kapazität Vorrang vor einem manuellen Fallback; fehlt eine belastbare Kapazität, bleibt die Prozentpunkt-Angabe erhalten und nur die kWh-Angabe entfällt;
- die bisher in der Standardkarte sichtbare normalisierte Primärspeicher-SOC-Prozentanzeige bleibt intern diagnostisch verfügbar, wird aber nicht mehr als konkurrierender Prozentwert in der Standardkarte dargestellt;
- Primärspeicher-spezifische Harmonisierung/Harvest-Rechnung bleiben im Experten-/Diagnosekontext zugänglich, ohne die Standardkarte vertikal zu überladen;
- der bereits in V16.2.0 eingeführte optionale Settingswert `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` bleibt der manuelle Maximalwert für die Entladeskala, bis spätere Geräte-/Template-Capabilities belastbare technische Metadaten automatisch liefern.

## Daten- und Fallbacksemantik

Für Restenergie und Leistungsbalken werden nur belastbare Größen verwendet. Fehlende Kapazität oder Maximalleistung erzeugt keinen Ersatzwert, sondern blendet ausschließlich die abhängige Zusatzinformation aus. Für den SMA-Sunny-Island-Pfad bleibt die frische und gültige reale Entlade-Untergrenze die untere Grenze der Entladesicht. Die intern vorhandene normalisierte usable-SOC-Diagnostik bleibt unverändert read-only und ohne Reglerwirkung.

## Explizite Nicht-Ziele

- keine Änderung von `controller_logic.py`, Lade-/Entladestrategie oder Commandpfad;
- keine neue Reglerwirkung aus Restenergie-, Kapazitäts- oder Leistungsanzeigen;
- keine automatische Geräte-Metadatenabfrage für Kapazität/Maximalleistungen; `ZEC-BL-PRIMARY-METADATA-001` bleibt separater Folgepunkt;
- keine vollständige Umsetzung des offenen Statusseiten-Expertenmodus `ZEC-BL-UI-STATUS-EXPERT-001`;
- keine Umsetzung von Block B, Fast Capture oder `ZEC-BL-DEP-002`.

## Schutzgrenze

`controller_logic.py` bleibt gegenüber V16.2.0 byteidentisch; kanonischer SHA256:

`d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`

## Releaseidentität

- Version: `16.2.1`
- Label: `V16.2.1`
- Build-ID: `v16.2.1-20260921`
- unterstützte Updatequelle: ausschließlich `16.2.0 / v16.2.0-20260920`
- Fresh Install: ausschließlich bei real erkanntem `CLEAN_FRESH_INSTALL`
- Paket: `zendure_controller_v16_2_1.zip`

## Produktivfreigabe

V16.2.1 besitzt **TECHNICAL BUILD PASS**. Der releasespezifische Real-Field-PASS erfordert noch die kompakte reale Update-Feldabnahme V16.2.0 → V16.2.1. Der projektweite vollständige PRODUCTIVE-PASS bleibt zusätzlich durch `ZEC-EV-DEP-001` blockiert.
