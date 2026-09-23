# Installation – Zendure Energy Controller V16.2.5

**Release:** `V16.2.5`  
**Build-ID:** `v16.2.5-20260922`

V16.2.5 besitzt einen gemeinsamen Deploymentpfad für ein strikt unterstütztes Update und einen Clean Fresh Install. Unklare oder partielle Installationen werden fail-closed abgewiesen. Der mutationsfreie Preflight verifiziert zusätzlich die kanonische maschinenlesbare Build-Evidenz `validation/V16_2_5_BUILD_EVIDENCE.json`; Freitextmarker sind keine Installer-Autorität.

## 1. Voraussetzungen

Der ZEC-Installer ist kein Betriebssystem-Bootstrapper. Vorausgesetzt werden insbesondere:

- Raspberry Pi OS/Linux mit `systemd`;
- Benutzer und Gruppe `pi`, `/home/pi` und funktionsfähiges `sudo`;
- Python 3 einschließlich der ZEC-Runtimeabhängigkeiten;
- die vom Preflight geprüften lokalen Werkzeuge, u. a. `unzip`, `rsync`, `tar`, `curl`, `sha256sum`, `install`, `find` und `visudo`.

Fehlende Runtime-/Installerabhängigkeiten werden **nicht** automatisch per apt/pip installiert. Der Preflight bricht vor Produktivmutation ab und gibt einen konsolidierten Installationshinweis aus.

Ein lokaler `mosquitto.service` ist keine Installationsvoraussetzung. Für den normalen Regelbetrieb muss der konfigurierte MQTT-Broker erreichbar sein.

## 2. Paket vorbereiten

Das finale `zendure_controller_v16_2_5.zip` unter `/home/pi/Downloads` ablegen, den extern veröffentlichten SHA256 prüfen und anschließend:

```bash
cd /home/pi/Downloads
unzip -t zendure_controller_v16_2_5.zip
rm -rf zendure_controller_v16_2_5
unzip -q zendure_controller_v16_2_5.zip
chmod +x zendure_controller_v16_2_5/tools/install_zendure_controller.sh
```

Der kanonische Installer heißt ab V16.0.0:

```text
tools/install_zendure_controller.sh
```

`tools/update_zendure_controller.sh` bleibt nur als Kompatibilitätswrapper erhalten.

## 3. Reguläres Update: kombinierter sicherer Ablauf

Für ein regulär freigegebenes reales Update wird kein separater manueller `--preflight-only`-Zwischenstopp benötigt. Der normale Installer führt intern zuerst den vollständigen Preflight aus und beginnt Produktivänderungen ausschließlich bei `PREFLIGHT_RESULT=PASS` und `SAFE_TO_INSTALL=yes`.

Empfohlener Ein-Schritt-Ablauf für V16.2.4 -> V16.2.5:

```bash
set -euo pipefail
cd /home/pi/Downloads
ZIP="zendure_controller_v16_2_5.zip"
EXPECTED_SHA="<VEROEFFENTLICHTER_SHA256>"
DIR="zendure_controller_v16_2_5"
ACTUAL_SHA="$(sha256sum "$ZIP" | awk '{print $1}')"
[ "$ACTUAL_SHA" = "$EXPECTED_SHA" ] || { echo "FEHLER: SHA256 stimmt nicht" >&2; exit 1; }
unzip -t "$ZIP"
rm -rf "$DIR"
unzip -q "$ZIP"
chmod +x "$DIR/tools/install_zendure_controller.sh"
bash "$DIR/tools/install_zendure_controller.sh" v16_2_5
```

Der Updatepfad akzeptiert ausschließlich:

- Version `16.2.4`
- Build-ID `v16.2.4-20260921`

Bis zum abgeschlossenen internen Preflight gilt `PRODUCTIVE_CHANGES=NONE`. Erst danach erzeugt der Installer das Rollback-Backup und setzt das Update fort. Ein separater `--preflight-only`-Lauf bleibt für ausdrücklich mutationsfreie Diagnose-/Vertragsprüfungen verfügbar.

Ein erfolgreicher Installerlauf schreibt den maschinenlesbaren Report atomar und timestamped nach `/home/pi/Downloads/zec_v16_2_5_install_report_<STAMP>.json`; `/tmp/zec_v16_2_5_install_report.json` bleibt nur Kompatibilitätskopie.

## 4. Clean Fresh Install

Für Clean-Fresh-Installationen bleibt der explizite Fresh-Install-Vertrag erhalten. Ein mutationsfreier Diagnose-Preflight kann bei Bedarf separat ausgeführt werden:

```bash
bash zendure_controller_v16_2_5/tools/install_zendure_controller.sh \
  v16_2_5 --fresh-install --preflight-only
```

Normaler Fresh-Install-Lauf mit Default-Webport 8080:

```bash
bash zendure_controller_v16_2_5/tools/install_zendure_controller.sh \
  v16_2_5 --fresh-install
```

Alternativer Webport, z. B. 8088:

```bash
bash zendure_controller_v16_2_5/tools/install_zendure_controller.sh \
  v16_2_5 --fresh-install --web-port 8088
```

Unterstützter Bereich: `1024..65535`. Ein belegter oder nicht bindbarer Port wird vor Produktivmutation abgewiesen. Ein erfolgreicher erster Start endet absichtlich in `FIRST_INSTALL_SETUP`:

```text
service active
/health alive=true
/settings erreichbar
config_health=missing
control_allowed=false
ready=false
```

`ready=false` ist in diesem Zustand korrekt. Der MQTT-Verbindungsaufbau wird bis zum ersten gültigen Settings-Commit ausgesetzt. Der gewählte Bootstrap-Webport ist im Settingsmodell sichtbar. Nach dem ersten gültigen Commit ist ein Neustart erforderlich; erst danach beginnt der normale Betriebsstart mit der kanonischen `config.json`.

## 5. Dynamischer lokaler Webendpoint

Installer, Field-Acceptance und Supportwerkzeuge verwenden den tatsächlich wirksamen `WEB_PORT` und setzen nicht fest `:8080` voraus. Maßgeblich sind Produktivkonfiguration, First-Install-Bootstrap oder der Defaultport 8080.

## 6. Uninstaller / Fresh-Install-Reset

Der kanonische Uninstaller ist:

```text
tools/uninstall_zendure_controller.sh
```

### Nur prüfen

```bash
cd /opt/zendure-controller
bash tools/uninstall_zendure_controller.sh --fresh-install-reset --preflight-only
```

### Fresh-Install-Reset mit Standard-Benutzerdatensicherung

```bash
cd /opt/zendure-controller
bash tools/uninstall_zendure_controller.sh --fresh-install-reset
```

Vor der Entfernung wird standardmäßig ein lokales, restore-orientiertes Benutzerdatenbackup erzeugt. Dieses Backup kann echte Secrets enthalten und ist **kein** extern teilbares Supportbundle.

Optional:

```text
--backup-dir DIR
--include-measurement-data
--no-user-data-backup --confirm-no-user-data-backup
--yes
```

Measurement-/Deep-Trace-Daten werden wegen ihrer möglichen Größe nur mit `--include-measurement-data` in das User-Data-Backup aufgenommen. `--fresh-install-reset` ist erst erfolgreich, wenn der gemeinsame Zustandsdetektor anschließend `CLEAN_FRESH_INSTALL_STATE=yes` bestätigt.

Der Uninstaller entfernt keine Betriebssystempakete, keinen MQTT-Broker, kein EVCC, keine Netzwerk-Konfiguration und keine allgemeinen Python-/Systempakete.

## 7. Support- und Fehlerdiagnose

Jeder Installerlauf besitzt ein persistentes Installerlog. Bei Installerfehlern wird automatisch ein secretsicheres Supportbundle aufgebaut:

1. Fehlerzustand vor Rollback erfassen;
2. Rollback ausführen, soweit erforderlich;
3. Rollbackresultat demselben Diagnosevorgang hinzufügen;
4. genau ein finalisiertes Support-ZIP bereitstellen.

Das standardmäßig extern teilbare Support-ZIP enthält keine rohe `config.json`. Für einen manuellen Supportfall steht zusätzlich der gemeinsame Supportbundle-Einstiegspunkt zur Verfügung.

## 8. Feldabnahme

Nach einem Update bzw. einem vollständig eingerichteten Normalstart:

```bash
cd /opt/zendure-controller
python3 tools/v16_field_acceptance.py \
  --expect-primary-profile modbus_template \
  --output /home/pi/Downloads/ZEC_V16_2_5_FIELD_ACCEPTANCE.json
```

Das Tool ermittelt den lokalen Webendpoint dynamisch, sofern kein expliziter `--base-url` angegeben wird. Ohne `--install-report` bevorzugt es den neuesten persistenten V16.2.5-Installationsreport unter `/home/pi/Downloads`; nur wenn keiner vorhanden ist, wird die definierte `/tmp`-Kompatibilitätskopie verwendet. Ein explizites `--install-report` gewinnt immer. Die erwartete Updatequelle wird aus dem Installervertrag abgeleitet. Für den Startzustand gilt dieselbe READY/TRANSITIONAL/REJECT-Klassifikation wie im Installer; ein zulässiger `TRANSITIONAL`-Zustand wird transparent ausgewiesen und setzt Runtime-`/ready` nicht auf `true`.

Ein `TECHNICAL BUILD PASS` bestätigt ausschließlich Build, Paketintegrität und Fresh-Extract-Gates; er ist keine reale Feldfreigabe. Für die releasespezifische V16.2.5-Feldfreigabe ist die reale Update-Feldabnahme V16.2.4 -> V16.2.5 einschließlich Speicherstatuskarten-, Mobile-Settings-, Instance-Owner- und Graph-Gap-Evidenz erforderlich.

Der übergreifende vollständige `PRODUCTIVE-PASS` bleibt darüber hinaus solange unzulässig, wie die separat zurückgestellte reale Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Gesamtabnahme (`ZEC-EV-DEP-001`) offen ist. Eine erfolgreiche V16.2.5-Update-Feldabnahme schließt diesen separaten Deployment-Evidenzpunkt nicht automatisch. Build-, Harness- und `--preflight-only`-Nachweise ersetzen reale Feldtests nicht.
