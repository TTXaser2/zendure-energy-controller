# Zendure Energy Controller V12.11.2-RC13

## Aktueller Release

V12.11.2-RC13 ist der eng abgegrenzte Sicherheits-Nachkorrekturrelease zu RC12. Er behebt die im produktiven Morgenzyklus vom 27.07.2026 bestätigte zyklusweise Wiederholung vollständiger 0-W-Kommandos, das umgehbare Command-State-Retry-Fenster und falsche Resyncs während physikalisch plausibler Ladeendphasen.

Wesentliche Änderungen:

- Bestätigte Neutralisierungen werden als physische Episoden behandelt und nach der ersten wirksamen 0-W-Herstellung vollständig dedupliziert.
- Wechselnde Gründe wie `MIN_SOC_LIMIT`, `MAX_SOC_LIMIT`, `SAFE_STATE` oder `CROSS_CHARGE_BLOCKED` erzeugen bei identischem Nullzustand keinen erneuten MQTT-Batch.
- Ein einheitlicher Command-State-Gate-Zustandsautomat ersetzt die wechselnden RC12-VERIFY/APPLY-Signaturen.
- Änderungen des exakten Wattziels innerhalb derselben Lade- oder Entladerichtung setzen das 30-s-Retry-Fenster nicht zurück.
- Nicht neutrale Leistungsbefehle sind auch bei Force-/Resync-Pfaden nur mit frisch bestätigtem `smartMode=1` möglich.
- Sicherheitsrelevante 0-W-Kommandos bleiben bei unsicherem Command-State möglich, aber höchstens einmal pro Retry-Fenster.
- Sollwerttracking verwendet den größeren Wert aus absoluter und relativer Toleranz; Default der neuen relativen Diagnose-Toleranz ist 10 %.
- Physikalisch bestätigtes BMS-/Ladeannahme-Taper kann bereits ab `MAX_SOC_PERCENT - 10` als `COMMAND_CHARGE_ACCEPTANCE_LIMITED` klassifiziert werden.
- Echte Nichtwirkung bei niedrigem SOC bleibt mismatch- und resyncfähig.
- Neue Measurement-V4-Felder machen tatsächliche Publish-Batches eindeutig: Event-ID, Epoch, Gate-Zustand, Retry-Restzeit und Neutralisierungs-Episoden-ID.
- RC12-Dateien bleiben unverändert; RC13 beginnt bei älterem Header automatisch eine neue `schema_rc13`-Datei.

Ausführliche Informationen:

```text
TECHNICAL_NOTES_V12_11_2_RC13.md
RELEASE_INFO_V12_11_2_RC13.md
UEBERGABE_ZEC_V12_11_2_RC13_COMMAND_SAFETY_FOLLOWUP.md
```

## Sicherheitsabgrenzung

RC13 ändert keine AUTO-/Harvest-Zielwertformel. Die Korrektur von `SMA_FULL_OR_IDLE` bleibt bewusst für den folgenden RC-B-Block reserviert.

Der Runtime-Schreibpfad bleibt auf folgende verifizierte Zendure-Eigenschaften begrenzt:

```text
smartMode = ON
acMode
inputLimit
outputLimit
```

ZEC schreibt weiterhin keine persistenten Geräte-Caps, SOC-Grenzen oder Offgrid-Konfigurationen.

## Bewusst nicht enthalten

- Korrektur der absoluten `SMA_FULL_OR_IDLE`-Zielwertformel,
- asynchrone Entkopplung der lokalen Zendure-API,
- Readiness-/Sticky-Error-Nacharbeit,
- produktiver Offgrid-Steckdosentest,
- Settings-Redesign.

## Installation

Siehe `README_INSTALLATION.md`.
