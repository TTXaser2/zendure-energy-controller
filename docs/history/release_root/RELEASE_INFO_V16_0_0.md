# ZEC V16.0.0

## Zweck
V16.0.0 führt einen vollständigen, brokerneutralen Deployment- und Supportvertrag für Supported Update und Clean Fresh Install ein. Der Release ändert nicht die fachliche Regelstrategie.

## Deployment-Suite
- kanonischer Installer `tools/install_zendure_controller.sh`;
- rückwärtskompatibler Wrapper `tools/update_zendure_controller.sh`;
- gemeinsamer Installationszustandsdetektor mit `SUPPORTED_UPDATE`, `CLEAN_FRESH_INSTALL` und fail-closed `AMBIGUOUS_OR_PARTIAL_INSTALL`;
- mutationsfreier `--preflight-only`-Pfad;
- Clean Fresh Install mit optionalem `--web-port` im Bereich 1024..65535;
- First-Install-Bootstrap ausschließlich für `WEB_PORT`;
- FIRST_INSTALL_SETUP ohne MQTT-Verbindungsaufbau, mit erreichbarer Web-/Settingsoberfläche, `control_allowed=false` und erwartbarem `ready=false`;
- keine systemd-Abhängigkeit zu `mosquitto.service`;
- dynamischer lokaler Webendpoint für Installer, Field-Acceptance und Diagnosetools.

## Uninstaller und Wiederherstellung
- `tools/uninstall_zendure_controller.sh` mit `--uninstall`, `--fresh-install-reset` und `--preflight-only`;
- lokales restore-orientiertes Benutzerdatenbackup standardmäßig aktiv;
- optionales Measurement-/Deep-Trace-Backup;
- explizit doppelt bestätigter Backup-Opt-out;
- Fresh-Reset gilt erst nach gemeinsam erkanntem `CLEAN_FRESH_INSTALL` als erfolgreich.

## Support-Hardening
- gemeinsamer secretsicherer Diagnosekern für Fresh-Install-Fehler, Updatefehler und manuellen Support;
- persistentes Installer-/Uninstallerlog;
- Fehlerzustand wird vor Rollback erfasst, Rollbackresultat im selben Supportvorgang ergänzt;
- extern teilbares Standardbundle ohne rohe `config.json`;
- dynamischer WEB_PORT, Dependency-Matrix, systemd/journald, HTTP-Snapshots und Storage-/Kernel-Evidenz.

## Schutzgrenzen
- keine fachliche Änderung an Regelstrategie, Harvest, Cross-Charge, Command-Semantik, Measurement-Semantik oder Hardware-Schonungslogik;
- `controller_logic.py` bleibt geschützt;
- Measurement V4 bleibt unverändert;
- bestehende Graph-/History-/UI- und Primärspeicherfunktionen bleiben erhalten.

## Releaseidentität
- Version: `16.0.0`
- Label: `V16.0.0`
- Build-ID: `v16.0.0-20260913`
- unterstützte Updatequelle: ausschließlich `15.0.3 / v15.0.3-20260911`
- Fresh Install: ausschließlich bei real erkanntem `CLEAN_FRESH_INSTALL`
- Paket: `zendure_controller_v16_0_0.zip`

## Produktivfreigabe
TECHNICAL BUILD PASS wird erst nach vollständigem Source-Freeze und Fresh-extract-Gate erteilt. PRODUCTIVE-PASS erfordert zusätzlich reale Update- und Clean-Fresh-Install-Feldtests.
