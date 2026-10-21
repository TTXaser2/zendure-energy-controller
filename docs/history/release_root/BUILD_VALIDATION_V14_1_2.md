# ZEC V14.1.2 – Build Validation

## Release identity

- Version: `14.1.2`
- Label: `V14.1.2`
- Build-ID: `v14.1.2-20260905`
- Direct update basis: `V14.1.1 / v14.1.1-20260905`

## Graph interaction completion

The Greenfield graph presentation layer now closes the field UX findings without changing Graph Core V3 semantics:

- compact analysis toolbar with custom date controls only on demand;
- arbitrary period/day comparison, side-by-side or overlaid;
- t=0 episode comparison with selection and output colocated in the bottom analysis lane;
- explicit drag range selection with independent zoom/compare/clear actions;
- synchronized cursor across power, SOC and controller-state lanes;
- ZEC cursor value cards with native Chart.js tooltips disabled;
- circled information help for advanced concepts;
- correct WP9 episode response mapping via `episode.overview.*`;
- Evidence segment arrays are summarized as AVAILABLE/GAP/NOT_INSTRUMENTED/PURGED_BY_RETENTION instead of an empty placeholder;
- right context column reduced to Inspector / Command / Daten.

## Functional gates

- Graph interaction contract: **47/47 PASS**
- Targeted release/installer/interaction block: **65/65 PASS**
- Full suite: **960 tests + 679 subtests PASS** across 124 test files
- ResourceWarning gate: **960 tests + 679 subtests PASS** with `ResourceWarning` promoted to error
- Python compileall: **PASS**
- Bash syntax: **10/10 PASS**
- Browser JavaScript syntax: **3/3 PASS**
- Measurement V4: **246 Standard / 249 Extended unchanged**
- `controller_logic.py`: byteidentical, SHA256 `56f854bbe5bbecc9a7ce305af3915bd461615cc425e444b0c3e427c38e4184b1`

## Installer / migration semantics

V14.1.2 supports direct productive update only from V14.1.1 / `v14.1.1-20260905`. The existing Graph Core V3 database is preserved and verified read-only using the hardened runtime-root contract introduced in V14.1.1. No V4→V3 rebuild is performed.

## Product semantics

No controller, command, safety or hardware semantics changed. No new retention duration, scheduler or automatic VACUUM policy is introduced.

## Package exit gate

The final installable ZIP must be built only from the frozen source checkpoint, extracted into an empty directory, and all source-manifest, syntax, full-suite and ResourceWarning gates repeated on the exact package hash before delivery.
