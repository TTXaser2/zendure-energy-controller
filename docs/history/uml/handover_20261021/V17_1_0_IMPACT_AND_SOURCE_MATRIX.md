# UML-Migrationsmatrix – Altatlas V0.4 (V17.0.2) → aktiver V17.1.0-Sourcevertrag

**Status:** verbindliche Prüfliste, **kein** schon abgeschlossener Diagramm-Diff. Datum 21.10.2026.

Die 19 früher erstellten Diagramme bilden die anfängliche Mindestabdeckung, keine ewige Maximalzahl. Vor Übernahme **Originalatlas ZIP wiederbeschaffen/prüfen**. Dann für jedes Diagramm tatsächlichen `.dot`-/`.puml`-Quelltext und reale V17.1.0-Implementierung vergleichen. Die früher genannten Titel/ID-Nummern sind Provenienz aus dem UML-Chat, kein Nachweis einer bereits durchgeführten V17.1.0-Übernahme.

| Nr. | Altatlas / Gegenstand | V17.1.0-Pflichtprüfung und ggf. Korrektur | Schwerpunkt / Quellen |
|---:|---|---|---|
| 01 | Controller State Machine | `current_mode` echt; S3/Strategic Share/Grid-Stale als orthogonale Gründe/Ebenen, nicht als neue Hauptmodi | `controller_logic.py`, `state.py` |
| 02 | Control Cycle Activity | `run_once`-Dispatch neu prüfen; NIGHT + MIN_SOC darf Grid-Verarbeitung für zulässigen Export nicht ungewollt abbrechen | `controller_logic.py`, NIGHT-Fix-Tests |
| 03 | Charge Target Pipeline | S3-Zeitprofil + opt-in Saisonpolicy vor Harvest-Share; Export-Capture-Floor; Fast Baseline `B` + Overlay `O`; Command-/Cross-Charge-Gates | `_harvest_time_profile`, `_s3_season_policy`, `handle_charge`, Fast-Capture-Tests |
| 04 | Harvest State Machine | Tagesprofil-Confirm aus wirksamer Runtimekonfiguration statt hardcoded-only; distinct/fresh/monotonic; Saison-Effekt vs. Eligibility | `controller_logic.py`, S3-Tests |
| 05 | Fast Capture State Machine | Quelle revalidieren; Eigenständigkeit `FULL_IDLE`/`NEAR_LIMIT`, Shadow/Active/Evidence beibehalten; Releasebezeichnung konsistent „Fast Capture“ | `controller_logic.py`, `state.py`, Fast-Tests |
| 06 | Cross-Charge Activity | symmetrische physische Gegenflusskorrektur, keine automatische 0-W-HOLD-Behauptung; S3/Fast-Overlay darf nicht überstimmen | `controller_logic.py`, Cross-Charge-Tests |
| 07 | Command Lifecycle Sequence | Publish, Readback, Effekt, Resync physisch getrennt; neue GRID/S3-Felder bedeuten keine zweite Commandautorität | `command_lifecycle.py`, `controller_logic.py` |
| 08 | Command Effect & Recovery | Kategorien und Recovery aus Quelle prüfen; keine aus Oktober-Rohdaten unbelegten Hardwareursachen oder Wirkungs-PASS behaupten | `command_lifecycle.py`, `measurement.py`, Command-Episodenevidenz |
| 09 | Component Map | `live_status.py`, `live_shelly_sampler.py`, `/status-live-data` (UI 1 s), `operational_events.py`, SMA-OBIS-Parser, bestehendes Systemmapping ergänzen | As-built V17.1.0, `web_ui.py`, `state.py` |
| 10 | Discharge / Night / Manual | Nachtreserve & MIN_SOC nicht als pauschales Grid-Blindness-STOP; 0-W-Neutralisierung und anschließenden Grid-/AUTO-Pfad korrekt | `controller_logic.py`, NIGHT/MIN_SOC-Tests |
| 11 | AUTO Grid Export Target Math | nach NIGHT-/MIN_SOC-Fix korrekt erreichbare Exportverarbeitung; Delta-vs.-Absolut weiterhin sauber | `handle_charge`, `run_once` |
| 12 | AUTO Grid Import Target Math | SOC-Limits, Readiness, Entladeberechnung und Recovery-Nichteffekt unverändert oder gemäss Code aktualisiert | `handle_discharge` |
| 13 | FULL/IDLE Deep Dive | Harvest-`SMA_FULL_OR_IDLE` nicht als Fast-Capture-`FULL_IDLE` bezeichnen; absoluter Zielwert | Harvest-/Fast-Pfade |
| 14 | NEAR_LIMIT Power Balance | `STRATEGIC_SHARE`, `EXPORT_CAPTURE`, `BOTH_EQUAL`, floor/primary target math; bei opt-in `sma_priority` strategischen Share nicht fälschlich aktiv markieren | Harvest Share/S3-Code |
| 15 | Priority & Override Layers | echte Arbitration statt scheinbar lineare Totalordnung; S3 ist nur strategischer Kontext, Safety und Capture-Floor bleiben maßgeblich | invariants/ctrl/S3 |
| 16 | Timing & Hysteresis | **nicht mehr nur feste Uhrzeiten**; konfigurierbare S3-Tagesgrenzen, Entry Confirm, frische Beobachtungen, DST/Restart, Fast A400/R100 | S3-Settings/Tests, Fast-Code |
| 17 | Regelzyklus unter dem Mikroskop | illustrative Zahlen bleiben Illustration; S3 Legacy/opt-in Ausgangslage in Szenariovoraussetzung, B/O und Cross-Charge korrekt | aktueller Regler, S3-Effekt |
| 18 | Reason / Limiter / Target Provenance | neue S3-Diagnose (`harvest_season_requested`, `harvest_season_effective`, `harvest_profile_confirm_s`, `harvest_s3_applicability`, `harvest_s3_override_reason`), `STRATEGIC_SHARE` ≠ `current_mode` | `state.py`, `measurement_v4.py`, As-built |
| 19 | High-SOC Strategic Share & Time Profile | **wesentliche V17.1.0-Aktualisierung**: Fenster sind konfigurierbare Default-Zeiten, `HARVEST_SEASON_POLICY_ENABLED=false` ist wirksamkeitsneutraler Default; Requested/Effective/`legacy_parallel`, `parallel|sma_priority|calendar`, `NOT_APPLICABLE|APPLIED|OVERRIDDEN`, Capture-Floor | `_harvest_time_profile`, `_s3_season_policy`, Registry, Validation, S3-Spec |

## Fachlich sinnvolle additive Diagramm-Kandidaten (keine blind vorgeschriebene Stückzahl)

1. **20 – S3 Saisonpolicy / Opt-in / Override-Arbitration**: optional von Blatt 19 abspalten, falls 19 unlesbar groß wird. Zeigt saisonale Kalenderfenster, Effective `legacy_parallel`, Validierung und `NOT_APPLICABLE/OVERRIDDEN`.
2. **21 – NIGHT/MIN_SOC/Grid-Weiterverarbeitung V17.1.0**: detaillierte korrigierte Übergänge und Safety/Netzexport-Folgepfad. Wegen real behobener NIGHT/MIN_SOC-Fehlerklasse besonders lehrreich.
3. **22 – Grid-/Primär-/Zendure-Livestatus gegen Regelzyklus**: Quell-Samples vs. unabhängiges 1-s-GET vs. 3-s-Control vs. 10-s-Minigraph; Source-Age und „kein synthetischer Fresh-Wert“.
4. **23 – GRID_STALE / GRID_PROCESSING_STALE Operational Event State**: Stale-Open/Resolve getrennt von Safe/Reglerstatus, nur wenn für Verständlichkeit nötig.
5. **24 – SMA Speedwire / OBIS-Parser Input Contract**: Parser-Telegrammvalidierung und Plausibilitätsguard, optional als technisches Detail.

Eine kleinere, fachlich vollständige Kombination ist zulässig. **Pflicht ist vollständige Abdeckung der tatsächlich geänderten As-built-Verträge, nicht eine künstliche Nummernsteigerung.**

## Semantische Konflikte, die ausdrücklich geschlossen werden müssen

- **S3 – historischer Atlas:** V0.4 hat V17.0.2-Zeiten 09:30/11:30/14:30/18:00 als fest codierte Implementierung beschrieben. In V17.1.0 sind diese Zeiten nur kompatible Defaults der nun wirksamen S3-Zeitsettings. Das alte Blatt 19 ist damit als aktuelles As-built **nicht unverändert verwendbar**.
- **S3 – Status:** `HARVEST_SEASON_POLICY_ENABLED=false` (Default): `season_requested=sma_priority` kann vorliegen, aber effektive Strategie `legacy_parallel` sein. V17.1.0 realer HOLD zeigte `s3_applicability=NOT_APPLICABLE`; daraus folgt keine physisch wirksame Harvest-Episode.
- **Kommandowirkung:** Oktober-Evidenz zu echten Resync-/Ladeannahmeepisoden ist forensische Diagnose, **keine** Erlaubnis, Command-Recovery-Diagramme nach Vermutungen zu „reparieren“.
- **Fast Capture:** realer Active-NEAR_LIMIT-Nachweis existiert; Active-FULL_IDLE weiter ohne natürliche Feldevidenz, nicht als PASS zeichnen.
- **Parser/Nacht:** Fixes V17.1.0 technisch implementiert/QA PASS, aber natürliche Trigger-/Fehlerevidenz teils noch `EVIDENCE_PENDING/NOT_EVALUABLE`.
- **Hardware:** ursprünglicher realer Controllerzyklus (~3 s) bleibt unverändert, trotz sichtbarer sekündlicher Datenaktualisierung.

## Gemeinsame Quellenrangfolge

1. Aktuell verifizierte Produkt-Source + reale unabhängige Feldevidenz;
2. freigegebene Implementierungsspezifikation;
3. `07_ZEC_CURRENT_RELEASE_AND_FIELD_STATUS.md`;
4. `01`–`06` einschließlich `05` als einziger Backlog-/Roadmap-Autorität;
5. normative Regelwerke;
6. alte UML V0.4 als historische Architektur- und Visualisierungsprovenienz.

**Reviewprotokoll je Blatt:** `diagram_id | last_reconciled_version/build | file_dot_sha256 | rendered_svg_sha256 | source_symbols | tests | status (UPDATED/REVIEWED_UNCHANGED/NEW/HISTORICAL_ONLY) | reviewer | reviewed_at | conflicts/limitations`.
