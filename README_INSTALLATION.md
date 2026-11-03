> **Nur das gesondert SHA256-verifizierte technische Releasepaket installieren.** Ein Entwicklungscheckpoint-ZIP ist kein freigegebenes Installationspaket.

# ZEC V18.0.1 – Installation und Feldabnahme

**Build:** `v18.0.1-20261102`  · **Ziel:** V18.0.0 (`v18.0.0-20261027`) → V18.0.1

**Paket:** `zendure_controller_v18_0_1.zip`. Enthält Battery Care und vollständige Produkt-Sources, technische Dokumentation sowie Validierung. Der reguläre Installer führt den vollständigen Preflight selbst vor jeder Mutation aus.

## Update via Termius (SSH als Benutzer `pi`)

1. Das unveränderte Release-ZIP nach `/home/pi/Downloads/zendure_controller_v18_0_1.zip` übertragen.
2. Die separat mitgeteilte SHA256 gegen das übertragene ZIP verifizieren.
3. Das ZIP entpacken (`unzip -q`) und in `zendure_controller_v18_0_1` wechseln.
4. Den normalen Installer einmal starten: `bash tools/install_zendure_controller.sh v18_0_1`. Dieser führt **vor** Dienststopp/Backup/Kopie seinen vollständigen Preflight aus. Bei `PREFLIGHT_RESULT=FAIL` bricht er ohne Produktivmutation ab. Ein separater `--preflight-only`-Lauf ist ausschließlich für gezielte Diagnose optional.
5. Installerbericht, `/health`, `/ready`, Settings/Status und die versionsrichtige `tools/v18_field_acceptance.py` prüfen. Realen Battery-Care-Effekt getrennt beobachten.

## Sicherheits- und Recovery-Vertrag

Vor jedem Update prüft der Installer Runtime-/Source-Identität, Manifest, Datenblatt, Build-Evidence, Abhängigkeiten, Laufzeitbereitschaft und Konfigurationsmigration. Bei Update erstellt er vollständige Sicherungen des vorherigen `/opt/zendure-controller`, der Konfiguration sowie privilegierter Root-Artefakte. Bei Fehlern löst er einen Rollback und ein Diagnosepaket aus. **Die erfolgreiche reale Recovery ist vor Ort noch nicht nachgewiesen; Backup nicht vor Feldfreigabe löschen.**

Nur für eine tatsächlich leere Installation gilt `--fresh-install`; dies darf nicht als Update-Fallback dienen. Nach Fresh Install bleibt der Controller in `FIRST_INSTALL_SETUP` ohne gültige Konfiguration sicher inaktiv. Optionaler `--web-port` nur bei Fresh Install.

**Abgrenzung:** Die automatisierten Regressionen sind keine reale Gerätestrom-/Battery-Care-Abnahme. Meldet der Preflight einen Fehler, keinesfalls Schutzprüfungen umgehen.
