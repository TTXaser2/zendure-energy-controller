# CP37 – AST-verifizierter V18-Dualkontextschutz

**Entwicklungscheckpoint · 27.10.2026 · nicht installierbar**

CP36 enthält duale V17.1.3-/V18.0.0-Testverträge und ist vollständig unveränderlich extern gesichert. Bei der Fresh-Extract-Prüfung blockierte der historische CP35-Stringmatcher jedoch einen erlaubten mehrzeiligen `shutil.copytree(...)`-Aufruf im V18-Zweig – **falsch positiv**, ohne die zwei vorgesehenen Regressionen zu starten.

CP37 repariert ausschließlich diese Prüfwerkzeug-Lücke: AST statt wörtlicher Zeile. Eine Fixture besteht diesen Vorabcheck nur, wenn der tatsächliche V18-`if cls.from_staging`-Zweig eine `shutil.copytree`-Kopie mit explizitem Runtime-Hygiene-`ignore` und `verify_staging` verwendet und der entgegengesetzte Zweig weiterhin den historischen `prepare(ROOT, ...)`-Vertrag ausführt. Fehlende Quelle, ungültige Syntax, ungeschützter V17-Aufruf und eine Kopie ohne Hygiene bleiben `FAIL`. Fokus-Negativtests belegen das; CP36 und alle früheren Checkpoints bleiben byteidentisch erhalten.

Weder Installer-Exit-78 noch `BUILD_EVIDENCE=BLOCKED`, Datenblatt-Entwurf, fachliche UML-Pflicht oder reale Battery-Care-Hardwarewirkung wurden freigegeben. Das technisch mit der Stagingkopie arbeitende Regressionstool generiert **keine** finale Build-Evidence. Produktiv-Pi V17.1.3 unverändert; `05` bleibt einziges Master-Ledger.
