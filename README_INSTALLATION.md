# Installation - Zendure Energy Controller V12.13.0

**Ziel-Build-ID:** `v12.13.0-20260811`

## 1. Normaler Ausgangsstand

Der reguläre Updatepfad ist:

```text
V12.12.2
APP_VERSION  = 12.12.2
APP_BUILD_ID = v12.12.2-20260810
```

Der Installer akzeptiert zusätzlich die bereits dokumentierten kompatiblen Recovery-Ausgangsstände. Ein unbekannter Stand wird vor jeder Produktivänderung abgelehnt.

Eine vorhandene `config.json`, Last-Good-Slots und Laufzeitdaten bleiben erhalten.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_13_0.zip
unzip -t zendure_controller_v12_13_0.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v12_13_0
unzip -q zendure_controller_v12_13_0.zip
chmod +x zendure_controller_v12_13_0/tools/update_zendure_controller.sh
bash zendure_controller_v12_13_0/tools/update_zendure_controller.sh v12_13_0
```

Node.js ist keine Produktivvoraussetzung. JavaScript wird ohne Node.js über das buildseitig geprüfte Source-Manifest abgesichert.

## 4. Config-Migration

Für bestehende V12.12.2-Installationen mit dem normalen Marker `MEASUREMENT_SCHEMA_VERSION=4` ist die Migration ein No-op.

Falls eine historische Konfiguration noch den alten Marker `3` enthält, wird ausschließlich dieser Kompatibilitätsmarker kontrolliert auf `4` migriert. Das aktiviert keine neue Loggingfunktion und ändert keine Reglerparameter.

Nach der Installation kann geprüft werden:

```bash
python3 - <<'PY'
import json
p='/opt/zendure-controller/config.json'
with open(p, encoding='utf-8') as f:
    cfg=json.load(f)
print('MEASUREMENT_SCHEMA_VERSION =', cfg.get('MEASUREMENT_SCHEMA_VERSION'))
PY
```

Erwartet:

```text
MEASUREMENT_SCHEMA_VERSION = 4
```

## 5. Unmittelbare Verifikation

```bash
grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' \
  /opt/zendure-controller/version.py
systemctl is-active zendure-controller.service
curl -fsS http://127.0.0.1:8080/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/ready  | python3 -m json.tool
```

Erwartet:

```text
APP_VERSION = "12.13.0"
APP_VERSION_LABEL = "V12.13.0"
APP_BUILD_ID = "v12.13.0-20260811"
Dienst = active
/ready ready = true   (bevorzugter Normalfall)
```

Die Single-Owner-Diagnostik aus V12.12.2 bleibt erhalten.

## 6. Measurement-V4-Abnahme

Bei aktiviertem Measurement-Logging gilt:

- neu geschriebene produktive CSV-Dateien sind V4;
- Standardprofil hat 246 Felder, Extended 249;
- ein historischer Schema-3-Marker kann keinen V3-Writer aktivieren;
- Manifest-/Rotation-/Rowcount-/Close-Semantik aus V12.12.2 bleibt erhalten.

Es ist keine künstliche Dateirotation für die Installation erforderlich.

## 7. Graph-CSV

Der UI-Graph-Export ist bewusst kein Measurement-Paket. Optional prüfen:

```bash
curl -fsS http://127.0.0.1:8080/graph-data.csv | head -n 2
```

Der Export verwendet `ZEC-GRAPH-EXPORT-V1` und darf nicht als `ZEC-MEASUREMENT-V3` oder `ZEC-MEASUREMENT-V4` gekennzeichnet sein.

## 8. Historische V3-Dateien

Alte V3-Dateien werden nicht gelöscht oder umgeschrieben. Replay-, Analyse- und Importwerkzeuge können historische V3-Daten weiterhin offline lesen. Es gibt jedoch keinen produktiven V3-Runtimewriter mehr.

## 9. Handbuch

Aktuelles Handbuch:

```text
/opt/zendure-controller/docs/Zendure_Energy_Controller_Handbuch.pdf
```

Es ist als Benutzerhandbuch V12.13.0 gekennzeichnet und beschreibt V4-only Runtime sowie den historischen V3-Lesepfad.

## 10. Backups und Rollback

Nach Beginn der Produktivtransaktion legt der Installer unter anderem an:

```text
/home/pi/zendure-controller-backup-<Zeitstempel>.tar.gz
/home/pi/config.pre-v12.13.0.<Zeitstempel>.json
/var/backups/zec-v12.13.0-root-artifacts-<Zeitstempel>
```

Diese Sicherungen bis zum Abschluss der Feldabnahme nicht löschen. Bei einem echten Fehler nach dem Dienststopp verwendet das Update-Skript den vorhandenen automatischen Rollbackpfad.

Der feste Marker `MEASUREMENT_SCHEMA_VERSION=4` bleibt bewusst in der Config erhalten, damit auch ein Rollback auf V12.12.2 weiterhin den V4-Pfad auswählt.

## 11. Git-Übernahme

```text
Commit: Release V12.13.0
Tag:    v12.13.0
```
