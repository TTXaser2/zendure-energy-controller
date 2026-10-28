# ZEC-BL-BATCARE-001 · Engineering CP12 – read-only Stufe-1-Quellenintegration

26.10.2026 · **DEVELOPMENT_NOT_INSTALLABLE** · keine Gerätekommandofreigabe.

## Tatsächlicher Stand

`controller_logic.ZendureController.run_once()` wertet nach gültiger AUTO-Grid-Erfassung einen read-only Care-PV-Schattenkandidaten aus. Der vorhandene Sourceadapter verwendet **ausschließlich die bisherigen** Grid-Sample-Zeitstempel, unabhängige AC-grid-seitige Zendure-Istleistung mit Quellzeitstempel und Frische-/Konfliktflags sowie die normalisierte reale Primärspeicherleistung mit Integration und Validity. `PvMemory` hält pro Quellfamilie distinct-Observation-Kontinuität getrennt von Harvest und Fast Capture; sie wird bei Care-off, außerhalb Saison oder anderem manuellen Modus zurückgesetzt. Ein Watch-/Poll-Intervall ist **kein** künstlich neues Messsample.

Statusfelder `care_pv_shadow_candidate_w`, `care_pv_shadow_extra_w`, `care_pv_shadow_balance_w`, `care_pv_shadow_reason` sind bewusst **nur Diagnostik**. Sie sind weder Geräte-Kommando, BMS-Readback noch Nachweis tatsächlicher PV-Umlenkung. Frühe Controller-Returns setzen Kandidaten im selben Zyklus auf 0/`NOT_EVALUATED` statt alte Schattenwirkung zu behaupten. Keine neue Sourcepollrate, kein zweiter Command-Owner, kein Netzwerk-Request in dieser Adapterfunktion.

**QA:** 989/989 `unittest`-Tests PASS mit `ResourceWarning=error` auf CP12-Working-Tree, darunter 10 neue Arbiter-Tests und 4 read-only Runtimeadapter-Tests; Python-Syntax für `controller_logic.py`, `state.py`, `battery_care_pv_allocation.py` PASS. Diese Zahlen sind Testevidenz, kein Hardware-/Release-PASS.

## Restarbeit und Grenzen

- PV: tatsächlicher Aufruf im existierenden zentralen Commandpfad **noch nicht** aktiviert; Baseline-Leak nach Care-Ende, Care/Fast-Capture-Exklusivität, aktive Import-Backoff-Reaktion und reguläre Safe-/Cross-Charge-Guards erst mit realer Dispatcher-Pipeline in einem weiteren source-/safety-getesteten Block integrieren.
- Netzpflege und Notladung, persistente Command-Effect-Verknüpfung, Warn-Popover, episodische Events/SOC-Graph, responsive Sichtprüfung, Quellenabgleich, 22-UML-Atlas, aktuelles Datenblatt und finaler Installer fehlen.
- Ältere Manifestdateien bleiben vollständige historische Provenienz; der CP12-Manifestauszug umfasst alle aktuellen Source-Dateien, nicht deren historischen Inhalt als gültige heutige Release-Manifeste.
- Realer Raspberry Pi verbleibt auf V17.1.3. Keine ferninstallierte Änderung, kein deklarierter Battery-Care-Effekt oder `PRODUCTIVE_PASS`.
