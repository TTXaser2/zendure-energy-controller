# Spezifikation V12.11.2-RC17
## Harvest-Revision: strategische Parallel-Allokation mit verbindlichem 0-W-Netzziel

**Stand:** 30.07.2026  
**Basis:** V12.11.2-RC16  
**Status:** fachlich final; zur separaten Buildfreigabe; noch keine Codeänderung  
**Release:** V12.11.2-RC17  
**Arbeitstitel:** Harvest 0-W Network Target  

**Normative Grundlagen:**

- `ZEC_REGELSTRATEGIE_HARVEST_ZIELBILD_UND_MODUSDOKUMENTATION_V1.2.md`
- `ZEC_CODE_UND_MODUSINVENTUR_V12_11_2_RC16_V1.0.md`
- `ZEC_ANALYSE_REGELWERK_V1.1.md`
- `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md`
- `SPEZIFIKATION_ZEC_V12_11_2_RC16_RCB_SMA_FULL_OR_IDLE_ABSOLUTZIEL_FINAL.md`
- `UEBERGABE_ZEC_V12_11_2_RC16_RCB_SMA_FULL_OR_IDLE_ABSOLUTZIEL.md`
- `SPEZIFIKATIONSENTWURF_ZEC_HARVEST_REVISION_0W_NETZZIEL_V0.1.md`

---

## 1. Zweck und verbindliches Systemziel

RC17 erhält die entwickelte High-SOC-/Parallel-Harvest-Strategie und korrigiert die noch verbliebene Vermischung von:

1. Harvest-Entry- und Rauschschwellen,
2. strategischer Leistungsaufteilung zwischen SMA und Zendure,
3. gewünschter Netzleistung.

Verbindliches energetisches Systemziel:

```text
PV-Erzeugung
→ zuerst Hauslast
→ danach verfügbare Speicherladung
→ nur technisch nicht aufnehmbarer Rest ins Netz
```

Für alle von RC17 betroffenen Harvest-Ladezweige gilt:

```text
harvest_network_target_w = 0 W
intentional_export_bias_w = 0 W
```

Solange Hauslast oder mindestens ein verfügbarer Speicher den PV-Überschuss aufnehmen kann, darf kein Überschuss allein aufgrund von Share, Floor, Zeitprofil oder einer früheren Profilreserve eingespeist werden.

Eine Regeltoleranz beziehungsweise Deadband ist kein gewünschter Export. Kleine unvermeidbare Abweichungen durch Messrauschen, Rampen, Smoothing, Geräteverzögerung oder diskrete Sollwertänderungen bleiben zulässig, ohne dass der Controller absichtlich einen positiven Exportbetrag reserviert.

---

## 2. Unveränderte strategische Grundentscheidung

SMA bleibt Primärspeicher mit Vorrang, aber nicht mit Exklusivität.

Ab dem bestehenden High-SOC-Eintritt darf Zendure bewusst mehr als nur den momentanen Restexport übernehmen und dadurch die gleichzeitig positive SMA-Ladeleistung reduzieren. Dieser Parallel-Harvest ist beabsichtigt, damit:

- der SMA nicht unnötig früh vollständig geladen wird;
- SMA und Zendure länger gemeinsam Aufnahmeleistung bereitstellen;
- spätere solare Ertragsspitzen mit ungefähr 2.300 W SMA plus bis zu 2.400 W Zendure parallel aufgenommen werden können;
- nutzbare PV-Energie nicht wegen eines bereits früh gefüllten Primärspeichers verloren geht.

Verbindlich:

```text
Strategische SMA-Verdrängung bei gleichzeitigem Laden ist zulässig.
Batterie-zu-Batterie-Cross-Charge ist weiterhin unzulässig.
```

RC17 darf die entwickelte Share-, Floor-, Restart-, Entry-, Hysterese- und Hold-Logik nicht beiläufig entfernen oder vereinfachen.

---

## 3. Scope

### 3.1 Bestandteil

RC17 verändert ausschließlich die Harvest-Zielwertbildung und die unmittelbar zugehörige Diagnose:

1. verbindliches 0-W-Netzziel in allen Harvest-Ladezweigen;
2. Trennung von strategischem Share-Ziel und Export-Capture-Ziel;
3. harte Untergrenzenwirkung des Export-Capture-Ziels;
4. Kappung des rechnerischen SMA-Share-Ziels auf die konfigurierte technische SMA-Maximalleistung;
5. unabhängige physische Zendure-AC-Referenz in allen absoluten Harvest-Rechnungen;
6. klar diagnostizierter inkrementeller Fallback bei unsicherer Referenz;
7. Entfernung der Profilreserve aus der Zielwertrechnung;
8. Erhalt der Profilanteile und Entry-Bestätigungszeiten;
9. eindeutiger Measurement-V4-Vertrag;
10. vollständige Differential-, No-Regression- und Hardwareschonungstests.

### 3.2 Nicht Bestandteil

Nicht verändert werden:

- Harvest-Reason-Priorität;
- High-SOC-Schwellen 75 % / 70 %;
- Full-SOC-Schwelle 98 %;
- Zeitfenster oder Share-Prozente;
- Floor-, Restart- oder Near-Limit-Schwellen;
- Entry-Bestätigung;
- bestehende Stay-/Hold-Endsemantik;
- `LATCH_RECOVERY_TO_AUTO_GRID_EXPORT` als Schutzkonzept;
- normale AUTO-, DEADBAND-, NIGHT-, STOP- oder feste Modi;
- symmetrischer Cross-Charge-Schutz;
- MAX-/MIN-SOC und RC14-Acceptance/Taper;
- RC15 Publish-/Readback-Trennung und Late-Effect-Guard;
- Command-State-Gate oder Flash-Schutz;
- lokale Zendure-API-Architektur;
- Offgrid-Konfiguration oder Offgrid-Leistungssemantik;
- aktive SMA-Steuerung;
- ein Zendure-Langzeitausfall-Regelmodus;
- Settings-Redesign;
- Excel-Lernsimulation.

---

## 4. Kein separater Zendure-Langzeitausfallmodus

Ein neuer Regelmodus wie:

```text
ZENDURE_LONG_UNAVAILABLE
SMA_AUTONOMOUS_FALLBACK
```

wird ausdrücklich nicht eingeführt.

Begründung:

- ZEC steuert den SMA nicht aktiv.
- Ein rechnerischer Zendure-Share reserviert keine physische Leistung.
- Nimmt Zendure einen Sollwert nicht an, bleibt der Export am Netzanschlusspunkt sichtbar.
- SMA/Home Manager kann diesen Export weiterhin autonom bis zur eigenen Aufnahmegrenze verwenden.
- Ein zusätzlicher 600-s-Timer hätte keine neue Stellwirkung, aber zusätzliche Latch-, Recovery- und Wiederanlaufrisiken.

Länger anhaltende Nichtsteuerbarkeit darf später als Betriebsereignis dargestellt werden, bleibt aber reine Diagnose und ist nicht Bestandteil von RC17.

---

## 5. Verbindliche Ist-Zustandsmaschine

RC17 konserviert die RC16-Entry-/Stay-/Exit-Logik einschließlich ihrer derzeitigen Reason-Priorität.

### 5.1 Reason-Priorität

```text
1. SMA_FULL_OR_IDLE
2. HIGH_SMA_SOC_SMA_NEAR_LIMIT
3. HIGH_SMA_SOC
4. SMA_NEAR_LIMIT
5. NONE / EXPORT_HOLD / LATCH_RECOVERY
```

### 5.2 Entry-Bedingungen

#### `SMA_NEAR_LIMIT`

```text
SMA-Ladeleistung >= Near-Limit-Schwelle
UND Restexport >= REST_SURPLUS_MIN_EXPORT_W
```

#### `HIGH_SMA_SOC`

```text
SMA-SOC >= HARVEST_HIGH_SMA_SOC_ENTER_PERCENT
UND
(Restexport >= HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W
 ODER SMA-Ladeleistung >= Restart-Schwelle)
UND SMA-Ladeleistung >= Floor
```

#### `HIGH_SMA_SOC_SMA_NEAR_LIMIT`

Beide vorgenannten Bedingungen sind gleichzeitig erfüllt.

#### `SMA_FULL_OR_IDLE`

RC17 behält die tatsächliche RC16-Entry-Semantik unverändert:

```text
SMA-SOC >= HARVEST_SMA_FULL_SOC_PERCENT
UND Restexport >= HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W
```

Der bestehende Reason-Name wird nicht geändert, obwohl der Code keinen zusätzlichen expliziten Idle-Leistungsnachweis verlangt. Eine spätere Umbenennung oder echte Idle-Erweiterung benötigt einen separaten Migrationsentscheid.

### 5.3 Entry-Zeiten und Zeitprofile

Unverändert:

```text
09:30–11:30  SMA-Anteil 60 %  Entry 60 s
11:30–14:30  SMA-Anteil 50 %  Entry 30 s
14:30–18:00  SMA-Anteil 35 %  Entry 15 s
sonst         SMA-Anteil 50 %  konfigurierter High-SOC-Entry
```

Für `SMA_NEAR_LIMIT` bleibt `REST_SURPLUS_ENTRY_CONFIRM_SECONDS` maßgeblich.

### 5.4 Stay-/Hold-Semantik

Die vorhandene Semantik wird in RC17 ausdrücklich konserviert:

1. Fällt die unmittelbare Eligibility weg, bleibt Harvest bei SMA-SOC oberhalb der Exit-Schwelle zunächst während `HARVEST_HIGH_SMA_SOC_HOLD_SECONDS` aktiv.
2. Der vorherige Harvest-Reason wird im Regelfall weitergeführt.
3. Nach Ablauf der Hold-Zeit endet der aktive Zustand bei weiterhin aktiviertem High-SOC-Feature derzeit nicht zwingend; der Code kann den vorherigen Reason mit `PRIMARY_BAND_LIMIT` weiterführen.
4. `HARVEST_HIGH_SMA_SOC_HOLD_SECONDS` ist daher im RC16-Iststand keine harte maximale Stay-Dauer.

RC17 verändert dieses Verhalten nicht. Es wird durch Differentialtests festgeschrieben. Eine spätere Änderung benötigt:

- eigene fachliche Entscheidung;
- produktive Übergangsanalyse;
- Current-vs-New-Matrix;
- Latch- und Hardwareschonungsprüfung.

---

## 6. Gemeinsame Messgrößen und Vorzeichen

```text
Standort-Netzleistung:
  positiv = Netzbezug
  negativ = Netzeinspeisung

Zendure-AC-Leistung:
  positiv = Laden aus dem netzgekoppelten AC-Port
  negativ = Entladen zum Hausnetz

SMA-Leistung:
  positiv = SMA lädt
  negativ = SMA entlädt
```

Gemeinsame Größen:

```text
E = max(0, -control_grid_power_w)
S = max(0, frische gültige SMA-Ladeleistung)
C = frische unabhängige Zendure-AC-Ladung
T = S + C + E
```

Bedeutung:

```text
E = verbleibender Standort-Netzexport nach bereits wirksamer Zendure-Ladung
S = aktuell physisch beobachtete positive SMA-Ladung
C = aktuell physisch beobachtete positive Zendure-Netzportladung
T = gesamte aktuell verfügbare Speicher-Ladeleistung inklusive Restexport
```

`T` ist keine PV-Erzeugungsmessung. Es ist eine lokale Allokationsgröße aus beobachteter Speicherladung und verbleibendem Export.

---

## 7. Unabhängige Zendure-AC-Referenz

### 7.1 Zulässige Referenz

Die einzige zulässige physische Baseline für `C` ist die unabhängige Zendure-Netzportbeobachtung:

```text
zendure_power_observation_direction
zendure_power_observation_confidence
zendure_power_observation_signed_w
zendure_power_observation_age_s
```

Zulässig:

#### Frische positive Ladung

```text
direction = CHARGE
confidence = HIGH
signed_w > 0
kein CONFLICT
Beobachtung frisch
```

Dann:

```text
C = signed_w
reference_source = ZENDURE_GRID_PORT_OBSERVATION
reference_valid = true
```

#### Frisch bestätigte Neutralität

```text
direction = NEUTRAL
confidence = MEDIUM
beide expliziten AC-Richtungstopics frisch
```

Dann:

```text
C = 0
reference_source = ZENDURE_GRID_PORT_NEUTRAL
reference_valid = true
```

Die Freshness- und Zeitkohärenzregeln entsprechen zunächst dem in RC16 eingeführten 15-s-Evidenzvertrag. RC17 führt keinen neuen Timer und keine zyklusbasierte Bestätigung ein.

### 7.2 Unzulässige Referenzen

Nicht als physische Baseline verwenden:

```text
last_input_power
Desired Target
inputLimit-Readback
Command-Intent
Sollrichtung
outputPackPower
packInputPower
gridOffPower
Headunit-PV-Leistung
SMA-Leistung
berechnete Charge-Pressure
```

Ein Sollwert oder Readback darf niemals fehlende physische Zendure-Ladung ersetzen.

### 7.3 Unsichere Referenz

Unsicher bei:

```text
UNKNOWN
CONFLICT
DISCHARGE
stale
fehlendem signed Wert
fehlenden expliziten AC-Richtungstopics bei vermeintlicher Neutralität
ungültiger Grid-Quelle
unzulässigem Zeitversatz
```

Dann gilt:

```text
reference_valid = false
C wird nicht als 0-W-Istzustand behauptet
```

---

## 8. Inkrementeller Fallback

Bei unsicherer physischer Zendure-Referenz wird keine Absolutformel künstlich vervollständigt.

Der Zyklus verwendet:

```text
fallback_raw_target_w
=
last_input_power
+ CONTROL_GAIN × effective_export_power
```

Semantik:

```text
harvest_target_semantics = INCREMENTAL_FALLBACK
harvest_target_selected_by = INCREMENTAL_FALLBACK
reference_valid = false
```

Verbindlich:

- `last_input_power` ist nur interner Reglerzustand, keine behauptete Istleistung;
- bestehende Smoothing-, Step-, Cap-, Cross-Charge- und Command-Safety-Pipeline bleibt nachgeschaltet;
- bei wieder gültiger Referenz erfolgt automatisch die Rückkehr zur absoluten Branch-Rechnung;
- kein Latch;
- kein Rückfall auf `export - reserve` als absolutes Ziel;
- das Netz-Ziel bleibt fachlich 0 W, auch wenn der Fallback dieses aufgrund unsicherer Daten nur schrittweise annähern kann.

---

## 9. Neue Zielwertformeln

### 9.1 Gemeinsame Share-Rechnung

Für High-SOC-Branches:

```text
profile_share = aktiver tageszeitabhängiger SMA-Zielanteil
SMA_max       = SECOND_BATTERY_MAX_CHARGE_POWER_W
SMA_floor     = bestehende Floor-Schwelle

primary_share_unclamped_w
= max(SMA_floor, profile_share × T)

primary_share_target_w
= min(SMA_max, primary_share_unclamped_w)

zendure_share_target_w
= max(0, T - primary_share_target_w)

export_capture_target_w
= C + E
```

Die Kappung auf `SMA_max` ist zwingend. Ein rechnerischer SMA-Anteil oberhalb seiner technischen Aufnahmeleistung darf Zendure nicht begrenzen und dadurch Export erzeugen.

### 9.2 `SMA_NEAR_LIMIT`

```text
raw_target_w = export_capture_target_w = C + E
harvest_target_semantics = ABSOLUTE_EXPORT_CAPTURE
harvest_target_selected_by = EXPORT_CAPTURE
harvest_network_target_w = 0
```

Der reine Near-Limit-Zweig verwendet künftig ebenfalls die unabhängige physische AC-Referenz statt `last_input_power` als vermeintliche Basis.

### 9.3 `HIGH_SMA_SOC`

```text
raw_target_w
= max(
    zendure_share_target_w,
    export_capture_target_w
  )

harvest_target_semantics = ABSOLUTE_SHARE_OR_EXPORT_CAPTURE
```

Auswahlgrund:

```text
STRATEGIC_SHARE   wenn zendure_share_target_w > export_capture_target_w
EXPORT_CAPTURE    wenn export_capture_target_w > zendure_share_target_w
BOTH_EQUAL        bei Gleichheit innerhalb der Rundungsauflösung
```

Wirkung:

- Das strategische Share darf Zendure über die reine Restexportaufnahme hinaus erhöhen und SMA-Ladeleistung verdrängen.
- Das Export-Capture-Ziel ist eine harte Untergrenze. Share, Floor oder Zeitprofil dürfen es nicht unterschreiten.

### 9.4 `HIGH_SMA_SOC_SMA_NEAR_LIMIT`

Identische Max-Verknüpfung:

```text
raw_target_w
= max(
    zendure_share_target_w,
    export_capture_target_w
  )
```

Near-Limit-Capture darf nicht durch Share, Floor, Restart oder frühere Profilreserve abgeschnitten werden.

### 9.5 `SMA_FULL_OR_IDLE`

```text
primary_share_target_w = 0
zendure_share_target_w = 0
export_capture_target_w = C + E
raw_target_w = C + E

harvest_target_semantics = ABSOLUTE_EXPORT_CAPTURE
harvest_target_selected_by = EXPORT_CAPTURE
harvest_network_target_w = 0
```

Keine Profilreserve, kein SMA-Share und kein Floor-Abzug.

### 9.6 `EXPORT_HOLD` und fortgeführter Origin-Reason

Die Zustandsmaschine bleibt unverändert und führt während Hold im Regelfall den vorherigen Harvest-Reason fort. Die Zielrechnung verwendet deshalb weiterhin den tatsächlich gespeicherten Origin-Reason:

- früherer `HIGH_SMA_SOC` → High-SOC-Max-Verknüpfung;
- früherer kombinierter Reason → kombinierte Max-Verknüpfung;
- früherer `SMA_FULL_OR_IDLE` → vollständiges Export-Capture;
- früherer `SMA_NEAR_LIMIT` → vollständiges Export-Capture.

Wenn ausschließlich `EXPORT_HOLD` ohne belastbaren Origin-Reason vorliegt:

```text
bei gültiger Referenz: raw_target_w = C + E
bei unsicherer Referenz: INCREMENTAL_FALLBACK
```

Es darf weder ein veralteter Sollwert als physische Baseline noch eine frühere Profilreserve verwendet werden.

---

## 10. Profilreserve wird aus der Zielwertrechnung entfernt

Die bisherigen Werte:

```text
09:30–11:30  250 W
11:30–14:30  150 W
14:30–18:00  100 W
sonst         typischerweise 300 W
```

werden nicht mehr vom Harvest-Ziel abgezogen.

Sie waren keine separate Config-Größe, sondern mit dem Zeitprofil hart gekoppelt. RC17 entfernt diese Kopplung aus der operationalen Zielwertbildung.

Unverändert bleiben:

- Profile `morning`, `midday`, `afternoon`, `default`;
- SMA-Share-Prozente;
- Entry-Bestätigungszeiten;
- `HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W` als Entry-/Rauschschwelle.

Verbindliche Rollenklärung:

```text
HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W
= Entry-/Rauschschwelle
≠ gewünschter stationärer Export
≠ Profilreserve
≠ Netz-Ziel
```

---

## 11. Latch-Recovery

Die vorhandenen Latch-Schutzkonzepte bleiben erhalten, werden aber an die neue physikalische Zielwertsemantik angepasst.

### 11.1 Aktiver Harvest mit unerwartetem 0-W-Kandidaten

Bei gültiger physischer Referenz und echtem Export darf ein defensiver Latch-Recovery niemals nur den Restexport als absoluten Sollwert verwenden, wenn bereits Zendure-Ladung wirksam ist.

Stattdessen:

```text
SMA_NEAR_LIMIT / SMA_FULL_OR_IDLE:
  recovery_target = C + E

HIGH_SMA_SOC / kombinierter Branch:
  recovery_target = max(zendure_share_target_w, C + E)
```

Bei unsicherer Referenz:

```text
recovery_target = INCREMENTAL_FALLBACK
```

Ein nacktes `target = E` ist nur dann physikalisch korrekt, wenn `C = 0` unabhängig bestätigt ist.

### 11.2 Kein gültiger Harvest-Grund mehr

Der vorhandene Schutz:

```text
LATCH_RECOVERY_TO_AUTO_GRID_EXPORT
```

bleibt unverändert. Bei aktivem Harvest ohne gültigen Grund und vorhandenem Export darf die normale inkrementelle AUTO-Exportregelung übernehmen und den Harvest-State zurücksetzen.

---

## 12. Command-Pipeline und Steuerbarkeit

RC17 führt kein zweites Command-Gate in der Harvest-Zustandsmaschine ein.

Die vorhandene Command-Pipeline bleibt alleinige Freigabeschicht:

```text
smartMode=1 frisch
Command-State vollständig
acMode und Gegenlimit konsistent
Flash-Schutz aktiv
Publish-Deduplizierung
Command-Effect
Mismatch/Resync
Late-Effect-Guard
```

Wichtig:

- Die fachliche Zielwertberechnung darf weiterlaufen, damit Desired-State, Command-Effect und Recovery konsistent bleiben.
- Ein nicht bereiter Command-Pfad verhindert über das bestehende Gate die ungeschützte Geräteaktion.
- RC17 darf keinen neuen Vorfilter einführen, der einen aktiven Desired-State verwirft und dadurch Mismatch-/Resync-Recovery verhindert.
- Es gibt keine Harvest-spezifische Neutralisierungsschleife.
- Es gibt keinen zusätzlichen Zeit- oder Zyklus-Latch.

Die Steuerbarkeit wird ausschließlich diagnostisch ausgewiesen:

```text
harvest_command_path_eligible
harvest_command_path_block_reason
```

Diese Felder behaupten keine Gerätewirkung und ersetzen keine vorhandenen Command-State-/Effect-Felder.

---

## 13. Unveränderte nachgeschaltete Schutzpipeline

Nach `raw_target_w` wirken unverändert:

```text
MAX_CHARGE_POWER_W
read-only chargeMaxLimit
MAX_SOC_PERCENT
RC14 Acceptance/Taper
Smoothing
MAX_POWER_STEP_W
MIN_COMMAND_CHANGE_W
symmetrischer Cross-Charge-Schutz
Command-State-Gate
smartMode-/Flash-Schutz
RC15 Publish-Deduplizierung
Command-Effect-/Recovery
Late-Effect-Guard
```

RC17 darf keine dieser Schichten umgehen.

---

## 14. Current-vs-New-Matrix

| Branch / Fall | RC16-Istverhalten | RC17-Zielverhalten |
|---|---|---|
| `SMA_NEAR_LIMIT` | `last_input_power + E` | `C + E`; physisch absolutes Export-Capture |
| `HIGH_SMA_SOC` | `T - max(Floor, Share×T) - Profilreserve`; bei fehlender positiver Istleistung kann Sollwert in `T` eingehen | `max(T - min(SMA_max, max(Floor, Share×T)), C+E)`; ausschließlich physische Referenz |
| `HIGH_SMA_SOC_SMA_NEAR_LIMIT` | gleicher Share-/Floor-/Reserve-Pfad wie High-SOC; Near-Limit kann abgeschnitten werden | `max(Zendure-Share, C+E)`; Near-Limit-Capture harte Untergrenze |
| `SMA_FULL_OR_IDLE` | `C + E - Profilreserve` | `C + E` |
| Hold mit gültigem Origin-Reason | bisherige Branch-Rechnung einschließlich Profilreserve | Origin-Branch ohne Profilreserve; Export-Capture bleibt Untergrenze |
| Hold ohne Origin-Reason | Charge-Pressure-/Reserve-Pfad | `C+E`, sonst inkrementeller Fallback |
| unsichere Zendure-Referenz | Full/Idle: inkrementeller Fallback; High-SOC kann Sollwert als Ersatz-Ist verwenden | in allen absoluten Harvest-Branches inkrementeller Fallback; kein Soll-/Readback-Istwert |
| SMA-Share oberhalb technischer Maximalleistung | nicht ausdrücklich gekappt | auf `SECOND_BATTERY_MAX_CHARGE_POWER_W` gekappt |
| Profilreserve | 100–300 W absichtlicher Restexport | 0 W Abzug; Netz-Ziel 0 W |
| Latch-Recovery bei bereits wirksamer Ladung | teilweise nackter Restexport als Ziel | branchengerechtes absolutes Ziel oder inkrementeller Fallback |
| Command-Pfad nicht ready | bestehendes Command-Gate | unverändert; zusätzliche Diagnose, kein neues Gate |
| Stay/Hold-Ablauf | Hold ist nicht zwingend maximale Stay-Dauer | bitidentische Zustandssemantik |

---

## 15. Intended-Delta-Beispiele

### 15.1 Reines Near-Limit-Export-Capture

```text
SMA-Ladung:                  2.300 W
Zendure-Istladung C:           500 W
Restexport E:                  600 W

RC17-Rohziel:
C + E =                      1.100 W
```

Zielrichtung: 0 W Netzexport, begrenzt durch nachgeschaltete Caps und Dynamik.

### 15.2 Strategische Verdrängung bleibt erhalten

```text
SMA S:                       2.500 W
Zendure C:                     500 W
Export E:                        0 W
T:                            3.000 W
Profil-Share:                    50 %
SMA-Maximum:                  2.300 W
Floor:                          700 W

primary_share_target:        1.500 W
zendure_share_target:        1.500 W
export_capture_target:         500 W
finales Rohziel:             1.500 W
selected_by: STRATEGIC_SHARE
```

Zendure darf erhöhen und SMA kontrolliert verdrängen.

### 15.3 Export-Capture verhindert verschenkte 250 W

```text
SMA S:                       2.000 W
Zendure C:                   1.750 W
Export E:                      250 W
T:                            4.000 W
Profil-Share:                    50 %

primary_share_target:        2.000 W
zendure_share_target:        2.000 W
export_capture_target:       2.000 W
finales Rohziel:             2.000 W
selected_by: BOTH_EQUAL
```

Kein absichtlicher 250-W-Export.

### 15.4 SMA-Maximum begrenzt den Primäranteil

```text
T:                            4.500 W
morgendlicher SMA-Share:         60 %
rechnerischer SMA-Anteil:     2.700 W
SMA-Maximum:                  2.300 W

primary_share_target:        2.300 W
zendure_share_target:        2.200 W
```

Kein künstlicher Export aufgrund eines technisch nicht erreichbaren SMA-Anteils.

### 15.5 Full/Idle

```text
Zendure C:                     300 W
Export E:                      600 W

RC16:                          650 W bei 250-W-Reserve
RC17:                          900 W
```

### 15.6 Hold unter früherer Reserve

```text
Zendure C:                     600 W
Export E:                      100 W

RC16 Full/Idle-Hold:           450 W bei 250-W-Reserve
RC17 Export-Capture:           700 W
```

Der bestehende Export wird aufgenommen; keine künstliche Zielabsenkung allein wegen einer historischen Reserve.

### 15.7 Unsichere Referenz

```text
last_input_power:              300 W
effective_export_power:        600 W
CONTROL_GAIN:                  0,30

Fallback-Rohziel:
300 + 0,30 × 600 =             480 W
```

Dies ist ausdrücklich ein inkrementeller Reglerwert, kein physisch bestätigtes Absolutziel.

---

## 16. Measurement-V4-Vertrag

### 16.1 Bestehende RC16-Felder bleiben erhalten

```text
rest_surplus_harvest_active
rest_surplus_harvest_eligible
rest_surplus_harvest_reason
rest_surplus_harvest_block_reason
rest_surplus_harvest_profile
rest_surplus_entry_progress_s
rest_surplus_hold_remaining_s
rest_surplus_exit_reason
second_battery_charge_pressure_w
rest_surplus_export_w
harvest_primary_floor_w
harvest_primary_restart_w
harvest_primary_near_limit_w
harvest_primary_target_share
harvest_primary_required_w
harvest_primary_share_reserve_w
harvest_candidate_raw_w
harvest_candidate_after_primary_w
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
harvest_limiter_reason
```

### 16.2 Präzisierte Semantik bestehender Felder

```text
second_battery_charge_pressure_w
= T = S + C + E bei gültiger physischer Referenz
```

```text
harvest_primary_required_w
= primary_share_target_w nach Floor und SMA-Max-Kappung
```

```text
harvest_primary_share_reserve_w
= ungeklemmtes profile_share × T
```

```text
harvest_candidate_raw_w
= ausgewähltes ungeklemmt-nichtnegatives Branch-Rohziel
```

```text
harvest_candidate_after_primary_w
= gerundetes ausgewähltes Branch-Rohziel vor allgemeiner Schutzpipeline
```

```text
harvest_profile_reserve_w
= 0.0 in RC17, da keine aktive Exportreserve angewendet wird
```

```text
harvest_candidate_delta_w
= E bei gültiger physischer Export-Capture-Rechnung
```

```text
harvest_candidate_absolute_w
= export_capture_target_w = C + E
```

Bei `INCREMENTAL_FALLBACK` bleibt `harvest_candidate_absolute_w = 0`, damit kein physischer Absolutnachweis vorgetäuscht wird.

### 16.3 Additive RC17-Felder

```text
harvest_network_target_w
harvest_total_available_charge_w
harvest_primary_share_target_w
harvest_zendure_share_target_w
harvest_export_capture_target_w
harvest_target_selected_by
harvest_calculation_branch
harvest_entry_min_export_w
harvest_command_path_eligible
harvest_command_path_block_reason
```

Damit steigt der Standardheader bei exakt diesen zehn additiven Feldern von 228 auf 238 Felder.

### 16.4 Controlled Enums

`harvest_target_semantics`:

```text
ABSOLUTE_EXPORT_CAPTURE
ABSOLUTE_SHARE_OR_EXPORT_CAPTURE
INCREMENTAL_FALLBACK
NOT_APPLICABLE
```

`harvest_target_selected_by`:

```text
EXPORT_CAPTURE
STRATEGIC_SHARE
BOTH_EQUAL
INCREMENTAL_FALLBACK
NOT_APPLICABLE
```

`harvest_calculation_branch`:

```text
SMA_NEAR_LIMIT
HIGH_SMA_SOC
HIGH_SMA_SOC_SMA_NEAR_LIMIT
SMA_FULL_OR_IDLE
EXPORT_HOLD_EXPORT_CAPTURE
INCREMENTAL_FALLBACK
NOT_APPLICABLE
```

`harvest_reference_fallback_reason` mindestens:

```text
GRID_SOURCE_INVALID
REFERENCE_STALE
REFERENCE_UNKNOWN
REFERENCE_CONFLICT
REFERENCE_DISCHARGE
REFERENCE_VALUE_MISSING
INPUT_TIME_SKEW
INCREMENTAL_FALLBACK
```

`harvest_command_path_block_reason` verwendet bestehende Command-Gate-/Readback-Gründe und darf keine neue unabhängige Safety-Taxonomie erfinden.

### 16.5 Headerrotation

```text
RC16-Dateien bleiben unverändert
RC17 startet eine neue Measurement-V4-Datei
Contract-ID: schema_rc17
RC17 Standardheader: 238 Felder, sofern exakt die zehn definierten Felder umgesetzt werden
```

Keine gemischten RC16-/RC17-Header in derselben CSV.

---

## 17. Status- und UI-Diagnose

Die Statusseite darf keine zweite Zielwertrechnung implementieren. Sie zeigt ausschließlich den Controller-Snapshot.

Für aktive Harvest-Zweige soll sie kompakt unterscheiden:

```text
Netzziel:             0 W
Gesamt-Ladeangebot:   T
SMA-Share-Ziel:       primary_share_target_w
Zendure-Share-Ziel:   zendure_share_target_w
Export-Capture:       export_capture_target_w
gewählt durch:        target_selected_by
Rohziel:              harvest_candidate_raw_w
```

Bei Fallback:

```text
Inkrementeller Fallback
physische Referenz nicht bestätigt
konkreter Fallbackgrund
```

Kein UI-Text darf Sollwert, Publish oder Readback als bestätigte physische Wirkung darstellen.

---

## 18. Differentialtests

### 18.1 Reason- und State-Matrix

1. Reason-Priorität bleibt exakt:
   ```text
   FULL > COMBINED > HIGH > NEAR
   ```
2. Entry-Zeiten bleiben unverändert.
3. High-SOC-Hysterese 75/70 bleibt unverändert.
4. Full-SOC-Schwelle 98 bleibt unverändert.
5. Hold-Zeit wird unverändert heruntergezählt.
6. Nach Hold-Ablauf bleibt `PRIMARY_BAND_LIMIT`-Stay gemäß RC16 erhalten.
7. Profilwechsel ändern weiterhin Share und Entry-Profil wie bisher.
8. `REST_SURPLUS_HARVEST_ENABLED=false` bleibt normales AUTO.

### 18.2 Rechenvertrag

1. `SMA_NEAR_LIMIT`: `C=500`, `E=600` → 1.100 W.
2. `HIGH_SMA_SOC`: Share kleiner als Capture → Capture gewinnt.
3. `HIGH_SMA_SOC`: Share größer als Capture → strategischer Share gewinnt.
4. Gleichheit → `BOTH_EQUAL`.
5. kombinierter Branch: Capture darf nicht durch Share/Floor reduziert werden.
6. `SMA_FULL_OR_IDLE`: `C=300`, `E=600` → 900 W.
7. Kein Abzug von 250/150/100/300 W.
8. SMA-Share `2.700 W` bei SMA-Max `2.300 W` → Kappung auf 2.300 W.
9. Floor wirkt weiter auf strategisches Share, aber nicht unter Export-Capture.
10. Rundung exakt und reproduzierbar.

### 18.3 Referenzvertrag

1. CHARGE/HIGH/frisch → physischer signed Wert.
2. NEUTRAL/MEDIUM plus beide AC-Topics frisch → C=0 gültig.
3. DISCHARGE → Fallback.
4. CONFLICT → Fallback.
5. UNKNOWN/stale → Fallback.
6. fehlende explizite AC-Topics bei Neutral → Fallback.
7. `last_input_power`, `inputLimit`, Sollrichtung → niemals physische Referenz.
8. Pack-, Offgrid- und PV-Werte → niemals AC-Referenz.
9. Zeitversatz > Evidenzvertrag → Fallback.
10. Grid-Spike/ungültige Quelle → kein Absolutziel.

### 18.4 Hold und Latch

1. Hold mit Origin `HIGH_SMA_SOC` verwendet Max-Verknüpfung ohne Reserve.
2. Hold mit Origin `SMA_FULL_OR_IDLE` verwendet `C+E`.
3. Hold ohne Origin verwendet Export-Capture oder Fallback.
4. gültige Referenz plus Export kann nicht auf 0 W hängen bleiben.
5. Latch-Recovery verwendet kein nacktes E bei C>0.
6. `LATCH_RECOVERY_TO_AUTO_GRID_EXPORT` bleibt funktionsfähig.
7. kein neuer Latch durch Referenzwechsel frisch→stale→frisch.

### 18.5 Schutzpipeline

1. `MAX_CHARGE_POWER_W` bleibt wirksam.
2. read-only Gerätecap bleibt wirksam.
3. MAX_SOC und RC14-Taper bleiben wirksam.
4. Smoothing bleibt wirksam.
5. `MAX_POWER_STEP_W` bleibt wirksam.
6. `MIN_COMMAND_CHANGE_W` bleibt wirksam.
7. SMA beginnt zu entladen → Cross-Charge reduziert/neutralisiert weiter.
8. Command-State nicht ready → kein ungeschütztes aktives Limit.
9. bestehender Desired-State bleibt mismatch-/resyncfähig.
10. Late-Effect-Guard unverändert.

### 18.6 Hardwareschonung

1. kein zusätzlicher `acMode`-Wechsel bei gleichem CHARGE-Intent;
2. keine 0-W-Zwischenphase innerhalb derselben Laderichtung;
3. keine zusätzlichen CHARGE↔DISCHARGE-Wechsel;
4. keine Same-State-Publish-Serie;
5. keine persistenten Geräteschreibversuche;
6. keine neue zyklusbasierte Timerlogik;
7. keine zusätzliche Neutralisierungsschleife;
8. kein neuer Langzeitausfallmodus;
9. höhere reale Ladeaufnahme nur bei tatsächlichem PV-Überschuss oder beabsichtigter gleichgerichteter SMA-Verdrängung;
10. Cross-Charge bleibt nachgeschaltet und vorrangig.

---

## 19. No-Regression

Unverändert grün bleiben müssen:

```text
SAFE_STATE
STOP_HOLD
FIXED_CHARGE
FIXED_DISCHARGE
NIGHT_DISCHARGE
NIGHT_RESERVE_SOC
AUTO_GRID_IMPORT
AUTO_GRID_EXPORT außerhalb Harvest
DEADBAND/HOLD außerhalb aktivem High-SOC-Harvest
Harvest Entry/Hysterese/Hold/Exit
SMA_NEAR_LIMIT Entry
HIGH_SMA_SOC Entry
HIGH_SMA_SOC_SMA_NEAR_LIMIT Reason-Priorität
SMA_FULL_OR_IDLE Entry
LATCH_RECOVERY_TO_AUTO_GRID_EXPORT
symmetrischer Cross-Charge-Schutz
MAX-/MIN-SOC
RC14 Acceptance/Taper
RC15 Publish-/Readback-Trennung
RC15 Late-Effect-Guard
Command-State-Gate
Flash-Schutz / smartMode=1
Neutralization-Dedupe
Offgrid-Trennung
inverseMaxPower read-only
Config-Snapshot-/Hash-Vertrag
Excel-Lernsimulation bitidentisch
```

---

## 20. Produktivabnahme

### 20.1 Erforderliche Episoden

Die Branches werden getrennt bewertet:

```text
SMA_NEAR_LIMIT
HIGH_SMA_SOC
HIGH_SMA_SOC_SMA_NEAR_LIMIT
SMA_FULL_OR_IDLE
legitime Hold-Phase, sobald natürlich vorhanden
```

Nicht jeder seltene Branch muss vor Installation künstlich provoziert werden. Buildseitige Differentialtests sind Pflicht; produktive Freigabe erfolgt branchenspezifisch anhand natürlicher Episoden.

### 20.2 Pflichtnachweise je Episode

1. Zustand und Reason aktiv.
2. Eingangsdaten frisch und unabhängig.
3. Branch-Rechnung korrekt.
4. ausgewähltes Rohziel korrekt.
5. nachgeschaltete Limiter nachvollziehbar.
6. Readback folgt.
7. tatsächliche Zendure-AC-Leistung folgt.
8. SOC-/Energiebilanz plausibel.
9. Restexport konvergiert Richtung 0 W.
10. kein Mismatch, keine Resync-/Publish-Serie.
11. keine zusätzliche Hardwareumschaltung.

### 20.3 Stationäre Zielgrenzen

Für stationäre, nicht gecappte, nicht getaperte und nicht Cross-Charge-limitierte Episoden nach Settling:

```text
Median |control_grid_power_w|
<= max(DEADBAND_W, 100 W)

p95 |control_grid_power_w|
<= max(2 × DEADBAND_W, 200 W)
```

Diese Grenzen sind Auswertungsziele und keine Behauptung, dass jedes dynamische Wolken-/Lastintervall stationär sein muss.

### 20.4 Gegenhypothesen

Getrennt prüfen:

```text
BMS-Taper versus Allokationsfehler
Command-Nichtwirkung versus falsches Rohziel
Grid-/Zendure-Zeitversatz versus Rechenfehler
Cross-Charge-Limitierung versus Unterallokation
Gerätecap versus Branch-Fehler
Smoothing/Step versus stationärer Offset
Wolken-/Lastsprung versus Regelabweichung
```

### 20.5 Technischer Exportbias

RC17 startet mit:

```text
intentional_export_bias_w = 0
```

Nur wenn Produktivdaten wiederholt nachweisen:

- unnötige Netzbezugsspitzen;
- Pendeln um 0 W;
- erhöhte Publish-Frequenz;
- physische Richtungswechsel;
- erhöhte thermische oder elektrische Zyklen;

kann später ein eigener, klar benannter Bias von ungefähr 20–50 W geprüft werden. Er darf nicht an Zeitprofil, Share, Floor oder Entry-Schwellen gekoppelt werden.

---

## 21. Build-Abnahmekriterien

RC17 gilt buildseitig als bestanden, wenn:

1. ausschließlich Harvest-Zielbildung, Diagnose, Tests und Dokumentation fachlich geändert wurden;
2. alle vier Harvest-Ladebranches das definierte 0-W-Netzziel besitzen;
3. Parallel-Harvest und strategische SMA-Verdrängung erhalten bleiben;
4. Export-Capture eine harte Untergrenze ist;
5. der SMA-Anteil auf die technische Maximalleistung gekappt ist;
6. ausschließlich unabhängige AC-Beobachtung als physische Zendure-Referenz dient;
7. unsichere Referenz in den inkrementellen Fallback führt;
8. Profilreserve nicht mehr in irgendeine Zielwertformel eingeht;
9. Entry-/Share-Zeitprofile unverändert bleiben;
10. Hold-/Stay-Semantik durch Differentialtests unverändert nachgewiesen ist;
11. kein neues Gate, kein Timer und kein Langzeitausfallmodus eingeführt wurde;
12. Command-Safety, Cross-Charge und Hardwareschonung unverändert nachgeschaltet bleiben;
13. V4-Headerrotation und neue Felder reproduzierbar sind;
14. alle bestehenden und neuen Tests bestanden sind;
15. Python-, JavaScript- und Update-Skript-Syntax geprüft sind;
16. keine `config.json`, Credentials, Logs, SQLite- oder Pycache-Artefakte im ZIP liegen;
17. die Excel-Lernsimulation byteidentisch bleibt;
18. finales ZIP, Root, Dateigröße und SHA256 dokumentiert sind.

Produktiv freigabefähig wird RC17 erst branchenspezifisch nach Abschnitt 20.

---

## 22. Voraussichtlich geänderte Dateien

### Fachlich erforderlich

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
RELEASE_INFO_V12_11_2_RC17.md
TECHNICAL_NOTES_V12_11_2_RC17.md
UEBERGABE_ZEC_V12_11_2_RC17_HARVEST_0W_NETZZIEL.md
SPEZIFIKATION_ZEC_V12_11_2_RC17_HARVEST_0W_NETZZIEL_FINAL.md
```

### Neue Tests

```text
tests/test_v12_11_2_rc17_harvest_zero_grid_target.py
tests/fixtures/rc17_harvest_branch_matrix.json
```

Vorhandene relevante Tests werden erweitert, nicht ersetzt:

```text
tests/test_v12_10_rc9_rest_surplus.py
tests/test_v12_11_1_rc1_high_sma_harvest.py
tests/test_v12_11_2_rc16_rcb_sma_full_or_idle_absolute_target.py
```

### Nur falls technisch erforderlich

```text
operational_events.py
translations.py
```

### Nicht vorgesehen

```text
config_manager.py
config.example.json
mqtt_bridge.py
command_lifecycle.py
zendure_power_observation.py
zendure_local_api.py
cross_charge.py
Excel-Lernsimulation
```

Es werden keine neuen Config-Keys eingeführt.

---

## 23. Release- und Migrationsvertrag

```text
Version: V12.11.2-RC17
Basis:   unverändertes finales RC16-ZIP
```

Config:

- keine automatische Migration;
- keine Änderung produktiver Nutzerwerte;
- keine neuen Pflichtparameter;
- `HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W` wird nur in seiner bereits dokumentierten Rolle als Entry-/Rauschschwelle verwendet.

Measurement:

- neue `schema_rc17`-Datei;
- RC16-Dateien bleiben unverändert;
- alte Analysewerkzeuge müssen unbekannte additive Felder tolerieren oder explizit auf RC17 aktualisiert werden.

Artefakte:

- vorhandenes RC16-ZIP wird nicht überschrieben;
- eindeutige neue ZIP-Datei und SHA256;
- keine stille Revision unter gleicher Versionskennung.

---

## 24. Entwicklungsreihenfolge

```text
finale RC17-Spezifikation
→ ausdrückliche Buildfreigabe
→ RC17 auf finalem RC16-ZIP bauen
→ vollständige Differential-/No-Regression-Tests
→ finales ZIP und SHA256
→ Installation
→ unmittelbarer Sicherheits-/Statuscheck
→ natürliche branchenspezifische Harvest-Abnahme
→ parallel RC-C vollständig spezifizieren
→ RC-C in eigenem Folge-Release
→ anschließend Settings-Redesign fortsetzen
```

Keine Codeänderung und kein Build ohne separate ausdrückliche Freigabe.
