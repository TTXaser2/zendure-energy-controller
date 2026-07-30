# Spezifikation V12.11.2-RC16 / Entwicklungsblock RC-B
## `SMA_FULL_OR_IDLE` als physikalisch korrektes absolutes Ladeziel

**Stand:** 30.07.2026  
**Basis:** V12.11.2-RC15  
**Status:** fachlich final; zur separaten Buildfreigabe; noch keine Codeänderung  
**Ersetzt:** `SPEZIFIKATION_ZEC_RCB_SMA_FULL_OR_IDLE_ABSOLUTZIEL_ENTWURF.md`  
**Normative Grundlagen:**

- `ZEC_ANALYSE_REGELWERK_V1.1.md`
- `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md`
- `UEBERGABE_ZEC_V12_11_2_RC15_COMMAND_PUBLISH_READBACK_GUARD.md`
- `ANALYSE_ZEC_RECOVERY_20260725_NACH_REGELWERK.md`
- `ERRATA_ANALYSE_ZEC_REGELCHECK_20260724.md`

---

## 1. Ziel

RC-B korrigiert ausschließlich die mathematische Zielwertbildung im bereits bestehenden Harvest-Zweig:

```text
SMA_FULL_OR_IDLE
```

Der nach bereits laufender Zendure-Ladung verbleibende Netzexport ist ein **Delta**, kein absoluter Lade-Sollwert.

Künftig gilt:

```text
absolutes Zendure-Ladeziel
=
unabhängig beobachtete aktuelle Zendure-AC-Ladung
+ verbleibender Netzexport
- zeitprofilabhängige Exportreserve
```

Danach wirken unverändert:

```text
MAX_CHARGE_POWER_W
Gerätebegrenzungen
MAX_SOC_PERCENT
Smoothing
MAX_POWER_STEP_W
MIN_COMMAND_CHANGE_W
symmetrischer Cross-Charge-Schutz
Command-State-Gate
Flash-Schutz
RC15-Publish-Deduplizierung
Command-Effect-/Recovery-Logik
```

RC-B verändert weder Harvest-Entry/-Hold/-Exit noch andere Reglerzweige.

---

## 2. Produktiver Anlass

Im RC10-Recovery-Lauf wurde nachgewiesen:

```text
stabile SMA_FULL_OR_IDLE-Zyklen:         3.920
Zyklen mit mindestens 200 W Unterallokation:
                                          3.052 = 77,9 %
Median der Unterallokation:               288,7 W
p95:                                      496 W
Maximum:                                1.122 W
konservativ ungenutzte Energie:          ca. 0,95 kWh in 4,2 h
```

Der Fehler besteht unabhängig von der damaligen Command-Recovery-Störung.

RC15 hat inzwischen die Publish-/Readback-Trennung, Command-Safety und verschleißarme Neutralisierung stabilisiert. RC-B darf diese Schicht nicht verändern.

---

## 3. Mathematischer Fehler im RC15-Iststand

Aktuell wird im Zweig `SMA_FULL_OR_IDLE` sinngemäß berechnet:

```text
raw_candidate_w = remaining_export_w - profile_reserve_w
```

Mit:

```text
S = Überschuss vor Zendure
C = aktuelle Zendure-AC-Ladung
E = verbleibender Netzexport = S - C
R = Profilreserve
```

setzt der bisherige Regler:

```text
C_neu = E - R
```

Im stationären Gleichgewicht folgt:

```text
C = (S - R) / 2
E = (S + R) / 2
```

Der Regler konvergiert dadurch systematisch auf ungefähr die Hälfte des nach Reserve nutzbaren Überschusses.

Fachlich korrekt ist:

```text
C_neu = C + E - R
```

weil:

```text
C + E - R
= C + (S - C) - R
= S - R
```

Damit wird der nach Reserve nutzbare Gesamtüberschuss als absolutes Ladeziel abgebildet.

---

## 4. Verbindliche Begriffe und Vorzeichen

```text
Standort-Netzleistung:
  positiv = Netzbezug
  negativ = Einspeisung

Zendure-AC-Leistung:
  positiv = Laden aus dem netzgekoppelten AC-Port
  negativ = Entladen zum Hausnetz

remaining_export_w:
  max(0, -control_grid_power_w)

reference_charge_w:
  unabhängig beobachtete aktuelle positive Zendure-AC-Ladung

profile_reserve_w:
  bereits bestehende Reserve des aktiven Harvest-Zeitprofils

candidate_delta_w:
  remaining_export_w - profile_reserve_w

candidate_absolute_w:
  max(0, reference_charge_w + candidate_delta_w)
```

`candidate_delta_w` ist bewusst signed. Eine Reserve darf ein bestehendes Ladeziel bei zu kleinem Restexport auch reduzieren.

---

## 5. Unabhängige AC-Referenz

### 5.1 Zulässige Primärquelle

Die einzige zulässige physische Baseline für die Absolutrechnung ist die unabhängige Zendure-Netzportbeobachtung:

```text
zendure_power_observation_direction
zendure_power_observation_confidence
zendure_power_observation_signed_w
zendure_power_observation_age_s
```

Für eine positive Referenz müssen gemeinsam gelten:

```text
direction = CHARGE
confidence = HIGH
signed_w > 0
kein Power-CONFLICT
Beobachtung nach bestehendem 15-s-Netzport-Evidenzvertrag frisch
```

Dann:

```text
reference_charge_w = zendure_power_observation_signed_w
reference_valid = true
reference_source = ZENDURE_GRID_PORT_OBSERVATION
```

Die Referenz stammt damit aus `gridInputPower`/`outputHomePower` am netzgekoppelten AC-Port.

### 5.2 Frisch bestätigte Neutralität

Bei einer belastbaren frischen Netzportbeobachtung:

```text
direction = NEUTRAL
confidence = MEDIUM
```

gilt:

```text
reference_charge_w = 0
reference_valid = true
reference_source = ZENDURE_GRID_PORT_NEUTRAL
```

Eine neutrale Referenz ist fachlich korrekt, wenn Zendure noch nicht lädt und der gesamte nutzbare Überschuss erst aufgenommen werden soll.

### 5.3 Unzulässige Referenzen

Nicht als physische Baseline verwenden:

```text
last_input_power
gewünschter Sollwert
rückgelesenes inputLimit
Command-Intent oder Sollrichtung
outputPackPower allein
packInputPower
gridOffPower
Solar-/PV-Eingangsleistung der Headunit
SMA-Leistung
berechnete Charge-Pressure
```

Insbesondere darf ein Sollwert niemals als Beweis der tatsächlichen aktuellen Zendure-Ladung dienen.

### 5.4 Unsichere Referenz

Unsicher ist die Referenz bei:

```text
UNKNOWN
CONFLICT
DISCHARGE
staler Netzportbeobachtung
fehlendem signed Wert
unplausibler oder verworfener Telemetrie
```

Dann gilt:

```text
reference_valid = false
reference_charge_w = 0
```

Der Wert 0 ist dabei **keine behauptete physische Neutralität**, sondern nur ein nicht addierter Referenzanteil.

---

## 6. Fallback bei unsicherer Referenz

Bei unsicherer physischer Referenz darf die Absolutformel nicht mit einem Sollwert oder Readback künstlich vervollständigt werden.

Stattdessen verwendet dieser Zyklus den bestehenden inkrementellen AUTO-Exportregler:

```text
fallback_raw_target_w
=
last_input_power
+ CONTROL_GAIN * effective_export_power
```

Dabei gelten weiterhin Smoothing, Ramp, Cross-Charge, Caps und Command-Safety.

Wichtig:

- `last_input_power` ist hier nur interner Reglerzustand;
- er wird nicht als physische Istleistung bezeichnet;
- `reference_valid` bleibt false;
- die Diagnose nennt den konkreten Fallbackgrund;
- sobald wieder eine gültige unabhängige AC-Beobachtung vorliegt, wird automatisch die Absolutformel verwendet;
- kein Latch und kein abruptes Zurückfallen auf `export - reserve` als absoluten Zielwert.

---

## 7. Exakte RC-B-Zielwertpipeline

Nur wenn gilt:

```text
rest_surplus_harvest_active = true
rest_surplus_harvest_reason = SMA_FULL_OR_IDLE
bestehende Branch-Bedingungen weiterhin erfüllt
```

wird gerechnet:

```text
remaining_export_w
= max(0, -control_grid_power_w)

candidate_delta_w
= remaining_export_w - profile_reserve_w

candidate_absolute_unclamped_w
= reference_charge_w + candidate_delta_w

candidate_absolute_w
= max(0, round(candidate_absolute_unclamped_w))
```

Danach unverändert:

```text
target_capped_w
= min(candidate_absolute_w, MAX_CHARGE_POWER_W)

target_smoothed_w
= bestehendes Smoothing(last_input_power, target_capped_w)

target_ramped_w
= bestehendes MAX_POWER_STEP_W

target_after_cross_charge_w
= bestehender symmetrischer Cross-Charge-Schutz

target_after_device_caps_w
= bestehende read-only Gerätebegrenzungen

Publish
= bestehendes RC15-Command-State-/Flash-/Dedupe-Verfahren
```

Keine zusätzliche Anwendung von `CONTROL_GAIN` auf den gültigen Absolutkandidaten.

---

## 8. Zeitliche Kohärenz

Die Absolutformel kombiniert zwei Messgrenzen:

```text
Standort-Netzleistung
Zendure-Netzportleistung
```

Daher gilt:

- beide Quellen müssen gemäß ihrem bestehenden Freshness-Vertrag gültig sein;
- die Zendure-Referenz muss den bestehenden 15-s-Evidenzvertrag erfüllen;
- unplausible Grid-Spikes dürfen nicht als Exportanteil verwendet werden;
- die tatsächlich verwendeten Quellalter und die Zeitdifferenz werden diagnostisch protokolliert;
- keine Bestätigung anhand einer festen Zahl von Regelzyklen;
- keine neue konfigurierbare Wartezeit und kein neuer Timer.

Bei unzureichender zeitlicher Kohärenz greift der Fallback aus Abschnitt 6.

---

## 9. Current-vs-New-Matrix

| Fall | RC15 | RC-B |
|---|---:|---:|
| 300 W aktuelle Ladung, 600 W Restexport, 250 W Reserve | 350 W absolut | 650 W absolut |
| 1.800 W aktuelle Ladung, 800 W Restexport, 150 W Reserve | 650 W absolut | 2.450 W vor Caps |
| 0 W aktuelle Ladung, 600 W Restexport, 250 W Reserve | 350 W | 350 W |
| 600 W aktuelle Ladung, 250 W Restexport, 250 W Reserve | 0 W | 600 W |
| Referenz CHARGE/HIGH/frisch | Restexport allein | physische Ladung + Restexport − Reserve |
| Referenz stale/CONFLICT | Restexport als Absolutziel | inkrementeller AUTO-Fallback |
| BMS-Taper bei hohem Zendure-SOC | RC14-Acceptance | unverändert |
| SMA beginnt zu entladen | Cross-Charge nach Zielbildung | unverändert, bleibt nach Zielbildung |
| wechselnde Wolken | systematische Halbierung möglich | Absolutziel folgt Gesamtüberschuss, bestehende Rampe bleibt |
| gleicher Ladeintent | Limitupdates | weiterhin nur erforderliche Limitupdates |
| Richtungswechsel | bestehender Command-Vertrag | unverändert |

---

## 10. Abgrenzung

RC-B verändert ausschließlich:

```text
SMA_FULL_OR_IDLE-Zielwertberechnung
zugehörige Diagnose-/Measurement-Felder
zugehörige Tests und Dokumentation
```

Nicht Bestandteil:

```text
keine Änderung von Harvest-Entry, -Bestätigung, Hold oder Exit
keine Änderung von HARVEST_SMA_FULL_SOC_PERCENT
keine Änderung von HIGH_SMA_SOC
keine Änderung von HIGH_SMA_SOC_SMA_NEAR_LIMIT
keine Änderung von SMA_NEAR_LIMIT
keine Änderung von Primary Floor, Restart, Share oder Kapazitätsgewichtung
keine Änderung normaler AUTO_GRID_EXPORT-/AUTO_GRID_IMPORT-Zweige
keine Änderung von NIGHT_DISCHARGE
keine Änderung fester Modi
keine Änderung von Cross-Charge
keine Änderung der RC14-Ladeannahmeklassifikation
keine Änderung der RC15-Publish-/Readback- oder Guard-Logik
keine Änderung der lokalen API-Architektur
keine Readiness-/Settings-/UI-Neuentwicklung
keine Änderung persistenter Geräteeinstellungen
keine Änderung von inverseMaxPower
keine Änderung der Excel-Lernsimulation
```

---

## 11. Hardwareschonungs- und Reaktionsinvarianten

RC-B darf durch die höhere, fachlich korrekte Ladeallokation keine unnötige Hardwareaktivität erzeugen.

Verbindlich:

1. kein zusätzlicher `acMode`-Wechsel;
2. keine 0-W-Zwischenphase für dieselbe Laderichtung;
3. keine zusätzlichen Lade↔Entlade-Richtungswechsel;
4. keine normalen Wiederholungspublishes für denselben Desired-State;
5. keine persistenten Geräteschreibvorgänge;
6. keine Umgehung von `MAX_CHARGE_POWER_W` oder Gerätebegrenzungen;
7. keine Umgehung von `MAX_POWER_STEP_W`, Smoothing oder `MIN_COMMAND_CHANGE_W`;
8. keine Umgehung von MAX_SOC oder RC14-Taper;
9. kein Batterie-zu-Batterie-Umladen; Cross-Charge bleibt nachgeschaltet;
10. kein neuer Zeit- oder Zyklus-Latch.

Die höhere reale Energieaufnahme ist nur dann beabsichtigt, wenn echter zusätzlicher Netzexport vorhanden ist. Sie ist der fachliche Nutzen des Zweitspeichers und kein unnötiger Zusatzzyklus.

---

## 12. Diagnose- und Measurement-Vertrag

### 12.1 Bestehende Felder weiterverwenden

```text
rest_surplus_export_w
rest_surplus_harvest_reason
rest_surplus_harvest_profile
harvest_candidate_raw_w
harvest_candidate_after_primary_w
zendure_power_observation_direction
zendure_power_observation_confidence
zendure_power_observation_signed_w
zendure_power_observation_age_s
```

### 12.2 Additive RC-B-Felder

```text
harvest_target_semantics
harvest_reference_charge_w
harvest_reference_charge_source
harvest_reference_charge_confidence
harvest_reference_charge_age_s
harvest_reference_charge_valid
harvest_reference_fallback_reason
harvest_profile_reserve_w
harvest_candidate_delta_w
harvest_candidate_absolute_w
harvest_input_time_skew_s
```

Semantik:

```text
harvest_target_semantics:
  ABSOLUTE
  INCREMENTAL_FALLBACK
  NOT_APPLICABLE

harvest_reference_charge_source:
  ZENDURE_GRID_PORT_OBSERVATION
  ZENDURE_GRID_PORT_NEUTRAL
  NONE

harvest_reference_charge_confidence:
  HIGH
  MEDIUM
  NONE
```

`harvest_candidate_raw_w` bleibt kompatibel und enthält im `SMA_FULL_OR_IDLE`-Zweig künftig den absoluten ungeklemmt-nichtnegativen Kandidaten.

### 12.3 Headerrotation

Wegen additiver V4-Felder:

```text
RC15-Dateien bleiben unverändert
RC16/RC-B startet eine neue V4-Datei
neue Contract-ID
```

Keine gemischten RC15-/RC16-Header in derselben CSV.

---

## 13. Controlled Enums / Gründe

Mindestens:

```text
SMA_FULL_OR_IDLE_ABSOLUTE
REFERENCE_CHARGE_FRESH
REFERENCE_NEUTRAL_FRESH
REFERENCE_STALE
REFERENCE_UNKNOWN
REFERENCE_CONFLICT
REFERENCE_DISCHARGE
REFERENCE_VALUE_MISSING
GRID_SOURCE_INVALID
INPUT_TIME_SKEW
INCREMENTAL_FALLBACK
```

Reasons dürfen keine physische Wirkung behaupten, wenn nur eine Rechnung oder ein Publish vorliegt.

---

## 14. Intended-Delta-Tests

### 14.1 Rechenvertrag

1. Referenz 300 W, Export 600 W, Reserve 250 W:
   ```text
   delta = 350 W
   absolute = 650 W
   ```

2. Referenz 1.800 W, Export 800 W, Reserve 150 W:
   ```text
   absolute = 2.450 W
   danach bestehende Caps
   ```

3. Referenz 0 W, Export 600 W, Reserve 250 W:
   ```text
   absolute = 350 W
   ```

4. Referenz 600 W, Export 250 W, Reserve 250 W:
   ```text
   absolute = 600 W
   ```

5. Referenz 600 W, Export 100 W, Reserve 250 W:
   ```text
   delta = -150 W
   absolute = 450 W
   ```

6. Negatives Rechenergebnis:
   ```text
   max(0, ...)
   ```

7. Rundung exakt und reproduzierbar.

### 14.2 Referenzvertrag

1. CHARGE/HIGH/frisch:
   - physischer signed Wert wird verwendet.

2. NEUTRAL/MEDIUM/frisch:
   - Referenz 0, gültig.

3. DISCHARGE:
   - nicht als negative oder positive Ladebaseline verwenden;
   - inkrementeller Fallback.

4. CONFLICT:
   - inkrementeller Fallback.

5. stale/UNKNOWN:
   - inkrementeller Fallback.

6. `inputLimit`, `last_input_power` oder Sollrichtung:
   - niemals Quelle von `harvest_reference_charge_w`.

7. Offgrid-/Pack-/PV-Werte:
   - niemals in AC-Referenz addieren.

### 14.3 Dynamik und Konvergenz

1. Konstantes Gesamtsurplus bei wechselnder Aufteilung zwischen Zendure-Ladung und Restexport:
   - absoluter Kandidat bleibt konstant;
   - kein Halbierungsgleichgewicht.

2. Wolkenfolge:
   - bestehendes Smoothing/Step begrenzt Änderungen;
   - keine neue Oszillation.

3. Referenz wird kurz stale und danach wieder frisch:
   - Fallback ohne abrupten Zielkollaps;
   - automatische Rückkehr zur Absolutformel;
   - kein Latch.

4. Grid-Spike oberhalb Plausibilitätsgrenze:
   - nicht in Absolutkandidat übernehmen.

5. Zeitlich zu stark versetzte Eingänge:
   - Fallback und Diagnose.

### 14.4 Schutzpipeline

1. Kandidat oberhalb `MAX_CHARGE_POWER_W`:
   - vorhandene Cap-Klemmung.

2. read-only Gerätebegrenzung niedriger:
   - bestehende Command-Cap-Klemmung;
   - keine Schreibänderung an der Gerätebegrenzung.

3. SMA beginnt zu entladen:
   - Cross-Charge reduziert beziehungsweise neutralisiert weiterhin.

4. Zendure erreicht MAX_SOC:
   - bestehender Safe-State/Neutralisierungspfad.

5. High-SOC-Acceptance/Taper:
   - kein Mismatch-/Resync-Regression.

6. RC15 State-Readback abweichend:
   - keine Same-State-Publish-Wiederholung.

7. RC15 Late-Effect-Guard:
   - unverändert.

### 14.5 Verschleiß

1. gleicher CHARGE-Intent mit veränderlichem Absolutziel:
   - kein `acMode`-Wechsel.

2. keine neue 0-W-Zwischenphase.

3. keine zusätzlichen physischen CHARGE↔DISCHARGE-Wechsel.

4. genau ein Limitpublish je tatsächlich neuem Desired-State.

5. keine persistenten Property-Schreibversuche.

---

## 15. No-Regression-Tests

Unverändert bleiben müssen:

```text
AUTO_GRID_EXPORT außerhalb SMA_FULL_OR_IDLE
AUTO_GRID_IMPORT
DEADBAND/HOLD
SMA_NEAR_LIMIT
HIGH_SMA_SOC
HIGH_SMA_SOC_SMA_NEAR_LIMIT
Harvest Entry/Hold/Exit
Latch-Recovery
Primary Floor/Restart/Share
NIGHT_DISCHARGE und Reserve-SOC
FIXED_CHARGE
FIXED_DISCHARGE
STOP_HOLD
symmetrischer Cross-Charge-Schutz
Flash-Schutz / smartMode=1
Command-State-Gate
Neutralization-Dedupe
RC14 Acceptance/Taper
RC15 Publish-/Readback-Trennung
RC15 Late-Effect-Guard
Offgrid-Trennung
inverseMaxPower read-only
Measurement-/Config-Snapshot-Vertrag
finale Excel-Lernsimulation bitidentisch
```

---

## 16. Produktivabnahme nach Installation

### 16.1 Datenbasis

Erforderlich ist mindestens eine natürliche `SMA_FULL_OR_IDLE`-Episode mit:

```text
frischer gültiger Grid-Quelle
frischer gültiger Zendure-Netzportbeobachtung
Zendure unter MAX_SOC
kein Taper/not_accepting
kein aktiver Cross-Charge-Limiter
kein Command-Mismatch
ausreichendem Restexport
```

Bevorzugt:

```text
mindestens zwei Episoden
oder mindestens 30 Minuten auswertbare Gesamtdauer
```

Kurze, stark bewölkte Einzelspitzen allein reichen nicht zur Konvergenzbewertung.

### 16.2 Pflichtnachweise

#### Zustandsnachweis

- `SMA_FULL_OR_IDLE` unter den bestehenden Bedingungen aktiv;
- Entry/Hold/Exit unverändert;
- kein Latch.

#### Rechennachweis

Je Zyklus:

```text
harvest_candidate_absolute_w
≈ harvest_reference_charge_w
 + rest_surplus_export_w
 - harvest_profile_reserve_w
```

Abweichung nur durch definierte Rundung.

#### Wirkungsnachweis

- gesendeter Zielwert folgt der bestehenden Smoothing-/Ramp-/Cap-Pipeline;
- Geräte-Readback folgt;
- physische Zendure-Ladung folgt;
- SOC-/Energiebilanz plausibel.

#### Konvergenznachweis

Nach Settling und ohne Cap/Taper/Wolkenstörung:

```text
Restexport nähert sich der Profilreserve
kein systematisches Halbierungsgleichgewicht
kein dauerhafter positiver Offset von mehreren hundert Watt
```

Auswertungsziel für stabile Episoden:

```text
Median |Restexport - Profilreserve|
<= max(DEADBAND_W, 100 W)

p95
<= max(2 × DEADBAND_W, 200 W)
```

Wenn Wetter- oder Lastdynamik diese Grenzen verhindert, wird die Episode als nicht ausreichend stationär gekennzeichnet und nicht künstlich als Fehler oder Erfolg gewertet.

#### Recovery-Nachweis

- echte Command-Nichtwirkung bleibt mismatch-/resyncfähig;
- dynamische Ziele verschleiern keine persistente Nichtwirkung;
- keine Same-State-Publish-Serie.

#### Hardwareschonungsnachweis

- keine Zunahme unnötiger `acMode`-Wechsel;
- keine zusätzliche 0-W-Zwischenphase;
- keine zusätzlichen physischen Richtungswechsel;
- Publish-Zahl entspricht echten Desired-State-Änderungen;
- keine persistenten Schreibversuche.

### 16.3 Gegenhypothesen

Mindestens getrennt prüfen:

```text
BMS-Taper versus falsche Allokation
Grid-/Zendure-Zeitversatz versus Formelfehler
Command-Nichtwirkung versus zu kleiner Sollwert
Cross-Charge-Limitierung versus Unterallokation
Gerätecap versus Rechenfehler
Wolkenrampe versus stationärer Offset
```

---

## 17. Abnahmekriterien

RC-B gilt buildseitig als bestanden, wenn:

1. ausschließlich `SMA_FULL_OR_IDLE` fachlich geändert wurde;
2. die Absolutformel exakt implementiert ist;
3. ausschließlich unabhängige AC-Netzportbeobachtung als physische Referenz dient;
4. Sollwert, Readback, Pack-, Offgrid- und PV-Werte nicht als AC-Referenz missbraucht werden;
5. unsichere Referenz in den inkrementellen AUTO-Fallback führt;
6. alle neuen Diagnosefelder reproduzierbar im V4-Vertrag enthalten sind;
7. Smoothing, Step, Caps, Cross-Charge, MAX_SOC und Command-Safety unverändert nachgeschaltet bleiben;
8. kein neues Latch, keine Race Condition und keine Prioritätsumkehr entsteht;
9. keine unnötigen Modus-, Richtungs- oder 0-W-Wechsel entstehen;
10. RC14-/RC15-Regressionen vollständig grün bleiben;
11. alle bestehenden und neuen Tests bestanden sind;
12. die Excel-Lernsimulation bitidentisch bleibt.

Produktiv freigabefähig ist RC-B erst nach dem Nachweis aus Abschnitt 16.

---

## 18. Voraussichtlich geänderte Dateien

```text
controller_logic.py
state.py
measurement.py
measurement_v4.py
measurement_v4_contract.py
status_page_v2.py
web_ui.py
static/status_v2.js
version.py
README.md
README_INSTALLATION.md
RELEASE_INFO_V12_11_2_RC16.md
TECHNICAL_NOTES_V12_11_2_RC16.md
UEBERGABE_ZEC_V12_11_2_RC16_RCB_SMA_FULL_OR_IDLE_ABSOLUTZIEL.md
tests/test_v12_11_2_rc16_rcb_sma_full_or_idle_absolute_target.py
tests/fixtures/rc10_sma_full_or_idle_underallocation.csv
tests/fixtures/rc16_expected_sma_full_or_idle.json
```

Nur falls technisch erforderlich:

```text
operational_events.py
translations.py
```

Nicht vorgesehen:

```text
config_manager.py
config.example.json
mqtt_bridge.py
command_lifecycle.py
zendure_power_observation.py
zendure_local_api.py
cross_charge.py
Excel-Datei
```

Es werden keine neuen Config-Keys eingeführt.

---

## 19. Releasebezeichnung

```text
Version:
V12.11.2-RC16

Entwicklungsblock:
RC-B

Arbeitstitel:
SMA_FULL_OR_IDLE Absolute Charge Target
```

---

## 20. Entwicklungsreihenfolge

```text
RC15 produktiv weiterbetreiben
→ RC-B-Spezifikation ausdrücklich zum Build freigeben
→ V12.11.2-RC16 bauen und vollständig regressionstesten
→ installieren
→ natürliche SMA_FULL_OR_IDLE-Episode erfassen
→ branchenspezifische Produktivabnahme
→ erst danach RC-C asynchrone lokale Zendure-API
→ anschließend Settings-Redesign fortsetzen
```

Keine Codeänderung und kein Build ohne separate ausdrückliche Freigabe.
