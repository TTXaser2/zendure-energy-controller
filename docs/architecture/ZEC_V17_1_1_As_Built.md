# ZEC V17.1.1 – As-built-Architektur und Safety-Mapping

**Releaseidentität:** V17.1.1 · `v17.1.1-20261020`. **Stand:** 20.10.2026. **Nachweisstand:** technische Sourcebasis; Feldwirkung und abschließende QA separat. **Dies ist kein V17.1.1-Feld-PASS.**

## Steuerungsdatenfluss und Safety-Owner

1. Datenaufnahme: SMA-Speedwire-UDP-Empfänger (`sma_energy_meter.py`), alternativ Shelly-kompatibler HTTP-Pfad; Zendure-MQTT und Primärspeicher-Modbus-/MQTT-Collector liefern unabhängig gepflegte Daten an `ControllerState` (`state.py`).
2. `controller_logic.py` hält alleinige Regler- und Zendure-Commandautorität. Netzleistungsfilter, Primärpriorität, exportseitiger Aufnahme-Floor, SOC-/MIN/MAX-, Cross-Charge- und Command-Resync-/Recovery-Schutz sind höher priorisiert als Zeit-/Saisonstrategien. Der Regeltakt wird nicht durch die UI verändert.
3. S3-Tagesprofil und optionaler Saisonmodus (`controller_logic.py::_harvest_time_profile`, `_s3_season_policy`) bestimmen ausschließlich den strategischen High-SOC-Share-Zweig; `HARVEST_SEASON_POLICY_ENABLED=false` bleibt wirksamkeitsneutraler Default. Frühere, gespeicherte `sma_priority`-Werte erzeugen kein implizites Opt-in. In `calendar` entscheidet das inklusive zyklische MM-DD-Intervall.
4. `sma_energy_meter.py` validiert Speedwire-Header, Data2-Länge, Tag und Protokoll, Geräteselektion und die 4-/8-Byte-OBIS-Recordgrenzen; im Control-Pfad bleibt der 30-kW-Plausibilitätsschutz unabhängig aktiv.
5. Nacht-`MIN_SOC` neutralisiert Entladeanforderung, führt aber die Grid-Aufnahme und zulässige Export-Ladeprüfung weiterhin aus. Ohne valide Netzmessung wird nicht fiktiv weitergeladen (`tests/test_v17_nextrelease_night_min_soc_grid.py`).
6. `live_status.py`, `live_shelly_sampler.py`, `web_ui.py` `/status-live-data` und `static/status_v2.js` liefern getrennten UI-Refresh im 1000-ms-Takt bei sichtbarem Browser-Tab. Browser-Abrufrate ist nicht gleich Sensor-Samplingrate. Quelle, Sensoralter, Validity und Freshness stammen aus den unabhängigen Empfangs-/Collectorpfaden; bei stale/invalid kein Frischwert, keine zusätzliche Commandautorität.
7. `operational_events.py` beobachtet Grid-Staleness im unabhängigen Eventjournal mit Open-/Resolve-Hysterese, ohne Flooding oder Rückkopplung in den Regler. Quelle/Verarbeitungsdiagnose werden separat ausgewiesen, auch wenn überhaupt kein Initialsample eintrifft.

## UI-, Settings- und Evidenzverträge

- `settings_registry.py` ist Produkt-/Default-Autorität, `settings_validation.py` blockiert nicht monotone Tagesgrenzen und bei aktivem `calendar` invalide/MM-DD-29.02.-Grenzen. Draft, Preview und CAS/Commit bleiben in `web_ui.py` getrennt.
- `state.py`, `measurement_v4.py` und `measurement_v4_contract.py` liefern additive S3-Evidenz (`harvest_season_requested`, `harvest_season_effective`, `harvest_profile_confirm_s`, `harvest_s3_applicability`, `harvest_s3_override_reason`). Mögliche Anwendbarkeit: `NOT_APPLICABLE`, `APPLIED` **nur im strategischen Rechenzweig**, `OVERRIDDEN` mit Export-Capture-/Saisonbegründung. Ein berechnetes Ziel ist kein physikalischer Wirkungsnachweis; der finale Sollwert wird getrennt angezeigt.
- Aktuelle V4 Standard-/Extended-Header enthalten 278/281 Spalten; historische RC17/RC16/RC15-Header bleiben 238/228/217. Historische archivierte V17.0.2-Messungen werden nicht umgeschrieben.
- Graph-Evidence-Gap: `static/graph_v14_1.js` verhindert Nearest-Value im bestätigten Gap und stellt Gap-Inspector dar. Statuskarten-Warning-Chip mit Desktop-Popover / Mobile Panel: `static/status_v2.js`, `static/status_v2.css`.

## Abnahmegrenzen / Verweise

- Neue Tests: `tests/test_v17_nextrelease_sma_structured_parser.py`, `tests/test_v17_nextrelease_night_min_soc_grid.py`, `tests/test_v17_nextrelease_live_validity.py`, `tests/test_v17_nextrelease_s3_diagnostics.py`, `tests/test_v17_nextrelease_grid_never_received_event.py` plus bestehende Tests.
- Real-Pi-Last, Browser-/Mobilgerät, physische Lade-/Entladewirkung, Wiederherstellung und realer Installationslauf sind **nur durch nachgelagerte Feldevidenz** nachweisbar. Dieses Dokument behauptet diese Nachweise nicht.
- Normativ: `01_ZEC_PROJECT_RULES.md`, `03_ZEC_CONTROL_AND_SAFETY_INVARIANTS.md`, `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md`; Source-Release-Snapshot im `docs/ZEC_Master_Backlog.md`. Projekt-Roadmapautorität ist außerhalb des Releasebaums ausschließlich kanonische `05_ZEC_BACKLOG_AND_ROADMAP.md`.

## V17.1.1 – differenzielle UI-As-built-Änderungen

- `settings_help.py` und `settings_registry.py`: 190 operative Felder mit eigenen Endanwender-Wirkungstexten inklusive Aktivierungs- und Vorrangverträgen, 74 dauerhaft erklärte Bereiche. Textänderungen sind keine Control-Semantik. Fallback-Phrasen nicht als fertige Help-Kompletion ausgeben.
- `web_ui.py::/grid-mini-data`: getrenntes Zeitfenster `window_minutes=5|15|60`, Zeitachse auf `epoch_s`/`epoch_ms`, begrenzter RAM-Read; für 60 Minuten optional begrenzte read-only Graph-V3-Historie mit Cache-Mindestabstand 15 s, ohne Regel-/Command-/Sensorpolling. Fehlende Proben, Zeitlücken und unvollständige Deckung werden ehrlich angezeigt.
- `static/status_v2.js`, `static/status_v2.css`, `status_page_v2.py`: 3-s-Chart-Poll, 5/15/60-Minuten-Buttons, getrennte 1-s-Livezahl, mobile/Touch-/Keyboard-Reichweite. 1-min-Historie ist keine 1-Hz-Messung.
- Zwischenversionen: `docs/architecture/ZEC_V17_1_0_As_Built.md` bleibt unveränderte Provenienz für das freigegebene V17.1.0. Der Controller-Regelkern hat gegenüber dem veröffentlichten V17.1.0 **keine Codeänderung**. Reale Pi-UX/Performance und Update bleiben nachgelagerte Feldevidenz.
