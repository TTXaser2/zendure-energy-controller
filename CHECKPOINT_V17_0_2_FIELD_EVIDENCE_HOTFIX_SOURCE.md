# ZEC V17.0.2 Field-Evidence Hotfix – Source Checkpoint

Status: SOURCE_IMPLEMENTED / TESTS_PENDING
Basis: V17.0.1 final release ZIP SHA256 91cbbc437c67b9b046d12dc7bc6879a5ed2283b46854ec6356bab2b2d773d16c
Target: V17.0.2 / v17.0.2-20260923

Implemented scope:
- Fast Capture runtime state -> graph/Measurement-V4 evidence bridge.
- Fast analyzer version evidence scoped to config hashes referenced by analyzed rows.
- Human report exposes structural manifest/version evidence.
- create_zec_analysis_package.sh --latest-only made pipefail/SIGPIPE-safe.
- Focused regression tests added for these field-evidence defects.
- Installer/field-tool release identity advanced to V17.0.2; supported update source V17.0.1.

Safety boundary:
- A400/R100 control semantics unchanged.
- No Fast classification/command/safety/cross-charge/recovery strategy change.
- controller_logic.py remains SHA256 113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031.

Tests not yet executed at this checkpoint by design; checkpoint precedes validation per external-sicherung rule.
