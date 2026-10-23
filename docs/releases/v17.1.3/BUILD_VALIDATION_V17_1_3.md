**Build-QA-Stand 22.10.2026:** Reguläre und strenge V17.1.3-Suite abgeschlossen; Paket-/Fresh-extract-/Library-Gates bleiben bis zur finalen Paketverifikation getrennt.

# V17.1.3 – Technische Validierung und Evidenzgrenzen

**Basis:** ausschließlich verifizierte V17.1.2 Release-Sources (SHA256 `d8128796c897ee1fcd610ab530760c492422d4c23d6a73e3a3da5ce3630ab02e`) mit quellgeprüfter UML-Dokumentationsvorintegration. V17.1.3 ist ohne reales Update und ohne echte Clean-Fresh-Abnahme kein produktiv feldfreigegebener Release.

## Technische QA (Build-Umgebung, 22.10.2026)

Für V17.1.3 wurden **171 Testdateien, 1.254 Tests und 1.126 Subtests regulär PASS** und in der identischen disjunkten Acht-Gruppen-Suite unter `-W error::ResourceWarning` nochmals **1.254 Tests und 1.126 Subtests PASS** geprüft. Die maschinenlesbare Evidenz liegt in `validation/V17_1_3_BUILD_EVIDENCE.json`; detaillierte Testlogs und deren SHA256 liegen im separat gesicherten QA-Artefakt. Build-Gates sind kein Pi-Feld-PASS. Paket-/Fresh-extract-/Library-Gates sind vor technischer Veröffentlichung separat nachzuweisen.

Der dauerhafte UML-Regleratlas besitzt separat 22/22 fachliche Source-/Visualreviews und den vollständigen `DOC_UML_RELEASE_GATE=PASS`; dieser PASS ersetzt keine vollständige Produktregression oder eine reale Feldabnahme.

**Geschützter Regler:** `controller_logic.py` SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7`, byteidentisch.

Die Suite wurde mit einem **externen, nicht paketierten** QA-only-`paho-mqtt`-Importshim auf dem isolierten Buildhost geprüft (dort kein `paho-mqtt` installiert). Dadurch werden reale MQTT-Sitzungen weder ausgeführt noch behauptet; die reguläre Pi-Installation benötigt die tatsächliche Dependency.

**Grenzen:** Chromium-Browserdaten sind synthetische API-Fakes, kein echter Pi-Performance-, Sensor- oder physischer Command-Nachweis. `ZEC-EV-DEP-001` (realer Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Lauf auf separatem Image) bleibt offen. Natürliche S3-/Grid-Stale-/Fast-Capture-FULL_IDLE-Evidenz bleibt eigenständig offen. Ein technischer Build-PASS ist nicht `PRODUCTIVE_PASS`.


## UI/Deployment und Dokumentation

- Headless Chromium: 320/375/390/430/1280/1769 px, Standard- und Expertenmodus, kompakter Desktop-Standard bei 1280 und 1769 px **300 px**, der Minigraph **103 px**. Footer in den synthetischen Beispielen vollständig, kein horizontaler Overflow; Expertendetails dürfen die entsprechende Speicherkarte eigenständig vergrößern. Details `validation/V17_1_3_UI_VISUAL_GATE.json`.
- Deployment-Simulator 11/11 PASS; Syntax der Python-/JS-/Bash-Quellen, UML 22/22, Architektur-/History- und Datenblatt DOCX/PDF-Validierung PASS.
- Keine reale V17.1.3-MQTT-/Pi-/Naturereignisvalidierung aus diesen Buildtests ableiten.
