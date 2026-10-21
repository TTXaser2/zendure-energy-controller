# ZEC V16.0.1

## Zweck

V16.0.1 ist ein enger Installer-Hotfix. Der Release korrigiert die ausführbare Paketidentitätsprüfung im mutationsfreien Preflight. Regelalgorithmus, Regelstrategie, Settingssemantik, Measurement-Semantik, Graphdaten und Hardware-Schonungslogik bleiben unverändert.

## Korrektur

- Der Installer verwendet keinen eingebetteten, shell-escape-abhängigen Python-RegEx mehr.
- Die Paketidentität wird über den gemeinsamen Parser in `tools/deployment_contract.py` geprüft.
- Exakte Version und Build-ID werden fail-closed validiert.
- Eine falsche oder unvollständige Paketidentität beendet den Preflight vor jeder Produktivmutation.
- Ein ausführender Regressionstest deckt den real verwendeten Identitätsparser und dessen Installerintegration ab.

## Deployment-Suite

- kanonischer Installer `tools/install_zendure_controller.sh`;
- rückwärtskompatibler Wrapper `tools/update_zendure_controller.sh`;
- gemeinsamer Installationszustandsdetektor mit `SUPPORTED_UPDATE`, `CLEAN_FRESH_INSTALL` und fail-closed `AMBIGUOUS_OR_PARTIAL_INSTALL`;
- mutationsfreier `--preflight-only`-Pfad;
- Clean Fresh Install mit optionalem `--web-port` im Bereich 1024..65535;
- FIRST_INSTALL_SETUP ohne MQTT-Verbindungsaufbau und mit gesperrter Regelung;
- dynamischer lokaler Webendpoint für Installer, Feldabnahme und Diagnosetools.

## Schutzgrenzen

- keine fachliche Änderung an Regelstrategie, Harvest, Cross-Charge oder Command-Semantik;
- `controller_logic.py` bleibt byteidentisch;
- Measurement V4 bleibt unverändert;
- bestehende Graph-/History-/UI- und Primärspeicherfunktionen bleiben erhalten.

## Releaseidentität

- Version: `16.0.1`
- Label: `V16.0.1`
- Build-ID: `v16.0.1-20260915`
- unterstützte Updatequelle: ausschließlich `15.0.3 / v15.0.3-20260911`
- Fresh Install: ausschließlich bei real erkanntem `CLEAN_FRESH_INSTALL`
- Paket: `zendure_controller_v16_0_1.zip`

## Produktivfreigabe

TECHNICAL BUILD PASS wird erst nach vollständigem Source-Freeze und Fresh-Extract-Gate erteilt. PRODUCTIVE-PASS erfordert zusätzlich reale Update- und Clean-Fresh-Install-Feldtests.
