# ZEC V15.0.3 – Build Validation

## Identität
- Version: `15.0.3`
- Label: `V15.0.3`
- Build-ID: `v15.0.3-20260911`

## Scope
Dokumentations-/Releaseprozess-Patch für die dauerhafte technische Datenblattintegration. Die Live-Regelalgorithmen und die native Primärspeicher-/Modbus-Implementierung bleiben unverändert.

## Source-Gates
- Full Suite: **1056 Tests + 692 Subtests PASS**
- ResourceWarning=error: **1056 Tests + 692 Subtests PASS**
- Python-Testdateien: **140**
- compileall: **PASS**
- Browser-JavaScript: **3/3 PASS**
- Bash-Syntax: **11/11 PASS**
- Measurement V4: **246 Standard / 249 Extended unverändert**
- Technisches Datenblatt: **DOCX/PDF jeweils 7 Seiten, vollständige Render-/Sichtprüfung PASS**
- Datenblatt-Inhalts-/Identitätsgate: **PASS**
- finales Source-Manifest: **688/688 PASS**
- `controller_logic.py`: `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff` – byteidentisch zu V15.0.2

## Datenblatt-Releasevertrag
- `docs/ZEC_Technisches_Datenblatt.docx` und `docs/ZEC_Technisches_Datenblatt.pdf` sind verpflichtende Releaseartefakte.
- Hardware-/Softwarevoraussetzungen und unterstützte Anlagenkonstellationen sind Pflichtinhalt.
- Bestehende unterstützte Produktpfade bleiben Bestandteil des Ist-Datenblatts; für die Netzmessung sind insbesondere SMA Speedwire/UDP und Shelly Pro 3EM / Shelly-kompatibles HTTP enthalten.
- Das Datenblatt enthält ausschließlich den Ist-Zustand des ausgelieferten Releases, keine Versionshistorie oder Vorgängervergleiche.
- `tools/validate_release_datasheet.py` prüft Identität, Build-ID, Hashmetadaten, Pflichtinhalte, Altversionsausschluss und Manifestintegration.
- Installer-Preflight und produktives Field-Acceptance prüfen die Datenblattintegration zusätzlich.
- Die fachliche und visuelle Review von DOCX/PDF bleibt trotz Automatisierung Pflicht.

## Source-Freeze-Status
Die vollständige Sourcebasis ist für den finalen Freeze vorbereitet und erfüllt die Source-Gates. Der **TECHNICAL BUILD PASS** wird erst nach Erstellung des Source-Freeze, Bau des Installer-ZIPs aus exakt diesem Freeze und vollständigen Fresh-extract-Gates erteilt. Produktiv-/Feldabnahme bleibt danach separat ausstehend.
