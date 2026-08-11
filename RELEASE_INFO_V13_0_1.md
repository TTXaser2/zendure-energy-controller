# Release Info – Zendure Energy Controller V13.0.1

**Version:** `13.0.1`  
**Label:** `V13.0.1`  
**Build-ID:** `v13.0.1-20260811`

## Zweck

V13.0.1 ist ein eng begrenzter Hotfix auf der V13.0.0-Codebasis. V13.0.0 konnte während der Produktivinstallation trotz bereits gesundem `/ready`-Payload (`ready=true`) automatisch zurückrollen, weil `tools/evaluate_installation_readiness.py` noch die V12.13.0-Releaseidentität hart codiert hatte.

## Korrektur

- Der Readiness-Evaluator liest `APP_VERSION` und `APP_BUILD_ID` direkt aus der gemeinsam ausgelieferten `version.py`.
- Dadurch existiert für die Post-Install-Abnahme keine separat zu pflegende Zielidentität mehr.
- Ein vollständig gesunder V13.0.1-`/ready`-Payload wird als `READY:FULL_READY` akzeptiert.
- Fremde bzw. ältere Releaseidentitäten bleiben `REJECT:IDENTITY`.
- Der Installer akzeptiert als Produktiv-Ausgangsbasis weiterhin ausschließlich die verifizierte V12.13.0 / `v12.13.0-20260811`, weil die fehlerhafte V13.0.0-Installation automatisch auf diesen Stand zurückgerollt hat.
- Der bereits implementierte idempotente Measurement-V4→Graph-Config-Timeline-Backfill bleibt fachlich unverändert und wird nach erfolgreicher Installations-Abnahme automatisch ausgeführt.

## No-Regression-Scope

Keine fachliche Änderung an AUTO, Harvest, Cross-Charge, NIGHT, Command Lifecycle/Resync, Single-Owner, Measurement V4, Config-State-/Import-/Exportlogik oder Graphhistoriensemantik.
