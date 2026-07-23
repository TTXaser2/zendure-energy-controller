# Zendure Energy Controller V12.11.2-RC8

## 1. Zweck

RC8 ist ein UI-, Diagnose- und Installations-Stabilisierungsrelease auf Basis von RC7. Es setzt die nach der ersten produktiven RC7-Nutzung bestätigten Restpunkte um.

## 2. Quantisierungsbewusste SOC-Anzeigekurve

RC7 verwendete eine monotone kubische Interpolation. Bei langen Folgen ganzzahlig identischer SOC-Werte setzt ein monotones Verfahren die Tangente absichtlich auf null; die Treppen blieben daher sichtbar.

RC8 rekonstruiert ausschließlich für die Canvas-Darstellung den plausiblen kontinuierlichen Verlauf innerhalb konsistenter 1-%-Lade- oder Entladefolgen:

- aufeinanderfolgende 1-%-Stufen gleicher Richtung werden über ihre tatsächlichen Zeitgrenzen verteilt,
- lange Plateaus bleiben erhalten,
- Reserve-, Min-/Max-SOC- und 100-%-Plateaus werden besonders geschützt,
- Richtungswechsel, größere Sprünge und Datenlücken werden nicht geglättet,
- es entstehen keine Bézier-Über- oder Unterschwinger.

Unverändert bleiben:

- SQLite-/CSV-Rohwerte,
- Tooltipwerte,
- Schwellenlinien und Schutzentscheidungen,
- Ereignis- und Regelungslogik.

## 3. Sicheres Auflösen der veralteten MQTT-Unsicherheitswarnung

Ein bei unsicherer MQTT-Telemetrie angeforderter Nicht-Null-Sollwert konnte als Warnung sichtbar bleiben, obwohl der aktuelle Sollwert später 0 W und die Gerätewirkung neutral war.

RC8 löscht ausschließlich diesen diagnostischen Warnzustand, wenn alle Bedingungen gleichzeitig erfüllt sind:

1. aktueller Controller-Sollwert ist 0 W,
2. Zendure-Gesamtstatus ist `ZENDURE_MQTT_OK`,
3. Live-Telemetrie ist bestätigt,
4. Istleistung ist gültig und innerhalb des konfigurierten Freshness-Timeouts,
5. Betrag der Istleistung liegt innerhalb `COMMAND_EFFECT_TOLERANCE_W`.

Bei veralteter Telemetrie oder weiterhin nicht-neutraler Gerätewirkung bleibt die Warnung erhalten.

Die Korrektur:

- sendet kein Kommando,
- verändert keine Deduplizierung,
- verändert keine Resync-Berechtigung,
- hält keinen Modus oder Sollwert fest.

## 4. Timing-Verteilung

Der bisherige Balken zeigte den aktiven Anteil von `aktive Arbeit / (aktive Arbeit + Sleep)`. Bei typischen 40–60 ms gegenüber mehreren Sekunden Sleep war er fast leer und ohne Beschriftung wenig aussagekräftig.

RC8 zeigt stattdessen:

```text
Aktiver Gesamtdurchlauf                    49,1 ms
Zyklusabstand ca. 2,05 s · aktive Arbeit 2,4 %
```

Darunter stehen der hierarchische Linienbaum und ein vollständig gefüllter gestapelter Verteilungsbalken. Jede Phase besitzt:

- einen festen neutralen Kategorienfarbton,
- denselben Farbpunkt in der Zeile,
- dasselbe Segment im Balken,
- Tooltip mit Millisekunden und Prozentanteil.

Die sichtbaren synchronen Phasen summieren sich zum aktiven Gesamtdurchlauf. Asynchrones SQLite-Schreiben ist ausdrücklich nicht enthalten.

Große Anteile sind nicht automatisch Warnungen. Slow-Cycle wird ausschließlich gegen die benannte Konfigurationsgrenze `SLOW_CYCLE_WARN_MS` bewertet. Diese Grenze ist eine Diagnosewarnung, keine harte Echtzeit-Deadline.

## 5. Installations-Ready-Check

Der bisherige Ready-Check konnte bereits wenige hundert Millisekunden nach `systemctl start` laufen und leeres beziehungsweise noch nicht verfügbares HTTP-JSON an `json.tool` übergeben.

RC8:

- prüft innerhalb eines begrenzten Zeitfensters von 20 Sekunden wiederholt im Abstand von 0,5 Sekunden,
- verwendet `curl -f` und ein kurzes Request-Timeout,
- akzeptiert nur syntaktisch gültiges JSON,
- meldet Erfolg ausdrücklich,
- beendet das Update bei Timeout mit konkreten Diagnosebefehlen und ohne falsche Erfolgsmeldung.

## 6. FastAPI-Lebenszyklus

Die Betriebsereignis-Komponente wird nun über einen `asynccontextmanager`-Lifespan gestartet und gestoppt. Die veralteten `@app.on_event("startup")`-/`shutdown`-Handler entfallen.

## 7. Testpflege

Der Operations-Dashboard-Test liest `static/status_v2.js` nun über `Path.read_text()` statt über einen nicht geschlossenen Dateihandle.

Neu hinzugefügte Differentialtests prüfen unter anderem:

- sichere Warnbereinigung nur bei bestätigtem neutralem Zustand,
- Nicht-Bereinigung bei stale oder nicht-neutraler Istleistung,
- vollständige Timing-Segmentsumme,
- Farblegenden-Vertrag zwischen Baum und Balken,
- Slow-Cycle-Schwelle,
- quantisierungsbewusste SOC-Renderlogik,
- Ready-Retry-Vertrag,
- FastAPI-Lifespan.

## 8. Sicherheitsabgrenzung

Unverändert bleiben:

- AUTO-, NIGHT_DISCHARGE- und FIXED-Fachlogik,
- Harvest und Cross-Charge,
- Safe-State-Auslösung,
- MQTT-Themen und Kommandoformat,
- Leistungsgrenzen und Sollwertpipeline,
- CSV-/V4-Vertrag,
- SQLite- und Event-Schema.

Es entstehen keine neuen blockierenden Operationen im Reglerpfad. UI-Rekonstruktion läuft ausschließlich im Browser. Die Warnbereinigung verwendet nur bereits vorhandene In-Memory-Werte und führt weder Netzwerk- noch Datei-/DB-Zugriffe aus.
