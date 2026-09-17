# ZEC V16.0.0 – Technical Notes

## Architektur
V16.0.0 ergänzt ZEC um eine transaktionale Deployment-Suite. Der gemeinsame `deployment_contract.py` liefert Installationszustand, WEB_PORT-/Bootstrapvertrag, dynamischen lokalen Endpoint und Dependency-Matrix. Installer und Uninstaller verwenden denselben Zustandsbegriff.

## Fresh Install
Ein Clean Fresh Install erzeugt keine erfundene Produktivkonfiguration. Der erste Controllerstart erfolgt mit fehlender `config.json` im `FIRST_INSTALL_SETUP`. Die Web-/Settingsoberfläche ist erreichbar, die Regelung bleibt gesperrt und MQTT wird bis zum ersten gültigen Commit nicht verbunden. Der Bootstrap kann ausschließlich `WEB_PORT` tragen und verliert nach dem ersten kanonischen Commit seine Autorität.

## Update
Der Updatepfad akzeptiert ausschließlich V15.0.3 / `v15.0.3-20260911`, erzeugt ein vollständiges Rollback-Backup, erhält konfigurierte Runtime-/Historydaten und kopiert die V16-Sources mit Löschung veralteter Paketdateien. Graph Core V3 wird nicht neu aufgebaut, sondern vor und nach dem Copy-Schritt read-only verifiziert.

## WEB_PORT
Der unterstützte Deploymentbereich ist 1024..65535. Fresh-Install-Preflight und Settings-Validierung blockieren nicht bindbare/belegte Ports. Installer- und Diagnoselogik verwendet den tatsächlich wirksamen lokalen Endpoint statt eines hart codierten `:8080`.

## Supportdiagnostik
`zec_support_bundle.py` ist der gemeinsame secretsichere Kern. Die externe Standarddiagnose enthält redigierte Konfiguration, Dependency-/HTTP-/systemd-/journal-/Kernel-/Storage-Evidenz und niemals eine rohe `config.json`. Installerfehler werden vor Rollback erfasst; das Rollbackresultat wird in dasselbe Diagnosepaket aufgenommen.

## Uninstaller/User-Data-Backup
Der Uninstaller entfernt ausschließlich aktive ZEC-Artefakte. Das standardmäßige lokale Restore-Backup darf echte Konfiguration/Secrets enthalten und besitzt deshalb einen anderen Sicherheitsvertrag als das extern teilbare Supportbundle. Measurement-/Deep-Trace-Daten sind opt-in.

## No-Regression
Der Live-Regelalgorithmus, die Control-&-Safety-Invarianten, Harvest, Cross-Charge, Command-Lifecycle, Measurement-Semantik und Hardware-Schonungslogik sind nicht fachlicher Bestandteil dieses Architekturblocks und bleiben geschützt.
