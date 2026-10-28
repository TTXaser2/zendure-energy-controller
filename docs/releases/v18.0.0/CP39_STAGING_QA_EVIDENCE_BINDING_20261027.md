# CP39 – Reproduzierbare V18-Staging-QA-Evidenzbindung (Entwicklungsstand)

**Datum:** 27.10.2026  
**Autoritätsniveau:** Engineering-As-built / `DEVELOPMENT_NOT_INSTALLABLE`  
**Vorgänger:** Extern verifizierter CP38-Source-Checkpoint, SHA256 `afc8e2daa79f471d803f096cff848ba9f77689ce90d1a630653c3a1f164f9374`.

## Ziel und Scope

CP38 lieferte zwei vollständige, isolierte V18-Stagingregressionen mit jeweils 1.175 Tests und 1.211 Subtests. Die Datei `ZEC_BATCARE_CP38_V18_DUAL_REGRESSION_20261027.json` bindet die Zählwerte an ein Source-Manifest, speichert aber bloße Logpfade. CP39 ergänzt **nur** `tools/verify_v18_staging_qa_evidence.py` als unabhängigen, lesenden Konsistenzprüfer für das reale Staging, den Dualbericht und dessen Rohlogs und Worker-Sidecars. Kein Controller-, Publisher-, Installer- oder Runtime-Funktionscode wird verändert.

## Prüfung

1. `prepare_v18_staging_tree.verify_staging()` muss auf demselben Stagingbaum PASS liefern, inklusive Source-Manifest, Datenblattbindung, Buildstatus `BLOCKED`, Installer-Exit-78-Guard und Release-Identitätsgate FAIL.
2. Der aus den Stagingbytes berechnete SHA256 des `V18_0_0_SOURCE_MANIFEST.sha256` muss mit dem Dualbericht übereinstimmen. Damit lässt sich ein älterer vollständiger CP38-Bericht **nicht** unbemerkt als QA für einen später geänderten CP39-/finalen Sourcebaum ausgeben.
3. Der Dualbericht muss explizit `gate=PASS`, `release_approved=false`, `build_evidence_generated=false`, zwei vollständige erfolgreiche Prozesse und gleiche Test-/Subtestzahlen enthalten.
4. Pro Lauf werden die **vom Aufrufer ausdrücklich angegebenen** Rohdateien `<report-dir>/regular.log`, `regular.worker.json`, `strict.log` und `strict.worker.json` gegen Prozessabschluss, `Ran … tests`/`OK`, Fehler-/Fehlschlagszahlen und `ResourceWarning=error`-Kennzeichnung geprüft. Eingebettete Logpfade aus dem Dualbericht werden aus Sicherheitsgründen nicht für Dateizugriffe verwendet. Ungültige/symbolische Links, übergroße oder fehlende Dateien scheitern fail-closed.
5. Bei PASS schreibt der Prüfer **nur außerhalb des Sourcebaums, optional mittels `--output-json`,** einen nicht installierbaren Nachweis mit Source-, Bericht-, Log- und Worker-SHA256.

## Grenzen / nächste Gates

- Der Prüfer ist **kein** kryptografisch signierter unabhängiger Testdienst und verifiziert nicht die Identität eines ausführenden Hosts. Synthetisch erzeugte und zueinander konsistente Testartefakte können damit nicht grundsätzlich ausgeschlossen werden. Er bindet vorhandene Artefaktbytes, keine unveränderliche Runtime-Identität im Betrieb.
- Der Status lautet ausschließlich `PRE_FREEZE_STAGING_QA_ONLY`; das kanonische `ZEC_BUILD_EVIDENCE_V1` bleibt `BLOCKED`. Die finale Build-Evidence darf nur nach unveränderlichem finalem Release-Freeze und zwei vollständigen Regressionen **auf dessen exakt finalen Bytes** entstehen, nicht aus dem CP38-Staging-PASS.
- Standardinstaller weiterhin **nicht ausführbar** und harter `RELEASE_HOLD`/Exit 78; reale Update-/Fresh-Install-/Rollback-/Supportbundle-Abnahme, finale DOCX/PDF-Datenblattfreigabe, 22 UML-Fachreviews sowie Battery-Care-Realfeld-/physischer Wirksamkeitsnachweis bleiben offen.
- Keine Produktivmutation am Raspberry Pi; produktiver Release weiterhin V17.1.3. Keine Archivquelle oder Master-Ledger-ID gelöscht.
