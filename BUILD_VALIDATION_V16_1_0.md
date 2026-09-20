# ZEC V16.1.0 – Build Validation

## Identität

- Version: `16.1.0`
- Label: `V16.1.0`
- Build-ID: `v16.1.0-20260919`
- Updatequelle: `16.0.2 / v16.0.2-20260917`

## Scope

SMA-Sunny-Island-spezifische read-only Entladefloor-Capability mit separater Freshness/Diagnose/Measurement-Evidenz und source-neutraler Settings-/Naming-Hygiene. Keine Reglerwirkung; `controller_logic.py` bleibt byteidentisch zu V16.0.2.

## Technische QA

- Capability-/Measurement-Kompatibilitätsregression: **72 Tests + 6 Subtests PASS**.
- vollständige pytest-Suite über 145 Testdateien, deterministisch in vier disjunkten Shards: **1086 Tests + 692 Subtests PASS**.
- identischer vollständiger Satz mit `ResourceWarning=error`: **1086 + 692 PASS**.
- Python `compileall`: **PASS**.
- Bash-Syntax: **14/14 PASS**.
- Browser-JavaScript-Syntax: **3/3 PASS**.
- V16-Deployment-Harness: **11/11 PASS**.
- Root-Artefakt-Rollback-Fixture: **PASS**.
- Measurement V4: **254 Standard / 257 Extended**; historische RC17/RC16/RC15-Verträge bleiben **238/228/217**.
- technisches Datenblatt: **PASS**, DOCX/PDF je 9 Seiten vollständig visuell geprüft; bekannter Tabellenkopf-Kontrastfehler korrigiert.
- geschützter Reglerkern: `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff` – byteidentisch zur kanonischen V16.0.2-Basis.
- `BACKLOG_NO_DROP_GATE`: Fast Capture, SMA-Acquisition und der Folgeblock „Strategic Usable-SOC Integration“ sind im Release-Snapshot `docs/ZEC_Master_Backlog.md` explizit erhalten.

## Finaler Release-Freeze

- `V16_1_0_SOURCE_MANIFEST.sha256`: **780/780 Einträge PASS**; das Manifest umfasst alle regulären Dateien des Release-Trees außer sich selbst.
- finales Installer-ZIP: ZIP-Integrität und eindeutiger Root `zendure_controller_v16_1_0/` **PASS**.
- Fresh-Extract des finalen ZIPs: Source-Manifest, Releaseidentität, Datenblatt, Master-Backlog, Reglerkernschutz und Ausschluss von Runtime-SQLite-/DB-Artefakten **PASS**.
- vollständige pytest-Suite direkt aus dem Fresh-Extract des finalen ZIPs: **1086 Tests + 692 Subtests PASS**.
- vollständige pytest-Suite direkt aus demselben Fresh-Extract mit `ResourceWarning=error`: **1086 + 692 PASS**.
- paketbezogene Syntax-/Compile-/Deployment-/Rollback-Gates aus dem finalen Fresh-Extract: **PASS**.

## Exit-Gate

**TECHNICAL BUILD PASS**

Dieser Status ist ausschließlich ein technischer Build-/Paketnachweis und keine reale Feldfreigabe. Für die releasespezifische V16.1.0-Feldfreigabe ist die reale Update-Abnahme V16.0.2 → V16.1.0 einschließlich SMA-Capability-Evidenz erforderlich.

Der übergreifende vollständige `PRODUCTIVE-PASS` bleibt zusätzlich solange unzulässig, wie die separat zurückgestellte Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Gesamtabnahme (`ZEC-EV-DEP-001`) offen ist. Eine erfolgreiche V16.1.0-Update-Feldabnahme schließt diesen separaten Deployment-Evidenzpunkt nicht automatisch.
