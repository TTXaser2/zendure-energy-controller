# ZEC V16.0.2 – Technical Notes

## Fehlerursache

Der V16.0.1-Updatepfad verwendet `rsync --delete`, schließt gleichzeitig jedoch `__pycache__/` aus. Wird ein kompletter alter Python-Modulbaum aus dem Release entfernt, kann sein ausgeschlossener Cache den ansonsten zu löschenden Elternordner nicht leer werden lassen. Im realen Update von V15.0.3 auf V16.0.1 erschien dadurch `cannot delete non-empty directory: zendure_controller_v12`; zurück blieben ausschließlich `.pyc`-Dateien.

## Korrektur

`tools/deployment_contract.py` stellt die Operation `cleanup-obsolete-caches` bereit. Sie ermittelt `__pycache__`-Verzeichnisse im installierten Runtimebaum, deren Elternpfad im gestagten Zielrelease nicht mehr existiert. Vor jeder Mutation wird der vollständige Kandidatensatz validiert. Nur leere Caches oder Caches mit ausschließlich regulären `.pyc`/`.pyo`-Dateien sind löschbar. Symlinks, Unterverzeichnisse oder andere Inhalte blockieren die gesamte Bereinigung fail-closed.

Der Installer führt diese Operation erst nach dem vollständigen Rollback-Backup und vor `rsync --delete` aus. Dadurch kann `rsync` den nun leeren obsoleten Modulordner regulär entfernen, während aktuelle Quellbäume und geschützte Benutzerdatenpfade unangetastet bleiben.

## Regression

`tests/test_v16_0_2_installer_cache_hygiene.py` deckt vier Aspekte ab:

1. nur Caches wirklich entfernter Quellbäume werden bereinigt;
2. fremder Nicht-Cache-Inhalt blockiert die Operation ohne Teilmutation;
3. ein realer `rsync --delete`-Lauf entfernt den alten V12-Modulordner ohne die bekannte Warnung und erhält geschützte Nutzerdaten;
4. CLI und Installerreihenfolge verwenden denselben geprüften Cleanup-Vertrag vor dem Sync.

## No-Regression

Der Release verändert den Live-Regelalgorithmus nicht. `controller_logic.py` besitzt weiterhin SHA256 `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`. Measurement-V4-Header bleiben 246/249. Der Deployment-Harness bleibt 11/11 PASS.
