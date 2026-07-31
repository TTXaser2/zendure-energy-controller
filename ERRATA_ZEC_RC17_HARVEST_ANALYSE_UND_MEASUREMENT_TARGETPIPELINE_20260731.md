# Errata und Korrektur – RC17-Harvest-Auswertung und Measurement-Zielpipeline

**Stand:** 31.07.2026  
**Controller:** Zendure Energy Controller V12.11.2-RC17  
**Datenbasis:** natürlicher Ladezyklus 31.07.2026, RC17-Measurement-V4-Standarddaten  
**Korrigierter Auswerter:** `zec_rc17_branch_analyzer_v1_3.py`

## 1. Anlass

Der Branch-Auswerter V1.2 bewertete `SMA_NEAR_LIMIT` als `CONVERGENCE_FAIL`, obwohl die RC17-Formel, das gesendete Ziel, der Readback und die reale Zendure-Ladeleistung konsistent waren.

Die anschließende Rohdaten- und Codeanalyse wies zwei voneinander getrennte Diagnosefehler nach:

1. Der Auswerter verwendete `operating_mode_duration_s` als Stationaritätskriterium. Dieses Feld beschreibt jedoch die Dauer des übergeordneten Modus, beispielsweise `AUTO`, nicht die Dauer der aktuellen Harvest-Episode.
2. RC17 meldet die wirksame Ladeleistungsbegrenzung nicht zuverlässig über `target_changed_by_power_limit`. Das Flag blieb in numerisch eindeutig gekappten Zeilen `0`.

Dadurch wurden frühe Branch-Übergänge und physikalisch unvermeidbarer Restexport fälschlich gegen das freie 0-W-Ziel geprüft.

## 2. Nachgewiesener Measurement-V4-Vertragsfehler

Im RC17-Code wird das Harvest-Rohziel vor Smoothing und Ramp auf `MAX_CHARGE_POWER_W` begrenzt. Diese Stufe wird in den Measurement-Feldern jedoch nicht korrekt abgebildet:

```text
target_raw_w                 = Harvest-Rohziel vor Leistungsbegrenzung
target_limited_w             = derzeit erneut last_target_before_smoothing
target_changed_by_power_limit= aus active_limiters abgeleitet
```

Die normale Begrenzung durch `MAX_CHARGE_POWER_W` fügt keinen passenden Eintrag zu `active_limiters` hinzu. Daher kann folgende reale Kombination entstehen:

```text
target_raw_w                  2.903 W
effektives Ladelimit          2.400 W
target_final_w                2.397 W
target_changed_by_power_limit 0
```

Die Regelung selbst begrenzt korrekt. Fehlerhaft ist die Diagnose der Zielwertpipeline.

## 3. Korrektur im Branch-Auswerter V1.3

V1.3 verändert keine Controllerdaten und keine Regelung. Der Auswerter:

1. verwendet mindestens 60 Sekunden kontinuierliche Dauer der konkreten Harvest-Episode statt `operating_mode_duration_s`;
2. rekonstruiert das effektive Ladelimit aus:
   - `MAX_CHARGE_POWER_W` des passenden Config-Snapshots;
   - `zendure_device_charge_max_limit_w`;
3. erkennt eine harte Begrenzung numerisch aus Rohziel, wirksamem Cap und finalem Ziel;
4. bereinigt bei Cap-Zeilen ausschließlich den physikalisch unvermeidbaren Exportanteil:

```text
erwarteter unvermeidbarer Export = max(0, target_raw_w - target_final_w)
cap-bereinigtes Netzresiduum      = control_grid_power_w + erwarteter Export
```

5. trennt:
   - freie stationäre Konvergenz;
   - cap-begrenzte Konvergenz;
   - Ladeannahmebegrenzung;
   - noch nicht stationäres physisches Tracking;
   - dynamische Zielwertpipeline;
6. meldet den Widerspruch zwischen numerisch erkanntem Cap und V4-Flag ausdrücklich.

## 4. Validierung von V1.3

Validiert gegen die 12 RC17-Standarddateien des natürlichen Ladezyklus:

```text
RC17-Schema                         PASS
SMA_NEAR_LIMIT                      PASS_CAP_ADJUSTED
cap-bereinigte stationäre Zeilen    583
freie stationäre Zeilen             0
Acceptance-limitierte Kontexte      273
Tracking noch nicht stationär       69
```

Neun längere cap-begrenzte Episoden bestanden jeweils einzeln. Repräsentative cap-bereinigte Ergebnisse:

```text
Median |Residuum|   etwa 25–44 W
p95 |Residuum|      etwa 26–45 W
Grenzen             Median <= 100 W, p95 <= 200 W
```

Der kombinierte High-SOC-/Near-Limit-Zweig wurde korrekt als `OBSERVED_ACCEPTANCE_LIMITED` klassifiziert.

Die vollständige lokale Validierung ergab außerdem:

```text
Power-Cap numerisch erkannt          1.046 Zeilen
Power-Cap im V4-Flag gemeldet        0 Zeilen
Cap-Flag-Mismatch                    1.046 Zeilen
```

Diese Zahl bezieht sich auf die lokal extrahierte relevante RC17-Datenmenge. Ein Lauf auf dem produktiven Gesamtbestand kann geringfügig mehr aktuelle Zeilen enthalten.

## 5. Verbindliche Korrektur für einen künftigen Controllerrelease

Die folgende Änderung ist Diagnose-/Datenvertragsscope und darf die Regelalgorithmen nicht verändern:

### 5.1 Zielwertstufen

Die Runtime muss die tatsächlichen Stufen getrennt führen und serialisieren:

```text
target_raw_w
target_power_limited_w
target_filtered_w
target_step_limited_w
target_cross_charge_limited_w
target_final_w
```

Um das bestehende Standardfeldbudget nicht unnötig zu erhöhen, soll zunächst geprüft werden, ob `target_limited_w` eindeutig als `target_power_limited_w` verwendet werden kann. Ein neues Feld ist nur erforderlich, wenn bestehende Verbraucher eine andere belegte Semantik benötigen.

### 5.2 Flags

Flags müssen aus numerischen Stufendifferenzen abgeleitet werden, nicht aus frei formulierten Reasons oder unvollständigen Limiterlisten:

```text
target_changed_by_power_limit = abs(target_power_limited_w - target_raw_w) > Toleranz
target_changed_by_smoothing   = abs(target_filtered_w - target_power_limited_w) > Toleranz
target_changed_by_step_limit  = abs(target_step_limited_w - target_filtered_w) > Toleranz
```

### 5.3 Limitergrund

Die Diagnose muss mindestens unterscheiden:

```text
CONFIG_MAX_CHARGE_POWER
DEVICE_CHARGE_MAX_LIMIT
CONFIG_MAX_DISCHARGE_POWER
DEVICE_INVERSE_MAX_POWER
```

Die Gerätewerte bleiben read-only.

### 5.4 Tests

Verbindliche Regressionstests:

1. Rohziel 2.903 W, Configcap 2.400 W, final 2.397 W:
   - `target_limited_w` bildet die Cap-Stufe ab;
   - `target_changed_by_power_limit=1`;
   - passender Limitergrund.
2. Rohziel unter Cap:
   - Flag bleibt `0`.
3. Nur Smoothing/Ramp aktiv:
   - Power-Limit-Flag bleibt `0`;
   - jeweiliges numerisches Stage-Flag wird `1`.
4. Ladeannahmebegrenzung nach der Zielwertpipeline bleibt getrennt von der Sollwert-Cap-Diagnose.
5. Standard-/Extended-Feldzahl und Headeränderungen werden explizit geprüft.
6. Keine Änderung an Publish, Readback, acMode, Direction, Recovery oder Flash-Schutz.

## 6. Releasezuordnung

Die Measurement-Korrektur wird als verbindliches Addendum für den nächsten ausdrücklich freigegebenen Controllerrelease geführt. Sie ist nicht im produktiven RC17-Code umgesetzt.

Bevorzugte Zuordnung:

```text
RC18 asynchrone lokale API
+ eng begrenzte Measurement-Zielpipeline-Korrektur
```

Voraussetzung ist, dass die Änderung rein diagnostisch bleibt und das bereits festgelegte RC18-Feldbudget nicht unnötig erweitert.

## 7. Korrigierter RC17-Status

```text
natürlicher Ladezyklus                erfolgreich
SMA_NEAR_LIMIT Formel                 PASS
SMA_NEAR_LIMIT physische Wirkung      PASS_CAP_ADJUSTED
HIGH_SMA_SOC_SMA_NEAR_LIMIT Formel    PASS
High-SOC physische Konvergenz         nicht bewertbar wegen Ladeannahmebegrenzung
NIGHT_DISCHARGE                       PASS
Rollbackbedarf                        nein
```

Nicht beobachtet und deshalb weiterhin offen:

```text
HIGH_SMA_SOC ohne Near-Limit
SMA_FULL_OR_IDLE
längerer freier, ungecappter stationärer 0-W-Fall
```

## 8. Feste Entlademodi – Status

Der RC14-Produktivfehler bestand aus:

1. Vermischung lokaler Publish-Historie und Geräte-Readback mit Same-State-Publish-Sturm;
2. fehlender sicherer Barriere gegen verspätete Altkommandowirkung nach Intentwechsel.

RC15 implementierte und RC16/RC17 übernahmen unverändert:

```text
getrennte last_published_values und last_device_readback_values
kein normales Wiederholungspublish bei konstantem Desired-State
120-s-Recovery ausschließlich über definierten Full-State-Resync
Late-Effect-Guard bei ungeklärtem Mismatch und Gegenrichtungswechsel
0/0-Readback plus zwei frische unabhängige Neutralbeobachtungen
monotonic elapsed time
keine zyklusbasierte Guardfreigabe
```

Der reale RC14-Fehlerdatensatz ist Bestandteil der Regressionstests. Die 17 spezifischen RC15-Command-/Readback-/Guard-Tests bestehen unter RC17.

Im aktuellen RC17-Produktivzeitraum wurden jedoch keine Modi `FIXED_CHARGE` oder `FIXED_DISCHARGE` beobachtet. Deshalb lautet der Status:

```text
Codefix                         implementiert
Regressionstests               PASS
RC17-Vererbung                 bestätigt
natürlicher Produktivnachweis   noch offen
Fehler vollständig geschlossen technisch sehr wahrscheinlich, produktiv noch nicht formal bestätigt
```

Ein kontrollierter Produktivtest darf erst nach separater Entscheidung durchgeführt werden und muss Publishanzahl, Readback, reale Leistung, Neutralisierung und einen absichtlich sicheren Moduswechsel prüfen.
