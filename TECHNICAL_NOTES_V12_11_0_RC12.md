# Technical Notes V12.11.0-RC12

RC12 ist ein Dashboard-Data-Integrity- und UI-Polish-Release auf Basis von RC11.

## Enthalten

- Expertenmenü als echtes Overlay mit höherem z-index.
- Statusseite: Bezeichnung „Netzleistungsquelle“ statt hartem SMA-Titel.
- Nachtmodus-Prognose in der Betriebsmodus-Karte statt separater gelber Full-Width-Box.
- Keine Fake-/Deko-Sparklines: Netzleistungs-Sparkline nutzt echte RAM-Historie, CPU-Footer zeigt nur Momentanwert, wenn keine Historie vorhanden ist.
- Graph-Seite: echte lineare Zeitachse mit Backend-Achsen-Metadaten für „Heute“ und „Letzte 24 Stunden“.
- Graph-Seite: Marker gefiltert und in scrollbar begrenztem Bereich.
- Graph-Seite: aktive Signale/Quellen im Dark-Table-Stil mit Status-Badges.
- Graphdaten-Cache leicht erhöht, keine Änderung an Measurement-Schema.

## Nicht enthalten

- Keine Änderung an AUTO, Nachtmodus-Regelwirkung, Cross-Charge oder Restüberschuss-Ernte.
- Keine Änderung an Zendure-MQTT-Kommandos oder Topicstruktur.
- Keine SSD-/Mount-Automation im Controller-Code.
