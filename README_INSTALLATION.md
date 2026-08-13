# Installation - Zendure Energy Controller V13.0.2

**Ziel-Build-ID:** `v13.0.2-20260812`

## 1. Verbindlicher Ausgangsstand

Der reguläre und einzige direkte Updatepfad dieses Installers ist:

```text
V13.0.1
APP_VERSION  = 13.0.1
APP_BUILD_ID = v13.0.1-20260811
```

Andere Versionen werden vor jeder Produktivänderung abgewiesen.

Erhalten bleiben insbesondere:

- `/opt/zendure-controller/config.json`;
- Last-Good-A/B-Store und Current-Pointer;
- Measurement-/SQLite-Laufzeitdaten;
- Operational Events;
- vorhandene `/opt/zendure-controller/config-states/`.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v13_0_2.zip
unzip -t zendure_controller_v13_0_2.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v13_0_2
unzip -q zendure_controller_v13_0_2.zip
chmod +x zendure_controller_v13_0_2/tools/update_zendure_controller.sh
bash zendure_controller_v13_0_2/tools/update_zendure_controller.sh v13_0_2
```

Der Installer verifiziert das Paket vor dem Dienststopp. Node.js ist keine Produktivvoraussetzung; wenn Node lokal vorhanden ist, wird die JavaScript-Syntax zusätzlich geprüft.

## 4. Preflight und Config-Migration

Vor dem Stoppen des Controllers prüft der Installer unter anderem:

- exakt V13.0.1 / `v13.0.1-20260811` als installierte Quelle;
- Paketversion und Build-ID;
- `V13_0_2_SOURCE_MANIFEST.sha256`;
- Python-, Bash- und, falls verfügbar, JavaScript-Syntax;
- Runtime-/Readiness-Smoke;
- vollständige Config-Migration im `--check-only`-Modus;
- vollständige Unit-Test-Suite mit `ResourceWarning` als Fehler.

`MEASUREMENT_SCHEMA_VERSION` bleibt produktiv auf `4` festgelegt.

## 5. Backups und atomische Installation

Nach bestandenem Preflight und vor dem Ersetzen produktiver Dateien legt der Installer Rollback-Sicherungen an, unter anderem:

```text
/home/pi/zendure-controller-backup-<Zeitstempel>.tar.gz
/home/pi/config.pre-v13.0.2.<Zeitstempel>.json
/var/backups/zec-v13.0.2-root-artifacts-<Zeitstempel>
```

Bei einem echten Installationsfehler nach Beginn der Produktivtransaktion wird automatisch auf den gesicherten Stand zurückgerollt.

## 6. Historischer Graph-Backfill und SQLite-Writer

Nach erfolgreichem Controllerstart führt der Installer den idempotenten historischen Config-Timeline-Backfill aus:

```text
tools/backfill_graph_config_timeline.py
```

V13.0.2 koordiniert dessen produktive SQLite-Schreibphase mit dem asynchronen Runtime-Writer über einen Maintenance-Lock. Die lange CSV-Suche erfolgt außerhalb dieses produktiven DB-Locks.

Wichtig:

- historische V3-Dateien werden nicht als Runtimequelle aktiviert;
- Config, Last-Good und Gerätezustand werden vom Backfill nicht verändert;
- fehlende alte Config-Snapshots werden als unbekannt markiert;
- NUL-/CSV-Leseprobleme werden diagnostiziert;
- ein Backfill-Fehler macht einen ansonsten gesunden Controller nicht unready und löst keinen Installationsrollback aus;
- der Runtime-Writer recovern nach transienten DB-Schreibfehlern selbständig mit Rollback und neuer Connection.

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
APP_VERSION = "13.0.2"
APP_VERSION_LABEL = "V13.0.2"
APP_BUILD_ID = "v13.0.2-20260812"
Dienst = active
/ready ready = true   (bevorzugter Normalfall)
```

Der Installer akzeptiert nur die ausdrücklich definierten sicheren transienten Readbackzustände; echte Daten-, Command- oder Guardfehler werden nicht weichgezeichnet.

## 8. Konfigurationsstände / Import / Export prüfen

Empfohlener Smoke in den Settings:

1. benannten Stand ohne Secrets anlegen;
2. optional den Scope „Nur verteilbare Einstellungen“ verwenden;
3. Stand öffnen und Preview/Diff prüfen, ohne ihn sofort zu aktivieren;
4. vollständigen Export erzeugen;
5. verteilbares Regelprofil erzeugen und kontrollieren, dass nur portable Parameter enthalten sind;
6. Export erneut importieren und bei identischer Konfiguration prüfen, dass kein Commit angeboten wird;
7. Rename/Delete/Preview mit „Zurück“ prüfen; der Parent-Dialog muss erhalten bleiben;
8. prüfen, dass `config.json` bis zum bestätigten Commit unverändert bleibt.

Bei Restart-Settings muss `configured` den neuen Wert zeigen, während `effective` bis zum Neustart alt bleibt und `pending_restart` gesetzt ist.

## 9. Historischen SOC-Graph prüfen

- heutiger Graph: Overlay aktualisiert sich auch bei gecachten historischen Tagespunkten;
- vergangener Tag: damalige Grenzwerte und Nachtfenster bleiben historisch erhalten;
- Configwechsel innerhalb eines Tages: getrennte zeitliche Segmente;
- Rückkehrfolge wie `99 % → 80 % → 99 %` bleibt in der Legende vollständig sichtbar;
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

Das aktuelle Benutzerhandbuch erläutert Konfigurationsstände, Scope, Import/Export, verteilbare Regelprofile, Secrets, Preview/CAS, Last-Good-Abgrenzung, historisch korrekte Graph-Overlays und den aktuellen Bedienvertrag ohne unnötige historische Release-/RC-Erzählungen.

## 12. Rollbackhinweis

Ein fehlgeschlagener produktiver Installationsschritt wird vom Installer automatisch zurückgerollt. Die ausgegebenen Backup-Pfade bis zur abgeschlossenen Feldabnahme nicht löschen.

Ein manueller Rollback soll nur auf Basis des konkret vom Installer ausgegebenen Backups erfolgen. Historische Measurement-V4-Dateien bleiben unangetastet.

## 13. Git-Übernahme

```text
Commit: fix: release ZEC V13.0.2 config-state and sqlite hardening
Tag:    v13.0.2
```
