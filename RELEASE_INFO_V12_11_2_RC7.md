# Release-Information V12.11.2-RC7

## 1. Paket

```text
Datei: zendure_controller_v12_11_2_rc7.zip
Root:  zendure_controller_v12_11_2_rc7/
```

SHA256 und Dateigröße werden nach dem finalen Paketbau in der Release-Übergabe angegeben.

## 2. Installation auf dem Raspberry Pi

1. ZIP unverändert nach `/home/pi/Downloads/` kopieren.
2. Update mit dem bereits installierten Update-Skript starten:

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc7
```

Das Skript:

- stoppt die zuvor aktiven ZEC-Dienste,
- erstellt ein vollständiges Installationsbackup,
- sichert `config.json` separat,
- übernimmt die neue Version,
- führt Syntax- und Unit-Tests aus,
- startet die zuvor aktiven Dienste wieder.

## 3. Prüfung nach der Installation

```bash
systemctl status zendure-controller.service --no-pager -l
curl -s http://127.0.0.1:8080/ready | python3 -m json.tool
```

Browsercache anschließend aktualisieren:

```text
Desktop: Strg+F5
iOS: Statusseite neu laden; bei Bedarf Tab schließen und erneut öffnen
```

Plausibilitätskontrolle:

1. Zendure-Telemetrie bleibt bei frisch eingetroffenen Daten aktuell und flattert nicht zyklisch auf `Veraltet`.
2. Es entstehen keine periodischen Recovery-Kommandoabgleiche im ungefähr zweiminütigen Abstand mehr.
3. Erfolgreicher Kommandoabgleich und unterdrückter Versuch werden getrennt angezeigt.
4. Durchlaufzeiten erscheinen als hierarchischer Linienbaum unter dem aktiven Gesamtdurchlauf.
5. `Letzter DB-Schreibvorgang` zeigt eine reale Zeit statt `—`.
6. Das asynchrone SQLite-Timing zeigt einen Messwert oder `—`, niemals einen erfundenen Nullwert.
7. Systemressourcen zeigen die Swap-Aktivität.
8. SOC-Linien sind optisch ruhiger; Tooltipwerte entsprechen weiterhin den gespeicherten Originalwerten.
9. Die sichtbare Datumsfläche öffnet auf Desktop und iOS den nativen Kalenderwähler.
10. Ereignisüberschriften verwenden `Ereignisgruppe(n)` und kurze Telemetrieflanken erzeugen keinen Spam.

## 4. Optionale Resync-Diagnose

Nur falls nach RC7 weiterhin unerwartete Kommandoabgleiche auftreten:

```bash
cd /opt/zendure-controller
./tools/collect_resync_diagnostics.sh --minutes 20
```

Das erzeugte Archiv liegt standardmäßig unter `/home/pi/Downloads/`.

## 5. Rollback

Der genaue Backup-Pfad wird während des Updates ausgegeben, typischerweise:

```text
/home/pi/zendure-controller-backup-YYYYMMDD_HHMMSS.tar.gz
```

Bei einem fehlgeschlagenen Update versucht das Skript automatisch, zuvor aktive Dienste wieder zu starten. Für einen manuellen Rollback die Dienste stoppen, den Backup-Inhalt nach `/opt/zendure-controller` zurückspielen und die Dienste erneut starten.

## 6. GitHub-Übernahme

Lokales Repository:

```text
C:\github\zendure-energy-controller
```

Empfohlenes Vorgehen:

1. RC7-ZIP lokal entpacken.
2. Den Inhalt des Root-Ordners `zendure_controller_v12_11_2_rc7` in das lokale Repository spiegeln.
3. `.git`, produktive `config.json`, Logs, SQLite-Dateien und `__pycache__` nicht überschreiben beziehungsweise nicht committen.

Beispiel in PowerShell, Quellpfad entsprechend anpassen:

```powershell
robocopy "C:\Temp\zendure_controller_v12_11_2_rc7" "C:\github\zendure-energy-controller" /MIR /XD .git logs __pycache__ /XF config.json config.json.last-good *.sqlite *.sqlite3 *.db
```

Danach:

- `git status` beziehungsweise die Änderungen in GitHub Desktop prüfen,
- besonders gelöschte Dateien kontrollieren,
- Commit erstellen,
- Push zu `TTXaser2/zendure-energy-controller`.

Empfohlene Commit-Nachricht:

```text
Release V12.11.2-RC7: MQTT-Freshness und Diagnose-Backlog
```

Optionaler Tag:

```text
v12.11.2-rc7
```

## 7. Geänderte und neue Produktivdateien gegenüber RC6

Geändert:

- `controller_logic.py`
- `measurement_db.py`
- `operational_events.py`
- `state.py`
- `system_metrics.py`
- `web_ui.py`
- `status_page_v2.py`
- `static/status_v2.css`
- `static/status_v2.js`
- `version.py`
- `README.md`
- `README_INSTALLATION.md`

Neu:

- `tools/collect_resync_diagnostics.sh`
- `tests/test_v12_11_2_rc7_backlog_release.py`
- `TECHNICAL_NOTES_V12_11_2_RC7.md`
- `RELEASE_INFO_V12_11_2_RC7.md`

Zusätzlich wurden bestehende Versions-/UI-Vertragstests auf RC7 angepasst.

Gelöschte oder umbenannte Produktivdateien:

```text
Keine
```
