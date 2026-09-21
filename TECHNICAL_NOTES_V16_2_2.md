# ZEC V16.2.2 – Technical Notes

## Root Cause des V16.2.1-Installer-Fails

Das V16.2.1-Source-Manifest enthielt fünf Dateien unter `.pytest_cache/`. Der Installer schließt `.pytest_cache/` und `__pycache__/` beim `rsync` bewusst aus. Die anschließende Zielprüfung verwendete jedoch dasselbe vollständige Manifest. Dadurch waren die fünf im Manifest erwarteten Dateien im Ziel definitionsgemäß nicht vorhanden und `sha256sum -c` brach den Installer ab.

Der V16.2.1-Preflight konnte diesen Widerspruch nicht erkennen, weil er den unveränderten entpackten Paketbaum prüfte, in dem die Cachedateien noch vorhanden waren.

## V16.2.2 Manifest-/Release-Hygiene

`tools/deployment_contract.py` enthält nun einen gemeinsamen fail-closed Vertrag für Release-Hygiene und Manifestprüfung. Verboten sind insbesondere volatile Cache-/Bytecode-Artefakte und Runtime-Datenbanken. `manifest-build` verweigert einen nicht sauberen Tree; `release-hygiene` prüft Paketbaum und aktuelles Manifest; `verify-manifest` prüft Pfadsicherheit, verbotene Einträge, Duplikate, Existenz und SHA256.

Der Installer führt `release-hygiene` im Paket-Preflight vor Produktivmutation aus und verwendet nach dem Copy denselben `verify-manifest`-Vertrag. Damit sind Paketmanifest und tatsächlich deploybarer Releaseinhalt auf denselben Dateivertrag gebunden.

## Doppelte Fehlerfinalisierung

Der Installer verwendet `set -E`, wodurch `ERR`-Traps in Subshells vererbt werden. Der reale Manifestfehler lief in einem Subshell und konnte dort Supportcapture/Rollback auslösen; der Hauptprozess behandelte anschließend denselben Fehler erneut. V16.2.2 speichert den `BASHPID` des Hauptprozesses und erlaubt Supportcapture/Rollback ausschließlich dort. Ein Subshell beendet bei Fehler nur sich selbst und überlässt die einmalige Finalisierung dem Hauptprozess.

## Regression

Ein neuer Hotfixtest führt echte `rsync`-Kopien für Update und Fresh-Install mit den Installer-Excludes aus und verifiziert anschließend das Manifest am Ziel. Zusätzlich werden verbotene Cacheartefakte in Tree und Manifest fail-closed getestet.

## No-Regression

Der UI-Stand aus V16.2.1 wird unverändert übernommen. `controller_logic.py` bleibt byteidentisch mit SHA256 `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`.

## Technical-Build-QA

Der vollständige Pre-Freeze- und paketierte Fresh-Extract-Nachweis ist PASS: 147 Testdateien mit `1106 Tests + 698 Subtests`, derselbe vollständige Satz mit `ResourceWarning=error`, Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Rollback, Datenblatt und Release-Hygiene. Der neue Hygiene-Check erkannte während der Engineering-QA ein erzeugtes Runtime-SQLite-Artefakt fail-closed; dieses wurde vor Manifest-/Paketbau entfernt.
