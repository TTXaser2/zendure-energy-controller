# ZEC V16.2.0 – Technical Notes

## Statuskarten

Die beiden Speicherstatuskarten verwenden gemeinsame read-only Darstellungshelfer für Restenergie und Leistungsauslastung. Eine klare Leistungsrichtung oberhalb einer kleinen Diagnose-Deadband entscheidet zwischen Lade- und Entladesicht; im neutralen Bereich bleibt die Lade-/Max-SOC-Sicht stabil, damit die Beschriftung nicht um 0 W flattert.

Zendure verwendet die vorhandenen `MAX_SOC_PERCENT`, `MIN_SOC_PERCENT`, `ZENDURE_BATTERY_CAPACITY_WH`, `MAX_CHARGE_POWER_W` und `MAX_DISCHARGE_POWER_W`. Beim Primärspeicher hat eine von der aktiven Quelle gelieferte Kapazität Vorrang; `SECOND_BATTERY_CAPACITY_WH` dient nur als optionaler manueller Status-/Diagnose-Fallback. `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` ergänzt den bereits vorhandenen maximalen Ladewert für die Entladeskala. Beide neuen Settings sind ausdrücklich nicht regulatorisch wirksam.

Beim SMA-Sunny-Island-Pfad dient die frische und gültige reale Entlade-Untergrenze als untere SOC-Grenze für die diagnostische Restenergie beim Entladen. Fehlt eine erforderliche Größe, wird nur die davon abhängige Zusatzanzeige verborgen.

Die Primärspeicherkarte richtet ihren visuellen Speicherblock oben aus. Dadurch verändert die höhere rechte Detailspalte mit SMA-Capability-Zeilen nicht mehr die vertikale Position des SOC-Rings.

## Speicher-SOC-Tagescache

Der serverseitige Cache-Key unterscheidet explizit `today` und `history`. Ein vor Mitternacht erzeugter unvollständiger Tagesstand kann deshalb nach dem Kalendertagswechsel nicht mehr unter dem langen Historien-TTL weiterleben. Zusätzlich verwirft der Browser-Sessioncache Einträge, deren gespeicherte `is_today`-Rolle nicht mehr zur aktuellen lokalen Kalenderrolle des angeforderten Datums passt.

Die „Jetzt“-Linie und ihr Legendeneintrag werden nur gerendert, wenn der Payload den angeforderten Tag als aktuellen Tag kennzeichnet.

## Mobile Settings-Suche

Die Change-/Save-Bar besitzt auf mobilen Layouts einen eigenen festen Viewportbezug, eine ausreichend hohe Stacking-Ebene und Safe-Area-Abstand. Während der Such-Drawer selbst geöffnet ist, bleibt die Leiste ausgeblendet; nach Auswahl eines Treffers wird der Drawer geschlossen und die Leiste steht nach einer Änderung wieder unmittelbar zur Verfügung.

## Feldabnahme-Tool

`tools/v16_field_acceptance.py` liest die erwartete Updatequelle aus dem kanonischen Installervertrag statt eine historische Vorgängerversion fest zu verdrahten. Die Controller-Startbewertung verwendet dieselbe `evaluate_installation_readiness`-Klassifikation wie der Installer:

- `READY`: Runtime vollständig ready;
- `TRANSITIONAL`: releasevertraglich sicherer, begrenzter Übergangszustand; Runtime-`ready` bleibt transparent `false`;
- `REJECT`: Feldabnahmefehler.

Damit wird die Runtime-Readiness nicht aufgeweicht; lediglich Installer und Feldtool beurteilen denselben Zustand konsistent.

## No-Regression

`controller_logic.py` bleibt byteidentisch zu V16.1.0 mit SHA256 `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`. V16.2.0 erzeugt keine zusätzliche Commandwirkung, keine neuen Lade-/Entladerichtungen, keine zusätzlichen `acMode`-Wechsel und keine persistenten Gerätewrites im Regelzyklus.
