# Release-Information V12.11.2-RC10

## Release-Titel

```text
V12.11.2-RC10 – Topologiefähige Statusseite und passiver Live-Preview-Dienst
```

## Basis

```text
Vorgänger: V12.11.2-RC9
Typ:       UI-/Preview-Release
Migration: keine
```

## Geänderte produktive Dateien

```text
version.py
web_ui.py
status_page_v2.py
static/status_v2.js
static/status_v2.css
tools/update_zendure_controller.sh
README.md
README_INSTALLATION.md
```

## Neue Dateien

```text
tools/status_preview.py
tools/status_preview_scenarios.py
tools/STATUS_PREVIEW_README.md
systemd/zendure-status-preview.service
tests/test_v12_11_2_rc10_status_preview.py
TECHNICAL_NOTES_V12_11_2_RC10.md
RELEASE_INFO_V12_11_2_RC10.md
```

Historische Regressionstests wurden ausschließlich auf den aktuellen Versionsmarker RC10 nachgeführt.

## Unveränderte Kernbereiche

Insbesondere unverändert:

```text
controller_logic.py
state.py
mqtt_bridge.py
cross_charge.py
config_manager.py
csv_logger.py
measurement.py
measurement_db.py
measurement_v4.py
measurement_v4_contract.py
operational_events.py
```

## Verifikation

Vorgesehen beziehungsweise im finalen Paket ausgeführt:

```bash
python3 -m py_compile *.py tools/*.py
node --check static/status_v2.js
bash -n tools/update_zendure_controller.sh
python3 -m unittest discover -s tests -q
```

Testergebnis: `Ran 362 tests` → `OK`. Zusätzlich wurden beide Preview-Szenarien über echte HTTP-Aufrufe gegen den separaten FastAPI-Dienst geprüft (`PREVIEW_HTTP_OK`). Unter Python 3.13 erscheinen weiterhin die bereits bekannten `ResourceWarning`-Hinweise aus älteren SQLite-Tests; sie verursachen keine Testfehler.

## Installation

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc10
```

## Preview-Verifikation

```bash
sudo systemctl start zendure-status-preview.service
curl -fsS http://127.0.0.1:8091/health | python3 -m json.tool
```

Browser:

```text
http://192.168.0.40:8091/
```

Nach Abschluss:

```bash
sudo systemctl stop zendure-status-preview.service
```
