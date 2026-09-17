# Zendure Energy Controller V16.0.1

**Build-ID:** `v16.0.1-20260915`

ZEC ist eine lokale Speichersteuerung für einen aktiv gesteuerten Zendure-Speicher – optional koordiniert mit einem Primärspeicher. V16.0.1 stellt den vollständigen Deploymentvertrag für Supported Update, Clean Fresh Install, Uninstall/Fresh-Reset und secretsicheren Support bereit und korrigiert die ausführbare Paketidentitätsprüfung des Installers.

## 1. Produktumfang

- lokale automatische Netzleistungsregelung des Zendure-Speichers;
- optionale Primärspeicherintegration einschließlich direktem Modbus-TCP-Referenzpfad;
- SMA Energy Meter / Sunny Home Manager über Speedwire/UDP sowie Shelly Pro 3EM bzw. Shelly-kompatibles HTTP als unterstützte Netzleistungsmesspfade;
- Graph Core V3, historische Graphen, Inspector, Command-Follow und Episodenvergleich;
- Settings-/Konfigurationsstand-/Diagnosefunktionen;
- Supported Update und Clean Fresh Install mit fail-closed Installationszustandsklassifikation;
- mutationsfreier Installer-/Uninstaller-Preflight;
- lokales User-Data-Backup beim Uninstall/Fresh-Reset;
- secretsicheres Third-Party-Supportbundle ohne rohe `config.json`.

## 2. Deployment

Kanonische Werkzeuge:

```text
tools/install_zendure_controller.sh
tools/uninstall_zendure_controller.sh
```

`tools/update_zendure_controller.sh` bleibt als Kompatibilitätswrapper erhalten. Details einschließlich Fresh-Install- und Preflight-Semantik stehen in `README_INSTALLATION.md`.

## 3. Schutzvertrag

V16.0.1 ändert nicht die fachliche Regelstrategie. AUTO/Harvest/Cross-Charge/NIGHT, aktive Neutralisierung, Command-Effect/Readback/Resync, Primärspeicherpriorität, Measurement-Semantik und Hardware-Schonungslogik bleiben durch die kanonischen Control-&-Safety-Verträge geschützt.

## 4. Dokumentation

```text
README_INSTALLATION.md
RELEASE_INFO_V16_0_1.md
TECHNICAL_NOTES_V16_0_1.md
BUILD_VALIDATION_V16_0_1.md
docs/ZEC_Technisches_Datenblatt.pdf
docs/ZEC_Technisches_Datenblatt.docx
```

Das technische Datenblatt beschreibt ausschließlich den Ist-Zustand des ausgelieferten Releases und enthält keine Versionshistorie.

## 5. Release- und Feldstatus

TECHNICAL BUILD PASS wird erst nach finalem Source-Freeze und vollständigen Fresh-extract-Gates erteilt. Für PRODUCTIVE-PASS von V16.0.1 sind zusätzlich mindestens ein echter Update-Feldtest und ein echter Clean-Fresh-Install-Feldtest auf einem vorbereiteten Raspberry-Pi-OS-System erforderlich.
