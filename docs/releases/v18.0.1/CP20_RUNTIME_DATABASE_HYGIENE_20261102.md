# CP20 – Runtime database was packaged in CP19 (RELEASE_HOLD)

**Finding:** CP19 fresh-extract manifest validation found `FORBIDDEN_MANIFEST_ENTRY:RUNTIME_DATABASE` (`logs/zec_operational_events.sqlite3`, 20,480 bytes). CP19 is explicitly rejected as a distributable installer.

**Repair:** Delete only this transient runtime SQLite file from the source/release tree, recalculate the manifest, add a permanent negative test requiring no database paths in the release manifest. Product event persistence code and user field data are unchanged. Preserve the original CP19 archive as historical provenance, **not** an installable release.

**Status:** CP20 is noninstallable (`RELEASE_HOLD_CP20` / Exit 78; Build-Evidence BLOCKED) until new regular/strict and fresh-extract regressions plus all package gates pass.
