# Releasebericht – Zendure Energy Controller V12.11.5

## 1. Ergebnis

V12.11.5 wurde vollständig neu aus der verifizierten V12.11.4-Referenzbasis aufgebaut. Es handelt sich ausschließlich um den freigegebenen Settings-UX-Bugfix. Es wurden keine geschützten Regler-, Command- oder Measurementdateien verändert.

## 2. Implementiertes Delta

1. Desktop-Scrollshell mit stationärer Navigation/Toolbar/Changebar und eigenem Contentscroll.
2. Nachtfenster als zwei logische `HH:MM`-Compoundfelder bei unverändertem Vier-Key-Configvertrag.
3. Mobile Drawer-Scroll-Chaining-Härtung mit Scrollpositions-Erhalt.
4. Semantische Verarbeitung fachlicher HTTP-422-Previewantworten einschließlich Feldsprung und Retry.
5. Last-Good-Pointer-Reparatur ausschließlich im Expert/System-Adminbereich.
6. Generischer Empty-State mit sichtbarkeitsgerechten Kategoriezählern.
7. Release-/Installeridentität V12.11.5, direkte Akzeptanz von V12.11.4 als Quelle.

## 3. Abnahme

Siehe `BUILD_VALIDATION_V12_11_5.md`. Die vollständigen Buildgates sind grün; der endgültige ZIP-SHA256 wird bewusst nicht in das ZIP selbst eingebettet, da dies eine selbstreferenzielle Prüfsumme erzeugen würde. Er wird in der externen Releaseübergabe zusammen mit Größe und Root angegeben.

## 4. Restpunkte außerhalb V12.11.5

Nicht Bestandteil und unverändert offen gemäß Roadmap:

- redaktioneller Ausbau der Settings-Hilfe/Info-Modals;
- benannte Konfigurationsprofile sowie Import/Export;
- Graph-Redesign;
- erweiterte Experten-/Diagnoseansicht;
- Measurement-Storage-Härtung;
- separater Simulationsdienst;
- formale produktive Feldabnahme von V12.11.5 nach Installation.

Es besteht kein bekannter Build-Blocker innerhalb des V12.11.5-Scopes.
