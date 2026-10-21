# Technical Notes – V12.11.5

## 1. Desktop-Scrollvertrag

Auf Desktop wird die Settings-Seite als höhengebundene Shell betrieben. `body`/Dokument sind kein primärer Scrollcontainer. Die rechte `.settings-main`-Fläche übernimmt den Settings-Scroll; die Sidebar kann unabhängig scrollen. Globale Navigation, Settings-Kontextkopf und Change-Set-Leiste bleiben stationär.

Ein normaler Kategoriewechsel setzt die Content-Scrollposition auf 0. Suchtreffer dürfen weiterhin gezielt zu einem Feld springen.

## 2. Nachtfenster-Compound

UI-seitig existieren genau zwei logische Eingaben:

```text
Startzeit des Nachtmodus  HH:MM
Endzeit des Nachtmodus    HH:MM
```

Persistiert werden unverändert:

```text
NIGHT_START_HOUR
NIGHT_START_MINUTE
NIGHT_END_HOUR
NIGHT_END_MINUTE
```

Wenn eine logische Zeit geändert wird, enthält der Preview-Payload beide technischen Keys des betreffenden Paars. Der Previewdiff fasst technische Zeitänderungen zu einer logischen Zeile `Nachtfenster` zusammen. Das Backend-/Configschema wird nicht migriert.

## 3. Preview-422-Vertrag

`/settings/preview` bleibt serverseitig autoritativ. Ein fachlich erwartetes Ergebnis:

```text
HTTP 422
status = blocked
issues[]
```

wird im Browser nicht als Transportfehler behandelt. Die UI zeigt vollständige Issues, markiert betroffene Felder, ermöglicht einen Sprung zum Setting, behält den Draft und sperrt Commit. 409 und 403 erhalten eigene verständliche Meldungen; unerwartete 422/5xx werden generisch behandelt, ohne rohe Exceptiontexte anzuzeigen.

## 4. Mobile Drawer

Beim Öffnen wird die Hintergrundposition gespeichert und der Body fixiert. Der Drawer selbst bleibt mit `overflow-y:auto` scrollbar und erhält `overscroll-behavior:contain`. Beim Schließen wird die vorherige Hintergrundposition wiederhergestellt. Es gibt keine globale `touchmove`-Sperre.

## 5. Administrative Last-Good-Aktion

Die bestehende Serverfunktion wird nicht geändert. Nur die Einordnung im Frontend ändert sich:

```text
Experte
→ System & Diagnose
→ Administrative Aktionen
→ Last-Good-Konfigurationsspeicher
```

Der Erklärungstext stellt klar, dass ausschließlich der interne `current`-Pointer auf einen serverseitig vollständig validierten Slot repariert wird und keine normalen Settings geladen, geändert oder auf Defaults gesetzt werden.

## 6. Empty-State

Die Navigationszahl wird aus den im aktuellen Modus und unter aktuellen Dependencies tatsächlich sichtbaren logischen Settings ermittelt. Sind im Standardmodus ausschließlich Expertenparameter vorhanden, zeigt die Kategorie einen Empty-State mit Anzahl der ausgeblendeten Expertenparameter und der Aktion `Expertenmodus anzeigen`.

## 7. Installer-Identität

Der Readiness-Klassifizierer erwartet nun ausschließlich die neue Zielidentität `12.11.5 / v12.11.5-20260807`. Seine sicherheitsrelevante READY-/TRANSITIONAL-/REJECT-Logik ist unverändert.

## 8. No-Regression

Byteidentisch zu V12.11.4 bleiben:

```text
controller_logic.py
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
measurement_v4.py
measurement_v4_contract.py
```
