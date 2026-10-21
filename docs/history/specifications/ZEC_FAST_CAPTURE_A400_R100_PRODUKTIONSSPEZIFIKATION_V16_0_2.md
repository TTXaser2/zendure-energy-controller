# ZEC – Produktionsspezifikation Fast Capture A400/R100 gegen V16.0.2

**Status:** Spezifikation / noch nicht implementiert  
**Basis:** ZEC V16.0.2, Build `v16.0.2-20260917`  
**Release-ZIP SHA256:** `122d1d85ed52b17576b3f505b36abb56eb4ebcfe8ba27c5a2915a164f2e5efee`  
**geschützter `controller_logic.py` SHA256:** `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`  
**Replay-Evidenz:** Pretrainer V0.6.1, Ergebnis-ZIP SHA256 `90c998f22f9ffa329dc33b9ff1e29722e6abe9b70eb344d97c29b85f1c7ed0ec`, 2.141.031 Pass-1- und Replay-Zeilen mit exakter Parität.

## 1. Ziel

Fast Capture ist ein eng begrenzter zusätzlicher Ladepfad für Zendure. Er soll **aktuell vermeidbare Einspeisung schneller aufnehmen**, wenn der Primärspeicher mit hoher Sicherheit entweder

1. **voll und praktisch lade-idle (`FULL_IDLE`)** oder
2. **nahe seiner bekannten Ladeleistungsgrenze (`NEAR_LIMIT`)**

ist.

Der Pfad ist ein **positiver Lade-Overlay** auf den normalen ZEC-AUTO-Ladezielwert. Er ist **kein eigener Vollregler**, kein Entladepfad und kein Ersatz für die bestehende Harvest-/AUTO-Logik.

Normative Priorität bleibt:

> Aktuell vermeidbare Einspeisung hat Vorrang vor strategischer Ladeverteilung; Safety-, Cross-Charge-, SOC- und physische Limits stehen darüber.

## 2. Explizite Nicht-Ziele

Fast Capture darf in diesem Block **nicht**:

- `RESERVE_UNKNOWN` beschleunigen;
- saisonale Ladeverteilung entscheiden;
- den SMA-spezifischen saisonalen Entladeboden (`31009`) verwenden;
- aus einem SMA-spezifischen Verhalten ein allgemeines Primärspeicherprofil machen;
- ein gelerntes Acceptance-/SOH-Modell als harten Leistungsbegrenzer verwenden;
- die globale AUTO-Glättung oder `MAX_POWER_STEP_W` verändern;
- `acMode` unnötig wechseln;
- direkt MQTT publizieren und damit den bestehenden Command-Safety-/Readback-/Late-Effect-Pfad umgehen;
- neue persistente Geräteeinstellungen schreiben.

Der SMA-Saison-SOC-Block bleibt ein separater Entwicklungsblock.

## 3. Warum ein separater Fast-Pfad erforderlich ist

Der reale V16.0.2-Pfad ist heute:

`run_once -> Grid/Primary/Cross-Charge -> Harvest-State -> handle_charge -> normaler Zielwert -> Power-Limit -> Smoothing -> MAX_POWER_STEP -> Cross-Charge -> Safe Command Publisher`.

Dabei begrenzen standardmäßig `SMOOTHING_FACTOR=0.25` und `MAX_POWER_STEP_W=150` die Reaktion. Außerdem hat die bestehende Harvest-Entry-Logik Bestätigungszeiten.

Die bestehende Runtime-Bezeichnung `SMA_FULL_OR_IDLE` darf **nicht** als Fast-Capture-Zustand wiederverwendet werden: V16.0.2 klassifiziert diesen Zweig aus hohem Primär-SOC + Export; ein tatsächliches Idle-Leistungsfenster ist dort nicht Bestandteil der Bedingung. Für Fast Capture wird deshalb ein eigener, strenger Zustandsdetektor benötigt.

Ebenso bleibt die bestehende `SMA_NEAR_LIMIT`-/Harvest-Latch-Logik unangetastet; Fast Capture besitzt eine eigenständige, evidenzbasierte Sofortklassifikation.

## 4. Evidenzprofil A400/R100

Der erste Produktionskandidat ist fest:

- **Attack:** `400 W/s`
- **Release:** `100 W/s`
- **Fast-Scope:** nur `FULL_IDLE` und `NEAR_LIMIT`
- **UNKNOWN:** kein Fast-Overlay

Bei einem typischen frischen Messabstand von etwa 3 s entspricht das maximal ungefähr:

- Attack: `+1.200 W` je frischem Update;
- Release: `-300 W` je frischem Update.

`R100` ist damit doppelt so schnell beim Abbau wie die getestete R50-Variante, aber weiterhin langsamer als die Attack-Rampe. Ein harter Import-/Safety-Abbruch setzt den Overlay unabhängig von R100 **sofort** auf null.

V0.6.1 lieferte für A400/R100 über die eingefrorene Vollhistorie:

- konservativ recoverable: **24,8524 kWh**;
- linearisiert induzierter Import: **0,00992 kWh** über 91 Replay-Zeilen;
- Command-TV gegenüber Baseline: **+20,02 %**;
- Candidate-Richtungswechsel: **2**;
- Primary-Opposition: **738**;
- 30-s-Ping-Pong: **11**.

Diese Werte sind Shadow-/Replay-Evidenz, kein Closed-Loop-Wirkungsnachweis.

## 5. Primärspeicher-Zustandsklassifikation

Die Klassifikation ist **source-neutral**. Sie verwendet die bereits normalisierten Primärspeicherwerte des ZEC; Herstellerlogik gehört in den jeweiligen Source-/Template-Adapter.

### 5.1 Gemeinsame Voraussetzungen

Fast-Klassifikation ist nur zulässig bei:

- AUTO-Betrieb;
- gültiger/frischer Netzleistung;
- gültiger/frischer Zendure-SOC- und Istleistungsinformation;
- gültiger/frischer Primärspeicher-Leistung;
- für `FULL_IDLE`: zusätzlich gültigem/frischem Primärspeicher-SOC;
- konfigurierter positiver Primärspeicher-Maximalladeleistung;
- sicherem Cross-Charge-Zustand;
- keinem Safe-State, keinem aktiven Neutralisierungs-/Command-Uncertainty-Fall;
- Zendure unter `MAX_SOC_PERCENT`;
- positivem bestätigtem Export von mindestens 100 W.

### 5.2 `FULL_IDLE`

`FULL_IDLE` gilt erst, wenn **alle** Bedingungen auf unabhängigen frischen Beobachtungen für mindestens 15 s anliegen:

- Primärspeicher-SOC `>= 99 %`;
- Betrag der normalisierten Primärspeicherleistung `<= 100 W`;
- effektiver Export `>= 100 W`.

Wiederholtes Verarbeiten desselben Quellzeitstempels darf die 15 s nicht fortschreiben. Eine Beobachtungslücke >10 s oder eine verletzte Bedingung setzt die Persistence zurück.

Die bekannte Feldsignatur des Sunny Island mit ungefähr 10 W bei vollem Speicher fällt damit korrekt in diesen Zustand, ohne daraus fälschlich ~2,3 kW freie Ladeleistung abzuleiten.

### 5.3 `NEAR_LIMIT`

`NEAR_LIMIT` gilt bei:

- Primärspeicher lädt positiv;
- `P_primary >= P_primary_max - 150 W`;
- effektiver Export `>= 100 W`.

Für den produktiven SI3.0M mit 2.300 W ergibt sich damit eine Schwelle von 2.150 W.

### 5.4 `RESERVE_UNKNOWN`

Alle übrigen gültigen Fälle mit Export werden `RESERVE_UNKNOWN`.

**Invariante:** `RESERVE_UNKNOWN -> fast_overlay = 0`.

Die normale ZEC-Regelung bleibt dort allein zuständig.

## 6. Zielwertmathematik

Bezeichnungen:

- `B` = normaler ZEC-Baseline-Ladezielwert nach bestehender Power-Begrenzung, Smoothing und globalem Step-Limit;
- `E` = bestätigter effektiver Export in W;
- `Pp` = aktuelle normalisierte Primärspeicher-Ladeleistung in W;
- `Pp_max` = konfigurierte Primärspeicher-Maximalladeleistung;
- `R` = noch nicht sicher vom Primärspeicher ausgeschöpfte Leistungsreserve;
- `O` = Fast-Capture-Overlay;
- `Zmax` = wirksames Zendure-Ladelimit aus Konfiguration und frischem Readback;
- `D` = gewünschter Overlay vor Rate-Limit.

### 6.1 Primärreserve

Für `NEAR_LIMIT`:

`R = max(0, Pp_max - max(0, Pp))`

Für `FULL_IDLE` wird aufgrund der bestätigten Full-/Idle-Signatur **keine nominelle Primärreserve beansprucht**:

`R = 0`

### 6.2 Gewünschter Overlay

`FULL_IDLE`:

`D_raw = E`

`NEAR_LIMIT`:

`D_raw = max(0, E - R)`

`RESERVE_UNKNOWN` / nicht eligible:

`D_raw = 0`

Zendure-Headroom:

`H_Z = max(0, Zmax - max(0, B))`

Damit:

`D = min(D_raw, H_Z)`

Das Acceptance-/Taper-Lernmodell ist **kein** harter Clamp. Real vorhandener Export darf weiterhin zu einem höheren Ziel führen und damit neue Evidenz erzeugen.

## 7. Rate-Limit A400/R100

Rate-Updates verwenden ausschließlich monotone Zeit zwischen **distinct/fresh** Beobachtungen.

Bei kontinuierlicher Beobachtung:

- wenn `D > O`: `O_new = min(D, O + 400 * dt)`;
- wenn `D < O`: `O_new = max(D, O - 100 * dt)`.

Bei erster Beobachtung nach Start/GAP:

- `O_new = 0`;
- erst das nächste frische Intervall darf Attack erzeugen.

Bei `dt <= 0` oder `dt > 10 s`:

- Continuity gilt als gebrochen;
- `O_new = 0`.

## 8. Hard-Abort und kontrollierter Release

### 8.1 Hard-Abort: Overlay sofort auf 0

Unabhängig von R100 wird der Overlay sofort auf null gesetzt bei:

- Grid-Import `> +100 W`;
- Safe-State;
- MAX-/MIN-SOC-Safety-Zweig;
- stale/invalid Grid, Primärspeicher, Zendure SOC oder Zendure Istleistung;
- aktivem Cross-Charge-Detect/Limit;
- Command-Uncertainty oder aktiver sicherheitsrelevanter Neutralisierung;
- MANUAL / FIXED / STOP_HOLD / fester NIGHT-Basissteuerung;
- Wechsel in Entladerichtung;
- Abschalten des Fast-Capture-Modus;
- Verlust der Command-State-/smartMode-Freigabe für aktive Limits.

Hard-Abort bedeutet **Overlay weg**, nicht zwangsläufig Gesamtziel 0. Der normale Baseline-Zielwert bleibt bestehen, sofern nicht eine höhere Safety-Logik selbst neutralisiert.

### 8.2 Controlled Release

Wenn kein bestätigter Export mehr besteht, aber noch kein Hard-Abort vorliegt, wird nur der Overlay mit `100 W/s` abgebaut. Dadurch wird ein unnötig harter Sollwertsprung bei bloßem Exportende vermieden.

## 9. Baseline-Isolation – zwingende Implementierungsinvariante

Der Fast-Overlay darf **niemals in den normalen Reglerzustand zurückgefüttert werden**.

V16.0.2 verwendet heute `last_input_power` als vorherigen Ladezielwert. Nach Einführung des Overlay wäre dieser Wert das kombinierte Ziel `B + O`. Würde die normale Baseline im nächsten Zyklus direkt damit weiterrechnen, würde Fast Capture in den Baseline-Regler „einsickern“ und der Overlay ließe sich nicht mehr sauber freigeben.

Daher sind zwei Zustände getrennt zu führen:

- `fast_capture_baseline_target_w` = letzter normaler Baseline-Zielwert;
- `fast_capture_overlay_w` = ausschließlich zusätzlicher Fast-Anteil.

Die normale Baseline-Rechnung verwendet bei einem laufenden Fast-Episode **den gespeicherten Baseline-Wert als vorheriges Ziel**, nicht den kombinierten `last_input_power`.

Wenn Fast Capture inaktiv und der Overlay 0 ist, wird der Baseline-Zustand wieder mit dem normalen aktuellen Ladeziel synchronisiert.

## 10. Einordnung in die V16.0.2-Zielwertpipeline

Die Zielreihenfolge wird verbindlich:

1. normale AUTO-/Harvest-Baseline berechnen;
2. normale Config-Powerlimits auf Baseline;
3. bestehendes `SMOOTHING_FACTOR` auf Baseline;
4. bestehendes `MAX_POWER_STEP_W` auf Baseline;
5. Fast-Capture-State/Desired-Overlay bestimmen;
6. A400/R100 auf **Overlay**, nicht auf Baseline, anwenden;
7. `combined = baseline + overlay`;
8. kombiniertes Ziel auf `MAX_CHARGE_POWER_W` und frisches Device-Charge-Max-Limit begrenzen;
9. bestehenden symmetrischen Cross-Charge-Limiter anwenden;
10. ausschließlich über `_publish_signed_target()` und den vorhandenen Command-State-/smartMode-/Readback-/Late-Effect-Vertrag publizieren.

Fast Capture **umgeht absichtlich nur die globale 150-W-Baseline-Rampe**, nicht die Safety-/Command-/Device-Limits.

`MAX_POWER_STEP_W` wird nicht global erhöht.

## 11. Branching in `run_once`

Eine aktive Fast-Episode muss auch im Deadband bzw. bei kleinem Netzbezug kontrolliert abbauen können.

Daher gilt:

- bei `fast_overlay > 0` und Grid `<= +100 W` bleibt der Charge-Pfad zuständig, auch wenn der Gridwert im normalen Deadband oder knapp auf Importseite liegt;
- bei Grid `> +100 W` wird der Overlay sofort auf 0 gesetzt; ein Richtungswechsel auf Entladung darf **nicht im selben Schritt erzwungen werden**, sondern folgt danach über den normalen AUTO-Pfad;
- eine bestehende Cross-Charge-Korrektur hat weiterhin Vorrang und kann den Zyklus beenden.

Damit gibt es keine unnötige Charge→Discharge-Umschaltung nur zum Abbau eines Fast-Overlay.

## 12. Settings-Vertrag

Für die erste Produktionsfassung wird **genau eine neue editierbare Einstellung** eingeführt:

### `HARVEST_FAST_CAPTURE_MODE`

Typ: Enum/String  
Kategorie: `Harvest / Restüberschuss`  
Abschnitt: `Fast Capture`  
Sichtbarkeit: `EXPERT`  
Apply: `LIVE_NEXT_CYCLE`  
Default bei Migration und Neuinstallation: `off`

Optionen:

- `off` – kein Fast-Capture-Rechen-/Wirkpfad;
- `shadow` – vollständige Klassifikation und A400/R100-Berechnung/Diagnose, **keine Änderung des Controllerziels und keine zusätzlichen Gerätekommandos**;
- `active` – Overlay wirkt auf den realen Ladezielwert.

### 12.1 Aktivierungsvalidator für `active`

`active` darf nur committed werden, wenn mindestens:

- `REST_SURPLUS_HARVEST_ENABLED=true`;
- `CROSS_CHARGE_ENABLED=true`;
- Primärspeicherintegration konfiguriert;
- `SECOND_BATTERY_MAX_CHARGE_POWER_W > 0`;
- Zendure-Maximalladeleistung >0.

Runtime-Freshness bleibt eine Laufzeitbedingung und wird nicht durch Configvalidierung ersetzt.

### 12.2 Keine editierbaren Tuningparameter in der ersten Fassung

Folgende evidenzgebundenen Werte werden **nicht** als freie Settings angeboten:

- Attack 400 W/s;
- Release 100 W/s;
- Min Export 100 W;
- Import-Guard 100 W;
- Full-SOC 99 %;
- Idle-Fenster 100 W;
- Full-Idle-Persistenz 15 s;
- Near-Limit-Margin 150 W;
- Continuity-Maximum 10 s.

Begründung: Nur A400/R100 mit diesem Klassifikationsprofil ist gegen die Vollhistorie replayt worden. Freie Kombinationen würden ungeprüfte Produktionsvarianten erzeugen.

Die Werte werden in Settings-Hilfe/Diagnose **read-only beschrieben**, aber nicht editierbar gemacht. Spätere Freigabe einzelner Parameter erfordert neue Replay-/Feldevidenz.

### 12.3 Moduswechsel

- `off/shadow -> active`: Overlay startet immer bei 0 und benötigt mindestens ein frisches Folgeintervall; kein Übernehmen eines im Shadow aufgelaufenen Overlay.
- `active -> shadow/off`: vorhandener realer Overlay wird sicher auf die aktuelle Baseline zurückgenommen; danach keine Fast-Wirkung mehr.

## 13. Source-Neutralität / Nicht-SMA-Primärspeicher

Fast Capture ist **nicht SMA-spezifisch**.

Es verwendet ausschließlich source-neutral normalisierte Primärspeicher-Capabilities:

- aktuelle Ladeleistung;
- SOC für `FULL_IDLE`;
- konfigurierte Maximalladeleistung;
- Freshness/Validity.

Ein `evcc_standard`, `custom` oder anderes `modbus_template` darf den Pfad nutzen, **wenn** diese Werte korrekt und frisch vorliegen.

Die SMA-spezifische saisonale Entladeuntergrenze aus Register `31009` gehört ausdrücklich **nicht** in diesen Fast-Capture-Block.

## 14. Runtime-State und Diagnose

Mindestens neue State-/Statusfelder:

- `fast_capture_mode`
- `fast_capture_active`
- `fast_capture_primary_state`
- `fast_capture_block_reason`
- `fast_capture_baseline_target_w`
- `fast_capture_desired_overlay_w`
- `fast_capture_overlay_w`
- `fast_capture_combined_target_w`
- `fast_capture_primary_reserve_w`
- `fast_capture_full_idle_progress_s`
- `fast_capture_observation_dt_s`
- `fast_capture_attack_limited`
- `fast_capture_release_limited`
- `fast_capture_forced_zero_reason`
- `fast_capture_activation_count`
- `fast_capture_forced_zero_count`

Die Statusseite darf klar unterscheiden:

- Mode `off/shadow/active`;
- erkannter Primärzustand;
- Baseline vs. Overlay vs. kombiniertes Ziel;
- Grund, warum Fast Capture blockiert oder beendet wurde.

Keine Eventflut pro Zyklus. Operational Events nur für relevante Zustands-/Fehlerereignisse, nicht für jede Rampenstufe.

## 15. Measurement-V4-Evidenz

Measurement V4 muss die Fast-Capture-Wirkung vollständig rekonstruierbar machen. Additiv aufzunehmen sind mindestens:

- `fast_capture_mode`
- `fast_capture_active`
- `fast_capture_primary_state`
- `fast_capture_block_reason`
- `fast_capture_baseline_target_w`
- `fast_capture_desired_overlay_w`
- `fast_capture_overlay_w`
- `fast_capture_combined_target_w`
- `fast_capture_primary_reserve_w`
- `fast_capture_full_idle_progress_s`
- `fast_capture_observation_dt_s`
- `fast_capture_forced_zero_reason`

Die bestehenden Felder `target_raw_w`, `target_filtered_w`, `target_step_limited_w`, `target_final_w`, Command-Readback und physische Zendure-/Gridwerte bleiben erhalten und bilden zusammen den Wirkungsnachweis.

Die Erweiterung muss über `measurement_v4_contract.py` erfolgen; keine parallele private CSV.

## 16. Geplante Sourceänderungen im Implementierungsblock

Voraussichtlich betroffen:

- `controller_logic.py` – Fast-State, Baseline-Isolation, Overlay/Guard/Branch-Integration;
- `state.py` – Runtime-/Statusdiagnostik;
- `settings_registry.py` – `HARVEST_FAST_CAPTURE_MODE` + strukturierte Hilfe;
- `config_validator.py` – `active`-Abhängigkeiten;
- `measurement_v4.py` – additive V4-Felder;
- `measurement_v4_contract.py` – kanonischer Feldvertrag;
- ggf. `web_ui.py` / UI-Assets / Übersetzungen – Diagnoseanzeige und Settings-Hilfe;
- Tests – neue Fast-Capture-Unit-/Differential-/Command-Safety-/Measurement-Tests.

Nicht erforderlich für diesen Block:

- Änderung an `primary_storage_modbus.py` wegen SMA `31009`;
- Acceptance-/SOH-Modell im Live-Regler;
- Änderung globaler AUTO-Defaults wie `MAX_POWER_STEP_W`, `SMOOTHING_FACTOR`, `CONTROL_GAIN`.

## 17. Pflicht-Tests vor technischer Freigabe

### 17.1 State-/Zeitsemantik

- `FULL_IDLE` erst nach >=15 s distinct/fresh Evidenz;
- identischer Timestamp zählt nicht mehrfach;
- Gap >10 s setzt Persistence/Overlay zurück;
- `NEAR_LIMIT` bei 2.300-W-Primärmax ab 2.150 W;
- `RESERVE_UNKNOWN` erzeugt niemals Overlay.

### 17.2 A400/R100

- bei 3,0 s dt maximal +1.200 W Attack;
- bei 3,0 s dt maximal -300 W Release;
- erster Sample nach Gap erzeugt 0 W Overlay;
- Zendure-Headroom wird nie überschritten.

### 17.3 Safety

- Import >100 W -> Overlay sofort 0;
- MAX_SOC -> vorhandene SOC-Hold-Semantik unverändert;
- Cross-Charge -> Overlay 0 / bestehender Limiter gewinnt;
- stale Grid/Primary/Zendure -> Overlay 0;
- Manual/Night/Stop/Safe-State -> keine Fast-Wirkung;
- Command-State nicht READY / smartMode nicht frisch geschützt -> keine aktive Fast-Leistungsänderung.

### 17.4 Baseline-Isolation

- Overlay darf nicht in die nächste Baseline eingehen;
- nach Overlay-Ende konvergiert Baseline sauber auf normalen AUTO-Zustand;
- Feature `off` muss gegen V16.0.2 einen Differential-No-Regression-Nachweis liefern.

### 17.5 Command-/Hardwareschonung

- gleiche Laderichtung aktualisiert nur das volatile Input-Limit, soweit bestehender Command-State READY;
- keine zusätzlichen `acMode`-Wechsel durch Fast-Capture-Rampen;
- keine zyklusweisen identischen Republishs;
- `MIN_COMMAND_CHANGE_W`/bestehende MQTT-Deduplizierung bleiben wirksam;
- kein persistenter Gerätewrite;
- Late-Effect-Guard und Resync bleiben unverändert wirksam.

### 17.6 Measurement/Status

- Baseline, Overlay, combined und final target stimmen mathematisch;
- Shadow-Modus verändert `target_final_w` nicht;
- Active-Modus ist aus V4 vollständig rekonstruierbar;
- keine stale Fast-Felder nach Mode-/Safety-Wechsel.

## 18. Freigabesequenz

### Phase 1 – Build / Differential

- vollständiger bestehender Testbestand;
- neue Fast-Capture-Tests;
- `ResourceWarning=error`;
- Compile-/Syntax-/Fresh-Extract-Gates;
- expliziter Differentialnachweis: `HARVEST_FAST_CAPTURE_MODE=off` verändert den V16.0.2-Regler nicht.

### Phase 2 – reale Shadow-Abnahme

Zuerst `shadow`, kein realer Overlay.

Nachzuweisen:

- 0 zusätzliche Fast-Capture-Gerätekommandos;
- `FULL_IDLE` entspricht real hohem SOC + Idle-Power + Export;
- `NEAR_LIMIT` entspricht realer Primärleistung nahe Max;
- UNKNOWN bleibt ohne Overlay;
- A400/R100-Candidate und Blockgründe plausibel;
- keine Daten-/Timingprobleme.

### Phase 3 – begrenzte Active-Feldabnahme

Erst nach Shadow-PASS `active`.

Pflichtbeobachtung:

- reale Exportreduktion nach Fast-Attack;
- keine neu verursachte persistente Netzaufnahme;
- keine zusätzliche Charge/Discharge-Oszillation;
- keine unnötigen `acMode`-Änderungen;
- Cross-Charge-/SOC-/Safe-State-Abbruch korrekt;
- Command-Readback/Effect bleibt gesund;
- Hardware-Schonungsmetriken zeigen keine neue problematische Richtungswechsel-/Ping-Pong-Klasse.

Ein gesendeter Sollwert allein ist kein Wirksamkeitsnachweis.

## 19. Abnahmekriterien für den ersten Active-PASS

Mindestens:

1. kein Safety-/Cross-Charge-Verstoß;
2. kein Fast-Overlay in `RESERVE_UNKNOWN`;
3. keine Fast-bedingte zusätzliche `acMode`-Änderung innerhalb gleicher Laderichtung;
4. kein Fast-bedingtes Charge↔Discharge-Ping-Pong innerhalb 30 s;
5. Import-Guard >100 W entfernt den Overlay im nächsten ausführbaren sicheren Command-Schritt;
6. FULL_IDLE-/NEAR_LIMIT-Klassifikation ist durch V4-Rohwerte reproduzierbar;
7. reale Zendure-Leistung folgt dem Fast-Ziel ausreichend, oder Abweichungen werden durch bestehenden Command-Effect-/Mismatch-Pfad sichtbar;
8. `off` und `shadow` bleiben mutationsfrei bezüglich Fast-Capture-Leistungswirkung;
9. kein Acceptance-Lernwert verhindert die Aufnahme von real bestätigtem Export;
10. Checkpoint-/Release-/Rollbackvertrag des ZEC-Projekts vollständig erfüllt.

## 20. Implementierungsgrenze

Diese Spezifikation ist **noch keine Source-Freigabe**. Vor Implementierung muss der Entwicklungsblock auf der dann aktuellen kanonischen Sourcebasis revalidiert werden. Falls vorher ein anderer Sourceblock (z. B. SMA-Saison-Capability/Settings-Hygiene) umgesetzt wurde, ist diese Spezifikation gegen dessen Checkpoint neu zu diffen; keine parallelen ungesicherten Working Trees.
