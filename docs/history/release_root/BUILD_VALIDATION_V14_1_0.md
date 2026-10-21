# ZEC V14.1.0 – Build Validation

## Release identity

- Version: `14.1.0`
- Label: `V14.1.0`
- Build-ID: `v14.1.0-20260904`
- Direct update basis: `V14.0.0 / v14.0.0-20260904-r2`

## Functional gates

- Full suite: **947 tests + 679 subtests PASS**
- ResourceWarning gate: **947 tests + 679 subtests PASS** with `ResourceWarning` promoted to error
- Python compileall: **PASS**
- Bash syntax: **10/10 PASS**
- Browser JavaScript syntax: **3/3 PASS**
- Measurement V4: **246 Standard / 249 Extended unchanged**
- `controller_logic.py`: byteidentical, SHA256 `56f854bbe5bbecc9a7ce305af3915bd461615cc425e444b0c3e427c38e4184b1`

## Greenfield graph contract

- active `/graph` presentation lives in new `graph_ui/` + `static/graph_v14_1.*`;
- no active `/graph_old`, `/graph-view-data`, `/graph-data`, `/graph-data.csv` presentation route;
- Light/Dark theme follows the global UI theme, no graph-specific force-dark override;
- desktop uses three-column investigation/workspace/context information architecture;
- power, SOC/config thresholds and controller-state lanes are synchronized;
- mobile context uses a bottom-sheet interaction;
- V3 Inspector, Command-Follow and Episode Comparison remain available;
- thin chart lines retain large pointer hit radii;
- historical SOC-day requests clear stale data, use request cancellation/sequence protection, validate returned dates and allow a 30 s historical request budget.

## Installer contract

V14.1.0 preserves the already productive Graph Core V3 database. It does not repeat the V4→V3 rebuild. Existing V3 is verified before and after source replacement. The full release rollback archive is hashed and recorded in `/tmp/zec_v14_1_install_report.json`.

## Fresh ZIP

The final ZIP must still be unpacked into an empty directory and all release gates repeated before release delivery.
