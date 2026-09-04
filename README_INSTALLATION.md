# Installation – Zendure Energy Controller V14.0.0

**Ziel-Build-ID:** `v14.0.0-20260904-r2`

`pytest` und Node.js sind **keine Produktivvoraussetzungen**. Die vollständige Testsuite wird buildseitig und erneut aus dem finalen ZIP ausgeführt. Der Installer verifiziert diese manifestgeschützte Build-Evidenz und führt auf dem Pi ausschließlich produktionsgeeignete Runtime-/Config-/Cutover-Smokes sowie Source-Manifestprüfungen aus.

## 1. Verbindlicher Ausgangsstand

Der einzige direkte Updatepfad dieses Installers ist:

```text
V13.0.3
APP_VERSION  = 13.0.3
APP_BUILD_ID = v13.0.3-20260814
```

Andere Versionen werden vor jeder Produktivänderung fail closed abgewiesen.

## 2. Paket prüfen und installieren

Das Releasepaket muss exakt heißen:

```text
zendure_controller_v14_0_0.zip
```

Auf dem Pi:

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v14_0_0.zip
unzip -t zendure_controller_v14_0_0.zip
rm -rf zendure_controller_v14_0_0
unzip -q zendure_controller_v14_0_0.zip
chmod +x zendure_controller_v14_0_0/tools/update_zendure_controller.sh
bash zendure_controller_v14_0_0/tools/update_zendure_controller.sh v14_0_0
```

Der SHA256 muss exakt dem in der Releaseübergabe genannten Wert entsprechen.

## 3. Installer-Preflight

Vor dem Stoppen produktiver Dienste prüft der Installer insbesondere:

- exakt V13.0.3 / `v13.0.3-20260814` als installierte Quelle;
- Zielversion 14.0.0 / `v14.0.0-20260904-r2`;
- vollständiges `V14_0_0_SOURCE_MANIFEST.sha256`;
- Python-Syntax;
- Bash-Syntax;
- JavaScript-Syntax, falls Node.js vorhanden ist;
- Runtime-/Readiness-Smoke;
- Config-Migration im `--check-only`-Modus;
- V14-Graph-Cutover-Preflight;
- vollständige Tests mit `ResourceWarning` als Fehler.

Node.js bleibt keine Produktivvoraussetzung.

## 4. Graph-Core-V3-Cutover

Nach dem normalen Installationsbackup wird der produktive History-Unterbau kontrolliert neu aufgebaut:

```text
Measurement V4
→ separate V3-Kandidaten-DB
→ vollständige Rebuild-/Integritätsprüfung
→ Backup bestehender DB/WAL/SHM
→ atomarer Swap
→ Post-Activation-Verify
```

Eine bereits vorhandene Engineering-V3-DB wird nicht als Produktivwahrheit übernommen.

Beschädigte V4-Quelldateien, unvollständige Quellmengen oder ein Rebuild ohne importierte Zeilen führen zum Abbruch. Die bestehende DB wird in diesem Fall nicht still überschrieben.

## 5. Rollback

Typische Sicherungen:

```text
/home/pi/zendure-controller-backup-<Zeitstempel>.tar.gz
/home/pi/config.pre-v14.0.0.<Zeitstempel>.json
/var/backups/zec-v14.0.0-root-artifacts-<Zeitstempel>
/home/pi/zec-v14-graph-backup-<Zeitstempel>/
```

Für DB/WAL/SHM werden Größe und SHA256 im Cutover-State gespeichert und beim Restore erneut geprüft. Restore verifiziert die Backupquellen und baut temporäre Restore-Artefakte vollständig auf, bevor produktive Dateien umgeschaltet werden. Ein manipuliertes oder beschädigtes Backup führt fail closed zum Abbruch.

Bei echtem Installationsfehler nach Beginn der Produktivtransaktion greift der automatische Rollbackvertrag. Zusätzlich wird ein Diagnosepaket erzeugt.

## 6. Unmittelbare Feldprüfung

Nach Installer-PASS:

```bash
grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' /opt/zendure-controller/version.py
systemctl is-active zendure-controller.service
curl -fsS http://127.0.0.1:8080/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/ready  | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/api/graph/v1/runtime | python3 -m json.tool
```

Erwartete Identität:

```text
APP_VERSION = "14.0.0"
APP_VERSION_LABEL = "V14.0.0"
APP_BUILD_ID = "v14.0.0-20260904-r2"
```

Für den Graph muss gelten:

```text
read_mode = V3_NATIVE
workspace_ready = true
control_readiness_impact = NONE
```

## 7. Vollständige read-only V14-Feldabnahme

```bash
cd /opt/zendure-controller
python3 tools/v14_field_acceptance.py \
  --base-url http://127.0.0.1:8080 \
  --cutover-report /tmp/zec_v14_cutover_report.json \
  --output /tmp/zec_v14_field_acceptance.json \
  --json
```

Der Report prüft ohne Gerätekommandos unter anderem:

- Releaseidentität und Dienststatus;
- `/health` und `/ready`;
- Graph-History-Readiness;
- Workspace und 48-h-Overview;
- Inspector;
- Command-Follow;
- Episode Comparison;
- SQLite-`quick_check`;
- Cutover-Rebuildreport;
- Integrität der Rollback-Artefakte.

Das Feldabnahmewerkzeug verändert keine Konfiguration und führt keinen Rollback aus.

## 8. Diagnosepakete

Bei Preflight- oder Updatefehlern erzeugt der Installer automatisch ein Diagnosepaket. Die rohe `config.json` wird nicht ungefiltert aufgenommen; Secrets werden redigiert. Controller- und Graph-Readiness werden getrennt dokumentiert.

## 9. Unveränderte Verträge

V14.0.0 ändert keine Regler-/Command-/Safety-Semantik und führt keine neue Retentiondauer, keinen Scheduler und keine automatische VACUUM-Policy ein.

## 10. Git-Vorschlag

```text
Commit: feat: ZEC V14.0.0 graph history platform and productive cutover
Tag:    v14.0.0
```
