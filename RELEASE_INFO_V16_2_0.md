# ZEC V16.2.0

## Zweck

V16.2.0 ist eine rückwärtskompatible funktionale Weiterentwicklung der Status-, Graph-, Settings- und Feldabnahmeoberflächen. Der Release bündelt die nach der realen V16.1.0-Feldabnahme gefundenen UI-/Cache-Befunde mit erweiterten, rein diagnostischen Speicheranzeigen. Der Live-Regelalgorithmus bleibt unverändert.

## Funktionsumfang

- Statuskarten beider Speicher mit richtungsabhängiger Restenergie bis zur relevanten SOC-Grenze, soweit Kapazität und Grenze verfügbar sind;
- richtungsabhängige Leistungsbalken relativ zur konfigurierten maximalen Lade- bzw. Entladeleistung;
- Primärspeicherkarte oben ausgerichtet, damit zusätzliche Diagnosezeilen den SOC-Kreis nicht mehr nach unten verschieben;
- optionale Primärspeicher-Fallbackwerte `SECOND_BATTERY_CAPACITY_WH` und `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` für Status/Diagnose, ohne Reglerwirkung;
- Tages-SOC-Cache trennt „heute“ und historische Tage, sodass ein vor Mitternacht erzeugter Teilstand nach dem Tageswechsel nicht als langer Historiencache weiterverwendet wird;
- „Jetzt“-Markierung und zugehörige Legende ausschließlich am aktuellen Kalendertag;
- mobile Settings-Suche: Änderungs-/Speicherleiste bleibt nach Auswahl eines Suchtreffers und Editieren erreichbar;
- Feldabnahme-Tool leitet die erlaubte Updatequelle aus dem Installervertrag ab und verwendet dieselbe sichere READY/TRANSITIONAL/REJECT-Klassifikation wie der Installer, ohne Runtime-`/ready` abzuschwächen.

## Daten- und Fallbacksemantik

Fehlende technische Primärspeicherinformationen erzeugen keine scheinpräzisen Ersatzwerte. Die jeweilige Zusatzanzeige wird einzeln ausgeblendet. Für die Primärspeicher-Kapazität hat eine von der aktiven Quelle gelieferte reale Kapazität Vorrang vor dem optionalen manuellen Fallback. Beim SMA-Sunny-Island-Pfad wird für die Entlade-Restenergie die frische und gültige reale Entlade-Untergrenze aus der V16.1.0-Capability verwendet.

## Explizite Nicht-Ziele

- keine Änderung von `controller_logic.py` oder der Lade-/Entladestrategie;
- keine neue Reglerwirkung aus Primärspeicher-Kapazität oder maximaler Entladeleistung;
- keine automatische Geräte-Metadatenabfrage für Kapazität/Maximalleistungen in diesem Release;
- keine Umsetzung von `ZEC-BL-DEP-002` (persistenter Installationsreport im Produkt);
- keine Umsetzung von Block B / strategischer usable-SOC-Integration oder Fast Capture.

## Schutzgrenze

`controller_logic.py` bleibt gegenüber V16.1.0 byteidentisch; kanonischer SHA256:

`d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`

## Releaseidentität

- Version: `16.2.0`
- Label: `V16.2.0`
- Build-ID: `v16.2.0-20260920`
- unterstützte Updatequelle: ausschließlich `16.1.0 / v16.1.0-20260919`
- Fresh Install: ausschließlich bei real erkanntem `CLEAN_FRESH_INSTALL`
- Paket: `zendure_controller_v16_2_0.zip`

## Produktivfreigabe

V16.2.0 besitzt **TECHNICAL BUILD PASS**. Der releasespezifische Real-Field-PASS bleibt bis zur realen Update-Feldabnahme V16.1.0 → V16.2.0 offen. Ein vollständiger projektweiter PRODUCTIVE-PASS bleibt zusätzlich ohne die separat zurückgestellte Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Gesamtabnahme unzulässig.
