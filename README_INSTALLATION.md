# Zendure Energy Controller V12.11.2-RC4 – Installation und Betrieb

## Update installieren

```bash
cd /home/pi
./update_zendure_controller.sh v12_11_2_rc4
```

Danach prüfen:

```bash
cd /opt/zendure-controller
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -q
sudo systemctl status zendure-controller.service --no-pager -l
```

Anschließend die Statusseite einmal mit `Strg+F5` hart neu laden, damit alte CSS-/JavaScript-Dateien sicher aus dem Browsercache verschwinden.

## Historische Regelgründe nachfüllen

Neue Messwerte speichern den Tooltip-Grund automatisch. Für den historischen Bestand zunächst nur den Dry-Run ausführen:

```bash
cd /opt/zendure-controller
python3 tools/backfill_measurement_reasons.py \
  --root /opt/zendure-controller \
  --db-path /opt/zendure-controller/logs/zec_measurements.sqlite3
```

Der echte Lauf darf nur bei gestopptem Controller erfolgen und erzeugt vorher automatisch ein SQLite-Rollback-Backup:

```bash
sudo systemctl stop zendure-controller.service

python3 tools/backfill_measurement_reasons.py \
  --root /opt/zendure-controller \
  --db-path /opt/zendure-controller/logs/zec_measurements.sqlite3 \
  --apply

sudo systemctl start zendure-controller.service
```

## Architekturhinweise

- Die Statusseite V2 liegt in `status_page_v2.py`, `static/status_v2.css` und `static/status_v2.js`.
- UI und Graph nutzen ausschließlich In-Memory-Snapshots und gecachte, indizierte Graphendpunkte.
- Die SQLite-Schemaänderung ist additiv und läuft außerhalb des Controller-Regelpfads im DB-Writer-Kontext.
- AUTO, Harvest, Cross-Charge, NIGHT_DISCHARGE, Fixed-Modi und MQTT-Command-Entscheidungen werden nicht verändert.
- Die bekannte `ResourceWarning: unclosed database` aus bestehenden Measurement-DB-Tests kann weiterhin erscheinen; entscheidend ist ein Testabschluss mit `OK`.
