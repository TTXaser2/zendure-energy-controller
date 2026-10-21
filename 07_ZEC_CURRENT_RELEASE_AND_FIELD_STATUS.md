# ZEC – Current Release & Field Status

**Stand:** 25.09.2026, V17.0.2 real installiert / allgemeine Feldabnahme PASS-FULL_READY; Fast-Capture-Feldevidenz teilweise PASS, Gesamtabschluss EVIDENCE_PENDING  
**Status:** aktuelle versionsspezifische Autorität für Release- und Feldstatus

## A. Aktueller Stand V17.0.2

- **Reale Runtimebasis:** `V17.0.2 / 17.0.2 / v17.0.2-20260923`. Reales Update V17.0.1 -> V17.0.2 am 23.09.2026 erfolgreich; Installer-Preflight/Backup/Copy/Postchecks PASS; Controller anschließend vollständig `ready=true`.
- **Allgemeine Feldabnahme:** `tools/v17_field_acceptance.py` real PASS / FULL_READY. Persistente Feldartefakte liegen auf dem Pi vor. Dies ist von der funktionsspezifischen Fast-Capture-Abnahme zu trennen.
- **Paket:** `zendure_controller_v17_0_2.zip`, SHA256 `82bd2db52a71b4a4e56f8e8c39e30511494fb02f8735909667052b73bd82f311`, Größe `14.402.481 Byte`. Vollständige Regression **157 Testdateien / 1169 Tests + 706 Subtests PASS**; identischer ResourceWarning-Lauf; Bash 13/13, Browser-JavaScript 3/3, Compileall, Deployment-Harness 11/11, Datenblatt, Build-Evidence, Manifest-/Hygiene-/Fresh-extract-Gates PASS.
- **Reglerkern:** `controller_logic.py` SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031`.
- **Fast Capture Shadow:** neue V17.0.2-V4-Evidenz ist verwertbar; ein natürlicher Lauf mit zwei Episoden `PASS / SHADOW_ONLY`, ein weiterer ohne Episode korrekt `NOT_EVALUABLE`; definierter Shadow-Gate **PASS**.
- **Fast Capture Active:** begrenzter Active-Rollout ausdrücklich freigegeben. Erster beaufsichtigter/unbeaufsichtigter Lauf ohne natürliche Episode korrekt `NOT_EVALUABLE`; ein externer Watchdog-Readiness-Abbruch wurde nachträglich als False Positive auf zulässiges `TRANSITIONAL:LIMIT_READBACK_CONVERGENCE` klassifiziert und stellte `shadow` korrekt wieder her. Spätere reale Active-Daten zeigen `NEAR_LIMIT`-Wirkung: 23.794 Active-Mode-Zeilen, 501 positive Overlay-Zeilen, 20 erkannte Episoden, max. Fast-Capture-Overlay 1.642 W; für die auswertbaren `NEAR_LIMIT`-Episoden liegen reale Exportreduktion, Command-Tracking, Import-Guard/Recovery und Cross-Charge-Evidenz ohne bestätigten Command-Mismatch vor. **Active-`FULL_IDLE` fehlt weiterhin**, daher bleibt der Fast-Capture-Gesamtabschluss `EVIDENCE_PENDING`. Letzter real beobachteter Nutzungsstand: Fast Capture `active`.
- **Fast-Capture-Evidence-Tooling:** Analyzer-Hotfix2 besitzt einen applicability-bezogenen Calculation-False-Positive (`PRIMARY_RESERVE_MISMATCH` in blockierten/nicht anwendbaren Zyklen). Außerdem ist Vollhistorienmaterialisierung im Analyzer für lange Real-Pi-Zeitfenster ressourcenunsicher. Vor Fast-Capture-Gesamtabschluss sind applicability-aware Calculation-Prüfung und bounded-memory-/bounded-extract-Langzeitvertrag zu härten.
- **Next-Release-Blocker:** `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` müssen spätestens im nächsten Produktrelease implementiert und regressionsgeprüft werden.
- **Projektweiter PRODUCTIVE-PASS:** weiterhin zusätzlich durch deferred `ZEC-EV-DEP-001` begrenzt.

## 0. Historischer V17.0.0-Entwicklungsblock (Provenienz)

Am 22.09.2026 wurde der revalidierte Fast-Capture-A400/R100-Makro-Scope ausdrücklich zur Sourceumsetzung freigegeben. `ZEC-BL-CTRL-FASTCAP-001` ist damit **IN_PROGRESS**. Die produktive/reale Runtimebasis bleibt bis zu einem vollständig gebauten und feldinstallierten Nachfolger unverändert V16.2.5. Checkpoint A (Controllerkern/State/Differential-/Safetytests) ist fokussiert PASS mit **110 Tests + 11 Subtests**. Checkpoint B (Settings/Validation, Measurement V4, releaseintegrierte Fast-Feldanalyse, V17-Feldabnahme und Analysis-Package-Integration) ist fokussiert PASS mit **114 Tests + 640 Subtests**. Der V17-Entwicklungsstand ist weiterhin **kein TECHNICAL BUILD PASS und keine Feldfreigabe**; Checkpoint C mit den zwei isolierten UI-Follow-ups ist fokussiert PASS mit **12 Tests**. Der nächste Block ist der Release-Freeze; vollständige Regression, ResourceWarning-, Syntax-, Manifest-, Datenblatt-, Build-Evidence- und Fresh-extract-Gates stehen noch aus.

## 1. Historische V16.2.5 Entwicklungs- und Feldbasis (Provenienz)

- aktuelle technische Releasebasis: `V16.2.5 / 16.2.5 / v16.2.5-20260922`
- Paket: `zendure_controller_v16_2_5.zip`
- Paketgröße: `14.270.492 Byte`
- SHA256: `ebb19bf9cb820781dd60c4c5b42d7048f94552768097cea12e7228b95b6f2f84`
- ZIP-Root: `zendure_controller_v16_2_5/`
- technischer Status V16.2.5: **TECHNICAL BUILD PASS**
- reales Update V16.2.4 → V16.2.5: **PASS**
- aktuelle reale Release-/Runtimebasis: `V16.2.5 / 16.2.5 / v16.2.5-20260922`
- automatischer V16.2.5-Feldstatus: **PASS**, `controller_ready=WARN LIMIT_READBACK_CONVERGENCE`, `controller_readiness_acceptance=PASS TRANSITIONAL:LIMIT_READBACK_CONVERGENCE`
- manuelle V16.2.5-Abnahme: **ACCEPTED_WITH_KNOWN_UI_FOLLOWUPS** – Statuskartenlayout PASS, Mobile Settings PASS, Instance Owner PASS, Graph-Linienunterbrechung PASS, aktive Warnung ein-/ausgeklappt PASS; offene nicht blockierende UI-Follow-ups: Gap-Cursor/Tooltip/Inspector sowie höhenneutrale Warning-Chip-Interaktion
- geschützter Reglerkern `controller_logic.py`: `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`
- vollständiger projektweiter `PRODUCTIVE-PASS`: weiterhin durch `ZEC-EV-DEP-001` begrenzt/deferred

V16.2.5 ist die aktuelle technische Installationsbasis und reale Runtimebasis. Das reale Update V16.2.4 → V16.2.5 sowie der automatische Feldlauf sind erfolgreich. Der Hotfix ändert keine Regler-, Command-, Safety- oder Recoverysemantik. Die manuelle Feldentscheidung akzeptiert V16.2.5 mit zwei dokumentierten, isolierten und nicht sequenzblockierenden Frontend-Follow-ups: Gap-Cursor/Tooltip/Inspector müssen bestätigte Datenlücken semantisch respektieren; aktive Speicherwarnungen sollen im kompakten Zustand höhenneutral als Header-Chip erscheinen und Details außerhalb des normalen Kartenflows öffnen. Für diese Punkte wird kein eigener Hotfix-Zyklus erzwungen; sie werden im nächsten ohnehin anstehenden Release separat regressionsgeprüft mitgeführt.

### 1.1 Technischer Buildnachweis V16.2.5

Das finale Installer-ZIP wurde aus dem extern gesicherten Final-Freeze neu gebaut und anschließend frisch extrahiert. Auf genau diesem finalen Paket wurden bestätigt:

- Source-Manifest: **895/895 PASS**;
- Release-Hygiene: **PASS**;
- `ZEC_BUILD_EVIDENCE_V1`: **PASS**, 152 Testdateien;
- vollständige pytest-Regression: **1132 Tests + 698 Subtests PASS**;
- identischer Fresh-extract-Lauf mit `error::ResourceWarning`: **1132 + 698 PASS**;
- Produkt-Bash-Syntax: **13/13 PASS**;
- Browser-JavaScript: **3/3 PASS**;
- Python Compileall: **PASS**;
- Deployment-Harness: **11/11 PASS**;
- Root-Artefakt-Transaktion/Rollback-Fixture: **PASS**;
- technisches Datenblatt-Gate: **PASS**; finale 10-Seiten-Renderprüfung bereits im Final-Freeze belegt;
- Datenblatt-DOCX SHA256: `6810e63e266f5544661adb48daa90ca8f63ce5fb11907ebeb88486f84992552c`;
- Datenblatt-PDF SHA256: `2ab6e5f9d795d70628749d04ed9bec70324a293651dd4f0162fcf0a083230954`;
- `controller_logic.py` byteidentisch mit `d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`;
- `BACKLOG_NO_DROP_GATE=PASS`, **85/85** Ledger-IDs erhalten;
- externer `paho-mqtt`-Importshim ausschließlich in der QA-Runtime außerhalb des Release-Trees.

TECHNICAL BUILD PASS ist nicht gleich Real-Field-Pass. Das reale Update, der automatische Feldlauf und die manuelle Abnahmeentscheidung liegen vor; V16.2.5 ist als reale Runtimebasis akzeptiert. Die zwei bekannten UI-Follow-ups bleiben offen und werden nicht als erledigt ausgegeben.

## 2. Reale V16.2.5-Installations- und Feldevidenz

Reales kombiniertes Update V16.2.4 → V16.2.5 am 22.09.2026:

- `INSTALL_MODE=SUPPORTED_UPDATE`;
- `PREFLIGHT_RESULT=PASS`;
- `SAFE_TO_INSTALL=yes`;
- Rollback-Backup: `/home/pi/Downloads/zendure-controller-backup-20260922_111223.tar.gz`;
- Rollback-Backup SHA256: `6ce61938df8e2edb2e7fd1e4f32478db758cadec2ad333681a8cc9686120ef6f`;
- Installationsreport: `/home/pi/Downloads/zec_v16_2_5_install_report_20260922_111223.json`;
- Installationsreport SHA256: `02b59bbc599049b9d4a51d6175879cd182db16b5813eb59497edbb0a1f1e9860`;
- V16.2.5 erfolgreich installiert.

Direkt nach dem Start war `/ready` transient wegen `command_readback` / `INPUT_LIMIT` noch nicht vollständig konvergiert. Der vorhandene Installer-/Readinessvertrag akzeptierte diesen Zustand korrekt als sicheren Übergangszustand.

Konsolidierter read-only Feldlauf:

- Evidence-Verzeichnis: `/home/pi/Downloads/ZEC_V16_2_5_FIELD_EVIDENCE_20260922_114523`;
- Feldartefakt SHA256: `14d5b978b96f67a44930876c2e6c48eb34905d94afc0ea7a12be80319a666dcc`;
- Evidence-Archiv SHA256: `b8b188f487f05eac5fcba8d94614ecb17731c88389708e84425113cf43cad239`;
- `controller_ready=WARN LIMIT_READBACK_CONVERGENCE`;
- `controller_readiness_acceptance=PASS TRANSITIONAL:LIMIT_READBACK_CONVERGENCE`;
- Releaseidentität, Datenblatt, Dienst, `/health`, Primärspeicherquelle/Capability, Graph-Runtime/Workspace/Overview/Inspector/Command-Follow/Episode-Comparison, Settings-Surface, SOC-Day, DB-Integrität, Installationsreport, Rollback-Integrität und Performance-Gates: PASS;
- `rollback_backup_integrity=RELEASE_BACKUP_EXACT`.

Instance-Owner real im Snapshot:

- `INSTANCE_OWNER_ACTIVE=True`;
- `INSTANCE_OWNER_PID=39159`;
- `INSTANCE_OWNER_BUILD_ID=v16.2.5-20260922`.

### 2.1 Manuelle V16.2.5-Sichtprüfung 22.09.2026

**Speicherstatuskarten:** Desktop und reales iPhone bestätigen keine Footer-/Content-Überdeckung. `Noch ladbar` ist in der rechten Detailspalte lesbar; Leistungsdarstellung und Kartenwachstum sind stabil. Eine reale aktive Ladeannahme-/High-SOC-Warnung wurde anschließend sowohl eingeklappt als auch ausgeklappt beobachtet. Warnexistenz bleibt sichtbar, Langtext ist lesbar und auf-/zuklappbar, regulärer Inhalt wird nicht überdeckt. Damit ist die funktionale V16.2.5-Warnungsevidenz PASS. Neues UX-Finding: Bereits die eingeklappte Warnungsbox erhöht die Speicherkarte und damit die gesamte obere Grid-Reihe deutlich. Freigegebener Follow-up: höhenneutraler Warning-Chip im Kartenkopf; Details Desktop als verankertes Popover, mobil als Bottom-Sheet/kompaktes Modal außerhalb des normalen Kartenflows.

**Mobile Settings:** reales iPhone im Expertenmodus mit Input, Einheit, langem technischem Key, Meta-Pills und absichtlich ungültigem Draftwert geprüft. Die Validierungsbox bleibt vollständig sichtbar und der Content wird nicht horizontal abgeschnitten. `ZEC-BL-UI-SETTINGS-MOBILE-001 = CLOSED / REAL_FIELD_PASS`.

**Instance Owner:** automatische Snapshot-Evidenz bestätigt den Fix real. `ZEC-BL-DIAG-OWNER-001 = CLOSED / REAL_FIELD_PASS`.

**Graph-Gap:** über der bekannten Controller-Downtime ist die numerische Linie sichtbar korrekt unterbrochen; der primäre Gap-Fix ist real PASS. Beim Hover/Klick innerhalb des Gaps zeigt das synchronisierte Cursor-/Tooltip-Overlay jedoch weiterhin den nächsten realen Messpunkt außerhalb der Lücke. Im rechten Inspector fehlen die Messwerte zwar korrekt, bei `actual_ms=null` erscheint aber `01.01.1970, 01:00:00`. Sourcegegenprüfung bestätigt: `syncPlugin`/`updateCursorCards()` arbeiten mit nearest sample ohne Evidence-Gap-Gate; `renderInspector()` macht aus `null` über `Number(null)` den Zeitwert 0. Dieser isolierte Interaktionsrest bleibt unter `ZEC-BL-GRAPH-GAP-001` offen.

**Release-/Sequencing-Entscheidung:** Die zwei offenen UI-Follow-ups – Graph-Interaktion im Gap und höhenneutrale Warnungsdarstellung – rechtfertigen nach Nutzerentscheidung keinen separaten Hotfix-Zyklus. Sie werden im nächsten ohnehin anstehenden Release als getrennte Frontend-Subscopes mit eigener Regression aufgenommen. V16.2.5 bleibt akzeptierte reale Runtimebasis. Die anschließende Fast-Capture-vs.-Adaptive-Gegenüberstellung ist abgeschlossen: Der Nutzer hat am 22.09.2026 Fast Capture A400/R100 als nächsten Controllerblock gewählt und die Entkopplung von Adaptive bestätigt. Die Fast-Spezifikation ist gegen V16.2.5 revalidiert; Controller-Sources sind noch unverändert.

## 3. Reale V16.2.4-Installations- und Feldevidenz

Kombinierter regulärer Installerlauf (Paketprüfung → interner vollständiger Preflight → bei PASS unmittelbar Installation) am 21./22.09.2026:

- Package-Identität, Datenblatt, Runtime-Smoke, Build-Evidence und Dependency-Preflight: PASS;
- `INSTALL_MODE=SUPPORTED_UPDATE`;
- `PREFLIGHT_RESULT=PASS`;
- `PRODUCTIVE_CHANGES=NONE` bis zum abgeschlossenen Preflight;
- `SAFE_TO_INSTALL=yes`;
- Installation erfolgreich; Controller anschließend `ready=true`;
- persistenter Installationsreport: `/home/pi/Downloads/zec_v16_2_4_install_report_20260921_232843.json`;
- Installationsreport SHA256: `778b0716fba2c79ff6f77f26e11b818fb08cee96b9e0630f7cbf8624280b5260`;
- Rollback-Backup: `/home/pi/Downloads/zendure-controller-backup-20260921_232843.tar.gz`;
- Rollback-Backup SHA256: `8e541acdc71fffb4e97bb9ec0428eab575eba526eeacf4d1f32c28b0fbf77150`.

Konsolidierter read-only Feldlauf:

- Artefakt: `/home/pi/Downloads/ZEC_V16_2_4_FIELD_EVIDENCE_20260922_012620/ZEC_V16_2_4_FIELD_ACCEPTANCE.json`;
- Feldartefakt SHA256: `5cccbad72472835b4268556c12dd2a93cc81182677b87ec4f03fd5e22111b317`;
- vollständiges Evidence-Archiv SHA256: `064f79f9675468d1db0e667757effa6a63eb3f3eb46f873fd78e5040561c24b0`;
- Ergebnis: **27/27 PASS**;
- `controller_ready=FULL_READY`;
- `controller_readiness_acceptance=READY:FULL_READY`;
- `primary_storage_settings_surface=PASS`;
- `install_report=PASS`;
- `rollback_backup_integrity=RELEASE_BACKUP_EXACT`;
- Performance-Requests innerhalb bestehender Budgets.

Die drei V16.2.4-Primärspeicher-Controls wurden live bestätigt: `SECOND_BATTERY_INTEGRATION_ENABLED`, `SECOND_BATTERY_CAPACITY_WH` und `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` jeweils `available=True`, `editable=True`, `applicable=True`, `surface_state=operational`.

## 4. Durch V16.2.4 real geschlossene Punkte

- `ZEC-BL-UI-SETTINGS-001`: **CLOSED / REAL_FIELD_PASS**. Settings-Surface-/Applicability-Vertrag real bestätigt; manueller Kapazitätsfallback wirkt bis zur kWh-Anzeige.
- `ZEC-BL-DEP-002`: **CLOSED / REAL_FIELD_PASS**. Persistenter Installationsreport wird real automatisch bevorzugt; reale Backup-Datei exakt per Pfad/Größe/SHA256 bestätigt.
- Technischer V16.2.4-Build bleibt unverändert PASS; `controller_logic.py` ist byteidentisch zum V16.2.3-Reglerkern.

## 5. Manuelle V16.2.4-UI-/Diagnosefindings – freigegebener V16.2.5-Scope

### 5.1 Speicherstatuskarten / `ZEC-BL-UI-STATUS-003`

- Mobile Typografie von `Noch ladbar/entladbar` und Leistungsbalken ist zu klein.
- Im aktuellen Desktoplayout kollidiert der untere Leistungsbereich mit dem Footer; starre Kartenhöhe und wachsender linker Detailblock sind strukturell ungeeignet.
- Ein aktiver `HIGH_SOC_CHARGE_LIMITED`-Hinweis kann die Karte großflächig überdecken und besitzt keinen kompakten/einklappbaren Darstellungsvertrag.
- V16.2.5 verschiebt `Noch ladbar/entladbar` in die rechte Detailspalte, schafft ausreichend lesbaren linken Leistungsbereich, verhindert Footer-/Content-Overlap und rendert aktive Warnungen kompakt mit aufklappbarem Langtext.

### 5.2 Mobile Settings / `ZEC-BL-UI-SETTINGS-MOBILE-001`

- Auf realem iPhone laufen Controls, Einheit und Validierungstext rechts aus dem Viewport; horizontaler Scroll ist absichtlich gesperrt und der Inhalt dadurch unerreichbar.
- V16.2.5 muss bei 320/375/390/430 CSS-Pixel ohne horizontalen Content-Overflow funktionieren; horizontales Scrollen/Pinch-Zoom sind kein Ersatz für Responsive Layout.

### 5.3 Instance-Owner-Diagnose / `ZEC-BL-DIAG-OWNER-001`

- Reale V16.2.4-Instanz läuft gesund, aber `/status-view-data`/UI melden `Owner nicht bestätigt`, `Prozess —`, `Build —`.
- Feldsnapshot: `instance_owner_active=False`, `instance_owner_pid=None`, leere Build-ID.
- Sourcebefund: Ownerdaten werden beim Instance-Lock gesetzt und im Readinesspfad exportiert, fehlen aber im allgemeinen Snapshotpfad. V16.2.5 korrigiert ausschließlich Snapshot-/Diagnosekonsistenz, nicht die Single-Owner-/Lock-Semantik.

### 5.4 Graph-Datenlücken / `ZEC-BL-GRAPH-GAP-001`

- Reale Controller-Downtime wird trotz korrektem Coverage-Gap als durchgängige numerische Linie dargestellt.
- `spanGaps=false` reicht ohne explizites Null-/Break-Segment nicht; zwei zeitlich getrennte gültige Punkte werden verbunden.
- V16.2.5 muss bestätigte Daten-/Evidence-Gaps sichtbar unterbrechen, ohne synthetische Messwerte zu erzeugen.

## 6. V16.2.5 Abgrenzung

- Bugfix-/Hotfixklasse `+0.0.1`;
- keine Reglerstrategieänderung;
- keine Command-/Safety-/Recoveryänderung;
- kein Fast Capture, kein Adaptive, kein usable-SOC Block B, keine Battery-Care-Implementierung;
- `controller_logic.py` muss byteidentisch bleiben;
- `ZEC-BL-UI-STATUS-EXPERT-001` bleibt nach dem Hotfix weiterhin `OPEN / partial`.

## 7. Weiter offene Grenzen nach V16.2.5 (historischer Stand; durch Abschnitt A/10 fortgeschrieben)

- `ZEC-BL-UI-STATUS-003`: **OPEN / REAL_FIELD_PASS_WITH_UI_FOLLOWUP**; Warnungsfunktion real bestätigt, höhenneutraler Header-Chip + Desktop-Popover/Mobile-Bottom-Sheet im nächsten ohnehin anstehenden Release; kein Sequencing-Blocker;
- `ZEC-BL-UI-SETTINGS-MOBILE-001`: **CLOSED / REAL_FIELD_PASS**;
- `ZEC-BL-DIAG-OWNER-001`: **CLOSED / REAL_FIELD_PASS**;
- `ZEC-BL-GRAPH-GAP-001`: **OPEN / REAL_FIELD_PASS_WITH_UI_FOLLOWUP**; Linienbreak real PASS, Cursor-/Tooltip-/Inspector-Gap-Semantik im nächsten ohnehin anstehenden Release; kein Sequencing-Blocker;
- `ZEC-BL-UI-STATUS-EXPERT-001`: **OPEN / partial**;
- `ZEC-BL-PRIMARY-METADATA-001`: **SPEC_NEEDED**;
- `ZEC-BL-CTRL-USABLE-SOC-001`: **DEFERRED / SPEC_NEEDED**;
- `ZEC-BL-CTRL-FASTCAP-001`: **IN_PROGRESS / implementation_state=partial / sequencing=ACTIVE / spec_state=REVALIDATED_V16_2_5**; Checkpoint A fokussiert PASS (110 Tests + 11 Subtests), Checkpoint B fokussiert PASS (114 Tests + 640 Subtests); releasegekoppelte Fast-Feldanalyse ist im Entwicklungsstand enthalten; vollständige Releasegates und reale Shadow-/Active-Evidenz stehen noch aus;
- `ZEC-BL-CTRL-ADAPTIVE-001`: **SPEC_NEEDED / OPEN**; kein weiterer verlorener Abschlussartefakt wird vorausgesetzt. Nach Bereitstellung des Fast-Capture-Releases beginnt ein eigener Spezifikationsblock für S3-Mapping, Optimierungsziel/Aktionsraum, Lernzustand/Persistenz/Reset, Confidence/Fallback, Capacity Weighting und Evidenzvertrag;
- `ZEC-EV-DEP-001`: reale Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Gesamtabnahme bleibt zurückgestellt.

Die Gegenüberstellung Fast Capture versus Adaptive ist abgeschlossen. **Fast Capture A400/R100 ist der ausdrücklich gewählte und aktuell in Umsetzung befindliche Controllerblock; Adaptive folgt entkoppelt als eigener Spezifikationsblock nach Bereitstellung des Fast-Capture-Releases.** Der V17.0.0-Makro-Scope ist freigegeben; Checkpoint A und B sind fokussiert PASS. Die beiden isolierten UI-Follow-ups unter `ZEC-BL-GRAPH-GAP-001` und `ZEC-BL-UI-STATUS-003` sind im Checkpoint C umgesetzt und fokussiert PASS (12 Tests); vollständige Releasegates stehen noch aus.


## 10. Historischer Snapshot: V17.0.2 Fast-Evidence-Hotfix – Technical Build 23.09.2026

V17.0.2 ist der isolierte Hotfix auf die real in V17.0.1 gefundenen Fast-Capture-Feldevidenzdefekte. Behoben sind der fehlende cycle-exakte Fast-Feldtransport in den Measurement-V4-Zulauf, die versionsübergreifend zu breite Config-Snapshot-Prüfung des Analyzers sowie der `--latest-only`-SIGPIPE/rc=141-Pfad des Analysis-Package-Wrappers. Der Human-Report weist strukturelle Manifest-/Versions-Evidenz nun explizit aus.

Technische Evidenz vor finalem Paketfreeze: fokussiert 51 Tests PASS; vollständige Regression 157 Testdateien / **1169 Tests + 706 Subtests PASS**; identischer ResourceWarning-Lauf; Bash 13/13, Browser-JavaScript 3/3, Compileall, Deployment-Harness 11/11, Datenblatt-Gate und Build-Evidence PASS. Aktuelles Datenblatt 10/10 Seiten visuell geprüft. Der Reglerkern ist byteidentisch zu V17.0.1.

Zum damaligen Stand 23.09.2026 war die reale Installation V17.0.1 -> V17.0.2 **PENDING**. Dieser historische Status ist durch Abschnitt A sowie die Abschnitte 12–15 überholt. Danach war ausschließlich neue V17.0.2-Shadow-Evidenz für Fast Capture verwertbar. Fehlen natürliche FULL_IDLE-/NEAR_LIMIT-Episoden, ist `NOT_EVALUABLE` korrekt; ein begrenzter Active-Rollout benötigt weiterhin eine ausdrückliche spätere Freigabe nach zufriedenstellender Shadow-Evidenz.


## 11. Historischer Snapshot: V17.0.2 Finales Installerpaket – 23.09.2026

Finales Paket: `zendure_controller_v17_0_2.zip`, SHA256 `82bd2db52a71b4a4e56f8e8c39e30511494fb02f8735909667052b73bd82f311`, Größe 14.402.481 Byte. Das exakt veröffentlichte ZIP bestand Root-/ZIP-Integrität, Release-Hygiene, Source-Manifest **932/932**, Fresh-extract-Manifest **932/932**, Build-Evidence und Datenblatt-Gate. Der echte Installer erreichte in der Build-Runtime mit diesem Paket Package-Identität, Datenblatt, Runtime-Smoke und Build-Evidence PASS und stoppte danach erwartungsgemäß vor Host-/Produktivmutation am Benutzer-`pi`-Gate.

Zum damaligen Paketfreeze war der reale V17.0.1 -> V17.0.2 Updatefeldlauf **PENDING** und V17.0.1 noch reale Runtimebasis; dieser historische Stand ist durch Abschnitt A überholt. Nach erfolgreichem Update müssen neue Fast-Capture-Shadow-Daten gesammelt und mit dem korrigierten Evidence-Pfad ausgewertet werden.

## 12. Reale Fast-Capture-Feldevidenz 23.–25.09.2026

### 12.1 Shadow

- Measurement-V4-Felder sind nach V17.0.2 cycle-exakt vorhanden.
- Lauf `...T123452Z`: `status=PASS`, `evidence_phase=SHADOW_ONLY`, 1701 Rows, 2 natürliche Episoden; State/Calculation/Mutation/Recovery PASS, physische Wirkung im Shadow korrekt `NOT_EVALUABLE`.
- Lauf `...T140151Z`: 1751 Rows, keine Episode, korrekt `NOT_EVALUABLE`.
- Ergebnis: Shadow-Gate PASS; begrenzter Active-Rollout anschließend ausdrücklich freigegeben.

### 12.2 Active

- Watchdog-Lauf 24.09.2026 08:32Z–10:20Z: Active real gesetzt, aber keine natürliche Fast-Capture-Episode; Watchdog stoppte wegen zu grobem `ready=false`-Guard. Nachauswertung: ausschließlich zulässiges `TRANSITIONAL:LIMIT_READBACK_CONVERGENCE`; Restoration `PASS_SHADOW_RESTORED`. Watchdog-Hotfix2 korrigiert die Readiness-Klassifikation; dies ist Tooling-, kein Controllerfehler.
- Spätere Active-Messung 24./25.09.2026: 40.531 Rows im Untersuchungsfenster, davon 23.794 Active-Mode-Rows, 501 positive Overlay-Rows, 20 Episoden, max. Overlay 1.642 W; `math_failures={}` im streamingbasierten Forensik-Extractor.
- `NEAR_LIMIT`: reale Fälle zeigen, dass das Fast-Capture-Overlay zusätzlich zur Baseline aufgebaut wird und der Restexport mit steigender Zendure-Istleistung deutlich sinkt. Keine Beobachtung mit positivem Fast-Capture-Overlay und gleichzeitig >100 W Netzbezug.
- Import-Guard: realer Umschlag auf Netzbezug führte zu sofortigem Overlay 0 (`GRID_IMPORT_ABORT`); anschließend Cross-Charge-/Neutralisierungspfad und physische Leistung gegen 0.
- Cross-Charge: 71 reale Erkennungen, alle begrenzt; kein positiver Fast-Capture-Overlay in diesen Cross-Charge-Zyklen.
- Command-Effekt in frischen Active-Overlay-Beobachtungen: überwiegend `COMMAND_TARGET_TRACKING_EFFECTIVE`/`COMMAND_PARTIALLY_EFFECTIVE`, kein `COMMAND_MISMATCH_CONFIRMED`.
- **Noch offen:** keine ausreichend belastbare Active-`FULL_IDLE`-Episode; Gesamtstatus deshalb nicht CLOSED.

### 12.3 Nomenklatur

In Prosa, UI, Logs und Reports künftig **„Fast Capture“**, bei echter Platzknappheit **„FastC“**, nicht kontextlos „Fast“. Technische Keys/Feldnamen bleiben unverändert.

## 13. Nacht-/MIN_SOC-Netzpfad-Incident 25.09.2026

### 13.1 Reale Ereignislinie

- letzter normal aktualisierter Grid-Wert etwa 01:24:04 lokal;
- Zendure erreicht etwa 01:24:07 den globalen `MIN_SOC=10 %`; Primärspeicher lag gleichzeitig nahe seiner Entladeuntergrenze, ist aber **nicht** Trigger des Fehlers;
- allgemeiner ZEC-Grid-State wird ab etwa 01:24:22 stale; letzter Wert bleibt stehen;
- exakt mit Ende des konfigurierten Nachtfensters um 05:30 wird im ersten Folgezyklus wieder ein neuer frischer Grid-Wert übernommen; scheinbare ZEC-Grid-Lücke rund 4 h 06 min;
- Nutzergegenprüfung in der SMA-Anwendung zeigte während des Incidents normale SMA-Hardware-/Portalwerte. Dies schließt nicht jedes lokale Multicastproblem formal aus, spricht aber gegen einen tatsächlichen Ausfall des Home Managers/Zählers.

### 13.2 Bestätigter Sourcebefund / `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001`

Im aktiven Nachtfenster führt `Zendure_SOC <= MIN_SOC` über den Night-/SOC-Hold-Pfad zu einem Early Return aus `run_once()` vor frischer Grid-Verarbeitung und vor normaler AUTO-Regelung. Deshalb ist der Defekt funktional: `MIN_SOC` neutralisiert zwar korrekt weitere Entladung, kann aber zugleich zulässiges Laden bei neu auftretendem realem PV-Export verhindern. Eine reine Display-Refresh-Korrektur reicht nicht.

**Verbindlicher Fixvertrag für den nächsten Release:** MIN_SOC bleibt harte Entladegrenze; Netztelemetrie muss frisch bleiben; bei realem Export darf normale AUTO-Ladung stattfinden, sofern MAX_SOC, Command-, Cross-Charge- und sonstige Safety-Grenzen dies erlauben. Fast Capture muss hierfür nicht im Nachtmodus freigegeben werden.

### 13.3 Diagnose-UI

Während `NIGHT_RESERVE_STOP`/`SOC_LIMIT_HOLD:MIN_SOC` und stale Grid-Telemetrie zeigte die UI `HOLD – Grund: Netzleistung nahe 0 W`. Dies ist als Diagnose-/Reason-Priorisierungsfinding unter `ZEC-BL-DIAG-001` offen; es beweist keine falsche Geräteansteuerung.

## 14. SMA-Speedwire-/OBIS-Parser-Finding 25.09.2026

- wiederkehrender realer dekodierter Rohwert: `-1.730.098,8 W`; der vorhandene 30-kW-Plausibilitätsfilter verwirft ihn korrekt.
- reale SMA-Topologie: ausgewählter Sunny Home Manager mit integriertem Hausanschlusspunktzähler plus zweiter SMA Energy Meter für die drei Zaun-Wechselrichter.
- V17.0.2-Sourcebefund: Leistungs-OBIS-Signaturen werden global per Bytefolge im UDP-Datagramm gesucht; echte Speedwire-/Protokoll-/OBIS-Recordstruktur und 4-/8-Byte-Werttypen werden nicht ausreichend als Parservertrag erzwungen.
- Entscheidung: Parserdefekt ist unabhängig von der noch nicht gesicherten exakten historischen Raw-Frame-Ursache **bestätigt und reparaturpflichtig**. Kein 72-h-Passivcapture als Fix-Vorbedingung.
- nächster Release: strukturierte Frame-/Protokollvalidierung + sequentieller OBIS-Recordparser + robuste Längen-/Typprüfung + unbekannte Felder überspringen + Seriennummernselektion beibehalten + Plausibilitätsfilter als zweite Schutzschicht erhalten. Deterministische Regression umfasst insbesondere False-Signature innerhalb eines 8-Byte-Wertes, falsche Protokoll-ID, Truncation, zusätzliche/umgeordnete OBIS-Felder und beide realen SMA-Geräte.
- Nach dem Fix genügt zunächst natürliche Feldbeobachtung der bestehenden Logs. Nur wenn der Extremwert erneut erscheint, ist ein gezielter Raw-Frame-Capture erforderlich.

## 15. Analyse-/Forensik-Ressourcenfinding 25.09.2026

Ein erster langer V4-Analyseblock materialisierte vollständige Measurement-Rows in RAM und machte den Raspberry Pi während Schritt 5/8 nicht mehr erreichbar; der Host musste neu gestartet werden. Ein Kernel-OOM-Beleg ist mangels verwertbarer historischer Journal-Evidenz nicht gesichert. Der direkte Analyseweg gilt dennoch als ressourcenunsicher.

Ein nachfolgender streamingbasierter Extractor verarbeitete 69.087 V4-Rows bounded und erzeugte die verwertbare Fast-Capture-/Grid-Incident-Evidenz. Dauerhafte Konsequenz: große Real-Pi-Historien nur streaming/bounded-memory; Vollmaterialisierungs-Analyzer nur gegen vorher begrenzte Extrakte.


## 16. Oktober-2026 Herbst-/Strategie-Evidenz (read-only, keine Produktfreigabe)

- Aus vollständig extern exportierten und offline bewerteten V4-Daten vom 24.09.–16.10.2026 (23 Tage): 646.890 gültige Messzyklen; 7 Tage, an denen beide Speicher jeweils unter 98 % SOC blieben; High-SOC-Rechenzweig 1.706 Minuten, `STRATEGIC_SHARE` 725 Minuten, an den 7 knappen Tagen 132 Minuten. Am 24.09., 08.10. und 13.10. keine strategische Share-Auswahl; am 13.10. betrug der Primärspeicher-SOC-Maximalwert ca. 88 %, also erklärt die SOC-Eintrittsschwelle allein die Branch-Nichtanwendung nicht.
- Vereinfachte Offline-A1-Sensitivität für 1.008 rekonstruierbare High-SOC-Minuten: +/-10 Prozentpunkte strategischer Primärshare verändern den begrenzten Zielwert in 226/139 Minuten um >=50 W. **Kein** geschlossener physikalischer Gegenfaktual-/Ertrags- oder Hardware-Nutzenbeleg. Bisheriges A1-Aktionsfeld für produktives Lernen als beschränkt bewertet; Adaptive wird im Master-Backlog begründet zurückgestellt, nicht entfernt.
- Im sieben-/23-Tage-Material Nacht-/MIN_SOC-Grid-Staleness-Reproduktionen sowie separate 05.10.2026 Command-Episoden: wiederholte mögliche unbegründete Lade-Resyncs und intermittierende Entlade-Nichtwirkung. Die Command-Kausalität ist nicht abschließend belegt; gezielte spätere Source-/Readback-Prüfung bleibt erforderlich. Dies **ersetzt nicht** die zwingenden Next-Release-Fixes vom 25.09.2026 und erweitert sie nicht stillschweigend.
- Analysegrenzen: V4-Samplemittel nicht automatisch korrekt integrierte Energiemengen; keine vollständige unabhängige PV-/Hausenergiemessung in diesen Exporten, 5 Minuten Datenlücke im ersten 16-Tage-Fenster. Auf dem produktiven Raspberry Pi wurden nur begrenzte read-only Streamingexports mit positivem Extractorstatus durchgeführt; alle fachlich schweren Auswertungen offline.
- Referenzen: `ZEC_A1_WIRKSAMKEIT_23T_DECISION_BRIEF_20261017.md`, `ZEC_HERBSTANALYSE_23T_KONSOLIDIERT_20261017.md`, `ZEC_20261005_COMMAND_EPISODES_OFFLINE_20261017.md`. Diese Analyseberichte sind Evidenz-/Provenienzquellen, **keine** automatische Runtime- oder Releasefreigabe.
