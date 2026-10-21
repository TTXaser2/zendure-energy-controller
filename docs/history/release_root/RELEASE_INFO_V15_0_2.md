# ZEC V15.0.2

## Zweck
V15.0.2 ist ein fokussierter UI-Bugfix auf V15.0.1. Er korrigiert drei im Real-Pi-Feldtest bestätigte Interaktionsprobleme im Graph-/Analysebereich. Controller-, Modbus-, Regelungs- und Graph-Backend-Verträge bleiben unverändert.

## Änderungen
1. **Adaptiver Detailausschnitt**
   - max. 10 Minuten bei großen Zeitfenstern;
   - bei engem Elternfenster 50 % des aktuell sichtbaren Zeitraums;
   - konstante Ausschnittsbreite auch nahe den Fensterrändern;
   - Beschriftung neutral als „Zoom um den Cursor“.
2. **Command-Follow ohne Layout-Reflow**
   - Cursorwerte dauerhaft unterhalb des Mini-Graphs;
   - vier feste Messreihen mit Platzhaltern;
   - konstante Panelgeometrie während Hover/Pointerleave.
3. **Vertikales Tooltip-Follow der großen Graphen**
   - bestehendes X-Achsen-Seitenwechselverhalten bleibt erhalten;
   - Tooltip folgt zusätzlich der relativen Maus-Y-Position;
   - weiche 100-ms-Interpolation ohne träges Nachlaufen.

## Schutzgrenzen
- `controller_logic.py` byteidentisch zu V15.0.1.
- Native Modbus-/Primärspeicherimplementierung unverändert.
- Kein neues Runtime-Dependency.
- Graph Greenfield Contract bleibt `v14.1.4`.
- Measurement V4 bleibt 246 Standard / 249 Extended.

## Releaseidentität
- Version: `15.0.2`
- Label: `V15.0.2`
- Build-ID: `v15.0.2-20260911`
- Upgradequelle: ausschließlich `15.0.1 / v15.0.1-20260911`
- Paket: `zendure_controller_v15_0_2.zip`

## Feldabnahme
Nach Installation `tools/v15_field_acceptance.py` gegen `/tmp/zec_v15_0_2_install_report.json` ausführen und die drei korrigierten UI-Interaktionen visuell prüfen.
