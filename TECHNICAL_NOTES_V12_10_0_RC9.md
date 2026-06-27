# Technical Notes V12.10.0-RC9

V12.10.0-RC9 ist ein gezielter Reglerlogik-RC auf stabiler RC8-Basis. Er ergänzt genau eine echte Regeländerung: Restüberschuss-Ernte bei Primärspeicher-Ladelimit.

## Restüberschuss-Ernte

Die Funktion ist nur im AUTO-Kontext aktiv. Sie startet erst, wenn der Primärspeicher/die Zweitbatterie über eine bestätigte Zeit nahe der konfigurierten maximalen Ladeleistung lädt und am Netzanschluss weiterhin Export anliegt. Der Mindestexport ist eine Entry- und Rauschschwelle, kein dauerhaft gewünschter Restpuffer.

Leitprinzipien:

- Entry streng und zeitlich bestätigt.
- Stay großzügig, damit kurze Last-/PV-Schwankungen nicht zu hektischem Ausstieg führen.
- Exit problemorientiert bei Netzbezug, SMA-Entladung/Cross-Charge-Risiko, stale Daten, SOC-Limit, Safe-State oder Moduswechsel.
- Die Funktion darf nur Ladeziele erzeugen, halten oder reduzieren. Sie darf niemals Entladung auslösen.
- Step-/Smoothing-Limits bleiben aktiv; der Primärspeicher bleibt der schnelle Regler, Zendure der trägere Restüberschuss-Sammler.

## Settings

Der bisherige Bereich „Cross-Charge-Schutz“ ist als Hauptbereich zu eng. RC9 strukturiert die Settings als Hauptbereich „Zweitbatterie“ mit Unterabschnitten für Messwerte, Cross-Charge-Schutz und Restüberschuss-Ernte.

Die Restüberschuss-Ernte ist standardmäßig deaktiviert bzw. ohne eingetragene maximale Primärspeicher-Ladeleistung nicht wirksam. Für einen SMA Sunny Island 3.0M-11 ist aus ZEC-Sicht 2300 W die relevante maximale AC-Ladeleistung.

## V4-Messdaten

Das V4-Standardprofil wurde um Harvest-Diagnosefelder erweitert. Dadurch kann später nachvollzogen werden, wann die Funktion eligible war, wann sie aktiv wurde, wie weit der Entry fortgeschritten war, warum sie beendet wurde und welche Schwellen galten.

Neuer `target_final_reason`:

- `REST_SURPLUS_HARVEST`

Neue Harvest-Diagnosefelder:

- `rest_surplus_harvest_active`
- `rest_surplus_harvest_eligible`
- `rest_surplus_entry_progress_s`
- `rest_surplus_exit_reason`
- `second_battery_charge_pressure_w`
- `second_battery_charge_saturation_threshold_w`
- `rest_surplus_export_w`

## Nachtmodus-Prognose

Die Statusseite zeigt im Nachtmodus zusätzlich eine Prognose für das voraussichtliche Ende inklusive prognostiziertem SOC, sofern SOC, Kapazität und Entladeleistung ausreichend bekannt sind.

## Diagnose-Nacharbeiten

- `/status` liefert die Controller-Version explizit.
- Config-Snapshots werden bei Versionswechsel nicht mehr irreführend mit alter Controller-Version weitergeführt.
- Cross-Charge-V4-Flags/Reasons wurden semantisch enger an tatsächlich aktive Zielwertänderungen gebunden.
- Timing-Detaildiagnose protokolliert längere Zyklen mit Teilphasen im Runtime-Log.
- Analyse-Preflight behandelt sehr kleine Dateiauswahlen weniger pessimistisch und nutzt eine eingebettete Bestätigung statt Browser-Popup.
