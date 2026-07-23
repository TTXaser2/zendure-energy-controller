# Release-Information V12.11.2-RC8

## 1. Paket

```text
Datei: zendure_controller_v12_11_2_rc8.zip
Root:  zendure_controller_v12_11_2_rc8/
```

SHA256 und Dateigröße werden nach dem finalen Paketbau in der Release-Übergabe angegeben.

## 2. Installation

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc8
```

Nach erfolgreichem Abschluss muss erscheinen:

```text
Update abgeschlossen und Ready-Check erfolgreich.
```

## 3. Prüfung nach der Installation

```bash
systemctl status zendure-controller.service --no-pager -l
curl -fsS http://127.0.0.1:8080/ready | python3 -m json.tool
```

Plausibilitätskontrolle:

1. Version `V12.11.2-RC8` sichtbar.
2. SOC-Kurven in konsistenten Lade-/Entladephasen ohne dominante 1-%-Treppen.
3. Echte Reserve-/Voll-Plateaus weiterhin sichtbar.
4. Timingbaum mit Farbpunkten und darunter identisch zugeordnetem Segmentbalken.
5. Klartext zu Zyklusabstand und aktivem Arbeitsanteil.
6. Keine veraltete gelbe MQTT-Unsicherheitswarnung bei bestätigtem neutralem Soll-/Istzustand.
7. Ready-Check meldet gültiges JSON statt `Expecting value`.

## 4. Rollback

Das Update-Skript zeigt den automatisch erzeugten Backup-Pfad an, typischerweise:

```text
/home/pi/zendure-controller-backup-YYYYMMDD_HHMMSS.tar.gz
```

## 5. GitHub-Übernahme

Lokales Repository:

```text
C:\github\zendure-energy-controller
```

Empfohlen:

1. ZIP auf Windows entpacken.
2. Inhalt von `zendure_controller_v12_11_2_rc8` in das lokale Repository spiegeln.
3. `.git`, `config.json`, Logs, SQLite-Dateien, `__pycache__` und `*.pyc` ausschließen.
4. Änderungen in GitHub Desktop prüfen und pushen.

Beispiel:

```powershell
robocopy "C:\Temp\zendure_controller_v12_11_2_rc8" "C:\github\zendure-energy-controller" /MIR /XD .git logs __pycache__ /XF config.json config.json.last-good *.sqlite *.sqlite3 *.db *.pyc
```

Empfohlene Commit-Nachricht:

```text
Release V12.11.2-RC8: SOC-Darstellung und Timing-Verteilung
```

Empfohlener Tag:

```text
v12.11.2-rc8
```

Zielrepository:

```text
TTXaser2/zendure-energy-controller
```

## 6. Geänderte Produktivdateien gegenüber RC7

- `controller_logic.py`
- `web_ui.py`
- `status_page_v2.py`
- `static/status_v2.js`
- `static/status_v2.css`
- `tools/update_zendure_controller.sh`
- `version.py`
- `README.md`
- `README_INSTALLATION.md`

Neu:

- `tests/test_v12_11_2_rc8_backlog_completion.py`
- `TECHNICAL_NOTES_V12_11_2_RC8.md`
- `RELEASE_INFO_V12_11_2_RC8.md`

Zusätzlich wurden bestehende Versions- und UI-Vertragstests auf RC8 angepasst.

Gelöschte Produktivdateien: keine.
