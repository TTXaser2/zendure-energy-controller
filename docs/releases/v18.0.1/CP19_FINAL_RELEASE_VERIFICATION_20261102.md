# V18.0.1 CP19 – Release Candidate / Exact-package verification

**Build:** `v18.0.1-20261102`; **approved update:** V18.0.0 `v18.0.0-20261027` → V18.0.1. This report is the source-bound *pre-extract release-candidate* provenance; the final exact-package review must be archived separately.

## Included changes

- Fail-closed SOC-freshness SAFE_STATE → HOLD recovery in Battery Care night reserve branch.
- Settings model error/retry, localized season `TT.MM.` UI, primary SOC display-only upper limit, Shield-type Battery Care status/help, reserve journal and `Nachtreserve` label.
- Bounded 7-day Battery Care analyzer and PV-differential tests; no unsubstantiated PV algorithm change.
- CP17/CP18 fixes: V18.0.1 field tool no longer contains hard CP28 candidate hold; natural PV/grid/emergency effects remain explicitly `NOT_EVALUABLE` until observed; legacy Fast-Capture analysis support set extended to V18.0.0/V18.0.1; matching generic/versioned installer guide.

## Prior source QA

CP18 independently byte-identically library secured; 4 groups of 289 `unittest` cases = 1,156 tests, 0 errors/failures in regular and strict warning mode; 1,219 measured subtests in strict mode; 85 documented historical version-bound assertions are still retained and explicitly inapplicable. Exact logs hashed in `validation/V18_0_1_BUILD_EVIDENCE.json`.

## Still required before technical release

- Run regular AND strict regression against the *identical bytes of the final ZIP* after fresh extract.
- Run package CRC/Manifest/Build-Evidence/UML/Datasheet/Architecture/Install-Syntax/Preflight contracts.
- Verify external Release-library upload + independent SHA256/bytes/ZIP readback; then provide real-user installation/field acceptance command.

`BUILD_PASS` does not mean Raspberry Pi deployment or naturally observed Battery Care grid and emergency physical effect.
