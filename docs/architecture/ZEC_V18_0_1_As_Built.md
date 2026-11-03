# ZEC V18.0.1 – Sourcegebundenes As-built (Korrekturreleasedesign)

**Softwareidentität:** V18.0.1 / `v18.0.1-20261102`. Baseline: veröffentlichtes V18.0.0 / `v18.0.0-20261027`. Das Dokument beschreibt die im Kandidaten vorhandenen Sources, nicht eine bereits installierte V18.0.1-Runtime.

## Architektur und unterstützte Pfade

- **Regelung:** `controller_logic.py::run_once` zyklisch typischerweise ca. 3 s; Source-/Controller-Frische sind getrennte Konzepte. STOP, Safety/Readiness, erforderliche SOC/Grid-Telemetrie, Cross-Charge und einziger Command-Owner behalten Vorrang. `MIN_SOC` und die aktive individuelle Battery-Care-Reserve R begrenzen Entladung; PV-Exportaufladung bleibt bei frischen Messungen möglich.
- **Messpfad:** SMA Energy Meter/SHM über Speedwire/OBIS (robuster Parser) oder Shelly-kompatibler HTTP-Messpfad. Primärspeicher via `evcc_standard`, `custom` MQTT oder `modbus_template` (SMA Sunny Island); SOC-/Capability-Validität unabhängig. `primary_usable_soc_percent` ist Diagnostik, keine alternative Controller-SOC-Autorität.
- **S3:** `HARVEST_SEASON_POLICY_ENABLED` opt-in; requested/effective/applicability werden getrennt ausgewiesen. Strategische Shares sind dem realen Export-Capture-Floor nachgeordnet. Fast Capture bleibt ein eigenes B+Overlay-System und darf PV nicht doppelt zu Battery-Care-Care-PV zählen.
- **UI:** `/status-live-data` Browserpoll alle **1000-ms**, `/grid-mini-data` Browserpoll 3000 ms (nicht identisch mit neuer Sensorprobe); Controller hält eigene Zeitstempel und Sources. Statuskarten/Graphen sind rein lesend. Standard- und Expertenmodus unterliegen Superset-Vertrag.
- **Settings:** `SettingsRegistry` bleibt Typ-/Default-/Freigabeautorität; Preview/Commit, atomisches Persistenzverhalten und Secretschutz unverändert. Der neue Anzeigeparameter `SECOND_BATTERY_DISPLAY_MAX_SOC_PERCENT` startet mit 100 % und begrenzt ausschließlich die Darstellung von Primärspeicher-Laderaum, niemals Hardware-/BMS-/Steuergrenzen. Saisonfelder werden im Browser als `TT.MM.` dargestellt und ans Backend weiterhin als `MM-DD` übergeben.

## Korrekturpaket V18.0.1

1. **SOC-Stale-Recovery Nacht/Reserve:** Bei SOC-Stale ist SAFE_STATE mit neutralisierter Batterie korrekt. Nach Frische-Recovery und erreichtem Care-R darf der bisherige frühe Night-/Import-Return einen alten SAFE_STATE nicht festhalten. V18.0.1 setzt den Modus ausschließlich bei frischem SOC/Netz, neutralen Desired/Readback, gültiger unabhängiger 0-W-Istleistung und nicht aktivem Neutralisierungszyklus auf HOLD; bei Unsicherheit bleibt er SAFE. **Keine** zusätzliche Entladefreigabe, kein zweiter Gerätetarget-Publisher.
2. **Settings-Lade-Resilienz:** `static/settings_v2.js` validiert Modellstruktur und Antwortstatus vor Verwendung, begrenzt transienten Retry und zeigt „Erneut laden“ statt eines JavaScript-Exceptions. Fehlerzustände dürfen kein Settings-Commit auslösen.
3. **Battery-Care-Saison und Status:** Lokalisierte Eingabe bei identischem Speicherformat; Shield „Battery Care · Schutz aktiv“ mit Prioritäts-/Sonderzuständen und bestehendem Karten-Info-Dialog. SOC-Tagesgraph nennt `NIGHT_DISCHARGE_STOP_SOC_PERCENT` „Nachtreserve“, nicht Battery-Care-R.
4. **Reserve-Journal:** `operational_events.py::_observe_care_reserve_reached` persistiert einen gedrosselten Episodeneintritt unter Care R und unterscheidet angeforderte 0-W-Begrenzung von späterem validem Readback/0-W-Istbestätigungsereignis. Eventjournal ist Diagnoseebene, ändert nie den Commandpfad.
5. **PV-Care:** `battery_care_pv_allocation.py`/Care-Stage-Quelle bleiben unverändert. Die Realfolge 02.11. mit häufigen Stage- und `input_limit`-Änderungen war an AUTO/HOLD gekoppelt. Differentialtests fanden keinen eigenständigen Fehler, die physische Kausalmehrladung ist nicht bewiesen.
6. **7D-Analyzer:** `tools/zec_battery_care_7d_readonly.py` schreibt ausschließlich ein externes Diagnosearchiv, nicht Config/Controller. Zeitbezogene V4-Dateierfassung, begrenzter Speicher/IO, SQLite-Core-Nutzdatenvalidation mit V4-Fallback; fehlende Werte sind `NOT_EVALUABLE`, nicht 0 Wh.

## Evidenz- und Freigabegrenzen

Es gibt 2 natürliche 0-W-Reserve-Neutralisierungen, PV-Care positive AC-Gesamtfensterladung aber keinen kausal gemessenen Zusatzgewinn, und keine natürliche N-/E-Episode. Vor einem technischen Release sind finaler Source-/Paket-Manifest, vollständige QA regulär+`ResourceWarning=error`, aktuelles Datenblatt DOCX/PDF und 22/22 UML-Review, zuverlässige Install-/Rollback-/Fresh-Extract-Gates zwingend. `TECHNICAL_BUILD_PASS` ist kein Pi-Feld-PASS. Die zuvor freigegebene V18.0.0 und deren SHA256 bleiben unverändert.

**Verweise:** `docs/architecture/uml/INDEX.md`; `docs/architecture/uml/SOURCE_REVIEW_V18_0_1_20261102.md`; `docs/releases/v18.0.1/`; `docs/ZEC_Master_Backlog.md` (nicht-kanonischer Release-Snapshot).
