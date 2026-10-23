# Verifikationsnotiz – reale Basis für UML-Übergabe

**Prüftag:** 21.10.2026. **Methode:** tatsächlich hier vorhandenes `zendure_controller_v17_1_0.zip` mit `sha256sum` geprüft; ZIP-Inhalt read-only inventarisiert und relevante `docs`/Gate-Files in Originaltext gelesen. Es wurde **keine** Controller-Datei modifiziert.

## Releaseidentität und Scope

- Datei: `zendure_controller_v17_1_0.zip`.
- SHA256 **selbst gemessen:** `11dddaaaa7831e2339a19b9b7f46412ee72f35917935b7292a005a47bfe61669`.
- Paket-Root `zendure_controller_v17_1_0/`.
- Release/Build in `docs/INDEX.md`: `V17.1.0` / `v17.1.0-20261019`.
- Projektquelle `07`: reale Installation 20.10.2026 und allgemeine Feldabnahme `PASS / FULL_READY`; Teilnachweise wie natürlicher S3-Harvest, Grid-Stale, NIGHT/MIN_SOC-Export und Fast-Capture-FULL_IDLE nicht vollständig abgenommen.

## Vorhandene Dokumentationsinfrastruktur (ZIP-Pfade)

```text
docs/INDEX.md
docs/architecture/README.md
docs/architecture/ZEC_V17_1_0_As_Built.md
docs/architecture/ZEC_Fast_Capture_V17_0_2.md
docs/specifications/README.md
docs/specifications/ZEC_S3_PRODUKTIONSSPEZIFIKATION_20261019.md
docs/decisions/README.md
docs/decisions/ADR-0002-S3-Legacy-Opt-in-20261019.md
docs/history/README.md
docs/Zendure_Energy_Controller_Handbuch.docx
docs/Zendure_Energy_Controller_Handbuch.pdf
docs/Zendure_Energy_Controller_V12_6_Benutzerhandbuch.docx/.pdf
docs/ZEC_Technisches_Datenblatt.docx/.pdf
docs/ZEC_Master_Backlog.md
tools/verify_arch_history.py
tests/test_v17_1_0_documentation_consistency.py
```

`tools/verify_arch_history.py` besitzt heute feste V17.1.0-`REQUIRED`-Einträge und Release-Stringvergleiche, prüft Verfügbarkeit, `docs/INDEX.md`-Links, spezifischen As-built-Text und Ledger-ID-Erhalt; `tests/test_v17_1_0_documentation_consistency.py` ruft `validate(ROOT)` auf. **Noch kein UML-Atlas-Gate.** Der Hauptzweig sollte das Gate auf ein releasevariables und additiv prüfendes Modell erweitern, nicht hart von allen künftigen Releases V17.1.0 verlangen.

`docs/architecture/README.md` weist S3 teilweise als noch geplanten As-built-Abschnitt aus, obwohl `docs/INDEX.md` den nun real vorhandenen V17.1.0-As-built-Abschnitt verlinkt. Das sollte im nächsten Dokumentationsrelease bereinigt werden.

## UML-V0.4-Artefaktverfügbarkeit in diesem Handover-Kontext

- Die Pfade `ZEC_UML_REGLERATLAS_V0_4.zip` sowie dessen entpackte Quelldateien waren beim aktuellen Dateisysteminventar **nicht verfügbar**.
- **Nur aus vorangegangenem Chat dokumentiert, noch nicht re-verifiziert:** 19 Diagramme, V0.4, V17.0.2-Bezug; SHA256 `1b1229b8958bafbd69cd676a1986e77605dd09673847b6872ef54481a4a8a4c5` und 7.790.684 Byte.
- Deshalb enthält dieses Handover **keine behauptete Originalkopie** des V0.4-Atlas und **keinen** fiktiven Source-/Bilddatensatz. Den Atlas im Hauptentwicklungszweig als zusätzliche Originaldatei einlesen, verifizieren und mit diesem Handover gemeinsam verwenden.
- Die verifizierte aktuelle V17.1.0-Software bleibt die implementierte Wahrheit, V0.4 ist nur visuelle Ausgangs-/Historienbasis.

## Wichtigste mit Quelle belegte V17.1.0-Änderungen gegenüber dem Diagramm-Altstand V17.0.2

- S3: `HARVEST_SEASON_POLICY_ENABLED=false` als opt-in Default, wirksame konfigurierbare Zeit-/Confirm-/Shareprofile, saisonale Auswahl `parallel|sma_priority|calendar`, `legacy_parallel` als effektiver verhaltenskompatibler Default, zusätzliche S3-Diagnosefelder.
- unabhängige 1000-ms-UI-Liveabfrage mit Quellenfreshness, ohne schnelleren Controllerzyklus;
- `GRID_STALE`-/Processing-Stale-Ereignisse und Hysterese ohne neue Commandautorität;
- strukturell prüfender SMA-OBIS-/Speedwire-Parser;
- NIGHT-/MIN_SOC-/Grid-Weiterverarbeitung behoben;
- historische Fast-Capture-/Command-/Safety-Invarianten bleiben Reglerkern; neue S3-Policy darf keine implizite Änderung an Fast-/Safety-Vertrag verursachen.

Alle weitergehenden Diagrammdetails sind bei Übernahme erneut aus tatsächlichen aktuellen Sources/Tests abzuleiten; aus dieser Notiz wird **kein eigener** Produkt-Feld-PASS gefolgert.
