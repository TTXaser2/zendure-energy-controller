# Technical Notes V12.10.0-RC6

V12.10.0-RC6 ist der erste Reglerlogik-RC für den symmetrischen Cross-Charge-Schutz.

## Enthalten

- Symmetrischer Cross-Charge-Schutz in AUTO/HOLD/HOLD_DEADBAND.
- Gegenläufige Flüsse `SMA/Zweitbatterie entlädt + Zendure lädt` und `SMA/Zweitbatterie lädt + Zendure entlädt` werden erkannt.
- Sichtbarer Parameter `CROSS_CHARGE_SIGNIFICANT_W` als Engage-Schwelle; interne niedrigere Release-Schwelle gegen Flattern.
- Proportionale Reduktion des Zendure-Zielwerts; keine Richtungsumkehr durch die Schutzlogik.
- V4-Flags/Reasons: `control_cross_charge_detected`, `control_cross_charge_limited`, `target_changed_by_cross_charge`, `CROSS_CHARGE_REDUCED/BLOCKED`.
- Analyse/Replay unterscheidet Regler-Gegenfluss und kurzzeitigen Istwert-/Telemetrie-Nachlauf.
- Analyse-Service nutzt das aktive Measurement-Verzeichnis ohne unbeabsichtigten Fallback-Pfadwechsel.
- Kontrast von Fehlerboxen verbessert.

## Nicht enthalten

- Keine Restüberschuss-Ernte bei SMA nahe Ladeleistungsgrenze.
- Keine Cross-Charge-Korrektur in `NIGHT_DISCHARGE`, festen manuellen Modi, `STOP_HOLD` oder `SAFE_STATE`.
- Keine Änderung an MQTT-Topics oder MQTT-Kommandostruktur.
