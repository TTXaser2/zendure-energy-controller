# CP26 – Battery-Care-UML / technische Source-Reconciliation

**Dokumenttyp:** isolierter DEVELOPMENT_AS_BUILT – kein Produktrelease. **Basis:** extern gesicherter CP25, SHA256 `31edcd62a998505703dd9a864309c05d1c6d910aba73433f2ad56b3cc4e42222`. Datum 27.10.2026.

## Quellstand und Lücke

Vor CP26 scheiterte `tools/verify_uml_release.py --technical-only` mit `CONTROLLER_SOURCE_MISMATCH`. Das alte Manifest referenzierte Controller-SHA `7e22175569163d6870356af021131f1730a07197e5c0e85acded899cfdddb818`, obwohl die aktive CP25-Controllerdatei SHA `ba1a909d8247336bf248ecd5432f3bb96c4be10f679be4c0590c6eab6b0da31b` besitzt. Das historische V17.1.3-As-built bleibt unverändert, darf aber nicht als CP25-As-built ausgegeben werden.

## CP26-Grenze

UML-Blätter 01, 02, 03, 05, 06, 08, 09, 10, 15, 16, 18, 21 mit separatem, als Development gekennzeichnetem Care-Kontext versehen, DOT/SVG/PNG deterministisch neu gerendert, Quelle-und-Hexhash im Manifest aktualisiert, nachgezeichnete Python-Source-Symbole ergänzt. Alle anderen Blätter mit eigener Impactentscheidung `REVIEWED_UNCHANGED`. Dies ist **kein manuelles fachliches Review**: im Manifest und im Gate bleibt `DEVELOPMENT_SOURCE_REVIEW_PENDING`. Die vorhandene `version.py` bleibt `V17.1.3` und kennzeichnet weiterhin die zugrunde liegende binäre Produktbasis, NICHT einen neuen auslieferbaren Release.

## Freigabesperren

- **Software/Feld:** kein realer Pi-Battery-Care-Wirkungsbeleg (PV/S2/S3), kein echter Power-Loss-Test, keine Termius-iPhone-Installation.
- **Releaseidentität:** neuer Feature-Release benötigt neue eindeutige Version/Build-ID und darauf basierende aktualisierte Releaseunterlagen, Datenblatt, Version-/ZIP-Metadaten, Fresh-Extract- und Installerprüfung; alte V17.1.3-Begleitdokumente dürfen dabei nicht als neue aktuelle As-built-Freigabe verwendet werden.
- **UML:** technische Syntax-/Hash-/Symbolprüfung separat; fachliche visuelle Quellen-Review-Freigabe ausstehend. Die neue Care-Stufenzeichnung allein beweist keine physische Gerätewirkung.
- **Kontrollvertrag:** vorhandene §3a in `03_ZEC_CONTROL_AND_SAFETY_INVARIANTS.md` begrenzt die Notlade-Ausnahme auf das **wirtschaftliche** Cross-Charge-Veto; sämtliche SmartMode-/BMS-/STOP-/Readback-/Recovery-Schutzpfade bleiben invariant.
- **Quellen- und Backlogno-drop:** keine Dateien oder Ledgeridentitäten entfernt; Release-Snapshot `docs/ZEC_Master_Backlog.md` bleibt historisch bis neuem Release-Freeze.
