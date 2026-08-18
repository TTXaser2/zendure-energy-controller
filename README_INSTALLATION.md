# Installation - Zendure Energy Controller V13.0.3

**Ziel-Build-ID:** `v13.0.3-20260814`

## 1. Verbindlicher Ausgangsstand

Der einzige direkte Updatepfad dieses Installers ist:

```text
V13.0.2
APP_VERSION  = 13.0.2
APP_BUILD_ID = v13.0.2-20260812
```

Andere Versionen werden vor jeder Produktivänderung abgewiesen. `config.json`, Last-Good-A/B, Konfigurationsstände, Operational Events sowie Measurement-/SQLite-Laufzeitdaten bleiben erhalten.

## 2. Paket prüfen und installieren

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v13_0_3.zip
unzip -t zendure_controller_v13_0_3.zip
rm -rf zendure_controller_v13_0_3
unzip -q zendure_controller_v13_0_3.zip
chmod +x zendure_controller_v13_0_3/tools/update_zendure_controller.sh
bash zendure_controller_v13_0_3/tools/update_zendure_controller.sh v13_0_3
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installervertrag

Vor dem Stoppen des Controllers prüft der Installer insbesondere:

- exakt V13.0.2 / `v13.0.2-20260812` als installierte Quelle;
- Zielversion `13.0.3` / Build-ID `v13.0.3-20260814`;
- `V13_0_3_SOURCE_MANIFEST.sha256`;
- Python-, Bash- und, falls Node vorhanden ist, JavaScript-Syntax;
- Runtime-/Readiness-Smoke;
- Config-Migration im `--check-only`-Modus;
- vollständige Tests mit `ResourceWarning` als Fehler.

Node.js bleibt keine Produktivvoraussetzung.

## 4. Rollback

Vor dem Ersetzen produktiver Dateien werden weiterhin vollständige Rollback-, Config- und Root-Artefakt-Backups angelegt. Bei einem echten Installationsfehler nach Beginn der Produktivtransaktion greift der bestehende automatische Rollbackvertrag.

Typische Sicherungen:

```text
/home/pi/zendure-controller-backup-<Zeitstempel>.tar.gz
/home/pi/config.pre-v13.0.3.<Zeitstempel>.json
/var/backups/zec-v13.0.3-root-artifacts-<Zeitstempel>
```

## 5. Unmittelbare Feldprüfung

```bash
grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' /opt/zendure-controller/version.py
systemctl is-active zendure-controller.service
curl -fsS http://127.0.0.1:8080/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/ready  | python3 -m json.tool
```

Erwartet:

```text
APP_VERSION = "13.0.3"
APP_VERSION_LABEL = "V13.0.3"
APP_BUILD_ID = "v13.0.3-20260814"
Dienst = active
/ready ready = true   (bevorzugter Normalfall)
```

## 6. V13.0.3 UX-Feldabnahme

1. Einen unter V13.0.1 erzeugten kompatiblen Konfigurationsstand prüfen: Titel `Konfigurationsstand prüfen`, klare No-op-Aussage, keine Checkboxen und kein Commitbutton, `Zurück` führt zum Parent.
2. Das V13.0.1-Regelprofil importieren: Titel `Import prüfen`, keine irreführende `1 Migration`, technische Übergangscodes nicht in der Primäransicht.
3. Im Expertenmodus darf `Technische Details` die rohen Codes/Migrationsschritte zeigen.
4. Einen echten Wertunterschied prüfen: Diff und Commitpfad müssen unverändert funktionieren; echte Bestätigungen bleiben wirksam.
5. Modalstack und CSRF-Refresh/Retry regressionsfrei prüfen.
6. SQLite-Writerstatus beobachten; V13.0.3 ändert dessen Architektur nicht.

## 7. Unveränderte Verträge

V13.0.3 ändert weder Regleralgorithmus noch Measurement V4, SQLite-/Backfill-Architektur, Last-Good/Recovery, Graphdatenvertrag, Portabilitätsklassifikation oder Secret-Semantik. Die Bundle-/Registry-Kompatibilität bleibt fail closed; der bekannte V13.0.1-Display-Metadata-Übergang wird lediglich UX-seitig als technischer Kompatibilitätsübergang statt als nutzerrelevante Migration dargestellt.

## 8. Git-Vorschlag

```text
Commit: fix: ZEC V13.0.3 config preview UX hotfix
Tag:    v13.0.3
```
