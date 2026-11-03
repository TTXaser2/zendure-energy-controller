# V18.0.1 CP21 – Exact ZIP gate

**Release candidate:** `v18.0.1-20261102` only; not yet a real Pi installation.

The CP19 source was rejected on fresh-extract hygiene because a generated operational-events SQLite file was included. CP20 removed it and added a negative manifest regression; its independently verified checkpoint is immutable historical provenance. CP21 is produced from CP20 after unblocking only the final installer/build evidence, and is not published until CRC, full source-manifest, release hygiene, architecture, data sheet, UML, installer and both full `unittest` suites on *these same fresh-extracted release ZIP bytes* PASS.

Expected regression inventory: 207 test files, 1,157 tests, 1,219 subtests, 85 explicitly preserved but historically inapplicable version-bound assertions. CP21 test and library gate results must be separately documented outside the immutable ZIP.

**Deployment scope:** V18.0.0 → V18.0.1 only; no claim of real installation, full hardware effect or real rollback.
