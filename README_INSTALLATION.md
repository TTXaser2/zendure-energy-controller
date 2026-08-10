# Installation – Zendure Energy Controller V12.12.2

**Ziel-Build-ID:** `v12.12.2-20260810`

## 1. Normaler Ausgangsstand

Der reguläre Updatepfad ist:

```text
V12.12.1
APP_VERSION  = 12.12.1
APP_BUILD_ID = v12.12.1-20260810
```

Der Installer akzeptiert zusätzlich die bereits dokumentierten kompatiblen Recovery-Ausgangsstände. Ein unbekannter Stand wird vor jeder Produktivänderung abgelehnt.

Eine vorhandene `config.json`, Last-Good-Slots und Laufzeitdaten bleiben erhalten.

## 2. Paket prüfen

```bash
cd /home/pi/Downloads
sha256sum zendure_controller_v12_12_2.zip
unzip -t zendure_controller_v12_12_2.zip
```

Der SHA256 muss exakt dem Wert der Releaseübergabe entsprechen.

## 3. Installieren

```bash
cd /home/pi/Downloads
rm -rf zendure_controller_v12_12_2
unzip -q zendure_controller_v12_12_2.zip
chmod +x zendure_controller_v12_12_2/tools/update_zendure_controller.sh
bash zendure_controller_v12_12_2/tools/update_zendure_controller.sh v12_12_2
```

Node.js ist keine Produktivvoraussetzung. JavaScript wird ohne Node.js über das buildseitig geprüfte Source-Manifest abgesichert.

## 4. Unmittelbare Verifikation

```bash
grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' \
  /opt/zendure-controller/version.py
systemctl is-active zendure-controller.service
curl -fsS http://127.0.0.1:8080/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8080/ready  | python3 -m json.tool
```

Erwartet:

```text
APP_VERSION = "12.12.2"
APP_VERSION_LABEL = "V12.12.2"
APP_BUILD_ID = "v12.12.2-20260810"
Dienst = active
/health alive = true
/ready ready = true   (bevorzugter Normalfall)
```

`/health` und `/ready` enthalten zusätzlich `instance_owner.active=true`, Owner-PID und Build-ID.

## 5. Kontrollierter Single-Instance-Feldtest

Dieser Test soll den laufenden Produktivdienst **nicht** stoppen oder beeinflussen. Aus einem anderen Working Directory wird lediglich ein zweiter Startversuch ausgeführt:

```bash
cd /tmp
python3 /opt/zendure-controller/ZendureController.py
rc=$?
echo "Zweitstart Exit-Code: $rc"
```

Erwartet:

```text
Zweite Zendure-Controllerinstanz abgewiesen
...
Zweitstart Exit-Code: 73
```

Anschließend sofort prüfen:

```bash
systemctl is-active zendure-controller.service
curl -fsS http://127.0.0.1:8080/ready | python3 -m json.tool
```

Der bestehende Owner muss weiter `active`/`ready=true` sein. Die abgewiesene Instanz darf keine Gerätekommandos und keinen eigenen produktiven Measurement-Stream erzeugen.

## 6. Weitere Feldabnahme

1. Status → `Controller & Schnittstellen`: Owner wird als aktiv/exklusiv angezeigt; Desktop-Panel per Klick öffnen und mit Mausrad bis nach unten scrollen.
2. Smartphone → Speicher-SOC-Tagesgraph: Datenpunkt wählen; Kurve und Auswahlmarkierung bleiben sichtbar, Detailwerte stehen unter dem Plot.
3. Mobile Settings-Navigation aus V12.12.1 bleibt beim tiefen Scroll erreichbar.
4. Normalen AUTO-/HOLD-Betrieb beobachten; keine neuen Command-/Mode-Wiederholungen.
5. NIGHT-/Reserve-/Neutralisierungsvertrag bei regulärer Gelegenheit unverändert beobachten; keine künstliche Provokation nötig.
6. Nach einer **natürlich eintretenden** Measurement-Rotation das Manifest prüfen: tatsächlicher Rotationsgrund, finaler `row_count`, `closed_time_utc` des abgeschlossenen Files. Keine Rotation nur für die Abnahme erzwingen.

## 7. Harvest-Zeitsemantik

Die Änderung betrifft ausschließlich Entry-/Hold-Zeitführung und Beobachtungsdistinctness. Eine künstliche High-SOC-/Harvest-Provokation ist nicht erforderlich. Der Build enthält Differential-/Jitter-/Stalltests gegen den bisherigen nominalen Normalbetrieb.

## 8. Handbuch

Das Settings-Hilfe-/Glossar-Handbuch bleibt in diesem Bugfix die fachlich unveränderte V12.12.1-Edition:

```text
/opt/zendure-controller/docs/Zendure_Energy_Controller_Handbuch.pdf
```

V12.12.2 ändert keine Settings-Hilfe- oder Glossarsemantik.

## 9. Backups und Rollback

Nach Beginn der Produktivtransaktion legt der Installer unter anderem an:

```text
/home/pi/zendure-controller-backup-<Zeitstempel>.tar.gz
/home/pi/config.pre-v12.12.2.<Zeitstempel>.json
/var/backups/zec-v12.12.2-root-artifacts-<Zeitstempel>
```

Diese Sicherungen bis zum Abschluss der Feldabnahme nicht löschen. Bei einem echten Fehler nach dem Dienststopp verwendet das Update-Skript den vorhandenen automatischen Rollbackpfad.

## 10. Git-Übernahme

```text
Commit: Release V12.12.2
Tag:    v12.12.2
```
