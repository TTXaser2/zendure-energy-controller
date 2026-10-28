# ZEC V18.0.0 – Installation und Feldabnahme

**Build:** `v18.0.0-20261027`  · **Ziel:** V17.1.3 (`v17.1.3-20261022`) → V18.0.0

**Paket:** `zendure_controller_v18_0_0.zip`. Enthält Battery Care und vollständige Produkt-Sources, technische Dokumentation sowie Validierung. Nur mit vorangehendem Preflight installieren.

## Update via Termius (SSH als Benutzer `pi`)

1. Das unveränderte Release-ZIP nach `/home/pi/Downloads/zendure_controller_v18_0_0.zip` übertragen.
2. Die separat mitgeteilte SHA256 gegen das übertragene ZIP verifizieren.
3. Das ZIP entpacken (`unzip -q`) und in `zendure_controller_v18_0_0` wechseln.
4. Zuerst `bash tools/install_zendure_controller.sh v18_0_0 --preflight-only` ausführen und nur bei `PREFLIGHT_RESULT=PASS`, `INSTALL_MODE=SUPPORTED_UPDATE` und `SAFE_TO_INSTALL=yes` fortfahren.
5. Erst danach mit ausdrücklicher Benutzerentscheidung: `bash tools/install_zendure_controller.sh v18_0_0`.
6. Installerbericht, `/health`, `/ready`, Settings/Status und V18-Feldabnahme prüfen. Realen Battery-Care-Effekt getrennt beobachten.

## Sicherheits- und Recovery-Vertrag

Vor jedem Update prüft der Installer Runtime-/Source-Identität, Manifest, Datenblatt, Build-Evidence, Abhängigkeiten, Laufzeitbereitschaft und Konfigurationsmigration. Bei Update erstellt er vollständige Sicherungen des vorherigen `/opt/zendure-controller`, der Konfiguration sowie privilegierter Root-Artefakte. Bei Fehlern löst er einen Rollback und ein Diagnosepaket aus. **Die erfolgreiche reale Recovery ist vor Ort noch nicht nachgewiesen; Backup nicht vor Feldfreigabe löschen.**

Nur für eine tatsächlich leere Installation gilt `--fresh-install`; dies darf nicht als Update-Fallback dienen. Nach Fresh Install bleibt der Controller in `FIRST_INSTALL_SETUP` ohne gültige Konfiguration sicher inaktiv. Optionaler `--web-port` nur bei Fresh Install.

**Abgrenzung:** Die automatisierten Regressionen sind keine reale Gerätestrom-/Battery-Care-Abnahme. Meldet der Preflight einen Fehler, keinesfalls Schutzprüfungen umgehen.
