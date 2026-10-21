# V17.1.1 – technische QA-Evidenz (Release-Kandidat)

**Basis:** extern verifizierter `ZEC_UX_RELEASE_CANDIDATE_DEV_CP09_20261020.zip`, SHA256 `7b658197550a4dcc3fa30855f2dfe85aafb3ee8fe797dac87fa78d77abe41983`.

- **168 Testmodule** in 14 nicht überlappenden Gruppen, regulär **1236 Tests + 718 Subtests PASS**, unter `PYTHONWARNINGS=error::ResourceWarning` identisch **1236 + 718 PASS**.
- Interne QA-Belege und vollständige Batchlogs im nachfolgenden vollständigen Entwicklungs-Freeze, aggregierter Log-Hash-Vertrag in `v17_1_1_qa_aggregate.json`.
- Regression enthält sämtliche bestehenden ZEC V17.1.0- und neuen V17.1.1-Hilfe-/Minigraph-Tests. Legacy MQTT-Tests in getrennten Prozessen, keine Produktcode-Umgehungen.
- Browser-Smokes mit headless Chromium auf Desktop 1280px / mobil 390px, 320px für 5/15/60min, echte Zeitachsenlogik, Captions und horizontale Layoutintegrität; synthetische Transportfixtures, **kein** Real-Pi-Browser-PASS.
- Non-destructive Deployment-Harness: **11/11 PASS**. Reglerkern SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7` unverändert gegenüber finaler V17.1.0.
- Datenblatt und As-built-Index V17.1.1 versionsgebunden, reale Feldabnahme steht aus.
- Dieses Dokument ist eine QA-Zusammenfassung; der technische vollständige Freigabestatus erfordert erfolgreiches Manifest-/Fresh-extract-/Installer-Paketgate.
