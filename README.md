# Zendure Energy Controller V16.1.0

**Build-ID:** `v16.1.0-20260919`

ZEC ist eine lokale Speichersteuerung für einen aktiv gesteuerten Zendure-Speicher – optional koordiniert mit einem Primärspeicher. V16.1.0 erweitert den direkten SMA-Sunny-Island-Pfad um eine read-only Geräte-Capability für die aktuell wirksame untere Entladegrenze und macht daraus zusätzliche Diagnoseevidenz, ohne die Live-Regelstrategie zu verändern.

## 1. Produktumfang

- lokale automatische Netzleistungsregelung des Zendure-Speichers;
- optionale Primärspeicherintegration einschließlich direktem Modbus-TCP-Referenzpfad;
- beim Geräteprofil SMA Sunny Island: read-only Capability `current_discharge_floor_soc` aus Register `31009`, separate Freshness/Validity und diagnostischer normalisierter nutzbarer Primär-SOC;
- **keine Reglerwirkung** durch Floor oder usable SOC in V16.1.0;
- SMA Energy Meter / Sunny Home Manager über Speedwire/UDP sowie Shelly Pro 3EM bzw. Shelly-kompatibles HTTP als unterstützte Netzleistungsmesspfade;
- Graph Core V3, historische Graphen, Inspector, Command-Follow und Episodenvergleich;
- Settings-/Konfigurationsstand-/Diagnosefunktionen;
- Supported Update und Clean Fresh Install mit fail-closed Installationszustandsklassifikation;
- mutationsfreier Installer-/Uninstaller-Preflight;
- lokales User-Data-Backup beim Uninstall/Fresh-Reset;
- secretsicheres Third-Party-Supportbundle ohne rohe `config.json`.

## 2. Primärspeicher-Capability in V16.1.0

Das Sunny-Island-Template liest zusätzlich Register `31009` (`Lower discharge limit for self-consumption range in %`) per Modbus FC03/U32. Fehler dieser optionalen Capability degradieren nicht automatisch den bestehenden Pflichtpfad aus Leistung und Roh-SOC. Ein alter Capability-Wert wird bei Quellen-/Profilwechsel invalidiert und besitzt eine eigene Freshness-/Validity-Semantik.

Aus Roh-SOC und frischem Floor kann ZEC diagnostisch den auf den aktuell freigegebenen Entladebereich normierten `primary_usable_soc_percent` ausweisen. Diese Größe ist in Status/API/Readiness-Diagnose und Measurement V4 sichtbar, wird in V16.1.0 aber nicht vom Regler verwendet.

Generische Settings-/Help-Bezeichnungen verwenden „Primärspeicher“. Legacy-Konfigurationskeys bleiben kompatibel. Der New-Install-Default von `SECOND_BATTERY_DISPLAY_NAME` ist leer; explizit persistierte Nutzernamen werden nicht überschrieben.

## 3. Deployment

Kanonische Werkzeuge:

```text
tools/install_zendure_controller.sh
tools/uninstall_zendure_controller.sh
```

`tools/update_zendure_controller.sh` bleibt als Kompatibilitätswrapper erhalten. Details einschließlich Fresh-Install- und Preflight-Semantik stehen in `README_INSTALLATION.md`.

## 4. Schutzvertrag

Der geschützte Reglerkern `controller_logic.py` bleibt gegenüber V16.0.2 byteidentisch mit SHA256 `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`. AUTO/Harvest/Cross-Charge/NIGHT, aktive Neutralisierung, Command-Effect/Readback/Resync, Primärspeicherpriorität und Hardware-Schonungslogik werden durch Block A nicht verändert.

## 5. Dokumentation

```text
README_INSTALLATION.md
RELEASE_INFO_V16_1_0.md
TECHNICAL_NOTES_V16_1_0.md
BUILD_VALIDATION_V16_1_0.md
docs/ZEC_Master_Backlog.md
docs/ZEC_Technisches_Datenblatt.pdf
docs/ZEC_Technisches_Datenblatt.docx
```

Das technische Datenblatt beschreibt ausschließlich den Ist-Zustand des ausgelieferten Releases. Das Master-Backlog enthält auch offene Folgeblöcke; insbesondere bleibt die strategische usable-SOC-Integration (Block B) ausdrücklich außerhalb von V16.1.0 erhalten.
