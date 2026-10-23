# Zendure Energy Controller V17.1.3

**Release:** `V17.1.3` · **Build-ID:** `v17.1.3-20261022`

ZEC ist ein lokaler, sicherheitsüberwachter Energiespeichercontroller für einen aktiv geregelten Zendure-Speicher mit optionaler Primärspeicherintegration. Unterstützte Netzleistungsmessung: SMA Energy Meter / Sunny Home Manager via Speedwire/UDP und Shelly Pro 3EM beziehungsweise kompatible HTTP-Messpunkte. Die Primärspeicherprofile `evcc_standard`, `custom` (MQTT) und `modbus_template` (u. a. Sunny Island) bleiben erhalten. Eine zweite Zendure-Einheit kann im Status dargestellt werden; daraus entsteht keine zweite produktive Command-Owner-Konfiguration.

## Änderungen in V17.1.3 – anwendergerechte UI-Korrekturen

- Vollständige fachliche Settings-Hilfe und Bereichs-Zwecktexte (190 operative Einstellungen / 74 Bereiche).
- 3-s-Netzleistungs-Minigraph mit Zeitachse, Gaps, Verlaufswahl 5/15/60 min und transparentem Datenalter.
- Keine Änderung an `controller_logic.py`, Command- oder Safety-Semantik.

## Übernommene V17.1.0-Funktionen

- **S3:** Konfigurierbare Tagesfenster, Bestätigungszeiten und saisonale strategische High-SOC-Policy, ausschließlich nach ausdrücklichem Opt-in; Bestandskonfigurationen ändern ihre Reglerwirkung nicht stillschweigend. Realer Restexport und alle Safety-/Hardwaregrenzen haben Vorrang.
- **Unabhängiger 1-Hz-Livestatus:** Browser aktualisiert die zuletzt wirklich eingegangenen Netz-, Zendure- und Primärspeicherwerte sekündlich, unabhängig vom ungefähr 3-s-Regeltakt. Sensoralter, Validität und Staleness bleiben erkennbar; keine künstliche Messfrequenz oder zusätzliche Commandinstanz.
- **Grid-Stale-Betriebsereignisse:** persistentes Open-/Resolve-Journal mit Entprellung; Source-Stale und Controller-Processing-Stale werden getrennt behandelt.
- **Pflichtfix Nacht/MIN_SOC/Grid:** bei Nachtreserve/Entladebegrenzung kann die gesicherte Grid-Verarbeitung weiterlaufen und zulässiger PV-Export im AUTO-Pfad genutzt werden.
- **Pflichtfix SMA-Speedwire/OBIS:** strukturvalidierende Paket-/Record-Auswertung statt unsicherer globaler Bytefolgensuche; bestehender Netzleistungs-Plausibilitätsfilter bleibt aktiv.
- Status-UI-/Graph-Follow-ups sowie versionierte As-built-/Spezifikations-/ADR-/Historien-Dokumentation in `docs/`.

Das unverändert deterministische Controller-/Command-/Cross-Charge-/Recovery-Konzept bleibt Safety-Owner; die S3-Policy greift nur in bestehende zulässige strategische Harvest-Zweige ein. Adaptive A1/B2/C1 und Battery Care erhalten durch dieses Release keine zusätzliche Produktivregelautorität.

## Installation und Rollback

Die **aktuelle** Installationsanleitung ist [`README_INSTALLATION.md`](README_INSTALLATION.md), identisch mit [`README_INSTALLATION_V17_1_3.md`](README_INSTALLATION_V17_1_3.md). Reguläre Updates sind ausschließlich von `17.1.2 / v17.1.2-20261021` erlaubt. Der kanonische Installer ist `tools/install_zendure_controller.sh`; er prüft Preflight und Backup vor produktiven Änderungen, installiert nur bei bestandenem Gate und rollt bei nachfolgendem Fehler zurück. Fresh Install erfordert ausdrücklich `--fresh-install` und beginnt fail-closed im `FIRST_INSTALL_SETUP`.

## Dokumentation und Qualitätsgrenzen

Aktuelle Architektur, Scope, technische Begrenzungen und Historie: [`docs/INDEX.md`](docs/INDEX.md). Das technische Datenblatt liegt als DOCX und PDF unter `docs/`; die releasebezogene Backlog-Kopie liegt in `docs/ZEC_Master_Backlog.md`, während die externe kanonische Projektquelle `05_ZEC_BACKLOG_AND_ROADMAP.md` alleinige Roadmapautorität bleibt.

**Technische QA und reale Feldabnahme sind getrennt.** Der Build-Evidence-Vertrag liegt in `validation/V17_1_3_BUILD_EVIDENCE.json`; realer Pi-Rollout, Browser-/Hardwarelast, physische Wirkung und Produktiv-Wiederherstellung sind erst nach der separaten Feldabnahme bestätigt. Die zuletzt real allgemein feldabgenommene Version ist V17.1.2; V17.1.3 ist bis zur gesonderten Installation und Feldabnahme ein technischer Releasekandidat.


### Technische Architektur und UML-Regleratlas

Der [offline nutzbare UML-Regleratlas](docs/architecture/uml/INDEX.md) enthält 22 quellgeprüfte Regeldiagramme mit editierbaren DOT-Dateien sowie SVG-/PNG-Abbildungen. [Source- und Visualreview](docs/architecture/uml/SOURCE_REVIEW_V17_1_3.md) und `DOC_UML_RELEASE_GATE` sind in die bestehende Architekturprüfung integriert; Diagrammprüfung ersetzt keine Pi-Feldevidenz.
