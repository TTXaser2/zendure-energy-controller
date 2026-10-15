# ZEC – Projektquellen-Index

**Stand:** 23.09.2026  
**Status:** kanonisch – Einstiegspunkt für alle neuen ZEC-Chats und Entwicklungsblöcke

## 1. Zweck

Diese Datei definiert den aktiven Projektquellenbestand für „ZEC – Zendure Energy Controller“. Historische Chats, alte Release-ZIPs, Zwischen-Checkpoints und alte Übergaben sind keine aktive Quellbasis. Aktuelle reale Sources und reale Evidenz haben gemäß Quellenrangfolge Vorrang.

## 2. Aktuelle kanonische Entwicklungs- und Feldbasis

- aktuelle reale Runtimebasis: `V17.0.1 / 17.0.1 / v17.0.1-20260922`; reales Update V16.2.5 -> V17.0.1 **PASS**, automatischer V17-Feldlauf **PASS / FULL_READY**.
- aktueller technischer Releasekandidat: `V17.0.2 / 17.0.2 / v17.0.2-20260923`; Status **TECHNICAL BUILD PASS / FIELD_PENDING**.
- V17.0.2 ist ein isolierter `+0.0.1` Evidence-/Tooling-Hotfix für drei real in V17.0.1 gefundene Fast-Capture-Verifikationsdefekte: fehlende Fast-Felder im `record_graph_point()` -> Measurement-V4-Pfad, zu breite historische Snapshot-Versionprüfung im Fast-Analyzer sowie SIGPIPE/rc=141 im Analysis-Package `--latest-only`.
- vollständige V17.0.2-Regression: **157 Testdateien / 1169 Tests + 706 Subtests PASS**; identischer `ResourceWarning=error`-Lauf PASS; Bash 13/13, Browser-JavaScript 3/3, Python-Compileall, Deployment-Harness 11/11, Datenblatt und Build-Evidence PASS. Release-Hygiene, Source-Manifest 932/932, kanonischer ZIP-Root sowie Paket-/Fresh-extract-Manifest-, Build-Evidence- und Datenblatt-Gates sind im Release-Freeze PASS; dieselben Gates werden nach Dokumentationsfreeze auf dem exakt veröffentlichten ZIP erneut ausgeführt.
- geschützter Reglerkern `controller_logic.py`: SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031`, byteidentisch zu V17.0.1. Keine Änderung an A400/R100-, Command-, Safety-, Cross-Charge- oder Recoverysemantik.
- Fast Capture ist auf der realen V17.0.1-Runtime `shadow`; Night-Mode-Safety wurde real beobachtet. V17.0.1-Shadow-V4-Daten sind wegen des gefundenen Evidence-Pfadddefekts **nicht** als kanonischer Fast-Funktionsnachweis verwertbar. `active` bleibt nicht freigegeben. Nach V17.0.2-Installation muss neue Shadow-Evidenz gesammelt werden.
- V17.0.0 bleibt zurückgezogen: rootless Packaging-Reject im realen Installer-Preflight vor jeder Produktivmutation.
- UI V17: Desktop-Warning-Chip/Popover unter `ZEC-BL-UI-STATUS-003` ist am 23.09.2026 real visuell PASS; mobile Bottom-Sheet-Variante bleibt separat zu prüfen.
- projektweiter vollständiger `PRODUCTIVE-PASS` bleibt zusätzlich wegen des deferred `ZEC-EV-DEP-001` offen.

## 3. Quellenrangfolge bei Konflikten

1. aktuelle reale produktive Evidenz und aktuelle verifizierte Codebasis;
2. ausdrücklich freigegebene Spezifikation des laufenden Entwicklungsblocks;
3. `07_ZEC_CURRENT_RELEASE_AND_FIELD_STATUS.md`;
4. kanonische Dauerquellen `01` bis `06`;
5. normative Analyse- und Hardwareschonungs-Regelwerke;
6. Lernwerkzeug innerhalb seines dokumentierten Geltungsbereichs;
7. historische Releases, Übergaben und Chats.

Technischer Build-PASS ist nicht gleich reale Feldfreigabe.

## 4. Aktive Projektquellen

| Datei | Rolle |
|---|---|
| `00_ZEC_PROJECT_SOURCE_INDEX.md` | Einstieg und Quellenrangfolge |
| `01_ZEC_PROJECT_RULES.md` | Arbeits-/Freigabe-/Sicherungsregeln |
| `02_ZEC_CURRENT_STATE_AND_ARCHITECTURE.md` | aktueller System-/Architekturstand |
| `03_ZEC_CONTROL_AND_SAFETY_INVARIANTS.md` | normative Regler-/Safety-Invarianten |
| `04_ZEC_UI_SETTINGS_AND_DIAGNOSTICS_CONTRACT.md` | UI-/Settings-/Diagnosevertrag |
| `05_ZEC_BACKLOG_AND_ROADMAP.md` | persistentes Master-Ledger und Roadmap |
| `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md` | Build-/Release-/Handoververtrag |
| `07_ZEC_CURRENT_RELEASE_AND_FIELD_STATUS.md` | aktuelle Release-/Feldevidenz |
| `ZEC_ANALYSE_REGELWERK_V1.1.md` | normative Analysemethodik |
| `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md` | Hardware-/Batterieschonung |
| `README_INSTALLATION_V17_0_2.md` | aktuelle V17.0.2 Installation/Update-Anleitung |
| `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_2_5_REVALIDATED.md` | freigegebene/revalidierte Blockautorität für Fast Capture |
| `zendure_controller_v17_0_2.zip` | aktueller TECHNICAL-BUILD-PASS-Kandidat; reale Installation/erneute Shadow-Evidenz noch ausstehend |
| `zendure_controller_v17_0_1.zip` | aktuelle reale Runtime-/Feldbasis bis erfolgreicher V17.0.2-Installation |
| `zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx` | Lern-/Simulationsreferenz |

## 5. Historische Vorgänger

V17.0.0 ist ein real vor Produktivmutation abgewiesener und zurückgezogener Packaging-Fehlrelease. V16.2.5 und ältere Releases bleiben Feld-/Releaseprovenienz, sind aber keine aktuelle Implementierungsautorität. V17.0.1 bleibt reale Runtimebasis bis zur erfolgreichen V17.0.2-Installation.

## 6. Lernwerkzeug-Grenze

`zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx` bleibt Referenz, aber keine Default-Autorität. Maßgeblich sind reale Sources, `config.example.json` und `SettingsRegistry`.

## 7. No-Drop

Alle bisherigen **85** stabilen Ledger-IDs bleiben erhalten. Fast Capture, Adaptive einschließlich Child-IDs, usable-SOC Block B, Primary Metadata, Battery Care, Status-Expertenmodus, Storage-/Analyse-/Simulationsthemen und `ZEC-EV-DEP-001` bleiben recoverbar. Der V17.0.2-Hotfix wird unter der bestehenden ID `ZEC-BL-CTRL-FASTCAP-001` als Feld-/Evidence-Korrektur fortgeschrieben; keine neue Produkt-ID ist erforderlich.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**
