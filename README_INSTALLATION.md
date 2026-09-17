# Installation – Zendure Energy Controller V16.0.1

**Release:** `V16.0.1`  
**Build-ID:** `v16.0.1-20260915`

V16.0.1 besitzt einen gemeinsamen Deploymentpfad für ein strikt unterstütztes Update und einen Clean Fresh Install. Unklare oder partielle Installationen werden fail-closed abgewiesen.

## 1. Voraussetzungen

Der ZEC-Installer ist kein Betriebssystem-Bootstrapper. Vorausgesetzt werden insbesondere:

- Raspberry Pi OS/Linux mit `systemd`;
- Benutzer und Gruppe `pi`, `/home/pi` und funktionsfähiges `sudo`;
- Python 3 einschließlich der ZEC-Runtimeabhängigkeiten;
- die vom Preflight geprüften lokalen Werkzeuge, u. a. `unzip`, `rsync`, `tar`, `curl`, `sha256sum`, `install`, `find` und `visudo`.

Fehlende Runtime-/Installerabhängigkeiten werden **nicht** automatisch per apt/pip installiert. Der Preflight bricht vor Produktivmutation ab und gibt einen konsolidierten Installationshinweis aus.

Ein lokaler `mosquitto.service` ist keine Installationsvoraussetzung. Für den normalen Regelbetrieb muss der konfigurierte MQTT-Broker erreichbar sein.

## 2. Paket vorbereiten

Das finale `zendure_controller_v16_0_1.zip` unter `/home/pi/Downloads` ablegen, den extern veröffentlichten SHA256 prüfen und anschließend:

```bash
cd /home/pi/Downloads
unzip -t zendure_controller_v16_0_1.zip
rm -rf zendure_controller_v16_0_1
unzip -q zendure_controller_v16_0_1.zip
chmod +x zendure_controller_v16_0_1/tools/install_zendure_controller.sh
```

Der kanonische Installer heißt ab V16.0.0:

```text
tools/install_zendure_controller.sh
```

`tools/update_zendure_controller.sh` bleibt nur als Kompatibilitätswrapper erhalten.

## 3. Mutationsfreier Preflight

### Update einer vorhandenen V15.0.3-Installation

```bash
bash zendure_controller_v16_0_1/tools/install_zendure_controller.sh \
  v16_0_1 --preflight-only
```

Erwartet wird unter anderem:

```text
INSTALL_MODE=SUPPORTED_UPDATE
PREFLIGHT_RESULT=PASS
PRODUCTIVE_CHANGES=NONE
SAFE_TO_INSTALL=yes
```

### Clean Fresh Install

Default-Webport 8080:

```bash
bash zendure_controller_v16_0_1/tools/install_zendure_controller.sh \
  v16_0_1 --fresh-install --preflight-only
```

Alternativer Webport, z. B. 8088:

```bash
bash zendure_controller_v16_0_1/tools/install_zendure_controller.sh \
  v16_0_1 --fresh-install --web-port 8088 --preflight-only
```

Unterstützter Bereich: `1024..65535`. Ein belegter oder nicht bindbarer Port wird vor Produktivmutation abgewiesen. Es erfolgt keine automatische Ersatzportwahl.

Der Preflight ist read-only gegenüber den produktiven ZEC-Dateien, Diensten und der Produktivkonfiguration. Das persistente Installerlog ist ausdrücklich zulässige Diagnoseevidenz.

## 4. Installation

### Unterstütztes Update V15.0.3 -> V16.0.1

Nach erfolgreichem Preflight:

```bash
bash zendure_controller_v16_0_1/tools/install_zendure_controller.sh v16_0_1
```

Der Updatepfad akzeptiert ausschließlich:

- Version `15.0.3`
- Build-ID `v15.0.3-20260911`

Ein anderer, unvollständiger oder widersprüchlicher aktiver Installationszustand wird nicht automatisch als Fresh Install interpretiert.

### Clean Fresh Install

Nach erfolgreichem Fresh-Preflight:

```bash
bash zendure_controller_v16_0_1/tools/install_zendure_controller.sh \
  v16_0_1 --fresh-install
```

oder mit abweichendem Port:

```bash
bash zendure_controller_v16_0_1/tools/install_zendure_controller.sh \
  v16_0_1 --fresh-install --web-port 8088
```

Ein erfolgreicher erster Start endet absichtlich in `FIRST_INSTALL_SETUP`:

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
  --install-report /tmp/zec_v16_0_1_install_report.json \
  --expect-primary-profile modbus_template \
  --output /tmp/ZEC_V16_0_1_FIELD_ACCEPTANCE.json
```

Das Tool ermittelt den lokalen Webendpoint dynamisch, sofern kein expliziter `--base-url` angegeben wird.

Für PRODUCTIVE-PASS von V16.0.1 sind zusätzlich zwingend ein echter Update-Feldtest und mindestens ein echter Clean-Fresh-Install-Feldtest auf einem vorbereiteten Raspberry-Pi-OS-System ohne aktive ZEC-Installation erforderlich. Build-, Harness- und `--preflight-only`-Nachweise ersetzen diesen Realtest nicht.
