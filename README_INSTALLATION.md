# Installation – Zendure Energy Controller V14.1.2

**Release:** `V14.1.2`  
**Build-ID:** `v14.1.2-20260905`

`pytest` und Node.js sind keine Produktivvoraussetzungen. Vollständige Test- und ResourceWarning-Gates werden buildseitig und erneut aus dem finalen ZIP ausgeführt. Der Pi-Installer verwendet nur produktionsgeeignete Smokes, Manifestprüfung, Config-Preflight und read-only Graph-Core-V3-Verifikation.

## 1. Verbindlicher Ausgangsstand

Direktes Update ausschließlich von:

```text
V14.1.1
APP_VERSION  = 14.1.1
APP_BUILD_ID = v14.1.1-20260905
```

Andere Ausgangsstände werden vor jeder Produktivänderung fail closed abgewiesen.

## 2. Paketname und Installation

```text
zendure_controller_v14_1_2.zip
```

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v14_1_2.zip
unzip -t zendure_controller_v14_1_2.zip
rm -rf zendure_controller_v14_1_2
unzip -q zendure_controller_v14_1_2.zip
chmod +x zendure_controller_v14_1_2/tools/update_zendure_controller.sh
bash zendure_controller_v14_1_2/tools/update_zendure_controller.sh v14_1_2
```

Der SHA256 muss exakt dem im Release-Exit-Gate genannten Wert entsprechen.

## 3. Installer-Preflight

Vor dem Stoppen der Dienste werden geprüft:

- exakte V14.1.1-Quellidentität;
- V14.1.2-Zielidentität;
- `V14_1_2_SOURCE_MANIFEST.sha256`;
- Python-/Bash-Syntax;
- JavaScript-Syntax, falls Node.js vorhanden ist;
- Runtime-/Readiness-Smoke mit `ResourceWarning` als Fehler;
- Config-Migration `--check-only`;
- bestehender Graph Core V3 per read-only Verify;
- manifestgeschützte vollständige Build-Testevidenz.

## 4. Datenbankverhalten

V14.1.2 baut Graph Core V3 **nicht erneut auf**. Die produktive V3-Datenbank aus V14.1.1 bleibt erhalten. `logs/`, SQLite-Dateien, Config, Last-Good und Konfigurationsstände werden beim Source-Copy nicht überschrieben.

Vor und nach dem Kopieren muss die vorhandene V3-Datenbank erfolgreich verifiziert werden.

## 5. Rollback

Vor jeder Produktivänderung erzeugt der Installer ein vollständiges `/opt/zendure-controller`-Backup sowie Config- und Root-Artefakt-Backups. Größe und SHA256 des vollständigen Release-Backups werden im Installationsreport gespeichert.

Bei echtem Installationsfehler nach Beginn der Transaktion wird das vollständige Backup automatisch wiederhergestellt und der vorherige Dienstzustand hergestellt.

## 6. Feldabnahme

Nach erfolgreicher Installation:

```bash
cd /opt/zendure-controller
python3 tools/v14_field_acceptance.py \
  --base-url http://127.0.0.1:8080 \
  --install-report /tmp/zec_v14_1_2_install_report.json \
  --output /tmp/ZEC_V14_1_2_FIELD_ACCEPTANCE.json \
  --json
```

Die Abnahme ist read-only und sendet keine Gerätekommandos. Sie prüft Releaseidentität, Dienst, `/health`, `/ready`, V3-Runtime, Greenfield-Graphseite, 48-h-Overview, Inspector, Command-Follow, Interaktionsvertrag (Zeitraumvergleich, t=0-Episodenvergleich, Bereichsauswahl, synchroner Cursor, Evidence-Segmente), SQLite-`quick_check` sowie die Integrität des vollständigen Release-Rollback-Backups.

## 7. Unveränderte Verträge

V14.1.2 ändert keine Regler-/Command-/Safety-Semantik. Keine neue Retentiondauer, kein Scheduler, keine automatische VACUUM-Policy.
