# Technische Notizen V12.8.4

V12.8.4 ist eine gezielte Bugfix- und Robustheitsversion.

## Ablaufreihenfolge / feste Betriebsarten

Die interne Regelzyklus-Reihenfolge wurde korrigiert:

1. MQTT-Sicherheitsprüfung
2. Zendure-/SOC-Telemetrie-Fallback
3. Manuelle Betriebsarten (`STOP_HOLD`, `FIXED_DISCHARGE`, `FIXED_CHARGE`)
4. Nachtmodus
5. SOC-Prüfung für die normale Automatik
6. Shelly-/UniMeter-Netzmessung
7. normale netzleistungsbasierte Regelung

Damit hängen feste Betriebsarten nicht mehr unnötig von der Shelly-/UniMeter-Netzleistungsmessung ab. Insbesondere setzt ein Shelly-/UniMeter-Ausfall im aktiven Nachtmodus die Zendure-Leistung nicht mehr auf 0 W, solange SOC und MQTT-Pfad gültig sind.

## Safe-State-Rückkehr nach Shelly-Fehler

`read_grid_power()` liefert nun einen booleschen Status. Wenn ein Shelly-/UniMeter-Fehler bereits zum Safe-State geführt hat, beendet der Regelzyklus sofort und läuft nicht versehentlich mit altem/0-W-Netzwert weiter.

## Default-Logging

Bei neu angelegter `config.json` sind produktive Logging-Defaults weniger verbose:

- `DEBUG=false`
- `LOG_VALUES=false`
- `LOG_CONTROL=false`
- `LOG_MQTT=false`
- `LOG_SOC=false`

Bestehende Konfigurationen bleiben beim Update unverändert.

## Replay-Service

Die systemd-Priorität und Ressourceneinstellungen des Replay-Service wurden bewusst nicht geändert.
