# CP17 – V18.0.1 Field-Acceptance Release Gate Fix (02.11.2026)

**Status:** `DEVELOPMENT_NOT_INSTALLABLE`, Installer `RELEASE_HOLD_CP17` / Exit 78. The formerly prepared V18.0.1 archive must not be installed.

## Confirmed issues in CP16

- `tools/v18_field_acceptance.py` retained an unconditional CP28 development hold in both the normal and first-install acceptance functions. It would report FAIL on every real installation.
- It also marked all missing *natural* Battery-Care PV/grid/emergency physical episodes as a general installation FAIL rather than `NOT_EVALUABLE`. Physical effect is not claimed PASS: this becomes a clear WARN and remains a separate function-specific evidence gate.
- The Fast-Capture diagnostics checked V18.0.1 against an analyzer's historical *default* controller version V17.1.3, while the analyzer's allowed version set ended at V17.1.3. Allowed V18.0.0/V18.0.1 versions are now explicit, historical defaults remain compatible.
- `README_INSTALLATION_V18_0_1.md` had required a duplicate preflight-only call. Updated for the existing combined installer/preflight procedure.

## Regression guard and release conditions

`tests/test_v18_0_1_release_candidate_hold.py` now tests that the old unconditional field hold cannot reappear, unobserved physical Care effect is WARN (not a false PASS), and the analyzer accepts V18.0.0/V18.0.1. Ten focused tests PASS on the functional revision before the CP17 release hold was added.

**Required before technical release:** full normal and strict regression on the final bytes; exact versioned source manifest; identity, data sheet, UML, installer tests; fresh extract; external SHA256/size/CRC release archive readback. Earlier CP16 test logs are historical and do not certify the changed CP17 bytes. No Pi installation or simulated Care physical PASS.
