# Technische Hinweise – Zendure Energy Controller V12.11.2-RC12

## 1. Zweck

RC12 ist die sicherheitsnotwendige Nacharbeit der RC-A-Stufe. Die RC11-Produktivprüfung zeigte zwei getrennte Probleme:

1. ZEC regelte das Gerät bei rückgelesenem `smartMode=0`, obwohl Zendure für häufige Änderungen `smartMode=1` vorsieht.
2. `outputPackPower` wurde in RC11 als Entladebeleg behandelt, obwohl es laut zenSDK Batterieladung bezeichnet.

RC12 korrigiert beide Punkte und erweitert die Architektur um eine explizite Offgrid-Grenze.

## 2. Verifizierter MQTT-Command-Vertrag

Der lokale Home-Assistant-MQTT-Discovery-Vertrag des produktiven Geräts bestätigte:

```text
Zendure/switch/<DEVICE_ID>/smartMode/set
  Payload: ON / OFF

Zendure/select/<DEVICE_ID>/acMode/set
  Payload: Input mode / Output mode

Zendure/number/<DEVICE_ID>/inputLimit/set
  Bereich: 0–2400 W, Schritt 1 W

Zendure/number/<DEVICE_ID>/outputLimit/set
  Bereich: 0–2400 W, Schritt 1 W
```

RC12 besitzt ausschließlich Setter für diesen freigegebenen Laufzeitbefehlssatz. Die Gerätegrenzen und Offgrid-Konfiguration werden nur gelesen.

## 3. Flash-Schutz

Zendure beschreibt `smartMode=1` als volatile Betriebsart: häufig geänderte Parameter werden nicht in den Flash geschrieben und nach Geräteneustart werden die zuvor persistenten Werte wiederhergestellt.

RC12 erzwingt:

```text
Aktiver CHARGE-/DISCHARGE-Intent
→ smartMode=1 frisch bestätigt?
   nein: nur ON anfordern, keine dynamischen Limits senden
   ja: vollständigen Command-State prüfen
```

Der Runtime-Setter wirft bei jedem Versuch, `smartMode=False` zu setzen, einen Fehler. Eine spätere administrative Freigabe aus der ZEC-Steuerung müsste einen separaten, ausdrücklich autorisierten Pfad erhalten.

### 3.1 Normaler Hochfrequenzpfad

Nach bestätigtem Zustand:

```text
CHARGE, gleiche Richtung:
  nur inputLimit ändern

DISCHARGE, gleiche Richtung:
  nur outputLimit ändern
```

Voraussetzung ist jeweils:

```text
smartMode = 1
acMode = erwarteter Modus
inaktives Gegenlimit = 0
Command-State vollständig und frisch
```

### 3.2 Vollständiger Abgleich

Ein Full-State-Abgleich erfolgt bei:

- Start beziehungsweise fehlender Rücklesung,
- MQTT-/Geräte-Reconnect,
- Richtungswechsel,
- statischem Zustandswiderspruch,
- bestätigtem Mismatch/Resync,
- sicherheitsrelevanter Neutralisierung.

Ist `smartMode=1` bereits frisch bestätigt, wird es bei einem normalen Richtungswechsel nicht redundant geschrieben. Der vollständige logische Zustand besteht dann aus dem bestätigten Smart Mode und den neu gesetzten AC-/Limitfeldern.

### 3.3 Sicherheitsneutralisierung

Eine Neutralisierung darf nicht auf Command-Readback warten:

```text
smartMode=ON, falls nicht bestätigt
acMode = ursprungsbezogen beziehungsweise sicherer Fallback
inputLimit = 0
outputLimit = 0
```

Die Reihenfolge erfolgt über denselben MQTT-Client. Hier gilt Safety vor vollständiger Rücklesung. Im ungünstigen Fall kann eine seltene 0-W-Sicherheitsaktion noch vor Verarbeitung des Smart-Mode-Wechsels persistiert werden; RC12 vermeidet jedoch wiederholtes zyklisches Schreiben und blockiert die Neutralisierung nicht.

## 4. Command-State-Readback

Rückgelesen und auf Frische geprüft werden:

```text
smartMode
acMode
inputLimit
outputLimit
```

Zusätzlich read-only:

```text
inverseMaxPower
chargeMaxLimit
gridOffMode
```

Die Readbacks kommen über MQTT und ergänzend über die lokale Read-only-API. Reconnect invalidiert die Frischemarker.

## 5. Gerätecap-Klemmung

Die Zielwerte werden begrenzt auf:

```text
Laden:
min(ZEC-Konfigurationslimit, chargeMaxLimit, berechnetes Ziel)

Entladen:
min(ZEC-Konfigurationslimit, inverseMaxPower, Betrag des berechneten Ziels)
```

RC12 verändert diese Caps nicht. Beim produktiven Audit lagen sie bei 2400 W Lade- und 2000 W Entladeleistung.

## 6. Elektrische Leistungsgrenzen

RC12 modelliert drei unabhängige Grenzen.

### 6.1 Netzgekoppelter AC-Port

```text
gridInputPower  → AC-Bezug, signed positiv
outputHomePower → Haus-/Netzausgang, signed negativ
```

Diese Grenze ist primär für ZEC-Command-Effect und netzseitige Neutralisierung.

### 6.2 Batterie

```text
outputPackPower → Batterieladung, signed positiv
packInputPower  → Batterieentladung, signed negativ
```

Die Batteriegrenze bestätigt SOC-/Ladeannahme-/Energiebilanz, aber eine Batterieentladung beweist nicht automatisch eine Abgabe an das Haus.

### 6.3 Offgrid-Ausgang

```text
gridOffPower → separater Verbraucher am Notstromausgang
```

Offgrid wird niemals in die netzseitige signed Leistung eingerechnet.

Beispiel:

```text
gridInputPower = 0 W
outputHomePower = 0 W
packInputPower = 400 W
gridOffPower = 400 W
```

Ergebnis:

```text
Netzport neutral
Batterie entlädt
Offgrid-Verbrauch 400 W
Neutralisierung des Hausnetzausgangs bestätigt
```

## 7. Diagnosebilanz

RC12 berechnet nur diagnostisch:

```text
gridInputPower + packInputPower + solarInputPower
- outputHomePower - outputPackPower - gridOffPower
```

Der Residualwert wird wegen Wandlungsverlusten und zeitversetzten MQTT-Telegrammen nicht als Regelgröße verwendet.

## 8. High-SOC-Ladeannahme

Bei bestätigter Batterieladung nahe `MAX_SOC_PERCENT`, aber deutlichem Untertracking des angeforderten Ladeziels, kann RC12 klassifizieren:

```text
COMMAND_CHARGE_ACCEPTANCE_LIMITED
```

Dies bedeutet:

- Laderichtung vorhanden,
- Sollwerttracking nicht erreicht,
- Gerät/BMS begrenzt wahrscheinlich die Ladeannahme,
- kein automatischer Command-Mismatch und kein unnötiger Resync.

Außerhalb des High-SOC-Fensters bleibt persistente erhebliche Teilwirkung Mismatch- und Resync-fähig.

## 9. Lifecycle- und Event-Semantik

```text
MISMATCH_SUPERSEDED_BY_SAFETY_NEUTRALIZATION
MISMATCH_ABORTED_BY_INTENT_CHANGE
MISMATCH_RECLASSIFIED_AS_CHARGE_ACCEPTANCE_LIMITED
```

Ein neuer Sicherheitsintent schließt den alten Intent, ohne dessen Wirkung als wiederhergestellt zu behaupten.

Publish-Ereignisse:

```text
SMART_MODE_ENABLE_SENT
COMMAND_STATE_WAITING
FULL_STATE_COMMAND_SENT
COMMAND_LIMIT_UPDATED
FULL_STATE_NEUTRALIZATION_SENT
FULL_STATE_RESYNC_SENT
COMMAND_BATCH_DEDUPED
```

## 10. Measurement V4

Neue additive Felder umfassen:

- Grid-/Batterie-/Offgrid-Richtung und Leistung,
- `gridOffPower` und `solarInputPower`,
- diagnostischen Leistungsbilanz-Residualwert,
- gewünschten `smartMode`,
- Command-State-Readbacks,
- Flash-Schutzstatus,
- Gerätecaps und Offgrid-Modus,
- Mismatch-Auflösungsgrund.

RC10- und RC11-Header werden erkannt. Bestehende Dateien bleiben unverändert; RC12 setzt in einer neuen `schema_rc12`-Datei fort.

## 11. No-Write-Whitelist

ZEC schreibt in RC12 ausschließlich:

```text
smartMode = ON
acMode = Input mode / Output mode
inputLimit = 0..zulässiges Ziel
outputLimit = 0..zulässiges Ziel
```

ZEC schreibt ausdrücklich nicht:

```text
smartMode = OFF
inverseMaxPower
chargeMaxLimit
gridOffMode
socSet
minSoc
gridStandard
gridReverse
```

## 12. Bewusst offene Folgeblöcke

### RC-B

Korrektur von `SMA_FULL_OR_IDLE` auf ein absolutes Ladeziel mit vertrauenswürdiger Ist-/Tracking-Baseline.

### RC-C

Entfernung der lokalen Zendure-API aus dem synchronen Regelpfad über Hintergrundworker und Latest-Snapshot-Cache.

## 13. Grenzen der Zusicherung

Ohne veröffentlichte Flash-Endurance- und Firmware-Implementierungsdetails ist keine absolute Hardwaregarantie möglich. RC12 reduziert das beeinflussbare Risiko durch:

- Nutzung des von Zendure vorgesehenen volatilen Smart Mode,
- harte Sperre gegen Runtime-Deaktivierung,
- Deduplizierung und Mindeständerung,
- minimale gleichgerichtete Limitupdates,
- Retry-Fenster statt zyklischem Full-State-Spam,
- keine Änderung persistenter Gerätekonfigurationen,
- Rücklese- und physische Wirkungsprüfung.
