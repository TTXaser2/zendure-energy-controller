# Build Validation V17.0.1

**Release:** `17.0.1` / `V17.0.1`  
**Build-ID:** `v17.0.1-20260922`  
**Status:** **TECHNICAL BUILD PASS** – reale V16.2.5 → V17.0.1 Feldabnahme und natürliche Fast-Capture-Wirkungsevidenz ausstehend.

## Regression

- Testdateien: **157**
- vollständige Regression: **1164 Tests + 706 Subtests PASS**
- identischer Lauf mit `-W error::ResourceWarning`: **1164 + 706 PASS**
- Ausführung in vier disjunkten Shards wegen Tool-Laufzeitgrenze; Gesamtheit aller `tests/test_*.py` abgedeckt.

## Statische / Deployment-Gates

- Bash-Syntax: **12/12 PASS**
- Browser-JavaScript: **3/3 PASS**
- Python Compileall: **PASS**
- Deployment-Harness: **11/11 PASS**
- Datenblatt-Gate: **PASS**; DOCX/PDF zuvor visuell auf 10 Seiten geprüft
- `ZEC_BUILD_EVIDENCE_V1`: **PASS**
- Release-Hygiene / Source-Manifest: **PASS**
- Fresh-extract Manifestverifikation: **PASS**

## V17.0.1 Scope

- Fast Capture A400/R100 mit `off|shadow|active`, Baseline-Isolation und Safety-/Cross-Charge-Gates.
- additive Measurement-V4-Evidenz sowie read-only `tools/fast_capture_field_analysis.py` und `tools/v17_field_acceptance.py`.
- Gap-aware Graph-Cursor/Tooltip/Inspector.
- höhenneutrale Speicherwarnung mit Header-Chip und Detail-Overlay.

## Feldgrenze

TECHNICAL BUILD PASS ist nicht gleich reale Feldfreigabe. Der normale V16.2.5 → V17.0.1 Installerlauf auf dem Ziel-Raspberry-Pi bleibt erforderlich. Fast-Capture-Physikwirkung darf nur bei natürlich vorhandenen auswertbaren Shadow-/Active-Episoden als PASS bewertet werden; andernfalls ist `NOT_EVALUABLE` korrekt.

## V17.0.1 Packaging-Hotfix-Gate

- V17.0.0 wurde im realen Installer-Preflight vor Produktivmutation wegen fehlendem ZIP-Root abgewiesen.
- V17.0.1 baut das Release mit `tools/release_package.py`; `verify` erzwingt exakt `zendure_controller_v17_0_1/` als einzigen Datei-Root.
- Negativtest eines rootless ZIP und Positivtest des kanonischen Builders sind Bestandteil der Regression.
