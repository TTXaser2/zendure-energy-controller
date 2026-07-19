# Zendure Energy Controller V12.11.2-RC3 – Installation und Betrieb

## Update installieren

```bash
cd /home/pi
./update_zendure_controller.sh v12_11_2_rc3
```

Danach prüfen:

```bash
cd /opt/zendure-controller
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -q
sudo systemctl status zendure-controller.service --no-pager -l
curl -s http://127.0.0.1:8080/ready | python3 -m json.tool
```

Anschließend die Statusseite einmal mit `Strg+F5` hart neu laden, damit alte CSS-/JavaScript-Dateien sicher aus dem Browsercache verschwinden.

## Architekturhinweise

- Die Statusseite V2 ist eine eigenständige Neuimplementierung in `status_page_v2.py`, `static/status_v2.css` und `static/status_v2.js`.
- Sie nutzt ausschließlich In-Memory-Snapshots und gecachte Graphendpunkte.
- AUTO, Harvest, Cross-Charge, NIGHT_DISCHARGE, Fixed-Modi und MQTT-Command-Entscheidungen werden durch die UI nicht verändert.
- Die bekannte `ResourceWarning: unclosed database` aus bestehenden Measurement-DB-Tests kann weiterhin erscheinen; entscheidend ist ein Testabschluss mit `OK`.
