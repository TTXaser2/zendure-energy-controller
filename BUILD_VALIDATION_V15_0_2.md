# ZEC V15.0.2 – Build Validation

## Identität
- Version: `15.0.2`
- Label: `V15.0.2`
- Build-ID: `v15.0.2-20260911`

## Ergebnis
- Full Suite: **1050 Tests + 692 Subtests PASS**
- ResourceWarning=error: **1050 Tests + 692 Subtests PASS**
- Python-Testdateien: **138**
- compileall: **PASS**
- Browser-JavaScript: **3/3 PASS**
- Bash-Syntax: **10/10 PASS**
- Measurement V4: **246 / 249 unverändert**
- `controller_logic.py`: `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff` – byteidentisch zu V15.0.1

## Neue Regressionsevidenz
- adaptiver Detailausschnitt / Elternmarkierung
- stabiles Command-Follow-Wertepanel unterhalb des Mini-Graphs
- vertikales Tooltip-Follow bei unverändertem horizontalem Flip-Vertrag
- Installer und Feldabnahme prüfen die neuen Assets explizit

## Build-Umgebung
Die Engineering-Runtime enthält das bereits bestehende Projektpaket `paho-mqtt` nicht. Wie bei V15.0.0/V15.0.1 wurde für die reine Test-Collection ein externer Minimal-Import-Shim unter `/tmp` verwendet. Er ist nicht Teil des Working Trees, Source-Manifests, Installers oder Release-Bundles. V15.0.2 fügt keine Runtime-Abhängigkeit hinzu.
