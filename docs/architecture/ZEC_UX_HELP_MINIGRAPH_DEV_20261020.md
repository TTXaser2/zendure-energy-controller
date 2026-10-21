# UX-Qualitätsblock – Entwicklung 20.10.2026 (UNRELEASED)

**Basis:** produktiv ausgeliefertes V17.1.0, unverändert. **Status:** Entwicklungsstand, kein V17.1.0-As-built und keine Releasefreigabe.

## Settings-Hilfe (CP06)

190 operative Settings besitzen individuelle fachliche Zweck-/Wirkungstexte; alle 74 Settings-Bereiche haben sichtbare Einleitungen. S3-Opt-in/Legacy-Wirkungsgrenzen und aktiv/inaktiv werden ausdrücklich erklärt. Ein Help-QA-Gate und die komplette CP06-Regression sind im CP06-Archiv dokumentiert; reale mobile Anwenderabnahme bleibt noch offen.

## Netzleistungs-Minigraph (nach CP06)

- `static/status_v2.js`: drei Sekunden Minigraph-Abruf bei sichtbarem Tab, abweichend vom separaten 1-Hz-Livepfad, Wahl 5/15/60 Minuten, Zeitabstands- statt Indexdarstellung, echte Datenlücken und Verlaufspunkt statt scheinbar zeitgleichem Livewert.
- `web_ui.py::build_grid_mini_payload`: Controller-RAM-Graphpunkte besitzen Zeitstempel und Gültigkeitsmerkmale; keine künstlichen 1-Hz-Proben; 5/15 Minuten ohne zusätzliche Datenbank-I/O. 60 Minuten: höchstens alle 15 Sekunden ein begrenzter read-only 1-Minuten-Graph-V3-Abruf (falls verfügbar), kombiniert mit jüngsten RAM-Punkten. DB-Ausfall -> sichtbarer Hinweis auf unvollständige Historie; keine Auswirkung auf `/ready`, Controller oder MQTT.
- `status_page_v2.py` / CSS: mobiltaugliche, tastaturzugängliche Zeitwahl, Aktualisierungs- und Verfügbarkeitsanzeige. Der tatsächliche Pi-CPU-/WAL-Effekt ist vor dem Release zu bewerten und nach Installation feldzuprüfen.
- `tests/test_v17_ux_minigraph_timeline.py`: Zeitfenster, Validität, Gaps, Payloadgrenzen, UI-Contract.

**Grenzen:** kein Controller-/Gerätecommand, keine Erhöhung von `GRAPH_HISTORY_LIMIT` oder des Control-Takts; noch keine Release-Versionsänderung, Manifest-Freeze, Installations- oder Feldfreigabe.
