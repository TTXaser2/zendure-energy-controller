# Technical Notes V12.11.0-RC2

## Ziel

RC2 ergänzt auf RC1-Basis eine direkte SMA-Home-Manager-/SMA-Energy-Meter-Netzleistungsquelle. Der bestehende Shelly-/UniMeter-HTTP-Pfad bleibt Default. Die direkte SMA-Quelle kann passiv parallel beobachtet oder bewusst als experimentelle Grid-Quelle gewählt werden.

## Enthalten

- Neuer passiver UDP-Multicast-Listener für SMA Energy Meter / Sunny Home Manager 2.0.
- Standardwerte: Multicast `239.12.255.254`, UDP-Port `9522`.
- Parser für Gesamtbezug / Gesamteinspeisung mit ZEC-Vorzeichen: positiv = Netzbezug, negativ = Einspeisung.
- Neue Settings:
  - `GRID_METER_SOURCE`
  - `SMA_ENERGY_METER_PASSIVE_ENABLED`
  - `SMA_ENERGY_METER_GROUP`
  - `SMA_ENERGY_METER_PORT`
  - `SMA_ENERGY_METER_INTERFACE`
  - `SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS`
- Statuskarte „SMA Direktquelle“ mit Wert, Alter, Paket-/Dekodierzählern und Fehlerstatus.
- Semantische Settings-Warnung, wenn SMA direkt als produktive Regelquelle gewählt wird.
- Statuskarte „Konfigurationsstatus“ ans Ende der Statusübersicht verschoben.

## Nicht enthalten

- Keine Änderung an AUTO-/Harvest-/Cross-Charge-/Nachtmodus-Strategie.
- Keine Änderung an Zendure-MQTT-Kommandostruktur.
- Kein Entfernen von UniMeter/Shelly als Default.
- Kein automatischer Wechsel auf SMA direkt.

## Sicherheit

SMA direkt sollte zunächst passiv beobachtet werden. Produktive Umschaltung auf `GRID_METER_SOURCE=sma_energy_meter_udp` erst nach Plausibilitätsprüfung von Vorzeichen, Alter, Paketstabilität und Vergleich zur bisherigen Netzleistung.
