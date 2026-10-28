## V18.0.0 – 27.10.2026: bereitgestelltes Installationspaket zur realen Feldabnahme

**NEUE technische Installationskandidaten-Basis:** `zendure_controller_v18_0_0.zip`, Build `v18.0.0-20261027`; aus verifiziertem CP42 V18-Stagingbaum abgeleitet, mit echtem Preflight-Installer, Release-Datenblatt und gemessenem anwendbaren Regressionsergebnis. Die explizit inventarisierten historischen 56 Release-Hold-/Altversionsassertions bleiben unter CP42-Staging-QA belegt und sind in der installierbaren Quellkopie nicht als PASS gezählt. **Dies ist die Bereitstellung zur Nutzer-Feldinstallation, nicht die Behauptung einer bereits erfolgreichen Feldinstallation oder einer physisch bestätigten Battery-Care-Wirkung.** Manuelle UML-Fachabnahme bleibt PENDING. Alle bisherigen V17.1.3-Pi-Feldangaben bleiben unverändert. Das Master-Ledger `05` bleibt alleinige Backlogautorität.

**Persistenz:** Frühere Ledgerpunkte und IDs bleiben vollständig erhalten; V18-Feld-Wirkung, manuelle UML-Fachabnahme und reale Installer-/Rollbackabnahme verbleiben ausdrücklich offen.

## Engineering-Nachtrag CP42 – 27.10.2026: Duale Installer-Audit-Testfixture

- `ZEC-BL-BATCARE-001`: **CP42_V18_INSTALLER_AUDIT_DUAL_ROOT_TEST_FIX / DEVELOPMENT_NOT_INSTALLABLE**. Beim echten CP41-V18-Staging-Gesamttest schlugen sieben Negativtests der neuen Auditfixture fehl, weil sie in ihrem eigenen temporären V17-Root den V18-gesperrten Standardinstaller verwendete. CP42 schützt beide historischen und aktuellen Testwurzeln: V17 behält vollständige alte Identity-Assertions, V18 testet den non-executable Standardinstaller mit Exit 78. Zusätzlich wird eine syntaktisch sichere Backup-Manipulation geprüft. Keine Tests gelöscht oder Excludes eingeführt; `tools/verify_v18_installer_recovery_readonly.py`, V18-Standardinstaller und Produktsteuerung byteidentisch. Volles CP42-Staging und Bibliotheksregression erst mit separaten Erfolgslogs grün; echter Update-/Fresh-/Backup-/Rollback-Nachweis, Build-Evidence PASS, UML-Fachabnahme, finaler Datenblattstatus und physischer Care-Wirkungsnachweis **weiter offen**. Keine Source-/Ledger-ID entfernt, keine Projektquellenbereinigung, kein Pi-Eingriff. Einzelheiten `docs/releases/v18.0.0/CP42_DUAL_ROOT_INSTALLER_AUDIT_FIXTURE_20261027.md`.

## Engineering-Nachtrag CP41 – 27.10.2026: nichtmutierender V18-Installer-/Recovery-Vertrag

- `ZEC-BL-BATCARE-001`: **CP41_V18_READONLY_INSTALLER_RECOVERY_AUDIT / DEVELOPMENT_NOT_INSTALLABLE**. CP40-Entwicklungsquelle unabhängig gesichert. CP41 ergänzt ein sourcegebundenes Audit für den hart gesperrten V18-Kandidaten und V18-Stagingstandard: früher Exit 78 vor allen externen Aktionen, Preflight-/Klassifikation-/Fresh-Zwang, Buildprüfung, Root-/Tar-/Config-Backup-Reihenfolge, Update-Datenerhalt, Failure-Traps, Diagnose vor Recovery und getrennte Rollbackfunktionen. Gezielte Manipulationsfälle fail-closed. **Grenze:** `STATIC_CONTRACT_PASS` ist kein echter Installer-/Backup-/Restore-/Rollback-/Feldnachweis. Insbesondere vollständige Archive-Restore-Integrität unter Hostbedingungen, injizierte Teilfehler, Root-Artefakt-Restore, Dienststatus und reale Batteriewirkung bleiben ausdrücklich offene Releasegates; `ZEC_BUILD_EVIDENCE_V1=BLOCKED`, Installer Exit 78, manuelle UML-Fachabnahme PENDING, finales Datenblatt PENDING, Hardwarewirkung NOT VERIFIED. Keine Source-/Ledger-ID gelöscht, keine Produktionsmutation, kein Quellenbereinigungs-No-Drop ausgelöst. Ausführlicher Scope `docs/releases/v18.0.0/CP41_READONLY_INSTALLER_RECOVERY_CONTRACT_20261027.md`.

## Engineering-Nachtrag CP40 – 27.10.2026: Dual-Root-Regressionsfixture ohne Quell-/Produktänderung

- `ZEC-BL-BATCARE-001`: **CP40_V18_STAGING_QA_TEST_CONTEXT_FIX / DEVELOPMENT_NOT_INSTALLABLE**. Die reale CP39-V18-Testausführung scheiterte in `setUpClass` wegen `prepare(ROOT)` auf bereits V18-gestagten Sources. CP40 korrigiert ausschließlich `tests/test_batcare_v18_staging_evidence_binding.py`: historischer V17-Prepare-Vertrag bleibt erhalten, V18 verwendet read-only-verifizierte hygienische Stagekopie; zusätzliche Root-Identitätstestmethode. Der CP39-Sourcecheckpoint und seine historischen Rohlogs bleiben unverändert; eine neue V18-Dualregression gilt erst bei vollständigem realen PASS. Release-Installer weiterhin `RELEASE_HOLD` Exit 78, `ZEC_BUILD_EVIDENCE_V1=BLOCKED`; Installer-/Rollback-, Datenblatt-/UML-Fach- und physische Wirksamkeitsgates weiterhin offen. Kein Source-/Backlog-ID-Verlust, keine Project-Quellenbereinigung, kein Pi-Eingriff.

## Engineering-Nachtrag CP39 – 27.10.2026: V18-Staging-QA-Manifest-/Rohlog-Bindung (kein Release)

- `ZEC-BL-BATCARE-001`: **CP39_STAGING_QA_EVIDENCE_BINDING / DEVELOPMENT_NOT_INSTALLABLE**. Extern unabhängig verifizierte Entwicklungsbasis CP38 (SHA256 `afc8e2daa79f471d803f096cff848ba9f77689ce90d1a630653c3a1f164f9374`). Das neue rein lesende `tools/verify_v18_staging_qa_evidence.py` gleicht ein unverändertes Staging-Manifest und dessen Provenienzgates mit dem dualen Testreport, zwei echten `Ran … / OK`-Rohlogs, Worker-Sidecars, Prozessabschlüssen und vollständigen Test-/Subtestzahlen ab; SHA256 der Rohbelege werden ausgegeben. Negativtests umfassen Replay-Manifest, falsche/fehlende Sidecars, abgeschnittene Logs, falsche Warnungsoption, abweichende Subtests und Symlink. Die CP38-Rohbelege sind ein **historischer** bereits abgeschlossener Staginglauf und dürfen keine finale V18-Build-Evidence ersetzen. Keine Produktivinstallation, `ZEC_BUILD_EVIDENCE_V1=BLOCKED`, Standardinstaller `RELEASE_HOLD` Exit 78, manuelle UML-/Datenblatt-/physische Hardware-/Installer-/Backup-/Rollback-Gates weiterhin offen. Keine Source-/Testdatei und keine historische Backlog-ID entfernt; kein `BACKLOG_NO_DROP_GATE` für eine Quellenbereinigung ausgelöst.

## Engineering-Nachtrag CP38 – 27.10.2026: Isolierter Staging-Runner und echte SMA-Testfixtures

- `ZEC-BL-BATCARE-001`: CP37-Staging und Testkontext-Provenienz waren korrekt; der Worker der dualen Regression meldete **drei Importfehler** durch `ModuleNotFoundError: sma_packet_fixtures` wegen fehlendem `tests/` im Testworker-`PYTHONPATH`, nicht durch die Battery-Care-Implementierung. CP38 ergänzt den Testpfad ausschließlich für die vom V18-Tool angelegte eigene isolierte Kopie und sichert dies durch einen eigenen subprocessbasierten Test. Keine Excludes/Mocks, keine V17-Alttests entfernt, kein Test-PASS vor vollständigem Lauf. Build-Evidence weiterhin `BLOCKED`, Installer Exit 78, UML-/Datenblatt-/Hardwarewirkung/Installer-/Rollback-/Releasegates unverändert offen. Historische Ledger-IDs vollständig erhalten, keine Quellenbereinigung und keine produktive Pi-Mutation. Technische Details unter `docs/releases/v18.0.0/CP38_ISOLATED_TEST_FIXTURE_IMPORT_20261027.md`.

## Engineering-Nachtrag CP37 – 27.10.2026: AST-Härtung Staging-Testkontext (kein Release)

- `ZEC-BL-BATCARE-001`: Der CP36-Fresh-Extract lieferte ordnungsgemäße V18-Stagingintegrität, aber die erste Dual-Suite wurde vom CP35-Readiness-Stringmatcher irrtümlich blockiert: `shutil.copytree(ROOT, cls.stage, ignore=...)` steht mehrzeilig, der Guard suchte wörtlich `shutil.copytree(ROOT, cls.stage)`. CP37 prüft den **realen AST-Ablauf** mit Gegen-Zweig V17-Prepare und Hygienefilter. Negativtests für ungeschützte bzw. hygienelose Aufrufe bleiben fail-closed. CP36 bleibt unabhängig gesichert, alle alten Testkörper/Backlog-IDs erhalten. Nur Tool, fokussierte Tests und Doku geändert; der Installer bleibt `RELEASE_HOLD`/Exit 78, Build-Evidence `BLOCKED`, UML und physische Wirkung weiterhin offen. Kein Pi-Eingriff, keine Bereinigung.

## Engineering-Nachtrag CP36 – 27.10.2026: Duale V17-/V18-Testkontexte (kein Produktrelease)

- `ZEC-BL-BATCARE-001`: Der CP35-Readiness-Blocker wurde auf dem echten V18-Staging reproduziert. Nach Anpassung der drei vom Vorprüfer identifizierten Fixtures lief eine volle Staging-Suite mit 1.167 Tests und 37 zusätzlichen Fehlern aus früheren V17.1.3-Release-/Installer-/Datenblatt-Rootannahmen. CP36 erhält alle historischen V17-Assertions und ergänzt für die 37 nachgewiesenen Testmethoden eine eigene, fail-closed V18-Staging-Sicherheitssemantik (exakte Runtime-/Source-ID, Hard-Hold Exit 78, gesperrte Dokumententwürfe, kein Execute-Bit). Weder testdiscovery-excludes noch heimliche Version-Overrides oder Installerfreigaben. Die explizite Einschränkung lautet: Im V18-Kontext ersetzen Sicherheitshold-Assertions einzelne historische V17-Installationsaspekte; diese bleiben weiterhin im tatsächlichen V17-Testroot zu beweisen. Neuer Root-/Fälschungsschutz. Das vorhandene Staging-Provenienzgate bleibt fail-closed, Build-Evidence weiter `BLOCKED` unabhängig von den Regressionsergebnissen. Dokumentation `docs/releases/v18.0.0/CP36_DUAL_CONTEXT_REGRESSION_CONTRACT_20261027.md`. **Keine** reale Hardwarewirkung, kein Pi-Eingriff, kein echter Installer-/Rollback-/UML-Freigabe-PASS. Alle bestehenden Ledger-IDs und historischen Quellen bleiben erhalten, keine No-Drop-Bereinigung.

## Engineering-Nachtrag CP35 – 27.10.2026: V18-Staging-Tests und Build-Evidence-Gate (DEVELOPMENT_NOT_INSTALLABLE)

- `ZEC-BL-BATCARE-001`: Beim exakten CP34-V18-Staging ist der vollständige strenge Testlauf **nicht** erfolgreich beendet worden. Drei noch V17-only gebundene Entwicklungstests (`test_batcare_v18_staging_freeze.py`, `test_batcare_v18_candidate_contract.py`, `test_batcare_release_identity_readiness.py`) sind für die V18-Rootidentität nachweislich inkonsistent. CP35 stellt ein schreibgeschütztes, deterministisches Readiness-Gate vor die späteren zwei vollständigen, im isolierten Kopierbaum durchzuführenden Regressionsläufe. Widersprüche blockieren ohne Testausschluss, verkürzte Testzahlen oder Fake-`PASS`; `ZEC_BUILD_EVIDENCE_V1=BLOCKED`, manuelle UML, Installer-/Rollback-/Feldgates offen. Details in `docs/releases/v18.0.0/CP35_STAGING_TEST_CONTEXT_GATE_20261027.md`. Bestehender `ZEC-BL-BATCARE-001`-Punkt bleibt offen, keine vorherigen IDs gelöscht und keine Quellenbereinigung. Produktiver Pi V17.1.3.

## Engineering-Nachtrag CP34 – 27.10.2026: V18-Staging-Datenblattquellenbindung (kein Release)

- `ZEC-BL-BATCARE-001`: **CP34_V18_STAGING_DATASHEET_BINDING / DEVELOPMENT_NOT_INSTALLABLE**. Auf unabhängig verifiziertem CP33 wird das V18.0.0-Staging nun mit dem dreiseitigen DOCX/PDF-Entwurf und seinem unveränderten Provenienzdatensatz verknüpft. `tools/prepare_v18_staging_tree.py` prüft vor dem Staging sämtliche originalen CP33-Entwurfs-/Quelldigests und erstellt im Staging `validation/V18_0_0_STAGING_DATASHEET_BINDING.json`. Diese Bindung belegt die Dokument-SHA256 und die **exakt zwei** absichtlichen Unterschiede zwischen CP33-Sources und Staging (`version.py`, `tools/install_zendure_controller.sh`); alle übrigen 12 dokumentgebundenen Source-SHA256 und alle drei vorherigen V17.1.3-Datenblattbestandsdateien bleiben unverändert. `verify_staging()` verifiziert alle Bindungen read-only zusätzlich zum vollständigen Stagingmanifest.
- Die zehn CP33-Provenienztests bleiben erhalten; `tests/test_batcare_v18_staging_freeze.py` enthält zusätzlich die negativen Staging-Integritätsfälle (manipuliertes PDF, veränderte Care-Source, fehlende Bindung, gefälschter V18-Quellhash). Ein korrektes Staging ist **kein installierbares Release**: Standardinstaller Exit 78 und ohne Executable-Bit, `ZEC_BUILD_EVIDENCE_V1=BLOCKED`, `RELEASE_IDENTITY_GATE=FAIL`, keine Produktivmutation. Der DOCX/PDF-Entwurf wird nicht an die Stelle des veröffentlichten kanonischen Datenblatts kopiert.
- Weiter offen: echte finale Build-Evidence mit zwei finalbaumbezogenen Regressionen, Gesamtpaket-/Fresh-Extract-/Rollbackgates, finaler Datenblatt-/Architektur-Release-Freeze, 22 UML-Blätter mit manueller Fachfreigabe, reale PV-/Grid-/Notlade-Wirkungsbeobachtung und Feldabnahme. Das 05-Ledger bleibt alleinige Backlog-Autorität; keine historischen Datei-/Vorgangsverlust- oder Quellenbereinigung.

## Engineering-Nachtrag CP33 – 27.10.2026: V18-Datenblatt-Entwurf, Sourcebound und visuell geprüft

- `ZEC-BL-BATCARE-001`: **CP33_V18_DATASHEET_DRAFT_PROVENANCE / DEVELOPMENT_NOT_INSTALLABLE**. Auf unabhängig byteverifiziertem CP32-Sourcebaum wurde ein eigenes dreiseitiges, visuell geprüftes `docs/releases/v18.0.0/ZEC_Technisches_Datenblatt_V18_0_0_ENTWURF.docx` und das daraus gerenderte gleichnamige PDF erzeugt; sie ersetzen die produktive V17.1.3-Datenblatt-Releaseidentität ausdrücklich nicht. Inhalt: vorhandene technische Anforderungen, Raspberry-Pi-/MQTT-/Netz-/Shelly-/SMA-/Modbus-Pfade, Einschränkungen für zwei Zendure, abgeschlossene Battery-Care-Quellimplementierung, Status-/Graph-Provenienz und eigenständige physische Wirksamkeitsgrenzen. Kein aktuelles Release-Datenblatt-PASS aus einem Entwurf.
- `tools/verify_v18_datasheet_draft.py` prüft read-only und fail-closed DOCX/PDF-Digests, 14 konkrete relevante Source-SHA256, die unveränderten drei V17.1.3-Datenblattdateien, grundlegende Mussinhalte und explizite Nichtfreigabe-/Hardware-Ungeprüft-Marker. Zehn positive/manipulative Tests `tests/test_batcare_v18_datasheet_draft.py` verhindern gefälschte Freigabe, geänderte Belege oder entfernte Source-Abdeckung. Erfolgsstatus lautet ausschließlich `V18_DATASHEET_DRAFT_INTEGRITY_ONLY`, niemals Produktfreigabe.
- **Unverändert offen:** V18 finale Runtime-/Installer-/Build-Identity, finalbaumbezogene zwei volle Regressionen und `ZEC_BUILD_EVIDENCE_V1`, Freigabedatenblatt inkl. Render-/Fachprüfung im kanonischen Dokumentpfad, manuelle 22-UML-Fachreview, vollständiges Fresh-Extract-/Update-/Rollback-/Supportbundle-Gate sowie reale unabhängige PV-/Netzpflege-/Notlade-Wirkungsbeobachtung. Der V18-Stagingstandardinstaller bleibt mit Exit 78 gesperrt; der Pi bleibt auf V17.1.3. Keine historische Quelle, Vorgangs-ID oder freigegebene Datei entfernt; `BACKLOG_NO_DROP_GATE` für eine Quellenentfernung wird nicht ausgelöst.

## Engineering-Nachtrag CP32 – 27.10.2026: V18-Build-Evidence-Identitätsgate fail-closed

- `ZEC-BL-BATCARE-001`: **CP32_V18_BUILD_EVIDENCE_STRICT_IDENTITY / DEVELOPMENT_NOT_INSTALLABLE**. Die nach CP31 identifizierte Release-Safety-Lücke ist explizit geschlossen: Das Read-only-Gate `tools/verify_release_identity_readiness.py` hatte bei vorhandener nichtleerer `validation/V18_0_0_BUILD_EVIDENCE.json` nur JSON-Existenz und -Form geprüft. Ein `BLOCKED`-Status war zuvor allein durch andere Gatefehler überdeckt; nach Schließen dieser anderen Fehler hätte trotz unbestätigter Tests fälschlich `RELEASE_IDENTITY_GATE=PASS` entstehen können. CP32 nutzt nun den bereits kanonisch vorhandenen Vertragsvalidator `deployment_contract.verify_build_evidence`: exakte Zielversion und Build-ID, `ZEC_BUILD_EVIDENCE_V1`, `status=PASS`, beide `PASS`-Regressionen, identische Test-/Subtestzahlen, gültige Anzahl Testdateien und `warnings_mode=error::ResourceWarning` werden geprüft; jede Verletzung erzeugt einen eigenen `BUILD_EVIDENCE_CONTRACT_FAIL:*`-Blocker. Neue Negativtests prüfen `BLOCKED`, nicht gelaufene Endbaumtests und widersprüchliche Regressionszahlen. Die Staging-/Installer-Hard-Holds, reale V17.1.3-Quellidentität sowie alle ursprünglichen CP31-Paketdateien bleiben intakt.
- **Offen:** Die finale Build-Evidence muss aus tatsächlich auf dem finalen V18-Quellbaum ausgeführten Tests stammen; bloße strukturelle Vertragsprüfung ist kein Nachweis der Echtheit einzelner Testlogs. `V18_RELEASE_IDENTITY_GATE=FAIL`, bis Datenblatt/UML/Manualreview/Installer/Build zusammenpassen. Die physische PV-/Netz-/Notlade-Wirkung, Raspberry-Pi-Abnahme und echte Rollback-/Fresh-Extract-Gates bleiben unabhängig offen. Kein Pi-Eingriff; keine Installationsfreigabe, Historie und alle bisherigen Ledger-IDs erhalten.

## Engineering-Nachtrag CP31 – 27.10.2026: V18-Staging-Hygiene unter voller Regression

- `ZEC-BL-BATCARE-001`: **CP31_V18_STAGING_RUNTIME_DB_HYGIENE / DEVELOPMENT_NOT_INSTALLABLE**. Beim ersten CP30-Gesamttest erzeugte eine historische Testfixture eine nur zur Laufzeit gehörende SQLite-Datei unter `logs/`. Das seit CP30 extern gesicherte V18-Stagingwerkzeug stoppte darauf korrekt am Release-Hygienegate (`RUNTIME_DATABASE`), der volle Testlauf war deshalb **FAIL (setUpClass)**; kein Controller-/Hardwaredefekt. CP31 nimmt ausschließlich `logs/`, `*.sqlite3`, SQLite-Sidecars und typische Test-/Laufzeitlogs von der **Kopie in das V18-Staging** aus. In der vollständigen Quellsicherung selbst bleiben alle historisch vollständigen CP30-Dateien erhalten; Runtime-Artefakte werden nicht als Source eingepackt. Neues Negativszenario prüft ein mit SQLite-Logs verunreinigtes Input-Verzeichnis; fehlgeschlagene Testklassen-Setups räumen temporäre Stagingverzeichnisse zuverlässig auf. Die bestehende hart nicht übersteuerbare Installer-Exit-78-Sperre und die Build-Evidence `BLOCKED` bleiben unverändert. Master-Ledger-/Releasegates behalten alle offenen Punkte. CP31-PASS erst nach unabhängiger Bibliotheksprüfung und voller strenger Regression gesondert behaupten.

## Engineering-Nachtrag CP30 – 27.10.2026: V18-Identitäts-Staging mit zwingender Installationssperre

- `ZEC-BL-BATCARE-001`: **CP30_V18_ATOMIC_STAGING_SOURCE_MANIFEST / DEVELOPMENT_NOT_INSTALLABLE**. Ausgangspunkt ist ausschließlich der unabhängig byteverifizierte CP29 (SHA256 `73d85c2d39567b913667698eafe96637ae7838e04d31d3825031bdd556d54cdf`). `tools/prepare_v18_staging_tree.py` prüft den CP29-Provenienzvertrag vor jedem Eingriff, kopiert den vollständigen Entwicklungsbaum nur in ein separates, neues Ausgabeverzeichnis und setzt dort *gemeinsam* `version.py` und den Standardinstaller auf V18.0.0 / vorläufig `v18.0.0-20261027`, Quelle V17.1.3 / `v17.1.3-20261022`. Der aus CP28 stammende Installer behält den nicht übersteuerbaren `RELEASE_HOLD`, Exit 78 vor jeder Dienst-/Datei-/Preflight-Aktion und verliert das Execute-Bit. Das stagingeigene `V18_0_0_SOURCE_MANIFEST.sha256` umfasst den kompletten Baum; `docs/ZEC_Master_Backlog.md` ist ein byteidentischer Snapshot dieses kanonischen Ledgers. Eine separate `validation/V18_0_0_BUILD_EVIDENCE.json` meldet ausdrücklich `BLOCKED` und `NOT_RUN_ON_FINAL_TREE`, **niemals PASS**. Die ursprüngliche V17.1.3-Version und der historische Installer bleiben im CP30-Sourcebaum byteidentisch zu CP29. Manipulation des Standardinstaller-Holds oder eines Manifestfiles, inkonsistente Identitäten und Output-Overwrite sind technische Fehler.
- **V18-Staging darf weder als finales Produkt-ZIP noch als fertiger Source-Freeze ausgegeben werden.** Das Identitätsgate muss weiterhin `FAIL` melden, solange finale Datenblatt-Metadaten/DOCX/PDF, UML-Manualreview, vollständige finalbaumbezogene Buildtests, Update-/Fresh-/Rollback-/Supportbundle-Abnahme und physische Battery-Care-Evidenz fehlen. Nach endgültiger Build-ID-Entscheidung muss ein neuer finaler Baum und Manifest aus genau diesen finalen Bytes entstehen; CP30 ist keine pauschale Freigabe der vorläufigen Build-ID. Die CP29-Draft-Provenienz bleibt ausdrücklich eine Source-Entwurfsevidenz, nicht zur Release-Freigabe wiederverwenden.
- **No-drop:** keine historische Quelle, keine Vorgangs-ID, kein älterer Checkpoint entfernt; `BACKLOG_NO_DROP_GATE` wird nicht durch Quellenbereinigung ausgelöst. Die Restpunkte bleiben im Master-Ledger und in `docs/releases/v18.0.0/CP30_STAGING_SOURCE_FREEZE_CONTRACT_20261027.md` nachvollziehbar. Der produktive Raspberry Pi bleibt V17.1.3, Ferninstallation via Termius erst nach vollständiger technischer Freigabe.

## Engineering-Nachtrag CP29 – 27.10.2026: sourcegebundene V18-Releaseunterlagen als gesperrte Entwürfe

- `ZEC-BL-BATCARE-001`: **CP29_V18_DOCUMENT_SOURCE_TRACEABILITY / DEVELOPMENT_NOT_INSTALLABLE**. Der aus externer Bibliothek rückleseverifizierte CP28 ist die aktuelle Codebasis. Sechs neue, klar als Entwurf gesperrte V18-Textunterlagen (As-built, Releaseinfo, Technical Notes, Build-Gates, Datenblatt-Quellenmatrix, Installationshinweis) und eine maschinenlesbare Provenienzdatei mit **15 konkreten Source-SHA256** sind eingeführt. `tools/verify_v18_draft_provenance.py` prüft readonly die SHA-/Dokumentintegrität, die fehlende physische Feldwirkung, die offene manuelle UML-Prüfung und den weiter wirksamen Installer-Hard-Hold. Es ist **kein Release-Gate** und kann keinen Installations-PASS erteilen. Der historische V17-Release-Datenblattbestand (DOCX/PDF) bleibt unverändert, neues V18-DOCX/PDF wird erst nach echtem Source-/Hardwareabgleich erstellt.
- **Weiter offen/unverändert bindend:** tatsächliche finale Runtime- und Build-ID V18.0.0, Standardinstaller/Preflight/Manifest/`ZEC_BUILD_EVIDENCE_V1` atomar umstellen, kanonische README-/INDEX-Verträge, aktuelles V18-DOCX + daraus erzeugtes PDF samt Render-/Fachprüfung, 22 fachlich manuell geprüfte UML-Blätter, komplette Fresh-Extract-/Update-/Fresh-Install-/Rollback-/Supportbundle-Abnahme, reale PV-/Netzpflege-/Notlade- und Restart-/Wirksamkeitsnachweise. `V18_RELEASE_IDENTITY_GATE=FAIL`, `DEVELOPMENT_NOT_INSTALLABLE`, kein Pi-Eingriff.
- **No-drop:** Kein alter stabiler `ZEC-BL`-/`ZEC-EV`-Eintrag, kein historisches Sourceoriginal und kein früherer Checkpoint entfernt. Die historischen erfolgreichen CP28-Tests sind Provenienz; CP29-QA und Bibliotheksgate werden nur bei tatsächlich erfolgreichem eigenen Lauf als PASS geführt.

## Engineering-Nachtrag CP28 – 27.10.2026: V18-Upgrade-Installer-Kandidat + versionsgebundene Feldabnahme (kein Release)

- `ZEC-BL-BATCARE-001`: **CP28_V18_UPGRADE_CANDIDATE / DEVELOPMENT_NOT_INSTALLABLE**. Ausgangspunkt: unabhängig bibliotheksgeprüfter CP27 (SHA256 `a47dd86dcbef460d30fc343bfebba68827d088c35cd05629dfa844df19356ae2`). Ein eigenständiger Kandidat `tools/install_zendure_controller_v18_candidate.sh` leitet den existierenden V17-Installer-Backup-/Preflight-/Rollback-/Diagnosepfad für die *exakte* unterstützte Updatequelle `V17.1.3 / v17.1.3-20261022` und das geplante Ziel `V18.0.0 / v18.0.0-20261027` ab; **unbedingtes `RELEASE_HOLD`/Exit 78 vor Pfadzugriff, Preflight, Backup oder Produktivmutation**, keine Freischaltvariable, Kandidat ohne Ausführungsrechte. Die bis zum Paketfreeze zu erstellenden `V18_0_0_SOURCE_MANIFEST.sha256` und `validation/V18_0_0_BUILD_EVIDENCE.json` bleiben verpflichtend; der Zeitstempel in der Build-ID ist weiterhin **vorläufig**. Der produktive, kanonische `tools/install_zendure_controller.sh` sowie `version.py` bleiben unverändert V17.1.3.
- `tools/v18_field_acceptance.py` ist aus der bisherigen read-only V17-Feldprüfung abgeleitet, verwendet V18-Zielidentität und den Kandidaten-Installer als Nachweis der echten V17.1.3-Updatequelle und übernimmt persistente Report-/Backup-/Fresh-Installprüfungen. Für **alle** Phasen gilt das aktive `RELEASE_HOLD_CP28`, für die normale Feldabnahme zusätzlich `battery_care_physical_effect=RELEASE_BLOCKER_NOT_EVALUABLE`: vorhandene Readiness-/ACK-Tests beweisen keine reale PV-/Netzpflege-/Notladewirkung. Kein künstliches V18-Feld-PASS. Erweiterung um tatsächlich beobachtete unabhängige Leistungs-/SOC-Evidenz, saubere Freigabe der technischen Felder und reale Hardwaretests bleibt vor Produktivfreigabe offen.
- Vertragstests `tests/test_batcare_v18_candidate_contract.py` schützen Identity, Installer-Safety-Gate vor jeglichem Zugriff, No-Bypass, Versionsbindung, unabhängige Feld-Reportauflösung und fortbestehenden `FAIL` des CP27-Identitätsgates. Bestehende V17.1.3-Tests/Verträge nicht umetikettiert. Alle bisherigen Backlog-IDs und historische Source-/Planungsunterlagen erhalten. Noch offen: vollständige V18-Dokumente, Datenblatt, Manifest, Build-Evidence, finaler Installer-Freeze samt Gate-Freigabe, echte Fresh-extract/Recovery-/Rollbacktests, fachliche UML-Abnahme und reale Battery-Care-Wirksamkeit. Kein Pi-Eingriff und keine Installationsanweisung.

## Engineering-Nachtrag CP27 – 27.10.2026: mutationsfreies Battery-Care-Release-Identitätsgate (kein Release)

- `ZEC-BL-BATCARE-001`: **CP27_RELEASE_IDENTITY_PREPARATION / DEVELOPMENT_NOT_INSTALLABLE**. CP26 ist die hash- und bibliotheksverifizierte Basissource. Gemäß `01` §5 ist `V18.0.0` als nächster Releasekandidat für das neue Entwicklungsthema vorgesehen; Build `v18.0.0-20261027` ist ausschließlich eine provisorische Prüfreferenz, keine Freigabe oder reservierte finale Identität. Der derzeitige `version.py`-/Installer-/Datenblatt-/UML-Stand bleibt absichtlich V17.1.3 und darf nicht mit einem V18-Dateinamen installiert werden. Ein neues **schreib- und mutationsfreies, fail-closed Identitätsgate** prüft Runtime, Installer-Ziel UND exakte V17.1.3-Quellidentität, Manifest, Build-Evidence, Release-/Installationsdokumente, Datenblatt-/UML-Metadaten und versionsspezifisches Feldtool. Es muss auf CP26/CP27 `FAIL` melden, solange diese Quellen nicht zusammenhängend für V18 erstellt wurden. `PASS` prüft allein Identitätskonsistenz, **niemals** Installierbarkeit oder reale Wirkung. Sourcebasierte Differenzial-, Installer-/Fresh-extract-/Rollback-, manuelle UML-, Datenblatt-, echte Clean-Fresh- und Pi-Wirksamkeitsgates bleiben als Blocker bestehen. Dauerunterlagen: `docs/releases/v18.0.0/BATCARE_RELEASE_PREPARATION_20261027.md` und `TERMIUS_IPHONE_REMOTE_INSTALL_PREPARATION_20261027.md` (beide ausdrücklich nicht zur Installation freigegeben). Keine historische Source/ID entfernt, kein Source- oder Command-Algorithmus geändert; Pi weiterhin V17.1.3.

## Engineering-Nachtrag CP26 – 27.10.2026: Battery-Care-UML-Source-Reconciliation / Releaseblocker

- `ZEC-BL-BATCARE-001`: **CP26_UML_SOURCE_RECONCILIATION / DEVELOPMENT_NOT_INSTALLABLE**. Start aus dem extern verifizierten CP25 (SHA256 `31edcd62a998505703dd9a864309c05d1c6d910aba73433f2ad56b3cc4e42222`). Das Release-Werkzeug meldete zuvor `CONTROLLER_SOURCE_MISMATCH`, weil das Atlasmanifest noch eine frühere Controller-SHA trug. Die von Care geänderten 12 UML-Quellblätter wurden mit expliziten Developmenthinweisen, tatsächlichen Care-Modulen und erneuerten DOT/SVG/PNG-Hashes abgeglichen. Die übrigen 10 Blätter erhielten nach Sourceimpact eine begründete Entscheidung `REVIEWED_UNCHANGED`. Der technische UML-Hash-/Render-/Sourcegate wird gesondert ausgeführt; die **manuelle Quellen-/Visualfreigabe bleibt PENDING**.
- **Release-Evidenz:** Das `version.py`-Tag und die V17.1.3-As-built/Datenblatt/Installerunterlagen beziehen sich weiterhin auf das bestehende produktive Originalrelease und sind **nicht** die fertige Battery-Care-Releaseidentität. Neuen versionsrichtigen Installer, vollständige Gates, reale Pi-/Termius- und physische Ladeeffekte sowie fachliche UML-Review nicht als PASS ausgeben. Vor Source-Freeze getrennte Spec-Matrix je Care-Stufe, echte Source-/Readback-/Wirkungs-/Recovery-Evidenz und differential disabled/out-of-season. Produktiver Pi bleibt V17.1.3. Keine historischen Backlog-IDs/Projektquellen/Checkpoints entfernt; nichtvollzogene Release-Freigabe bleibt als Blocker im Master-Ledger.

## Engineering-Nachtrag CP25 – 27.10.2026, persistierte Care-Stufenwechsel und Graphmarker (kein Release)

- `ZEC-BL-BATCARE-001`: **CP25_STAGE_EVENT_PROVENANCE / DEVELOPMENT_NOT_INSTALLABLE**. Ausgangspunkt ist exakt CP24 (extern rücklesegeprüft). Neue rein diagnostische `battery_care_stage_events.py`-Klassifikation belegt PV-Priorität, Netzpflege, Notladung, Reserve-Policy und STOP/Ende **nur aus zwei verschiedenen abgeschlossenen Controllerzyklen**. Hierfür wird das Ende des Zyklus durch eine separate bestätigte Zyklus-ID im State-Snapshot kenntlich; Power-Wünsche, Shadow-Vorschläge, ACKs und Snapshots während des laufenden Zyklus sind keine Start-Events. In der bestehenden Operational-Event-DB persistiert ein atomarer Singleton-Stagecursor zusammen mit jedem `battery_care_stage_transition`-Ereignis, sodass Restarts keine identischen Übergänge doppelt zählen. Änderungen der effektiven Policy-Untergrenze werden auch bei gleichbleibender Stufe protokolliert; normale Watt-Rampen nicht. Anzeigemarker aus tatsächlichen gespeicherten Events nur in `Care-Details`, nie als physische Lade-/Entladewirkung ausgegeben. Bestehende Notlade-Fehler-/Recovery-Historie und AUTO-/NIGHT-Linien unverändert. **Keine Änderung an Command-Owner, Safety-Prioritäten oder MQTT-Dispatch.**
- **Nachweise/Grenzen:** fokussierte Battery-Care-Tests vor Freeze **186/186 PASS**; weitere Gesamtregression und unabhängiges Bibliotheksgate sind separat nach Fertigstellung zu belegen, kein vorweggenommener PASS. Der Journaleintrag trägt den Zeitpunkt der nach zwei Zyklen bestätigten Beobachtung; kürzere Zustände und uncommittete Powerloss-Zeitfenster sind keine historisch bewiesenen Ereignisse. Diagnostisches SQLite-Versagen begründet keinen Command-Safety-Bypass und darf auch keinen Persistenz-PASS vortäuschen. Noch offen: vollständige Release-/UML-/iPhone-UI-/Pi-Feld-/Batteriewirkungs-/Installer-/Rollback-Gates. `docs/architecture/ZEC_BATCARE_CP25_PERSISTENT_STAGE_EVENTS_20261027.md` dokumentiert den Entwicklungs-As-built. Sämtliche alten Backlog-IDs und Quellnachweise verbleiben; **kein** No-Drop-Bereinigungsvorgang. Der produktive Pi bleibt V17.1.3; spätere Remote-Installation via Termius iPhone.

## Engineering-Nachtrag CP24 – 27.10.2026, historischer NIGHT-Care-SOC-Graph (kein Release)

- `ZEC-BL-BATCARE-001`: **CP24_CARE_HISTORICAL_NIGHT_FLOOR / DEVELOPMENT_NOT_INSTALLABLE**. CP23-Grenzlinienvertrag additiv um belegtes `NIGHT_DISCHARGE` ergänzt: rekonstruierte NIGHT-Untergrenze nur innerhalb historisch bekannter Nachtfenster aus `max(historischem MIN_SOC, Care-R, ggf. historischer NIGHT_DISCHARGE_STOP_SOC_PERCENT)`. Beobachtete NIGHT-Proben mit <=3 Minuten Abstand, keine STOP-/AUTO-/manuellen Mode-Gaps; über-Mitternacht-Fenster korrekt getrennt, fehlende/ungültige Zeitfenster nicht erraten. Höherer Night-Floor bleibt höher. AUTO-Overlay bleibt semantisch unverändert; neue gemeinsame `effective_discharge_floor_soc` für einen konsistenten visuellen Linienvertrag. Legenden/Tooltips machen AUTO/NIGHT und rekonstruierte Policy statt physischer Wirksamkeit kenntlich. Rein historischer Read-only-/UI-Block, **keine** Command-/Battery-Care-Ladestrategie-Änderung, kein neuer MQTT- oder DB-Schreibpfad. Cache-Key-Version CP24.
- **Offen ohne No-Drop:** Echte zeitlich persistierte PV-/Grid-/Emergency-Start-/End-Episoden samt Feature-/Reserve-/STOP-Übergängen im bestehenden OperationalEventStore (Dedupe, kein Loop-Spam), keine aus Hypothesen erfundenen Graph-Marker. Historischer Care-Liniennachweis bleibt Modus-/Konfigurations-Policy und kein Hardware-Wirkungsnachweis. Reale iPhone-/Pi-Feldabnahme, komplette technische UML-/Dokumentations-/Release-/Installer-/Rollback-Gates bleiben PENDING; aktive V17.1.3 unverändert. Keine historische ID oder Datei bereinigt. Technisches As-built: `docs/architecture/ZEC_BATCARE_CP24_NIGHT_SOC_GRAPH_20261027.md`.

## Engineering-Nachtrag CP23 – 27.10.2026, historischer Care-SOC-Tagesgraph (kein Release)

- `ZEC-BL-BATCARE-001`: **CP23_CARE_SOC_GRAPH_HISTORY / FOCUSED_QA_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Zeitkorrektes, rein lesendes `care_day_lines` auf CP22-historisierten Care-Konfigurationssegmenten. Anzeige der AUTO-Untergrenze `max(MIN_SOC,R)` ausschließlich bei damals gültiger Saison, valider Care-Konfiguration sowie durch beobachtete zeitlich zusammenhängende AUTO-Messpunkte belegtem Modus; STOP, NIGHT, FIXED, unfrische/fehlende Zeitpunkte und Lücken werden nicht als Care-Wirkung fortgesetzt. Standardansicht maximal eine zusätzliche dezente Care-AUTO-Grenze; per `Care-Details`-Schalter Experten-N-/E-Schwellen und reale, in OperationalEvents gespeicherte Notlade-Wirkungsfehler-/Recovery-Marker. Schreibt keine neue DB und löst keine Gerätebefehle aus. Historisches NULL ist nicht deaktiviert und nicht die heutige Reserve; reine Konfigurations-/AUTO-Policy ist **kein Hardware-Wirksamkeitsnachweis**.
- **Quellenvertrag:** Read-only-Abfrage des bestehenden `operational_events` auf exakte Tageszeitstempel, Eventtyp `battery_care_emergency_failure`, `started_at` und bei `resolved` `ended_at`; kein Publish-/ACK-Marker, keine generischen synthetischen PV-/Grid-/Notladeereignisse. Deutlich getrennte Status `recorded`, `not_recorded`, `unavailable`. Tagesgraph-Session-Cache versioniert; bestehende SOC-Messlücken, mobile Detailanzeige, Grund-SOC-Linien und Primärspeicherverhalten bleiben erhalten.
- **Restpunkte ohne Löschung:** Historisch belegte NIGHT-Care-Untergrenze mit Modus-/Nachtfenster-Vorrang und eigenständige PV-/Netzpflege-/Notlade-Episodenübergänge samt echter Ereignisaufzeichnung; reale Pi-Batteriewirkung, Livebrowser-/iPhone-UX, vollständige UML-/Datenblatt-/Installer-/Feld-/Releaseprüfung. Bestehende `ZEC-BL-BATCARE-001`-Roadmap-Pflicht bleibt bis zur echten Release-/Feldevidenz offen, kein Release-PASS, Pi unverändert V17.1.3. `docs/architecture/ZEC_BATCARE_CP23_SOC_GRAPH_HISTORY_20261027.md` ist nur entwicklungsgebundenes As-built; keine historischen Dateien/IDs bereinigt. Bibliotheks-/Gesamt-QA-Gates werden ausschließlich nach tatsächlich erfolgter Prüfung als PASS ausgewiesen.

## Engineering-Nachtrag CP22 – 26.10.2026, Battery-Care-SOC-Graph-Konfigurationsprovenienz (kein Release)

- `ZEC-BL-BATCARE-001`: **CP22_CARE_CONFIG_TIMELINE / FOCUSED_QA_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Alle sieben Care-Konfigurationsparameter gehen neu in den kontrollrelevanten Measurement-Config-Hash ein. Die vorhandene `graph_config_timeline`-SQLite-Tabelle erhält sechs additive, NULL-fähige Historienfelder (`care_enabled`, `care_start`, `care_end`, `care_r`, `care_n`, `care_e`), ohne bestehende Messzeilen/Hash-Originale umzuschreiben. Runtime-, Backfill-, Query-, Semantic-Diff- und Segmentpfade erhalten die damalige Care-Konfigurationsprovenienz chronologisch; selbst ein Care-only-R-Wechsel erzeugt einen neuen Segmentabschnitt bei ansonsten identischem MIN/MAX/Night-SOC. Historische Legacy-/Missing-Snapshot-Daten bleiben für Care **UNKNOWN**, niemals stillschweigend `disabled` oder mit den heutigen R/N/E-Einstellungen nachgefüllt. Der Grid-Cap ist Teil der Historienidentität, aber kein SOC-Prozentwert und deshalb keine Graph-Linie.
- **Scope-/Evidenzgrenze:** Hiermit werden historische Care-Linien oder Ereignismarker **noch nicht angezeigt** und keine reale Wirksamkeit aus Settings behauptet. STOP, manuelle Modi, Saison, SOC-Frische und bestätigter Dispatch brauchen zusätzliche punktgenaue Provenienz, bevor der Graph einen effektiven Schutzverlauf oder Ereignisse darstellen darf. Ausstehend: Frontend-/Legenden-/Tooltip-/Marker-Visualisierung, tatsächlicher per-cycle Ereignisquellenvertrag, reales Browser-/iPhone-/Feld-Gate, vollständige technische Dokumentations-/UML-/Installer-/Releasefreigabe. Kein Produktiv-Pi-Eingriff; V17.1.3 unverändert. Termius-iPhone-Installationsschritte sind erst zusammen mit freigegebenem Release/Installer zu liefern.
- **No-Drop / technische Evidenz:** Sämtliche bestehenden IDs und CP01–CP21-Dateien erhalten; `docs/architecture/ZEC_BATCARE_CP22_HISTORICAL_CONFIG_PROVENANCE_20261026.md` ist nur Entwicklungs-As-built. Neue differenzielle Graph-/Legacy-Migrationstests sowie die unveränderte V13/V14-Graph-Timeline getestet. Ein Test- oder Bibliotheksgate wird erst nach separater tatsächlicher Prüfung als PASS bezeichnet. Keine Bereinigung historischer Quellen.

## Engineering-Nachtrag CP21 – 26.10.2026, kompakte Battery-Care-Statusintegration (kein Release)

- `ZEC-BL-BATCARE-001`: **CP21_COMPACT_STATUS / FOCUSED_QA_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Status-Slice in der Zendure-Speicherkarte für 1- und 2-Unit-Layouts; kein neuer Footer und keine neue Kartenreihe. Abgrenzung zwischen belastbarem Policy-/Kalenderstatus, tatsächlichem Dispatch **eines zentralen Publishers** und unabhängig bestätigter physischer Batterieladung. Care-Shadow-Vorschläge alleine liefern keinen angeforderten Ladevorgang; eine tatsächliche Publisher-Anforderung wird als *angefordert* bezeichnet, niemals als physischer Effekt. Aktive valide Saison bei manuellem STOP/FIXED oder fehlendem Policy-Gate bleibt kompakt *derzeit ausgesetzt*, nicht fälschlich *Reserve geschützt*. Außerhalb Saison oder Care-Off bleibt die normale Anzeige verborgen, **offene persistierte Notlade-Warnvorfälle bleiben sichtbar und haben Priorität**. Vorhandener Events-Popover und Mehrfachvorfall-Zähler unverändert.
- **Fokussierte QA:** 31/31 bestehende und neue Status-/PV-/Grid-/Runtime-Tests PASS; `node --check static/status_v2.js` PASS. Volle strenge Testregression nach externem CP21-Sicherungsgate separat auszuführen. Dokument `docs/architecture/ZEC_BATCARE_CP21_COMPACT_STATUS_20261026.md` ist Entwicklungs-As-built, keine produktive Releasefreigabe. **Offen:** echte Mobile-/Desktop-Geometrie (320/375/390/430/1280/1769 px), SOC-Tagesgraph mit historischen Policy-Grenzen und Marker, vollständige UI-/UML-/Installer-/Feld-/physische Care-Abnahme. Kein produktiver Pi-Eingriff; V17.1.3 bleibt Produktivbasis.
- **No-Drop:** nur additiver Eintrag zur einzigen stabilen Master-Ledger-ID `ZEC-BL-BATCARE-001`; alle bisherigen Ledger-IDs, CP20-Source-/Evidenzdateien und historischen Quellen bleiben bestehen. Kein `BACKLOG_NO_DROP_GATE` für Projektquellenlöschung erforderlich.

## Engineering-Nachtrag CP20 – 26.10.2026, unabhängige parallele Notlade-Incidents (kein Release)

- `ZEC-BL-BATCARE-001`: **CP20_MULTI_INCIDENT_RECOVERY / FOCUSED_QA_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Der unter CP19 verbliebene `MULTI_INCIDENT_GAP` wird im bestehenden Operational-Events-SQLite-Store quellseitig geschlossen: jede separat vom tatsächlichen Command-Effect-Watchdog bestätigte Notladeepisode erhält einen **eigenen** persistierten Failure-ID-Eintrag mit ihrem beim Fehler fixierten Reservewert; die vorangegangene offene Warnung wird nicht ersetzt oder unzutreffend als neue Persistenzbestätigung ausgegeben. Die ursprünglichen CP18/19-Einträge mit gemeinsamem Dedupe-Key bleiben unverändert les- und recoverbar. Für jeden offenen Event wird mit eigener SOC-Proben-/3-s-Hysterese unabhängig bis zur damaligen Reserve bestätigt, ohne Replay über Neustart. Gekennzeichnete Reserve im Detailtext und tatsächliche Mehrfachzählung in der kompakten Statuswarnung; Eventliste/Popover zeigen Einzeleinträge, kein zweiter Warnspeicher. Der alte Einzelfall-Testvertrag wurde auf die fachlich genehmigte Mehrfachvorfallsemantik angepasst.
- **Safety/Abgrenzung:** Kein weiterer MQTT-Publisher, keine Command-/Cross-Charge-/BMS-/Reglerstrategieänderung; Write-through ausschließlich bei bestätigter Notlade-Nichtwirkung, kein Event aus Publish/ACK; SQLite-Sperre oder widersprüchliche Failure-ID/Reserve darf niemals einen erfolgreichen Commit vortäuschen. **Offen** bleiben vollständige Release-/UI-Visual-/Graph-Historie, manuelle UML-Prüfung, reale Netzlade-/SOC-Wirkung und Pi-Feld-/Power-Loss-Tests. Produktive V17.1.3-Installation unverändert. Termius-iPhone-Installationsanleitung erst für später technisch freigegebenes Installerpaket.
- **Qualifizierung bisher:** 35/35 fokussierte Batterie-Care/Event/UI-Regressionstests PASS und 70/70 wiederholte Parallel-Schreibtests PASS. Vollständige strenge Regression und unabhängiges Bibliotheksgate folgen nach Source-Freeze separat; diese Zeile behauptet keinen Gesamt-PASS. CP19 (SHA256 `9c14815ad3e15555a2fb3d8bd369eed831c76c1eb77bb8df19ad0acd7450a1c9`) bleibt unverändert als Provenienz vorhanden. Alle stabilen Ledger-IDs und bisherigen historischen Dokumente erhalten, keine Quellenbereinigung, **BACKLOG_NO_DROP_GUARD: alle vorhandenen Identitäten bleiben enthalten**.

# ZEC – Master-Backlog & Roadmap

## Engineering-Nachtrag CP19 – 26.10.2026, persistenter Notlade-Warnvorfall ohne reguläres 2-s-Schreibfenster (kein Release)

- `ZEC-BL-BATCARE-001`: **CP19_EMERGENCY_INCIDENT_WRITE_THROUGH / STRICT_UNITTEST_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Der ausschließlich vom tatsächlichen Command-Effect-Watchdog bestätigte Stufe-3-Notladefehler wird nun unmittelbar unter derselben quellengebundenen Failure-ID und unveränderlichen Reserve R im **bestehenden** `OperationalEventJournal` in SQLite (`WAL`, `synchronous=FULL`, Busy-Timeout 0,2 s) committet. Der 2-s-Hintergrundobserver bleibt für normale Diagnostik und die unabhängige SOC-Recovery zuständig. Ein kurzes `BEGIN IMMEDIATE` serialisiert konkurrierende Confirmed-Failure-Inserts und verhindert eine Doppeleintragung beim Race zwischen Background-/Write-through-Pfad. Keinerlei I/O bei bloßem Publish, ACK oder unbestätigter Nichtwirkung; kein zweiter MQTT-Publisher, keine Safety-Ausnahme, keine Änderung der Command-Entscheidung. Der Controllerstatus meldet `care_emergency_incident_persisted` und `care_emergency_incident_persistence_error` quellwahr; DB-Lock/IO-Fehler darf niemals `persisted=true` ergeben und wird bei weiterer bestätigter Nichtwirkung mit derselben Event-ID erneut versucht. **Einschränkung:** Ein dauerhaft nicht beschreibbares oder abgeschaltetes Dateisystem kann selbstverständlich keinen Persistenz-PASS garantieren, und der SQLite-Busy-Timeout garantiert keine harte maximale Dateisystem-I/O-Latenz.
- **Noch offener CP19-Fund unter derselben stabilen ID:** Die Journalauflösung unterstützt derzeit nur einen gleichzeitig offenen `battery_care_emergency_failure`-Incident. Eine **weitere eigenständige bestätigte Notladeepisode**, solange der erste Incident offen ist, wird absichtlich nicht als erfolgreich persistiert markiert; mehrere zeitgleich offene Failure-IDs und ihre unabhängigen Reserve-/Recoveryziele benötigen vor Release einen separaten fachlichen Incident-State-/UI-Vertrag samt Tests (`OPEN / MULTI_INCIDENT_GAP`). Dies ist keine Freigabe des bisherigen Einzelfallvertrags für Mehrfachereignisse und kein Grund, historische Vorfälle zu löschen.
- **QA:** 6 neue DB-/Restart-/Lock-/Race-/Retry-Testfälle; Gesamtregression mit `-W error::ResourceWarning` **1.050/1.050 PASS in 30,905 s**, Python-Compile PASS, technisches UML-Gate **22/22 PASS** mit zwei neu gerenderten Blättern (08/09), `manual_gate=PENDING` für den neuen Entwicklungszweig. Vollständige Pi-Feld-/Power-loss-/Thermal-/Installer-/UI-/SOC-Graph-/UML-Releasefreigabe bleibt offen; **kein** produktiver Pi-Eingriff, derzeit weiterhin V17.1.3. Extern gesicherte CP18-Source SHA256 `8fcf20ec041e0280f1f313ad5ed7b3d8b747f2d0f5271e63183e355e1f876888` bleibt Provenienz.
- **Checkpoint-Hygienefund:** Der CP18-Vollbaum enthielt versehentlich die volatile, durch synthetische Tests erzeugte `logs/zec_operational_events.sqlite3` (kein kanonischer Quell- oder Archivvertrag). Diese Runtime-DB wird im CP19-Entwicklungsarchiv ausdrücklich **nicht** als Source übernommen. Das unveränderte CP18-Original bleibt unabhängig in der persönlichen Bibliothek erhalten; die CP19-Manifestauditdatei benennt die Ausnahme. Alle nichtvolatilen CP18-Sources bleiben vollständig erhalten.
- **No-Drop:** ausschließlich additiver Master-Ledger-Nachtrag. Alle bisherigen stabilen `ZEC-BL-`/`ZEC-EV-`-IDs und historischen CP01–CP18-Originale bleiben erhalten; keine Projektquellenbereinigung, kein Lösch-Gate nötig. Die vereinbarte spätere Termius-iPhone-Ferninstallation bleibt von einer vollständigen technischen Release- und Safetyfreigabe abhängig.

## Engineering-Nachtrag CP18 – 26.10.2026, Notlade-Command-Effect → persistenter Incident (kein Release)

- `ZEC-BL-BATCARE-001`: **CP18_EMERGENCY_EFFECT_INCIDENT_BRIDGE / STRICT_UNITTEST_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Der vorhandene `_mark_mismatch()`-Watchdog öffnet bei unabhängig bestätigtem, positivem **Stufe-3-Notlade**-Command-Mismatch (nicht Publish/ACK/Readback/neutralem oder regulärem Ladeziel) ein einmalig identifiziertes, im `ControllerState.snapshot()` bereitgestelltes Failure-Event mit dem ursprünglichen geschützten Episoden-R. Der vorhandene `OperationalEventJournal` persistiert diesen im **bestehenden** SQLite-Store und löst ihn ausschließlich nach mehreren distinct/frischen SOC-Beobachtungen über diesem unveränderten Ziel; beobachtete AC-/Batterieladung wird getrennt auf Source-Frische geprüft und reicht allein zur Incident-Auflösung nicht aus. Neue Fehlerereignisse nur für tatsächlich neue Eskalationsepisoden; wiederholte Command-Mismatches und UI-Snapshot-Polls erzeugen keinen neuen Vorfall. Offene Events erscheinen auch bei Care-Off/STOP/außer Saison über vorhandene `open`-Operational-Events-Ausgabe. **Keine** neue Command-Autorität, Hardwarewirkung oder Installation freigegeben. 36/36 fokussierte Tests und vollständige `unittest`-Suite mit `ResourceWarning=error`: **1.040/1.040 PASS** in 42,1 s. Der PV-/Grid-Live-Regler und die bereits bekannten fehlenden UI-/Graph-/UML-/Feld-/Release-Gates bleiben separat offen. Sourcebasis CP17 (SHA256 `1332e0dc6cb4db5c2c9db4df8637846c0b14d874b6adc13e5e3436494422da02`). **BACKLOG_NO_DROP:** ausschließlich additiver Ledger-Nachtrag, keine historische ID, Datei oder Evidenz entfernt.


## Engineering-Nachtrag CP17 – 26.10.2026, Regression/Legacy-Konfiguration kompatibel (kein Release)

- `ZEC-BL-BATCARE-001`: **CP17_EPISODE_RESTART_QA / STRICT_UNITTEST_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Nach extern erfolgreich rücklesegeprüftem CP16 wurde ein einzelner **Testkompatibilitätsfehler** korrigiert: Historische Controller-only-Fixtures ohne ConfigManager konstruieren weiterhin einen inert bleibenden Controller, ohne dass der zusätzliche Battery-Care-Persistenzadapter im Konstruktor auf `.get` des fehlenden Testdoubles zugreift. Bei gültiger realer Controllerkonfiguration gilt unverändert das Fail-Closed-Grid-Episodengate aus CP16. Kein fachlicher Ladealgorithmus, neuer Publisher oder Command-Effekt-Safety-Bypass wurde in CP17 ergänzt.
- **QA:** CP16-Volltest ergab 1.036 Tests, 1 Legacy-Fixture-Konstruktorfehler; CP17-Quellkorrektur ist mit **1.036/1.036 `unittest` PASS, `ResourceWarning=error`, 51,759 s** vollständig nachgetestet. Das ist keine reale Netzlade-/Restart-/Pi-Feldabnahme. Persistenter tatsächlicher Command-Effect-Fehler und SOC-Graph/UI, UML/As-built, Readback-/Echtwirkungs-/Installer-/Release-Gates bleiben offen. Alle bisherigen Ledger-IDs und CP01–CP16-Historie bleiben erhalten; keine Sourcebereinigung, kein Installationspaket. iPhone-Termius-Deployment erst nach finaler Build-/Installationsfreigabe.

## Engineering-Nachtrag CP16 – 26.10.2026, persistente Battery-Care-Grid-Episode und Restart-Gate (kein Release)

- `ZEC-BL-BATCARE-001`: **CP16_EPISODE_RESTART_PERSISTENCE / DEVELOPMENT_NOT_INSTALLABLE**. CP15 besitzt nun einen in die **bestehende** `zec_operational_events.sqlite3` integrierten Singleton-Episoden-Latch für Stufe 2/3 (`active_level`, **ursprüngliches** `target_reserve_soc`). Die aktive Ladungsanforderung wird erst nach erfolgreicher SQLite-Persistierung der Episodenstufe für den bestehenden Publisher freigegeben. Beim Start wird der gespeicherte Episodenzustand geladen, ohne frühere SOC-Beobachtungstoken, Bestätigungszähler, Monotonic-Timer, Geräte-/Safety-Freigaben oder vermeintliche physische Ladewirkung als frisch zu übernehmen. Rekonfiguration mit niedrigerem R, Restart oberhalb N/E und Ende der Saison bei bereits laufender Notladung beenden die geschützte Episode nicht künstlich. Explizites Care-Off, STOP und manuelle Nicht-AUTO-Modi verwerfen den Episoden-Latch vor möglichen frühen Sensor-Returns; ohne vorhandene Datenbank erzeugt Default-Off dabei keine neue DB. Unlesbare/korrupt gespeicherte Episoden sowie fehlgeschlagene SQLite-Commits sperren den **zusätzlichen Grid-Care-Dispatch** und neutralisieren einen vorher aktiven Care-Anteil über den existierenden Publisher; sie erzeugen keine neue Freigabe.
- **Evidenzgrenze:** Getestete Programmschnittstelle und SQLite-Restart-Simulation sind **kein** realer Pi-Neustart, kein verifizierter SOC-Anstieg, kein Command-Effect-Incident und keine physische Netzladeannahme. Offen: Command-Effect→persistenter Warnvorfall einschließlich Failure-ID und Recovery, vollständige UI/Graph-/UML-/Performance-/Release-/Installer-Gates, echte Feldevidenz. Bereits freigegebene CP15-Source bleibt in der Bibliothek unverändert; alle historisch ausgeschriebenen Ledger-IDs bleiben erhalten, keine Quellenbereinigung und deshalb kein `BACKLOG_NO_DROP_GATE` zur Löschung ausgelöst. Termius-iPhone-Installationsanleitung erst mit einem späteren freigegebenen Installer.

## Engineering-Nachtrag CP15 – 26.10.2026, aktiver Stufe-2-/Stufe-3-Dispatch (kein Release)

- `ZEC-BL-BATCARE-001`: **CP15_GRID_LIVE_DISPATCH / SOURCE_FOCUSED_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Stufe 2 (bei bestätigter zulässiger, nicht entladender Primärlage) und Stufe 3 (unmittelbares Notlade-Intent mit nur wirtschaftlicher Cross-Charge-Ausnahme) können aus dem CP14-Quelladapter über die **bestehende** `_publish_signed_target`-Command-/Safety-/Readback-/Late-Effect-Kette ein begrenztes positives Netzladeziel anfordern; kein neuer MQTT-Publisher, keine SMA-Steuerkommandos. Frische AC-/SOC-/Grid-/Command-Quellen sind Voraussetzung. Stufe 2 durchläuft weiterhin den normalen symmetrischen Cross-Charge-Korrekturpfad. PV hat bei unabhängig bestätigtem positivem zusätzlichen Care-PV-Kandidaten Vorrang. Rückkehr/STOP/Cap-Verlust/Config-Off neutralisieren aktive Grid-Care-Intention über denselben vorhandenen Publisher, ohne altes Grid-Ziel als AUTO-Baseline zu vererben; bei bestehender Entladung zunächst Neutralisierung.
- **Begrenzung:** sourcefokussierte Tests 55/55 PASS; eine aktive `CareDecision` ist ausdrücklich **kein** physischer Ladeerfolg. Persistente Episoden-/Restart-/Saisonende-Provenienz, echte Command-Effect-Incident-Öffnung/-Auflösung, optimierte PV/Grid-Übergänge, Device-/BMS-Extremfälle, vollständige Suite samt ResourceWarning/Browser/Performance, Dokumentation/UML/Datenblatt/Installer und vollständiges Releasegate bleiben offen. Insbesondere darf ein Restart während einer bereits über N oder E hinaus aufgeladenen Episode diese **nicht** als geschlossen behandeln; dieses verpflichtende Persistenz-/Recoverygate ist vor irgendeinem Installationspaket nachzuholen. `PRODUCTIVE_PASS` und reale Pi-Installation sind nicht freigegeben. Der Benutzer nutzt bei späterem freigegebenem Remote-Update Termius auf dem iPhone.
- Keine No-Drop-Bereinigung; B2/C1/Adaptive/S3 sowie historische Befunde/Evidenzen unverändert im Master-Ledger erhalten.


## Engineering-Nachtrag CP14 – 26.10.2026, Netzpflege-/Notlade-Mess- und Policy-Gate (kein Installer)

- `ZEC-BL-BATCARE-001`: **CP14_GRID_POLICY_SHADOW / SOURCE_QA_FOCUSED_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Auf unverändert extern geprüftem CP13 wurden die bestehenden reinen Stufe-2-/Stufe-3-Policies gehärtet und mit einer sourcegebundenen, rein diagnostischen Runtime-Beobachtung verbunden. Das Messgate prüft explizite SOC-Quellsequenz, Netz-/Zendure-AC-Richtung mit echtem Quellalter, SmartMode-/Readback-/Command-Schutz sowie Primärspeicher-Leistungs- und optionale Floor-Capability-Freshness. Ein bekannter, aber stale SMA-Floor wird **nicht** irrtümlich als andere neutrale Primärtopologie freigegeben. Vorhandene Notlade-Reserveziele werden bei späterer Konfigurationsabsenkung nicht stillschweigend kleiner; `MAX_SOC_PERCENT` stammt nun aus tatsächlichem Controller-Config-Snapshot statt pauschal 100 %. Die wirtschaftliche Cross-Charge-Entscheidung wird im Notlade-Shadow nicht als Hardware-Safety-Aussage missverstanden.
- **Noch nicht aktiv:** CP14 publiziert keine neue Netzlade-/Notladeanforderung; `CareDecision.stage=EMERGENCY_REQUESTED` ist ein hypothetischer Sollzustand, kein realer Lade-/Wirkungsnachweis. Persistente Episoden-/Restart-Provenienz, physische Rückmeldung, Incident-Verdrahtung und Ausnahme-Dispatch verbleiben ausdrücklich offen. Fokussierte Tests 47/47 PASS, volle QA erst nach Sicherung; Produktivinstallation nicht autorisiert. Noch keine Release-/Field-/Battery-Care-Wirkungsfreigabe.
- iPhone-Fernzugang für spätere Nutzerinstallation: **Termius** (kein Release-/Pi-Eingriff ohne ausdrückliche Freigabe). Master-Ledger und ältere Source-/Evidenz-IDs ohne Bereinigung erhalten.


## Engineering-Nachtrag CP13 – 26.10.2026, Stufe-1-PV-Dispatch im vorhandenen Command-Owner

- `ZEC-BL-BATCARE-001`: **IN_DEVELOPMENT / CP13_STAGE1_LIVE_DISPATCH_FOCUSED_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Aufbauend ausschließlich auf CP12 ist der zuvor rein diagnostische, vollständig source-geprüfte PV-Absolutkandidat bei tatsächlich aktivierter validierter Care-Saison (`SOC<R`) in den vorhandenen `handle_charge`-/`_publish_signed_target`-Pfad eingebunden. Deadband-Freigabe, isolierte AUTO-Baseline, keine B+Fast+Care-Doppeladdition, Netzimport-Rücknahme des Care-Zusatzes sowie sauberer Exit bei Care-Off sind quell- und testseitig geprüft. Primary-Sample-Alter und Bestätigung nach Import-Backoff zusätzlich gehärtet. **Keine reale AC-Ladewirkung, Ertragsverbesserung, Geräteakzeptanz oder Sicherheit im produktiven Pi als PASS behauptet.**
- **Noch offen:** komplette Stufe-2-/3-Netz- und Notladeepisode, Cross-Charge-Ausnahme nur für Notladung, echte Command-Effect-Incident-Anbindung, vollständiger Settings-/UI-/Warn-/SOC-Graph-Vertrag, Regression/Performance/22-UML/As-built/Datenblatt/Installer/Fresh-Extract/Release-Gates sowie realer Feldnachweis. Keine Pi-Installation freigegeben. Für späteres Deployment per iPhone ist Termius als vorhandener SSH-Zugang vom Nutzer bestätigt; die endgültigen Schritte sind release-/installergebunden abzuleiten. Sämtliche Ledger-IDs und historische Evidenz bleiben erhalten.

## Engineering-Nachtrag CP11/CP12 – 26.10.2026, Battery-Care-PV-Arbiter und read-only Sourceadapter

- `ZEC-BL-BATCARE-001`: **IN_DEVELOPMENT / CP11_PV_ARBITER_FOCUSED_PASS / CP12_PV_SHADOW_RUNTIME_PASS / DEVELOPMENT_NOT_INSTALLABLE**. Ein quellenneutraler, side-effect-free Stufe-1-Arbiter bildet die **absolute** Netz-/Primär-/Zendure-AC-Bilanz und isoliert den zusätzlichen Care-Anteil von der normalen AUTO-Baseline. Distinct/Fresh-Quellen, AC-Istrichtung, SmartMode-/Commandbereitschaft, unmittelbare Import-Backoff-Neutralisierung nur des Care-Zusatzanteils und schrittweise Attack sind als mathematische Kandidaten implementiert. CP12 integriert die bereits vorhandenen unabhängigen Sourcefelder **ausschließlich als read-only Schattenentscheidung** in `run_once`, ohne neuen MQTT-Publisher oder Live-Gerätekommando. Fokussiert 34 Tests PASS, vollständiger `unittest`-Lauf mit `ResourceWarning=error` **989/989 PASS**. Keine neue produktive PV-Ladewirkung belegt und Stufe 1 noch nicht live angeschlossen.
- **Noch offen:** kontrollierte Einbindung des Care-PV-Absolutziels im vorhandenen AUTO-/Deadband-/`low_surplus`-Dispatch ohne Fast-Capture-Doppeladdition und ohne Baseline-Leck beim Exit; vollständige Stufe-2-/Stufe-3-Episoden/Command-/Effect-/Warnintegration; UX/Graph/22-UML/Datenblatt/Installer/Release- und Feldevidenzgates. Kein Produktiv-Pi-Zugriff und keine Installationsfreigabe. Alle historischen Ledger-IDs, B2/C1/Adaptive/S3 und bisherigen offenen Evidenzpunkte unverändert erhalten. CP11 und CP12 sind getrennte Vollcheckpoints, CP12-Bibliotheksgate ist erst nach unabhängiger Rücklese PASS.

## Engineering-Nachtrag CP10 – 26.10.2026, wirksamer Status-SOC-Vertrag

- `ZEC-BL-BATCARE-001`: Realer Controller-State-Pfad setzt für die bereits integrierte saisonale AUTO-/NIGHT-Entladegrenze nun die effektiven SOC-Statusfelder. Disabled, fehlende validierte Policy, Out-of-Season, STOP/FIXED, stale SOC und SAFE_STATE zeigen keinen aktiv wirksamen Care-Grenzwert. 30 fokussierte Tests PASS. Kein Nachweis physischer Wirksamkeit und kein vollständiger Battery-Care-Lade-/Incident-/Graph-/Releasevertrag. Der CP09-Bestand blieb ansonsten erhalten; alle historischen Ledger-IDs unverändert.

## Engineering-Nachtrag CP09 – 26.10.2026, Packaging-/QA-Reconciliation

- `ZEC-BL-BATCARE-001`: CP08-Vollregression 968 Tests, zwei **Unix-Dateimodusfehler** nach ZipFile-Extraktion; alle 46 betroffenen CP07-Ursprungsmodi wiederhergestellt, keine zusätzlichen Regleränderungen. Erst nach neuem rücklesegeprüftem CP09 erneute Voll-Regression. Keine geänderte Freigabe oder Feldevidenz, keine Ledger-ID entfernt.

## Engineering-Nachtrag CP08 – 26.10.2026, kein Release

- `ZEC-BL-BATCARE-001`: **IN_DEVELOPMENT / CP08_DISCHARGE_FLOOR_FOCUSED_PASS / NOT_INSTALLABLE**. Die wirksame saisonale AUTO-/NIGHT-Entladegrenze und Deadband-HOLD-Neutralisierung sind auf dem CP07-Quellstand integriert. Disabled/außer Saison/invalid bleiben differential legacy, Night→AUTO darf die Care-Reserve nicht unterschreiten, echte PV-Ladeausgänge bleiben dem bestehenden Command-Owner vorbehalten. Weder Stufe 1/2/3 noch Incident-Effect-Integration oder vollständige UX/Graph-Funktion gelten dadurch als fertig. Der im Folgedokument genannte Testumfang ist fokussierte Sourceevidenz, keine Hardwarefreigabe.
- `CHECKPOINT_LIBRARY_GATE` für CP08 ist erst nach unabhängigem Upload/Readback als PASS auszuweisen. Alle bisherigen IDs, B2/C1/Adaptive/S3-/Evidenzzustände und historischen Einträge unverändert behalten; keine Quellenbereinigung.


## AKTUELL – 26.10.2026, Battery-Care-Sourcefreigabe (kein Release)

- `ZEC-BL-BATCARE-001`: **SPEC_FINAL_20261025 / USER_SOURCE_SCOPE_APPROVED_20261026 / DEVELOPMENT_IN_PROGRESS / NOT_INSTALLABLE**. Ausdrückliche Nutzerfreigabe für den **gesamten** finalen Battery-Care-Sollvertrag mit begrenzter Cross-Charge-Notladeausnahme, Settings, drei Stufen, Status/Graph, persistenter Incident-Warnung, Tests und Release-Dokumentation; **keine** reale Pi-Installation freigegeben. Exakter Spezifikations-SHA256 `eb192149a885fe5eeb89a0af28b937251eafa9d4a5d6b6bbfba2a4552a9f3d29`. Nur das verifizierte V17.1.3-Release ist Startsource, nicht das konzeptionelle CP02. Geänderte Cross-Charge-Invariante ausschließlich nach `03` §3a; sonstiges Safety-Regelwerk unverändert. Dieser Zusatz überstimmt nur die unten historisch datierte Kennzeichnung `NO_CODE_AUTHORIZATION` für diesen Scope, **nicht** die historischen Ledger-Inhalte.
- Vollständige Entwicklung erst nach bestandenem `CHECKPOINT_LIBRARY_GATE` je wesentlichem Sourceblock fortsetzen; jeder Zwischencheckpoint bleibt `DEVELOPMENT_NOT_INSTALLABLE` bis vollständige Freigabegates. Kein technischer Build-/Hardwarewirkungs-PASS allein aus Tests.
- B2 `ZEC-BL-CTRL-USABLE-SOC-001`, C1 `ZEC-BL-CTRL-CAP-001`, Adaptive `ZEC-BL-CTRL-ADAPTIVE-001`, S3 `ZEC-BL-CTRL-S3-001`, SOH `ZEC-BL-BATTERY-SOH-001` und alle Evidenz-/Historieneinträge bleiben unabhängig mit unverändertem Erledigungs-/Evidenzstatus erhalten.

## AKTUELL – 23.10.2026, V17.1.3 REAL_FIELD_PASS und Folgeroadmap

**Alle folgenden Altstände sind historische Planungs-/Implementierungsprovenienz; die bestehenden Ledger-IDs bleiben vollständig erhalten. Dieser Nachtrag ersetzt keine frühere ID und erzeugt keine zweite Roadmapautorität.**

- **Release:** `V17.1.3 / v17.1.3-20261022` ist am 23.10.2026 via `SUPPORTED_UPDATE` auf dem Pi installiert, Installer `PREFLIGHT_RESULT=PASS`, `ready=true`. Die vom Nutzer gepostete komplette allgemeine Feldabnahme hat global und in jedem ausgegebenen Einzelcheck `PASS`, darunter `FULL_READY`, `READY:FULL_READY`, `RELEASE_BACKUP_EXACT`, Fast-Capture-/Settings-/Graph-Surfaces und bestehende Performancebudgets. Terminalausgabe als ausreichende allgemeine Feldbeobachtung akzeptiert; kein zusätzlicher JSON-Upload oder formelles Feldabnahmeprotokoll erforderlich. Eigenständiger Real-Clean-Fresh-Install-Test und spezifische natürliche Effekt-/Fehler-Episoden bleiben getrennt offen.
- `ZEC-BL-UI-SETTINGS-HELP-001`: **IMPLEMENTED_V17_1_3 / TECHNICAL_QA_PASS / GENERAL_FIELD_PASS**. 190 operative Settings-Hilfen, 74 Bereichshilfen, Metahinweise und erklärte deaktivierte Wirkung; kein Anspruch einer manuellen Satz-für-Satz-Textprüfung, neue UX-Funde bleiben wiedereröffnungsfähig. Dauerqualitätsvertrag `04` unverändert gültig.
- `ZEC-BL-UI-STATUS-COMPACT-001`: **IMPLEMENTED_V17_1_3 / VISUAL_QA_PASS / GENERAL_FIELD_PASS**; kurze Minigraph-Erklärung, 103-px-Diagramm erhalten, Desktopkartenkompaktheit und mobil keine abgeschnittenen Quellen/Freshness-Angaben; reale Screenshotbeobachtung vom 23.10.2026 ergänzt synthetische Layoutmatrix. `ZEC-BL-UI-STATUS-003` (Warnchip) und `ZEC-BL-GRAPH-GAP-001` (Datenlücken/Inspector) bleiben bereits realisierte, im V17.1.3-Rahmen regressionsgeschützte Vorgängerfeatures; keine erneute Funktionsentwicklung durch diesen Release.
- `ZEC-BL-DOC-ARCH-001`: **UML_SUBSCOPE_INTEGRATED_V17_1_3 / DOC_UML_RELEASE_GATE_PASS / ONGOING_RELEASE_MAINTENANCE**. Dauerhafter As-built-Atlas aus 22 überprüften DOT/SVG/PNG-Diagrammen unter `docs/architecture/uml/`; bei jedem relevanten Folge-Release Quelle/Visuals/Traceability/Handbuchbezug erneut nachziehen. Historische V0.4-Quellen bleiben Provenienz.
- `ZEC-BL-DEP-README-001`: Ein-ZIP-Installationsvorgang in V17.1.3; SHA256 ist im externen Bash-Befehl direkt prüfbar, ohne zweite Datei auf den Pi kopieren zu müssen. Neue Code-Releasebasis bleibt unverändert; Build-/Readback-Gates bestanden.
- **Empfohlener nächster eigenständiger Fach-/Spezifikationsblock:** `ZEC-BL-BATCARE-001`, **SPEC_NEEDED / WINTER_PRIORITY / NO_CODE_AUTHORIZATION**. Gemäß Roadmapentscheid 18.10. sind B2 (`ZEC-BL-CTRL-USABLE-SOC-001`) und C1 (`ZEC-BL-CTRL-CAP-001`) weiterhin unabhängige offene Optionen. Battery Care darf mit dokumentierter Winternutzen-/Komplexitätsbegründung vorgezogen werden, nicht wegen einer unterstellten S3-/B2-/C1-Abhängigkeit. Zunächst Ziel/Nichtziel, aktuelle reale Verbraucher/Regelvorränge, SOC-/Zeit-/Schwellen-/Episode-, Netzlade-/Cross-Charge-, BMS-/Safety-/Recovery-Vertrag und Wirksamkeitsnachweis fachlich entwerfen und vom Nutzer explizit freigeben lassen. Eine ältere Brainstorming-Diskussion ist keine freigegebene Spezifikation; **keine implizite Genehmigung zu Netzladung oder Änderungen am Regler**. Adaptive bleibt `DEFERRED / EVIDENCE_GAP`.
- **Weiterhin separat:** `ZEC-EV-DEP-001` echter Clean-Fresh-Test ausstehend, keine destruktive Pi-Aktion. S3-Naturwirkung, Fast-Capture-Aktiv-FULL_IDLE, Grid-Stale und NIGHT/MIN_SOC bleiben nach ihrer tatsächlichen Evidenzlage im Ledger erhalten; ein allgemeines Feld-PASS ersetzt diese nicht.


## V17.1.3 Sammelrelease – technischer Implementierungs-/QA-Nachtrag 22.10.2026

**Geltung:** Keine neue Roadmapautorität, kein Löschen oder Umdeuten historischer Einträge. Alle bestehenden stabilen IDs werden unterhalb erhalten. Die reale produktive Version bleibt V17.1.2, bis V17.1.3 installiert und eigenständig feldabgenommen wurde.

- `ZEC-BL-UI-SETTINGS-HELP-001`: V17.1.3-Umsetzung der 190 operativen individuellen Hilfen, 74 Bereichserklärungen, dynamischen Meta-Hinweise, Ein-/Aus-Erläuterungen sowie Fast-Capture-Optionsnamen. Fokussierte und vollständige technische Regression PASS; qualitative reale Anwenderlektüre bleibt nach Installation separat zu bewerten. Keine Regler-/Safetyänderung.
- `ZEC-BL-UI-STATUS-COMPACT-001`: kompakte Minigraph-Beschriftung, X-Achse „Aktuellster Wert“, volle 103-px-Diagrammhöhe; synthetische Standard-Desktopgeometrie bei 1280/1769 px 300 px und mobile Footer ohne Cropping. Zusätzliche Expertendetails können berechtigt mehr Raum benötigen. Technischer Visualvertrag PASS, reale Feld-UX ausstehend.
- `ZEC-BL-UI-STATUS-003` und `ZEC-BL-GRAPH-GAP-001`: bestehende bereits implementierte Warnchip- und Graph-Lückenbehandlung in der realen V17.1.2-Source nachgeprüft; keine erneute Sourceentwicklung, Regression bewahrt. Historische offene Einträge bleiben als Provenienz erhalten.
- `ZEC-BL-DOC-ARCH-001`: UML-Unterumfang als dauerhafter Release-As-built-Standard unter `docs/architecture/uml/` integriert; 22 DOT-/SVG-/PNG-Blätter, Source-/Visualreview und fail-closed `DOC_UML_RELEASE_GATE=PASS`. Handbuchhistorie nicht als aktuelles Produkt umetikettieren.
- `ZEC-BL-DEP-README-001`: V17.1.3 aktualisiert nur mit genau einem ZIP auf dem Pi, SHA256-Erwartungswert extern direkt im Bash-Installationskommando; kein Sidecar-Upload erforderlich. Clean Fresh real gesondert unter `ZEC-EV-DEP-001` offen.
- **Technisches QA-Ergebnis:** reguläre und strenge Regression jeweils 171 Testdateien / 1.254 Tests + 1.126 Subtests PASS, technische Deployment-/Dokumentations-/Datenblatt-/Browser-Gates. Endgültiger technischer Release-PASS erst nach finales Source-Manifest, Fresh-extract und unabhängigem Release-Bibliotheks-Readback. Keine automatische Änderung funktionsspezifischer realer S3-/Fast-Capture-/Grid-Stale-/Nacht-Evidenz.


**Stand:** 21.10.2026 – aktuelle Feld-/Qualitäts-Reconciliation; frühere Zeitstände erhalten  
**Status:** kanonische, persistente Entwicklungsledger- und Roadmap-Autorität  
**Aktuelle Produktbasis:** V17.1.2 real auf dem Raspberry Pi installiert; allgemeine automatische Feldabnahme `PASS / FULL_READY / READY:FULL_READY`, Rollback `RELEASE_BACKUP_EXACT` am 21.10.2026. Die historisch beschriebenen V17.1.0-/V17.1.1-Stände unten bleiben Provenienz. Für natürliche S3-/NIGHT-/Grid-Stale-/Fast-Capture-FULL_IDLE-Episoden sowie echten Clean Fresh Install bestehen weiterhin gesonderte Evidenzgrenzen.

## Aktuelle Ledger-Fortschreibung – 21.10.2026 (vor historischen Einträgen maßgeblich)

**Autorisierung:** ausschließlich Projektquellen-/Ledgerpflege auf ausdrücklichen Nutzerauftrag. **Keine** Freigabe für Produktcode, V17.1.3-Tests, Paketierung oder produktive Installation. Der vorhandene CP02 bleibt eingefroren. Die fachliche Folgerelease-Konzeption soll vor Sourceentscheidung weitere Nutzerpunkte aufnehmen; **kein isolierter Quick-Hotfix und kein zusätzlicher Pi-Installationszyklus ohne Notwendigkeit**.

### ZEC-BL-UI-SETTINGS-HELP-001 – erneuter verbindlicher Feldqualitätsbefund

- **Status aktuell:** `IMPLEMENTED_V17_1_2 / TECHNICAL_QA_PASS / FIELD_UX_REOPENED / NEXT_BUNDLED_RELEASE_SCOPE_UNAPPROVED`. Alle 190 operativen Hilfen und 74 Bereichserklärungen besitzen technische Abdeckung. Reale Nutzerlektüre vom 21.10. belegt **keinen vollständigen sprachlichen Qualitätsabschluss**, trotz allgemeinem V17.1.2-Feld-PASS. Früherer `IMPLEMENTATION_PARTIAL`-Text darunter bleibt seine historische Zeitstandsaussage.
- **Verbindlicher Korrekturvertrag:** Sektionshilfe erläutert Zweck und Verhältnis der Einstellungen, nicht die Optionsliste eines einzelnen Settings; je Setting tatsächliche Auswahlbenennungen in Anführungszeichen, ausdrücklich Ein-/Aus-Wirkung und Nichtwirkung, realer Verbraucher, Vorränge, Folgen/Abhängigkeiten und anschauliche Darstellung. Nicht nur `extended_help`, sondern sämtliche angezeigten kurzen Hilfen, Meta-Chips, Default-/Apply-/Sicherheitsausgangs-Hinweise, Tooltips und Standard-/Expertenkontexte. Fachbegriffe (`FULL_IDLE`, `NEAR_LIMIT`, Overlay, Hysterese, 0-W-Neutralisierung, Untertracking, Intent, etc.) ersetzen oder unmittelbar nachvollziehbar erklären; Rechtschreibung/Grammatik prüfen. Komplexe Sektionen wie Tagesprofile und S3 ausführlicher im Zusammenhang erklären. Fachliche Detailanforderungen und Exit-Matrix stehen **normativ in `04`**.
- **Konkrete Nutzerevidenz:** Screenshot Fast Capture mit unverständlichem „Overlay 0“, Sektion nennt technische Modecodes und erklärt den einzigen Dropdown schon vorweg, Optionsnamen teilweise nicht deckungsgleich mit „Aus“, „Shadow (nur Diagnose)“, „Aktiv“, grammatischer Fehler „voll ... kaum noch lädt“; weitere Nutzerbeispiele zu „klassifizieren“, „Hysterese“, „Command-Wirksamkeitskontrolle“ und nicht erklärter Abschaltwirkung. Keine pauschale Behauptung, alle Felder hätten denselben Fehler. Im nächsten genehmigten Release inventarisieren, fachlich überprüfen und in der gerenderten UI abnehmen.
- **Exit:** technische Vollständigkeit plus menschlich nachvollziehbare Vollprüfung der 190/74 aktuellen Texte und aller zugehörigen Meta-Labels; Mapping zur implementierten Wirkung, negative Aus-Fälle, Responsive/Accessibility und Regression; reines Keyword-/Snapshot-Gate reicht nicht. `CLOSED` erst mit wirklichem Abschluss; kein sofortiger Releasezwang.

### ZEC-BL-UI-STATUS-COMPACT-001 – Kompaktheit der Statusseite ohne Informationsverlust

- **Status:** `OPEN / REAL_FIELD_UX_REGRESSION_V17_1_2 / FROZEN_CANDIDATE_CP02 / NEXT_BUNDLED_RELEASE_SCOPE_UNAPPROVED`.
- **Realer Befund:** Die im V17.1.2-Release notwendige Behebung eines abgeschnittenen Minigraph-Netzquellen-/Freshness-Footers vergrößert mit dem langen Minigraph-Erklärungstext die gemeinsame Kartenreihe und verschiebt darunter den SOC-Tagesgraphen/weitere Statusbereiche nach unten. Desktop-Screenshot 21.10.2026; keine Safety- oder Messpath-Korruption behaupten. Nutzerpriorität: hohe Informationsdichte ohne unnötiges Scrollen bewahren, ohne wieder etwas abzuschneiden.
- **Geplanter UI-Vertrag:** Haupttext knapp „Minigraph-Update 3 s · Livewert 1 s“, soweit tatsächliche UI-Abfrageintervalle zutreffen; rechte Zeitachse „Aktuellster Wert“ statt „Jetzt“. Ausführliche Mess-/Sample-/Lücken-/Tooltipsemantik weiterhin barrierearm zugänglich; Netzwerkquelle, Alter, Validity/Freshness vollständig sichtbar. Keine feste Höhe als versteckter Cropping-Fix; Kartenhöhe, Graphposition und Sichtbarkeit zugleich messen.
- **Evidenz/Gates:** desktop 1280/≈1769 px mit quantifiziertem Referenzvergleich, mobil 320/375/390/430 px, alle 5/15/60-Minuten-Ansichten, lange Provider-Namen, Schriftvergrößerung, Standard/Experte, frische/stale Fälle. Keine unerwünschte vertikale Verschiebung der anderen Karten/SOC-Grafik, kein horizontaler Overflow. Umfangreiche visuelle Vollabnahme und normale QA erforderlich; bloßer CSS-Texttest reicht nicht.
- **Vorhandene, aber nicht freigegebene Provenienz:** CP02 `ZEC_V17_1_3_DEV_CHECKPOINT_02_COMPACT_LAYOUT_20261021.zip`, SHA256 `9a7ff51fe1c237c05555bf17e8ef589646ee8db242add8cbba90bea7ba77695a`, 14.835.446 Bytes, Bibliothek `Checkpoints/`, unabhängiger Readback PASS. `FROZEN / NO_SOURCE_AUTHORIZATION / DEVELOPMENT_NOT_INSTALLABLE`. 988 relevante Dateien gegen Working-Tree identisch; Hilfsskripte und Freeze-Record gesondert archiviert. Nach Scopeabschluss vor Nutzung von CP02 fachlich entscheiden: selektiv übernehmen oder von bestätigter V17.1.2-Releasebasis neu starten.

### ZEC-EV-PROC-SCOPE-001 – Unautorisierter UI-Sourcebeginn / Regelanwendungsfehler

- **Status:** `PROCESS_INCIDENT_RECORDED / NO_NEW_GATE_APPROVED / SOURCE_FROZEN`. Am 21.10.2026 wurden CP01/CP02 für V17.1.3 begonnen, obwohl nach `01` §2 **keine ausdrückliche Source-Freigabe** vorlag. Scopebeschreibung und Änderungswunsch waren Analyse-/Planungsinput, keine Makrofreigabe. Nutzer benennt primär Risiko unbeachteter anderer Regeln, nicht Datenverlust; produktive V17.1.2-Sources bleiben byteidentisch. Bibliothekscheckpointing und Freeze erfolgreich, aber **keine rückwirkende Entwicklungslegitimation**.
- **Bewertung:** `01` §2 enthält die Regel bereits eindeutig; dieser Vorfall ist primär ein **Ausführungs-/Disziplinfehler** und begründet derzeit keinen zusätzlichen technischen Autorisierungsgate, keinen neuen Nutzerklick pro Mikroschritt und keinen isolierten neuen Release. Erst bei wiederholtem Versagen oder belegter nicht abgedeckter Risikostelle eine schlanke technische Schutzmaßnahme gesondert beurteilen. Bei Analyseaufträgen ohne explizite Scopefreigabe keine Produkt-Sourceänderung; bei bereits erteilter Makrofreigabe innerhalb des vereinbarten Umfangs selbstständig arbeiten.
- **Nachweisgrenze:** Checkpoints belegen Integrität und Rücklesbarkeit, **nicht** die zuverlässige Einhaltung jeder projektbezogenen Verhaltensregel. Dies bleibt ein beobachteter Risikofaktor, keine behauptete formale Zertifizierung des gesamten Prozesses. Bestehende Source-, Checkpoint-, No-Drop-, Safety- und Releasegates bleiben vollständig wirksam.

### V17.1.2 Feld-/Installer-/Dokumentations-Reconciliation

- V17.1.2 am 21.10. auf produktivem Pi: allgemeine Feldabnahme mit allen in der sichtbaren Terminalausgabe genannten Einzelchecks `PASS`; Controller `FULL_READY`, `READY:FULL_READY`, Backup `RELEASE_BACKUP_EXACT`, Performance innerhalb bestehender Requestbudgets. **Das vollständige JSON lag nicht als Originalupload vor**; spezifische natürliche Regel-/Fast-Capture-/Stale-/S3-Episoden sind dadurch nicht automatisch nachgewiesen. `ZEC-EV-DEP-001` bleibt `REAL_CLEAN_FRESH_PENDING`.
- `ZEC-BL-UI-GRID-FOOTER-001`: Screenshot-Teilbeleg zur vollständigen sichtbaren Netzquellen-/Freshness-Zeile (5/15/60); Höhenkompaktheit bleibt **separat offen** unter `ZEC-BL-UI-STATUS-COMPACT-001`, keine erneute Footerabschneidung zulässig. `ZEC-BL-UI-GRID-MINICHART-001`: funktionale Darstellung live beobachtet, Text-/Höhenkritik bleibt UX-Abnahmepunkt.
- `ZEC-BL-DEP-README-001`: Nutzer benötigt **nur das veröffentlichte ZIP** auf dem Pi; SHA256 kann direkt als bekannter Erwartungswert im Bash-Befehl geprüft werden. Eine externe SHA256-Sidecar-Datei ist ein optionales Prüfartefakt, **keine zusätzliche notwendige Installationsvoraussetzung**. Das V17.1.2-Paket bleibt unverändert; ursprünglich ausgelieferte README-Texte mit Sidecar-Pflicht sind dokumentarische Provenienz und bei der nächsten regulären Anleitungskorrektur zu berichtigen, ohne dafür allein einen neuen Produktrelease zu erzeugen.
- `ZEC-BL-CTRL-S3-001`: Saisonstrategie bleibt bewusster Opt-in; Nutzer-Screenshot zeigt Schalter „Aus“. Ohne Freigabe/Aktivierung keine zusätzliche S3-Saisonwirkung; weitere physische Strategieevidenz bleibt offen. Kein ungefragtes Aktivieren auf dem Pi.
- **Sequencing:** Nutzer will weitere fachliche Punkte vor abschließender Folgerelease-Freigabe bündeln. Keine V17.1.3-Weiterentwicklung, keine weitere Pi-Installation und keine Veröffentlichung bis zu inhaltlich geschlossenem und ausdrücklich freigegebenem Scope.


### ZEC-BL-UI-SETTINGS-HELP-001 – Anwendergerechte Settings-Erklärungen und Bereichszwecke

- **Status:** `IN_PROGRESS / USER_APPROVED_20261020 / IMPLEMENTATION_PARTIAL`; vollständige inhaltliche Umsetzung und Freigabe **noch offen**.
- **Zweck/Pflicht:** Jede tatsächlich angebotene Einstellung muss ohne Entwicklungs- oder Elektrotechnik-Vorkenntnisse ihren konkreten Systemzweck und die Wirkung auf Regelung, Steuerausgabe oder reinen Diagnose-/Speicher-/Zugriffspfad erläutern. Der Zusammenhang zu benachbarten Einstellungen, Aktivierungsschaltern, Quellen, wirksamen Limits, Ausnahmen und Vorrangregeln ist **Pflichtbestandteil des einleitenden Haupttextes** und darf nicht in isolierte technische Unterkapitel ausgelagert werden. Benutzer müssen unterscheiden können zwischen *gespeichert*, *aktiviert*, *anwendbar*, *berechnet* und *physisch wirksam*.
- **Hilfestruktur:** Direkt unter jeder Bereichsüberschrift steht eine sinnvolle, dauerhaft sichtbare Erklärung zum jeweiligen Zweck. Die Hilfe je Setting behandelt fachlich korrekt: (1) Wozu und Verhältnis zu anderen Settings/Reglerpfaden, (2) Ein/Aus bzw. Änderung und Optionen, (3) Wann/nicht anwendbar, (4) konkrete Auswirkungen und übergeordnete Schutzregeln, (5) passende anschauliche Beispiele. Technische Kennungen und Codes nur ergänzend für Experten.
- **Kein generischer Fallback als fertige Hilfe:** Formeln wie `Konfiguration für …`, `wirkt gemäß …`, `zusammengehörige Parameter …`, `RICH/BASE` oder rein technische Metadaten gelten nicht als Endnutzer-Erklärung. Alle operativ sichtbaren Settings einschließlich Standard/Experte müssen individuell gegen echten V17.1.0-Source-Consumer/Registry und Hardware-Safety begründet werden. Fehlende oder nicht verifizierbare Beschreibung wird als Qualitäts-Finding inventarisiert und verhindert UI-Completion.
- **Umsetzung in überprüfbaren Scheiben:** erster Source-Slice S3-Saison-/Tagesprofiltexte, Hilfedialog-Grundstruktur und sichtbare Abschnittszwecke; noch **kein** Gesamt-PASS für ca. 190 operative Settings. Erweiterung in der Registry automatisiert inventarisieren und in fachlichen Schritten abarbeiten, ohne die QA für Teilfortschritt als Gesamtabnahme auszugeben.
- **Tests/Exit:** Quellenmapping und Vollständigkeits-/Placeholder-Gates, nachvollziehbare Text-/Wirkungsprüfung jedes aktiven Keys, i18n/mobile/standard/expert/accessibility, Headless-Browserprüfung, Negativfälle bei abgeschalteter S3-Policy und unveränderte Command-/Controllerlogik; vollständige Regression und Releasegates erst vor Produktivpaket.
### ZEC-EV-HOST-FREEZE-001 – Historischer externer Host-Freeze, Provenienz
- **Status:** `HISTORICAL_EVIDENCE_GAP / NO_NEW_RELEASE_SCOPE`. `RELEASE_INFO_V12_12_2.md` erwähnt einen externen 14-Minuten-Host-Freeze ausdrücklich als damaligen Nicht-Scope. Dieser alte Hinweis wird erhalten, nicht als aktuell reproduzierter ZEC-Fehler eingestuft. Nur bei neuer Beweislage beurteilen.

### ZEC-BL-CTRL-REFACTOR-001 – Historische optionale Controllerzyklus-Refaktorierung
- **Status:** `DEFERRED_IDEA / NO_APPROVED_CODE_SCOPE`. `TECHNICAL_NOTES_V12_8_6.md` nennt eine mögliche spätere größere Refaktorierung. Nicht als Entwicklungspflicht oder freigegebener Umbau der Safetysemantik interpretieren.



### ZEC-BL-DOC-ARCH-001 – Reconciliation historischer Release-Root-Originale V17.1.2

**UML_RELEASESTANDARD_APPROVED_20261022 / SUBSCOPE_OPEN:** Nutzer hat die *dauerhafte* Integration des echten 19-Blatt-Atlas V0.4 (originaler SHA256 `1b1229b8958bafbd69cd676a1986e77605dd09673847b6872ef54481a4a8a4c5`) ab dem nächsten neu gebauten ZEC-Release unter der bestehenden Architektur-/As-built-Dokumentation freigegeben. Basis für neue fachliche Diagramme ist die aktuell veröffentlichte V17.1.2-Source, **nicht** die V17.0.2-UML-Historie oder die V17.1.0-Handover-Zeitstandsnotiz. Verbindlicher Umfang: Quellen + offline SVG/PNG, 19-Blatt-Impact und sinnvolle Ergänzungen, Source-Traceability, Index/README/As-built-/Handbuch- und Datenblattpflege, integriertes fail-closed `DOC_UML_RELEASE_GATE`, Fresh-extract und SHA/No-Drop, Source-Checkpoint je Slice extern rückgeprüft. Die UML-Vorintegration mit 22 DOT/SVG/PNG-Blättern ist derzeit `TECHNICAL_DRAFT / SOURCE_REVIEW_REQUIRED`, keine aktuelle Release-/Feldfreigabe. Kein Controller-/Command-/Safety-Scope, keine separate Roadmap-/Projektdatei für die Diagramme. Keine isolierte Produktinstallation: Abschluss und fachliche Gateprüfung im nächsten gebündelten Release mit eigener späterer Gesamtumfangfreigabe. Subscope erst nach tatsächlichem As-built-Fachreview und vollständigen Releasegates als umgesetzt kennzeichnen; Pflicht gilt auch nach späterer Umsetzung bei jedem relevanten Folge-Release fort.

**Status:** `RECONCILED_AS_HISTORICAL_PROVENANCE`, 185 ausschließlich versionsbezogene Root-Release-/Notes-/Build-Dokumente werden unverändert nach `docs/history/release_root` umgeordnet; Originalbytes/Hashes/Planungsmarker/Quellen und konkrete Ledger-Referenzen sind zusätzlich in `docs/history/release_root/ARCHIVE_NO_DROP_AUDIT.json` dokumentiert. Historische Nicht-Scope-Angaben sind keine nachträglichen Produktaufträge. Sämtliche Markertexte bleiben byteidentisch in den archivierten Originalen, neue separate EV-/Ideen-IDs sind explizit erhalten. Keine anderen oder unbekannten Dokumente werden entfernt.


## Vorangestellter aktueller Master-Ledger-Status – 21.10.2026

Die V17.1.2-Release-Reconciliation unterhalb ist der **aktuelle** technische Ledgerstatus, nicht die früheren `IN_PROGRESS`-Texte aus der 20.10.-Provenienz. Der V17.1.2-Release-Build ist technisch abgenommen, aber ohne eigenes Pi-Update und echte Fresh-Install-Feldabnahme. Die historische V17.1.0-/V17.1.1-Evidenz bleibt erhalten. Das Projektquellen-Update fügt ausschließlich Texte und stabile IDs hinzu, alle ursprünglich enthaltenen `ZEC-BL-`- und `ZEC-EV-`-IDs bleiben erhalten.


## V17.1.2 – Technische Folge-Reconciliation (21.10.2026)

**Geltungsbereich:** Diese Fassung ist der versionsbezogene Snapshot der kanonischen Projektdatei `05_ZEC_BACKLOG_AND_ROADMAP.md` zuzüglich expliziter Release-Reconciliation; die Projektquelle `05` bleibt alleinige Masterautorität. Produktbasis für die Entwicklung: V17.1.1 mit realem `FULL_READY`-Feld-PASS. V17.1.2 hat ohne Installation noch **KEINEN** eigenen Realfeld-PASS. Historische Statusabschnitte darunter bleiben unverändert als Provenienz.

- `ZEC-BL-UI-SETTINGS-HELP-001`: **IMPLEMENTED / TECHNICAL_QA_PASS / FIELD_UX_PENDING**. 190 operative Settings-Hilfen plus 74 Bereichserklärungen, inkl. Anwendbarkeit/Vorrang/A400-R100; vollständige Tests. Menschliche Feldlektüre und Realbrowserabnahme stehen getrennt aus.
- `ZEC-BL-UI-GRID-MINICHART-001`: **IMPLEMENTED / TECHNICAL_QA_PASS / FIELD_UX_PENDING**. 60-Minuten-Darstellung einheitlich in Zeitminuten, Rohbelege im Tooltip, 5/15-Minuten-Rohdaten, echte Lücken. Kein neuer Regler-/Sensorpfad.
- `ZEC-BL-UI-GRID-FOOTER-001`: **NEW / IMPLEMENTED / TECHNICAL_VISUAL_PASS / FIELD_VISUAL_PENDING**. V17.1.1-Fund: Provider-/Freshness-Footer in der Netzkarte bei 60 Min und kleinen Ansichten abgeschnitten. V17.1.2: variable Kartenhöhe/Umbruch, Chromium-15/15-Layoutbelege; auf dem realen Pi nachprüfen. Kein Safety-Change.
- `ZEC-BL-DEP-README-001`: **NEW / IMPLEMENTED / TECHNICAL_QA_PASS / FIELD_INSTALL_PENDING**. Installations-/Checksum-Vertrag von V17.1.2: keine zirkuläre SHA-Platzhalterkennung im Archiv; echter SHA256 in externer Sidecar-Datei nach Finalfreeze; reguläres Update ausschließlich V17.1.1; Fresh Install nur mit ausdrücklichem `--fresh-install`. Simulierte Deployment-Gates ersetzen keinen Real-Fresh-Install.
- `ZEC-BL-DOC-ARCH-001`: **IMPLEMENTED / TECHNICAL_HISTORY_NO_DROP_PASS / MAINTENANCE_CONTINUES**. 185 versionierte historische Root-Dokumente unter `docs/history/release_root` byteidentisch und einzeln sha256-/marker-/ledgerreconciliiert. Drei aktuelle Übersichten unter `docs/releases/v17.1.2/` sowie aktuelle As-built-Dokumentation. Historische Provenienz bleibt erhalten.
- `ZEC-EV-DEP-001` **DEFERRED / REAL_CLEAN_FRESH_PENDING**. Produktiv-Pi ausdrücklich nicht destruktiv zurücksetzen.
- Adaptive, Battery Care, S3-Naturepisoden, Night/MIN_SOC/GRID-Feldevidenz, Grid-Stale-Realtrigger und Fast-Capture-FULL_IDLE bleiben wie historisch vorgesehen offen; keine automatische Scope-/Statusänderung.

### No-Drop-Status

Sämtliche bisher belegten stabilen `ZEC-BL-`-/`ZEC-EV-`-Kennungen bleiben im Snapshot erhalten. Die historischen 185 Root-Dokumente wurden unter Erhalt der Original-Bytes verschoben; ihre Evidenz-/Planungsmarker sind in `docs/history/release_root/ARCHIVE_NO_DROP_AUDIT.json` je Original abgebildet. Dies ist **keine** Löschung oder Umdeutung früherer Roadmapentscheidungen.

## 1. Zweck und Persistenzvertrag

Diese Datei ist nicht nur eine Liste aktueller offener Aufgaben. Sie ist das **verlustfreie Master-Ledger der ZEC-Produktentwicklung**. Jeder recoverbare relevante Entwicklungs-, Evidenz-, Spezifikations- oder Prozesspunkt erhält eine stabile ID, Provenienz und einen expliziten Status.

Ein Eintrag darf nicht durch Quellenbereinigung verschwinden. Er darf nur fortgeschrieben und in einen anderen Status überführt werden. Die **Roadmap** ist eine priorisierte Sicht auf dieses Ledger; das Ledger selbst bleibt historisch vollständig.

Historische Chats, Übergaben und Releaseunterlagen sind Provenienz-/Archivbelege. Aktuelle reale Sources und aktuelle reale Evidenz haben bei Widerspruch Vorrang.


## Ergänzung 20.10.2026 – Quellenmitgliedschaft / 25-Dateien-Grenze

- **Projekt-Quelleninventar vor diesem Zusatzupdate:** 20 tatsächlich aktive Dateien, darunter kanonische `00`–`07`, das exakte finale V17.1.0-Source-ZIP, Installationsanleitung, Normregelwerke, Lernwerkzeug und historische Planungs-/Evidenzquellen. Acht Kernquellen einschließlich bereits aktualisierter `00`, `02`, `04`, `05`, `07` wurden lesbar angetroffen.
- **Verbindliches Ziel nach manueller Einspielung:** 22/25 Dateien. Nur `00` und `05` mit neuem Inhalt **ersetzen**, `ZEC_S3_PRODUKTIONSSPEZIFIKATION_V17_0_2_FINAL_20261019.md` und `ZEC_V17_1_0_RELEASE_UND_FELDEVIDENZ_KONSOLIDIERT_20261020.md` **ergänzen**. Keine andere Projektdatei löschen oder ersetzen. Anschließende Prüfung des realen Projektbestands ist vor Behauptung `PROJECT_SOURCE_ADOPTION_PASS` zwingend.
- **Verlustfreier Evidenzvertrag:** Das Sammeldokument enthält den technischen V17.1.0-Releasebericht und alle vier Realfeldberichte **vollständig im Originaltext** mit Prüfsummen pro Original. Die getrennten Originale bleiben in der persönlichen Bibliothek `/ZEC - Zendure Energy Controller/Releases/`. Abweichende Datumsstände nicht als aktuelle Feldautorität vermischen; `07` bleibt aktuell. Bibliothek allein ersetzt keinen aktiv angehängten Projektquellenplatz.
- **Backlog-/No-Drop-Vertrag:** Diese Quellenergänzung nimmt **keinen** neuen technischen Roadmappunkt vor, entfernt keine `ZEC-BL-`- oder `ZEC-EV-`-ID, verändert keinen fachlichen Status der Regler-/Safety-/Hardwarewirkung. Der neue Minigraph-Folgepunkt `ZEC-BL-UI-GRID-MINICHART-001` bleibt offen, S3-/Stale-/NIGHT-MIN_SOC-/Fast-Capture-Realnachweise bleiben evidenzabhängig offen. Keine historisch aktive Projektquelle wird entfernt: ein source-spezifisches **Bereinigungs-`BACKLOG_NO_DROP_GATE` ist nicht ausgelöst**; der rein additive Ledger-Identitätsabgleich wird beim Paketbau dokumentiert.
- **Geltungsgrenze:** Dies ist eine **Projektquellenpflege**, keine Source-/Konfigurationsänderung der produktiven Controller-Software, keine neue Version und keine neue Feldfreigabe. Technische `TECHNICAL_BUILD_PASS`- und `FULL_READY`-Evidenz bleibt unverändert.

## Aktuelle Release-/Feld-Reconciliation 20.10.2026 – V17.1.0 (maßgeblich)

- **Release:** unverändertes final veröffentlichtes ZIP `zendure_controller_v17_1_0.zip`, SHA256 `11dddaaaa7831e2339a19b9b7f46412ee72f35917935b7292a005a47bfe61669`, Build `v17.1.0-20261019`; TECHNICAL_BUILD_PASS; 1.220 Tests + 718 Subtests regulär und unter `ResourceWarning=error`, sowie Fresh-extract/Deployment/Manifest/Dokumentationsgates. Reales Pi-Update und allgemeine Feldabnahme 20.10. **PASS / FULL_READY**, `RELEASE_BACKUP_EXACT`.
- `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001`: Sourcefix und vollständige technische Regression umgesetzt; alte Next-Release-Blockerpflicht damit technisch erledigt; natürliche Low-SOC-Export-Feldepisode weiterhin ausstehend.
- `ZEC-BL-GRID-SMA-OBIS-001`: strukturierter Parser inkl. OBIS-Länge/4-/8-Byte/Seriennummer/Negativtests implementiert, technische Regression PASS; historische Extremwertursache weiterhin nicht als eindeutig bewiesen behandeln. Live-HOLD-Grid-Pfad mit SMA-Receiver ist real frisch beobachtet.
- `ZEC-BL-CTRL-S3-001`: abgeschlossener finaler Produktionsvertrag umgesetzt; Opt-in/Legacy-Migration und `NOT_APPLICABLE` im realen HOLD beobachtet; reale Zielwert-/Hardwarewirkung im natürlichen Harvest **EVIDENCE_PENDING**.
- `ZEC-BL-UI-STATUS-LIVE-001`: reale unabhängige 1-Hz-Grid- und Primärspeicherfrische während `HOLD` **PASS**; Browser-/Sourcegates technisch PASS; NIGHT, weitere Quellen und physisch schnelle Gerätewechsel weiterhin differenziert nachzuweisen.
- `ZEC-BL-DIAG-GRID-STALE-001`: Incident-Diagnostik/Entprellung/Resolve technisch PASS, aber nach vollständiger 2-Tages-Inventur (155 Events, davon 0 stale, 0 open) kein natürlicher Grid-Stale-Fall -> Realtrigger/Resolve **NOT_EVALUABLE**. Kein Sensor künstlich trennen.
- `ZEC-BL-DOC-ARCH-001`: Releasegebundene `docs/architecture`, Specs, ADR/History und prüfendes Dokumentationsgate in V17.1.0 PASS. Dauerhafte Pflicht bleibt für Folgeversionen.
- `ZEC-BL-PROC-CHKPT-LIBRARY-001`: CP15 und finales Release-ZIP sind extern Bibliothek-Readback-/SHA256-/Byte-/CRC-verifiziert; gesicherte Releaseevidenz separat im Bibliotheksordner `Releases`.
- **Reales Betriebsereignis:** seit 09:52 genau eine Mode-Transition um 10:03:22 `SAFE_STATE → HOLD`; Journalfolge `systemd Started` 10:03:12, MQTT verbunden 10:03:16, `COMMAND_RESYNC` 10:03:21 stützt Start-/Reinitialisierungskontext, nicht eine Oszillation. Anlass dieses Dienststarts nicht geklärt.
- **UX-Finding** `ZEC-BL-UI-GRID-MINICHART-001` nach Screenshot 20.10.: Live-Netzwert 1 s, Minigraph-Poll 10 s und Controller-Historypunkte typischerweise je Reglerzyklus; sichtbar kein Refreshintervall. **OPEN / NEXT_UI_ITERATION / non-blocking**. Kein rückwirkender Eingriff in eingefrorenes V17.1.0-Release.
- **Roadmap nach Installation:** S3-/Stale-/NIGHT-MIN_SOC-Realnachweise fortführen, Fast-Capture-FULL_IDLE erhalten, weiterhin B2/C1 (separat spezifizieren), Battery Care winterpriorisiert, Adaptive deferred; Graph-UX-Härtung in nächstem passenden UI-Release, ohne Roadmapverlust oder Sicherheitssemantikänderung.
- **No-drop:** alle vor diesem Update erkannten IDs und historischen Roadmap-/Freigabetexte bleiben bestehen; neue ID ausschließlich `ZEC-BL-UI-GRID-MINICHART-001`. Projektquellen werden nicht gelöscht oder archiviert. Das Release-Snapshot im ZIP bleibt unveränderlich und wird nicht nachträglich umgeschrieben.

### ZEC-BL-UI-GRID-MINICHART-001 – Netzleistungs-Minigraph: Aktualisierungsfrequenz sichtbar machen (NEU 20.10.2026)

- **Status:** `OPEN / UX_FOLLOWUP / NEXT_UI_ITERATION`; `implementation_state=not_started`; `priority=non_blocking`; kein Incident im Steuer- oder Messpfad.
- **Reale Evidenz:** Screenshot des produktiven V17.1.0 am 20.10.2026: Netzleistungszahl `+8 W` schnell, letzter Verlaufspunkt `-3 W` wirkt verzögert; keine Erklärung des Chart-Intervalls außer „letzte 48 Punkte“. Exakte Sourcepfade: `static/status_v2.js` PollChannel(`/status-live-data`, **1000 ms**) und PollChannel(`/grid-mini-data`, **10000 ms**); `web_ui.build_grid_mini_payload` liest 48 letzte `state.graph_history`-Regler-Messpunkte.
- **Verpflichtende UX-Abnahme:** in der Karte unmittelbar lesbar unterscheiden zwischen „Livewert (1 s)“ und „Minigraph: letzte 48 Regler-Messpunkte · Aktualisierung alle 10 s“ (oder vergleichbar korrekt und responsive); Chart-Endwert als letzter **Verlaufspunkt** statt als zeitgleich aktueller Istwert ausweisen; Standard/Experte/Mobile, i18n/Info-Text und visuelle Regression prüfen.
- **Optional gesondert:** Minigraph auf echte read-only 1-Hz-Grid-Samples umrüsten, falls nach Performance-/Zeitachsen-/Speicher-/Datenalterkonzept sinnvoll; keine bloße 1-s-Abfrage unveränderter Controller-3-s-Historie als scheinbare Livegrafik. Controller-/Command-/Safety-Semantik nicht ändern. Vor Sourceentwicklung separater UX-Scope und freigegebenes Releasefenster.
- **Exit:** im tatsächlich ausgelieferten Folge-Release UI-Vertrags-/Browser-/Accessibilitytests, sichtbare Refreshsemantik und nachvollziehbare Anzeige bei voneinander abweichenden Live-/History-Werten. V17.1.0 bleibt byteidentisch.

## Historische Freigabe-/Scopefortschreibung 19.10.2026 – S3 + unabhängige 1-Hz-Status-Evidenz

**Nutzerentscheidung:** S3-Produktionsvertrag fachlich schließen und anschließend ohne neue Grundsatzdiskussion auf der verifizierten V17.0.2-Basis entwickeln. Zusätzlich im **nächsten Produktrelease** verpflichtend: 1-Hz-Anzeige der real vorhandenen Netz-/Zendure-/Primärspeicherleistung, SOC und weiterer relevanter Messstati, unabhängig vom Controller-Intervall und davon, ob der Regelpfad in `NIGHT`/`HOLD`/`MIN_SOC` bereits zurückgekehrt ist; Messalter/Validity immer ehrlich mitführen. Grid-Stale/Controller-Processing-Stale als persistente Betriebsereignisse erfassen, open/resolve und Entprellung, ohne Event-Flut. Bestehende zwei Pflichtdefekte und UI-Followups bleiben im selben Produktrelease zwingend. Separate Quellen- und Hardwarepfade (SMA direkt, MQTT, nativer Modbus, Shelly HTTP) dürfen keine unehrlichen Aktualitätsbehauptungen erzeugen.

**Freigabe-/Entwicklungsbasis:** `ZEC_S3_PRODUKTIONSSPEZIFIKATION_V17_0_2_FINAL_20261019.md` ist der geschlossene fachliche Sollvertrag; **keine Release-/Feldevidenz**. Am 19.10.2026 wurde ein **nicht freigabefähiger Source-Checkpoint** begonnen. Die S3-Settings werden dort in einer Entwicklungsfassung verdrahtet, 1-Hz-Read-only-Live-Snapshot (für SMA-Empfänger unabhängig vom Controller) und Grid-Stale-Eventprototyp fokussiert getestet. Erforderliche vollständige Ausleitung für Shelly-HTTP, UI-/Browser-/Sicherheits-/Profil- und sämtliche Releasegates noch offen. Die aktuelle produktive Software bleibt V17.0.2 und darf nicht mit dem Entwicklungscheckpoint verwechselt werden.

### ZEC-BL-UI-STATUS-LIVE-001 – quellenunabhängige sekündliche Statusaktualisierung (NEU 19.10.2026)
- **Status 20.10.2026:** `IMPLEMENTED / TECHNICAL_PASS / HOLD_PARTIAL_FIELD_PASS / EVIDENCE_PENDING_OTHER_MODES`, `implementation_state=implemented`. Ursprünglich `IN_PROGRESS / REQUIRED_NEXT_RELEASE` am 19.10.2026; das ist historische Scope-Provenienz.
- Zweck: Browser-Status jede Sekunde mit den neuesten von den Messquellen empfangenen Werten aktualisieren, nicht nur im Reglerzyklus gepflegte Statusfelder erneut ausgeben. Erfassungsraten der physischen Quellen bleiben separat; fehlende neue Samples als stale kennzeichnen, keine synthetisch frischen Werte.
- Integrität: keine neue Command-/Polling-Autorität, keine 3-s-Reglerbeschleunigung, kein blockierendes HTTP-Modbus-/SMA-/MQTT-IO im Regler; spezifisch unabhängiger Shelly-/Fallback-Quellenvertrag nötig; Zeitalter/Messquellen-/Browserlatenz/Performance auf Pi 3B+ testen.
- Exit: 1-Hz-fester Aktualisierungszyklus sichtbare Seite, Rohquellen auch bei NIGHT/HOLD und vollständigen frischen/staleness Failures, gültige Time-/Validity-UI in Standard/Experte, minimale CPU/IO-Kosten, No-Regression.

### ZEC-BL-DIAG-GRID-STALE-001 – persistente Netzleistungs-Stale-Betriebsereignisse (NEU 19.10.2026)
- **Status 20.10.2026:** `IMPLEMENTED / TECHNICAL_PASS / GRID_STALE_REAL_NOT_EVALUABLE`, `implementation_state=implemented`; 155 Events ohne Stale/OPEN. Ursprünglich `IN_PROGRESS / REQUIRED_NEXT_RELEASE` am 19.10.2026.
- Zweck: ausbleibende Netzleistungsaktualisierung persistiert als eigener Incident mit Quelle, Alter, Reglerzustand; bei verfügbaren unabhängigen SMA-Receiver-Werten `SOURCE_STALE` von `CONTROLLER_PROCESSING_STALE` trennen; Debounce, single-open, resolved/recovered, keine pro-Zyklus-Ereignisflut. Auch bei Regler-Early-Return wirksam.
- Link: `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` funktional reparieren; `ZEC-BL-DIAG-001` Reason-/Stale-Anzeigensemantik weiterhin eigenständig. Dieser Diagnostikscope ersetzt **keinen** der beiden Fixes.
- Exit: mindestens Incident+Recovery bei Nacht/MIN_SOC mit lebendem SMA-RX, echter Sensorstale, initialer Startupphase, anderer Quelle, Modewechsel, SQLite-Restart und UI-Persistenz; realer Feldtest oder dokumentiertes `NOT_EVALUABLE`.

**Quellen-/No-Drop-Status:** Die früheren Ledgerabschnitte/IDs und die historische 87er-Aussage bleiben unverändert erhalten. Zwei neue eindeutige IDs additiv; nie eine Quellenbereinigung vor dem vollständigen `BACKLOG_NO_DROP_GATE`. Dokumentationsgate `ZEC-BL-DOC-ARCH-001` bleibt verbindlich.

### ZEC-BL-PROC-CHKPT-LIBRARY-001 – Extern verifizierte Checkpoint-Sicherung (NEU 19.10.2026)

- **Quellen-Übernahmestand 20.10.2026 nach Teilupdate:** `20_OF_25_VERIFIED / CORE_00_TO_07_ADOPTED / FINAL_S3_AND_EVIDENCE_AGGREGATE_PENDING_USER_UPLOAD`, Ziel `22_OF_25` nach diesem Paket. Hieraus folgt weder ein Produkt-Release-Rollback noch eine automatische PROJECT_SOURCE_ADOPTION_PASS-Behauptung.

- **Status 20.10.2026 (vorher):** `PROCESS_IMPLEMENTED / CP15_AND_RELEASE_LIBRARY_GATE_PASS / PROJECT_SOURCE_REPLACEMENT_PENDING`; die ursprüngliche CP03-Evidenz bleibt historische Provenienz. Source- und Releasebackup sind unabhängig in der Bibliothek byteidentisch verifiziert; die **neuen kanonischen Projektdateien sind erst nach Nutzerupload aktiv**.
- **Nutzerbeschluss 19.10.2026:** vollständige Entwicklungscheckpoints aus temporärem Working Tree **sofort in die persönliche ChatGPT-Bibliothek hochladen, unabhängig wieder materialisieren und Bytezahl/SHA256/ZIP-Integrität vergleichen**; `EXTERNALLY_SECURED` erst nach `CHECKPOINT_LIBRARY_GATE=PASS`. Kein weiteres wesentliches Coding bei ungesichertem Fortschritt. Normative Ausführung in `01` § 3 und `06` § 11; Einstieg `00` § 2c.
- **Konkrete Evidenz:** Checkpoint 03 am 19.10.2026 unter `ZEC - Zendure Energy Controller/Checkpoints/` erfolgreich hochgeladen und byteidentisch zurückgelesen (SHA256 `24b31fd0867ef770c6bbef43a5c942b31477d874fff8e3f5e0964daebb31c3fc`). Checkpoints 04–06 sind dadurch **nicht** wiedergefunden; keine falsche Rekonstruktion.
- **Retention:** keine automatische Löschung; bei Bedarf und mit expliziter Nutzerfreigabe unter Erhalt von Release-/Branch-/Rollback-/Handover-Ankern und allen nur dort erhaltenen Quellen, Tests und Entscheidungen. Bereinigung von Projektquellen/Planungsbelegen setzt zusätzlich `BACKLOG_NO_DROP_GATE=PASS` voraus.
- **Exit:** aktualisierte `00`/`01`/`05`/`06` in aktive Projektquellen übernommen und dort wiederauffindbar; künftig für **jeden** wesentlichen Sourcecheckpoint rücklesbarer PASS samt Evidenz. Kein finales `CLOSED`, solange die Übernahme nicht nachgewiesen ist.

## 2. Statusmodell

- `OPEN`: fachlich offen und grundsätzlich umsetzbar; vor Umsetzung Scope/Freigabe erforderlich.
- `DEFERRED`: bewusst zurückgestellt, nicht erledigt.
- `SPEC_NEEDED`: Thema ist beschlossen/erhalten, aber ein freigegebener implementierbarer Scope fehlt.
- `EVIDENCE_PENDING`: Implementierung existiert im Wesentlichen, aber ein geplanter realer Nachweis fehlt.
- `IN_PROGRESS`: aktiv freigegebener Entwicklungsblock.
- `CLOSED`: implementiert/abgeschlossen; Abschluss- und Releasebeleg bleibt dauerhaft erhalten.
- `SUPERSEDED`: durch spätere Architektur ersetzt; historische Provenienz bleibt erhalten.
- `REJECTED`: bewusst verworfen; Grund bleibt erhalten.

Zusätzlich kann `implementation_state` beispielsweise `none`, `partial` oder `implemented` sein. **Diskutiert**, **freigegeben**, **implementiert** und **real feldvalidiert** sind getrennte Aussagen.

## 3. Aktuelle Roadmap – priorisierte Sicht

**Verbindliches Realfeld-/Source-Delta 25.09.2026:** Der reale V17.0.2-Betrieb und die anschließende Sourceanalyse haben zwei eigenständige Defekte bestätigt. `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` ist **RELEASE_BLOCKER_NEXT_RELEASE**: bei aktivem Nachtfenster und erreichtem Zendure-`MIN_SOC` kehrt der aktuelle Pfad vor frischer Grid-Verarbeitung und normaler exportseitiger AUTO-Regelung zurück; dadurch kann realer PV-Export ungenutzt bleiben. `ZEC-BL-GRID-SMA-OBIS-001` ist **BUG_CONFIRMED / FIX_REQUIRED_NEXT_RELEASE**: der V17.0.2-SMA-Parser sucht Leistungs-OBIS-Bytefolgen global im Datagramm statt die Speedwire-/Protokoll-/OBIS-Struktur robust zu validieren. Der wiederholt verworfene Rohwert `-1.730.098,8 W` ist real belegt; seine exakte historische Raw-Frame-Ursache muss nicht als Vorbedingung für die strukturelle Parserkorrektur erneut eingefangen werden. Der bestehende 30-kW-Plausibilitätsfilter bleibt als zweite Schutzschicht erhalten.

**Release-Gate:** Kein nächster ZEC-Produktrelease darf freigegeben werden, solange **beide** Punkte nicht implementiert und regressionsgeprüft sind. Für `NIGHT-MINSOC-GRID` sind mindestens Nacht+MIN_SOC+Import, Nacht+MIN_SOC+Export, Import↔Export und Nachtende/Recovery nachzuweisen. Für `GRID-SMA-OBIS` sind mindestens valide Home-Manager-Frames, zusätzliche/unbekannte OBIS-Felder, 4-/8-Byte-Recordgrenzen, False-Signature-in-Payload, falsche Protokoll-ID, Truncation sowie die Seriennummernselektion der realen Zwei-SMA-Zähler-Topologie abzudecken.

**Verbindlicher Roadmap-/Strategieentscheid 18.10.2026 (überschreibt nur das bisherige Sequencing, nicht die Historie):** Nach Offline-Bewertung der 23 Herbsttage wird Adaptive-Lernen (A1) **DEFERRED / EVIDENCE_GAP**; S3, strategischer usable SOC (B2) und weiche Kapazitätsgewichtung (C1) sind **eigenständige** Funktions-/Spezifikationsscopes ohne notwendige Adaptive- oder High-SOC-Kopplung. S3 ist unmittelbar zu spezifizieren und als nächster freizugebender Funktionsblock vorgesehen; B2 und C1 benötigen je einen *zweck-/nutzenorientierten* Produktionsvertrag. Bei unverhältnismäßigem B2/C1-Aufwand wird Battery Care wegen Winterpriorität vorgezogen. Für jede neue policy-basierte Regelwirkung gelten nutzbarer Endzielwert und tatsächliche physische Wirkung als Wirksamkeitskriterium, kein alleiniger interner Sharewechsel. Verbindliche Freigabegrenze: kein produktiver Code allein durch diese Quellenkonsolidierung.

**Aktuelle priorisierte Roadmapsicht 18.10.2026:**

1. **Nächster Produktrelease – zwingend:** `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` beheben, alle vorhandenen Safety-/Regression-Gates; ohne beide kein Release-PASS.
2. **S3 eigenständig:** `ZEC-BL-CTRL-S3-001` – Saison-/Tagesprofile: Zweck, Runtimewirksamkeit aller vorgesehenen Keys, sichere Legacy-/Neuinstallationsmigration, zeitrichtige Kalender-/Timersemantik, UI-/Diagnosevertrag und No-Regression; vor Sourceänderung eigenständige finale Spezifikations-/Scopefreigabe.
3. **B2 eigenständig:** `ZEC-BL-CTRL-USABLE-SOC-001` – sinnvolle deterministische, kontextabhängige strategische Nutzung des diagnostisch bereits vorhandenen usable SOC, nicht pauschal Winter-only; konkrete Wirksamkeit und Geltungsgrenzen vor Coding.
4. **C1 eigenständig:** `ZEC-BL-CTRL-CAP-001` – optionale weiche Kapazitätsgewichtung `off|soft`, default `off`; übergreifenden erlaubten Aktionsraum prüfen, nicht unreflektiert auf High-SOC begrenzen; harte Invarianten bleiben erhalten.
5. **Winterpriorisiert Battery Care:** `ZEC-BL-BATCARE-001` – getrennte Zendure-Reserve-/SOC-Erhaltungsstrategie; **vorziehen**, wenn B2/C1 zeitlich unverhältnismäßig aufwendig werden. Netzladung ist gesondert freigabepflichtig und nicht implizit aktiviert.
6. **Adaptive bewusst DEFERRED:** `ZEC-BL-CTRL-ADAPTIVE-001` und `ZEC-BL-CTRL-001` – sämtliche Konzepte/Lern-/Replay-/Confidence-/Persistenzfragen und A1-Evidenz erhalten; Wiederaufnahme nur bei plausiblem Zusatznutzen und geprüftem Aktionsraum (gegebenenfalls jenseits High-SOC).
7. **Release-Dokumentationsvertrag:** `ZEC-BL-DOC-ARCH-001` – versionsgebundene aktuelle Architektur, Specs, ADR und niedrigaufwändige echte Historie im Source-`docs/`; ab nächstem Release; keine Vorbedingung für die S3-Fachspezifikation.
8. **Fast Capture Field/Evidence:** `ZEC-BL-CTRL-FASTCAP-001` Active-`FULL_IDLE` und bounded-/applicability-aware Forensik bleiben `EVIDENCE_PENDING`, sind keine Voraussetzung für getrennte S3-Konzeption.
9. **Verbleibende Frontend-/Storage-/Analyse-/Simulation-/Multi-/Release-Härtungen** verbleiben unverändert unter ihren bisherigen stabilen IDs, mit jeweiligem Implementierungs- und Feldevidenzstatus.

**Historischer Roadmap-Snapshot 23.09./25.09.2026, inzwischen im Sequencing abgelöst (Provenienz, nicht aktuelle Anweisung):**

**Roadmapstand 23.09.2026:** V17.0.1 ist real installiert und automatisiert FULL_READY feldabgenommen. V17.0.2 korrigiert ausschließlich drei real gefundene Fast-Capture-Evidenzdefekte und besitzt nach 157 Testdateien / 1169 Tests + 706 Subtests, identischem ResourceWarning-Lauf sowie statischen/Deployment-/Datenblatt-/Build-Evidence-Gates TECHNICAL BUILD PASS; finale Paket-/Fresh-extract-Gates folgen vor Veröffentlichung. `ZEC-BL-CTRL-FASTCAP-001` bleibt FIELD_PENDING, bis nach V17.0.2-Installation neue Shadow-Evidenz und anschließend ausdrücklich freigegebene begrenzte Active-Evidenz vorliegen. Desktop-Warning-Chip/Popover ist real visuell PASS; mobile Bottom-Sheet-Variante bleibt offen.

**Roadmapstand 22.09.2026 nach abgeschlossener V16.2.5-Feldentscheidung:** Das Update V16.2.4 → V16.2.5 ist real erfolgreich. Der konsolidierte automatische Feldlauf ist PASS; `controller_ready` war wegen `LIMIT_READBACK_CONVERGENCE` transient, `controller_readiness_acceptance=PASS TRANSITIONAL:LIMIT_READBACK_CONVERGENCE`. Instance Owner, Speicherstatuskarten-Geometrie, Mobile Settings, sichtbare Graph-Linienunterbrechung sowie die funktionale ein-/ausklappbare High-SOC-/Command-Warnung sind real beobachtet.

Die reale Sichtprüfung hat zwei klar isolierte Frontend-Restpunkte ergeben: (1) `ZEC-BL-GRAPH-GAP-001`: Cursor/Tooltip/Inspector müssen innerhalb bestätigter Evidence-Gaps einen ehrlichen Gap-/Empty-State statt Nearest-Sample-Werten bzw. Epoch-Nullzeit zeigen; (2) `ZEC-BL-UI-STATUS-003`: der persistente Warnhinweis soll im kompakten Zustand höhenneutral als Warning-Chip im Kartenkopf erscheinen, während Details Desktop als verankertes Popover und mobil als Bottom-Sheet/Modal außerhalb des normalen Kartenflows geöffnet werden. Der Nutzer hat am 22.09.2026 ausdrücklich entschieden, für diese zwei kleinen, bereits klar abgegrenzten UI-Härtungen **keinen separaten Hotfix-Zyklus** zu erzwingen. Sie werden im nächsten ohnehin anstehenden Release als eigenständige, regressionsgeprüfte Frontend-Subscopes mitgeführt und sind **keine Sequencing-Blocker**.

Das Sequencing-Gate ist am 22.09.2026 durch ausdrückliche Nutzerentscheidung geschlossen: **`ZEC-BL-CTRL-FASTCAP-001` wird als nächster Controllerblock umgesetzt; Fast Capture wird technisch und fachlich von `ZEC-BL-CTRL-ADAPTIVE-001` entkoppelt.** Die eingefrorene A400/R100-Spezifikation wurde gegen die reale V16.2.5-Codebasis revalidiert (`PASS_WITH_V16_2_5_INTEGRATION_DELTAS`). `controller_logic.py`, `ZendureController.py`, `command_lifecycle.py`, `config_validator.py` und `primary_storage_source.py` sind zwischen V16.0.2 und V16.2.5 byteidentisch; die notwendigen Deltas betreffen vor allem State-/Settings-/Measurement-/UI- und Feldevidenzverträge. Die revalidierte Spezifikation `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_2_5_REVALIDATED.md` ist Blockautorität. Der V17.0.0-Makro-Implementierungsscope wurde anschließend ausdrücklich freigegeben. Checkpoint A (Controllerkern/State/Differential-/Safetytests) ist fokussiert PASS mit 110 Tests + 11 Subtests; Checkpoint B (Settings/Validation, Measurement V4, Fast-Feldanalyse und V17-Feldabnahme) ist fokussiert PASS mit 114 Tests + 640 Subtests. Ein TECHNICAL BUILD PASS liegt noch nicht vor.

Adaptive bleibt vollständig erhalten, ist aber kein Vorläufer für Fast Capture. Nach Bereitstellung des Fast-Capture-Releases beginnt ein eigener Adaptive-Spezifikationsblock; reale Fast-Episoden dürfen dabei als Evidenzinput dienen. Adaptive-Controller-Sourcearbeit benötigt weiterhin Lernzustand/Persistenz/Reset, Confidence/Fallback, S3-Mapping, Capacity-Weighting-Vertrag und eigene explizite Freigabe.

Historische priorisierte Sicht vom 23.–25.09.2026 (durch Roadmapsicht 18.10.2026 hinsichtlich Adaptive/S3/B2/C1/Battery Care ersetzt):

1. **Zwingende Fixes im nächsten Produktrelease:** `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001`; Releaseblocker bis Implementierung und Regression beider Punkte.
2. **`ZEC-BL-CTRL-FASTCAP-001` – Fast Capture A400/R100:** Implementierung und allgemeine V17.0.2-Feldbasis PASS; Shadow-Gate PASS; reale Active-`NEAR_LIMIT`-Evidenz in den beobachteten Aspekten PASS. Active-`FULL_IDLE` sowie die abschließende Evidence-Tooling-Härtung bleiben EVIDENCE_PENDING.
3. **Verbindliche UI-Follow-ups im nächsten ohnehin anstehenden Release:** `ZEC-BL-GRAPH-GAP-001` Gap-aware Cursor/Tooltip/Inspector sowie `ZEC-BL-UI-STATUS-003` höhenneutraler Warning-Chip + Desktop-Popover/Mobile-Bottom-Sheet. Beide als isolierte Frontend-Deltas mit eigener Regression.
4. **`ZEC-BL-CTRL-ADAPTIVE-001` – Adaptive-Spezifikationsblock:** S3 + adaptive Strategie + weiche Kapazitätsgewichtung vollständig spezifizieren; dies darf parallel zur verbleibenden Fast-Capture-Feldevidenz erfolgen. Produktive Adaptive-Sourcearbeit bleibt separat freigabepflichtig und muss die beiden Next-Release-Fixes mitführen, falls sie den nächsten Produktrelease erzeugt.
5. **ZEC-BL-BATCARE-001 – Battery Care / Winter- und Reserve-SOC-Erhaltung** folgt gemäß bestehender Roadmap nach dem adaptiven Block; vor Implementierung ist aus dem erhaltenen Brainstorming eine explizit freigegebene Spezifikation zu erstellen.
6. **ZEC-BL-STORAGE-001 – Measurement-/SQLite-Storage-Lifecycle.** S4/S5/S6/S7/S9 gegen die aktuelle Codebasis inventarisieren und in sicheren Stufen umsetzen.
7. **ZEC-BL-ANALYSIS-HANDOFF-001 – Graph → Analyse-Service.**
8. **ZEC-BL-SIM-001 – kontrafaktische Regler-Simulation.**
9. **ZEC-BL-SCENARIO-001 – allgemeiner Szenarioeditor.**
10. **ZEC-BL-MULTI-001 – echter Multi-Zendure-Command-/Regelpfad.** Darstellung mehrerer Entities ist keine aktive Dual-Headunit-Regelung.
11. **ZEC-BL-REL-001 – repo-zentrierter/reproduzierbarer Releaseprozess / CI.**

Querschnittlich bleiben `ZEC-BL-PRIMARY-METADATA-001`, `ZEC-BL-UI-STATUS-EXPERT-001`, Diagnose-/Command-Langzeitevidenz, Lernwerkzeugabgleich und Storage-Langzeitperformance erhalten.

### 3.1 Historische S1–S9-Stufen – vollständige Reconciliation

| Stufe | historische Bedeutung | aktueller Ledgerstatus | Auflösung |
|---|---|---|---|
| S1 | Settings-Basis, UI und Legacy-Audit | CLOSED | in RC20/V12.11.x–V12.12.x produktiv umgesetzt; dauerhaft in der Closed-Historie erhalten |
| S2 | Primärspeicherintegration | CLOSED / SUPERSEDED BY V15 ARCHITECTURE | source-neutrale Primärspeicherintegration und direkte read-only Modbus-Anbindung in V15.0.0 schließen die alte S2-Kopplungslücke |
| S3 | Saison- und Tagesprofile | OPEN / SPEC_DRAFT, **jetzt eigenständiger Scope** | `ZEC-BL-CTRL-S3-001`; Adaptive-Umbrella-Anbindung vom 20.09.2026 historisch, ab 18.10.2026 in der Reihenfolge supersediert |
| S4 | SQLite-Pfad und `report_only` | OPEN / partial | `ZEC-BL-STORAGE-S4-001` |
| S5 | SQLite-Enforce | OPEN | `ZEC-BL-STORAGE-S5-001`; Bedeutung aus `conversations.json` wiederhergestellt |
| S6 | V4-Schutz, Katalog und Sicherheitsdialog | OPEN / partial | `ZEC-BL-STORAGE-S6-001` |
| S7 | V4 `compress_only` und Restore | OPEN | `ZEC-BL-STORAGE-S7-001` |
| S8 | Analyse- und Simulationspakete | PARTIAL / SPLIT | vorhandener Analysedienst ist produktiv; fehlende Graph-Übergabe `ZEC-BL-ANALYSIS-HANDOFF-001`, echte Simulation `ZEC-BL-SIM-001`, Szenarioeditor `ZEC-BL-SCENARIO-001` |
| S9 | V4-Retention Enforce | OPEN / nachgelagert | `ZEC-BL-STORAGE-S9-001` |

Damit ist keine historische S1–S9-Stufe mehr nur implizit oder unaufgelöst.

## 4. Offenes und zurückgestelltes Master-Ledger

### ZEC-BL-CTRL-ADAPTIVE-001 – historischer gemeinsamer Adaptive-Umbrella; aktueller Scope nur Adaptive (DEFERRED)

- **Aktueller Entscheid 18.10.2026:** `DEFERRED / EVIDENCE_GAP`, `implementation_state=none`; S3 und C1 **nicht** mehr verpflichtende Children bzw. technische Vorbedingungen. Der Umbrella-Zuschnitt vom 20.09.2026 und seine Detailanforderungen bleiben im folgenden Abschnitt ausdrücklich als Provenienz erhalten, sind aber als Sequencing-Anweisung supersediert. Adaptive-Wiederaufnahme soll Aktionsraum auch abseits High-SOC und tatsächlichen Zusatznutzen prüfen; 23-Tage-Analyse und A1-Brief dauerhaft referenzieren. Kein produktives Shadow-/Lern-Coding im nächsten Block.

#### Historische Umbrella-Spezifikation / Entscheidung 20.09.2026 (Sequencing supersediert)

- **Status:** SPEC_NEEDED / OPEN; Controller-Implementierung noch nicht begonnen. Nach Nutzerentscheidung vom 22.09.2026 ist Adaptive von Fast Capture entkoppelt und folgt als eigener Spezifikationsblock nach Bereitstellung des Fast-Capture-Releases.
- **Rolle:** Roadmap-/Umbrella-Eintrag für `ZEC-BL-CTRL-S3-001`, `ZEC-BL-CTRL-001` und `ZEC-BL-CTRL-CAP-001`. Die Child-IDs bleiben eigenständig erhalten und dürfen durch die Zusammenführung nicht verschwinden.
- **Entscheidung 20.09.2026:** S3 nicht separat vorab implementieren. Saisonale Faktoren und dynamische Tagesprofile sollen mit der adaptiven Lade-/SOC-/Ertragsstrategie sowie der weichen Kapazitätsgewichtung in einem konsistenten Regelmodell zusammengeführt werden, sofern die finale Lernmodell-Übergabe dies bestätigt.
- **Pflicht vor Sourceänderung:** Es existiert nach aktueller Quellenprüfung keine weitere verlorene/finale Adaptive-Spezifikation. Der nächste Adaptive-Arbeitsschritt ist daher bewusst **Spezifikation**, nicht Suche nach einem vorausgesetzten Artefakt. Neu zu erstellen sind mindestens: Mapping-Matrix vorhandene S3-Settings → aktive Nutzervorgabe / Modellinput / deterministischer Fallback / deprecated; Abdeckung von `CTRL-001` und `CTRL-CAP-001`; konkretes Optimierungsziel und Aktionsraum; Lernzustand/Persistenz/Versionierung/Reset; Inputvertrag; Confidence/Fallback; Hardwarewechsel-/Invalidierungsvertrag; Offline-/Replay-/Shadow-/Differential-Evidenz; Safety-/Hardwaregrenzen und reproduzierbare Entscheidungsprovenienz.
- **Simulation/Evidenz:** Der spätere produktive allgemeine Counterfactual-Simulator `ZEC-BL-SIM-001` bleibt ein eigener Roadmappunkt und ist nicht zwingende Vorbedingung für diesen Block. Vor produktiver Reglerwirkung sind dennoch belastbare simulationsnahe bzw. replay-/pretrainer-/shadowbasierte Nachweise auf realen Daten erforderlich.
- **Normative Grenzen:** Die bestehende Grundinvariante „aktuell vermeidbare Einspeisung vor strategischer Ladeverteilung“ bleibt erhalten. Adaptive/gelernte Logik darf harte Safety-, SOC-, Command-, Recovery-, Cross-Charge- und Hardwareschonungsregeln nicht überstimmen.
- **Versionsklasse:** erst mit finalem Runtime-Scope festlegen; ein echter neuer produktiver Lern-/Adaptionslayer ist nach `01_ZEC_PROJECT_RULES.md` als neues Entwicklungsthema zu bewerten, eine rein statische Parameternutzung gegebenenfalls anders.
- **Exit:** Child-IDs einzeln mit Implementierungs-/Evidenzstatus reconciliert; keine exponierte S3-Einstellung bleibt unbeabsichtigt wirkungslos; Lern-/Fallback-/Recovery-Verhalten und Hardware-/Konvergenzeigenschaften sind nachgewiesen.

### ZEC-BL-CTRL-S3-001 – Saison-/Tagesprofile Completion & Effectiveness

- **Status 20.10.2026:** `IMPLEMENTED / TECHNICAL_PASS / FIELD_EFFECT_PENDING`; finale Produktionsspezifikation 19.10. freigegeben, Runtime/Settings/Tests und Opt-in/Legacy-Migration in V17.1.0 real ausgeliefert. Reale HOLD-S3-Diagnose `season_requested=sma_priority`, `season_effective=legacy_parallel`, `NOT_APPLICABLE`; natürliche Harvest-Wirksamkeit noch nicht belegt. Die folgenden 18.10.-Aussagen sind **historische Ausgangsbefunde**.

- **Aktuelle Entscheidung 18.10.2026:** `OPEN / SPEC_DRAFT`, eigenständiger nächster Funktionsscope ohne Adaptive-Abhängigkeit; Zweck/Wirksamkeit, vollständige zehn S3-Settings, Legacy-Share-/Confirm-Migration, aktuelle `sma_priority`-New-Install-Default-Falle, `VAL-014` Jahreswechsel, Timergrenzen, Registry-ProductSurface, Testmatrix und transparente Nichtanwendbarkeit in `ZEC_S3_FACHLICHE_PRODUKTIONSSPEZIFIKATION_ENTWURF_20261018.md`. Der historische Child-/Sequencingtext darunter bleibt Provenienz, ist **nicht mehr aktuell**. Vor Reglercode: finale Spezifikation und explizite Scopefreigabe.


- **Historischer Status vor V17.1.0:** OPEN
- **Historische Roadmapbindung ab 20.09.2026:** Child-Scope von `ZEC-BL-CTRL-ADAPTIVE-001`; kein separater vorgelagerter S3-Release vorgesehen.
- **Historische Herkunft:** S3 `Saison- und Tagesprofile`; Settings-/RC19-Planung und spätere Completion-Audits.
- **Aktueller V16-Befund:** Registry und Validation enthalten Kalenderfenster, Tagesprofilzeiten und gestaffelte High-SOC-Entry-Confirm-Zeiten. Für repräsentative S3-Keys existiert außerhalb Registry/Validation/Tests kein Runtime-Consumer.
- **Risiko:** UI/Config kann eine Wirksamkeit suggerieren, die der reale Regler nicht vollständig besitzt.
- **Vor Umsetzung:** reale V16-Zielwert-/State-Machine-Analyse; historische harte Zeiten/Confirm-Werte gegen Zielsettings abgleichen; Zustand/Rechnung/Wirkung/Recovery; Konvergenz und Hardwareschonung.
- **Exit:** explizit nachweisen, welche S3-Settings runtimewirksam sind; Tests für Kalender über Jahreswechsel, Tagesgrenzen, Hold-/Confirm-Übergänge und No-Regression.

### ZEC-BL-STORAGE-001 – Measurement-/SQLite-Storage-Lifecycle

- **Status:** OPEN
- **Rolle:** Parent für die historischen S4/S5/S6/S7/S9-Stufen sowie Langzeitperformance und retention-aware Backfill.
- **Grundinvariante:** keine automatische Löschung/Kompression allein aufgrund vorhandener Settings. Jede destruktive Stufe benötigt Vorschau, Protection/Coverage, Restore und klare Provenienz.

#### ZEC-BL-STORAGE-S4-001 – S4 SQLite-Pfad & report_only
- **Status:** OPEN; `implementation_state=partial`.
- SQLite ist produktive Messdatenbasis; Pfad-/Writer-/Graphfunktionen existieren. Maintenance-Settings sind vorhanden, aber der historische S4-Lifecycle ist nicht als vollständig geschlossener Maintenancevertrag nachgewiesen.
- Vor S5 ist S4 gegen reale V16-Datenbankpfade, Status-Snapshot, Inventory/Long-run und Schutz gegen Controller-Blockierung abzuschließen.

#### ZEC-BL-STORAGE-S5-001 – S5 SQLite-Enforce
- **Status:** OPEN; `implementation_state=none/placeholder settings`.
- **Recoverybeleg:** OpenAI-Export definiert S5 eindeutig als `SQLite-Enforce`.
- V16 besitzt `MEASUREMENT_DB_MAINTENANCE_MODE` und Retention-Settings/Validation, aber keinen produktiven Retention-Enforcer.
- Muss Retention/Backfill, Online-Betrieb, DB-Locking, Crashsicherheit, Vacuum-/Compaction-Strategie und Restore berücksichtigen.

#### ZEC-BL-STORAGE-S6-001 – S6 V4-Schutz, Katalog & Sicherheitsdialog
- **Status:** OPEN; `implementation_state=partial`.
- Teile der Katalog-/Coverage-/Validation-Infrastruktur existieren. Vor einer Lösch-/Kompressionsstufe muss ein vollständiger, manipulations- und crashsicherer Bestandsschutz nachgewiesen werden.
- Protection muss u. a. aktive Datei, Incident-/Forensic-/Simulation-Coverage und explizite Schutzzeiträume respektieren.

#### ZEC-BL-STORAGE-S7-001 – S7 V4 `compress_only` & Restore
- **Status:** OPEN.
- Historischer Vertrag: geschlossene `.csv` streamingbasiert komprimieren, temporäres `.csv.gz.tmp`, Flush/fsync, vollständige Dekompressions-/SHA256-/gzip-CRC/EOF-Verifikation, atomisches Rename, Manifestumschaltung, Original erst ganz am Ende löschen.
- Toolchain muss `.csv` und `.csv.gz` transparent lesen: Analyse/Replay, Backfill, Import, Diagnosepakete und relevante Branchanalyse.
- Runtime-/Betriebsereignisse benötigen einen konsistenten Rotation-/gzip-Lifecycle; deren relevante Evidenz darf nicht früher verschwinden als zugehörige Measurements.

#### ZEC-BL-S8-001 – S8 Analyse- und Simulationspakete
- **Status:** OPEN; `implementation_state=partial`, historischer Sammelpunkt.
- Der reale Datenanalysedienst/Replay-Service ist produktiv vorhanden. Der historische S8-Rest wird bewusst auf drei konkrete Nachfolger aufgeteilt:
  - `ZEC-BL-ANALYSIS-HANDOFF-001` – Graph-Selection/Evidence-Handoff an Analyse;
  - `ZEC-BL-SIM-001` – kontrafaktische Regler-Simulation realer historischer Situationen;
  - `ZEC-BL-SCENARIO-001` – allgemeiner/synthetischer Szenarioeditor.
- S8 gilt erst als vollständig geschlossen, wenn diese Aufteilung fachlich abgeschlossen oder ausdrücklich anders entschieden wurde.

#### ZEC-BL-STORAGE-S9-001 – S9 V4-Retention Enforce
- **Status:** OPEN, absichtlich nachgelagert.
- Erst nach S6/S7, real verifiziertem Restore, Coverage-/Protection-Gates und expliziter Freigabe destruktiv aktivieren.
- Retention nach Alter/Gesamtgröße muss aktive/geschützte Dateien ausnehmen und fail-closed arbeiten.

#### ZEC-BL-STORAGE-BACKFILL-001 – retention-aware Backfill/Rebuild
- **Status:** OPEN; `implementation_state=partial`.
- **Normative Invariante:** Daten, die absichtlich durch Retention entfernt wurden, dürfen durch späteres Backfill nicht stillschweigend wieder permanent hergestellt werden.
- Graph Core V3 besitzt hierfür bereits Retention-Ledger/`PURGED_BY_RETENTION` und Reapply beim Rebuild. Der Vertrag muss über V4/SQLite/Graph/Restore hinweg konsistent werden.

#### ZEC-BL-STORAGE-GRAPH-001 – automatische Graph-Retention entscheiden
- **Status:** SPEC_NEEDED / DEFERRED.
- V14 implementierte Retention-Ledger-Semantik, aber ausdrücklich keine automatische Retentiondauer, keinen Scheduler und keine automatische VACUUM-Policy.
- Vor jeder Automatisierung müssen Highres-/1-Minuten-Langzeitbedarf, Speicherbudget, Coverage und Rebuildverhalten fachlich festgelegt werden.

#### ZEC-BL-STORAGE-PERF-001 – SQLite-/Storage-Langzeitverhalten
- **Status:** OPEN / observation.
- Langzeitperformance, Größenwachstum, Retention/Backfill und seltene Langläuferepisoden evidenzbasiert beobachten. Kurze Feldsnapshots sind kein Langzeitnachweis.

### ZEC-BL-ANALYSIS-HANDOFF-001 – Graph-Auswahl an bestehenden Analyse-Service

- **Status:** OPEN.
- **Produktkette:** Status → Graph-Exploration → Analyse-Handoff → bestehender Analysedienst.
- Historische Graphplanung spezifiziert die Aktion `In Analyse untersuchen`.
- Handoff soll ein reproduzierbares Untersuchungsobjekt übertragen, mindestens Zeitraum/Selection, Zeitzone, REAL-Dataset, Guided/Free-Kontext, relevante Series/Entities, historische Version/Config/Topologie, Coverage/Evidence und optional Fokuszeitpunkt.
- Der Graph entscheidet keine Kausalität; der Analysedienst bewertet nach Analyse-Regelwerk.
- Aktuell fehlt die Aktion; `replay_web.py` ist im Startpfad primär dateibasiert.

### ZEC-BL-SIM-001 – kontrafaktische Regler-Simulation auf realen Daten

- **Status:** SPEC_NEEDED / OPEN.
- **Frage:** „Was wäre in genau dieser real stattgefundenen Situation passiert, wenn andere Regelparameter bzw. eine andere freigegebene Reglerlogik gegolten hätten?“
- Muss reale Eingangsdaten, damalige Config/Topologie, Timer/Hysterese/Latches und bekannte/nicht beobachtbare Gerätezustände transparent behandeln.
- Deterministische Ergebnisse und approximierte Annahmen müssen getrennt markiert werden.
- Zielintegration: Reality vs Simulation A/B im Graphen vergleichbar; keine Simulation darf als reale Evidenz ausgegeben werden.
- Historischer Alias: S8 `Analyse- und Simulationspakete`; Analyseanteil existiert heute, echte Counterfactual-Simulation nicht.

### ZEC-BL-SCENARIO-001 – allgemeiner Szenarioeditor

- **Status:** DEFERRED / SPEC_NEEDED.
- Synthetische frei definierte Eingangssituationen sind von `SIM-001` zu trennen.
- Erst sinnvoll, wenn Simulationskern und Parametrisierung belastbar definiert sind.


### ZEC-BL-CTRL-FASTCAP-001 – Fast Capture A400/R100

- **Status:** IN_PROGRESS / EVIDENCE_PENDING; `implementation_state=implemented`; `technical_state=TECHNICAL_BUILD_PASS`; `field_state=SHADOW_PASS_ACTIVE_NEAR_LIMIT_PASS_FULL_IDLE_PENDING`; Releasebasis `V17.0.2 / v17.0.2-20260923`.
- **Provenienz:** Pretrainer V0.5 -> V0.6.1, Freeze-Spezifikation vom 19.09.2026, V16.2.5-Revalidierung vom 22.09.2026 und reale V17.0.2-Feldevidenz vom 23.–25.09.2026. Aktive Blockautorität: `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_2_5_REVALIDATED.md`.
- **Scope:** Fast-Capture-Overlay ausschließlich für `FULL_IDLE` und `NEAR_LIMIT`; `RESERVE_UNKNOWN` bleibt im normalen Baseline-Regelpfad. Produktionskandidat A400/R100. Strategische Baseline `B` und kurzfristiger Fast-Capture-Overlay `O` sind strikt getrennte Schichten.
- **Release-/Allgemeinfeldbasis:** V17.0.2 real installiert; allgemeiner V17-Feldlauf PASS / FULL_READY. `controller_logic.py` SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031`.
- **Shadow-Evidenz:** neuer V17.0.2-V4-Pfad real verwertbar. Ein natürlicher Shadow-Lauf mit zwei Episoden ist `PASS / SHADOW_ONLY`; ein zweiter Lauf ohne Episode korrekt `NOT_EVALUABLE`. Der definierte Shadow-Gate ist damit PASS.
- **Active-Evidenz:** begrenzter Active-Rollout wurde freigegeben. Ein erster unbeaufsichtigter Lauf war wegen fehlender natürlicher Episode für Fast Capture `NOT_EVALUABLE`; ein externer Watchdog beendete ihn aufgrund eines inzwischen als False Positive identifizierten `TRANSITIONAL:LIMIT_READBACK_CONVERGENCE` und stellte `shadow` korrekt wieder her. Spätere reale Active-Daten enthalten 23.794 Active-Mode-Zeilen, 501 Zeilen mit positivem Overlay, 20 erkannte Fast-Capture-Episoden und max. Overlay 1.642 W. Für frische `NEAR_LIMIT`-Episoden liegen reale Exportreduktion, Command-Tracking, Import-Guard/Recovery und Cross-Charge-Evidenz ohne bestätigten Command-Mismatch vor.
- **Noch offen:** eine belastbare Active-`FULL_IDLE`-Episode. Fehlende natürliche Episode bleibt `NOT_EVALUABLE`, niemals synthetischer PASS.
- **Evidence-Tooling-Fund 25.09.2026:** Analyzer-Hotfix2 meldet bei langen gemischten Active-Zeitfenstern `PRIMARY_RESERVE_MISMATCH` auch in Zyklen, in denen die Fast-Capture-Rechnung wegen Night/SOC/Cross-Charge/anderen Blockern nicht anwendbar ist; Calculation-Prüfungen müssen applicability-aware werden. Zusätzlich materialisiert der Analyzer große CSVs aktuell vollständig in RAM und ist deshalb auf dem produktiven Pi für lange Historien ungeeignet. Releaseintegrierte Langzeitanalyse muss streaming/bounded-memory arbeiten oder ausschließlich auf vorher begrenzten Extrakten laufen.
- **Feldevidenzvertrag:** Zustand, Rechnung, physikalische Wirkung und Recovery getrennt. Active muss reale Exportreduktion bzw. transparent nicht bewertbare Episoden, Import-Guard/Recovery, Command-Readback/Effect, Cross-Charge und Hardwareschonung episodespezifisch auswerten.
- **Sequenzgrenze:** Adaptive-Spezifikation darf parallel zur verbleibenden Fast-Capture-Feldevidenz fortgeführt werden. Adaptive-Sourcearbeit bleibt separat freigabepflichtig und darf Fast Capture nicht stillschweigend verändern.
- **Exit:** Active-`FULL_IDLE` ausreichend beobachtet oder transparent `NOT_EVALUABLE` bei klar dokumentiertem Beobachtungsfenster; Analyzer-Anwendbarkeit und ressourcensichere Langzeitanalyse korrigiert/regressionsgeprüft; Safety, Command-Effect und Hardware-Schonung separat belegt.

### ZEC-BL-PRIMARY-SMA-FLOOR-001 – Sunny-Island Entladeuntergrenze als Capability

- **Status:** CLOSED; `implementation_state=implemented`, `field_state=REAL_FIELD_PASS` in V16.1.0.
- **Reale Vorimplementierungs-Evidenz:** SMA Register `31009` (`Lower discharge limit for self-consumption range in %`, U32/FIX0/RO) lieferte am realen Sunny Island 19 %; FC03/FC04 identisch.
- **V16.1.0 Block A:** SMA-template-spezifische, read-only Capability `current_discharge_floor_soc`; getrennte Freshness/Validity/Invalidierung; diagnostischer normalisierter `primary_usable_soc_percent`; API/Status/Readiness/Connection-Test/Measurement-V4-Evidenz.
- **Safety-Grenze:** keine Reglerwirkung; `controller_logic.py` bleibt byteidentisch zu V16.0.2. Andere Primärspeicherprofile erhalten diese Capability nicht automatisch.
- **Settings-Vertrag:** kein editierbarer Floor, kein Override, kein On/Off-Schalter, keine ZEC-Saisonkurve; generische UI-/Help-Bezeichnungen werden auf „Primärspeicher“ neutralisiert; explizite Anzeigenamen bleiben erhalten.
- **Reale Feldabnahme 20.09.2026:** Update V16.0.2 → V16.1.0 erfolgreich; Capability auf realem `modbus_template`/Sunny Island `supported=true`, `fresh=true`, `valid=true`, Floor `19.0 %`; `primary_usable_soc_percent` real vorhanden/plausibel; Feldtool-Gate `primary_storage_sma_discharge_floor_capability=PASS`.
- **Abgrenzung der Feldabnahme:** globales `/ready` blieb während der Abnahme wegen eines bestehenden `INPUT_LIMIT`-/`ACTIVE_ACCEPTANCE_LIMITED`-Zustands `false`; dies ist kein Block-A-Pfad und wird separat unter `ZEC-BL-DIAG-FIELD-001` dokumentiert.

### ZEC-BL-CTRL-USABLE-SOC-001 – Block B: strategische usable-SOC-Integration

- **Aktueller Entscheid 18.10.2026:** `SPEC_NEEDED / OPEN` als unabhängiger deterministischer B2-Scope; diagnostischer usable SOC bleibt real implementiert, strategische Runtime-Wirkung **nicht**. Ganzjährige Anwendungsfälle untersuchen, Winter ist nur ein möglicher Kontext. Kein globaler RAW-SOC-Ersatz, kein aus Discharge-Floor erfundener Charge-Headroom, keine implizite Zendure-Netzladung. Die ältere Vorgabe „mit Adaptive zusammenführen“ gilt nur als historische Provenienz und ist im Sequencing abgelöst. Zweck, Nutzen, Kontext, Policy/Arbitration, Fallback und reale Wirksamkeit vor Coding klären.


- **Status:** DEFERRED / SPEC_NEEDED; `implementation_state=none`.
- **Provenienz:** Folgeblock der SMA-Capability-Entscheidung vom 19.09.2026.
- **Ziel:** den aus realem Roh-SOC und aktueller geräteseitiger Entladeuntergrenze abgeleiteten nutzbaren Primär-SOC gezielt in Winter-/Schwachertragsstrategie verwenden.
- **Abgrenzung:** kein globaler Ersatz des Roh-SOC. FULL/IDLE, High-SOC-/Taper-Erkennung, Lade-Headroom bis 100 %, Fast Capture sowie physische Safety-/Limitentscheidungen bleiben am realen Roh-SOC bzw. Leistungszustand.
- **Voraussetzung:** mit Adaptive-/Replay-Ergebnissen zusammenführen; Zustand, Rechnung, physikalische Wirkung, Konvergenz, Recovery und Hardwareschonung vor Reglerfreigabe separat belegen.

### ZEC-BL-CTRL-CAP-001 – echte weiche Kapazitätsgewichtung

- **Aktueller Entscheid 18.10.2026:** `SPEC_NEEDED / OPEN`, eigenständig von Adaptive/High-SOC und B2; explizites `off|soft`, Default `off` als Zielvertrag (Ist derzeit `diagnostic` ohne Sollwertwirkung); keine Nenn-kWh-Quotenautomatik. Nur bei validiertem Lade-Headroom, unabhängiger Aufnahmefähigkeit, tatsächlicher Allokationsfreiheit und nachweisbarer Endzielwertwirkung. Physische Export-/Safety-/Hardwaregrenzen haben Vorrang; Datenausfall -> neutral. Historischer Child-/Pretrainer-Text darunter als Provenienz erhalten, Sequencing supersediert.


- **Status:** SPEC_NEEDED.
- **Roadmapbindung ab 20.09.2026:** Child-Scope von `ZEC-BL-CTRL-ADAPTIVE-001`; die laufende Lernmodell-/Pretrainer-Arbeit ist primärer Spezifikationsinput.
- `HARVEST_CAPACITY_WEIGHTING_MODE` ist historisch bewusst diagnostisch geblieben; keine echte Reglerwirkung vortäuschen.
- Eine neue weiche Gewichtung ist eine Reglerstrategie. Vor produktiver Wirkung ist sie mit historischen Produktivdaten über belastbare Offline-/Replay-/Pretrainer-/Shadow- bzw. simulationsnahe Evidenz zu prüfen; der spätere allgemeine Produktiv-Simulator `ZEC-BL-SIM-001` ist dafür keine zwingende Vorbedingung. Danach Differential-/Konvergenz-/Hardwareschonungsbewertung und explizite Freigabe.

### ZEC-BL-CTRL-001 – ertrags-/SOC-bewusste Ladeverteilung weiterentwickeln

- **Aktueller Entscheid 18.10.2026:** `DEFERRED / EVIDENCE_GAP` als lernender Teil unter der erhaltenen Adaptive-Historie. 23-Tage-A1-Evidenz belegt begrenzte Wirksamkeit des bestehenden High-SOC-Share-Gates, jedoch keine bewiesene Überlegenheit einer alternativen Regelung; bei Wiedervorlage Architektur jenseits High-SOC und echte Reglerstellbarkeit kritisch prüfen. Kein Coding bis erneute Nutzen-/Scopeentscheidung.


- **Status:** OPEN.
- **Roadmapbindung ab 20.09.2026:** Child-Scope von `ZEC-BL-CTRL-ADAPTIVE-001`; nicht mehr als separater späterer Block hinter `SIM-001` geplant.
- Die Grundinvariante „aktuell vermeidbare Einspeisung vor strategischer Ladeverteilung“ ist bereits produktiv implementiert und darf nicht neu erfunden werden.
- Erweiterungsraum: adaptive/lernende Ladeannahme-/Taper-Kennlinie, batteriespezifische Anpassung, erweiterte SOC-/Ertragsstrategie.
- Vor produktiver Reglerwirkung: Lernzustand/Persistenz/Reset, Confidence/Fallback, belastbare Offline-/Replay-/Pretrainer-/Shadow-/Differential-Evidenz, Konvergenz/Oszillation, Zustand/Rechnung/Wirkung/Recovery und Hardwarebelastung.

### ZEC-BL-BATCARE-001 – Battery Care / Winter- und Reserve-SOC-Erhaltung

- **Aktuelle Winterpriorität 18.10.2026:** `SPEC_NEEDED`; nach S3 möglichst zeitnah, bei übergroßem B2/C1-Aufwand **vorziehen** statt komplexe Allokationsscopes vor Winter zu erzwingen. Primärer zu prüfender Zweck: Zendure in langen Schwachertragsphasen nicht unnötig auf sehr niedrigem SOC halten; reale Nutzerbeobachtung, dass bei ca. 9 % keine autonome Nachladung beobachtet wurde, ist keine Garantie über sämtliche BMS-Modi. Saison-Policy, PV-Vorrang, explizit genehmigte optionale Netzladung, Episode, Trigger/Ziel-SOC, Hysterese, Cross-Charge-Verbot, Hardware- und Recoveryvertrag vor Sourcearbeit spezifizieren. Keine Netzladefreigabe aus B2 oder C1 ableiten. Die historische „nach Adaptive“-Bindung unten ist durch diese Entscheidung hinsichtlich Reihenfolge supersediert.


- **Status:** SPEC_NEEDED.
- **Roadmappriorität ab 20.09.2026:** unmittelbar nach `ZEC-BL-CTRL-ADAPTIVE-001`, ausdrücklich wegen der zeitnahen Winterrelevanz.
- **Wichtig:** Es existiert keine freigegebene Battery-Care-Spezifikation. Der Chat vom 11.08.2026 wird als **Brainstorming-Provenienz** erhalten, nicht als normative Entscheidung.
- Recoverter Brainstorming-Input, ausdrücklich neu zu prüfen:
  - opt-in / default-off als Idee;
  - kalendergebundene Wirksamkeit über Jahreswechsel;
  - Trigger-SOC → Ziel-SOC als echte Episode/Hysterese statt Nachregeln am Ziel;
  - mögliche Policy-/Episode-Architektur statt komplett neuem gleichrangigem Hauptmodus;
  - Safety, MIN/MAX, Command-Guards/Recovery und Cross-Charge bleiben übergeordnet;
  - bei aktiver Episode und temporärer Ladesperre eher HOLD als unbeabsichtigtes Weiterentladen;
  - offene Grundsatzfrage, ob kontrollierte Netzladung für Reserveerhaltung zulässig sein soll; niemals SMA→Zendure-Cross-Charge;
  - eigener Battery-Care-Leistungscap als mögliche Hardwareschonungsoption;
  - Restart benötigt bei echter Hysterese möglicherweise restartfeste Episode-Provenienz, die selbst niemals ein Kommando autorisiert;
  - Leap-Day-/Kalendersemantik, SOC-Freshness, Exit-Neutralisierung, Events/Measurement/Settings und No-Regression sind zu spezifizieren.
- Beispielwerte aus dem Brainstorming (z. B. 12/20 %) sind **keine allgemeinen Softwaredefaults**.

### ZEC-BL-BATTERY-SOH-001 – diagnostische reale Kapazitäts-/Alterungserkennung (NEU 18.10.2026)

- **Status:** `DEFERRED / SPEC_NEEDED`; `implementation_state=none`; eigenständige Diagnostik, **nicht** B2/C1/Adaptive oder Battery Care automatisch integriert.
- **Provenienz:** Herbst-/Adaptive-Fachgespräch vom 18.10.2026; bisheriger Hinweis auf Ladeannahme-/Taperlernen unter `ZEC-BL-CTRL-001` ersetzt keine reale Energie-/SOH-Kapazitätsbestimmung.
- **Zweck:** langfristig erkennen, ob die unter definierten und vergleichbaren Bedingungen messbare effektive Batteriekapazität abnimmt. Messpunkt (AC/Batterieseite), Wirkungsgrad, BMS-SOC-Korrekturen, Temperatur, Anfangs-/End-SOC, Mindesthub, Metadatenqualität und Unsicherheit sind vor jeder quantitativen SOH-Aussage zu klären.
- **Nichtziele:** kein unmittelbares Ändern von SOC-, Batterie-, Lade-/Entlade- oder Commandgrenzen; keine Alterungsdiagnose aus bloßer Ladeleistungs-/Taperabweichung; kein Automatik-Ersatz der Nennkapazität in C1. Erst Datentauglichkeit prüfen; bei unzureichender Evidenz `NOT_EVALUABLE`.

### ZEC-BL-MULTI-001 – echter Multi-Zendure-Command-/Regelpfad

- **Status:** DEFERRED / SPEC_NEEDED.
- Graph/Entitymodell kann mehrere Zendures darstellen. Der produktive Commandpfad ist weiterhin auf eine aktive Controller-/`DEVICE_ID`-Instanz ausgelegt.
- Echte Zielallokation, Priorität, Safety, Readback, Wirkung, Ausfall einer Unit und gemeinsame Netzkonvergenz müssen separat spezifiziert werden.

### ZEC-BL-DOC-ARCH-001 – versionsgebundene Architektur-/Historien-Dokumentation in `docs/` (NEU 19.10.2026)

- **Status 20.10.2026:** `CLOSED / V17_1_0_DOC_GATE_PASS` für erstmalige technische Umsetzung; dauerhafte Releasepflicht weiterhin aktiv. Ursprünglich `OPEN / DOC_POLICY_DEFINED` zum Beschluss 19.10. (damals noch nicht im V17.0.2-Release).
- **Zweck:** Der Releasestand muss neben ausführbarem Code die fachliche Absicht, die tatsächlich implementierten Daten-/Regler-/Safety-/Commandpfade, Designentscheidungen und deren Historie ohne Abhängigkeit von einem Chat nachvollziehbar dokumentieren.
- **Releasepflicht ab nächstem Entwicklungs-/Produktrelease:** `docs/INDEX.md`, strukturierte `docs/architecture/`, `docs/specifications/`, `docs/decisions/`, `docs/history/` als schlanke, versions-/statusgetrennte Struktur; bei relevanten Sourceänderungen betroffene As-built-/Spec-/ADR-Dokumente gemeinsam aktualisieren. Source-/Manifest-/Hash-/Fresh-extract-Prüfung und `DOC_ARCH_HISTORY_GATE` gemäß `01` § 6b und `06` § 13 einführen. Bereits veröffentlichte V17.0.2-Dateien bleiben byteidentisch.
- **Historie ausdrücklich erwünscht und pragmatisch:** Existierende historische Original-Spezifikationen/Entscheidungen bevorzugt im Original erhalten und indizieren, zuerst `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_0_2.md`. Die im Ledger belegte V16.2.5-Revalidierungsfassung fehlt als zugängliches Original (`MISSING_ORIGINAL`), darf nicht fingiert werden. Aus realem V17.0.2-Code abgeleitete aktuelle Architektur erhält eigenen `AS_BUILT`-Status. Ältere Entscheidungen mit belegter Provenienz gern ergänzen, ohne ein vollständiges retrospektives Großprojekt zu erzwingen.
- **Gates/No-Drop:** historisch nicht auffindbares Original allein kein Releaseblocker; fehlende/inkorrekte *aktuelle* As-built-Dokumentation einer relevanten Änderung oder falsche Releasebehauptung schon. Keine neue Roadmapautorität in `docs`, `docs/ZEC_Master_Backlog.md` bleibt Snapshot. Historische Quellen nicht vor bestandenem `BACKLOG_NO_DROP_GATE` entfernen.
- **Abgrenzung:** keine aktuell genehmigte Controller-/Installer-Sourceänderung, keine eigenständige Versionsvergabe durch die Quellenpflege; Umsetzung im nächsten ohnehin anstehenden Entwicklungs-/Releaseblock statt Verzögerung von S3/B2/C1/Battery Care.

### ZEC-BL-REL-001 – repo-zentrierter/reproduzierbarer Releaseprozess

- **Status:** DEFERRED.
- Historisches Ziel: repo-zentrierter Build, reproduzierbares ZIP, weniger manuelles Kopieren, perspektivisch GitHub/GitHub Actions.
- V16.2.0 enthält weiterhin keine `.github`-Automation. Umsetzung darf bestehende Fresh-extract-, Manifest-, Hash-, Test-, Datenblatt- und Feldgates nicht abschwächen.

### ZEC-BL-LEARN-001 – Lernwerkzeug V4.2.7 auf V16-Registry/Defaults abgleichen

- **Status:** OPEN.
- Strukturintegrität des XLSX ist belegt; Dashboard enthält noch historischen „Startwert V12.8.10“.
- Werte/Bezeichnungen gegen reale V16-Registry und `config.example.json` prüfen; keine anlagenspezifischen Werte als allgemeine Defaults übernehmen.

### ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001 – Nachtfenster + Zendure-MIN_SOC darf Grid/AUTO nicht blindlegen

- **Status 20.10.2026:** `FIX_IMPLEMENTED / TECHNICAL_PASS / NATURAL_NIGHT_MIN_SOC_EXPORT_FIELD_PENDING`; `implementation_state=implemented`, V17.1.0-Fix und deterministische Regressionsfälle PASS. Historische V17.0.2-Evidenz 25.09. bleibt, der damals geltende `RELEASE_BLOCKER_NEXT_RELEASE` ist technisch erfüllt.
- **Realer Fund:** Im aktiven Nachtfenster erreicht Zendure den globalen `MIN_SOC`. `pause_fixed_night_discharge_for_reserve_soc()` ruft `soc_limit_hold(... MIN_SOC ...)` auf und liefert `False`; `run_once()` kehrt dadurch vor `refresh_grid_power_for_display()`/`read_grid_power()` und vor der normalen AUTO-Regelung zurück. Der allgemeine Grid-State altert anschließend bis `stale`. Im beobachteten Fall fror der letzte Wert ab ca. 01:24 ein und wurde im ersten Zyklus nach dem konfigurierten Nachtende 05:30 wieder aktualisiert.
- **Control-Impact:** Der Defekt ist nicht nur UI-/Diagnosekosmetik. Entsteht bei `night_active && Zendure_SOC <= MIN_SOC` realer PV-Überschuss/Export, wird dieser im betroffenen Pfad nicht neu eingelesen und kann daher keine Zendure-Ladung auslösen. Das verletzt im betroffenen Zeitfenster die Invariante „aktuell vermeidbare Einspeisung vor strategischer Ladeverteilung“.
- **Abgrenzung:** `MIN_SOC` bleibt harte Entladegrenze und darf keine weitere Zendure-Entladung erlauben; Laden bei realem Export muss dagegen weiterhin möglich sein, sofern MAX_SOC, Command-, Cross-Charge- und sonstige Safety-Grenzen es erlauben. Der Primärspeicher-SOC ist kein Trigger dieses Fehlers. Fast Capture ist nicht ursächlich; im realen Incident war Fast-Capture-Wirkung 0 W.
- **Zielkorrektur:** Nacht-MIN_SOC darf die Entladung neutralisieren, aber nicht Grid-Telemetrie und exportseitige AUTO-Ladereaktion blindlegen. Der genaue Implementierungsweg ist im nächsten Release-Scope source-seitig zu bestimmen; eine reine Display-Refresh-Korrektur reicht **nicht**, wenn der AUTO-Ladepfad weiterhin vorzeitig verlassen wird.
- **Pflichttests:** mindestens (1) Nacht+MIN_SOC+Netzbezug => keine Entladung/korrekte Neutralisierung; (2) Nacht+MIN_SOC+PV-Export => frische Grid-Evidenz und zulässige Ladeentscheidung; (3) Wechsel Import↔Export bei MIN_SOC; (4) Nachtende 05:30/konfiguriertes Ende ohne Latch; (5) MAX_SOC-/Cross-Charge-/Command-Guard-No-Regression; (6) Status/Measurement/Reason bleiben aktuell und konsistent.
- **Exit:** Sourcefix + fokussierte Regression + vollständige Releasegates; reale Feldbeobachtung bei passender Low-SOC-/Nachtkonstellation oder ausdrücklich dokumentiertes `NOT_EVALUABLE`, falls die natürliche physische Exportepisode vor Release nicht entsteht. Technische Regression darf dadurch nicht entfallen.

### ZEC-BL-GRID-SMA-OBIS-001 – SMA-Speedwire-/OBIS-Parser strukturell härten

- **Status 20.10.2026:** `FIX_IMPLEMENTED / TECHNICAL_PASS / NATURAL_REOCCURRENCE_MONITORING`; `implementation_state=implemented`, V17.1.0 strukturierter Speedwire-/OBIS-Parser mit Negativtests PASS, real frische SMA-Grid-Werte im HOLD. Historischer V17.0.2-Fund bleibt dokumentiert; seine exakte Extremwertursache nicht rückwirkend als bewiesen behaupten.
- **Realer Fund:** Wiederholt tritt exakt `-1.730.098,8 W` als dekodierter Netzleistungsrohwert auf. `GRID_POWER_PLAUSIBILITY_MAX_ABS_W=30000` verwirft ihn korrekt, sodass der Extremwert nicht in AUTO-Regelung oder Glättung eingeht.
- **Bestätigter Sourcefehler:** V17.0.2 sucht die Gesamtwirkleistungs-OBIS-Kennungen `00 01 04 00` und `00 02 04 00` per globaler Bytefolgensuche im vollständigen UDP-Datagramm und liest die folgenden vier Bytes als Wert. Damit werden Speedwire-/Protokollstruktur, deklarierte Länge, echte OBIS-Recordgrenzen und 4-/8-Byte-Werttypen nicht ausreichend als Parservertrag erzwungen. Eine OBIS-ähnliche Bytefolge innerhalb eines anderen Payloadwertes kann dadurch prinzipiell fehlinterpretiert werden.
- **Topologie:** Im realen Netz existieren zwei SMA-Messgeräte: der für ZEC ausgewählte Sunny Home Manager mit integriertem Hausanschlusspunktzähler sowie ein zweiter Energy Meter für die drei Zaun-Wechselrichter. Die Seriennummernselektion bleibt erforderlich, ersetzt aber keine strukturelle Frame-/OBIS-Validierung.
- **Entscheidung 25.09.2026:** Ein 72-h-Raw-Frame-Auditor ist **keine Vorbedingung** für den Fix. Die Parserdefizienz ist unabhängig vom exakten historischen Raw-Frame reparaturwürdig. Ob genau der wiederkehrende Wert `-1.730.098,8 W` ausschließlich aus dieser Defektklasse stammt, bleibt bis zur Nachbeobachtung eine offene Kausalitätsdetailfrage.
- **Zielkorrektur:** SMA-/Speedwire-Frame und Protokolltyp strukturell validieren; Geräteidentität sauber lesen; OBIS-Datensätze sequentiell an Recordgrenzen dekodieren; 4-/8-Byte-Werttypen und Längen respektieren; unbekannte zusätzliche OBIS-Felder robust überspringen; verkürzte, inkonsistente oder fremde Frames verwerfen; konfigurierte Seriennummernselektion beibehalten; 30-kW-Plausibilitätsfilter als zweite Schutzschicht unverändert erhalten.
- **Pflichttests:** (1) bekannte valide Home-Manager-Telegramme liefern identische korrekte Leistung; (2) wechselnde OBIS-Reihenfolge/zusätzliche Felder; (3) `00 01 04 00` bzw. `00 02 04 00` innerhalb eines 8-Byte-Payloads erzeugt keinen False Match; (4) falsche Protokoll-ID => Reject; (5) Truncation/Längenfehler => Reject; (6) beide realen SMA-Seriennummern => nur ausgewählter Home Manager aktualisiert Grid Power; (7) Sentinel-/ungültige Werte; (8) Plausibilitätsfilter bleibt wirksam.
- **Feldevidenz nach Fix:** normaler SMA-Netzleistungspfad muss stabil bleiben; bestehende Logs auf erneutes Auftreten des Extremwertes beobachten. Verschwindet er über ein repräsentatives Betriebsfenster, stützt dies die konkrete Root-Cause-Zuordnung. Tritt er erneut auf, wird erst dann ein gezielter Raw-Frame-Capture notwendig.
- **Exit:** strukturierter Parser implementiert, fokussierte + vollständige Regression PASS, reale normale Netzleistungsmessung bestätigt; kein nächster Produktrelease mit unverändertem globalem Byte-Search-Parser.

### ZEC-BL-DIAG-001 – aktuelle Fehler vs. historisches `last_error`

- **Status:** OPEN / observation-hardening.
- Diagnosesemantik weiter schärfen, damit historische Fehler nicht als aktueller aktiver Incident erscheinen.
- **Realfund 25.09.2026:** Während `NIGHT_RESERVE_STOP`/`SOC_LIMIT_HOLD:MIN_SOC` und gleichzeitig stale Grid-Telemetrie zeigte die Statusoberfläche `HOLD – Grund: Netzleistung nahe 0 W`. Reason-Auflösung muss aktuelle operative Limiter-/Target-Final-Gründe gegenüber generischem/sticky HOLD-Kontext korrekt priorisieren und darf einen stale Netzleistungswert nicht als aktuellen fachlichen HOLD-Grund suggerieren.

### ZEC-BL-CMD-OBS-001 – Command-/Readback-Feldevidenz

- **Status:** OPEN / evidence.
- Command Effect, Readback, Resync und physikalische Wirkung weiter mit realen Episoden belegen. Zeitliche Reihenfolge allein ist kein Kausalitätsnachweis.

### ZEC-EV-OFFGRID-001 – kontrollierter realer Offgrid-Feldtest

- **Status:** EVIDENCE_PENDING / DEFERRED.
- Die Power-Semantik trennt `gridOffPower` von Hausnetz-/Packfluss und ZEC verändert die Offgrid-Konfiguration nicht.
- Historisch ausdrücklich offen: ungefährlichen Verbraucher am Offgrid-Ausgang real testen und belegen, dass Offgrid-Last nicht als Hausnetzentladung, Cross-Charge oder fehlgeschlagene Neutralisierung interpretiert wird.

### ZEC-BL-PRIMARY-METADATA-001 – technische Primärspeicher-Metadaten automatisch aus Gerät/Template

- **Status:** SPEC_NEEDED.
- **Provenienz:** Status-GUI-/V16.2.0-Scope vom 20.09.2026.
- **Ziel:** technische Eigenschaften wie nutzbare/nominale Kapazität, maximale Ladeleistung und maximale Entladeleistung sollen – soweit das konkrete Gerät sie belastbar bereitstellt – perspektivisch über Geräteprofile/Templates automatisch erfasst werden, statt dauerhaft manuell gepflegt werden zu müssen.
- **Vor Umsetzung zu entscheiden:** Source-vs.-manueller Fallback/Override-Vertrag, Freshness/Validity, Gerätewechsel/Invalidierung, Einheiten und Verhalten bei nur teilweise verfügbaren Capabilities.
- **Abgrenzung:** V16.2.0 implementiert ausschließlich optionale manuelle Status-/Diagnose-Fallbackwerte; daraus entsteht keine Reglerwirkung.

### ZEC-BL-DEP-002 – persistente Installationsreports

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.4 / v16.2.4-20260921`.
- **Umsetzung V16.2.4:** Der Installer schreibt den maschinenlesbaren Installationsreport atomar und timestamped persistent unter `/home/pi/Downloads`; `/tmp/zec_v16_2_4_install_report.json` bleibt ausschließlich Kompatibilitätskopie.
- **Feldtool-Vertrag:** Ein explizites `--install-report` gewinnt immer. Ohne expliziten Pfad wird der neueste persistente releasespezifische Report bevorzugt; nur wenn keiner vorhanden ist, darf die definierte `/tmp`-Kompatibilitätskopie verwendet werden.
- **Integrität:** Reportformat, Release-/Buildidentität und Installationsmodus werden fail-closed validiert. Beim Update wird die im Report referenzierte reale Rollback-Datei weiterhin über Pfad, Größe und SHA256 verifiziert.
- **Abgrenzung:** keine Änderung an Rollback-, Supportcapture-, Installationszustands-, Regler-, Command-, Safety- oder Recoverysemantik.
- **Technischer Exit V16.2.4:** vollständige Regression `1123 Tests + 698 Subtests PASS` über 150 Testdateien; identischer Lauf mit `ResourceWarning=error`; Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Artefakt-Transaktion, Datenblatt-, Build-Evidence-, Manifest-/Hygiene- und Fresh-extract-Gates PASS.
- **Realer Exit 22.09.2026:** Update V16.2.3 → V16.2.4 erfolgreich; persistenter Report `/home/pi/Downloads/zec_v16_2_4_install_report_20260921_232843.json` real gefunden und vom Feldtool ohne explizites `--install-report` bevorzugt; Report-SHA256 `778b0716fba2c79ff6f77f26e11b818fb08cee96b9e0630f7cbf8624280b5260`; reale Rollback-Datei SHA256 `8e541acdc71fffb4e97bb9ec0428eab575eba526eeacf4d1f32c28b0fbf77150`; `rollback_backup_integrity=RELEASE_BACKUP_EXACT`; Gesamtfeldlauf PASS. Damit CLOSED / REAL_FIELD_PASS.

### ZEC-BL-DEP-003 – V16.2.1 Manifest-/Deploymentvertrag und einmalige Fehlerbehandlung

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; technischer Fix ab V16.2.2, realer Exit mit `V16.2.3 / v16.2.3-20260921`.
- **Realer Fund 21.09.2026:** V16.2.1 bestand Package-/Fresh-Extract-Gates, enthielt aber fünf `.pytest_cache`-Dateien im Source-Manifest. Der Installer schließt `.pytest_cache/` beim Update/Fresh-Install bewusst aus und prüfte anschließend das unveränderte vollständige Manifest im Ziel; dadurch brach der reale Updatepfad V16.2.0 → V16.2.1 nach Backup und Copy mit fehlenden Manifestdateien ab.
- **Rollback-Evidenz:** automatischer Update-Rollback stellte V16.2.0 wieder her; `/health` meldete V16.2.0 alive=true, `/ready` true und keine failed_checks. V16.2.1 erhält daher keinen Real-Field-PASS.
- **Zweiter bestätigter Befund:** `set -E` vererbt den `ERR`-Trap in Subshells. Ein Fehler im Manifest-Subshell konnte Supportcapture/Rollback dort und anschließend nochmals im Hauptprozess auslösen; dies erklärt die zwei Diagnosepakete des realen Fehlversuchs.
- **V16.2.2-Scope:** volatile Cache-/Bytecode-/Runtime-DB-Artefakte fail-closed aus Release-Tree und aktuellem Manifest ausschließen; gemeinsamer Manifestverifier für Paket und Ziel; Paket-Preflight prüft Release-Hygiene vor jeder Mutation; reales rsync-Update und Fresh-Install werden gegen denselben Manifestvertrag regressionsgetestet; nur der Haupt-Shellprozess darf Supportcapture/Rollback finalisieren.
- **Abgrenzung:** keine UI-, Regler-, Command-, Safety- oder Recoverysemantikänderung; `controller_logic.py` muss byteidentisch bleiben. `ZEC-BL-DEP-002` wird in diesem Hotfix nicht stillschweigend mit umgesetzt.
- **Pre-Freeze-Evidenz:** vollständige Regression `1106 Tests + 698 Subtests PASS`, identischer Lauf mit `ResourceWarning=error`, Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Rollback, Datenblatt und reale rsync/Manifest-Regression für Update/Fresh PASS. Das neue Hygiene-Gate erkannte ein während QA entstandenes Runtime-SQLite-Artefakt fail-closed; dieses wurde vor Manifest/Paketbau entfernt.
- **Technical Exit:** paketierter Fresh-Extract ohne volatile Artefakte, Manifest/Hygiene, vollständige Regression `1106 + 698`, identischer ResourceWarning-Lauf, statische Gates, Deployment-Harness und Root-Rollback PASS.
- **Realer Exit 21.09.2026:** V16.2.3-Preflight und Update V16.2.0 → V16.2.3 erfolgreich; konsolidierte Feldabnahme insgesamt PASS. Exaktes Rollback-Backup SHA256 `d860ad8d3af8cdd31d6e568357509f6320258c2ef5d79e699e1a33e11ed8d518`. Damit ist der Manifest-/rsync-/Single-Finalization-Vertrag real bestätigt.

### ZEC-BL-UI-STATUS-002 – V16.2.0 Status-/SOC-Day-/Mobile-Settings-Härtung

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.0 / v16.2.0-20260920`.
- **Provenienz:** reale V16.1.0-Nutzung / Nutzerbefunde vom 20.09.2026.
- **Scope:** Primärspeicher-SOC-Ring-Layout; Tageswechsel-sicherer SOC-Day-Cache; „Jetzt“-Markierung nur am aktuellen Tag; mobile Settings-Suche mit erreichbarer Commit-Leiste; richtungsabhängige Restenergie und Leistungsbalken für beide Speicher; optionale Primärspeicher-Fallbackwerte für Kapazität und maximale Entladeleistung.
- **Safety:** reine UI-/Diagnose-/Settings-Metadaten-Erweiterung; `controller_logic.py` bleibt byteidentisch; neue Primärspeicherwerte besitzen keine Reglerwirkung.
- **Technischer Exit:** vollständige Regression `1098 Tests + 698 Subtests PASS`, identischer Lauf mit `ResourceWarning=error`, Browser-/Compile-/Deployment-/Datenblatt-/Fresh-extract-Gates PASS.
- **Realer Exit 20.09.2026:** Update V16.1.0 → V16.2.0 erfolgreich; Installer `ready=true`; konsolidierte read-only Feldabnahme insgesamt PASS mit allen 26 ausgewiesenen Checks PASS, einschließlich Releaseidentität, Controller-Readiness, Graph-/SOC-Day-/Settings-Verträgen, Installationsreport, Rollback-Backup und Performance-Budgets.

### ZEC-BL-DEP-004 – kanonischer maschinenlesbarer Build-Evidence-/Preflight-Vertrag

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.3 / v16.2.3-20260921`.
- **Fund 21.09.2026:** realer V16.2.2-`--preflight-only`-Lauf auf V16.2.0 brach vor jeder Produktivmutation ab, weil der Installer nicht vorhandene Freitextmarker in den vorhandenen grünen QA-Dateien verlangte. Diagnosebundle belegte `installed_identity=V16.2.0` und `rollback_result=not_required_preflight`.
- **Root Cause:** Build-Erzeugung und Installer hatten keinen gemeinsamen maschinenlesbaren Evidence-Vertrag; human-readable QA-Texte wurden als implizite Parser-API missbraucht.
- **V16.2.3-Scope:** `ZEC_BUILD_EVIDENCE_V1`; gemeinsamer `deployment_contract.py verify-build-evidence`; Installerdelegation ohne Freitextparsing; fail-closed Release-/Count-/ResourceWarning-Prüfung; finales Paketgate muss den Evidence-Teil des echten Installer-Preflights aus dem Fresh Extract ausführen.
- **Abgrenzung:** keine UI-, Regler-, Command-, Safety- oder Recoveryänderung; `controller_logic.py` bleibt byteidentisch. `ZEC-BL-DEP-002` bleibt separat offen.
- **Realer Exit 21.09.2026:** mutationsfreier V16.2.3-Preflight PASS; anschließendes Update V16.2.0 → V16.2.3 erfolgreich; Installationsreport SHA256 `7f727963537ca81c78184bdd28933ce24f5654f78a3c86126e5f0e66a98097ff`; Feldartefakt SHA256 `cd82a345765186104b9b6fbb485e69d0f43740f83d8bf81f70d104c95db5eab7`; Feldlauf insgesamt PASS. Damit ist der maschinenlesbare Build-Evidence-/Preflight-Vertrag real bestätigt.

### ZEC-BL-UI-SETTINGS-001 – Settings-Webmodell unterdrückt aktuelle produktive Releasefelder

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.4 / v16.2.4-20260921`.
- **Realer Fund 21.09.2026:** Nach erfolgreichem V16.2.3-Update fehlten `SECOND_BATTERY_CAPACITY_WH` und `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` auf der realen Settings-Webseite. Bei der Sourceverifikation wurde zusätzlich bestätigt, dass auch der produktive Aktivierungsschalter `SECOND_BATTERY_INTEGRATION_ENABLED` vom selben historischen S1/RC19-Filter betroffen war.
- **Root Cause:** Provenienzmetadaten `release_stage`/`origin` wurden fälschlich als Produkt-Surface-Autorität verwendet.
- **Umsetzung V16.2.4:** `SettingsRegistry` trennt explizit `SurfaceState` (`operational`/`target_only`) und Hardware-/Konfigurations-`Applicability`. `settings_model.py` und First-Install-Persistenz verwenden dieselbe zentrale operative Surface-Autorität. Nichtlegacy-Settings müssen explizit klassifiziert sein; unbekannte aktive/visible Kandidaten schlagen fail-closed fehl.
- **Hardwarevariabilität:** `SECOND_BATTERY_INTEGRATION_ENABLED` bleibt als operativer Einstieg unabhängig vom aktuellen Primärspeicherzustand erreichbar. Untergeordnete Primärspeicherfelder sind produktiv freigegeben, werden aber abhängig vom aktuellen Browser-Draft der Integration sichtbar. Die Topologie kann 1 oder 2 Zendure-Entities ausweisen; daraus entstehen ausdrücklich keine zweite Zendure-Commandkonfiguration und keine Freigabe von `ZEC-BL-MULTI-001`.
- **Negativvertrag:** spätere S3/S4/S6/S7-Zielsettings bleiben `target_only` und dürfen auch bei passender Hardware nicht produktiv exponiert werden.
- **Feldtool-Lücke geschlossen:** Die V16.2.4-Feldabnahme prüft live `/settings/model`, die drei erwarteten Primärspeicher-Controls, deren Surface-/Applicability-Vertrag sowie Negativproben für target-only Settings.
- **Safety:** keine Regler-, Command-, Safety- oder Recoveryänderung; `controller_logic.py` bleibt byteidentisch.
- **Realer Exit 22.09.2026:** konsolidierter V16.2.4-Feldlauf PASS; `primary_storage_settings_surface=PASS`; `SECOND_BATTERY_INTEGRATION_ENABLED`, `SECOND_BATTERY_CAPACITY_WH` und `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` jeweils real `available=True`, `editable=True`, `applicable=True`, `surface_state=operational`. Manuelle UI-Prüfung bestätigte Kapazitätsvalidation und die daraus resultierende kWh-/Maximalleistungsanzeige auf der Sunny-Island-Karte. Damit CLOSED / REAL_FIELD_PASS.

### ZEC-BL-UI-SETTINGS-MOBILE-001 – Mobile Settings ohne horizontalen Content-Overflow

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; `technical_state=TECHNICAL_BUILD_PASS`; Release `V16.2.5 / v16.2.5-20260922`.
- **Implementierungsstand 22.09.2026:** responsiver Viewport-/Intrinsic-Width-Vertrag umgesetzt; Input/Einheit stapeln auf kleinen Viewports, lange Keys/Fehler/Meta-Pills brechen, Pinch-Zoom bleibt zulässig aber nicht erforderlich. Fokussierte UI-/Diagnose-Regression und vollständige Build-/Fresh-extract-Gates PASS.
- **Reale Feldabnahme 22.09.2026:** auf realem iPhone im Expertenmodus geprüft. Input, Einheit, langer technischer Key, Validierungsfehler, Meta-Pills, Standard/Experte-Umschalter und die feste Änderungsleiste bleiben innerhalb des nutzbaren Settings-Viewports erreichbar; der gezeigte absichtlich ungültige Draftwert wird vollständig und ohne horizontal abgeschnittenen Content dargestellt. Kein Commit des Testwerts.
- **Realer Fund 22.09.2026:** Auf dem iPhone laufen Settings-Controls, Einheit, Validierungsbox und teilweise der Standard/Experte-Umschalter rechts über den Viewport hinaus. Die Seite ist absichtlich nicht horizontal scrollbar; dadurch wird Inhalt abgeschnitten und ist nicht erreichbar.
- **Root-Cause-Richtung:** der mobile Scrollcontainer ist auf vertikale Interaktion begrenzt (`overflow-x:hidden` / vertikaler Touch-Pfad), während einzelne Settings-Layoutzeilen eine Mindest-/Intrinsic-Breite oberhalb des Viewports behalten.
- **Zielvertrag V16.2.5:** Settings-Content muss bei 320/375/390/430 CSS-Pixel vollständig innerhalb des Viewports bleiben; horizontales Scrollen oder Pinch-Zoom sind kein Ersatz für responsives Layout. Lange Keys, Fehlermeldungen, Einheiten, Meta-Pills und Standard/Experte-Umschalter müssen umbrechen bzw. in eine mobile Layoutvariante wechseln. `scrollWidth <= clientWidth` ist als Regression-Gate abzudecken.
- **Abgrenzung:** keine Settings-Semantik-, Validation-, Persistenz- oder Regleränderung.

### ZEC-BL-UI-STATUS-003 – Speicherstatuskarten-Konsolidierung und reale Layout-Completion

- **Status:** OPEN / REAL_FIELD_PASS_WITH_UI_FOLLOWUP; `implementation_state=implemented_v16_2_5_plus_followup`; `technical_state=TECHNICAL_BUILD_PASS`; Releasebasis `V16.2.5 / v16.2.5-20260922`.
- **Standardkartenvertrag:** große signierte Istleistung ohne zusätzliche Richtungsbeschriftung; einteiliger Leistungsbalken Laden grün links→rechts / Entladen orange rechts→links; W/kW relativ zur belastbaren Maximalleistung ohne Prozentlabel; `Ladegrenze`/`Entladegrenze`; `Noch ladbar`/`Noch entladbar` als SOC-Prozentpunkte plus kWh nur bei belastbarer Kapazität.
- **Kapazitätspriorität:** reale/source-seitige usable/effective Kapazität → belastbare Geräte-/Templatekapazität → manueller Fallback → keine kWh. Keine scheinpräzisen Ersatzwerte.
- **V16.2.5 real bestätigt:** Desktop und reales iPhone zeigen keine Footer-/Content-Überdeckung; `Noch ladbar` steht lesbar in der rechten Detailspalte, Leistungsbeschriftung/-balken bleiben lesbar. Eine reale aktive `HIGH_SOC_CHARGE_LIMITED`-/Ladeannahme-Warnung wurde am 22.09.2026 sowohl eingeklappt als auch ausgeklappt beobachtet: Warnung bleibt sichtbar, Details sind lesbar und auf-/zuklappbar, regulärer Inhalt wird nicht überdeckt.
- **Neues reales UX-Finding 22.09.2026:** Bereits die eingeklappte V16.2.5-Warnungsbox vergrößert die Speicherkarte und dadurch die gesamte obere Kartenreihe deutlich. Das widerspricht dem erreichten Ziel hoher vertikaler Informationsdichte, obwohl die funktionale Warnungs-Evidenz selbst PASS ist.
- **Freigegebener Follow-up-Vertrag:** aktiver Warnzustand höhenneutral als Warning-Chip im vorhandenen Kartenkopf, vorzugsweise mit fachlicher Kurzbezeichnung (`Begrenzt`, `Ladeannahme` o. ä.); bei mehreren aktiven Warnungen aggregierter Hinweis/Anzahl. Details werden außerhalb des normalen Kartenflows geöffnet: Desktop als an der Karte verankertes nicht-layoutverschiebendes Popover, mobil als touch-taugliches Bottom-Sheet bzw. kompaktes Modal. Schließen der Details darf die aktive Warnung nicht verbergen. Hover allein reicht nicht; Touch/Tastatur müssen funktionieren. Keine schwebende Box darf regulären Karteninhalt verdecken.
- **Sequencing-/Releaseentscheidung:** Für diesen Follow-up wird kein eigener Hotfix-Zyklus erzwungen. Er ist verbindlicher isolierter Frontend-Subscope des nächsten ohnehin anstehenden Releases und blockiert die Fast-Capture-vs.-Adaptive-Entscheidung nicht.
- **Expert-Slice:** der V16.2.4-Primärspeicher-Slice `Strategie & Diagnose` bleibt erhalten; der vollständige kartenübergreifende Expertenmodus bleibt unter `ZEC-BL-UI-STATUS-EXPERT-001` offen.
- **Safety:** reine UI-/Diagnosedarstellung; keine Regler-, Command-, Safety- oder Recoveryänderung; bis zu einem Controllerrelease-spezifisch anders freigegebenen Scope bleibt die bestehende Reglersemantik unberührt.
- **Follow-up-Exit:** eingeklappte aktive Warnung erzeugt keine zusätzliche Karten-/Gridhöhe; geöffnete Details verschieben das Seitenlayout nicht; Warnexistenz bleibt permanent sichtbar; Desktop/Mobile/Keyboard/Touch und Mehrfachwarnungsfall regressionsgetestet.

### ZEC-BL-DIAG-OWNER-001 – Produktive Instance-Owner-Evidenz im Statussnapshot

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; `technical_state=TECHNICAL_BUILD_PASS`; Release `V16.2.5 / v16.2.5-20260922`.
- **Implementierungsstand 22.09.2026:** die fünf Instance-Owner-Felder sind im allgemeinen `ControllerState.snapshot()` ergänzt; Lock-/Owner-Semantik unverändert. Fokussierte Regression sowie vollständige Build-/Fresh-extract-Gates PASS.
- **Realer Exit 22.09.2026:** produktiver Snapshot bestätigt `INSTANCE_OWNER_ACTIVE=True`, `INSTANCE_OWNER_PID=39159`, `INSTANCE_OWNER_BUILD_ID=v16.2.5-20260922`. Damit ist der V16.2.4-Falschzustand `Owner nicht bestätigt` im realen V16.2.5-Pfad behoben, ohne Änderung der Instance-Lock-/Single-Owner-Semantik.
- **Realer Fund 22.09.2026:** Die produktive V16.2.4-Instanz läuft gesund und `ready=true`, aber `Controller & Schnittstellen` zeigt `Owner nicht bestätigt`, `Prozess —`, `Build —`. Der Feldsnapshot bestätigt `instance_owner_active=False`, `instance_owner_pid=None`, leere Build-ID.
- **Sourceverifikation:** `ZendureController.py` setzt Owner-Status/PID/Build-ID beim erfolgreichen Instance-Lock; `readiness_snapshot()` exportiert sie. Der allgemeine `ControllerState.snapshot()`-Pfad für `/status-view-data` übernimmt diese Felder jedoch nicht vollständig, wodurch ein falscher Diagnosezustand entsteht.
- **Zielvertrag V16.2.5:** Instance-Owner-Evidenz muss in allen relevanten Status-/Readiness-Snapshots konsistent sein; die UI darf eine real bestätigte produktive Instanz nicht als unbestätigt darstellen. Keine Lock-/Single-Owner-Semantikänderung, nur Snapshot-/Diagnosekonsistenz.
- **Exit:** Regression über `/health`, `/ready`, `/status` und `/status-view-data` bzw. deren reale Datenpfade; produktive Ownerdaten konsistent, fehlende Ownerdaten weiterhin ehrlich als unbestätigt dargestellt.

### ZEC-BL-GRAPH-GAP-001 – echte Datenlücken unterbrechen numerische Graphlinien

- **Status:** OPEN / REAL_FIELD_PASS_WITH_UI_FOLLOWUP; `implementation_state=partial`; `technical_state=TECHNICAL_BUILD_PASS`; Releasebasis `V16.2.5 / v16.2.5-20260922`.
- **V16.2.5 real bestätigt:** bestätigte Nicht-AVAILABLE-Evidence erzeugt renderseitige `null`-Breaks; über bekannter Controller-Downtime ist die numerische Linie tatsächlich sichtbar unterbrochen. Es entstehen keine synthetischen Messwerte. Damit ist der primäre Graph-Gap-Fix real PASS.
- **Verbleibender Interaktionsfehler:** Beim Hover/Klick innerhalb einer bestätigten Lücke zeigt das synchronisierte Cursor-/Tooltip-Overlay weiterhin Werte des nächsten realen Messpunkts außerhalb der Lücke; der Inspector liefert zwar keine Messwerte, rendert bei `actual_ms=null` aber `01.01.1970, 01:00:00` statt eines ehrlichen Gap-/Empty-States.
- **Sourceverifikation:** `syncPlugin` und `updateCursorCards()` verwenden `nearestDatasetPoint()`/`nearestIndex()` ohne Evidence-Gap-Gate; die `y:null`-Breaks verhindern die Linie, nicht das Nearest-Sample-Overlay. `renderInspector()` wandelt `null` über `Number(null)` in `0` und erzeugt damit den Epoch-Zeitwert.
- **Follow-up-Zielvertrag:** Innerhalb bestätigter `GAP`/`NOT_INSTRUMENTED`/`PURGED_BY_RETENTION`-Intervalle dürfen Cursor, Tooltip, Marker und Inspector keinen realen Nachbarpunkt an den Cursorzeitpunkt projizieren. Stattdessen Gap-/Empty-State ohne synthetische Werte; außerhalb bestätigter Lücken bleibt die bisherige Nearest-Interaktion unverändert. Normale Sampling-Jittertoleranz darf nicht unnötig in Gap-Semantik umklassifiziert werden.
- **Sequencing-/Releaseentscheidung:** Der Restfehler ist ein isolierter UI-/Interaktionsdefekt und kein Daten-, Regler-, Command-, Safety- oder Recoveryfehler. Wegen der real bereits korrekten Linienunterbrechung wird kein eigener V16.2.6-Hotfix-Zyklus erzwungen. Der Fix ist verbindlicher, eigenständig regressionsgeprüfter Frontend-Subscope des nächsten ohnehin anstehenden Releases und blockiert die Fast-Capture-vs.-Adaptive-Entscheidung nicht.
- **Exit:** Query-/Frontend-Regression mit Vorher-/Nachherpunkten und echtem Gap; Linie, Hover/Cursor, Tooltip, Inspector und Coverage/Evidence semantisch konsistent; im nicht verfügbaren Intervall keine Nearest-Sample-Werte oder Marker am Cursor; kein Epoch-Nullzeit-Fallback; außerhalb des Gaps unveränderte Interaktion.

### ZEC-BL-UI-STATUS-EXPERT-001 – vollständiger Statusseiten-Experten-/Diagnosemodus

- **Status:** OPEN; `implementation_state=partial`; Roadmapposition nach V16.2.4 weiterhin nicht automatisch festgelegt.
- **V16.2.4-Stand:** `UI_MODE=standard|expert` steuert nun auf der Primärspeicherkarte einen echten sichtbaren Superset-Slice. Im Expertenmodus werden `Strategie & Diagnose` mit Harmonisierung, Harvest/Strategie, diagnostischem usable SOC und Quellenstatus kompakt gerendert; die Standardkarte bleibt unverändert schlank.
- **Vertrag:** Expert bleibt Superset von Standard. Kritische Warnungen und Standardinformationen verschwinden nicht; der Modus ändert niemals Regler-/Command-/Safety-Semantik und erzeugt keine neue externe I/O.
- **Weiter offen:** der kartenübergreifende Completion-Scope mit vertieftem Status-Snapshot, Freshness/Validity, Reason-/Limiter-/Sollwertpipeline, Command-Effect/Readback/Resync, Timing/Runtime, Events und kontextbezogenen Diagnosezugängen. Nur vorhandene belastbare Daten dürfen exponiert werden.
- **Interaktion/Privacy:** technische Details benötigen erkennbare responsive Zugänge; Hover allein reicht nicht. Secrets und rohe vertrauliche Konfiguration bleiben ausgeschlossen.
- **Exit des Gesamtpunkts:** `UI_MODE` wirkt nachweisbar kartenübergreifend; Expert ist vollständiges Superset; responsive/Accessibility-/Regressionstests decken beide Modi und Moduswechsel ab.

### ZEC-BL-DIAG-FIELD-001 – Feldabnahme-Tool an Release- und Readinessvertrag synchronisieren

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.0 / v16.2.0-20260920`; **kein eigener Hotfix-Release**.
- **Fund V16.1.0 Realfeldabnahme 20.09.2026:** `tools/v16_field_acceptance.py` prüfte bei `SUPPORTED_UPDATE` noch hart auf V16.0.1 / `v16.0.1-20260915`, obwohl der V16.1.0-Installer korrekt ausschließlich V16.0.2 / `v16.0.2-20260917` als Updatequelle akzeptierte. Dadurch entstand ein falsches `install_report=FAIL` trotz realem Report `status=ok` für V16.0.2 → V16.1.0 und exakt verifiziertem Rollback-Backup.
- **Zweiter historischer Vertragsunterschied:** das Feldtool verlangte im Normalpfad strikt `ready=true`, während der Installer bereits eine gemeinsame releasespezifische READY/TRANSITIONAL/REJECT-Klassifikation besaß.
- **Umsetzung V16.2.0:** erwartete Updatequelle wird aus dem Installer-/Releasevertrag abgeleitet; Feldtool und Installer verwenden dieselbe sichere Readiness-Akzeptanzklassifikation, ohne Runtime-`/ready` abzuschwächen.
- **Realer Exit 20.09.2026:** reales Update V16.1.0 → V16.2.0 mit `FULL_READY`; Feldtool meldete `controller_ready: FULL_READY`, `controller_readiness_acceptance: READY:FULL_READY`, `install_report: PASS` und `rollback_backup_integrity: RELEASE_BACKUP_EXACT`; Gesamtfeldabnahme PASS.

### ZEC-EV-DEP-001 – reale Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Abnahme

- **Status:** DEFERRED durch Nutzerentscheidung vom 19.09.2026.
- Risiko bewusst akzeptiert; weiterhin erforderlich, aber bis auf weiteres kein Entwicklungsblocker.
- Offener Realpfad: read-only Uninstaller-Preflight, User-Data-Backup/Fresh-Reset, CLEAN_FRESH_INSTALL, Fresh Install, FIRST_INSTALL_SETUP, erster Settings-Commit, Restart NORMAL, Feldabnahme, abschließender Reset/Restore.

## 5. Dauerhaft geschlossene / supersedierte Entwicklungshistorie

Die folgenden Einträge bleiben bewusst im Master-Ledger. Die Liste ist auf die aus Release-Tree und Chat-Export belastbar recoverbaren größeren Schritte ausgerichtet.

| Ledger-ID | Release/Phase | Status | recoverbarer Abschlussinhalt |
|---|---|---|---|
| `ZEC-HIST-BASE-001` | frühe V12-Entwicklung | SUPERSEDED | lokale MQTT-/Zendure-Steuerung, frühe Shelly-/Graph-/Statusgrundlagen; in spätere Architektur überführt |
| `ZEC-HIST-MEAS-V3` | V12.9.x | SUPERSEDED | Measurement V3 als Diagnose-/Historienbasis; später durch V4 ersetzt |
| `ZEC-HIST-MEAS-V4` | V12.10/V12.13 | CLOSED | Measurement V4 als produktiver Diagnosevertrag; seit V12.13.0 V4-only Runtime, V3 nur offline/read-only |
| `ZEC-HIST-RC6` | V12.11.2-RC6 | CLOSED | UI-/Diagnose-Hotfix, Operational-Event-Semantik und Legacy-Statusreferenz |
| `ZEC-HIST-RC7` | V12.11.2-RC7 | CLOSED | MQTT-Freshness-0s-Fehler, Command-Lifecycle-/Timing-/Journaldiagnose |
| `ZEC-HIST-RC8` | V12.11.2-RC8 | CLOSED | SOC-Darstellung, stale Warnungsauflösung und UI/Diagnose/Installationsstabilisierung |
| `ZEC-HIST-RC9` | V12.11.2-RC9 | CLOSED | Replay-/Timing-/Status-/Logging-Diagnosepolish |
| `ZEC-HIST-RC10` | V12.11.2-RC10 | CLOSED | topologiefähige Statusseite und passiver Live-Preview-Dienst |
| `ZEC-HIST-RC11` | V12.11.2-RC11 | CLOSED | 0-W-Neutralisierung, Full-State-Resync, intentbasierter Effect-Timer, unabhängige Wirkungsklassifikation |
| `ZEC-HIST-RC12` | V12.11.2-RC12 | CLOSED | SmartMode-/Flash-Schutz, Command-State-Rücklesung, getrennte Netz-/Pack-/Offgrid-Powersemantik |
| `ZEC-HIST-RC13` | V12.11.2-RC13 | CLOSED | Neutralisierungs-Deduplizierung, Command-State-Gate, Trackingtoleranz, Publish-Evidenz |
| `ZEC-HIST-RC14` | V12.11.2-RC14 | CLOSED | High-SOC-Ladeannahme/Taper-Reklassifikation ohne Zielwertformeländerung |
| `ZEC-HIST-RC15` | V12.11.2-RC15 | CLOSED | Publish-Historie vs. Geräte-Readback getrennt, Late-Effect-/Recovery-Guard-Härtung |
| `ZEC-HIST-RC16` | V12.11.2-RC16 | CLOSED | `SMA_FULL_OR_IDLE` Delta→Absolutzielkorrektur |
| `ZEC-HIST-RC17` | V12.11.2-RC17 | CLOSED | Harvest 0-W-Netzziel/Export-Capture-Untergrenze, High-SOC-/Near-Limit-Allokation |
| `ZEC-HIST-RC18` | V12.11.2-RC18 | CLOSED | asynchroner lokaler Zendure-API-Worker; keine externe I/O im Regelzyklus |
| `ZEC-HIST-RC19` | V12.11.2-RC19 | CLOSED | Status-/Diagnose-Stabilisierung, Requested-vs-Applied, API-Worker-Sichtbarkeit |
| `ZEC-HIST-RC20` | V12.11.2-RC20/Fix6 | CLOSED | SettingsRegistry/UI, Config-Runtime, Preview/Commit, Restart, Last-Good/Recovery-Unterbau |
| `ZEC-HIST-V12_11_3` | V12.11.3 | CLOSED | Installer-Readiness-Akzeptanz sicherer transienter Commandzustände |
| `ZEC-HIST-V12_11_4` | V12.11.4 | CLOSED | mobile Settings/Modal/Event-Reconciliation/Warnzähler |
| `ZEC-HIST-V12_11_5` | V12.11.5 | CLOSED | Desktop-Settings-Shell, Nacht-HH:MM-Compoundfelder, Preview-422-UX, Adminaktionen |
| `ZEC-HIST-V12_11_6` | V12.11.6 | CLOSED | Settings-/Status-UX, lokale Validation, Default/Reset-Semantik, sichere Sentinelwerte |
| `ZEC-HIST-V12_11_7` | V12.11.7 | CLOSED | explizite Default-Provenienz/Reset-Policy und fail-closed FIRST_INSTALL_SETUP-Vertrag |
| `ZEC-HIST-V12_12_0` | V12.12.0 | CLOSED | strukturierte Settings-Hilfe & Guided Configuration |
| `ZEC-HIST-V12_12_1` | V12.12.1 | CLOSED | Help-/Terminologie-/Such-/Mobile-Quality-Fix |
| `ZEC-HIST-V12_12_2` | V12.12.2 | CLOSED | Single-Owner, monotone/fresh Harvest-Entry, Limiter-/Manifest-/SOC-UI-Härtung |
| `ZEC-HIST-V12_13_0` | V12.13.0 | CLOSED | Measurement V4-only / Legacy-V3-Runtime-Cleanup |
| `ZEC-HIST-V13_0_0` | V13.0.0 | CLOSED | benannte Konfigurationsstände, Import/Export, Portabilität, historische Config-/SOC-Timeline |
| `ZEC-HIST-V13_0_1` | V13.0.1 | CLOSED | Readiness-/Releaseidentitätsfix der V13-Linie |
| `ZEC-HIST-V13_0_2` | V13.0.2 | CLOSED | Config-State-/CSRF-/SQLite-Writer-/Backfill-Härtung |
| `ZEC-HIST-V13_0_3` | V13.0.3 | CLOSED | Config-Preview-UX-Hotfix und Feldabschluss vor Graph-Hauptblock |
| `ZEC-HIST-V14_0_0` | V14.0.0 | CLOSED | Graph Core V3, relationale Persistenz, Query/Catalog, Coverage/Evidence/Retention-Ledger, Inspector/Command-Follow/Episodenvergleich, Rebuild/Cutover |
| `ZEC-HIST-V14_1_0` | V14.1.0 | CLOSED | Greenfield Graph-UI/Analyse-Workspace |
| `ZEC-HIST-V14_1_1` | V14.1.1 | CLOSED | Installer-/Runtime-Root-Fix für Graphassets |
| `ZEC-HIST-V14_1_2` | V14.1.2 | CLOSED | explizite Selection, Zeitraum-/Episodenvergleich, synchronisierte Interaktion/Evidence-Segmente |
| `ZEC-HIST-V14_1_3` | V14.1.3 | CLOSED | Graph-State-History-Repair und Status-SOC-Responsiveness |
| `ZEC-HIST-V14_1_4` | V14.1.4 | CLOSED | Graph-/Status-Performance und UX-Polish |
| `ZEC-HIST-V15_0_0` | V15.0.0 | CLOSED | source-neutrale Primärspeicherarchitektur, EVCC/custom/Modbus-Template, read-only Modbus/TCP |
| `ZEC-HIST-V15_0_1` | V15.0.1 | CLOSED | Graph-/Analyse- und Primary-Settings-UX-Härtung |
| `ZEC-HIST-V15_0_2` | V15.0.2 | CLOSED | Graph-Interaktionsbugfixes / Detailausschnitt / Command-Follow-Layout |
| `ZEC-HIST-V15_0_3` | V15.0.3 | CLOSED | technisches Datenblatt dauerhaft in Releasevertrag integriert |
| `ZEC-HIST-V16_0_0` | V16.0.0 | CLOSED IMPLEMENTATION | brokerneutraler Installer/Fresh-Install/Uninstaller/Support-Grundvertrag; Real-Fresh-Evidenz siehe `EV-DEP-001` |
| `ZEC-HIST-V16_0_1` | V16.0.1 | CLOSED | Installer-Paketidentitäts-Hotfix |
| `ZEC-BL-DEP-001` | V16.0.2 | CLOSED | fail-closed Cleanup verwaister Python-Caches entfernter Quellbäume; realer Updatepfad bestätigt |
| `ZEC-HIST-V16_1_0` | V16.1.0 | CLOSED | SMA Sunny Island 31009 Capability, separate Freshness/Diagnose/usable SOC, source-neutrale Primärspeicher-Namenshygiene; keine Reglerwirkung; reales Update/Block-A am 20.09.2026 feldabgenommen. Rohes Feldtool `23 PASS / 2 FAIL`; beide FAILs als Toolvertrag-Abweichungen unter `ZEC-BL-DIAG-FIELD-001` belegt. |

## 6. No-Drop-/Reconciliation-Vertrag für dieses Ledger

Vor dem Entfernen/Archivieren einer Übergabe, Spezifikation, Work-Chat-Delta-Datei oder historischen Projektquelle müssen alle Planungsmarker und IDs gegen dieses Ledger reconciliiert werden. Mindestens zu prüfen:

```text
Backlog / Roadmap / offen / Restpunkt / später / perspektivisch
Nicht Bestandteil / deferred / TODO / Folgeblock / S1..S9
```

Jeder Fund benötigt genau eine Auflösung:

1. bestehender Master-Eintrag,
2. neuer Master-Eintrag, oder
3. explizit belegtes `CLOSED`, `SUPERSEDED` oder `REJECTED`.

Ein ungeklärter Fund bedeutet **BACKLOG_NO_DROP_GATE = FAIL** und blockiert die Quellenbereinigung.

## 7. Release-Evidenz und Changelog

Ab dem ersten Release nach dieser Kanonisierung wird eine Snapshot-Fassung dieses Master-Ledgers im Release-Tree mitgeliefert:

```text
docs/ZEC_Master_Backlog.md
```

Sie ist Entwicklungs-/Roadmap-Evidenz. Ein Release-Changelog kann aus den seit dem Vorgänger neu `CLOSED` gesetzten bzw. releasezugeordneten Einträgen abgeleitet werden. Das Changelog ersetzt das Ledger nicht; offene, zurückgestellte, supersedierte und verworfene Punkte bleiben im Master erhalten.

## 8. Recovery-Provenienz 19.09.2026

Der aktuelle Ledgerstand wurde aus folgenden Ebenen reconciliiert:

1. aktuelle kanonische Projektquellen;
2. verifiziertes V16.0.2-Release-ZIP und darin erhaltene Spezifikationen/Release-/Übergabeunterlagen;
3. `conversations.json` mit 34 systematisch geprüften ZEC-/Zendure-relevanten Chats;
4. aktueller V16.0.2-Implementierungsgegencheck.

Details: `ZEC_34_CHAT_RECONCILIATION_20260919.md`.

## 9. Roadmapentscheidung 20.09.2026 – Provenienz

Nutzerentscheidung im ZEC-Projekt am 20.09.2026 nach Recovery/Neuaufstellung des Master-Ledgers:

```text
(S3 + adaptive Strategie + Kapazitätsgewichtung)
→ Battery Care
→ Storage
→ Graph→Analyse-Handoff
→ Counterfactual Simulation
→ Szenarioeditor
→ Multi-Zendure-Commandbetrieb
→ Release/CI-Hardening
```

Begründung für die Zusammenführung des ersten Blocks: Im parallelen Projektchat **„Installierte PV Anlage“** wird das grundlegende Lernmodell für adaptive Lade-/SOC-/Ertragsstrategie und Kapazitätsgewichtung entwickelt; saisonale Faktoren und dynamische Tagesprofile sind Teil dieser Konzeption. Die finale Abdeckung ist erst mit der dortigen Abschlussübergabe verbindlich festzustellen. Bis dahin werden keine historischen Child-Scopes als erledigt markiert.

## 10. Projektquellen-Reconciliation 21.09.2026

Der V16.2.3-Technical-Freeze-Stand enthält maschinell inventarisiert **81 eindeutige stabile `ZEC-BL`/`ZEC-EV`/`ZEC-HIST`-IDs**. Die Post-Freeze-Reconciliation nach realer V16.2.3-Installation und manueller UI-Prüfung erhält sämtliche 81 IDs und ergänzt genau eine neue ID:

1. `ZEC-BL-UI-SETTINGS-001` – real bestätigter Settings-Webmodell-/Availability-Defekt für aktuelle produktive V16.2.0-Felder.

Fortgeschrieben, aber nicht entfernt oder umbenannt wurden insbesondere:

- `ZEC-BL-DEP-003` → `CLOSED / REAL_FIELD_PASS` durch erfolgreichen V16.2.3-Updatepfad;
- `ZEC-BL-DEP-004` → `CLOSED / REAL_FIELD_PASS` durch erfolgreichen V16.2.3-Preflight/Update;
- `ZEC-BL-UI-STATUS-003` → `OPEN`, `implementation_state=partial`, weil die manuelle UI-Prüfung nach automatischem PASS einen realen Surface-Defekt fand;
- `ZEC-BL-UI-STATUS-EXPERT-001` bleibt `OPEN / partial` und erhält den realen Primärspeicher-Superset-Befund;
- `ZEC-BL-CTRL-FASTCAP-001`, `ZEC-BL-CTRL-ADAPTIVE-001` und alle Child-/Folgepunkte bleiben vollständig erhalten; ihre nächste Reihenfolge wird nach dem unmittelbaren UI-/Settings-Bugfix explizit entschieden.

Damit enthält dieses Ledger nach Kanonisierung **82 eindeutige stabile IDs**. Keine Vorgänger-ID wurde entfernt. Die im Handover inventarisierten Planungsmarker sind entweder einem bestehenden Eintrag oder `ZEC-BL-UI-SETTINGS-001` zugeordnet.

**BACKLOG_NO_DROP_GATE = PASS**

### V16.2.4 Build-Reconciliation 21.09.2026

Der freigegebene V16.2.4-Block erzeugt **keine neue Ledger-ID**. Alle 82 zuvor kanonisierten stabilen IDs bleiben erhalten. Fortgeschrieben werden ausschließlich bestehende Punkte: `ZEC-BL-UI-SETTINGS-001`, `ZEC-BL-UI-STATUS-003`, `ZEC-BL-UI-STATUS-EXPERT-001` und `ZEC-BL-DEP-002`. Fast Capture, Adaptive samt Child-IDs, usable-SOC Block B, Primary Metadata und Battery Care bleiben unverändert recoverbar.

**BACKLOG_NO_DROP_GATE = PASS (82/82 IDs erhalten)**

### V16.2.4 Real-Field-/V16.2.5-Hotfix-Reconciliation 22.09.2026

Die reale V16.2.4-Abnahme erhält alle bisherigen **82** stabilen IDs und ergänzt für die manuell bestätigten neuen Defektklassen genau drei IDs:

1. `ZEC-BL-UI-SETTINGS-MOBILE-001`;
2. `ZEC-BL-DIAG-OWNER-001`;
3. `ZEC-BL-GRAPH-GAP-001`.

`ZEC-BL-UI-SETTINGS-001` und `ZEC-BL-DEP-002` werden durch reale V16.2.4-Evidenz auf `CLOSED / REAL_FIELD_PASS` fortgeschrieben. `ZEC-BL-UI-STATUS-003` bleibt erhalten und wird wegen der realen Karten-/Warnungsbefunde in den freigegebenen V16.2.5-Hotfix überführt. `ZEC-BL-UI-STATUS-EXPERT-001` bleibt `OPEN / partial`. Fast Capture, Adaptive samt Child-IDs, usable-SOC Block B, Primary Metadata, Battery Care und alle übrigen Vorgängerpunkte bleiben unverändert recoverbar.

Damit enthält das Ledger **85 eindeutige stabile IDs**. Keine Vorgänger-ID wurde entfernt oder umbenannt.

**BACKLOG_NO_DROP_GATE = PASS (82/82 Vorgänger-IDs erhalten; 3 neue IDs; Gesamt 85)**

### V16.2.5 Real-Field-Reconciliation 22.09.2026

Die reale Installation V16.2.4 → V16.2.5 und der konsolidierte automatische Feldlauf sind PASS. Die übergebene Evidence weist `controller_ready=WARN LIMIT_READBACK_CONVERGENCE`, aber `controller_readiness_acceptance=PASS TRANSITIONAL:LIMIT_READBACK_CONVERGENCE` aus; das entspricht dem bestehenden Readinessvertrag. Evidence-Archiv-SHA256: `b8b188f487f05eac5fcba8d94614ecb17731c88389708e84425113cf43cad239`.

Die anschließende manuelle Sichtprüfung und Nutzerentscheidung führen ohne neue Ledger-ID zu folgenden Fortschreibungen:

- `ZEC-BL-UI-SETTINGS-MOBILE-001` → `CLOSED / REAL_FIELD_PASS`;
- `ZEC-BL-DIAG-OWNER-001` → `CLOSED / REAL_FIELD_PASS`;
- `ZEC-BL-UI-STATUS-003` → funktionale V16.2.5-Warnungsdarstellung real PASS; neuer UX-Follow-up für höhenneutralen Header-Warning-Chip mit Desktop-Popover/Mobile-Bottom-Sheet bleibt `OPEN`;
- `ZEC-BL-GRAPH-GAP-001` → sichtbare Linienunterbrechung real PASS; Gap-aware Cursor-/Tooltip-/Inspector-Semantik bleibt `OPEN`.

Der Nutzer entscheidet am 22.09.2026 ausdrücklich, für die beiden isolierten UI-Restpunkte keinen eigenen Hotfix-Zyklus zu erzwingen. Beide werden verbindlich im nächsten ohnehin anstehenden Release separat regressionsgeprüft mitgeführt und blockieren die Fast-Capture-vs.-Adaptive-Sequencing-Entscheidung nicht. Damit ist das Sequencing-Gate freigegeben, ohne eine Reihenfolge vorwegzunehmen.

Alle bisherigen **85** stabilen IDs bleiben erhalten; keine ID wird entfernt, umbenannt oder durch die neue Feldbeobachtung ersetzt.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**

### Fast-Capture-Sequencing-/Revalidation-Reconciliation 22.09.2026

Die neutrale Gegenüberstellung Fast Capture versus Adaptive ist abgeschlossen. Der Nutzer bestätigt die technische Entkopplung und legt **Fast Capture A400/R100 als nächsten Controllerblock** fest. Die eingefrorene Produktionsspezifikation wurde gegen V16.2.5 revalidiert und um die releaseintegrierte Feldverifikationspflicht ergänzt. Adaptive bleibt mit sämtlichen Child-IDs erhalten und wird nach Bereitstellung des Fast-Capture-Releases als eigener Spezifikationsblock fortgeführt.

Es entsteht keine neue Ledger-ID: Die Verifikationslogik ist Bestandteil des Exit-/Evidenzvertrags von `ZEC-BL-CTRL-FASTCAP-001`, und die Adaptive-Spezifikationslücke bleibt unter `ZEC-BL-CTRL-ADAPTIVE-001` samt Child-IDs erhalten. Alle bisherigen **85** stabilen IDs bleiben unverändert.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**



### V17.0.0 Fast-Capture Checkpoint A/B Reconciliation 22.09.2026

Der freigegebene V17.0.0-Fast-Capture-Block bleibt unter der bestehenden ID `ZEC-BL-CTRL-FASTCAP-001`; es entsteht keine neue Ledger-ID. Checkpoint A implementiert Controllerkern/State und bestand die fokussierte Differential-/Safetyregression mit **110 Tests + 11 Subtests PASS**. Checkpoint B ergänzt Settings-/Validationvertrag, Measurement-V4-Evidenz, `tools/fast_capture_field_analysis.py`, `tools/v17_field_acceptance.py` und die Analysis-Package-Integration; die fokussierte Checkpoint-B-Regression bestand mit **114 Tests + 640 Subtests PASS**.

Die V16.2.5-Produktivbasis bleibt bis Release-/Feldfreigabe unverändert. Die zwei bekannten Frontend-Follow-ups bleiben unter `ZEC-BL-GRAPH-GAP-001` und `ZEC-BL-UI-STATUS-003` erhalten und bilden den nächsten isolierten Entwicklungscheckpoint. Vollständige Regression, ResourceWarning-, Syntax-, Manifest-, Fresh-extract- und Releasegates sind noch ausstehend; daher **kein TECHNICAL BUILD PASS**.

Checkpoint C setzt die zwei separat freigegebenen Frontend-Follow-ups um: Gap-aware Cursor/Marker/Inspector/Command-Follow/Comparison-Hover sowie den höhenneutralen Zendure-Warning-Chip mit Desktop-Popover/Mobile-Bottom-Sheet. Die fokussierte Checkpoint-C-Regression besteht mit **12 Tests PASS**.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**


### V17.0.1 Real-Field / V17.0.2 Fast-Evidence-Hotfix Reconciliation 23.09.2026

`ZEC-BL-CTRL-FASTCAP-001` bleibt dieselbe stabile Ledger-ID; keine neue Produkt-ID erforderlich. Reales V16.2.5 -> V17.0.1 Update PASS, automatischer V17-Feldlauf PASS und Runtime `FULL_READY`. Fast Capture wurde anschließend real auf `shadow` gesetzt. Ein Night-Mode-Snapshot bestätigte fail-closed `fast_capture_active=false`, Overlay 0 und `NIGHT_MODE`-Blockierung. Der Desktop-Warning-Chip/Popover unter `ZEC-BL-UI-STATUS-003` ist real visuell PASS; die mobile Bottom-Sheet-Variante bleibt Feld-Follow-up.

Beim ersten natürlichen Shadow-Evidenzversuch wurden drei Verifikationsdefekte des V17.0.1-Evidenzpfads real gefunden: (1) Fast-Capture-Runtimefelder fehlten in `ControllerState.record_graph_point()` und fielen in Measurement V4 dadurch auf `off`/0 zurück; (2) der Fast-Analyzer bewertete alle historischen Config-Snapshot-Versionen statt nur die von analysierten Rows referenzierten Config-Hashes und erzeugte `CONTROLLER_VERSION_MISMATCH`; (3) `create_zec_analysis_package.sh --latest-only` konnte unter `set -o pipefail` durch eine früh abbrechende Pipeline mit SIGPIPE/rc=141 enden. Die V17.0.1-Shadow-V4-Daten sind daher nicht als kanonischer Fast-Funktionsnachweis verwertbar. Active bleibt nicht freigegeben.

V17.0.2 ist als isolierter Evidence-/Tooling-Hotfix (+0.0.1) freigegeben: Fast-Felder werden cycle-exakt in den Measurement-V4-Zulauf übernommen; Analyzer-Versionsevidenz wird auf referenzierte Config-Hashes begrenzt und strukturelle Evidenz im Human-Report sichtbar; `--latest-only` wird pipefail-/SIGPIPE-sicher. A400/R100-Regler-, Command-, Safety-, Cross-Charge- und Recoverysemantik bleiben unverändert; `controller_logic.py` bleibt byteidentisch zu V17.0.1. Nach V17.0.2-Installation muss neue reale Shadow-Evidenz gesammelt werden, bevor ein begrenzter Active-Rollout überhaupt freigegeben werden kann.

**BACKLOG_NO_DROP_GATE = PASS (85/85 stabile IDs erhalten; 0 neue IDs)**


### V17.0.2 Fast-Evidence-Hotfix Technical-Build-Pass Reconciliation 23.09.2026

`ZEC-BL-CTRL-FASTCAP-001` bleibt dieselbe stabile Ledger-ID; keine neue Produkt-ID entsteht. V17.0.2 korrigiert die drei am realen V17.0.1-Shadow-Evidenzpfad gefundenen Defekte: cycle-exakte Fast-Felder werden in `record_graph_point()` und damit Measurement V4 transportiert; Analyzer-Versionsevidenz wird ausschließlich über von analysierten Rows referenzierte Config-Hashes gebildet und strukturelle Evidenz wird im Human-Report sichtbar; `create_zec_analysis_package.sh --latest-only` ist pipefail-/SIGPIPE-sicher.

Technischer Nachweis: fokussierte Regression **51 Tests PASS**; realer `--latest-only`-Shelltest mit >80 V4-Dateien PASS; vollständige Regression **157 Testdateien / 1169 Tests + 706 Subtests PASS**; identischer `-W error::ResourceWarning`-Lauf **1169 + 706 PASS**; Bash **13/13**, Browser-JavaScript **3/3**, Python Compileall, Deployment-Harness **11/11**, Datenblatt-Gate und maschinenlesbare Build-Evidence PASS. Das aktuelle 10-seitige Datenblatt wurde nach dem finalen Statusupdate vollständig gerendert und visuell geprüft. `controller_logic.py` bleibt SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031` und damit byteidentisch zu V17.0.1. Release-Hygiene, Source-Manifest 932/932, kanonischer ZIP-Root sowie Paket-/Fresh-extract-Manifest-, Build-Evidence- und Datenblatt-Gates sind im Release-Freeze PASS; nach dem Dokumentationsfreeze wird das exakt veröffentlichte ZIP neu gebaut und identisch verifiziert.

Reale V17.0.2-Installation und neue Shadow-Feldevidenz bleiben **FIELD_PENDING**. V17.0.1-Shadow-V4-Daten werden wegen des real nachgewiesenen Evidence-Pfadddefekts nicht als Fast-Funktionsnachweis verwendet. `active` bleibt nicht freigegeben. Der Desktop-Warning-Chip/Popover ist real visuell PASS; die mobile Bottom-Sheet-Variante bleibt als UI-Feldevidenz offen.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**


### V17.0.2 Final Package / Release Reconciliation 23.09.2026

Das exakt veröffentlichte Installerpaket `zendure_controller_v17_0_2.zip` hat SHA256 `82bd2db52a71b4a4e56f8e8c39e30511494fb02f8735909667052b73bd82f311` und Größe 14.402.481 Byte. Finaler Paketpfad: Release-Hygiene PASS; Source-Manifest **932/932 PASS**; kanonischer ZIP-Root `zendure_controller_v17_0_2/` PASS; ZIP-Integrität PASS; Fresh-extract Release-Hygiene PASS; Fresh-extract Manifest **932/932 PASS**; Build-Evidence PASS; Datenblatt-Gate PASS; Paket-Root-Verifikation PASS. Ein Build-Runtime-Lauf des echten Installers mit exakt diesem ZIP erreichte `Package-Identität: PASS`, Datenblatt PASS, Runtime-Readiness-Smoke PASS und Build-Evidence PASS und stoppte anschließend erwartungsgemäß am Host-Gate `Installer muss als Benutzer pi gestartet werden`; dies ist kein Ersatz für den realen Raspberry-Pi-Updatefeldtest.

`ZEC-BL-CTRL-FASTCAP-001` bleibt **IN_PROGRESS / TECHNICAL_BUILD_PASS / FIELD_PENDING**. V17.0.1 bleibt reale Runtimebasis bis zum erfolgreichen V17.0.2-Update. Danach müssen neue Shadow-Daten erzeugt werden; V17.0.1-Fast-V4-Evidence wird nicht wiederverwendet. `active` bleibt nicht freigegeben.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**

### V17.0.2 Nacht-MIN_SOC-/SMA-Parser-Reconciliation 25.09.2026

Die reale V17.0.2-Evidenz ergänzt genau zwei stabile Ledger-IDs:

1. `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` – real bestätigter Nacht-/MIN_SOC-Control-Gap; **RELEASE_BLOCKER_NEXT_RELEASE**.
2. `ZEC-BL-GRID-SMA-OBIS-001` – strukturell unzureichender SMA-Speedwire-/OBIS-Parser; **BUG_CONFIRMED / FIX_REQUIRED_NEXT_RELEASE**. Die exakte historische Raw-Frame-Ursache des wiederkehrenden Extremwertes ist keine Fix-Vorbedingung.

Alle bisherigen **85** stabilen IDs bleiben vollständig erhalten; keine Vorgänger-ID wurde entfernt oder umbenannt. Das aktuelle Ledger enthält damit **87 eindeutige stabile IDs**.

**BACKLOG_NO_DROP_GATE = PASS (85/85 Vorgänger-IDs erhalten; 2 neue IDs; Gesamt 87)**

### Projektquellen-/Realfeld-Synchronisation 25.09.2026

Die kanonischen Quellen `00`, `01`, `05`, `06` und `07` wurden auf die reale V17.0.2-Basis synchronisiert. Festgehalten sind insbesondere:

- V17.0.2 real installiert und allgemeiner Feldlauf PASS / FULL_READY;
- Fast-Capture-Shadow-Gate PASS; Active-`NEAR_LIMIT` in den beobachteten Aspekten real PASS; Active-`FULL_IDLE` weiterhin EVIDENCE_PENDING;
- Fast-Capture-Evidence-Tooling muss Calculation-Anwendbarkeit und bounded-memory-Langzeitanalyse härten;
- `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` sind zwingender Scope des nächsten Produktreleases;
- produktive Real-Pi-Analysen großer V4-Historien müssen streaming/bounded-memory erfolgen;
- Nomenklatur: „Fast Capture“, bei Platzknappheit „FastC“, nicht kontextlos „Fast“.

Keine der 85 Vorgänger-IDs wurde entfernt oder umbenannt. Die zwei neuen IDs bleiben stabil erhalten; Gesamtbestand 87.

**BACKLOG_NO_DROP_GATE = PASS (85/85 Vorgänger-IDs erhalten; 2 neue IDs; Gesamt 87)**


### Strategie-/Herbst-Reconciliation 18.10.2026

- Abgestimmte Richtungsentscheidung nach 23-Tage-Herbstanalyse: Adaptive-A1 begründet `DEFERRED/EVIDENCE_GAP`; `ZEC-BL-CTRL-S3-001`, `ZEC-BL-CTRL-USABLE-SOC-001` (B2) und `ZEC-BL-CTRL-CAP-001` (C1) eigenständige fachliche Scopes; Battery Care winterpriorisiert. Historischer 20.09.-Umbrella-Zuschnitt und spätere Vorgänger-Roadmap-Zitate bleiben als Provenienz erhalten, ihre Sequenz ist supersediert.
- Getrennte normative Ebenen: `05` alleinige Ledger-/Roadmapautorität; `ZEC_STRATEGIEARCHITEKTUR_ENTSCHEIDUNGSSTAND_20261018.md` hält fachliche Richtungsentscheidungen fest, **nicht** als freigegebene Implementierungsspezifikation; `ZEC_S3_FACHLICHE_PRODUKTIONSSPEZIFIKATION_ENTWURF_20261018.md` ist nicht freigegebener S3-Entwurf; `ZEC_A1_WIRKSAMKEIT_23T_DECISION_BRIEF_20261017.md` ist retrospektive Evidenz.
- Neues eigenständiges diagnostisches Forschungsthema `ZEC-BL-BATTERY-SOH-001` bewahrt die konkrete Kapazitätsalterungs-Frage, ohne sie stillschweigend als C1/Adaptive-Produktwirkung zu deklarieren.
- Zwei zwingende Fehlerkorrekturen `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` bleiben uneingeschränkte Next-Release-Blocker. Command-Episoden aus dem Oktober bleiben gezielte Analyse-/Recovery-Provenienz unter vorhandener Command-/Observability-Arbeit, ohne neuen pauschalen Pi-Langanalyseblock.
- Aktuelle Produktbasis bleibt V17.0.2; keine S3-/B2-/C1-/Adaptive-/Battery-Care-Sourceänderung, keine neue Runtime oder Release-PASS durch die Quellpflege.
- **BACKLOG_NO_DROP_GATE:** Alle **43** im gelieferten Ledgertext explizit vorhandenen stabilen ZEC-BL-/ZEC-EV-IDs bleiben erhalten; eine neue `ZEC-BL-BATTERY-SOH-001`, somit **44** textuell nachweisbare IDs. Die aus früheren Projektständen überlieferte Angabe „87 eindeutige IDs“ ist im aktuellen gelieferten Master-Ledger **nicht einzeln prüfbar**. Kein Dokument wird gelöscht, historische Entscheidungs-/Planungszeilen bleiben erhalten. Die historische 87er-Zählung ist bei späterer gezielter Auditierung zu klären, bevor Quellen entfernt/archiviert werden.

**BACKLOG_NO_DROP_GATE = PASS für 43/43 im aktuellen Ledgertext verifizierbare Vorgänger-IDs; 1 neue explizite ID; keine entfernten Quellen. Historischer 87/87-Vollbestand = NOT_EVALUABLE aus diesem Dateiinhalt; deshalb keine Quellenbereinigung zulässig, bevor die Diskrepanz geklärt ist.**


### Architektur- und Historien-Dokumentationsentscheid 19.10.2026

Der Nutzer bestätigt die künftige Versionierung wesentlicher technischer As-built-Dokumente, Produktionsspezifikationen und Architekturentscheidungen im Source-`docs/`, einschließlich möglichst leicht zu übernehmender historischer Originalunterlagen. Die damals noch nicht implementierte Fast-Capture-Spezifikation für V16.0.2 liegt wieder als Original vor; die V16.2.5-Revalidierung ist nur historisch belegt, als Original aktuell nicht verfügbar. Dies wird unter der stabilen neuen ID `ZEC-BL-DOC-ARCH-001` geführt; die Dokumentationspolicy ist in `01`/`06` festgelegt, die Integration in einen realen Release samt QA steht noch aus. Kein anderer Backlogpunkt wird geändert, gelöscht oder ersetzt. Die vorher textuell erkennbaren 44 eindeutigen ZEC-BL-/ZEC-EV-IDs bleiben erhalten; neu 1 -> 45 belegbare IDs. Der historisch genannte 87er-Gesamtbestand bleibt **nicht unabhängig verifiziert**, daher weiterhin keine Projektquellenbereinigung/History-Drops.
