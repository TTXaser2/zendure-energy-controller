# Technische Hinweise – Zendure Energy Controller V12.11.2-RC11

## 1. Zweck

RC11 ist **Stufe A** des freigegebenen P1-Robustheitsblocks nach der Produktivstörung vom 25.07.2026. Der Release schließt die bestätigten Lücken in der Command-Safety- und Recovery-Schicht, ohne gleichzeitig die Harvest-Zielwertrechnung oder die lokale API-Architektur umzubauen.

Normative Analysegrundlage:

```text
ZEC_ANALYSE_REGELWERK.md, Revision 1.1
```

## 2. Bestätigte RC10-Ursachen

RC10 hatte folgende zusammenhängende Probleme:

1. Ein Sollwert von 0 W wurde als `no_command` behandelt und daher nicht auf physische Wirkung überwacht.
2. `_force_resend_signed_target()` konnte 0 W nicht erneut senden.
3. Jede Änderung des exakten Sollwerts startete den Command-Effect-Timer neu.
4. Eine geringe gleichgerichtete Istleistung oberhalb `COMMAND_EFFECT_MIN_W` konnte als vollständige Wirkung gelten.
5. Zielwerte unter `COMMAND_EFFECT_MIN_TARGET_W` wurden trotz 0 W Istleistung als `COMMAND_EFFECTIVE` bezeichnet.
6. Die Vorzeichenableitung des mehrdeutigen `packInputPower` konnte die Sollrichtung als Beweis verwenden.
7. Resync-Versand und physisch bestätigte Recovery waren in Diagnose und UI nicht sauber getrennt.

## 3. Desired Command Batch

RC11 führt einen in-memory Command-Vertrag ein:

```text
DesiredCommandBatch
├─ sequence_id
├─ intent: CHARGE / DISCHARGE / NEUTRALIZE
├─ ac_mode
├─ input_limit_w
├─ output_limit_w
├─ signed_target_w
├─ reason
├─ safety_relevant
└─ created_epoch
```

Alle produktiven Controllerpfade verwenden den zentralen Batch-Publisher. Der Dispatcher enthält keine Datei-, Datenbank- oder Netzwerk-Leseoperation und wartet nicht auf Gerätebestätigungen.

Ein identischer gewünschter Gerätezustand behält seine Sequenz-ID. Ein neuer Zielzustand erhält eine neue Sequenz-ID.

## 4. Aktive Neutralisierung

0 W ist jetzt ein vollständiger gewünschter Gerätezustand:

```text
AC-Modus
inputLimit = 0
outputLimit = 0
```

Der Neutralization-Watch wird für sicherheitsrelevante Übergänge aktiviert, insbesondere:

- Nachtfensterende,
- Nachtreserve,
- MIN_SOC und MAX_SOC,
- Safe-State,
- manueller STOP,
- Abschluss fester Modi,
- Cross-Charge-Neutralisierung,
- explizite Richtungsneutralisierung.

Default:

```text
COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS = 30
```

Bleibt die beobachtete Leistungsgröße oberhalb der normalen Effect-Toleranz, entsteht `COMMAND_NEUTRALIZATION_MISMATCH`. Der vollständige neutrale Batch kann trotz MQTT-Deduplizierung erneut erzwungen werden.

Wiederholungen sind möglich bei neuer Episode, Reconnect, Neustart, bestätigter Fehlwirkung und nach Ablauf des Recovery-Cooldowns. Derselbe stabile 0-W-Zustand wird nicht in jedem Zyklus force-gesendet.

## 5. Intentbasierter Command-Effect-Watch

RC11 unterscheidet:

```text
COMMAND_BELOW_DIAGNOSTIC_THRESHOLD
COMMAND_PENDING
COMMAND_PARTIALLY_EFFECTIVE
COMMAND_TARGET_TRACKING_EFFECTIVE
COMMAND_MISMATCH_CONFIRMED
COMMAND_NEUTRALIZATION_PENDING
COMMAND_NEUTRALIZATION_CONFIRMED
COMMAND_NEUTRALIZATION_MISMATCH
COMMAND_RECOVERY_VERIFYING
COMMAND_TELEMETRY_UNCERTAIN
COMMAND_POWER_DIRECTION_AMBIGUOUS
COMMAND_POWER_DIRECTION_CONFLICT
```

Kleine Zieländerungen derselben Lade- oder Entladerichtung setzen die Richtungsbeobachtung nicht zurück.

Die Wirkung wird abgestuft bewertet:

1. Publish-Ereignis,
2. belastbare Richtungsreaktion,
3. Teilwirkung,
4. Sollwerttracking innerhalb der Toleranz,
5. fachliches Systemziel als separate Analyseebene.

Eine persistente erhebliche Teilwirkung wird nach Timeout als Mismatch behandelt und bleibt Full-State-Resync-fähig.

## 6. Unabhängige Leistungsbeobachtung

Das neue Observation-Modell hält getrennt:

```text
Rohsensorwerte
Richtung
signed Leistung oder unbekannt
Magnitude
Confidence
Begründung
Alter
```

Evidenz:

- `gridInputPower` bestätigt Ladung,
- `outputHomePower` beziehungsweise `outputPackPower` bestätigt Entladung,
- gleichzeitige explizite Lade- und Entladeevidenz ergibt `CONFLICT`,
- isolierter relevanter `packInputPower` ergibt `AMBIGUOUS`, nicht automatisch Laden oder Entladen.

Für eine Neutralisierung genügt die Magnitude: Bleiben beispielsweise rund 400 W sichtbar, ist 0 W nicht bestätigt, auch wenn die Richtung unklar ist.

Die bisherige signed Istleistung bleibt aus Kompatibilitätsgründen bestehen. Command-Effect und Neutralization-Watch verwenden die unabhängige Beobachtung, sobald Rohdaten vorliegen.

## 7. Recovery-Semantik

Ein Full-State-Resync setzt nicht mehr implizit „erfolgreich“.

```text
FULL_STATE_RESYNC_SENT
→ COMMAND_RECOVERY_VERIFYING
→ erst physische Telemetrie bestätigt Recovery
```

Ein bestätigter Mismatch bleibt bei vorübergehend unklarer Telemetrie offen. Verlust der Beobachtbarkeit ist keine Wiederherstellung.

## 8. Status, Betriebsjournal und Measurement V4

Statusseite:

```text
Letzter ausgeführter Zendure-Kommandoabgleich
Wirkung anschließend bestätigt
```

Das Betriebsjournal führt getrennt:

- Kommando nicht wirksam,
- Kommandoabgleich ausgeführt,
- Kommandowirkung wiederhergestellt.

Measurement V4 erhält additive Felder für:

- vollständigen gewünschten Command-Batch,
- Publish-Ereignis und veröffentlichte Felder,
- Lifecycle- und Effect-Kategorie,
- Effect-Bestätigung,
- Neutralization-Watch,
- unabhängige Leistungsbeobachtung und Rohsensorwerte.

Ein vorhandener RC10-V4-Header wird erkannt. Die alte Datei bleibt erhalten; RC11 schreibt in eine neue headerkorrekte Sitzungsdatei.

## 9. Konfigurations- und Hashvertrag

Folgende Settings sind Bestandteil des regelrelevanten Config-Snapshots beziehungsweise `config_control_hash`:

```text
COMMAND_EFFECT_MIN_W
COMMAND_EFFECT_MIN_TARGET_W
COMMAND_EFFECT_TIMEOUT_SECONDS
COMMAND_EFFECT_FORCE_RESEND_SECONDS
COMMAND_EFFECT_TOLERANCE_W
COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS
COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS
COMMAND_RESYNC_STALE_MIN_SECONDS
COMMAND_RESYNC_STALE_MIN_CYCLES
COMMAND_RESYNC_COOLDOWN_SECONDS
```

## 10. Intended Deltas

Bewusst verändert werden nur:

- Wirkungskontrolle aktiver Ziele,
- physische Kontrolle sicherheitsrelevanter 0-W-Zustände,
- Recovery- und Full-State-Resync-Fähigkeit,
- unabhängige Richtungsevidenz,
- Diagnose-, Event- und Measurement-Semantik.

## 11. No-Regression-Abgrenzung

Unverändert bleiben:

- normale AUTO-Zielwertbildung,
- NIGHT_DISCHARGE-Festwert im aktiven Nachtfenster,
- Fixed-Charge/Fixed-Discharge-Zielwerte,
- Deadband, Smoothing und Power-Step,
- symmetrische Cross-Charge-Zielwertkorrektur,
- Harvest-Entry, -Hold, -Exit und -Allokation,
- Safe-State-Eintrittsbedingungen,
- MQTT-Topics und Payloads.

## 12. Bewusst offene Folgeblöcke

Nicht Bestandteil von RC11:

### RC-B

`SMA_FULL_OR_IDLE` muss das absolute Ziel künftig aus einer vertrauenswürdigen aktuellen Zendure-Ladung plus verbleibendem Export minus Reserve bilden. Dieser Eingriff folgt erst nach Produktivvalidierung der neuen Power-Observation.

### RC-C

Die lokale Zendure-API bleibt in RC11 noch synchron. Ihre vollständige Entkopplung über einen Hintergrundworker und Latest-Snapshot-Cache folgt separat.

## 13. Sicherheitsinvarianten

- Kein Watch darf durch kleine Zieländerungen derselben Intention dauerhaft zurückgesetzt werden.
- Ein identischer in-memory Dedupe-Zustand darf einen erforderlichen Recovery-Batch nicht blockieren.
- Ein Resync ist kein Wirkungsnachweis.
- Unklare Richtung darf keinen falschen Erfolg bestätigen.
- Telemetrieverlust pausiert Timer, löst einen bestätigten Mismatch aber nicht auf.
- Keine neue Netzwerk-, Datei- oder DB-Operation wurde in den Regelpfad aufgenommen.
