# V17.1.2 – Technische Validierung und Evidenzgrenzen

**Basis:** ausschließlich verifizierte V17.1.1 Release-Sources (SHA256 `a3a055c4e4ff5b7f140cdb324ecaf00e8ab76048ef7e3cdcf56ca5f81b4db3ef`). V17.1.2 ist ohne reales Update und ohne echte Clean-Fresh-Abnahme kein produktiv feldfreigegebener Release.

## Technische QA (Build-Umgebung, 21.10.2026)

| Gate | Quellgebundener Stand |
|---|---|
| Vollständige pytest-Suite, vier disjunkte Abschnitte | **1.249 Tests + 1.095 Subtests PASS** |
| Identische Suite unter `PYTHONWARNINGS=error::ResourceWarning` | **1.249 Tests + 1.095 Subtests PASS** |
| Unabhängiger UI-/Layouttest Chromium 144 mit echtem `status_v2.css` und `status_v2.js` | **15/15 PASS**: 5/15/60 min an 320/375/390/430/1280 CSS-px, lange Quellenlabels, Bounding-Box-/Footer-/Horizontaloverflow-Gates |
| Python-AST | **263 Dateien PASS** |
| JavaScript-Syntax | drei kanonische Browser-Skripte PASS |
| Bash-Syntax | alle vorhandenen `tools/*.sh` PASS |
| Deployment-Harness | **11/11 PASS**, keine echten Hostmutationen |
| Architektur-, History-/No-Drop-Vertragsvalidator | PASS |
| Technisches Datenblatt | DOCX/PDF-Validator PASS; 10 gerenderte PDF-Seiten, visuell geprüft |
| Geschützter Controller | `controller_logic.py` SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7`, byteidentisch |
| Paketmanifest, Build-Evidence, finales Fresh-extract/CRC, Bibliotheks-Release-Readback | zum Zeitpunkt dieser Quelltextfassung **noch ausstehendes Freeze-Gate**; maßgeblich ist der externe finale technische Releasebericht |

Die Suite wurde mit einem **externen, nicht paketierten** QA-only-`paho-mqtt`-Importshim auf dem isolierten Buildhost geprüft (dort kein `paho-mqtt` installiert). Dadurch werden reale MQTT-Sitzungen weder ausgeführt noch behauptet; die reguläre Pi-Installation benötigt die tatsächliche Dependency.

**Grenzen:** Chromium-Browserdaten sind synthetische API-Fakes, kein echter Pi-Performance-, Sensor- oder physischer Command-Nachweis. `ZEC-EV-DEP-001` (realer Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Lauf auf separatem Image) bleibt offen. Natürliche S3-/Grid-Stale-/Fast-Capture-FULL_IDLE-Evidenz bleibt eigenständig offen. Ein technischer Build-PASS ist nicht `PRODUCTIVE_PASS`.
