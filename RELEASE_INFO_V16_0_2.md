# ZEC V16.0.2

## Zweck

V16.0.2 ist ein enger Installer-Hygiene- und Härtungsrelease. Er beseitigt den real beobachteten Updatebefund, bei dem ein entfernter Altmodulordner wegen eines ausgeschlossenen `__pycache__/`-Verzeichnisses nach `rsync --delete` als verwaister Restbestand bestehen bleiben konnte.

## Korrektur

- Vor dem Update-Sync werden ausschließlich Python-Cacheverzeichnisse betrachtet, deren übergeordneter Quellbaum im neuen Release nicht mehr existiert.
- Eine Bereinigung ist nur zulässig, wenn das Cacheverzeichnis leer ist oder ausschließlich reguläre `.pyc`/`.pyo`-Dateien enthält.
- Symlinks, Unterverzeichnisse oder sonstiger Inhalt blockieren die Bereinigung fail-closed vor Mutation.
- Bestehende aktuelle Quellbäume und deren Caches werden nicht von der neuen Bereinigung angefasst.
- Der reale `rsync --delete`-Regressionsfall mit einem entfernten `zendure_controller_v12/__pycache__` wird ausführend getestet; die Warnung `cannot delete non-empty directory` darf nicht mehr auftreten.
- Konfiguration und explizit geschützte Benutzerdatenpfade bleiben im simulierten Update unverändert.

## Schutzgrenzen

- keine fachliche Änderung an Live-Regelalgorithmus, Harvest, Cross-Charge, Command-Semantik oder Measurement V4;
- `controller_logic.py` bleibt byteidentisch zu V16.0.1;
- keine pauschale Löschung unbekannter Nicht-Cache-Inhalte durch die neue Cachebereinigung;
- Clean Fresh Install, Preflight, Rollback, Uninstaller und Supportpfade bleiben Bestandteil des bestehenden V16-Deploymentvertrags.

## Releaseidentität

- Version: `16.0.2`
- Label: `V16.0.2`
- Build-ID: `v16.0.2-20260917`
- unterstützte Updatequelle: ausschließlich `16.0.1 / v16.0.1-20260915`
- Fresh Install: ausschließlich bei real erkanntem `CLEAN_FRESH_INSTALL`
- Paket: `zendure_controller_v16_0_2.zip`

## Produktivfreigabe

**TECHNICAL BUILD PASS.** Source-Freeze und vollständige Fresh-Extract-Gates sind bestanden. Ein vollständiger PRODUCTIVE-PASS bleibt ohne die reale Update-Feldabnahme V16.0.1 → V16.0.2 und ohne die separat ausstehende reale Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Abnahmekette unzulässig.
