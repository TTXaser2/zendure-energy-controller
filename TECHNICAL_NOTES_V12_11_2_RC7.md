# Zendure Energy Controller V12.11.2-RC7

## 1. Zweck

V12.11.2-RC7 ist ein Stabilisierungs-, Diagnose- und UI-Release auf Basis von V12.11.2-RC6. Es setzt den nach der RC6-Liveauswertung bestätigten Backlog um. Kernpunkt ist die Korrektur eines MQTT-Freshness-Fehlers, der frisch eingetroffene Zendure-Werte mit `age_s == 0` kurzzeitig als veraltet bewertet hatte.

Die eigentliche Energie-Regelstrategie bleibt unverändert. Die Änderungen betreffen Freshness-Auswertung, Kommando-Lifecycle-Diagnose, Zeitmessung, Betriebsjournal, Statusdarstellung und Wartungswerkzeuge.

## 2. Korrektur der Zendure-MQTT-Freshness

### 2.1 Ursache in RC6

Die bisherige Prüfung verwendete sinngemäß:

```python
int(age_s or 999999)
```

Der gültige Wert `age_s == 0` ist in Python falsy und wurde dadurch durch `999999` ersetzt. Gerade unmittelbar nach dem Empfang einer neuen Nachricht konnte eine kritische Telemetriegruppe deshalb für einen Controllerzyklus als stale erscheinen.

### 2.2 Wirkung des Fehlers

Die Live-Diagnose zeigte:

- viele nur ein bis drei Zyklen lange `STALE`-/`PARTIAL_STALE`-Phasen,
- anschließend jeweils eine vermeintliche Recovery,
- bei produktiv aktiviertem `COMMAND_RESYNC_ON_MQTT_RECOVERY_ALWAYS` wiederholte echte Zendure-Kommandoabgleiche nach Ablauf des Cooldowns,
- Ereignisrauschen trotz durchgehend wirksamer Sollleistung.

### 2.3 Korrektur

`None` und `0` werden nun ausdrücklich unterschieden:

- `None` bedeutet fehlendes Alter,
- `0` bedeutet frisch empfangen,
- nur ein Alter oberhalb des konfigurierten Timeouts gilt als stale.

Ein Regressionstest prüft explizit `age_s == 0` für beide kritischen Zendure-Gruppen.

## 3. Zendure-Kommandoabgleich

Erfolgreiche und unterdrückte Abgleichversuche werden getrennt geführt:

- letzter erfolgreicher Zendure-Kommandoabgleich,
- letzter unterdrückter Abgleichversuch,
- getrennte Zeitpunkte, Gründe und Zähler.

`RESYNC_SUPPRESSED_COOLDOWN` überschreibt nicht mehr den Grund des letzten erfolgreichen Abgleichs und wird niemals als „erneut gesendet“ dargestellt.

Bestätigte Abweichungen zwischen Sollwert und Gerätewirkung dürfen den Cooldown weiterhin übersteuern. Damit kann die Diagnose-Deduplizierung keinen erforderlichen Wiederholungsversand verhindern und erzeugt kein „wurde bereits gesendet“-Latch.

## 4. Hierarchische Durchlaufzeitdiagnose

Die Karte `Controller & Schnittstellen` zeigt jetzt:

1. den aktiven Gesamtdurchlauf ohne Wartezeit/Sleep als übergeordneten Wert,
2. darunter einen eingerückten Linienbaum der wesentlichen Teilphasen,
3. das asynchrone SQLite-Schreiben separat außerhalb des Hauptdurchlaufs,
4. den langsamsten direkt gemessenen Teilabschnitt.

Übergeordnete Sammelwerte wie `run_once_ms` und `finish_cycle_ms` werden nicht mehr als Blattphase oder langsamster Abschnitt bewertet. Der residuale Wert `Sonstige, nicht einzeln erfasste Verarbeitung` vervollständigt die Summe, wird aber ebenfalls nicht als direkt gemessener langsamster Abschnitt ausgegeben.

### 4.1 Teilphasen

Je nach durchlaufenem Modus werden nur vorhandene, fachlich relevante Phasen angezeigt, unter anderem:

- Konfigurationsprüfung,
- Zendure Local API,
- SMA- und Netzdaten,
- Status- und Diagnoseaufbereitung,
- Regelentscheidung ohne verschachtelte MQTT-Sendedauer,
- tatsächlicher MQTT-Kommandopfad,
- Kommandowirkungsprüfung ohne verschachtelten Wiederholungsversand,
- Logging im Hauptthread,
- sonstige, nicht einzeln erfasste Verarbeitung.

### 4.2 Statistik

Ein fest begrenzter Ringpuffer hält maximal 60 Timing-Snapshots. Im Info-Pop-over stehen für zentrale Phasen:

- Mittelwert,
- P95,
- Maximum,
- Anzahl der Werte.

Es gibt kein unbeschränktes Wachstum im RAM.

### 4.3 Balkensemantik

Der Timing-Balken zeigt den aktiven Anteil des realen Start-zu-Start-Zyklus:

```text
aktive Arbeit / (aktive Arbeit + konfigurierte Wartezeit)
```

Die konfigurierte Wartezeit wird damit nicht fälschlich als harte Ausführungsdeadline interpretiert.

## 5. Messdaten- und SQLite-Diagnose

- `Letzter DB-Schreibvorgang` verwendet nun das tatsächlich gelieferte Feld `measurement_db_last_write_epoch_s`.
- Die Zeit wird adaptiv lesbar angezeigt, beispielsweise `vor 2 s` oder mit Datum bei älteren Zeitpunkten.
- Der asynchrone SQLite-Worker misst seine reale Write-/Commit-Dauer mit einer monotonen hochauflösenden Uhr.
- Ein fehlender SQLite-Timingwert wird nicht mehr als `0,0 ms` ausgegeben.

Der SQLite-Write bleibt asynchron und ist nicht Teil des aktiven Controllerdurchlaufs.

## 6. Betriebsereignisse

Die Telemetrie-Ereigniserfassung besitzt eine rein diagnostische Stabilitätsprüfung:

- ein fehlerhafter Zustand muss sechs Sekunden stabil bestehen, bevor ein Vorfall geöffnet wird,
- eine Recovery muss sechs Sekunden stabil bestehen, bevor der Vorfall geschlossen wird,
- ein bereits beim Start des Event-Beobachters bestehender stabiler Fehler wird nach dem gleichen Fenster korrekt als offen erfasst,
- kurze Ein-Zyklus-Flanken erzeugen keinen Journal-Spam.

Diese Stabilitätsprüfung existiert ausschließlich im separaten Ereignisbeobachter. Sie verändert weder den aktuellen Controllerstatus noch Freshness, Safe-State, Resync-Berechtigung oder MQTT-Kommandos.

Die Tagesüberschriften lauten jetzt beispielsweise `Heute · 6 Ereignisgruppen`.

## 7. Systemressourcen

Die Karte zeigt zusätzlich die aktuelle Swap-Aktivität:

```text
0 B/s hinein · 0 B/s hinaus
```

Die Berechnung nutzt die Differenzen von `pswpin` und `pswpout` aus `/proc/vmstat` sowie die Systemseitengröße. Der erste Snapshot zeigt `wird ermittelt …`. Die Erfassung erfolgt ausschließlich im gecachten Web-Diagnosepfad.

`Controller-Laufzeit` bleibt wie beschlossen in `Controller & Schnittstellen`; `Systemlaufzeit` bezeichnet weiterhin den Raspberry-Pi-Bootzeitraum.

## 8. Speicher-SOC-Tagesgraph

Die SOC-Linien werden ausschließlich visuell mit einer monotonen kubischen Interpolation gezeichnet:

- sie laufen durch die vorhandenen Messpunkte,
- sie überschwingen nicht,
- Datenlücken werden nicht verbunden,
- Datenbankwerte, Tooltipwerte, Schwellen und Ereignisauswertung bleiben unverändert.

Die Darstellung reduziert die optische Treppenwirkung ganzzahlig quantisierter SOC-Werte, ohne Messwerte zu verändern oder künstliche Extremwerte zu erzeugen.

## 9. Datumswähler des SOC-Graphen

- Desktop: Die sichtbare Datumsfläche ist ein echtes Button-Element und öffnet den nativen Datepicker über `showPicker()` mit Fallback.
- Tastatur: Enter und Leertaste werden unterstützt.
- Touch/iOS: Auf Geräten mit grobem Zeiger liegt weiterhin das native Date-Input über der vollständigen sichtbaren Fläche. Damit bleibt das bereits funktionierende iOS-Verhalten erhalten.

## 10. Diagnosewerkzeug

Neu enthalten:

```text
tools/collect_resync_diagnostics.sh
```

Das Werkzeug erstellt eine zeitlich zusammenhängende, begrenzte Resync-/MQTT-Freshness-Diagnose, ohne Dienste zu stoppen oder Einstellungen zu ändern. Der Journal-Ausschnitt verwendet ein von `journalctl --since` auf dem Ziel-Pi akzeptiertes lokales Datumsformat.

## 11. Sicherheitsabgrenzung

Unverändert bleiben insbesondere:

- AUTO-Regelstrategie,
- NIGHT_DISCHARGE-Fachlogik,
- FIXED-Modi,
- Harvest- und Cross-Charge-Strategie,
- Leistungslimits und Glättungsparameter,
- Safe-State-Entscheidungen,
- MQTT-Topics und Kommandostruktur,
- CSV-/V4-Messschema.

Die Änderungen führen zu keinem neuen Latch, keiner Race Condition und keiner Prioritätsumkehr:

- MQTT- und Reglerpfad bleiben synchron wie bisher; nur hochauflösende In-Memory-Zeitstempel wurden ergänzt.
- Es gibt keine neuen Sleeps, Netzwerk-, Datei- oder DB-Zugriffe im Controllerzyklus.
- Das Ereignisjournal bleibt ein separater Best-Effort-Thread.
- Ein bestätigter Command-Mismatch bleibt unabhängig vom Cooldown wiederholbar.
- Ein Fehler in UI, Statistik, Eventjournal oder SQLite-Diagnose kann die Regelung nicht blockieren.

## 12. Migration

Keine Konfigurations- oder Datenbankmigration ist erforderlich. Die bestehende produktive `config.json`, Messdatenbank und Ereignisdatenbank bleiben erhalten.
