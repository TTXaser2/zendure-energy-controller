# Technical Notes – Zendure Energy Controller V12.12.2

## 1. Globaler produktiver Instance Owner

`instance_owner.py` verwendet einen absoluten Lockpfad `/opt/zendure-controller/zendure_controller.instance.lock` und einen nichtblockierenden POSIX-`flock`. Der Kernel-Lock ist authoritative; Dateiinhalte dienen nur der Diagnose.

`ZendureController.main()` erwirbt die Ownership vor `ConfigManager`, MQTT, Measurement, Webserver und Regelzyklus. Ein abgewiesener Zweitprozess endet mit Exit-Code `73`. Es gibt weder automatische Übernahme noch ein Gerätekommando zur Bereinigung der Zweitinstanz.

Die Lockdatei wird absichtlich nicht gelöscht. Dadurch entsteht keine Unlink-/Inode-Race; ein harter Prozessabbruch gibt den Kernel-Lock automatisch frei.

## 2. Owner-Diagnose

`ControllerState`, `/health`, `/ready` und Statusdiagnose enthalten Active-Flag, PID, Build-ID und Startzeit; der technische Lockpfad wird nur im Ready-/internen Diagnosevertrag geführt.

## 3. Harvest Observation Clock

`update_rest_surplus_harvest_state()` verwendet `time.monotonic()` und einen Observation-Token aus Netzleistungs-Samplezeit plus Primärspeicher-Samplezeit.

- SMA-Direktquelle verwendet den tatsächlichen Paketzeitpunkt des Energy-Meter-Snapshots;
- Shelly-HTTP erhält pro erfolgreichem Read einen neuen Samplezeitpunkt;
- wiederholte identische Tokens erhöhen Entry/Hold nicht;
- die erste distinct Beobachtung erhält weiterhin ein nominelles `INTERVAL_SECONDS`-Intervall, um V12.12.1-Nominaltiming beizubehalten;
- danach wird tatsächliche monotone Zeit verwendet;
- überschreitet der Abstand die vorhandene Freshness-/Aktualitätsgrenze der beteiligten Quellen, gilt die Beobachtungskontinuität als unterbrochen: Entry startet mit genau einem nominellen Intervall neu; Hold verbraucht nach dem Stall höchstens ein nominelles Intervall.

Damit wird ein langer Host-Stall nicht als Folge vieler unabhängiger Beobachtungen gewertet. Wall-Clock-Sprünge sind irrelevant.

## 4. Harvest Current-State-Diagnose

`_reset_rest_surplus_harvest()` und inaktive/Exit-Pfade neutralisieren den aktuellen `harvest_limiter_reason`. Historische Gründe werden nicht länger über dieses Current-State-Feld suggeriert.

Die Zielwertfunktion `_rest_surplus_charge_pressure_target()` und die Harvest-Leistungsallokation bleiben unverändert.

## 5. Measurement-Manifest-Lifecycle

`MeasurementV4Logger` hält für neue Files den tatsächlichen pending Rotationsgrund fest und finalisiert bei sauberem Close:

- Writer-eigenen `row_count`;
- letzten geschriebenen Epochwert;
- `closed_time_utc`;
- Runtime-Event `logging_file_closed`.

Die Finalisierung liest die Messdatei nicht erneut ein und führt keinen Vollscan durch. Bei hartem Prozessabbruch wird die Finalisierung nicht ausgeführt; `closed_time_utc` bleibt leer.

## 6. Status-Info-Panel

Desktop `Controller & Schnittstellen` ist click-pinned: kein `mouseenter`-/`mouseleave`-Lebenszyklus und kein Focus+Click-Doppeltoggle. Interner Wheel-Scroll verändert nachweislich den eigenen `scrollTop`; Outside-Click/Escape/Close schließt.

## 7. Mobiler SOC-Tagesgraph

Bei Viewports bis 620 px rendert die Auswahl ihre Detaildaten in `#storageSocMobileDetails` unterhalb des Canvas. Der Floating-Tooltip wird auf Mobil ausgeblendet; Crosshair/Punktwahl im Canvas bleibt sichtbar. Desktop bleibt unverändert.

## 8. Regler-No-Regression

Die gezielt geänderte `controller_logic.py` enthält nur Harvest-Zeit-/Current-State- und Samplezeitänderungen. Normalpfadfunktionen für Cross-Charge, Harvest-Zielwertbildung, manuelle Modi, NIGHT, Discharge und Command-Effect werden über AST-/Differentialnachweise und den vollständigen Bestand abgesichert.

`measurement_v4_contract.py` bleibt unverändert; das V4-Feldschema wird nicht erweitert.
