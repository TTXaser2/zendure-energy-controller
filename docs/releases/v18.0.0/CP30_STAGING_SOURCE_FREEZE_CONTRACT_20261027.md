# CP30 – V18.0.0 technisches Identitäts-Staging (nicht zur Installation)

**Status:** `DEVELOPMENT_NOT_INSTALLABLE` / `RELEASE_HOLD` / `PHYSICAL_EFFECT_NOT_VERIFIED` / `MANUAL_UML_REVIEW_PENDING`  
**Quelle:** CP29 V18-Entwicklungsstand, reale Produktivbasis V17.1.3 / `v17.1.3-20261022`.  
**Ziel-Stagingidentität:** V18.0.0 / provisorisch `v18.0.0-20261027`. Dies ist **keine** endgültige freigegebene Build-ID.

`tools/prepare_v18_staging_tree.py` ist ein lokales Releasevorbereitungswerkzeug, kein Installer. Es akzeptiert nur einen unveränderten CP29-Entwicklungsbaum mit bestandener Draft-Provenienz, schreibt niemals in diesen Basisbaum, überschreibt keine vorhandene Ausgabe und erzeugt stattdessen einen neuen separaten `zendure_controller_v18_0_0_STAGING_NOT_INSTALLABLE`-Baum. Die V18-Identität wird ausschließlich in dieser Kopie gesetzt, mit exakter V17.1.3-Upgradequelle und dem bestehenden, bis vor jeglichem Preflight hart gesperrten V18-Installerkandidaten als Standardinstaller. Er besitzt kein Execute-Bit. Ein getrennter maschinenlesbarer Staging-Nachweis prüft V18-Kennung, Source-Manifest, Sperre und die erwartete *nicht bestandene* Release-Identitätsprüfung.

`V18_0_0_SOURCE_MANIFEST.sha256` deckt den Stagingbaum ab; `docs/ZEC_Master_Backlog.md` ist ein identischer Ledger-Snapshot. Das Build-Evidence-JSON ist bewusst `ZEC_BUILD_EVIDENCE_V1` mit `status=BLOCKED` sowie Tests `NOT_RUN_ON_FINAL_TREE`. **Ein mitgeliefertes Testlog früherer Checkpoints darf nie zu V18-Build-PASS umetikettiert werden.** Auch die historische V17.1.3-Build-Evidence bleibt als Provenienz, nicht als Freigabe des neuen Baums.

**Releaseblocker vor finaler Freigabe:** (1) endgültige Version/Build-ID und erneute vollständige Regressions-/Ressourcenwarnungs- und Source-Manifest-Prüfung auf exakt eingefrorenem Baum, (2) Datenblatt DOCX und daraus erzeugtes PDF mit visueller/fachlicher Prüfung, (3) fachlich manuelle UML-Freigabe, (4) voller Standardinstaller inkl. echter Fresh-Extract-/Preflight-/Update-/Fresh-Install-/Rollback-/Diagnose-Gates, (5) reale Battery-Care-Wirkung einschließlich PV-/Netz-/Notladung und Command-Effect-/Restart-Wirksamkeit. Bis dahin bleibt auch die übergeordnete Releaseidentitätsprüfung `FAIL` und die V18-Feldabnahme `NOT_EVALUABLE`.

**Keine Pi-Kommandos und keine Installationsanweisung** aus diesem Staging ableiten. Der spätere freigegebene Ablauf wird separat für Termius auf dem iPhone mit SHA, Backup, Update, Prüfung und Rollback beschrieben. Master-Ledger-Autorität: `05_ZEC_BACKLOG_AND_ROADMAP.md`.
