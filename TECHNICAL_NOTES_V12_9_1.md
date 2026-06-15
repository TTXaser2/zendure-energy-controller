# Technical Notes V12.9.1

## Zweck

V12.9.1 stabilisiert den mit V12.9.0 eingeführten `ZEC-MEASUREMENT-V3`-Stand. Die Live-Regelstrategie, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert. Der Fokus liegt auf Betriebsrobustheit nach Raspberry-/Mosquitto-Neustarts, Analyse-Schutz auf dem Raspberry Pi und verständlicherer Analyse-Semantik.

## Zendure MQTT Live-/Retained-/Partial-Stale-Erkennung

Der Controller bewertet nun aggregiert, ob kritische Zendure-MQTT-Gruppen nach Connect/Reconnect wieder frische nicht-retained Live-Daten liefern.

Statuswerte:

```text
ZENDURE_MQTT_OK
ZENDURE_MQTT_STALE
ZENDURE_MQTT_RETAINED_ONLY
ZENDURE_MQTT_PARTIAL_STALE
ZENDURE_MQTT_AFTER_BROKER_RESTART_NO_LIVE_UPDATES
```

Die Statusseite zeigt Live-Status, Grund, fehlende/stale Gruppen und einen Handlungshinweis. Warnungen sind selbstheilend: Sobald kritische Gruppen wieder frisch und live sind, verschwindet die Warnung automatisch.

## Analyse-/Replay-Schutz

Analyse/Replay akzeptiert ausschließlich gültige `ZEC-MEASUREMENT-V3`-Dateien. Alle anderen Dateien werden generisch abgelehnt.

Zusätzlich:

- konservativere Pi-Safe- und Extended-Grenzen,
- fail-closed Verhalten bei unsicherer Schätzung,
- Berücksichtigung von verfügbarem RAM,
- Analyse in isoliertem Worker-Prozess,
- Worker-Timeout und Speicherlimit,
- Abbruch des Workers bei Timeout, Speicherüberschreitung oder Benutzerabbruch.

Der Replay-Webdienst bleibt der kontrollierende Prozess; der Live-Controller wird nicht in die Analyse eingebunden.

## Analyse-UI-Semantik

Die Diagramme wurden nicht nur optisch, sondern semantisch nachgezogen:

- Prozentbalken verwenden bei Prozentwerten eine echte 0–100-Skala.
- Betriebszustände werden nicht mehr relativ zum größten Wert skaliert.
- Deadband-Diagramm zeigt eine additive Zeitaufteilung; das erweiterte Zielband wird als verschachtelte Zusatzkennzahl erläutert.
- Abweichungsursachen zeigen die Restkategorie `im Zielband / toleriert`, damit die Prozentbasis vollständig sichtbar ist.
- `Import`/`Export` in der Betriebszustandsmatrix wurden in `Netzbezug kWh` und `Einspeisung kWh` umbenannt.
- Info-Texte erklären Bedeutung, Einheit, Prozentbasis und Interpretation.

## Logging-Schutz

Es gibt kein V2-spezifisches Cleanup mehr. Der Logger prüft nur beim Öffnen/Initialisieren der aktiven Messdatei, ob ein gültiger V3-Header vorhanden ist. Ist der Header ungültig, wird nicht angehängt; das Logging pausiert mit Statuswarnung. Es wird nichts gelöscht oder migriert. Die Regelung läuft weiter.

## Update-Script

Das Update-Script bereinigt obsolete Tests im Zielverzeichnis per scoped `rsync --delete` nur für das Testverzeichnis. Dadurch bleiben stale Tests aus früheren Versionen nicht mehr im Ziel liegen und verfälschen den Installations-Testlauf nicht.

Bei Fehlern versucht das Script, zuvor aktive Dienste wieder zu starten und gibt Recovery-Hinweise aus. War der Replay-Dienst vor dem Update aktiv, wird er nach erfolgreichem Update wieder gestartet.

## Tests

Neue Tests prüfen unter anderem:

- automatische Entwarnung der Zendure-MQTT-Live-Diagnose,
- generische V3-only-Ablehnung im Replay-Preflight,
- Worker-/Subprozess-Schutz,
- Logger-Pause bei ungültigem aktivem Header,
- 0–100-Prozentbalken und sichtbare Restkategorien,
- Netzbezug-/Einspeisung-Beschriftung,
- Position der Messdaten-Erklärungsbox,
- stale-Test-Bereinigung im Update-Script.
