# ZEC V14.1.0 – Release Information

**Release:** V14.1.0  
**Build-ID:** `v14.1.0-20260904`  
**Direkte Basis:** V14.0.0 / `v14.0.0-20260904-r2`  
**Typ:** rückwärtskompatible Graph-UI-Neuentwicklung + gebündelte V14-Feldkorrekturen

## Umfang

V14.1.0 ersetzt die bisherige Graph-Präsentationsschicht vollständig durch eine neu entwickelte Greenfield-Oberfläche. Der produktiv validierte Graph-Core-V3-/Query-Unterbau bleibt unverändert erhalten.

Enthalten sind insbesondere:

- komplett neue Graph-Präsentationsschicht in eigenem `graph_ui/`-Modul;
- alte Graph-Seite und ausschließlich alte Graph-Präsentationsendpunkte entfernt;
- echtes globales Light-/Dark-Theme ohne `force_dark`-Sonderpfad;
- dreispaltige Desktop-Informationsarchitektur;
- responsive mobile Darstellung mit Kontext-/Inspector-Bottom-Sheet;
- getrennte, synchronisierte Zeitspuren für Leistung, SOC und Controllerzustände;
- historische Min-/Max-/Reserve-SOC-Linien aus der Config-Timeline;
- deutlich dünnere Chartlinien bei großer Hover-/Touch-Hitbox;
- V3-Inspector, Command-Follow und Episodenvergleich in der neuen Oberfläche;
- historischer SOC-Tagesgraph auf der Statusseite gegen Timeout-/Race-/stale-data-under-wrong-date-Fälle gehärtet.

## Greenfield-Grenze

Die neue Graph-Oberfläche verwendet keine alte Graph-HTML-/CSS-/JavaScript-Struktur. Sie konsumiert ausschließlich die definierten Graph-Core-V3-APIs. Legacy-Präsentationspfade wie `/graph_old`, `/graph-view-data`, `/graph-data` und `/graph-data.csv` sind kein aktiver Produktpfad mehr.

## Datenbank / Graph Core V3

V14.1.0 führt **keinen erneuten V4→V3-Rebuild** aus. Die in V14.0.0 produktiv aufgebaute und validierte Graph-Core-V3-Datenbank bleibt erhalten und wird vor sowie nach dem Update read-only verifiziert.

## No-Regression

Keine fachliche Änderung an Live-Regelalgorithmus, AUTO/Harvest/Cross-Charge/NIGHT, Primärspeicherpriorität, Command Lifecycle/Effect/Readback/Resync, Safety oder Hardwareschonung.

Keine neue Retentiondauer, kein Retention-Scheduler und keine automatische VACUUM-Policy.
