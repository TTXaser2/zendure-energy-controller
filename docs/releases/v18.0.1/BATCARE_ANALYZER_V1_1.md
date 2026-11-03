# ZEC Battery Care V18 – 7-Tage-Feldevidenz, READ-ONLY

**Werkzeugversion:** 1.1 · **Quellbasis:** hashverifiziertes ZEC V18.0.0 (`db1e33d7fbe247e602f86534edfbf22affddbc146a83318632e0b7e47d6f13c7`) · **ZEC-Produktquellen geändert:** keine.

## Zweck

Das Skript extrahiert sieben zurückliegende Tage bis zum Ausführungszeitpunkt (Zeitzone `Europe/Berlin`). Optional sind konkrete `--from`-/`--until`-Zeiten einstellbar. Die Analyse trennt:

1. **Policy / Konfiguration:** Historische Care-Freigabe und R/N/E, Saison, Changes, ausdrücklich `UNKNOWN` bei fehlendem Zeitliniennachweis.
2. **Zustand und Rechenwirkung:** SOC vor/unter Reserve, Grund `BATTERY_CARE_RESERVE`, Ziel 0 W, AUTO/NIGHT/HOLD, Abschätzung von Verweilzeiten und Flüssen.
3. **Physikalische Wirkung:** Reale AC-Leistung, Richtung, Netzleistung, SOC-Trend und unabhängige Validitäts-/Freshness-Signale aus Measurement V4, sofern vorhanden. SQLite-Grapheinträge alleine genügen **nicht** für eine bestätigte physikalische Wirkung.
4. **Wirkung & Recovery:** Command-Lifecycle, Readback, Resync, Neutralisierung, Cross-Charge sowie echte Operationsjournal-Übergänge für PV-Priorität, Netzpflege und Notladung. Ein Stufenwechsel ist kein Hardware-Wirkungsbeleg.

Die Roh-/Auszüge erlauben eine vertiefte nachgelagerte Prüfung mit ZEC-Analyse-Regelwerk V1.1: Zustand, Rechnung, unabhängige Wirkung und Recovery. Keine erfundene Closed-Loop-Gegenfaktik, keine pauschale Batteriegesundheits-/SOH-Aussage.

## Installation und ein Lauf auf dem Raspberry Pi

Das **einzelne Python-Skript** in `/home/pi/Downloads/` kopieren, nicht unter `/opt/zendure-controller` installieren. Standardbefehle:

```bash
cd /home/pi/Downloads
sha256sum zec_battery_care_7d_readonly.py
nice -n 10 ionice -c3 python3 zec_battery_care_7d_readonly.py \
  --root /opt/zendure-controller --days 7 --output-dir /home/pi/Downloads
```

Falls `ionice` fehlt: `nice -n 10 python3 ...`. **Keine `sudo`-Ausführung**, außer wenn die nötigen Daten anderweitig nicht lesbar sind; dann erst Rücksprache halten. Das Skript benötigt ausschließlich Python-Standardbibliothek (Python ≥3.10) und Schreibrechte im **Ausgabeverzeichnis**. Seine Quell-DBs werden mit SQLite `mode=ro`, `query_only=ON` geöffnet; Konfiguration wird gelesen, nicht exportiert. Es gibt keine MQTT-/HTTP-Verbindung, keinen Dienststopp, keinen Restart und keine Produktmutation.

Wird V4 auf einem externen, automatisch gewählten USB-Mount geschrieben, im ersten Ergebnis `WARNINGS` prüfen. Falls `V4_NO_ROWS`/`V4_EXTERNAL_AUTO_MOUNT_UNKNOWN` erscheint, den **tatsächlichen** vorhandenen V4-Logordner ergänzen:

```bash
nice -n 10 ionice -c3 python3 zec_battery_care_7d_readonly.py \
  --root /opt/zendure-controller --days 7 \
  --v4-dir /PFAD/ZU/DEN/V4-LOGS \
  --output-dir /home/pi/Downloads
```

**Nicht ungezielt ein ganzes USB-Laufwerk scannen.** Bei abweichendem SQLite-Pfad `--db /.../zec_measurements.sqlite3` und ggf. `--events-db /.../zec_operational_events.sqlite3` angeben. Ein konkreter Zeitraum ist mit `--from 2026-10-28T00:00 --until 2026-11-02T09:00` möglich (Ende exklusiv), sofern Daten noch vorliegen.

## Ergebnis

Das Skript gibt einen präzisen ZIP-Pfad, `SHA256`, Größe, Zeitraum, Datenmengen und Warnungen aus. ZIP auf den lokalen Rechner übertragen und hier zur Analyse hochladen. Das ZIP enthält:

- `report.json`: Integrität/Abdeckung/Limitstatus, keine erfundenen PASS-Aussagen.
- `daily_summary.csv`: Zeiträume/SOC/R/N/E, unvollständige beobachtete Zeit, Modusdauern, grobe Energieflüsse.
- `historical_care_config.csv`: historisch nachgewiesene Pflegekonfigurationen (nur die relevanten, nicht geheimen Felder).
- `sqlite_graph_points.csv`: zeitaufgelöste SOC-/Leistungs-/Ziel-/Regelgrundwerte plus historische Konfigurationszuordnung.
- `reserve_graph_candidates.csv`: erkannte 0-W-Reserve-Übergänge und zeitlicher Verlauf als **noch nicht unabhängig verifizierte** Kandidaten.
- `v4_command_and_effect_points.csv`: hochaufgelöste, validitätsgestützte Messungen, Command-Wirkungs- und Recoverykontext (wenn V4 verfügbar).
- `care_and_context_events.csv`: relevante Care-Journal- und Mode-Ereignisse; freie Detailtexte und identifizierende Schlüssel nicht exportiert.
- `SHA256SUMS.txt`: SHA256 der im ZIP enthaltenen Auszugsdateien.

### Sicherheits- und methodische Grenzen

- Streaming-Verarbeitung mit festen Maxima: 360.000 SQLite-Zeilen, 360.000 V4-Ausgabezeilen, 900 V4-Dateien, 3 GiB gescannte V4-Dateien, 30.000 Journalereignisse. Ein Überschreiten wird ausdrücklich in `report.json` als `truncated`/WARN ausgewiesen. Es wird niemals ein vollständiger Datensatz behauptet, wenn er gekappt wurde.
- SQLite liefert nur ein Graph-Teilschema; dessen AC-Istleistung hat **kein** eigenständiges valid/fresh-Feld. Die kWh sind grobe, auf maximal 15-s-frische Intervalle beschränkte Rechenwerte, keine unabhängig verifizierten AC-/DC-Bilanzen. Der angezeigte Ladewert ist AC, nicht Zell-Energie; Inverterverluste unberücksichtigt.
- Das Programm wertet ausschließlich natürliche historische Ereignisse aus; es löst **keine** Tiefentladung oder Netzladung aus. Fehlende Episoden (`N`/`E`/PV-Vorrang) sind `NOT_EVALUABLE`, nicht `PASS`.
- V4-Datensätze aus mehreren Dateien können überlappen und liegen im Export nicht garantiert chronologisch. Für eine sorgfältige Detailanalyse nach `measurement_epoch_ms` sortieren und überlappende Zeitstempel/Quellpfade auflösen. Das Programm nimmt keine erfundene Korrektur vor.
- Konfigurationshistorie aus `graph_config_timeline` wird herangezogen, sofern `known=1`; heutige Werte werden **nicht rückwirkend** auf ältere Zeitabschnitte übertragen. Bei fehlender historischer Tabelle sind Care-Zeiten nicht fachlich bewertbar.
- Ausgabeordner/-ZIP sind nur für Benutzer `pi` vorgesehen; das Archiv enthält echte Mess- und Betriebsdaten und sollte vertraulich behandelt werden. Keine Geheimnisse/ganzen Configs/Betriebsjournaldetails werden übernommen.
- Das Programm speichert die exportierten Daten zusätzlich unkomprimiert im erzeugten Ausgabeordner, damit die ZIP-Prüfsummen nachvollziehbar bleiben. Der belegte Plattenplatz ist zu prüfen; bei knappem Platz **nicht ausführen**. Keine automatische Löschung durch das Tool.

## Einordnung zum Projektstand

Die natürliche R=17-%-Neutralisierung am 29.10.2026 ist bereits als **einzelner** realer Feldbeleg dokumentiert. Die 7-Tage-Analyse soll insbesondere ermitteln, ob sich Reservegrenzeneinhaltung, Ruhezeiten, unnötige Richtungsschaltungen oder reale PV-/Netzpflege-/Notlade-Fälle über weitere Tage bestätigen lassen. Eine generelle Care-Wirksamkeit wird nicht vorweggenommen. Die verifizierten ZEC-Produktquellen und der Pi werden nicht verändert.

## Korrekturstand V1.1 (V18.0.1-Entwicklungszweig)

Bei fehlenden/NULL-gefuellten SQLite-Kernspalten wird die Graph-Tagesbilanz explizit als unbrauchbar eingestuft. Die Tagesbilanz wird dann ausschließlich aus gültigen, frischen V4-Werten mit maximal 15-Sekunden-Intervall neu berechnet; liegen auch diese nicht vor, ist die Bilanz `NOT_EVALUABLE` statt Nullverbrauch vorzutäuschen. Auf Archivdaten ohne global chronologische V4-Zeitstempel ist weiterhin eine Offline-Dedup erforderlich.

Die V4-Dateiauswahl verwendet nun die UTC-Zeitstempel der Dateinamen und das letzte Vorgängerfile des Anfragefensters, nicht das mtime-basierte Abschneiden auf 900 Dateien. Bei einer tatsächlich gekappten Menge zeitlich geeigneter Dateien werden `file_selection_truncated` und `truncated` beide auf `true` gesetzt. Die Ressourcenobergrenzen bleiben unverändert.
