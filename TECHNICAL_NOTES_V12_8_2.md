# Technische Notizen V12.8.2

V12.8.2 ist eine Korrekturversion auf Basis von V12.8. Der Live-Regelalgorithmus bleibt unverändert.

## Analyse-Weboberfläche

- HTML-Badges in Analyse-Tabellen werden gezielt als vertrauenswürdiges, intern erzeugtes HTML gerendert. Normale Werte bleiben HTML-escaped.
- `charge_acceptance_state` wird als lesbare Zusammenfassung angezeigt, z. B. `ok: 4568, Verdacht: 96, begrenzt: 12, nimmt nicht an: 116`.
- Tabellenbegriffe erhalten anklickbare `info`-Erklärungen direkt in der Begriffszelle.
- Sichtbare Analysewerte in HTML-Tabellen und Textreport werden deutsch formatiert, z. B. `0,1417 kWh`. Technische CSV-/JSON-Daten behalten den Dezimalpunkt.
- Die Mehrdatei-Schutzgrenze wurde von 10 auf 20 CSV-Dateien erhöht. Gesamtgröße und Messpunktlimit bleiben unverändert.

## Navigation

- Der Link von der Controller-Weboberfläche zur Analyse-Weboberfläche wird beim Seitenaufbau auf den aktuellen Hostnamen und den konfigurierten Analyse-Port gesetzt.
- Standard-Port bleibt 8090 über `REPLAY_WEB_PORT`.

## Settings

- `CSV_LOG_BACKUP_COUNT` darf nun bis 20 eingestellt werden.

## Nicht geändert

- Keine Änderung am Live-Regler.
- Keine Änderung am CSV-Schema `ZEC-MEASUREMENT-V2`.
- Keine Umstellung auf Datenbankdatei.
