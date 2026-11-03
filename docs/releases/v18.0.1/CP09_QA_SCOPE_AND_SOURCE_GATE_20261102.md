# CP09 – V18.0.1 QA-Scope und aktueller Release-HOLD (02.11.2026)

**Produktiv:** nur V18.0.0 / `v18.0.0-20261027`. **Engineering-Kandidat:** V18.0.1 / `v18.0.1-20261102`, ausdrücklich nicht installierbar.

CP06-Funktionsstand: anwendbare Regression 1.173 Tests / 1.219 Subtests, Fehler 0, `PYTHONWARNINGS=error::ResourceWarning`, 58 explizit inventarisierte historische V17/V18.0.0-Staging-Assertions, PASS. Diese Zahl ist **kein** Beleg für den später geänderten CP07–CP09-Endbaum.

CP07-Versionierungsprobe: 1.161 Tests, 14 FAIL und 1 Testklassenvorbereitungs-ERROR; Ursachen sind ausschließlich in dieser Erstanalyse historische V18.0.0-Release-/CP28-/CP41-Testidentitätsannahmen und der bewusst gesperrte Installer. Diese Fehler werden nicht als versteckt bestandene Tests bezeichnet. Die Dateien bleiben vollständig vorhanden; `validation/V18_0_1_RELEASE_APPLICABILITY.json` inventarisiert die fachlich zuordenbaren historischen Assertions und `tests/test_v18_0_1_release_candidate_hold.py` liefert V18.0.1-eigene versionierte, negatives Sicherheitschecks. Neuer Volltest aus diesem neuen Testkontext steht aus und muss mit vollständigem Rohlog nachgewiesen werden.

`DATASHEET_GATE=PASS` für V18.0.1-DOCX/PDF + Metadaten nach dreiseitiger Render-/Inhaltsprüfung; `DOC_UML_TECHNICAL_GATE=PASS` auf 22 Diagrammen und SOURCE_HASH, `DOC_UML_MANUAL_GATE=PENDING`. Es werden keine Bilder blind als fachlich freigegeben etikettiert.

`RELEASE_IDENTITY_GATE=FAIL` (Manifest/Build-Evidence/Manual-UML); `RELEASE_HOLD` ist unübersteuerbar vor jeder Pi-Mutation, Exit 78. Keine produktiven Konfigurations-, Geräte- oder Pi-Änderungen.

**Offen vor Freigabe:** semantisch manuell reviewte und ggf. aktualisierte UML-Blätter samt aktueller SOURCE_REVIEW_PASS-Evidenz; vollständige reguläre und strenge Endbaum-Regression auf identischen Quellen; Release-Metadaten und Build-Evidence daraus; finales V18.0.1-Source-Manifest, Hygiene- und Fresh-Extract-/ZIP-Gates; versionsgebundene Installer-/Update-/Backup-/Rollback-/Preflight-Tests; Release-README und As-built endgültig gegengeprüft; `BACKLOG_NO_DROP_GATE`/kanonischer `05`-Snapshot; erst dann Entfernen des Installer-Holds und erneute vollständige Tests. Reale Hardware-Feldabnahme erst nach kontrollierter Nutzerinstallation.

## CP10 candidate field identity correction (2026-11-02)

The V18.0.1 read-only field acceptance tool previously carried an incorrect expected build ID ending 20261027. Its exact candidate identity is now `v18.0.1-20261102`, and a new test covers both read-only field report routing and the exact V18.0.0 update source. The historical CP28 test requiring V18.0.0 is explicitly inventoried as non-applicable to V18.0.1; no historical fixture is removed. Excluded historical assertions: 85. This checkpoint is NOT an installable release.

The field tool now resolves its supported upgrade source from `tools/install_zendure_controller.sh`, never from the retired CP28 V18.0.0 pre-release installer.
