# Spezifikation V12.11.2-RC13
## RC12-Nachkorrektur: Command-State-Gate, Neutralization-Dedupe, Command-Effect und Publish-Vertrag

**Stand:** 27.07.2026  
**Basis:** V12.11.2-RC12  
**Status:** Spezifikation zur Freigabe; noch keine Codeänderung  
**Normative Analysegrundlage:** `ZEC_ANALYSE_REGELWERK_V1.1.md`

---

## 1. Anlass und Ziel

Die Produktivanalyse des RC12-Morgenzyklus bestätigte die grundsätzlichen RC12-Verbesserungen:

- `smartMode=1` blieb produktiv aktiv,
- die Zendure-Leistungsgrenzen wurden korrekt getrennt,
- normale gleichgerichtete Sollwertänderungen schrieben überwiegend nur das aktive Limit,
- Nachtentladung und normale AUTO-Regelung waren physikalisch plausibel,
- Offgrid-Leistung blieb separat.

Gleichzeitig wurden drei produktiv relevante Fehler nachgewiesen:

1. vollständige 0-W-Neutralisierungsbatches wurden in stabilen MIN-/MAX-SOC-, Cross-Charge- und Safe-State-Episoden zyklusweise wiederholt;
2. das 30-s-Command-State-Retry-Fenster wurde durch wechselnde `FULL_STATE_VERIFY`-/`FULL_STATE_APPLY`-Signaturen ausgehebelt;
3. natürliche Ladeleistungsreduktion im oberen SOC-Bereich wurde teilweise als Command-Mismatch behandelt und löste unnötige Full-State-Resyncs aus.

RC13 soll ausschließlich diese Fehler korrigieren. Die Regler-Zielwertbildung außerhalb der Command-/Wirkungsschicht bleibt unverändert.

---

## 2. Verbindlicher Scope

### 2.1 Bestandteil

1. Neutralization-Episodenmodell und Deduplizierung.
2. Einheitliches Command-State-Gate mit real wirksamem 30-s-Retry-Fenster.
3. Strikte Sperre nicht neutraler Leistungsbefehle ohne frisch bestätigtes `smartMode=1`.
4. Kombinierte absolute und relative Trackingtoleranz.
5. Frühe, physikalisch abgesicherte Erkennung von Ladeannahme-/BMS-Taper.
6. Saubere Segmentierung von Mismatch, MQTT-Ausfall, Recovery und Intentwechsel.
7. Eindeutiger Publish-Event-Vertrag mit Event-ID und Epoch.
8. Additive Measurement-V4-Felder und Headerrotation für RC13.
9. Intended-Delta- und No-Regression-Tests.

### 2.2 Nicht Bestandteil

- keine Korrektur der `SMA_FULL_OR_IDLE`-Absolutzielberechnung;
- keine Änderung der Harvest-Entry-/Hold-/Exit-Formeln;
- keine asynchrone Entkopplung der lokalen Zendure-API;
- keine Änderung von `gridOffMode` oder anderen persistenten Geräteeinstellungen;
- kein produktiver Offgrid-Steckdosentest;
- keine Readiness-Neudefinition;
- keine Bereinigung des sticky `last_error`;
- keine Behebung der beobachteten `control_soc_percent`-Snapshotlücke;
- kein Settings-Redesign;
- keine Änderung der Excel-Lernsimulation.

---

## 3. Sicherheitsinvarianten

### 3.1 Flash-Schutz

Für jeden nicht neutralen dynamischen Leistungsbefehl muss gelten:

```text
zendure_command_smart_mode == 1
UND smartMode frisch
UND zendure_flash_protection_active == true
```

Ist diese Invariante nicht erfüllt:

```text
keine Veröffentlichung von acMode,
inputLimit > 0 oder outputLimit > 0
```

Zulässig ist ausschließlich:

```text
smartMode = ON
```

und anschließend das Warten auf eine frische Rücklesung.

### 3.2 Neutralisierungs-Ausnahme

Eine sicherheitsrelevante 0-W-Neutralisierung darf bei unsicherem Command-State einmalig ausgeführt werden, um eine fortgesetzte Lade- oder Entladewirkung zu stoppen.

Dabei gelten zwingend:

- höchstens ein vollständiger Nullbatch je Retry-Fenster;
- `smartMode=ON` wird vor beziehungsweise zusammen mit dem Sicherheitszustand angefordert;
- keine zyklusweise Wiederholung;
- nach frischer Rücklesung und physischer 0-W-Bestätigung vollständige Deduplizierung;
- erneuter Versand nur bei bestätigter Nichtwirkung, Reconnect/Invalidierung oder Ablauf des Retry-Fensters.

### 3.3 Schreib-Whitelist

Der Runtime-Pfad darf weiterhin nur schreiben:

```text
smartMode = ON
acMode
inputLimit
outputLimit
```

Nicht geschrieben werden:

```text
inverseMaxPower
chargeMaxLimit
gridOffMode
socSet
minSoc
gridStandard
gridReverse
```

---

## 4. Neutralization-Episodenmodell

### 4.1 Physischer Schlüssel

Die Deduplizierung orientiert sich am physischen Zielzustand, nicht allein am Reason-Text:

```text
intent = NEUTRALIZE
acMode
inputLimit = 0
outputLimit = 0
```

Ein Reason-Wechsel wie:

```text
MIN_SOC_LIMIT → SAFE_STATE
```

ändert die fachliche Begründung, aber nicht automatisch den physischen Gerätebefehl.

### 4.2 Eintritt

Beim Übergang von CHARGE/DISCHARGE zu NEUTRALIZE:

1. neue Neutralization-Episode anlegen;
2. frischen Command-State prüfen;
3. wenn der rückgelesene Zustand bereits vollständig 0 W ist:
   - keinen unnötigen MQTT-Publish erzeugen,
   - physische Neutralität prüfen;
4. andernfalls genau einen `FULL_STATE_NEUTRALIZATION_SENT` ausführen;
5. 30-s-Neutralization-Watch starten.

### 4.3 Stabiler neutraler Zustand

Sobald die physische Neutralität bestätigt ist:

```text
COMMAND_NEUTRALIZATION_CONFIRMED
```

Danach:

- keine erneuten 0-W-Batches in derselben Episode;
- `MIN_SOC`, `MAX_SOC`, `SAFE_STATE`, `STOP_HOLD`, Cross-Charge-Block oder Deadband dürfen nicht je Zyklus erneut schreiben;
- Reason-Wechsel erzeugen höchstens ein Diagnoseereignis `NEUTRALIZATION_REASON_UPDATED`.

### 4.4 Nichtwirkung und Recovery

Bleibt die beobachtete netzseitige Leistung nach 30 s außerhalb der Neutralisierungstoleranz:

```text
COMMAND_NEUTRALIZATION_MISMATCH
```

Dann:

- Full-State-Resync für 0 W zulässig;
- Resync-Cooldown weiterhin 120 s;
- physische Wiederherstellung separat bestätigen;
- kein Dedupe-Latch: jeder bestätigte Mismatch muss nach Cooldown erneut recoveryfähig sein.

### 4.5 Ereignisse, die eine neue physische Episode erlauben

- vorheriger aktiver CHARGE-/DISCHARGE-Intent;
- MQTT-/Geräte-Reconnect mit Command-State-Invalidierung;
- bestätigter Neutralization-Mismatch;
- tatsächliche Abweichung der rückgelesenen Limits von 0 W;
- Wechsel des erforderlichen AC-Modus aufgrund einer echten Topologie-/Richtungsänderung.

Ein bloßer Reason-Wechsel bei identischem Nullzustand reicht nicht.

---

## 5. Einheitliches Command-State-Gate

### 5.1 Zustände

```text
UNPROTECTED
WAIT_SMART_MODE_READBACK
WAIT_FULL_STATE_READBACK
READY
SAFETY_NEUTRALIZATION_WAITING
```

### 5.2 Ablauf für aktive Lade-/Entladeziele

#### Zustand A – Smart Mode nicht frisch oder nicht 1

```text
smartMode=ON einmal senden
→ WAIT_SMART_MODE_READBACK
→ keine aktiven Limits senden
```

Weitere Zyklen dürfen vor Ablauf von `ZENDURE_COMMAND_STATE_RETRY_SECONDS` keine erneute Veröffentlichung erzeugen.

#### Zustand B – Smart Mode frisch 1, übriger Command-State unvollständig

```text
ein Full-State-Batch für den aktuellsten gewünschten Intent
→ WAIT_FULL_STATE_READBACK
```

Danach:

- 30 s warten oder früher durch vollständige Rücklesung READY werden;
- wechselnde exakte Wattziele innerhalb derselben Richtung umgehen das Retry-Fenster nicht;
- das jeweils neueste Ziel wird gespeichert und beim nächsten zulässigen Publish verwendet.

#### Zustand C – Command-State vollständig und statische Invarianten bestätigt

```text
READY
```

Normale gleiche Richtung:

```text
nur aktives Limit schreiben
```

Richtungswechsel:

```text
ein vollständiger State:
acMode + Gegenlimit 0 + aktives Limit
```

`smartMode=ON` wird nur ergänzt, wenn der Wert nicht frisch 1 ist oder ein ausdrücklich freigegebener Recovery-Resync vorliegt.

### 5.3 Einheitlicher Retry-Schlüssel

Die zwei RC12-Signaturen:

```text
FULL_STATE_VERIFY
FULL_STATE_APPLY
```

werden durch einen einzigen Retry-Zustand ersetzt.

Der Retry-Schlüssel darf nicht vom exakten Wattwert abhängen. Er enthält höchstens:

```text
Gerät
Gate-Phase
fachlicher Intent
Sicherheitsklasse
```

Eine normale Zieländerung von beispielsweise:

```text
+1.800 → +2.100 → +1.950 W
```

setzt das 30-s-Fenster nicht zurück.

### 5.4 Force-/Resync-Verhalten

`force=True` darf den Flash-Schutz für nicht neutrale Ziele nicht umgehen.

Bei aktivem Ziel und nicht frischem `smartMode=1`:

```text
Resync-Anforderung
→ smartMode=ON
→ Rücklesung abwarten
→ erst danach Full-State des aktuellen aktiven Intents
```

Bei sicherheitsrelevantem 0-W-Ziel bleibt die begrenzte Neutralisierungs-Ausnahme aus Abschnitt 3.2 zulässig.

---

## 6. Command-Effect- und Taper-Semantik

### 6.1 Qualitätsstufen

```text
COMMAND_PENDING
COMMAND_DIRECTION_EFFECTIVE
COMMAND_PARTIALLY_EFFECTIVE
COMMAND_TARGET_TRACKING_EFFECTIVE
COMMAND_CHARGE_ACCEPTANCE_LIMITED
COMMAND_MISMATCH_CONFIRMED
COMMAND_TELEMETRY_UNCERTAIN
```

Ein Publish ist weiterhin kein Wirkungsnachweis.

### 6.2 Hybride Trackingtoleranz

Neue Trackingtoleranz:

```text
effective_tolerance_w =
max(
    COMMAND_EFFECT_TOLERANCE_W,
    abs(target_w) × COMMAND_EFFECT_TOLERANCE_PERCENT / 100
)
```

Vorgeschlagener Default:

```text
COMMAND_EFFECT_TOLERANCE_PERCENT = 10
```

Beispiel:

```text
Soll +2.397 W
Ist  +2.233 W
Fehler 164 W = 6,8 %
→ TARGET_TRACKING_EFFECTIVE
```

Die relative Toleranz betrifft ausschließlich die Wirkungsdiagnose. Sie verändert keinen Regler-Sollwert und keine Leistungsgrenze.

### 6.3 Teilwirkung

Gleiche physische Richtung, aber außerhalb der Trackingtoleranz:

```text
COMMAND_PARTIALLY_EFFECTIVE
```

Dabei bleiben getrennt sichtbar:

- Richtung reagiert;
- Sollwerttracking nicht erreicht;
- Systemziel möglicherweise nicht erreicht.

Eine Teilwirkung darf nicht als vollständiger Erfolg erscheinen.

### 6.4 Ladeannahme-/BMS-Taper

`COMMAND_CHARGE_ACCEPTANCE_LIMITED` darf bereits vor `MAX_SOC-2` greifen.

Vorgeschlagene Taper-Zone:

```text
SOC >= MAX_SOC_PERCENT - 10 Prozentpunkte
```

Die Klassifikation setzt gemeinsam voraus:

1. Sollrichtung CHARGE;
2. `smartMode=1` frisch bestätigt;
3. rückgelesener Command-State stimmt mit dem gewünschten Ladebatch überein;
4. netzseitiger AC-Bezug in Laderichtung ist bestätigt;
5. `outputPackPower` bestätigt reale Batterieladung;
6. keine widersprechende Entladung über `outputHomePower`/`packInputPower`;
7. SOC ist frisch und fällt innerhalb der Episode nicht physikalisch widersprüchlich;
8. die Ladeannahmediagnose meldet `limited` oder `not_accepting`.

Wirkung:

- kein Command-Mismatch allein aufgrund geringerer Istleistung;
- kein periodischer Full-State-Resync;
- Sollwerttracking bleibt ausdrücklich **nicht** bestätigt;
- Restexport/Systemziel bleibt als nicht erreicht sichtbar.

### 6.5 Mismatch bleibt möglich

Ein Mismatch muss weiterhin entstehen, wenn beispielsweise:

```text
SOC 10 %
Soll +2.397 W
Ist 0 W
```

oder:

```text
SOC 10 %
Soll +2.397 W
Ist +100 W über längere Zeit
Command-State unvollständig oder abweichend
```

Die Recovery-Kette vom 25.07. darf nicht abgeschwächt werden:

```text
persistente Nichtwirkung
→ Mismatch
→ Full-State-Resync
→ physische Wirkung separat bestätigen
```

### 6.6 Telemetrieausfall und neue Episoden

Bei MQTT-/SOC-Ausfall:

- Effect-Timer pausieren;
- alter Mismatch-Reason nicht als aktuelle physische Aussage fortschreiben;
- nach Recovery neue Verifikationsphase beginnen;
- Recovery-Resync und alter Mismatch sind getrennte Episoden;
- ein neuer Intent beendet den alten Mismatch als `SUPERSEDED` oder `ABORTED`, nicht als `RECOVERED`.

---

## 7. Publish- und Measurement-Vertrag

### 7.1 Neue Felder

Additiv:

```text
command_publish_event_id
command_publish_epoch_s
command_state_gate_state
command_state_retry_remaining_s
command_neutralization_episode_id
```

### 7.2 Semantik

`command_publish_event_id`:

- monoton steigend;
- wird nur erhöht, wenn mindestens ein MQTT-Property-Publish tatsächlich ausgeführt wurde;
- bleibt in Snapshot-Folgezyklen unverändert.

`command_publish_epoch_s`:

- Epoch des tatsächlichen logischen Publish-Batches;
- ändert sich nur bei einem neuen Publish.

`command_sent_flag`:

- bleibt zyklusbezogen;
- `1` nur im tatsächlichen Publish-Zyklus.

`command_publish_event` und `command_publish_fields`:

- bleiben kompatibel als Last-Event-Snapshotfelder;
- Dokumentation und Hilfetext müssen dies ausdrücklich sagen.

### 7.3 Headerrotation

RC12-Dateien werden nicht verändert. RC13 startet wegen der additiven V4-Felder eine neue Measurement-Datei mit RC13-Contract-ID.

---

## 8. Current-vs-New-Matrix

| Fall | RC12 | RC13-Ziel |
|---|---|---|
| Dauerhaft MIN_SOC | jeder Zyklus Full-State 0 W | einmal neutralisieren, bestätigen, deduplizieren |
| Dauerhaft MAX_SOC | jeder Zyklus Full-State 0 W | einmal neutralisieren, bestätigen, deduplizieren |
| Cross-Charge blockiert mehrere Zyklen | wiederholte Nullbatches | eine Neutralization-Episode |
| Reason MIN_SOC → SAFE_STATE bei weiter 0 W | neuer physischer Publish möglich | nur Reason-/Ereignisupdate |
| Command-State unvollständig | VERIFY/APPLY-Signaturen alternieren | ein Gate, reales 30-s-Fenster |
| Ziel ändert sich innerhalb CHARGE | kann Retry erneut freigeben | neuestes Ziel speichern, Retry nicht zurücksetzen |
| aktiver Resync bei Smart Mode stale | aktive Limits möglich | nur Smart Mode aktivieren, dann warten |
| Soll 2.397 W / Ist 2.233 W | Mismatch nach 90 s | Tracking effektiv durch 10-%-Toleranz |
| SOC 93–96 %, Ladung tapert | periodische Mismatches/Resyncs | Acceptance limited, kein Resync |
| SOC 10 %, Soll 2.397 W / Ist 0 W | Mismatch/Resync | unverändert |
| Offgrid 400 W, Hausausgang 0 W | neutral korrekt | unverändert |
| Publish-Snapshot in Folgezyklen | analytisch missverständlich | Event-ID/Epoch machen echte Publishes eindeutig |

---

## 9. Intended-Delta-Tests

### 9.1 Neutralization-Dedupe

1. `MIN_SOC_LIMIT`, 100 Zyklen:
   - genau ein initialer Nullbatch;
   - nach bestätigter Neutralität kein weiterer Publish.

2. `MAX_SOC_LIMIT`, 100 Zyklen:
   - identische Erwartung.

3. `SAFE_STATE`, 100 Zyklen:
   - identische Erwartung.

4. `CROSS_CHARGE_BLOCKED`, 20 Zyklen:
   - ein Nullbatch, kein Zyklusspam.

5. Reason-Wechsel bei identischem Nullzustand:
   - `MIN_SOC_LIMIT → SAFE_STATE`;
   - kein zweiter physischer Publish;
   - Diagnosegrund aktualisiert.

6. Nicht wirksame Neutralisierung:
   - Soll 0 W, Ist bleibt −400 W;
   - Mismatch nach 30 s;
   - Full-State-Resync nach zulässigem Cooldown;
   - Recovery bleibt wiederholbar.

7. Reconnect während bestätigter Neutralität:
   - Command-State invalidiert;
   - höchstens ein Safety-Nullbatch je 30 s;
   - nach Rücklesung erneut dedupliziert.

8. NIGHT-Reserve plus Startup-Deadband im selben Zyklus:
   - maximal ein physischer Nullbatch.

9. Offgrid-Last:
   - `gridOffPower=400 W`, `packInputPower=400 W`, `outputHomePower=0 W`;
   - netzseitige Neutralisierung bestätigt;
   - Offgrid-Konfiguration unverändert.

### 9.2 Command-State-Gate

1. Smart Mode stale, aktives Ladeziel:
   - nur `smartMode=ON`;
   - kein `acMode`, kein aktives Limit.

2. Smart Mode frisch 1, übriger State unvollständig:
   - ein Full-State-Batch;
   - danach 30 s `COMMAND_STATE_WAITING`.

3. Zieländerungen alle 3 s innerhalb CHARGE:
   - Retry-Fenster bleibt erhalten;
   - kein Full-State-Spam.

4. Richtungsflattern während ungeschütztem Zustand:
   - keine aktiven Limits;
   - nach READY nur aktueller Intent wird angewandt.

5. Sicherheitsneutralisierung bei ungeschütztem Zustand:
   - einmaliger Nullbatch;
   - maximal ein Retry je 30 s.

6. READY, gleiche Richtung:
   - ausschließlich aktives Limit wird aktualisiert.

7. MQTT-Reconnect:
   - State invalidiert;
   - Smart Mode neu bestätigen;
   - aktive Limits erst danach.

8. Force-Resync bei stale Smart Mode:
   - Force umgeht den Schutz nicht.

### 9.3 Command Effect und Taper

1. Soll +2.397 W, Ist +2.233 W:
   - `COMMAND_TARGET_TRACKING_EFFECTIVE`;
   - kein Mismatch.

2. Soll +2.397 W, Ist +1.900 W, SOC 93 %, State exakt rückgelesen:
   - `COMMAND_CHARGE_ACCEPTANCE_LIMITED`;
   - kein Resync.

3. Taper +1.900 → +800 W, SOC 93 → 96 %:
   - kein periodischer Resync über mindestens 10 min.

4. Soll +2.397 W, Ist +100 W, SOC 10 %:
   - zunächst Teilwirkung;
   - nach Timeout Mismatch;
   - Recovery-Resync zulässig.

5. Soll +2.397 W, Ist 0 W:
   - Mismatch und Resync unverändert.

6. Soll unter Diagnosegrenze:
   - `COMMAND_BELOW_DIAGNOSTIC_THRESHOLD`;
   - niemals „effective“.

7. MQTT-Ausfall:
   - Timer pausiert;
   - Recovery bildet neue Episode.

8. Richtungs-CONFLICT:
   - `COMMAND_TELEMETRY_UNCERTAIN`;
   - Sollrichtung wird nicht als Beweis verwendet.

9. Rückgelesener Command-State widerspricht Soll:
   - Mismatch/Command-State-Recovery bleibt aktiv.

### 9.4 Publish-Vertrag

1. Event-ID erhöht sich exakt einmal pro logischem Batch.
2. Event-ID und Epoch bleiben in Snapshot-Folgezyklen konstant.
3. `command_sent_flag=1` nur im tatsächlichen Publish-Zyklus.
4. Deduplizierte Zyklen verändern Event-ID/Epoch nicht.
5. RC12→RC13 erzeugt neue CSV-Datei mit korrektem Header.
6. Replay-/Analyseparser erkennen die additiven Felder.

---

## 10. No-Regression-Tests

Unverändert bleiben müssen:

- NIGHT_DISCHARGE −400 W und Reserve-SOC;
- Nachtfensterende und physische 0-W-Wirkung;
- AUTO_GRID_IMPORT- und AUTO_GRID_EXPORT-Zielwerte;
- Deadband-/HOLD-Zielwertlogik;
- FIXED_CHARGE, FIXED_DISCHARGE und STOP_HOLD;
- symmetrische Cross-Charge-Zielwertberechnung;
- Harvest-Entry, -Hold, -Exit und Zielwertformeln;
- `HARVEST_HIGH_SMA_SOC`;
- Gerätecap-Klemmung;
- Offgrid-Trennung;
- kein Runtime-Pfad für `smartMode=OFF`;
- keine Schreibpfade für persistente Gerätecaps/Offgrid-Konfiguration;
- bestehende Recovery bei echter 0-W-Nichtwirkung;
- Excel-Lernsimulation bitidentisch;
- lokale API-Architektur unverändert.

---

## 11. Abnahmekriterien

RC13 gilt buildseitig als bestanden, wenn:

1. alle bisherigen Tests plus neue RC13-Tests grün sind;
2. keine kontinuierliche Neutralization-Episode mehr als einen initialen Nullbatch erzeugt, solange kein Recovery-Grund eintritt;
3. kein nicht neutraler Limit-Publish bei `zendure_flash_protection_active != true` möglich ist;
4. das 30-s-Retry-Fenster durch Zielwertänderungen nicht umgangen wird;
5. die produktive Taper-Episode 12:33–12:43 aus RC12 im Regressionstest keinen Full-State-Resync mehr erzeugt;
6. der echte Recovery-Fall mit 0 W Istleistung weiterhin Mismatch und Full-State-Resync auslöst;
7. Event-ID/Epoch tatsächliche Publishes eindeutig abbilden;
8. keine Änderung der Harvest-Zielwertformeln enthalten ist;
9. kein neues Latch, keine Race Condition und keine Prioritätsumkehr entsteht.

Produktiv zu validieren sind anschließend mindestens:

- längere MIN_SOC- und MAX_SOC-Episoden ohne Nullspam;
- Wolkenbetrieb mit vielen gleichgerichteten Zieländerungen;
- Ladeende/Taper ohne falsche Resync-Serie;
- echter Reconnect mit Smart-Mode-Rückbestätigung;
- NIGHT-Ausgang und Cross-Charge-Neutralisierung;
- später separat Offgrid mit ungefährlichem Verbraucher.

---

## 12. Voraussichtlich geänderte Dateien

```text
controller_logic.py
command_lifecycle.py
state.py
measurement.py
measurement_v4.py
measurement_v4_contract.py
operational_events.py
config_manager.py
config.example.json
README.md
README_INSTALLATION.md
version.py
tests/test_v12_11_2_rc13_command_safety_followup.py
bestehende Tests mit bewusst präzisierter Semantik
```

`mqtt_bridge.py` nur, falls für die Gate-Zustände zusätzliche reine Diagnoseinformationen erforderlich sind. Keine Änderung der verifizierten Topics oder Payloads.

---

## 13. Releasebezeichnung

```text
V12.11.2-RC13
Arbeitstitel:
Command Safety Follow-up / Neutralization Dedupe / Taper Classification
```
