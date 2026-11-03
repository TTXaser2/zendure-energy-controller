# CP18 – V18.0.1 Field-Acceptance + Installation Guide Consistency

**Status:** `DEVELOPMENT_NOT_INSTALLABLE` (`RELEASE_HOLD_CP17`, Exit 78) pending dual final regressions.

- Preserves CP17 correction of unconditional CP28 field-hold, correct `NOT_EVALUABLE` handling for unobserved Battery Care physical effect, and current V18 Fast Capture analyzer compatibility.
- Ensures `README_INSTALLATION.md` is byteidentical to `README_INSTALLATION_V18_0_1.md`, as required by current source-bound architecture/identity gates. The ordinary installer performs combined preflight+install in one call.
- `python tools/verify_arch_history.py --json` = PASS, 22 UML charts/source review PASS. 10 CP17/CP18 focused tests PASS.
- Older CP16 zip MUST NOT be distributed. CP18 is a noninstallable source checkpoint with incomplete final regression; no user Pi changes.
