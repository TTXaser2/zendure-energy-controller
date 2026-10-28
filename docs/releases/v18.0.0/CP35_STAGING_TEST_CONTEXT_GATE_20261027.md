# CP35 – V18-Staging-Regressionsreife: Test-Kontext-Gate (kein Release)

**Stand:** 27.10.2026 · **Status:** `DEVELOPMENT_NOT_INSTALLABLE` / `BUILD_EVIDENCE_BLOCKED`

## Tatsächlicher Befund aus dem CP34-Staging

- Gegenstand: frisch ausgepackter, unabhängig gesicherter CP34-V18-Stagingbaum; `verify_staging=PASS`, Quellmanifest konsistent, Standardinstaller weiterhin `RELEASE_HOLD`/Exit 78.
- Ein erster regulärer, mit `ResourceWarning=error` gestarteter Gesamtversuch auf dem V18-Staging lief nicht erfolgreich durch (mehrere Testfehler und ein vor vollständigem Abschluss erreichter Zeitgrenzwert). **Kein Test-PASS** und **keine Build-Evidence daraus**.
- Reproduzierbar feststellbare Quellkontrakte: `tests/test_batcare_v18_staging_freeze.py` führt als `setUpClass` eine Staging-Erzeugung **aus dem aktuellen Testroot** durch, verlangt aber dort absichtlich V17.1.3. `tests/test_batcare_v18_candidate_contract.py` und `tests/test_batcare_release_identity_readiness.py` verlangen ausdrücklich V17.1.3 am Testroot. Im absichtlich versionierten V18.0.0-Staging ist diese Erwartung falsch, obwohl der Produktionscontroller nicht defekt sein muss.
- Diese Tests sind **nicht** per Filter aus der Gesamtregression zu entfernen. Vor finaler Build-Evidence muss der Testvertrag versionsübergreifend angepasst oder der DEVELOPMENT-spezifische Testkontext sauber in eigenständige, voll abgenommene Tests getrennt werden. Anschließend zweimalige **vollständige** Regression auf dem exakten finalen Sourcebaum mit identischen Test- und Subtestzahlen; `ResourceWarning=error` ist zwingend.

## Neuer, mutationsfreier Guard

`tools/v18_staging_regression_gate.py` prüft zunächst echte Staging-Provenienz (Source-Manifest, Datenblattbindung, hart blockierte Build-Evidence und Installer), danach die konkret nachgewiesenen kontradiktorischen Testfixtures. Bei vorhandenem Widerspruch bleibt `test_compatibility_gate=FAIL` und ein langwieriger, sicher nicht erfüllbarer Gesamtlauf wird nicht gestartet. Es gibt **keine Testausschlüsse**.

Nach Beseitigung der Fixturekonflikte kann `--run-tests` optional zwei vollständige Läufe auf **je einer temporären Kopie** des Stagingbaums mit endlichem Timeout und maschinenlesbarer Ergebnisfassung starten. Gezählt werden Tests und Subtests; Exitcode, Fehlerzahl, Timeout und ResourceWarning-Mode werden fail-closed behandelt. Das geprüfte Original wird nicht verändert. Das Werkzeug erstellt **niemals** `ZEC_BUILD_EVIDENCE_V1=PASS` und **niemals** eine Installer- oder Feldfreigabe; der abschließende Build-Evidence-Freeze bleibt ein gesonderter Gate-Schritt auf dem endgültigen, bytegesicherten Releasebaum.

## Weiter offene Releasearbeiten

1. V17-gebundene Tests vollständig releasekontexttauglich machen, keine historischen Testkontrakte verlieren.
2. Echte beide vollständige Regressionsläufe auf dem finalen Baum; Test-/Subtestidentität, Build-Evidence und Paketmanifest beweisen.
3. Technisches Release-Datenblatt in `docs/ZEC_Technisches_Datenblatt.*` erst nach finalem Freeze und visueller Fachprüfung freigeben.
4. Manuelle 22-UML-Fachabnahme, umfassende Installer-/Backup-/Rollback-/Fresh-Extract-/Fresh-Install-Gates sowie reale Batterie-/Command-Wirkungs- und Feldnachweise bleiben `PENDING`.
5. Pi produktiv V17.1.3, keine Installation oder Produktivmutation.

**No-drop:** Alle vorherigen Quellen und Master-Ledger-IDs unverändert aufbewahren. Keine Quellenbereinigung und kein behauptetes `BACKLOG_NO_DROP_GATE` durch diesen Block.
