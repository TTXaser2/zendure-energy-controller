# Release-Information V12.11.2-RC6

## Installation auf dem Raspberry Pi

1. `zendure_controller_v12_11_2_rc6.zip` unverändert nach `/home/pi/Downloads/` kopieren.
2. Update mit dem bereits installierten Update-Skript starten:

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc6
```

3. Nach erfolgreichem Lauf prüfen:

```bash
systemctl status zendure-controller.service --no-pager -l
curl -s http://127.0.0.1:8080/ready | python3 -m json.tool
```

4. Statusseite öffnen und im Browser einmal `Strg+F5` ausführen.
5. Plausibilitätsprüfung:
   - breite Desktop-Ansicht zeigt vier untere Karten nebeneinander,
   - `/status_old` liefert die historische Referenzseite,
   - Controllerkarte zeigt Klartexte statt technischer Statuscodes,
   - Betriebsereignisse zeigen keine widersprüchlichen Telemetrie-Titel.

Das Update-Skript erstellt vor dem Kopieren automatisch ein Backup des aktuellen Installationsverzeichnisses und sichert `config.json` separat.

## Rollback

Der genaue Backup-Pfad wird während des Updates ausgegeben, typischerweise:

```text
/home/pi/zendure-controller-backup-YYYYMMDD_HHMMSS.tar.gz
```

Bei einem fehlgeschlagenen Update versucht das Skript, zuvor aktive Dienste wieder zu starten. Für einen manuellen Rollback zuerst die Dienste stoppen, den Backup-Inhalt nach `/opt/zendure-controller` zurückspielen und anschließend die Dienste erneut starten.

## GitHub-Übernahme

Lokales Repository:

```text
C:\github\zendure-energy-controller
```

Empfohlenes Vorgehen:

1. RC6-ZIP lokal entpacken.
2. Den Inhalt des Root-Ordners `zendure_controller_v12_11_2_rc6` in das lokale Repository übernehmen.
3. Lokale Laufzeitdateien wie `config.json`, Logs, SQLite-Datenbanken und `__pycache__` nicht committen.
4. Änderungen in GitHub Desktop prüfen.
5. Empfohlene Commit-Nachricht:

```text
Release V12.11.2-RC6: Status-Dashboard-Hotfix
```

6. Optionaler Git-Tag:

```text
v12.11.2-rc6
```

7. Commit und Tag in das private Repository `TTXaser2/zendure-energy-controller` pushen.

## Wesentliche geänderte Produktivdateien

- `version.py`
- `web_ui.py`
- `status_page_v2.py`
- `operational_events.py`
- `static/status_v2.css`
- `static/status_v2.js`
- `tests/test_v12_11_2_rc6_ui_diagnostics_hotfix.py`
- Versionsassertionen bestehender Tests
- `TECHNICAL_NOTES_V12_11_2_RC6.md`
- `RELEASE_INFO_V12_11_2_RC6.md`
