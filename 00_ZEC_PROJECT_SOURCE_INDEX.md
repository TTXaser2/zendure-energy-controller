# ZEC – Projektquellen-Index

**Stand:** 19.10.2026  
**Status:** kanonisch – Einstiegspunkt für alle neuen ZEC-Chats und Entwicklungsblöcke

## 1. Zweck

Diese Datei definiert den aktiven Projektquellenbestand für „ZEC – Zendure Energy Controller“. Historische Chats, alte Release-ZIPs, Zwischen-Checkpoints und alte Übergaben sind keine aktive Quellbasis. Aktuelle reale Sources und reale Evidenz haben gemäß Quellenrangfolge Vorrang.

## 2. Aktuelle kanonische Entwicklungs- und Feldbasis

- aktuelle reale Runtimebasis: `V17.0.2 / 17.0.2 / v17.0.2-20260923`; reales Update V17.0.1 -> V17.0.2 **PASS**, allgemeiner automatischer V17-Feldlauf **PASS / FULL_READY**.
- aktuelles veröffentlichtes Paket: `zendure_controller_v17_0_2.zip`, SHA256 `82bd2db52a71b4a4e56f8e8c39e30511494fb02f8735909667052b73bd82f311`, Größe `14.402.481 Byte`.
- vollständige V17.0.2-Regression: **157 Testdateien / 1169 Tests + 706 Subtests PASS**; identischer `ResourceWarning=error`-Lauf PASS; Bash 13/13, Browser-JavaScript 3/3, Python-Compileall, Deployment-Harness 11/11, Datenblatt und Build-Evidence PASS. Release-Hygiene, Source-Manifest 932/932, ZIP-Integrität und Fresh-extract-Manifest 932/932 sind auf dem exakt veröffentlichten Installer-ZIP PASS.
- geschützter V17.0.2-Reglerkern `controller_logic.py`: SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031`.
- Fast Capture: neue V17.0.2-Shadow-Evidenz liegt vor und der definierte Shadow-Gate ist **PASS**. Reale Active-Evidenz für `NEAR_LIMIT` zeigt in den beobachteten Aspekten Exportreduktion, Command-Wirkung, Import-Guard/Recovery und Cross-Charge **PASS**; eine belastbare Active-`FULL_IDLE`-Episode fehlt noch. Der Fast-Capture-Feldabschluss bleibt deshalb **EVIDENCE_PENDING**. Letzter real beobachteter Nutzungsstand: Fast Capture `active`.
- Fast-Capture-Evidence-Tooling bleibt offen: der Analyzer muss Berechnungsprüfungen an die tatsächliche Branch-Anwendbarkeit koppeln; große V4-Historien dürfen auf dem produktiven Pi nicht unbounded in RAM materialisiert werden.
- reale V17.0.2-Funde vom 25.09.2026: `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` (Nacht+MIN_SOC-Control-Gap) und `ZEC-BL-GRID-SMA-OBIS-001` (strukturell unzureichender SMA-Speedwire-/OBIS-Parser) sind für den **nächsten Produktrelease zwingend zu beheben**.
- V17.0.0 bleibt zurückgezogen: rootless Packaging-Reject im realen Installer-Preflight vor jeder Produktivmutation.
- projektweiter vollständiger `PRODUCTIVE-PASS` bleibt zusätzlich wegen des deferred `ZEC-EV-DEP-001` offen.

## 2a. Fachlicher Planungsstand 18.10.2026 (keine neue Runtime)

- Das Master-Ledger `05` priorisiert **S3**, die getrennten Spezifikationen für **usable SOC (B2)** und **Kapazitätsgewichtung (C1)** sowie winterpriorisiert **Battery Care**; die frühere gemeinsame Adaptive-Umbrella-Sequenz vom 20.09. wurde am 18.10. durch Nutzerentscheidung im Planungsstand abgelöst. Ausbleibender B2/C1-Mehrwert darf Battery Care nicht blockieren.
- Adaptive (A1; `ZEC-BL-CTRL-ADAPTIVE-001`, `ZEC-BL-CTRL-001`) ist **DEFERRED / EVIDENCE_GAP**, nicht gestrichen. Die 23-Tage-Herbstanalyse belegt derzeit begrenzten High-SOC-/Share-Spielraum; eine später eigenständige Allokationsstrategie außerhalb High-SOC bleibt eine offen zu prüfende Architekturfrage.
- `ZEC_STRATEGIEARCHITEKTUR_ENTSCHEIDUNGSSTAND_20261018.md` hält diese abgestimmten Richtungsentscheidungen ohne Produktionsfreigabe fest. `ZEC_S3_FACHLICHE_PRODUKTIONSSPEZIFIKATION_ENTWURF_20261018.md` ist ein **nicht freigegebener** eigenständiger S3-Entwurf. `ZEC_A1_WIRKSAMKEIT_23T_DECISION_BRIEF_20261017.md` ist retrospektive Evidenz, keine Codeautorität.
- Keine neue Softwareversion oder reale Feldfreigabe durch diese Projektquellenänderung. Beide vorhandenen Next-Release-Fixpflichten bleiben unverändert.

## 2a.1 Nachtrag 19.10.2026: neuer freigegebener Entwicklungsumfang, noch keine Runtime

- S3-Fachvertrag wurde am 19.10.2026 zur Sourceentwicklung abgeschlossen: `ZEC_S3_PRODUKTIONSSPEZIFIKATION_V17_0_2_FINAL_20261019.md`. Er ist Sollvertrag, nicht Feld- oder Release-PASS.
- Verbindliche Next-Release-Subscopes `ZEC-BL-UI-STATUS-LIVE-001` (quellenbasierte 1-Hz-Statusanzeige) und `ZEC-BL-DIAG-GRID-STALE-001` (persistenter Grid-/Processing-Stale-Incident) im Master-Ledger `05`. Das vorhandene 3-s-Reglerintervall wird nicht verändert; keine Frische vorgaukeln.
- Lokaler, isolierter Entwicklungscheckpoint besitzt noch keinen TECHNICAL_BUILD_PASS, kein finales Versionslabel und keine reale Feldfreigabe. Die beiden Pflichtdefekte bleiben weiterhin offen bis zu eigenen getesteten Fixes.

## 2b. Releaseintegrierte Architektur- und Historien-Dokumentation (Entscheid 19.10.2026)

- Ab dem nächsten Entwicklungs-/Produktrelease ist eine strukturierte und versionsgenau geprüfte technische Dokumentation im Release-Sourcebaum `docs/` zu pflegen. Verbindlicher Vertrag: `01_ZEC_PROJECT_RULES.md`, § 6b, und `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md`, § 13; Fortschritt: `ZEC-BL-DOC-ARCH-001` im Master-Ledger `05`.
- Aktuelle, releasegebundene **As-built-Architektur** ist von historischen Original-Spezifikationen, damaligen Entwurfsständen, retrospektiv erstellten Entscheidungsprotokollen und getrennten Feldnachweisen klar zu unterscheiden. Release-/Source-Mapping und Status sind Pflicht; ältere Dokumente sind Provenienz, nicht automatisch gültige Implementation.
- Vorhandene historische Kernunterlagen sollen ohne unverhältnismäßige Rekonstruktion **im Original** erhalten und indiziert werden (prioritär Fast Capture V16.0.2). Die für V16.2.5 berichtete Revalidierungsfassung liegt im aktuell verifizierten Quellbestand **nicht vor**; sie darf nicht als gegenwärtig zugängliche Originalquelle behauptet werden. Die spätere Umsetzung ist anhand realer V17.0.2-Sources nachgewiesen.
- Dies ist eine Dokumentations-/Prozessentscheidung, **keine Änderung von V17.0.2**, keine implizite S3- oder weitere Sourcefreigabe. `05` bleibt die einzige Backlog-/Roadmapautorität; dessen Kopie unter `docs/` ist nur ein versionsbezogener Release-Snapshot.

## 2c. Bindendes Checkpoint-Verfahren ab 19.10.2026

- **Verbindlich für alle ZEC-Entwicklungs- und Chatwechselblöcke:** `01_ZEC_PROJECT_RULES.md` § 3 und `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md` § 11. Vollständige ZIP-Checkpoints gelten erst nach Upload in die **persönliche ChatGPT-Bibliothek** (`ZEC - Zendure Energy Controller/Checkpoints/`) und unabhängigem SHA256-/Bytezahl-/ZIP-Rücklese-PASS als `EXTERNALLY_SECURED`. Sandbox-Link allein ist **kein** externes Backup. Bei fehlender externer Sicherung stoppt weitere umfangreiche Sourcearbeit.
- Das Library-Verfahren wurde am 19.10.2026 mit Checkpoint 03 (`ZEC_S3_LIVE_STATUS_DEV_CHECKPOINT_03_20261019.zip`, SHA256 `24b31fd0867ef770c6bbef43a5c942b31477d874fff8e3f5e0964daebb31c3fc`) einschließlich Readback/Bytevergleich positiv erprobt. Dies ist **kein** Wiederherstellungsnachweis für die behaupteten späteren Checkpoints 04–06 und **kein** technischer Release-PASS.
- Speicherbereinigung nur mit expliziter Nutzerfreigabe und geprüftem Folge-/Release-/Branch-/No-Drop-Anker. Der Bibliotheksordner ersetzt **nicht** die aktive Project-Quellenmitgliedschaft; kanonische Projektdateien müssen nach Änderungen ausdrücklich in den Project-Quellenbestand übernommen werden.

## 3. Quellenrangfolge bei Konflikten

1. aktuelle reale produktive Evidenz und aktuelle verifizierte Codebasis;
2. ausdrücklich freigegebene Spezifikation des laufenden Entwicklungsblocks;
3. `07_ZEC_CURRENT_RELEASE_AND_FIELD_STATUS.md`;
4. kanonische Dauerquellen `01` bis `06`;
5. normative Analyse- und Hardwareschonungs-Regelwerke;
6. Lernwerkzeug innerhalb seines dokumentierten Geltungsbereichs;
7. historische Releases, Übergaben und Chats.

Technischer Build-PASS ist nicht gleich reale Feldfreigabe. Eine erfolgreich installierte Releasebasis kann zugleich noch funktionsspezifische `EVIDENCE_PENDING`-Punkte besitzen.

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
| `ZEC_STRATEGIEARCHITEKTUR_ENTSCHEIDUNGSSTAND_20261018.md` | abgestimmte Strategierichtung; **keine** freigegebene Implementierungsspezifikation oder Roadmapautorität |
| `ZEC_S3_PRODUKTIONSSPEZIFIKATION_V17_0_2_FINAL_20261019.md` | geschlossener S3-Produktionsvertrag / Basis der aktuellen Entwicklung, noch keine Implementierungsfreigabe oder Feldfreigabe |
| `ZEC_S3_FACHLICHE_PRODUKTIONSSPEZIFIKATION_ENTWURF_20261018.md` | eigenständiger S3-Fachentwurf, **SPEC_DRAFT**, noch keine Sourcefreigabe |
| `ZEC_A1_WIRKSAMKEIT_23T_DECISION_BRIEF_20261017.md` | retrospektive A1-/Herbst-Evidenz; kein Produktiv-Spec |
| `ZEC_HERBSTANALYSE_23T_KONSOLIDIERT_20261017.md` | read-only 23-Tage-Herbst-Evidenz und methodische Grenzen |
| `ZEC_20261005_COMMAND_EPISODES_OFFLINE_20261017.md` | read-only Command-Feldevidenz, offene Ursachenfrage (kein Fix-Beleg) |
| `ZEC_ANALYSE_REGELWERK_V1.1.md` | normative Analysemethodik |
| `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md` | Hardware-/Batterieschonung |
| `README_INSTALLATION_V17_0_2.md` | aktuelle V17.0.2 Installation/Update-Anleitung |
| `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_0_2.md` | wiedergefundene **historische Original-Spezifikation** Fast Capture; Status im Original noch „nicht implementiert“; für V17.0.2 keine As-built-Implementierungsautorität |
| `zendure_controller_v17_0_2.zip` | aktuelle reale Release-/Runtime- und Implementierungsbasis; SHA256 `82bd2db52a71b4a4e56f8e8c39e30511494fb02f8735909667052b73bd82f311` |
| `zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx` | Lern-/Simulationsreferenz |

## 5. Historische Vorgänger

V17.0.0 ist ein real vor Produktivmutation abgewiesener und zurückgezogener Packaging-Fehlrelease. V17.0.1, V16.2.5 und ältere Releases bleiben Feld-/Releaseprovenienz, sind aber keine aktuelle Implementierungsautorität. Der Wechsel der aktiven Runtimebasis auf V17.0.2 löscht keine historische Release- oder Feldprovenienz.

## 6. Lernwerkzeug-Grenze

`zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx` bleibt Referenz, aber keine Default-Autorität. Maßgeblich sind reale Sources, `config.example.json` und `SettingsRegistry`.

## 7. Terminologie Fast Capture

- In Prosa, UI, Logs, Reports und Diagnoseausgaben wird **„Fast Capture“** verwendet.
- **„FastC“** ist nur bei echter Platzknappheit zulässig.
- **„Fast“ allein** wird nicht als Bezeichnung für die Funktion verwendet.
- Bestehende eindeutige technische Identifikatoren wie `HARVEST_FAST_CAPTURE_MODE` oder `fast_capture_overlay_w` bleiben aus Kompatibilitätsgründen unverändert.

## 8. No-Drop

Alle bisherigen **85** stabilen Ledger-IDs bleiben erhalten. Die reale V17.0.2-Reconciliation vom 25.09.2026 ergänzt genau zwei stabile IDs: `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001`. Damit enthält das Master-Ledger **87** eindeutige stabile IDs.

**No-Drop-Abgleich 18.10.2026:** alle 43 im gelieferten Ledgertext konkret ausgeschriebenen ZEC-BL-/ZEC-EV-IDs erhalten; 1 neue ID `ZEC-BL-BATTERY-SOH-001`. Die historische Angabe „87 IDs“ ist im aktuellen Ledgertext nicht einzeln inventarisierbar; daher keine unbewiesene Vollverifikation 87/87. Keine Quelle entfernt.
