# ZEC Battery Care CP13 – Stufe 1: vorläufige aktive PV-Dispatchintegration

**Status:** `IN_DEVELOPMENT / SOURCE_FOCUSED_PASS / DEVELOPMENT_NOT_INSTALLABLE`  
**Basis:** extern gesicherter CP12, der von V17.1.3 abstammt. **Keine Änderung des produktiven Raspberry Pi.**

## Source- und Entscheidungsabbildung

- `controller_logic.py::run_once`: Der bereits nur bei validierter, saisonal wirksamer, explizit aktivierter Care-Policy arbeitende Shadow-Pfad liefert eine messwertbasierte absolute Ladezielvorlage. Er kann nun den regulären Ladehandler im Deadband erreichen. Ein bereits wirksamer Care-Extra-Anteil wird bei Netzimport ausdrücklich über den vorhandenen Lade-/Commandhandler abgebaut statt als altes HOLD-Ziel übernommen.
- `_battery_care_pv_shadow_step`: Unabhängige Zendure-AC-Richtung, bestehende Commandbereitschaft, Grid-/Zendure- und ggf. Primary-Messwerte, Quellzeitstempel und deren Freshness. Der Primary-Pfad benötigt auch bei gesetzt `second_battery_data_valid` ein nicht älter als 15 Sekunden gültiges Sample. Die Vorberechnung bleibt ein **physikalisch unbewiesener Kandidat**.
- `handle_charge`: Der normale AUTO-/S3-/Harvest-Baseline-Wert wird unabhängig von zuvor kommandiertem Care-Zusatzleistungsteil geführt. Ein begrenztes, absolute Care-PV-Ziel wird via `max(baseline, pv_absolute)` zusammengeführt (nicht addiert). Bei Care-Vorrang wird Fast Capture für diesen Schritt auf null gesetzt, um denselben Export nicht doppelt zu verwenden. Vor Gerät/Publish bleiben Cross-Charge, Hardwarelimits, SmartMode-/AC-/0-W-/Readback-/Effect-/Resync-Owner erhalten.
- `battery_care_pv_allocation.py`: Import größer 100 W neutralisiert den *zusätzlichen* Care-Anteil; ein unabhängiger nichtimportierender Bestätigungsframe ist vor einem erneuten positiven Attack erforderlich. Bestehende normale Baseline bleibt eigenständig.

## Evidenz und Grenzen

- Fokussierte Source-Tests für Deadband, Fast-Isolation, Import-Exit, Default-Off, Cross-Charge-Pfadvorbereitung, fehlende AC-Physik, Primary-Stale, neue Frames; keine physische Leistungs-/Energie-Wirksamkeitsbehauptung.
- Die neue Stufe 1 ist **nicht** die vollständige Battery-Care-Produktionsspezifikation: Stufe 2/3, Episodenpersistenz, Command-Effect-Incident-Verbindung, Status-/Graph-/Event-Vollvertrag, 22 UML-Blätter, Datenblatt und kompletter Release-/Feldnachweis bleiben gesonderte Folgeblöcke.
- Kein produktives Installationspaket und keine Freigabe zur Ferninstallation per Termius. Bei finalem Release: gesonderte iPhone/Termius-Transfer-/SSH-/SHA256-/Rollback-/Feldabnahmeanleitung auf Grundlage des tatsächlich gebauten Installers.
