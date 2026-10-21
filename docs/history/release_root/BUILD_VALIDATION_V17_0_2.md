# Build Validation V17.0.2

Release: V17.0.2  
Build-ID: `v17.0.2-20260923`  
Status: **TECHNICAL BUILD PASS**

## Implementierter Hotfix-Scope

V17.0.2 korrigiert ausschließlich den real gefundenen Fast-Capture-Feldevidenzpfad aus V17.0.1:

- cycle-exakte Fast-Capture-Felder im `record_graph_point()` -> Measurement-V4-Zulauf;
- Analyzer-Versionsevidenz ausschließlich über von den analysierten Rows referenzierte Config-Hashes;
- strukturelle Manifest-/Versions-Evidenz im Human-Report sichtbar;
- `create_zec_analysis_package.sh --latest-only` pipefail-/SIGPIPE-sicher.

Keine Änderung an A400/R100-Regler-, Command-, Safety-, Cross-Charge- oder Recoverysemantik.

## Test- und Buildnachweis

- fokussierte Hotfix-Regression: **51 Tests PASS**;
- ausführbarer `--latest-only`-Test mit >80 V4-Dateien: **PASS**, exakt neueste Datei, kein rc=141/SIGPIPE;
- vollständige Regression: **157 Testdateien / 1169 Tests + 706 Subtests PASS**;
- identischer Lauf mit `-W error::ResourceWarning`: **1169 + 706 PASS**;
- Bash-Syntax: **13/13 PASS**;
- Browser-JavaScript (`node --check`): **3/3 PASS**;
- Python `compileall`: **PASS**;
- Deployment-Harness: **11/11 PASS**;
- technisches Datenblatt: DOCX/PDF auf **10 Seiten vollständig visuell geprüft**, Datenblatt-Gate PASS;
- maschinenlesbare Build-Evidence `ZEC_BUILD_EVIDENCE_V1`: **PASS**.

Protected `controller_logic.py` SHA256: `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031` (**byteidentisch zu V17.0.1**).

## Paket-/Fresh-extract-Gates

Der Release-Freeze bestand den vollständigen Paketpfad: Release-Hygiene PASS, Source-Manifest **932/932 PASS**, kanonischer ZIP-Root `zendure_controller_v17_0_2/` PASS, ZIP-Integrität PASS sowie Fresh-extract-Manifest **932/932**, Build-Evidence und Datenblatt-Gate PASS. Nach dieser Dokumentationsfinalisierung werden Manifest und Installer-ZIP deterministisch neu gebaut und dieselben Gates auf dem exakt veröffentlichten Paket nochmals ausgeführt; dessen SHA256 wird extern veröffentlicht.

Reale V17.0.2-Installation und **neue** Fast-Capture-Shadow-Feldevidenz bleiben FIELD_PENDING. V17.0.1-Shadow-V4-Daten werden nicht als Fast-Funktionsnachweis wiederverwendet. `active` bleibt bis zufriedenstellender neuer Shadow-Evidenz nicht freigegeben.
