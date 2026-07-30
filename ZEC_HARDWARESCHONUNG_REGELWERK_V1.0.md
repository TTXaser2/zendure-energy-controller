# ZEC-Hardwareschonungs-Regelwerk V1.0

**Stand:** 29.07.2026  
**Status:** verbindliche Entwicklungsleitplanke

## 1. Grundsatz

Ein Softwarekommando ist nicht automatisch ein physischer Verschleißvorgang. Getrennt zu bewerten sind:

1. lokaler Publish,
2. Geräte-Readback,
3. tatsächlicher Leistungsfluss,
4. tatsächlicher Lade-/Entladerichtungswechsel,
5. möglicher mechanischer Schaltvorgang,
6. persistenter Schreibvorgang.

Nur nachgewiesene oder technisch belastbar ableitbare physische Vorgänge dürfen als Hardwareumschaltung bezeichnet werden.

## 2. Verschleißpfade

### Batteriezellen

Relevant sind insbesondere hohe Temperatur, lange hohe SOC-Verweilzeiten, hohe C-Raten, große Entladetiefen und hoher kumulierter Energieumsatz. Kleine Sollwertänderungen ohne realen Stromfluss erzeugen keinen Zellzyklus.

### Leistungselektronik

Relevant sind hohe Verlustleistung, hohe Temperatur, starke und häufige Temperaturhübe sowie Ripple- und Lastwechsel. Die Anzahl der ZEC-Berechnungen ist nicht direkt die Verschleißgröße.

### Relais und Schütze

Nur wenn das konkrete Gerät tatsächlich mechanische Kontakte betätigt, zählen Öffnungs-/Schließvorgänge als mechanische Belastung. Schalten unter Last belastet stärker als lastloses Schalten. Für den SolarFlow 2400 AC+ ist nicht belegt, dass `acMode`, `inputLimit=0`, `outputLimit=0` oder jeder signed Leistungswechsel jeweils einen mechanischen Schaltvorgang auslösen.

### Nichtflüchtiger Gerätespeicher

Dynamische Limits dürfen nur unter bestätigtem `smartMode=1` geschrieben werden. Dadurch werden die dynamischen Parameter laut Zendure nicht in Flash persistiert. Persistente Geräteeinstellungen bleiben außerhalb des Regelpfads.

## 3. Verbindliche Invarianten

Jede Regler- oder Command-Änderung muss nachweisen:

- keine unnötigen realen Richtungswechsel,
- keine unnötigen `acMode`-Änderungen,
- keine 0-W-Zwischenphase ohne Sicherheitsgrund,
- keine zyklusweisen Wiederholungspublishes,
- keine persistenten Geräteschreibvorgänge im Regelzyklus,
- keine unnötige Erhöhung von C-Rate, SOC-Hub oder Energieumsatz,
- keine neue Oszillation oder thermisch ungünstige Leistungsrampe,
- normale AUTO-, HOLD-, NIGHT- und Festmodus-Reaktionsfähigkeit bleibt erhalten.

## 4. Zeit- und Zyklussemantik

Sicherheitsbestätigungen dürfen nicht ausschließlich als feste Zahl von Regelzyklen formuliert werden.

Verbindlich sind:

- monotone reale Zeit,
- distinct/fresh Messsequenzen oder Quellzeitstempel,
- Mindestzahl unabhängiger Beobachtungen,
- keine Mehrfachzählung identischer Telemetrie.

## 5. Diagnosepflichten

Mindestens messbar machen:

```text
physical_charge_to_discharge_transitions
physical_discharge_to_charge_transitions
ac_mode_command_changes
neutralization_commands
late_effect_guard_activations
late_effect_guard_total_duration_s
late_effect_guard_blocked_active_commands
command_publish_batches
persistent_property_write_attempts
estimated_charge_energy_throughput_kwh
estimated_discharge_energy_throughput_kwh
time_above_high_soc_s
time_in_high_temperature_band_s
```

## 6. RC15-spezifische Anwendung

Der Late-Effect-Guard darf nur greifen, wenn ein aktives Kommando als Mismatch bestätigt wurde, die Episode physisch nicht recovered ist und anschließend Neutralität oder die Gegenrichtung angefordert wird.

Nicht aktivieren bei normalen Wolkenzieländerungen, gleicher Richtung, HOLD innerhalb derselben Richtung, bereits physisch bestätigter Recovery oder reinen Reason-Wechseln.

Während der Neutralisierung bleibt der vorhandene `acMode` grundsätzlich erhalten. Ein Moduswechsel erfolgt erst nach bestätigter Neutralität und nur bei tatsächlich erforderlicher Gegenrichtung.
