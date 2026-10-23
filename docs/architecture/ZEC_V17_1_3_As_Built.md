# ZEC V17.1.3 – Sourcebasierte As-built-Architektur

**Release:** `V17.1.3 / 17.1.3 / v17.1.3-20261022`. **Quellenbasis:** veröffentlichtes V17.1.2 (`zendure_controller_v17_1_2.zip`, SHA256 `d8128796c897ee1fcd610ab530760c492422d4c23d6a73e3a3da5ce3630ab02e`). **Status:** aktuelle technische As-built-Spezifikation; reale V17.1.3-Pi-Feldabnahme folgt separat.

## Regler-, Command- und Safetyautorität unverändert

`controller_logic.py` SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7` ist byteidentisch zur freigegebenen V17.1.2-Produktbasis. Der unabhängige Browser-Livepoll bleibt beim **1000-ms**-Intervall. S3, AUTO, Nacht-/MIN_SOC-Exportpfad, strukturierter SMA-Speedwire-/ **OBIS**-Parser, Grid-Stale-Diagnose, Cross-Charge, Fast Capture, Geräte- und SOC-Grenzen sowie Command-/Readback-/Recoveryverhalten erhalten keine neue Regel- oder Kommandoimplementierung. Primärspeicher-`usable SOC` bleibt diagnostisch, kein eigenständiger Steuerfreigabeparameter.

Bei Fast Capture gelten A400/R100 als **zusätzliche** Overlay-Anstiegs-/Abbaueraten in W/s und nicht als globale Änderungen von `MAX_POWER_STEP_W`. Letzterer begrenzt den normalen Basiswert nach Smoothing je Regelzyklus. `B+O` wird nur im erlaubten Active-Fall angefordert; physische und Schutzgrenzen besitzen Vorrang. Ein Nettoanstieg ist nicht garantiert.

## Umgesetzte V17.1.3-Änderungen

- `settings_help.py`, `settings_help_v1712.py`, Settings-Registry- und UI-Hilfepfad: individuell geprüfte Wirkungs-/Nichtwirkungsbeschreibungen für 190 operative Settings und 74 Bereichserklärungen einschließlich S3-/Harvest-/Fast-Capture-/Cross-Charge-/Command-Kontext; explizite Auswirkung ausgeschalteter Schalter, exakte Fast-Capture-Optionsnamen und verständlichere dynamische Hinweise. Settings-Typen, reale Consumer und Sicherheitssemantik bleiben unverändert.
- `static/status_v2.js`, `status_page_v2.py` und `static/status_v2.css`: sichtbarer Minigraphtext „Minigraph-Update 3 s · Livewert 1 s“, rechte Achse „Aktuellster Wert“, vollständiger 103-px-Minigraph und kompakte obere Kartenreihe im Standarddesktop. Quellen-/Freshness-/Validity-Informationen bleiben auch mobil vollständig sichtbar. Details und Zeit-/Rohwertsemantik verbleiben in Info- und barrierefreien Texten.
- `/grid-mini-data` in `web_ui.py`: die bereits in V17.1.2 eingeführte zeitlich korrekte 60-Minuten-Minutenauflösung, getrennte 5-/15-Minuten-Rohkurven und echte Datenlücken sind unverändert. Keine neue Erfassungsfrequenz, kein künstliches Sampeln.
- `tools/install_zendure_controller.sh`: regulärer V17.1.2→V17.1.3-Updatevertrag mit Fail-Closed-Preflight und Rollback. Echter Clean Fresh Install bleibt ausschließlich mit ausdrücklichem `--fresh-install` zulässig; kein mutierender Test am produktiven Raspberry Pi. Eine SHA256-Sidecar-Datei ist zum Übertragen auf den Pi nicht erforderlich.
- `docs/architecture/uml/`: 22 Diagramme (19 historische Basisblätter V0.4 quellgeprüft und drei ergänzte) als versionierte editierbare DOT-Quellen und offline lesbare SVG/PNG. Fachliche Source- und Visualreviews sowie Manifest/Traceability sind unter [UML-Index](uml/INDEX.md) und [Review](uml/SOURCE_REVIEW_V17_1_3.md) nachgewiesen. Historische PlantUML-Sekundärquellen sind **nicht** separat renderverifiziert und bleiben historische Provenienz.
- `docs/releases/v17.1.3/`, `docs/specifications/`, `docs/decisions/`, `docs/history/`: aktuelle Version und historische Originale sind getrennt. Der Ledger-Snapshot innerhalb des Releasepakets ist keine zweite lebende Roadmapautorität.

## UML-Navigation und fachliche Nachvollziehbarkeit

[Atlas-Index](uml/INDEX.md) · [Source-Traceability](uml/RELEASE_TRACEABILITY.md) · [Change-/Impact-Matrix](uml/CHANGE_IMPACT.md) · [22-Blatt-Source-/Visualreview](uml/SOURCE_REVIEW_V17_1_3.md). `tools/verify_uml_release.py` wird durch `tools/verify_arch_history.py` als verpflichtender `DOC_UML_RELEASE_GATE` integriert. Auslieferung mit gerenderten Bildern benötigt auf dem Pi kein Renderingprogramm.

## Technische Abnahme und Grenzen

Vollständige reguläre und `ResourceWarning=error`-Regression, unabhängige Browser-/Responsive-Geometrie, Source-Manifest/Hygiene, Installations-/Fresh-Extract-Verträge, Dokumentations- und Datenblattgates sind vor der technischen Releasefreigabe separat nachzuweisen. Der UML-Review macht aus fehlenden natürlichen S3-/Fast-Capture-`FULL_IDLE`-/Grid-Stale-/NIGHT-Naturepisoden **keine** reale Feldevidenz. `ZEC-EV-DEP-001` bleibt bezüglich echtem Clean-Fresh-/Uninstaller-Rollout auf separater Hardware offen. Die letzte allgemein real geprüfte Pi-Version ist V17.1.2; V17.1.3 verlangt ein eigenes reales Update und Feldabnahme.
