# Installation - Zendure Energy Controller V17.1.3

**Release:** `V17.1.3`  
**Build-ID:** `v17.1.3-20261022`

V17.1.3 uses the established fail-closed deployment path for a strictly supported update or a clean fresh install.

**Produktumfang:** V17.1.3 lässt den Reglerkern und alle Safety-Pfade byteidentisch. Alle 190 Settings-Hilfen und 74 Bereichstexte besitzen einen dokumentierten technischen Quellenvertrag; die fachliche Verständlichkeitsabnahme bleibt ein getrenntes Qualitätsgate; 60 Minuten werden einheitlich in einer Minutenkurve mit getrennt erhaltenen Rohwerten dargestellt. Die Netzquellen-/Freshness-Zeile bleibt auch mobil sichtbar. Die 5- und 15-Minuten-Kurven enthalten unveränderte Einzelmesswerte. All safety, export-capture, command and recovery limits remain in force. The optional S3 season policy is disabled by default. The normal installer performs the complete internal preflight before any productive mutation. The preflight verifies the canonical machine-readable build evidence `validation/V17_1_3_BUILD_EVIDENCE.json`.

## 1. Requirements

The ZEC installer is not an operating-system bootstrapper. It expects Raspberry Pi OS/Linux with `systemd`, user/group `pi`, `/home/pi`, working `sudo`, Python 3 with the ZEC runtime dependencies and the system tools checked by the preflight. Missing dependencies are reported before productive mutation and are not installed automatically. A local `mosquitto.service` is not required; the configured MQTT broker must be reachable for normal controller operation.

## 2. Prepare package

Übertrage **nur** `zendure_controller_v17_1_3.zip` nach `/home/pi/Downloads`. Für die automatische SHA256-Prüfung verwende den mit dem Release bereitgestellten vollständigen Installationsbefehl mit der dort direkt eingetragenen Prüfsumme. Eine zusätzliche SHA256-Datei muss nicht auf den Pi übertragen werden. Der in diesem ZIP enthaltene Text kann die Prüfsumme des ZIPs selbst nicht enthalten.

## 3. Reguläres Update V17.1.2 → V17.1.3

The standard real update is deliberately combined: SHA/ZIP check -> fresh extract -> normal installer. The installer executes its full internal preflight and proceeds only when it reports `PREFLIGHT_RESULT=PASS` and `SAFE_TO_INSTALL=yes`. A separate `--preflight-only` run is reserved for intentional mutation-free diagnosis/contract verification.

```bash
set -euo pipefail
cd /home/pi/Downloads
ZIP="zendure_controller_v17_1_3.zip"
# SHA256 des ZIPs vor Installation mit dem veröffentlichten Releasewert vergleichen.
# Der externe Installationsbefehl enthält dafür den exakten erwarteten SHA256.
sha256sum "$ZIP"
unzip -t "$ZIP"
rm -rf zendure_controller_v17_1_3
unzip -q "$ZIP"
bash zendure_controller_v17_1_3/tools/install_zendure_controller.sh v17_1_3
```

The supported update source is exclusively:

- Version `17.1.2`
- Build-ID `v17.1.2-20261021`

The successful installer writes a timestamped machine-readable report under `/home/pi/Downloads/zec_v17_1_3_install_report_<STAMP>.json`; `/tmp/zec_v17_1_3_install_report.json` remains the compatibility copy.

## 4. Clean Fresh Install – nur auf einem separaten sauberen System

Nur auf einem tatsächlich sauberen System ohne aktive ZEC-Installation. `--fresh-install` ist **zwingend** und verhindert eine unbeabsichtigte Umdeutung eines normalen Updateversuchs zur Neuinstallation. Der produktive Raspberry Pi wird für diesen Test nicht zurückgesetzt.

Mutationsfreier diagnostischer Preflight:

```bash
bash zendure_controller_v17_1_3/tools/install_zendure_controller.sh \
  v17_1_3 --fresh-install --preflight-only
```

Normal fresh install on port 8080:

```bash
bash zendure_controller_v17_1_3/tools/install_zendure_controller.sh \
  v17_1_3 --fresh-install
```

Alternative web port, for example 8088:

```bash
bash zendure_controller_v17_1_3/tools/install_zendure_controller.sh \
  v17_1_3 --fresh-install --web-port 8088
```

The supported port range is `1024..65535`. A clean fresh install intentionally enters `FIRST_INSTALL_SETUP` until the first valid Settings commit; during that state `/health` is alive, Settings are reachable, control is blocked and `/ready` remains false.

## 5. Uninstaller / fresh-install reset

The canonical uninstaller remains `tools/uninstall_zendure_controller.sh`. Its mutation-free preflight and default user-data backup contracts are unchanged. It removes only ZEC-owned active artifacts and never removes the operating system, network configuration, MQTT broker, EVCC or general system/Python packages.

## 6. Immediate post-update field acceptance

After an update or fully configured normal start:

```bash
cd /opt/zendure-controller
python3 tools/v17_field_acceptance.py \
  --expect-primary-profile modbus_template \
  --output /home/pi/Downloads/ZEC_V17_1_3_FIELD_ACCEPTANCE.json
```

This validates release identity, service/readiness, installer/rollback evidence, the Fast-Capture setting/runtime/Measurement contract and compatibility of the read-only Fast analyzer. It does **not** require a naturally occurring Fast episode immediately after installation.

## 7. Fast Capture rollout

The safe release default remains:

```text
HARVEST_FAST_CAPTURE_MODE=off
```

Fast Capture behält beim Update den bisherigen gespeicherten Modus; der Installer schaltet ihn nicht automatisch um. Falls eine gesonderte Shadow-Auswertung fachlich gewünscht wird, erfolgt der Wechsel ausschließlich über den regulären Settings-Preview-/Commit-Ablauf. Natürliche Episoden können danach read-only analysiert werden:

```bash
cd /opt/zendure-controller
python3 tools/fast_capture_field_analysis.py --help
```

The analyzer reports `PASS`, `FAIL`, `WARN` or `NOT_EVALUABLE`. Missing natural episodes are `NOT_EVALUABLE`; they are never manufactured or counted as PASS. Eine neue, noch nicht abgesprochene Erprobung mit „Aktiv“ erfordert eine ausdrückliche Freigabe. Eine bereits bestehende und bewusst freigegebene Einstellung wird durch dieses Update nicht automatisch verändert.

## 8. Technical build versus productive evidence

TECHNICAL BUILD PASS confirms build/package integrity and the required regressions. It is not the real Fast-Capture field validation. The project-wide PRODUCTIVE-PASS also remains limited while the separately deferred real clean-fresh/FIRST_INSTALL_SETUP/uninstaller evidence item is open.

## V17.1.3 S3 and live-status safety

Season selection is opt-in only: `HARVEST_SEASON_POLICY_ENABLED=false` remains the default. No upgrade auto-enables an old stored `HARVEST_SEASON_MODE`. Use Settings draft → preview → confirm to enable seasonal strategy after verifying the daily/calendar policy. `calendar` requires two valid inclusive recurring MM-DD boundaries. Export Capture, Fast Capture, MIN/MAX_SOC and device/command protection remain authoritative.

The status screen requests source snapshots every second while visible; data timestamps, age and freshness remain independent of display polling. No promise is made that a sensor itself produces a new sample every second. The regulation cycle is unchanged. A `GRID_STALE` operational event can open or resolve with independent hysteresis and must not be interpreted as a control command.

This README documents intended installation only. Real field acceptance including physical command effect remains a separate step after the successful technical release gate.

## V17.1.3 – UI-Qualitätsrelease

Die zentrale Regelung und Zendure-Kommandos bleiben gegenüber der realen V17.1.1-Ausgangsbasis unverändert. Die Settings-Hilfe erklärt Wirkungen und Vorrangbedingungen nun für alle operativen Einstellungen, und der zeitgetreue Netzleistungs-Minigraph aktualisiert sich alle 3 s (5/15/60 min), getrennt von der 1-Hz-Livezahl. Die 60-Minuten-Historie verwendet Graph-V3 in begrenzter read-only 1-Minuten-Auflösung; bei fehlenden historischen Daten wird die Lücke offen ausgewiesen.

## UML-Regleratlas

Die editierbaren Reglerdiagramme und die offline lesbaren SVG-/PNG-Ansichten stehen unter [`docs/architecture/uml/INDEX.md`](docs/architecture/uml/INDEX.md). Die Atlas-Abnahme ist an `DOC_UML_RELEASE_GATE` gebunden; sie ersetzt keine reale Hardware- oder Strategie-Feldabnahme.
