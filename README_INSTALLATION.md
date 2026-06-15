# Zendure Energy Controller V12.9.0 - Installation und Betrieb

Diese Version ist für den Betrieb unter `/opt/zendure-controller` vorbereitet.

## Empfohlener Installationspfad

```bash
sudo mkdir -p /opt/zendure-controller
sudo chown -R pi:pi /opt/zendure-controller
sudo chmod 750 /opt/zendure-controller
ln -sfn /opt/zendure-controller /home/pi/zendure-controller
```

Danach kann bequem mit `cd ~/zendure-controller` gearbeitet werden, obwohl die Anwendung sauber unter `/opt` liegt.

## Update auf V12.9.0 installieren

Ab V12.7 liegt das Update-Script ausschließlich unter `tools/`.

```bash
cp /opt/zendure-controller/tools/update_zendure_controller.sh /home/pi/update_zendure_controller.sh
chmod +x /home/pi/update_zendure_controller.sh
/home/pi/update_zendure_controller.sh v12_9_0
```

Das Update-Script erhält die vorhandene `config.json`, sichert das Installationsverzeichnis, bereinigt alte Dopplungen (`Tools/`, `zendureController.py`) und installiert die systemd-Dateien für Live-Controller und optionalen Replay-Dienst.

Das Paket enthält zusätzlich die finale Excel-Lernsimulation `tools/zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx`. Diese Datei wird nur mitkopiert und nicht durch das Update-Script verändert.

Hinweis: V12.9.0 führt `ZEC-MEASUREMENT-V3` als bewusstes neues Messdatenmodell ein. Alte bekannte V2-Messdaten-Dateien im konfigurierten Log-Verzeichnis werden vom Update-Script gezielt gelöscht; es gibt keine Migration und keinen V2-Legacy-Parser.

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

V12.9.0 liefert einen separaten Analyse-Webdienst. Er wird nicht automatisch aktiviert und beeinflusst den Live-Regler nicht. Der Dienst enthält zusätzliche systemd-Ressourcengrenzen, damit eine zu große Analyse nicht den gesamten Raspberry Pi blockieren soll.

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

Die Analyse unterstützt Mehrfachauswahl von CSV-Dateien und startet nicht automatisch beim Seitenaufruf. Der Analyse-Webdienst nutzt den Controller-Freshness-/Validitätsvertrag, zeigt aktuelle Diagnoseinformationen, berechnet Mehrdatei-Zeiträume korrekt, stellt MQTT-Wirkungsbalken proportional dar und erklärt Datenqualitätswarnungen konkreter. Das Diagramm-Balkenlayout ist mobil robust; bekannte Betriebszustände und MQTT-Wirkungskategorien sind mit Info-Texten abgedeckt. Standardmäßig sind lokale Pi-Safe-Analysen auf 4 Dateien, 12 MiB und 40.000 Messpunkte begrenzt. Nach aktiver Warn-/Bestätigungslogik sind 5 Dateien, 18 MiB und 70.000 Messpunkte möglich. Alles darüber wird lokal abgelehnt; größere Analysen sollten auf einem PC/offline oder später per DB-/Aggregationslösung erfolgen.

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


Nach einem Dienstneustart aus der Weboberfläche leitet die Neustartseite auf die Hauptseite des konfigurierten Web-Ports weiter. Die MQTT-Diagnoseseite enthält einen Button zum Leeren der Diagnosetabelle und aktualisiert die sichtbaren Werte anschließend automatisch per Polling.

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

## Logging und Messdaten V3

Runtime-Log und V3-Messdaten sind unabhängig voneinander konfigurierbar. Standarddateien für neue Installationen:

```text
logs/runtime_events.log
logs/zendure_measurements.csv
```

Messdaten ab V12.9.0 verwenden ausschließlich:

```text
Schema:        ZEC-MEASUREMENT-V3
Trennzeichen:  Semikolon
Dezimalzeichen: Punkt
```

Das Messdaten-Logging wird über `MEASUREMENT_LOG_MODE` gesteuert:

```text
off       = keine zyklischen Messdaten, maximale SD-Schonung
standard  = vollständige Reglerdiagnose inklusive Freshness, MQTT-Stale-Aggregat, Sollwertkaskade, Kommando und Szenario ohne Zendure
extended  = Standard plus Detaildaten für Simulation, What-if und tiefe MQTT-/Freshness-Analyse
```

Die Settings-/Statusseite zeigt den aktiven Modus, den Logging-Status, freien Speicher und eine grobe geschätzte Aufbewahrungsdauer. Wenn Schreiben fehlschlägt oder zu wenig freier Speicher vorhanden ist, wird das Messdaten-Logging pausiert bzw. deaktiviert; die Regelung läuft weiter.

## Nachtmodus Reserve-SOC

Optional kann in den Settings im Bereich `Nachtmodus` ein `Nachtmodus Reserve-SOC` gesetzt werden. Leer bedeutet: Die feste Nachtentladung läuft bis zum globalen Mindest-SOC oder bis zum Ende des Nachtfensters. Wenn gesetzt, arbeitet dieser Wert ohne Latch und ohne Hysterese als laufende Untergrenze: Wenn `SOC <= NIGHT_DISCHARGE_STOP_SOC_PERCENT`, wird nur die feste Nacht-Basisentladung pausiert. Der Controller fällt danach in den normalen AUTO-Zweig zurück, liest die Netzleistung weiter und darf bei realem Netzbezug bis zum globalen `MIN_SOC_PERCENT` geregelt entladen. Wenn der SOC später wieder `> NIGHT_DISCHARGE_STOP_SOC_PERCENT` ist und Nachtfenster, SOC-Freshness und MQTT-Kommandopfad gültig sind, darf auch die feste Nachtentladung im selben Nachtfenster wieder laufen. Der Wert muss mindestens dem globalen `MIN_SOC_PERCENT` entsprechen.

Die Start- und Endzeit des Nachtmodus werden in der Weboberfläche als `hh:mm`-Felder angezeigt. Eingaben wie `5:30` werden beim Verlassen des Feldes zu `05:30` normalisiert. Intern werden weiterhin die bestehenden Felder `NIGHT_START_HOUR`, `NIGHT_START_MINUTE`, `NIGHT_END_HOUR` und `NIGHT_END_MINUTE` gespeichert, damit vorhandene Konfigurationen kompatibel bleiben.
