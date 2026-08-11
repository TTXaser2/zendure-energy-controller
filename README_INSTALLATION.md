# Installation - Zendure Energy Controller V13.0.0

**Ziel-Build-ID:** `v13.0.0-20260811`

## 1. Verbindlicher Ausgangsstand

Der reguläre und einzige direkte Updatepfad dieses Installers ist:

```text
V12.13.0
APP_VERSION  = 12.13.0
APP_BUILD_ID = v12.13.0-20260811
```

Ältere V12.12.x-/RC-Stände werden vor jeder Produktivänderung abgewiesen. Es gibt keinen Rücksprung auf eine ältere Entwicklungsbasis.

Erhalten bleiben insbesondere:

- `/opt/zendure-controller/config.json`;
- Last-Good-A/B-Store und Current-Pointer;
- Measurement-/SQLite-Laufzeitdaten;
- Operational Events;
- vorhandene `/opt/zendure-controller/config-states/`.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v13_0_0.zip
unzip -t zendure_controller_v13_0_0.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v13_0_0
unzip -q zendure_controller_v13_0_0.zip
chmod +x zendure_controller_v13_0_0/tools/update_zendure_controller.sh
bash zendure_controller_v13_0_0/tools/update_zendure_controller.sh v13_0_0
```

Der Installer entpackt und verifiziert das Release-ZIP vor dem Dienststopp noch einmal selbst. Node.js ist keine Produktivvoraussetzung; wenn Node lokal vorhanden ist, wird die JavaScript-Syntax zusätzlich geprüft.

## 4. Preflight und Config-Migration

Vor dem Stoppen des Controllers prüft der Installer unter anderem:

- exakt V12.13.0 / `v12.13.0-20260811` als installierte Quelle;
- Paketversion und Build-ID;
- `V13_0_0_SOURCE_MANIFEST.sha256`;
- Python-, Bash- und, falls verfügbar, JavaScript-Syntax;
- Runtime-/Readiness-Smoke;
- vollständige Config-Migration im `--check-only`-Modus;
- vollständige Unit-Test-Suite mit `ResourceWarning` als Fehler.

Die gemeinsame V13-Migrationsautorität übernimmt weiterhin die bestehenden historischen Config-Migrationen. `MEASUREMENT_SCHEMA_VERSION` bleibt produktiv auf `4` festgelegt.

## 5. Backups und atomische Installation

Nach bestandenem Preflight und vor dem Ersetzen produktiver Dateien legt der Installer Rollback-Sicherungen an, unter anderem:

```text
/home/pi/zendure-controller-backup-<Zeitstempel>.tar.gz
/home/pi/config.pre-v13.0.0.<Zeitstempel>.json
/var/backups/zec-v13.0.0-root-artifacts-<Zeitstempel>
```

Bei einem echten Installationsfehler nach Beginn der Produktivtransaktion wird automatisch auf den gesicherten Stand zurückgerollt.

## 6. Einmaliger historischer Graph-Backfill

Nach erfolgreichem Controllerstart führt der Installer einmalig und idempotent aus:

```text
tools/backfill_graph_config_timeline.py
```

Das Werkzeug liest ausschließlich historische Measurement-V4-Dateien und `zec_config_snapshots.json`, rekonstruiert `config_control_hash`-Wechsel und ergänzt die kleine SQLite-Config-Zeitachse.

Wichtig:

- historische V3-Dateien werden nicht als Runtimequelle aktiviert;
- Config, Last-Good und Gerätezustand werden vom Backfill nicht verändert;
- fehlende alte Config-Snapshots werden als unbekannt markiert;
- ein Backfill-Fehler macht einen ansonsten gesunden V13-Controller nicht unready und löst keinen Installationsrollback aus.

Neue Configwechsel werden anschließend automatisch inkrementell durch die Runtime erfasst.

## 7. Unmittelbare Verifikation

```bash
grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' \
  /opt/zendure-controller/version.py
systemctl is-active zendure-controller.service
curl -fsS http://127.0.0.1:8080/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/ready  | python3 -m json.tool
```

Erwartet:

```text
APP_VERSION = "13.0.0"
APP_VERSION_LABEL = "V13.0.0"
APP_BUILD_ID = "v13.0.0-20260811"
Dienst = active
/ready ready = true   (bevorzugter Normalfall)
```

Der Installer akzeptiert nur die ausdrücklich definierten sicheren transienten Readbackzustände; echte Daten-, Command- oder Guardfehler werden nicht weichgezeichnet.

## 8. Konfigurationsstände / Import / Export prüfen

In den Settings steht `Konfigurationsstände` zur Verfügung. Empfohlener Smoke:

1. benannten Stand ohne Secrets anlegen;
2. Stand öffnen und Preview/Diff prüfen, ohne ihn sofort zu aktivieren;
3. vollständigen Export erzeugen;
4. teilbares Regelprofil erzeugen und kontrollieren, dass nur portable Parameter enthalten sind;
5. optional Export erneut importieren und Preview abbrechen;
6. prüfen, dass `config.json` bis zum bestätigten Commit unverändert bleibt.

Bei Restart-Settings muss `configured` den neuen Wert zeigen, während `effective` bis zum Neustart alt bleibt und `pending_restart` gesetzt ist.

## 9. Historischen SOC-Graph prüfen

Nach einer Settingsänderung an Max-/Min-SOC, Nachtreserve oder Nachtzeit gilt:

- heutiger Graph: Overlay aktualisiert sich auch bei gecachten historischen Tagespunkten;
- vergangener Tag: damalige Grenzwerte und Nachtfenster bleiben historisch erhalten;
- Configwechsel innerhalb eines Tages: getrennte zeitliche Segmente;
- fehlender historischer Snapshot: keine rückwirkende Verwendung der aktuellen Config.

## 10. Measurement V4

Der produktive Messvertrag bleibt:

```text
ZEC-MEASUREMENT-V4
Standard: 246 Felder
Extended: 249 Felder
```

Historische V3-Dateien bleiben offline/read-only. Es wird kein V3-Runtimewriter eingeführt.

## 11. Handbuch

```text
/opt/zendure-controller/docs/Zendure_Energy_Controller_Handbuch.pdf
```

Das Handbuch ist als Benutzerhandbuch V13.0.0 gekennzeichnet und erläutert zusätzlich Konfigurationsstände, Scope, Import/Export, teilbare Regelprofile, Secrets, Preview/CAS, Last-Good-Abgrenzung und historisch korrekte Graph-Overlays.

## 12. Rollbackhinweis

Ein fehlgeschlagener produktiver Installationsschritt wird vom Installer automatisch zurückgerollt. Die ausgegebenen Backup-Pfade bis zur abgeschlossenen Feldabnahme nicht löschen.

Ein manueller Rollback soll nur auf Basis des konkret vom Installer ausgegebenen Backups erfolgen; dabei bleiben historische Measurement-V4-Dateien unangetastet. Die zusätzliche `graph_config_timeline` wird von V12.13.0 ignoriert und ändert den Measurement-V4-Vertrag nicht.

## 13. Git-Übernahme

```text
Commit: feat: release ZEC V13.0.0 config states and historical graph overlays
Tag:    v13.0.0
```
