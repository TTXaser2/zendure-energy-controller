# Spezifikation ZEC V12.12.2 – Single Owner, Harvest Timing/Diagnostics, Manifest Integrity & UI Field Fixes

**Status:** FINAL / umgesetzt  
**Basis:** V12.12.1 / `v12.12.1-20260810`  
**Ziel:** V12.12.2 / `v12.12.2-20260810`

## 1. Single-Owner-Invariante

Zu jedem Zeitpunkt darf auf dem Host maximal eine produktive ZEC-Instanz Eigentümer von Live-Regelung, Measurement und Geräte-Commandpfad sein. Die Ownership muss vor jeder produktiven Nebenwirkung erworben werden, unabhängig vom Working Directory sein und nach sauberem oder hartem Prozessende zuverlässig freigegeben werden. Ein abgewiesener Zweitstart endet fail closed, sendet keine Gerätekommandos und eröffnet keinen produktiven Measurement-Stream.

Pflichtfälle: Einzelstart, Zweitstart gleiches/anderes CWD, nahezu gleichzeitiger Start, sauberer Restart, harter Prozessabbruch/Recovery, keine stale Lock-Latch-Semantik, systemd-kompatibler Restart.

## 2. Harvest-Zeitinvariante

Entry-/Hold-Zeit verwendet monotone reale Zeit und nur neue fachlich gültige Beobachtungen. Doppelte Samples zählen nicht mehrfach; Wall-Clock-Sprünge wirken nicht. Ein langer Host-Stall darf nicht als viele unabhängige Beobachtungen gelten. Das nominelle Timing bei normalem Zyklusabstand bleibt erhalten.

Keine Änderung an Harvest-Leistungs-/Zielwertformeln.

## 3. Harvest-Limitersemantik

`harvest_limiter_reason` ist ausschließlich aktueller Zustand. Bei `NOT_APPLICABLE`, deaktiviertem Harvest, Reset oder beendetem Harvest darf kein alter Limitergrund fortgeführt werden. Historie ist bei Bedarf über explizite Event-/Last-Semantik zu führen, nicht über das Current-State-Feld.

## 4. Measurement-Manifest

Für sauber geschlossene Measurement-Files müssen tatsächlicher Rotationsgrund, finaler Writer-Rowcount und `closed_time_utc` korrekt sein. Ein abnormal offenes File bleibt von einem regulär geschlossenen unterscheidbar. Kein teurer Dateivollscan im normalen Regelpfad.

## 5. Status-/Graph-UI

Desktop-Info `Controller & Schnittstellen` ist klickfixiert und intern wirklich scrollbar. Mobil bleibt das viewportnahe Panel bestehen.

Auf Mobilgeräten werden SOC-Detailwerte außerhalb des Plotbereichs unter dem Canvas angedockt; Auswahlmarkierung und Kurven bleiben sichtbar. Desktop behält den Floating-Tooltip.

## 6. No-Regression

Geschützt bleiben AUTO/HOLD, Harvest-Zielwertrechnung, Cross-Charge, NIGHT, MAX_SOC, Command Effect/Readback/Resync, Settings Help/Guided Configuration, mobile Settings-Navigation sowie Measurement-V4-Header/Feldcontract. Keine Änderung aufgrund des externen Raspberry-Backup-/Host-Freezes und keine neue Installed-Tree-Provenance.

## 7. Exit-Gate

Zusätzlich zum vollständigen Releasegate sind Pflicht:

- P0-Single-Instance-Testmatrix einschließlich anderem CWD und Hard-Kill-Recovery;
- Harvest nominal/jitter/duplicate/stall/wall-clock/reset Differentialtests;
- Manifest service-start/rotation/open/clean-close/exakter Rowcount/no-fullscan;
- Status-Desktop echter Wheel-Scroll und Outside-Close;
- Mobile SOC-Docking auf 360/390/430 px;
- Differential-/AST-No-Regression der nicht betroffenen Regelpfade.
