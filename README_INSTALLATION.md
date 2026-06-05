# Zendure Energy Controller V12.8.4 - Installation und Betrieb

Diese Version ist für den Betrieb unter `/opt/zendure-controller` vorbereitet.

## Empfohlener Installationspfad

```bash
sudo mkdir -p /opt/zendure-controller
sudo chown -R pi:pi /opt/zendure-controller
sudo chmod 750 /opt/zendure-controller
ln -sfn /opt/zendure-controller /home/pi/zendure-controller
```

Danach kann bequem mit `cd ~/zendure-controller` gearbeitet werden, obwohl die Anwendung sauber unter `/opt` liegt.

## Update auf V12.8.4 installieren

Ab V12.7 liegt das Update-Script ausschließlich unter `tools/`.

```bash
cp /opt/zendure-controller/tools/update_zendure_controller.sh /home/pi/update_zendure_controller.sh
chmod +x /home/pi/update_zendure_controller.sh
/home/pi/update_zendure_controller.sh v12_8_4
```

Das Update-Script erhält die vorhandene `config.json`, sichert das Installationsverzeichnis, bereinigt alte Dopplungen (`Tools/`, `zendureController.py`) und installiert die systemd-Dateien für Live-Controller und optionalen Replay-Dienst.

Hinweis: Der CSV-Schemawechsel erfolgte bereits mit V12.7. Beim Update auf V12.8.4 werden CSV-Dateien daher nicht erneut automatisch verschoben.

## Syntaxcheck

```bash
cd /opt/zendure-controller
python3 -m py_compile *.py
python3 -m py_compile tools/*.py
```

## Tests

```bash
cd /opt/zendure-controller
python3 -m unittest discover -s tests
```

## systemd-Service einrichten

```bash
sudo cp /opt/zendure-controller/systemd/zendure-controller.service /etc/systemd/system/zendure-controller.service
sudo systemctl daemon-reload
sudo systemctl enable zendure-controller.service
sudo systemctl start zendure-controller.service
```

Status prüfen:

```bash
systemctl status zendure-controller.service --no-pager -l
journalctl -u zendure-controller.service -f
```

## Optionaler Analyse-/Replay-Dienst

V12.8 liefert einen separaten Analyse-Webdienst. Er wird nicht automatisch aktiviert und beeinflusst den Live-Regler nicht.

Einmalig installieren, falls das Update-Script nicht verwendet wurde:

```bash
sudo cp /opt/zendure-controller/systemd/zendure-replay.service /etc/systemd/system/zendure-replay.service
sudo systemctl daemon-reload
```

Start bei Bedarf:

```bash
sudo systemctl start zendure-replay.service
```

Optional dauerhaft aktivieren:

```bash
sudo systemctl enable zendure-replay.service
```

Aufruf standardmäßig:

```text
http://<RASPBERRY-IP>:8090
```

Die Analyse unterstützt Mehrfachauswahl von CSV-Dateien, begrenzt den Analyselauf aber zum Schutz des Raspberry Pi auf maximal 20 Dateien, 50 MB Gesamtgröße und 500.000 Messpunkte.

## Optionaler Neustart aus der Weboberfläche

Die Weboberfläche kann optional den systemd-Dienst nach dem Speichern neustartrelevanter Settings neu starten. Diese Funktion ist standardmäßig deaktiviert.

Einmalige Einrichtung:

```bash
sudo cp /opt/zendure-controller/systemd/zendure-controller-restart /usr/local/sbin/zendure-controller-restart
sudo chown root:root /usr/local/sbin/zendure-controller-restart
sudo chmod 755 /usr/local/sbin/zendure-controller-restart

sudo cp /opt/zendure-controller/systemd/zendure-controller-sudoers /etc/sudoers.d/zendure-controller
sudo chown root:root /etc/sudoers.d/zendure-controller
sudo chmod 440 /etc/sudoers.d/zendure-controller
sudo visudo -cf /etc/sudoers.d/zendure-controller
```

Danach in den Settings im Bereich `Weboberfläche` aktivieren:

```json
"WEB_SERVICE_RESTART_ENABLED": true,
"SERVICE_RESTART_COMMAND": "sudo /usr/local/sbin/zendure-controller-restart"
```

## Health- und Ready-Endpunkte

```text
http://<RASPBERRY-IP>:8080/health
http://<RASPBERRY-IP>:8080/ready
```

`/health` liefert eine minimale Liveness-Antwort. `/ready` zeigt, ob alle wichtigen Datenquellen aktuell genug sind und der Controller nicht im Safe-State steht.

## Logging und CSV V2

Runtime-Log und CSV-Messdaten sind unabhängig voneinander konfigurierbar. Standarddateien für neue Installationen:

```text
logs/runtime_events.log
logs/zendure_measurements.csv
```

CSV-Messdaten ab V12.7 verwenden ausschließlich:

```text
Schema:        ZEC-MEASUREMENT-V2
Trennzeichen:  Semikolon
Dezimalzeichen: Punkt
```
