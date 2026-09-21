# ZEC V16.2.1 – Build Validation

## Identität

- Version: `16.2.1`
- Label: `V16.2.1`
- Build-ID: `v16.2.1-20260921`
- Updatequelle: `16.2.0 / v16.2.0-20260920`

## Scope

Bugfix und UI-Härtung der Speicherstatuskarten: gemeinsamer Informationsvertrag für Zendure und Primärspeicher, prominent signierte Istleistung, intuitive verbleibende SOC-Prozentpunkte/kWh, richtungsabhängiger Leistungsbalken sowie Verlagerung primärspeicherspezifischer Diagnosezeilen aus der Standardkarte in den Expertenkontext. Keine Änderung der Live-Regelstrategie; `controller_logic.py` bleibt byteidentisch.

## Pre-Freeze-QA

- fokussierte Status-/Settings-/Installer-Regression: **71 Tests + 10 Subtests PASS**;
- vollständige pytest-Suite über 146 Testdateien: **1100 Tests + 698 Subtests PASS**;
- identischer vollständiger Satz mit `ResourceWarning=error`: **1100 + 698 PASS**;
- Bash-Syntax: **13/13 PASS**;
- Browser-JavaScript: **3/3 PASS**;
- Python Compileall: **PASS**;
- Deployment-/Fresh-Install-Harness: **11/11 PASS**;
- Root-Artefakt-Rollback-Fixture: **PASS**;
- technisches Datenblatt-Gate: **PASS**, DOCX/PDF je 9 Seiten visuell geprüft;
- geschützter Reglerkern SHA256: `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`.

## Exit-Gate

**TECHNICAL BUILD PASS**

Der bereinigte paketierte Fresh Extract hat Source-Manifest, vollständige Regression, `ResourceWarning=error`, Syntax/Compile, Deployment-Harness, Root-Rollback und Datenblatt-Gate PASS bestanden. Die reale Update-Feldabnahme V16.2.0 → V16.2.1 bleibt separat erforderlich; der projektweite vollständige PRODUCTIVE-PASS bleibt zusätzlich durch `ZEC-EV-DEP-001` offen.
