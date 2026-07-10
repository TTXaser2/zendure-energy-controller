# Technical Notes – V12.11.1-RC3

V12.11.1-RC3 ist ein Robustheits-Release auf Basis von V12.11.1-RC2. Auslöser war ein produktiver Restore-/Zendure-MQTT-Fall: ZEC berechnete im Nachtmodus korrekt `target_final_w=-400 W` und publizierte an den MQTT-Broker, Zendure setzte die Vorgabe aber nicht um. Nach erneutem Speichern der MQTT-Einstellungen in der Zendure-App kamen wieder Livewerte, ZEC sendete wegen unverändertem Sollwert jedoch weiter `NO_CHANGE`; erst ein Controller-Neustart löschte den internen Command-Cache und machte die Entladung wieder wirksam.

## Änderungen

- Zendure-Command-Resync bei MQTT-Recovery:
  - Wenn Zendure-MQTT von unsicher (`NO_LIVE`, `STALE`, `PARTIAL_STALE`, `RETAINED_ONLY`, Broker-Restart-No-Live) auf `ZENDURE_MQTT_OK` wechselt und ein aktiver Nicht-Null-Sollwert anliegt, sendet ZEC `acMode`, `inputLimit` und `outputLimit` erzwungen erneut.
  - Ein aktiver Sollwert, der bei unsicherem Zendure-MQTT gesendet/angefordert wurde, wird persistent als `command_uncertain_mqtt_active` diagnostiziert, bis Recovery-Resync oder beobachtete Gerätewirkung erfolgt.
- Command-Wirkungswächter:
  - Wenn ein aktiver Nicht-Null-Sollwert anliegt, aber die Zendure-Istleistung über `COMMAND_EFFECT_TIMEOUT_SECONDS` nahe 0 W bleibt bzw. nicht in die Sollrichtung folgt, wird `COMMAND_NOT_EFFECTIVE` gesetzt.
  - Nach `COMMAND_EFFECT_FORCE_RESEND_SECONDS` wird der aktive Sollwert kontrolliert erneut erzwungen gesendet.
  - Publish-Erfolg zum MQTT-Broker wird dadurch nicht mehr als Gerätewirkung missverstanden.
- Statusseite:
  - Zeigt Warnungen für unsicheren Zendure-MQTT-Command-State und nicht wirksame Sollwerte.
  - Der Hinweis, MQTT in der Zendure-App erneut zu speichern/aktivieren, wird bei passendem Zustand sichtbar.
- Feste Lade-/Entlademodi:
  - Analog zur Nachtmodus-Reichweitenprognose zeigt die Betriebsmoduskarte eine Prognose für manuelle feste Ladung/Entladung, z. B. „Manuelle feste Entladung bis 65 % SOC, voraussichtlich erreicht um 03:30 Uhr · danach STOP_HOLD“.

## Neue Config-Defaults

- `COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS=true`
- `COMMAND_EFFECT_MIN_W=80`
- `COMMAND_EFFECT_TIMEOUT_SECONDS=90`
- `COMMAND_EFFECT_FORCE_RESEND_SECONDS=120`

## Nicht geändert

- Keine Änderung an Harvest-Strategie, Cross-Charge-Regelstrategie oder Nachtmodus-Reserve-SOC-Logik.
- Keine Änderung an MQTT-Topics oder Zendure-Topicstruktur.
- Keine Änderung an SQLite-/CSV-Speicherzielstrategie.
