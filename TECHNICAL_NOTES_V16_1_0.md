# ZEC V16.1.0 – Technical Notes

## Capability-Architektur

`PrimaryStorageTemplate` besitzt nun optional `current_discharge_floor_soc`. Nur `sma_sunny_island` belegt diese Capability mit Register `31009`, FC03, zwei Registern, U32/FIX0 und `invalid_raw=0xFFFFFFFF`. Andere Templates führen keine implizite Saison-/Floor-Annahme ein.

Der Pflichtpoll für Primärspeicher-Leistung und Roh-SOC bleibt von der Capability getrennt. Der optionale Capability-Poll läuft mit eigenem Intervall und eigener Fehlerdiagnose. Ein Capability-Lesefehler verändert nicht rückwirkend den erfolgreichen Pflichtpoll. Letzte erfolgreiche Capability-Werte verlieren unabhängig über Freshness ihre Validität.

## Diagnostischer usable SOC

Bei gültigem Roh-SOC und gültigem Floor <100 % wird ausschließlich diagnostisch berechnet:

```text
usable_soc = clamp((raw_soc - floor) / (100 - floor) * 100, 0, 100)
```

Beispiel aus realer Vorimplementierungs-Evidenz: Roh-SOC 38 %, Floor 19 % -> 23,46 % des aktuell freigegebenen Entladebereichs. Diese Größe ersetzt den Roh-SOC in V16.1.0 an keiner Stelle des Reglers.

## API / Status / Measurement

Additive Felder umfassen Support, Wert, Freshness, Validity, Alter und Quelle der Entladeuntergrenze sowie den diagnostischen usable SOC. Measurement V4 wächst dadurch von 246/249 auf 254/257 Felder (Standard/Extended). Der Connection-Test liest die Capability diagnostisch mit, ohne sie zur Voraussetzung einer erfolgreichen Primärspeicherverbindung zu machen.

## Settings-/Naming-Hygiene

Herstellerneutrale Settings-Kategorien und Hilfetexte verwenden „Primärspeicher“. Bestehende technische Legacy-Keys mit `SMA` im Namen werden aus Kompatibilitätsgründen nicht migriert. Der New-Install-Default von `SECOND_BATTERY_DISPLAY_NAME` ist leer; die vorhandene Namensauflösung nutzt weiterhin expliziten Nutzerwert vor Template-Default vor neutralem Fallback.

## No-Regression

`controller_logic.py` bleibt byteidentisch zu V16.0.2 mit SHA256 `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`. Es gibt in Block A keine neue Commandwirkung, keine zusätzliche Lade-/Entladerichtung, keinen `acMode`-Wechsel und keinen persistenten Gerätewrite.
