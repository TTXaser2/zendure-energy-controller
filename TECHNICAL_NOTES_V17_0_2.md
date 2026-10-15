# Technical Notes V17.0.2

**Release:** V17.0.2  
**Build-ID:** `v17.0.2-20260923`  
**Class:** evidence/tooling hotfix (+0.0.1)

## Scope

V17.0.2 fixes three real-field defects discovered after the successful V17.0.1 installation and general field acceptance:

1. `ControllerState.record_graph_point()` now carries the canonical Fast Capture runtime fields into the row consumed by Measurement V4. Previously the Fast fields defaulted to `off`/zero in V4 even while `/status` correctly reported `shadow`.
2. `tools/fast_capture_field_analysis.py` validates controller-version evidence only for config hashes actually referenced by the analyzed rows. Unreferenced historical snapshots no longer create a false version mismatch. Structural manifest/version evidence is also visible in the human report.
3. `tools/create_zec_analysis_package.sh --latest-only` no longer uses early-closing pipelines that can terminate under `set -o pipefail` with SIGPIPE/rc=141.

## Safety / protected controller logic

No A400/R100 algorithm, primary-state classification, command, safety, cross-charge or recovery semantics are changed. `controller_logic.py` remains byteidentical to V17.0.1 with SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031`.

## Update source

Supported real update source: V17.0.1 / `v17.0.1-20260922`.

## Field status

V17.0.1 general installation/field acceptance is real PASS. Fast Capture remains in `shadow`; no Active authorization exists. New Shadow evidence must be collected after installing V17.0.2 because the affected V17.0.1 Measurement-V4 Fast columns are not valid Fast evidence.
