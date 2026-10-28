# ZEC Battery Care – CP21 kompakte Statuskarte (As-built Entwicklungszweig)

Stand 26.10.2026 · `ZEC-BL-BATCARE-001` · `DEVELOPMENT_NOT_INSTALLABLE`

## Quellvertrag

- `ControllerState.care_dispatched_stage` und `care_dispatched_target_w` entstehen ausschließlich aus dem realen zentralen Publisher-Dispatch in `controller_logic.py`. Der Wert wird zu Beginn jedes `run_once()` und bei SAFE_STATE gelöscht; er belegt eine tatsächlich vom Publisher angenommene **Anforderung**, keine bestätigte Akkuladung oder Readback-Wirkung. Ein nur berechneter PV-Shadow-Vorschlag darf diese Felder nie füllen.
- Der vorhandene `care_in_season && care_policy_valid`-Zustand belegt aktuell aktiven saisonalen AUTO-Reserve-Schutz. Die reine Kalender-/Validierungsprüfung anhand derselben `CareConfig` dient ausschließlich dazu, einen aktiven, aber vorübergehend **ausgesetzten** Care-Schutz sichtbar zu machen; daraus wird **keine** tatsächliche Schutzwirkung abgeleitet.
- `build_status_view_payload()` gibt `zendure.care` mit `visible`, `title`, `detail`, `tone` und `dispatch_w` aus. Priorität: offene, in `OperationalEventJournal` **persistierte** Notladevorfälle > tatsächlicher Stage-3-Command > Stage-2-Command > Stage-1-Command > aktive Reserve > validierte saisonale, aber ausgesetzte Policy. Nicht bestätigte physische Wirkung wird nie als Erfolg bezeichnet.
- Offene Notlade-Incidents bleiben außerhalb der Saison, bei OFF, STOP und Neustart als eigene `warning/error`-Events sichtbar; mehrere Incidents werden unter einem kompakten Status zusammengefasst, bleiben im Journal einzeln verfügbar.
- `status_page_v2.py` rendert eine einzige kompakte Zeile samt kurzer Detailzeile in der Zendure-Karte. Keine neue Kartenreihe und kein zusätzlicher Footer; auch Zwei-Unit-Layout. `static/status_v2.js` aktualisiert den Inhalt im vorhandenen Poll; die DOM-Region ist absichtlich **keine** jede Sekunde neu sprechende Live-Ansage.

## Abgrenzungen und offene Gates

- Nicht nachgewiesen: pixelgenaue Geometrie auf realem iPhone oder Browserbreiten 320/375/390/430/1280/1769, vollständig visuelle Responsive-Abnahme und Feldwirksamkeit.
- Die kompakten Worte `angefordert` und `derzeit ausgesetzt` sind bewusst keine tatsächliche Akkulade- oder BMS-Garantie.
- SOC-Tagesgraph-Historie, zeitkorrekte historische Schwellen/Merkmale, Ereignismarker, UML-Releasereview, Release-/Installer-/Realfeld-Gates bleiben ausstehend.
