# CP40 – Dual-Root-Fixture für CP39-QA-Nachweisprüfungen

**Status:** `DEVELOPMENT_NOT_INSTALLABLE`, 27.10.2026. Ausgangsbasis ist CP39, extern unverändert archiviert, SHA256 `3b2cf54f38304c2250de5942b7f25e73439ed64ea2486571f5139bc5e080ebaf`.

Das neue CP39-Testmodul enthielt eine V17-only-Setupanforderung `prepare(ROOT,...)`: Diese ist auf dem tatsächlich bereits als V18 umgestellten Stagingroot unzulässig. Ein gezielter V18-Ausführungstest schlug daher in `setUpClass` fehl, bevor Testmethoden liefen. Dieser Befund betrifft ausschließlich die Testfixture, nicht den Care-Regler oder den MQTT-Commandpfad.

CP40 trennt die beiden Testwurzeln explizit:

- **V17.1.3-Entwicklungsquellen:** Der ursprüngliche vollständige `prepare(ROOT,...)`-Stagingbau wird weiterhin geprüft; die Legacy-Vertragsassertions entfallen nicht.
- **V18.0.0-Staging:** Eine separate, flüchtige Kopie des bereits vorhandenen V18-Baums mit Ausschluss von Runtime-DB-/Log-/Cacheartefakten wird mit `verify_staging()` nochmals unabhängig überprüft. Kein erneuter V17-Buildaufruf auf einem V18-Root. Fehlschläge bereinigen die temporäre Testumgebung, auch bei `ResourceWarning=error`.
- Eine zusätzliche Testmethode bestätigt die tatsächliche Runtimeidentität beider Wurzeln und den unverändert gesperrten, nicht installierbaren Stagingbaum.

Im Scope wurden **nur** die CP39-Fixture und drei kanonische Status-/Ledgernotizen geändert sowie dieses technische As-built hinzugefügt. Das CP39-Evidenztool bleibt unverändert. Installer-Exit-78-Sperre, Build-Evidence `BLOCKED`, manuelle UML-/Datenblattfreigabe sowie reale V18-Update-/Fresh-/Rollback-/Feld-/Batteriewirkungsnachweise bleiben offen; produktiver Raspberry Pi V17.1.3.
