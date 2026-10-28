# CP38 – Testfixture-Import im isolierten V18-Regressionsrunner

**27.10.2026 · Entwicklungsstand, nicht installierbar.**

Der frisch aus der Bibliothek entpackte CP37-Baum wurde korrekt in das V18-Staging übersetzt. Der erste vollständige *isolierte* Regressionslauf meldete jedoch drei Importfehler (`ModuleNotFoundError: sma_packet_fixtures`); der isolierte Worker setzte `PYTHONPATH` nur auf Stagingroot und `tools/`, obwohl `unittest.discover(..., top_level_dir=root)` die Testverzeichnis-Sibling-Fixture nicht implizit in den Suchpfad übernimmt. Die direkt gestartete CP36-Staging-Suite hatte die Fixture korrekt gefunden.

CP38 erweitert **ausschließlich** den Worker-`sys.path` und den Worker-Subprocess-`PYTHONPATH` um dessen eigenes `tests/`-Verzeichnis, nie fremde Quellpfade. Ein neuer Negativ-/Positivtest führt einen separaten Pythonprozess mit einer konkreten `tests/sma_packet_fixtures.py` aus und überprüft den strengen, abgeschlossenen Ergebnisbericht. Keine Tests aus Discovery entfernt, keine Warnungen ignoriert, kein Release-PASS bei leerer oder unvollständiger Suite.

CP36/CP37 bleiben unverändert extern gesichert. `validation/V18_0_0_BUILD_EVIDENCE.json` bleibt `BLOCKED`; Installer Exit 78, UML-Fachreview, Endrelease-Tests, Hardwarewirkungs-/Rollback-/Pi-Feldgates und finales Datenblatt weiterhin ausstehend. Produktiver Pi V17.1.3.
