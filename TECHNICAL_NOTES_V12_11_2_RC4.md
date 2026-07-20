# V12.11.2-RC4 – Statusseiten-Feinschliff und historische Regelgründe

## Ziel

RC4 korrigiert die nach zweitägiger produktiver Nutzung von RC3 identifizierten UI-Kleinigkeiten, ohne die bewährte Statusseitenarchitektur oder die Live-Regelung zu verändern.

## Geänderte Dateien

- `version.py`
- `status_page_v2.py`
- `static/status_v2.css`
- `static/status_v2.js`
- `web_ui.py`
- `measurement_db.py`
- `README.md`
- `README_INSTALLATION.md`
- mehrere bestehende Versionstests

## Neue Dateien

- `tools/backfill_measurement_reasons.py`
- `tests/test_v12_11_2_rc4_ui_polish.py`
- `TECHNICAL_NOTES_V12_11_2_RC4.md`

## Funktionale Änderungen

1. Expertenmenü
   - native `details`-/`summary`-Semantik;
   - Maus, Tastatur und Touch;
   - Schließen per Außenklick oder Escape.

2. Tagesdatum
   - sichtbares Datum ist ein nativer `input[type=date]`-Trigger;
   - maximale Auswahl ist heute;
   - minimale Auswahl wird aus dem ersten vorhandenen SQLite-Minutenwert abgeleitet;
   - bestehende Tagesbuttons bleiben unverändert.

3. Graphlegende
   - dynamische Werte aus der aktuellen Konfiguration;
   - Max-SOC, Nachtreserve, Min-SOC, Nachtfenster und Jetzt-Zeitpunkt werden erklärt.

4. Regelgrund
   - Extraktion bevorzugt `control_reason`, anschließend `target_final_reason`, `safe_state_reason`, Harvest- und Command-Reasons;
   - additive Spalten `control_reason` und `control_reason_last`;
   - Tagesgraph liefert den historischen Grund aus `measurement_1min`;
   - Frontend übersetzt bekannte Enum-Reasons in verständliche deutsche Texte;
   - fehlt ein Grund in echtem Altbestand, wird keine leere `Grund —`-Zeile eingeblendet.

## Latch-/Race-/Prioritätsprüfung

- Keine Änderung an Zustandsautomat, Sollwertpipeline oder Mode-Transitions.
- Keine Änderung an Command-Deduplizierung oder Resync-Bedingungen.
- Keine synchronen MQTT-, Zendure-, Netzwerk-, DB- oder Dateisystemaufrufe im Reglerzyklus.
- SQLite-Schreiben bleibt non-blocking über den vorhandenen Writer-Queue-Pfad.
- Kalender-/Graphabfragen laufen ausschließlich im Webpfad und lesen pro Tag maximal den begrenzten 1-Minuten-Datensatz.
- Das Backfill-Werkzeug ist ein expliziter Offline-Wartungsschritt und verweigert `--apply` standardmäßig bei aktivem Controller.

Damit entstehen keine neuen Latches, Race Conditions oder Prioritätsumkehrungen.

## Tests

- additive SQLite-Migration und Reason-Persistenz;
- Reason-Abfrage im 1-Minuten-Graphstore;
- idempotenter Backfill einschließlich NUL-Zeichen in CSV;
- Expertenmenü, Kalenderwähler, Legende und UI-Markup;
- vollständige Regressionstest-Suite.
