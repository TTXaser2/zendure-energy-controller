# Technical Notes V12.8.13

## 1. Ziel

V12.8.13 ist ein minimaler Hotfix für die MQTT-Topic-Diagnoseseite aus V12.8.12. Die fachliche Regelstrategie bleibt unverändert.

## 2. Fehlerbild

Nach Installation von V12.8.12 lieferte der Aufruf der MQTT-Diagnoseseite:

```text
/mqtt-diagnostics
```

serverseitig `Internal Server Error`.

## 3. Ursache

Die Route `/mqtt-diagnostics` rief `html_or_headless()` mit dem bereits erzeugten HTML-String auf:

```python
html_or_headless(build_mqtt_diagnostics_page(cfg, rows, cleared=...))
```

`html_or_headless()` erwartet jedoch analog zu den anderen HTML-Routen eine Page-Builder-Funktion und ruft diese intern auf. Dadurch konnte aus dem HTML-String ein `TypeError: 'str' object is not callable` entstehen.

## 4. Korrektur

Die Route übergibt nun die Page-Builder-Funktion und deren Argumente getrennt:

```python
return html_or_headless(
    build_mqtt_diagnostics_page,
    cfg,
    state.snapshot().get("mqtt_topic_diagnostics", []),
    cleared=request.query_params.get("cleared") == "1",
)
```

Der in V12.8.12 eingeführte Button `Diagnosetabelle leeren` bleibt unverändert erhalten.

## 5. Tests

Neue Tests in `tests/test_v12_8_13_mqtt_diagnostics_route.py` prüfen echte FastAPI-Routen statt nur HTML-Builder:

- `GET /mqtt-diagnostics` liefert HTTP 200 und enthält Diagnoseinhalt.
- `POST /mqtt-diagnostics/clear` liefert Redirect auf `/mqtt-diagnostics?cleared=1` und leert den Puffer.
- Die geleerte Seite zeigt eine Bestätigung.
- Headless Mode liefert auch für `/mqtt-diagnostics` die Headless-Hinweisseite.

## 6. Abgrenzung

Nicht Bestandteil von V12.8.13:

- keine Änderung der eigentlichen Regelstrategie,
- keine Änderung am MQTT-Diagnosemodus selbst,
- kein vollständiger Standard-/Expertenmodus,
- kein Analyse-Streaming-/Aggregationsumbau,
- keine Änderung der Excel-Lernsimulation.
