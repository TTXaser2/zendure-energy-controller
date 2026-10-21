# ZEC V17.1.2 – Sourcebasierte As-built-Architektur

**Produktbasis:** verifiziertes, unverändertes V17.1.1-Release; V17.1.2 ist ein strikt UI-/Dokumentations-/Installer-bezogener Korrekturscope. **Status:** Entwicklungsstand, QA und Pi-Feldbelege gesondert; kein impliziter Productive-PASS.

## Unveränderte Steuer- und Sicherheitsautorität

Der bestehende quellenbasierte Live-Status-Poll bleibt bei **1000-ms** unabhängig vom Controller, die SMA-Speedwire-**OBIS**-Validierung und **MIN_SOC**-Schutzpfade bleiben unverändert.

`controller_logic.py` bleibt SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7`. Reglerzyklus, ZEC-Basiswertbildung, SmartMode/AC-Mode/Commandpublisher, Cross-Charge, Export Capture, Fast Capture, S3, Grid-Sensorverträge, SOC-Guards und Recovery sind **nicht geändert**. Fast-Capture-Anstieg A400: maximal +400 W pro tatsächlicher Sekunde frischer Beobachtungszeit, kontrollierter Abbau R100: 100 W/s, ausschließlich als zulässiger positiver Overlay `B+O`, wobei `B` den normal geglätteten und durch `MAX_POWER_STEP_W` pro Reglerzyklus begrenzten Basiswert bezeichnet. Die Rate garantiert keinen Nettoanstieg, physische Limits und Safety bleiben höherrangig.

## Änderungen und Source-Mapping

- `settings_help.py` und `settings_help_v1712.py`: für alle 190 operativen Registry-Settings explizite Anwendbarkeits- und Vorrangtexte; bestehende 74 Bereichseinführungen bleiben aktive UI-Bestandteile; User-Help ist keine neue Default- oder Steuerautorität.
- `web_ui.py::build_grid_mini_payload`: 5-/15-Minuten-Rohdatenserien, 60-Minuten-Minutenaggregation und begrenzte Originalsamples mit Zeitstempeln, Lücken, Min/Max, Validität und Abdeckung; Quellen aus der bestehenden read-only `graph_history`/Graph-V3-Datenbasis. Ohne rechnerische Interpolation und ohne zusätzlichen Sensortakt.
- `static/status_v2.js`: semantisch ehrliche 5-/15-/60-Minuten-Legenden und 60-Minuten-Tooltips, Live-Zahl separat 1-s-Abfrage; Verlauf-UI-Poll 3 s. `static/status_v2.css`: Gridkarte darf auf schmalen Screens vertikal mitwachsen; Freshness- und Providerinfo darf nicht durch feste Kartenhöhe verschwinden.
- `tools/install_zendure_controller.sh`: ausschließlich V17.1.1-Identität für unterstütztes Update; ausdrücklich markierter `--fresh-install` für saubere Erstinstallation, fail-closed Preflight, Nachkontrolle und Rollback. Dokumentation verwendet externe, nach Paketfreeze generierte SHA256-Datei. Kein Systembootstrapper; kein destruktiver Test am Produktiv-Pi.
- Dokumentation: `docs/releases/v17.1.2` enthält drei releasegebundene Übersichten, `docs/history/` historisches, jeweils provenance-markiertes Material. Dieses As-built ersetzt nicht ältere Originale oder deren Nachweisgrenzen.

## Differenzielle technische Abnahme

Source-Identität, Eingangsmanifest, Settings-Help-Vollständigkeit, Minigraph-/Zeitsemantik, responsive Screens 320/375/390/430 und Desktop, Accessibility, Fokustests, Vollregression + ResourceWarning, Build-Evidence, SHA/CRC/Source-Manifest, Fresh-extract, kontrollierte Installationssimulatoren, Datenblatt DOCX/PDF und `BACKLOG_NO_DROP_GATE` sind eigenständige Gates. Ein Paket-PASS ist kein Pi-Feld-PASS; natürliche Realwirkungen von S3/Stale/Fast FULL_IDLE und echter Clean Fresh Install bleiben jeweils evidenzabhängig.

**Vorversion:** [V17.1.1 As-built](ZEC_V17_1_1_As_Built.md) belegt den eingefrorenen Produktvorläufer, nicht eine Freigabe für V17.1.2.
