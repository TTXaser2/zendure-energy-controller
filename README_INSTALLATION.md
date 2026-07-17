# Zendure Energy Controller V12.11.2-RC2 - Installation und Betrieb

## Update installieren

Auf dem Raspberry Pi:

```bash
cd /home/pi
./update_zendure_controller.sh v12_11_2_rc1
```

Danach prüfen:

```bash
cd /opt/zendure-controller
python3 -m py_compile *.py tools/*.py
python3 -m unittest discover -s tests -q
sudo systemctl status zendure-controller.service --no-pager -l
curl -s http://127.0.0.1:8080/ready | python3 -m json.tool
```

## Hinweise

- Die Regelstrategie gegenüber V12.11.1-RC3 bleibt unverändert.
- Die neue Statusseite nutzt Snapshot-/Cache-Daten und soll keine blockierenden Zusatzabfragen in den Regelpfad einführen.
- `/status-view-data` liefert die Live-Karten-Snapshots.
- `/storage-soc-day-data?date=YYYY-MM-DD` liefert den Speicher-SOC-Tagesgraphen.
- Die bekannte `ResourceWarning: unclosed database` aus bestehenden Measurement-DB-Tests kann beim Unit-Testlauf weiterhin erscheinen; der Testlauf ist maßgeblich, sofern er mit `OK` endet.
