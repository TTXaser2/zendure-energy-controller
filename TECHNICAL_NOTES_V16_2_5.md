# Technical Notes V16.2.5

## Storage Card Geometry & Active Warnings

`Noch ladbar/entladbar` wird in die rechte Detailspalte integriert. Die linke Speicherhälfte enthält SOC und den lesbaren Leistungsbalken; Zendure-/Primärspeicherkarten verwenden keinen starren Höhenvertrag mehr, der Footer oder Warnungen überlagert. Aktive Command-/High-SOC-Warnungen bleiben als kompakte Summary sichtbar; nur der Langtext ist aufklappbar.

## Mobile Settings

Mobile Settings-Container und Controls sind auf `min-width:0`/Viewportbreite begrenzt. Bei kleinen Viewports stapeln Input und Einheit; lange Keys, Validierungsfehler und Meta-Pills dürfen umbrechen. Horizontaler Scroll oder Zoom ist kein Ersatz für das responsive Layout.

## Instance Owner Diagnostics

`ControllerState.snapshot()` exportiert dieselbe Instance-Owner-Evidenz wie der Readinesspfad. Die Änderung betrifft ausschließlich Snapshot-/Diagnosekonsistenz; Lock- und Single-Owner-Semantik bleiben unverändert.

## Graph Evidence Gaps

Der Browser-Datasetpfad fügt für bestätigte Nicht-AVAILABLE-Evidence zwischen realen Messpunkten ausschließlich renderseitige `null`-Breaks ein. Es werden keine Messwerte rekonstruiert oder interpoliert. Der Vertrag gilt für Hauptgraphen und – soweit Evidence vorhanden ist – Command-Follow sowie Zeitraum-/Episodenvergleich. Die bestehende Evidence-Jittertoleranz entscheidet weiterhin, ob ein Intervall überhaupt als Gap gilt.

## Release Safety

Der Updatevertrag ist ausschließlich V16.2.4 / `v16.2.4-20260921` → V16.2.5 / `v16.2.5-20260922`. `controller_logic.py` bleibt byteidentisch. Der technische Buildnachweis wird erst nach vollständiger Regression, ResourceWarning-, statischen, Deployment-, Datenblatt-, Manifest-/Hygiene- und Fresh-extract-Gates auf PASS gesetzt.
