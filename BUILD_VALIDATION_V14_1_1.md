# ZEC V14.1.1 – Build Validation

## Release identity

- Version: `14.1.1`
- Label: `V14.1.1`
- Build-ID: `v14.1.1-20260905`
- Direct update basis for the productive installation: `V14.0.0 / v14.0.0-20260904-r2`

## Field-root-cause gate

The failed V14.1.0 preflight was reproduced: relative `MEASUREMENT_LOG_DIR=logs` resolved below the staging CWD and produced `NOT_V3`. V14.1.1 adds explicit `--runtime-root` and pins installer/diagnostics to the installed runtime root. Existing V3 verification is read-only.

## Functional gates

- Targeted field/installer/release block: **77 tests + 10 subtests PASS**
- Full suite: **949 tests + 679 subtests PASS**
- ResourceWarning gate: **949 tests + 679 subtests PASS** with `ResourceWarning` promoted to error
- Python compileall: **PASS**
- Bash syntax: **10/10 PASS**
- Browser JavaScript syntax: **3/3 PASS**
- Measurement V4: **246 Standard / 249 Extended unchanged**
- `controller_logic.py`: byteidentical, SHA256 `56f854bbe5bbecc9a7ce305af3915bd461615cc425e444b0c3e427c38e4184b1`

## Product semantics

No controller, command, safety or hardware semantics changed. Graph Core V3 is preserved; no V4→V3 rebuild is performed. V14.1.1 contains the complete V14.1 Greenfield graph release plus the installer-path correction.

## Fresh ZIP

The final installable ZIP must be extracted into an empty directory and all release gates repeated on the exact frozen package before delivery.
