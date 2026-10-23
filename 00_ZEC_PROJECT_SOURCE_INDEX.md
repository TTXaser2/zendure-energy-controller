# ZEC – Projektquellen-Index

## Quellen-/Release-Nachtrag 22.10.2026 – V17.1.3 technischer Stand

- **Freigegebener Entwicklungsumfang:** nächster gebündelter UI-/Hilfetext-/UML-Korrekturrelease `V17.1.3 / v17.1.3-20261022` auf byteverifizierter veröffentlichter V17.1.2-Source. Der unveränderte Controllerkern besitzt SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7`.
- **Technische QA:** 171 Testdateien, 1.254 Tests + 1.126 Subtests regulär und identisch mit `ResourceWarning=error` PASS; UML 22/22 Source-/Visualreview und `DOC_UML_RELEASE_GATE=PASS`; Datenblatt, Architektur/History, Deployment-Harness 11/11 und responsive Synthetik-UI PASS. Das finale veröffentlichte ZIP und sein unabhängiger Bibliotheks-Readback müssen zusätzlich vor `TECHNICAL_BUILD_PASS` geprüft werden. **Der produktive Raspberry Pi bleibt auf V17.1.2**, bis ein neues reales Update erfolgt.
- **Projektquellen:** Diese `00`–`07` sind der aktuelle Release-Begleitsatz; alle vorherigen Ledger-IDs bleiben in `05`, historisch datierte Aussagen weiter unten sind Provenienz. `07` bleibt die aktuelle Realfeld-Autorität; kein Produktiv-PASS aus Buildprüfungen.


**Stand:** 21.10.2026 – aktueller V17.1.2-Feld-/UX- und Freeze-Nachtrag  
**Status:** kanonisch – Einstiegspunkt für alle neuen ZEC-Chats und Entwicklungsblöcke

## Neueste Quellen-/Entwicklungsautorität – 21.10.2026 (nach Realinstallation)

**UML_RELEASESTANDARD_APPROVED_20261022 – fachliche Dauerentscheidung:** Für den nächsten neu gebauten gemeinsamen Produktrelease ist ein versionierter UML-Regleratlas als Bestandteil der bestehenden `docs/architecture/`-Dokumentation verbindlich. Freigabe dieses Dokumentationsstandards ≠ Freigabe des noch offenen Gesamt-Releases. Alleinige Ledger-Autorität `05` unter `ZEC-BL-DOC-ARCH-001`; technische Definition in `01` §6b und `06` §13. Reales V17.1.2-Release bleibt byteidentisch; die UML-Vorintegration ist ein separat checkpointgesicherter, derzeit noch nicht fachlich freigegebener Dokumentationszweig. Das Atlasoriginal V0.4 hat SHA256 `1b1229b8958bafbd69cd676a1986e77605dd09673847b6872ef54481a4a8a4c5` und ist als Original in der persönlichen Bibliothek gesichert. Keine zusätzliche Project-Quellendatei für jedes UML-Blatt anlegen.

- **Aktuell real installiert und allgemein feldgeprüft:** **V17.1.2**, Build `v17.1.2-20261021` auf dem produktiven Raspberry Pi. Nutzerseitiger `tools/v17_field_acceptance.py --expect-primary-profile modbus_template`-Lauf am 21.10.2026: alle ausgegebenen Prüfungen `PASS`, insbesondere `FULL_READY`, `READY:FULL_READY`, `RELEASE_BACKUP_EXACT`, Settings-/Graph-/Fast-Capture-Surfaces sowie vorhandene Performance-Requestbudgets. Der komplette JSON-Rohbeleg liegt bislang nur auf dem Pi; kein eigenständiger Real-Clean-Fresh-Install-PASS. Einzelne natürliche S3-/Fast-Capture-/Night-/Grid-Stale-Episoden bleiben nach Evidenzlage separat offen. **`07` ist die aktuelle Feldautorität; ältere V17.1.0/V17.1.1-Zeitstände darunter sind historische Provenienz, auch wenn dort „aktuell“ steht.**
- **Unveränderte kanonische Codebasis:** veröffentlichtes, byteverifiziertes `zendure_controller_v17_1_2.zip`, SHA256 `d8128796c897ee1fcd610ab530760c492422d4c23d6a73e3a3da5ce3630ab02e`, in persönlicher Bibliothek `Releases/`. `controller_logic.py` SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7`.
- **Entwicklungsprovenienz ohne Freigabe:** V17.1.3-Kandidat `ZEC_V17_1_3_DEV_CHECKPOINT_02_COMPACT_LAYOUT_20261021.zip`, SHA256 `9a7ff51fe1c237c05555bf17e8ef589646ee8db242add8cbba90bea7ba77695a`, 14.835.446 Bytes, vollständig in Bibliothek `Checkpoints/` rücklesegeprüft; `FROZEN / NO_SOURCE_AUTHORIZATION / DEVELOPMENT_NOT_INSTALLABLE`. Fünf externe Hilfsskripte zusätzlich gesichert (`ZEC_V17_1_3_AUX_SCRIPTS_FREEZE_20261021.zip`), Freeze-/Wiederaufnahmeprotokoll ebenfalls in der Bibliothek. **CP02 ist keine freigegebene neue Produktbasis.** Vor neuer Sourceentwicklung ist ein fachlich abgestimmter Release-Gesamtscope und ausdrückliche Freigabe erforderlich; dabei erst entscheiden, ob der CP02-Kandidat selektiv integriert oder von V17.1.2 neu begonnen wird.
- **Aktuelle UX-Qualitätslücke:** V17.1.2-Hilfen technisch vollständig, aber in Nutzerlektüre sprachlich/fachlich teilweise weiter unverständlich; außerdem wächst die Netzkarte mit der langen Diagrammerklärung unnötig und verschiebt Statusbereiche vertikal. Maßgeblich: `04` (verbindlicher UX-Vertrag) und `05` (alleiniger Master-Ledger; `ZEC-BL-UI-SETTINGS-HELP-001`, `ZEC-BL-UI-STATUS-COMPACT-001`). Kein eigenständiger Sofort-Hotfix zugesagt; möglichst mit weiteren abgestimmten Arbeiten bündeln, um unnötige Pi-Installation/Feldabnahme/GitHub-Aktualisierung zu vermeiden.
- **Quellen-Mitgliedschaft:** Aktuelle Projektdateien `00`–`07` werden mit diesem Paket als **Ersatzdateien** geliefert, nicht als zusätzliche Quellen. Andere aktive Projektquellen, veröffentlichte ZIPs und historische Nachweise nicht löschen. Die persönliche Bibliothek allein aktualisiert keine Project-Quellenmitgliedschaft. Nach manueller Ersetzung tatsächliche Übernahme gesondert prüfen. Alte Dateiinventare/Zielzahlen weiter unten dokumentieren ihren historischen Erstellungszeitpunkt.
- **Freigabedisziplin:** Der unautorisierte CP01/CP02-Sourcebeginn war ein nachgewiesener Verstoß gegen bestehendes `01` §2; siehe `05` Ereignis `ZEC-EV-PROC-SCOPE-001`. Keine neue Freigabe- oder Gate-Bürokratie beschlossen: bestehende Scopeautorisation ist bindend; im Zweifel Analyse ohne Sourceänderung. 


## Aktueller Quellenindex-Nachtrag 21.10.2026 – V17.1.2

**Rangfolge aktuell:** (1) tatsächlich verifizierte veröffentlichte V17.1.2-Sources für Produkt-Code und technische UI-/Installervertragsdetails, (2) echte Feldrealität V17.1.1 für aktuell installierten Raspberry Pi, (3) kanonische Regeln `01`–`07`, insbesondere Master-Ledger `05`, (4) diese Release- und Handoverbelege; ältere V17.1.0-/V17.0.2-Notizen sind historische Provenienz. Es gibt noch keine V17.1.2-Feldfreigabe.

- Aktuell technisch veröffentlichtes Paket: `zendure_controller_v17_1_2.zip` SHA256 `d8128796c897ee1fcd610ab530760c492422d4c23d6a73e3a3da5ce3630ab02e`, `TECHNICAL_BUILD_PASS`, unabhängig aus persönlicher Bibliothek `Releases/` CRC-/Hash-/Manifest-verifiziert. Verifizierter Source-Freeze CP10 SHA256 `2ec0b7c9a0810e6c1b7120e7d455c2b65ad54fa672476634485a51f537076d45` unter `Checkpoints/`.
- Reale Pi-Runtime: **V17.1.1**, allgemeine reale Feldabnahme 21.10.2026 `FULL_READY=PASS`; kein V17.1.2-Update am Pi, kein CLEAN FRESH REAL PASS. `controller_logic.py` in beiden Releases SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7`.
- V17.1.2 UI/Hilfe/Installer Scope: 190 operative Settings-Hilfen und 74 Bereichstexte überprüft, 60-Minuten-Minigraph mit wahrer Minutensemantik und erhaltener Rohdaten-Evidenz, Netzquellen-/Freshness-Anzeige responsiv, 185 historische Root-Originale unter `docs/history/release_root`, drei Releaseübersichten und aktuelles As-built/Datenblatt. `05` führt die alten plus neue stabilen IDs; `BACKLOG_NO_DROP_GATE=PASS` für die 185 Originalverschiebungen im verifizierten Release.
- Begleitunterlagen: `README_INSTALLATION_V17_1_2.md`, `ZEC_V17_1_2_RELEASE_SHA256.txt`, `ZEC_V17_1_2_TECHNICAL_RELEASE_REPORT_20261021.md`; das Paket selbst enthält `docs/releases/v17.1.2/` und `docs/ZEC_Master_Backlog.md` als historischen Snapshot des Releasezeitpunkts. Der separat aktualisierte kanonische `05` bleibt die alleinige lebende Ledgerautorität.


## 1. Zweck

Diese Datei definiert den aktiven Projektquellenbestand für „ZEC – Zendure Energy Controller“. Historische Chats, alte Release-ZIPs, Zwischen-Checkpoints und alte Übergaben sind keine aktive Quellbasis. Aktuelle reale Sources und reale Evidenz haben gemäß Quellenrangfolge Vorrang.

## 2. Aktuelle kanonische Entwicklungs- und Feldbasis

**Aktuell seit 20.10.2026:** `V17.1.0 / 17.1.0 / v17.1.0-20261019` ist reale installierte Pi-Runtime, nicht nur Entwicklung. Produktive Installation per `SUPPORTED_UPDATE` von V17.0.2 und allgemeine Feldabnahme mit `FULL_READY` **PASS**. Der technische Paketstatus ist `TECHNICAL_BUILD_PASS`; der projektweite `PRODUCTIVE_PASS` bleibt insbesondere wegen `ZEC-EV-DEP-001` und funktionsspezifischer noch offener Evidenz eingeschränkt.

- **Kanonisches unverändertes Produktpaket:** `zendure_controller_v17_1_0.zip`, **14.561.945 Bytes**, SHA256 `11dddaaaa7831e2339a19b9b7f46412ee72f35917935b7292a005a47bfe61669`, Paket-/Fresh-extract-Integrität und externes Bibliotheks-Readback **PASS**.
- **Quelle:** exakt ausgelieferter Release-Sourcebaum bzw. `ZEC_V17_1_0_DEV_CHECKPOINT_15_20261019.zip` (SHA256 `68418e4436efaad7ddeae3b72310211ce78498cd8916c1dd4c6390abf9b281b2`), nicht der abgelehnte preliminary Installer-Kandidat.
- **QA:** regulär und `ResourceWarning=error` je **1.220 Tests + 718 Subtests PASS**, plus separate Fresh-extract-/Deployment-/Datenblatt-/Architekturgates; Details im technischen V17.1.0-Bericht.
- **Feld:** Installation, Releaseidentität, Persistenz-/Rollbackcheck und automatische Feldabnahme PASS; reale 1-Hz-Live-Daten für Grid und Primärspeicher im `HOLD` belegt; S3-Konfiguration / Legacy-Opt-in-Nichtanwendbarkeit beobachtet; kein Grid-Stale-Event im vollständig abgefragten 2-Tagesfenster (155 Ereignisse), reale Trigger-/Resolve-Wirkung **NOT_EVALUABLE**. Nur 1 Mode-Transition seit Upgrade; Logfolge 10:03:12–10:03:22 spricht für Wiederanlauf, Grund des Starts ungeklärt.
- **UI-Sourcebefund 20.10.2026:** große Netzleistungszahl wird über `/status-live-data` alle **1 s**, Minigraph separat über `/grid-mini-data` alle **10 s** aktualisiert; seine letzten 48 Punkte stammen aus der Controller-`graph_history`, nicht aus dem 1-Hz-Livestream. Realer Nutzerbefund: vermeintlich träger Verlauf ohne sichtbaren Poll-/Samples-Hinweis, Ledger-Follow-up `ZEC-BL-UI-GRID-MINICHART-001`.
- **V17.1.0 Umsetzung:** S3 opt-in; unabhängiges Live-Status-Read-only-Modell; persistenter Grid-Stale-Incident-Vertrag; Pflichtfix NIGHT/MIN_SOC/GRID und robuster SMA-Speedwire-/OBIS-Parser. Umsetzung/QA ist von fehlender natürlicher Fehler- oder Strategie-Episode zu trennen.
- **Projektquellen-Status / 25er-Limit (Quellenabgleich 20.10.):** Die acht kanonischen Dateien `00`–`07`, das reale V17.1.0-Release und elf weitere Einzelquellen sind im Projekt bereits vorhanden (20/25). Die Übernahme der hier vorgeschlagenen zwei zusätzlichen Dateien und der aktualisierten Fassungen von `00`/`05` durch den Nutzer bleibt bis zur anschließenden Projektquellenprüfung `PENDING`. Das veröffentlichte Release-ZIP wird nicht verändert.

### Historische V17.0.2-Basis (25.09.2026; abgelöst durch V17.1.0)

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

## 2a.1 Historischer Nachtrag 19.10.2026: damaliger Entwicklungsumfang, vor V17.1.0-Feldinstallation

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

## 4. Projektquellen-Mitgliedschaft mit 25-Dateien-Grenze (Stand 20.10.2026)

Die Dateimitgliedschaft ist **keine** Liste aller in der Historie erwähnten Dateinamen. Die folgende Tabelle beschreibt den **Zielbestand NACH manueller Einspielung** dieses Vier-Dateien-Updates: **22 / 25** getrennte Projektdateien. Beim hier zugrunde liegenden Live-Inventar am 20.10. waren **20 / 25** tatsächlich vorhanden. Solange die neuen Dateien nicht vom Nutzer aktiv als Projektquellen angehängt sind, gilt weiterhin der Istbestand von 20. Die persönliche ChatGPT-Bibliothek ist ein eigenes Archiv und ersetzt die Quellenmitgliedschaft nicht.

### 4.1 Zielbestand – direkt als Projektquellen angehängt

| Datei | Rolle |
|---|---|
| `00_ZEC_PROJECT_SOURCE_INDEX.md` | Kanonischer Einstieg, Quellenhierarchie und 25-Dateien-Architektur |
| `01_ZEC_PROJECT_RULES.md` | Verbindliche Entwicklungs- und No-Drop-Regeln |
| `02_ZEC_CURRENT_STATE_AND_ARCHITECTURE.md` | Aktuelle As-built-Architektur / Sourcegrenzen |
| `03_ZEC_CONTROL_AND_SAFETY_INVARIANTS.md` | Regler-, Command- und Safety-Invarianten |
| `04_ZEC_UI_SETTINGS_AND_DIAGNOSTICS_CONTRACT.md` | UI-/Settings-/Diagnosevertrag |
| `05_ZEC_BACKLOG_AND_ROADMAP.md` | Alleinige kanonische Master-Ledger-/Roadmap-Autorität |
| `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md` | Release-/Handover-/Checkpoint- und No-Drop-Verfahren |
| `07_ZEC_CURRENT_RELEASE_AND_FIELD_STATUS.md` | Aktuelle reale Release-/Feldstatus-Autorität |
| `ZEC_ANALYSE_REGELWERK_V1.1.md` | Normatives Analyseregelwerk |
| `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md` | Normatives Hardwareschonungs-Regelwerk |
| `ZEC_STRATEGIEARCHITEKTUR_ENTSCHEIDUNGSSTAND_20261018.md` | Fachentscheid 18.10.; kein aktueller produktiver Codevertrag |
| `ZEC_S3_FACHLICHE_PRODUKTIONSSPEZIFIKATION_ENTWURF_20261018.md` | Historischer S3-Entwurf / SPEC_DRAFT, nicht final |
| `ZEC_A1_WIRKSAMKEIT_23T_DECISION_BRIEF_20261017.md` | A1-Herbst-Wirksamkeitsnachweis, Planungsprovenienz |
| `ZEC_HERBSTANALYSE_23T_KONSOLIDIERT_20261017.md` | Historische 23-Tage-Herbstanalyse |
| `ZEC_20261005_COMMAND_EPISODES_OFFLINE_20261017.md` | Command-Episodenanalyse, Ursache noch nicht abschließend belegt |
| `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_0_2.md` | Historische Fast-Capture-Originalspezifikation, nicht V17.1.0-As-built |
| `README_INSTALLATION_V17_1_0.md` | Aktuelle V17.1.0-Installationsanleitung |
| `README_INSTALLATION_V17_0_2.md` | Historische vorherige Installationsanleitung |
| `zendure_controller_v17_1_0.zip` | Finale aktive Produkt-Source / Build v17.1.0-20261019, unverändert |
| `zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx` | Lern-/Simulationsreferenz innerhalb ihrer Grenzen |
| `ZEC_S3_PRODUKTIONSSPEZIFIKATION_V17_0_2_FINAL_20261019.md` | FREIGEGEBENE finale S3-Produktionsspezifikation vom 19.10.; Quelle bei V17.0.2, als Implementierungsvertrag für V17.1.0 |
| `ZEC_V17_1_0_RELEASE_UND_FELDEVIDENZ_KONSOLIDIERT_20261020.md` | Fünf vollständige und SHA256-inventarisierte V17.1.0-Release-/Feldberichte in einer lesbaren Datei |

### 4.2 Referenzierte, aber NICHT einzeln benötigte Archivoriginale

Die folgenden Dateien sind **keine zusätzlich zwingenden aktiven Projektdateien**. Sie sind vollständig als unveränderte Originaltexte im Sammeldokument aus § 4.1 eingebettet (mit originalen Bytezahlen/SHA256) und bleiben zusätzlich als einzelne Originaldateien in der persönlichen Bibliothek `ZEC - Zendure Energy Controller/Releases/` archiviert:

- `ZEC_V17_1_0_TECHNICAL_RELEASE_REPORT_20261020.md` — 6592 Bytes, SHA256 `91e600b85ce3fe0c8dc25f22ed7828685b36f3d8589ced96c90f09784ffe7195`.
- `ZEC_V17_1_0_LIVE_STATUS_HOLD_FIELD_EVIDENCE_20261020.md` — 2553 Bytes, SHA256 `5ccf7abfffb0c221c2b77a7bd421a7ddf17e63256b89190e9289c9a1822f29f0`.
- `ZEC_V17_1_0_S3_GRID_READONLY_FIELD_EVIDENCE_20261020.md` — 2910 Bytes, SHA256 `cde9c5d36c3fcf2f4bf58df75aee828f267e919b6f81e4211604bbc8983e9210`.
- `ZEC_V17_1_0_EVENT_INVENTORY_2D_20261020.md` — 2337 Bytes, SHA256 `3e422555d933cab5e4d2436128daca5b74f05965c7d4accb31d78ebb2d043706`.
- `ZEC_V17_1_0_MODE_TRANSITIONS_FIELD_EVIDENCE_20261020.md` — 2216 Bytes, SHA256 `3e2e9f6efb81781cd86d728363de1d5eb0e4ddfaa00754376b8fe9d8f01a39d8`.

Weitere getrennt abrufbare Archivreferenzen, **nicht als aktuelle Laufzeitautorität oder Projekt-Uploadpflicht**:

- `ZEC_V17_1_0_DEV_CHECKPOINT_15_20261019.zip` — vollständige Entwicklungsprovenienz; SHA256 `68418e4436efaad7ddeae3b72310211ce78498cd8916c1dd4c6390abf9b281b2`, in der persönlichen Bibliothek unter `ZEC - Zendure Energy Controller/Checkpoints/` rücklesegeprüft.
- `zendure_controller_v17_0_2.zip` — historische Vorgängerrelease-Identität; SHA256 `82bd2db52a71b4a4e56f8e8c39e30511494fb02f8735909667052b73bd82f311`, nicht notwendiger aktueller Projekt-Upload. Verfügbarkeit eines bestimmten Archivobjekts bei Bedarf gesondert nachweisen; niemals einen nicht überprüften Bibliotheksstand behaupten.
- Versionierte Code-/Architektur-/History-Unterlagen des aktuellen Releases befinden sich unter `docs/` im exakt hashverifizierten aktuellen `zendure_controller_v17_1_0.zip` (insbesondere `docs/INDEX.md` und `docs/architecture/`). Sie gelten nur im Umfang der tatsächlich ausgelieferten Source; keine zweite Backlogautorität aus einem Release-Snapshot ableiten.
- Andere historische Originale bleiben in den bestehenden Projektdateien und/oder eindeutig referenzierten Bibliotheksarchiven; Archivierung bedeutet weder Löschung noch `CLOSED` ohne Ledgerbeleg.

### 4.3 Pflege-/Zugriffsvertrag

1. **Zu Beginn jeder Planung/Entwicklung** zuerst `00`, danach die relevanten jeweils aktuellen kanonischen Projektquellen `01`–`07` und gegebenenfalls normative zusätzliche aktive Quellen lesen. Die aktuelle verifizierte reale Release-Source hat entsprechend § 3 Vorrang.
2. Für **Sourceentwicklung** das konkrete `zendure_controller_v17_1_0.zip` mit SHA256 aus § 2 materialisieren/verifizieren bzw. den letzten vollständig bibliotheksgesicherten neueren freigegebenen Sourcecheckpoint. ZIP-Archivdaten nicht als automatisch gelesenen Klartext voraussetzen.
3. Für **V17.1.0 Realfeld-Einzelbefunde** die konsolidierte Originaltextquelle aus § 4.1 und `07` verwenden. Neue Realbefunde im Ledger `05` und im aktuellen Release-/Feldstatus `07` fortschreiben, größere Einzelevidenz wieder originalgetreu im Bibliotheksarchiv sichern. Versionsgebundene As-built-Dokumentation verbleibt im Releasepaket.
4. **Vor Project-Quellenbereinigung** `BACKLOG_NO_DROP_GATE` nach `01` § 6a und `06` § 7.2 je entfernter historischer Quelle durchführen. Historische Ledger-/Prozessinformationen werden durch bloße Platznot nie gelöscht. Für die vier Dateien dieses Updates werden ausschließlich `00`/`05` ersetzt und zwei Dateien ergänzt, **keine** sonstige vorhandene Projektdatei entfernt.
5. Obergrenze: 25 Projektdateien; Ziel nach Einspielung 22 (drei freie Plätze für neue Facharbeit). Jede spätere Ersatz-/Konsolidierungsoperation muss den Zielbestand und die tatsächlich aktive Mitgliedschaft erneut zählen. Dateien in der Bibliothek belegen keinen Projektdateislot; sie sind nur über explizite Bibliotheksoperationen abrufbar.

## 5. Historische Vorgänger

V17.0.2 ist seit dem 20.10.2026 historische Update- und Rollbackbasis; die im Abschnitt 2 enthaltenen alten Statusangaben sind ausdrücklich historische Evidenz. V17.0.0 ist ein real vor Produktivmutation abgewiesener und zurückgezogener Packaging-Fehlrelease. V17.0.1, V16.2.5 und ältere Releases bleiben Feld-/Releaseprovenienz, sind aber keine aktuelle Implementierungsautorität. Der Wechsel der aktiven Runtimebasis auf V17.1.0 löscht keine historische Release- oder Feldprovenienz.

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

**Abgleich 20.10.2026:** Das aktuell direkt auffindbare Master-Ledger `05` enthält 49 konkret identifizierbare stabile `ZEC-BL-`/`ZEC-EV-`-IDs. Frühere Aussagen über 85/87 ursprünglich rekonstruierte IDs sind historische Zählstandsbehauptungen, nicht als hier vollständig nachgezählte Vollinventur zu interpretieren. Eine nicht belegte Rückwärtsverifikation wird nicht behauptet. Diese Quellenkonsolidierung entfernt keine einzige ID aus `05`.

## 9. Versionssynchronisation 20.10.2026

`07` ist die aktuelle Release-/Feldautorität; `05` ist alleinige Roadmap-/Backlogautorität. Die 18./19.10.-Planungstexte bleiben als historische Entscheidungslinie erhalten und werden nicht als unverändert aktueller Live-Stand gelesen. Offene Feldevidenz ist bewusst nicht künstlich geschlossen.
