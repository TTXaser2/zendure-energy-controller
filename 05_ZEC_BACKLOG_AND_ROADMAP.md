# ZEC – Master-Backlog & Roadmap

**Stand:** 20.10.2026  
**Status:** kanonische, persistente Entwicklungsledger- und Roadmap-Autorität  
**Produktbasis:** V17.1.0 reale Pi-Runtime / `TECHNICAL_BUILD_PASS` / Update und allgemeine Feldabnahme `FULL_READY` **PASS** am 20.10.2026. Die V17.0.2-Pflichtdefekte sind in V17.1.0 implementiert und regressionsgeprüft; spezifische natürliche NIGHT/MIN_SOC-/Stale-/S3-Strategie-Evidenz bleibt entsprechend unten `EVIDENCE_PENDING`/`NOT_EVALUABLE`. Fast Capture: bisheriger Active-NEAR_LIMIT-Nachweis erhalten, Active-FULL_IDLE weiterhin EVIDENCE_PENDING.

### ZEC-BL-UI-SETTINGS-HELP-001 – Anwendergerechte Settings-Erklärungen und Bereichszwecke

- **Status:** `IN_PROGRESS / USER_APPROVED_20261020 / IMPLEMENTATION_PARTIAL`; vollständige inhaltliche Umsetzung und Freigabe **noch offen**.
- **Zweck/Pflicht:** Jede tatsächlich angebotene Einstellung muss ohne Entwicklungs- oder Elektrotechnik-Vorkenntnisse ihren konkreten Systemzweck und die Wirkung auf Regelung, Steuerausgabe oder reinen Diagnose-/Speicher-/Zugriffspfad erläutern. Der Zusammenhang zu benachbarten Einstellungen, Aktivierungsschaltern, Quellen, wirksamen Limits, Ausnahmen und Vorrangregeln ist **Pflichtbestandteil des einleitenden Haupttextes** und darf nicht in isolierte technische Unterkapitel ausgelagert werden. Benutzer müssen unterscheiden können zwischen *gespeichert*, *aktiviert*, *anwendbar*, *berechnet* und *physisch wirksam*.
- **Hilfestruktur:** Direkt unter jeder Bereichsüberschrift steht eine sinnvolle, dauerhaft sichtbare Erklärung zum jeweiligen Zweck. Die Hilfe je Setting behandelt fachlich korrekt: (1) Wozu und Verhältnis zu anderen Settings/Reglerpfaden, (2) Ein/Aus bzw. Änderung und Optionen, (3) Wann/nicht anwendbar, (4) konkrete Auswirkungen und übergeordnete Schutzregeln, (5) passende anschauliche Beispiele. Technische Kennungen und Codes nur ergänzend für Experten.
- **Kein generischer Fallback als fertige Hilfe:** Formeln wie `Konfiguration für …`, `wirkt gemäß …`, `zusammengehörige Parameter …`, `RICH/BASE` oder rein technische Metadaten gelten nicht als Endnutzer-Erklärung. Alle operativ sichtbaren Settings einschließlich Standard/Experte müssen individuell gegen echten V17.1.0-Source-Consumer/Registry und Hardware-Safety begründet werden. Fehlende oder nicht verifizierbare Beschreibung wird als Qualitäts-Finding inventarisiert und verhindert UI-Completion.
- **Umsetzung in überprüfbaren Scheiben:** erster Source-Slice S3-Saison-/Tagesprofiltexte, Hilfedialog-Grundstruktur und sichtbare Abschnittszwecke; noch **kein** Gesamt-PASS für ca. 190 operative Settings. Erweiterung in der Registry automatisiert inventarisieren und in fachlichen Schritten abarbeiten, ohne die QA für Teilfortschritt als Gesamtabnahme auszugeben.
- **Tests/Exit:** Quellenmapping und Vollständigkeits-/Placeholder-Gates, nachvollziehbare Text-/Wirkungsprüfung jedes aktiven Keys, i18n/mobile/standard/expert/accessibility, Headless-Browserprüfung, Negativfälle bei abgeschalteter S3-Policy und unveränderte Command-/Controllerlogik; vollständige Regression und Releasegates erst vor Produktivpaket.
### ZEC-BL-UI-SETTINGS-HELP-001 – Anwendergerechte Settings-Erklärungen und Bereichszwecke

- **Status:** `IN_PROGRESS / USER_APPROVED_20261020 / IMPLEMENTATION_PARTIAL`; vollständige inhaltliche Umsetzung und Freigabe **noch offen**.
- **Zweck/Pflicht:** Jede tatsächlich angebotene Einstellung muss ohne Entwicklungs- oder Elektrotechnik-Vorkenntnisse ihren konkreten Systemzweck und die Wirkung auf Regelung, Steuerausgabe oder reinen Diagnose-/Speicher-/Zugriffspfad erläutern. Der Zusammenhang zu benachbarten Einstellungen, Aktivierungsschaltern, Quellen, wirksamen Limits, Ausnahmen und Vorrangregeln ist **Pflichtbestandteil des einleitenden Haupttextes** und darf nicht in isolierte technische Unterkapitel ausgelagert werden. Benutzer müssen unterscheiden können zwischen *gespeichert*, *aktiviert*, *anwendbar*, *berechnet* und *physisch wirksam*.
- **Hilfestruktur:** Direkt unter jeder Bereichsüberschrift steht eine sinnvolle, dauerhaft sichtbare Erklärung zum jeweiligen Zweck. Die Hilfe je Setting behandelt fachlich korrekt: (1) Wozu und Verhältnis zu anderen Settings/Reglerpfaden, (2) Ein/Aus bzw. Änderung und Optionen, (3) Wann/nicht anwendbar, (4) konkrete Auswirkungen und übergeordnete Schutzregeln, (5) passende anschauliche Beispiele. Technische Kennungen und Codes nur ergänzend für Experten.
- **Kein generischer Fallback als fertige Hilfe:** Formeln wie `Konfiguration für …`, `wirkt gemäß …`, `zusammengehörige Parameter …`, `RICH/BASE` oder rein technische Metadaten gelten nicht als Endnutzer-Erklärung. Alle operativ sichtbaren Settings einschließlich Standard/Experte müssen individuell gegen echten V17.1.0-Source-Consumer/Registry und Hardware-Safety begründet werden. Fehlende oder nicht verifizierbare Beschreibung wird als Qualitäts-Finding inventarisiert und verhindert UI-Completion.
- **Umsetzung in überprüfbaren Scheiben:** erster Source-Slice S3-Saison-/Tagesprofiltexte, Hilfedialog-Grundstruktur und sichtbare Abschnittszwecke; noch **kein** Gesamt-PASS für ca. 190 operative Settings. Erweiterung in der Registry automatisiert inventarisieren und in fachlichen Schritten abarbeiten, ohne die QA für Teilfortschritt als Gesamtabnahme auszugeben.
- **Tests/Exit:** Quellenmapping und Vollständigkeits-/Placeholder-Gates, nachvollziehbare Text-/Wirkungsprüfung jedes aktiven Keys, i18n/mobile/standard/expert/accessibility, Headless-Browserprüfung, Negativfälle bei abgeschalteter S3-Policy und unveränderte Command-/Controllerlogik; vollständige Regression und Releasegates erst vor Produktivpaket.

### ZEC-EV-HOST-FREEZE-001 – Historischer externer Host-Freeze, Provenienz
- **Status:** `HISTORICAL_EVIDENCE_GAP / NO_NEW_RELEASE_SCOPE`. `RELEASE_INFO_V12_12_2.md` erwähnt einen externen 14-Minuten-Host-Freeze ausdrücklich als damaligen Nicht-Scope. Dieser alte Hinweis wird erhalten, nicht als aktuell reproduzierter ZEC-Fehler eingestuft. Nur bei neuer Beweislage beurteilen.

### ZEC-BL-CTRL-REFACTOR-001 – Historische optionale Controllerzyklus-Refaktorierung
- **Status:** `DEFERRED_IDEA / NO_APPROVED_CODE_SCOPE`. `TECHNICAL_NOTES_V12_8_6.md` nennt eine mögliche spätere größere Refaktorierung. Nicht als Entwicklungspflicht oder freigegebener Umbau der Safetysemantik interpretieren.



### ZEC-BL-DOC-ARCH-001 – Reconciliation historischer Release-Root-Originale V17.1.2

**Status:** `RECONCILED_AS_HISTORICAL_PROVENANCE`, 185 ausschließlich versionsbezogene Root-Release-/Notes-/Build-Dokumente werden unverändert nach `docs/history/release_root` umgeordnet; Originalbytes/Hashes/Planungsmarker/Quellen und konkrete Ledger-Referenzen sind zusätzlich in `docs/history/release_root/ARCHIVE_NO_DROP_AUDIT.json` dokumentiert. Historische Nicht-Scope-Angaben sind keine nachträglichen Produktaufträge. Sämtliche Markertexte bleiben byteidentisch in den archivierten Originalen, neue separate EV-/Ideen-IDs sind explizit erhalten. Keine anderen oder unbekannten Dokumente werden entfernt.


## 1. Zweck und Persistenzvertrag

Diese Datei ist nicht nur eine Liste aktueller offener Aufgaben. Sie ist das **verlustfreie Master-Ledger der ZEC-Produktentwicklung**. Jeder recoverbare relevante Entwicklungs-, Evidenz-, Spezifikations- oder Prozesspunkt erhält eine stabile ID, Provenienz und einen expliziten Status.

Ein Eintrag darf nicht durch Quellenbereinigung verschwinden. Er darf nur fortgeschrieben und in einen anderen Status überführt werden. Die **Roadmap** ist eine priorisierte Sicht auf dieses Ledger; das Ledger selbst bleibt historisch vollständig.

Historische Chats, Übergaben und Releaseunterlagen sind Provenienz-/Archivbelege. Aktuelle reale Sources und aktuelle reale Evidenz haben bei Widerspruch Vorrang.


## Ergänzung 20.10.2026 – Quellenmitgliedschaft / 25-Dateien-Grenze

- **Projekt-Quelleninventar vor diesem Zusatzupdate:** 20 tatsächlich aktive Dateien, darunter kanonische `00`–`07`, das exakte finale V17.1.0-Source-ZIP, Installationsanleitung, Normregelwerke, Lernwerkzeug und historische Planungs-/Evidenzquellen. Acht Kernquellen einschließlich bereits aktualisierter `00`, `02`, `04`, `05`, `07` wurden lesbar angetroffen.
- **Verbindliches Ziel nach manueller Einspielung:** 22/25 Dateien. Nur `00` und `05` mit neuem Inhalt **ersetzen**, `ZEC_S3_PRODUKTIONSSPEZIFIKATION_V17_0_2_FINAL_20261019.md` und `ZEC_V17_1_0_RELEASE_UND_FELDEVIDENZ_KONSOLIDIERT_20261020.md` **ergänzen**. Keine andere Projektdatei löschen oder ersetzen. Anschließende Prüfung des realen Projektbestands ist vor Behauptung `PROJECT_SOURCE_ADOPTION_PASS` zwingend.
- **Verlustfreier Evidenzvertrag:** Das Sammeldokument enthält den technischen V17.1.0-Releasebericht und alle vier Realfeldberichte **vollständig im Originaltext** mit Prüfsummen pro Original. Die getrennten Originale bleiben in der persönlichen Bibliothek `/ZEC - Zendure Energy Controller/Releases/`. Abweichende Datumsstände nicht als aktuelle Feldautorität vermischen; `07` bleibt aktuell. Bibliothek allein ersetzt keinen aktiv angehängten Projektquellenplatz.
- **Backlog-/No-Drop-Vertrag:** Diese Quellenergänzung nimmt **keinen** neuen technischen Roadmappunkt vor, entfernt keine `ZEC-BL-`- oder `ZEC-EV-`-ID, verändert keinen fachlichen Status der Regler-/Safety-/Hardwarewirkung. Der neue Minigraph-Folgepunkt `ZEC-BL-UI-GRID-MINICHART-001` bleibt offen, S3-/Stale-/NIGHT-MIN_SOC-/Fast-Capture-Realnachweise bleiben evidenzabhängig offen. Keine historisch aktive Projektquelle wird entfernt: ein source-spezifisches **Bereinigungs-`BACKLOG_NO_DROP_GATE` ist nicht ausgelöst**; der rein additive Ledger-Identitätsabgleich wird beim Paketbau dokumentiert.
- **Geltungsgrenze:** Dies ist eine **Projektquellenpflege**, keine Source-/Konfigurationsänderung der produktiven Controller-Software, keine neue Version und keine neue Feldfreigabe. Technische `TECHNICAL_BUILD_PASS`- und `FULL_READY`-Evidenz bleibt unverändert.

## Aktuelle Release-/Feld-Reconciliation 20.10.2026 – V17.1.0 (maßgeblich)

- **Release:** unverändertes final veröffentlichtes ZIP `zendure_controller_v17_1_0.zip`, SHA256 `11dddaaaa7831e2339a19b9b7f46412ee72f35917935b7292a005a47bfe61669`, Build `v17.1.0-20261019`; TECHNICAL_BUILD_PASS; 1.220 Tests + 718 Subtests regulär und unter `ResourceWarning=error`, sowie Fresh-extract/Deployment/Manifest/Dokumentationsgates. Reales Pi-Update und allgemeine Feldabnahme 20.10. **PASS / FULL_READY**, `RELEASE_BACKUP_EXACT`.
- `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001`: Sourcefix und vollständige technische Regression umgesetzt; alte Next-Release-Blockerpflicht damit technisch erledigt; natürliche Low-SOC-Export-Feldepisode weiterhin ausstehend.
- `ZEC-BL-GRID-SMA-OBIS-001`: strukturierter Parser inkl. OBIS-Länge/4-/8-Byte/Seriennummer/Negativtests implementiert, technische Regression PASS; historische Extremwertursache weiterhin nicht als eindeutig bewiesen behandeln. Live-HOLD-Grid-Pfad mit SMA-Receiver ist real frisch beobachtet.
- `ZEC-BL-CTRL-S3-001`: abgeschlossener finaler Produktionsvertrag umgesetzt; Opt-in/Legacy-Migration und `NOT_APPLICABLE` im realen HOLD beobachtet; reale Zielwert-/Hardwarewirkung im natürlichen Harvest **EVIDENCE_PENDING**.
- `ZEC-BL-UI-STATUS-LIVE-001`: reale unabhängige 1-Hz-Grid- und Primärspeicherfrische während `HOLD` **PASS**; Browser-/Sourcegates technisch PASS; NIGHT, weitere Quellen und physisch schnelle Gerätewechsel weiterhin differenziert nachzuweisen.
- `ZEC-BL-DIAG-GRID-STALE-001`: Incident-Diagnostik/Entprellung/Resolve technisch PASS, aber nach vollständiger 2-Tages-Inventur (155 Events, davon 0 stale, 0 open) kein natürlicher Grid-Stale-Fall -> Realtrigger/Resolve **NOT_EVALUABLE**. Kein Sensor künstlich trennen.
- `ZEC-BL-DOC-ARCH-001`: Releasegebundene `docs/architecture`, Specs, ADR/History und prüfendes Dokumentationsgate in V17.1.0 PASS. Dauerhafte Pflicht bleibt für Folgeversionen.
- `ZEC-BL-PROC-CHKPT-LIBRARY-001`: CP15 und finales Release-ZIP sind extern Bibliothek-Readback-/SHA256-/Byte-/CRC-verifiziert; gesicherte Releaseevidenz separat im Bibliotheksordner `Releases`.
- **Reales Betriebsereignis:** seit 09:52 genau eine Mode-Transition um 10:03:22 `SAFE_STATE → HOLD`; Journalfolge `systemd Started` 10:03:12, MQTT verbunden 10:03:16, `COMMAND_RESYNC` 10:03:21 stützt Start-/Reinitialisierungskontext, nicht eine Oszillation. Anlass dieses Dienststarts nicht geklärt.
- **UX-Finding** `ZEC-BL-UI-GRID-MINICHART-001` nach Screenshot 20.10.: Live-Netzwert 1 s, Minigraph-Poll 10 s und Controller-Historypunkte typischerweise je Reglerzyklus; sichtbar kein Refreshintervall. **OPEN / NEXT_UI_ITERATION / non-blocking**. Kein rückwirkender Eingriff in eingefrorenes V17.1.0-Release.
- **Roadmap nach Installation:** S3-/Stale-/NIGHT-MIN_SOC-Realnachweise fortführen, Fast-Capture-FULL_IDLE erhalten, weiterhin B2/C1 (separat spezifizieren), Battery Care winterpriorisiert, Adaptive deferred; Graph-UX-Härtung in nächstem passenden UI-Release, ohne Roadmapverlust oder Sicherheitssemantikänderung.
- **No-drop:** alle vor diesem Update erkannten IDs und historischen Roadmap-/Freigabetexte bleiben bestehen; neue ID ausschließlich `ZEC-BL-UI-GRID-MINICHART-001`. Projektquellen werden nicht gelöscht oder archiviert. Das Release-Snapshot im ZIP bleibt unveränderlich und wird nicht nachträglich umgeschrieben.

### ZEC-BL-UI-GRID-MINICHART-001 – Netzleistungs-Minigraph: Aktualisierungsfrequenz sichtbar machen (NEU 20.10.2026)

- **Status:** `OPEN / UX_FOLLOWUP / NEXT_UI_ITERATION`; `implementation_state=not_started`; `priority=non_blocking`; kein Incident im Steuer- oder Messpfad.
- **Reale Evidenz:** Screenshot des produktiven V17.1.0 am 20.10.2026: Netzleistungszahl `+8 W` schnell, letzter Verlaufspunkt `-3 W` wirkt verzögert; keine Erklärung des Chart-Intervalls außer „letzte 48 Punkte“. Exakte Sourcepfade: `static/status_v2.js` PollChannel(`/status-live-data`, **1000 ms**) und PollChannel(`/grid-mini-data`, **10000 ms**); `web_ui.build_grid_mini_payload` liest 48 letzte `state.graph_history`-Regler-Messpunkte.
- **Verpflichtende UX-Abnahme:** in der Karte unmittelbar lesbar unterscheiden zwischen „Livewert (1 s)“ und „Minigraph: letzte 48 Regler-Messpunkte · Aktualisierung alle 10 s“ (oder vergleichbar korrekt und responsive); Chart-Endwert als letzter **Verlaufspunkt** statt als zeitgleich aktueller Istwert ausweisen; Standard/Experte/Mobile, i18n/Info-Text und visuelle Regression prüfen.
- **Optional gesondert:** Minigraph auf echte read-only 1-Hz-Grid-Samples umrüsten, falls nach Performance-/Zeitachsen-/Speicher-/Datenalterkonzept sinnvoll; keine bloße 1-s-Abfrage unveränderter Controller-3-s-Historie als scheinbare Livegrafik. Controller-/Command-/Safety-Semantik nicht ändern. Vor Sourceentwicklung separater UX-Scope und freigegebenes Releasefenster.
- **Exit:** im tatsächlich ausgelieferten Folge-Release UI-Vertrags-/Browser-/Accessibilitytests, sichtbare Refreshsemantik und nachvollziehbare Anzeige bei voneinander abweichenden Live-/History-Werten. V17.1.0 bleibt byteidentisch.

## Historische Freigabe-/Scopefortschreibung 19.10.2026 – S3 + unabhängige 1-Hz-Status-Evidenz

**Nutzerentscheidung:** S3-Produktionsvertrag fachlich schließen und anschließend ohne neue Grundsatzdiskussion auf der verifizierten V17.0.2-Basis entwickeln. Zusätzlich im **nächsten Produktrelease** verpflichtend: 1-Hz-Anzeige der real vorhandenen Netz-/Zendure-/Primärspeicherleistung, SOC und weiterer relevanter Messstati, unabhängig vom Controller-Intervall und davon, ob der Regelpfad in `NIGHT`/`HOLD`/`MIN_SOC` bereits zurückgekehrt ist; Messalter/Validity immer ehrlich mitführen. Grid-Stale/Controller-Processing-Stale als persistente Betriebsereignisse erfassen, open/resolve und Entprellung, ohne Event-Flut. Bestehende zwei Pflichtdefekte und UI-Followups bleiben im selben Produktrelease zwingend. Separate Quellen- und Hardwarepfade (SMA direkt, MQTT, nativer Modbus, Shelly HTTP) dürfen keine unehrlichen Aktualitätsbehauptungen erzeugen.

**Freigabe-/Entwicklungsbasis:** `ZEC_S3_PRODUKTIONSSPEZIFIKATION_V17_0_2_FINAL_20261019.md` ist der geschlossene fachliche Sollvertrag; **keine Release-/Feldevidenz**. Am 19.10.2026 wurde ein **nicht freigabefähiger Source-Checkpoint** begonnen. Die S3-Settings werden dort in einer Entwicklungsfassung verdrahtet, 1-Hz-Read-only-Live-Snapshot (für SMA-Empfänger unabhängig vom Controller) und Grid-Stale-Eventprototyp fokussiert getestet. Erforderliche vollständige Ausleitung für Shelly-HTTP, UI-/Browser-/Sicherheits-/Profil- und sämtliche Releasegates noch offen. Die aktuelle produktive Software bleibt V17.0.2 und darf nicht mit dem Entwicklungscheckpoint verwechselt werden.

### ZEC-BL-UI-STATUS-LIVE-001 – quellenunabhängige sekündliche Statusaktualisierung (NEU 19.10.2026)
- **Status 20.10.2026:** `IMPLEMENTED / TECHNICAL_PASS / HOLD_PARTIAL_FIELD_PASS / EVIDENCE_PENDING_OTHER_MODES`, `implementation_state=implemented`. Ursprünglich `IN_PROGRESS / REQUIRED_NEXT_RELEASE` am 19.10.2026; das ist historische Scope-Provenienz.
- Zweck: Browser-Status jede Sekunde mit den neuesten von den Messquellen empfangenen Werten aktualisieren, nicht nur im Reglerzyklus gepflegte Statusfelder erneut ausgeben. Erfassungsraten der physischen Quellen bleiben separat; fehlende neue Samples als stale kennzeichnen, keine synthetisch frischen Werte.
- Integrität: keine neue Command-/Polling-Autorität, keine 3-s-Reglerbeschleunigung, kein blockierendes HTTP-Modbus-/SMA-/MQTT-IO im Regler; spezifisch unabhängiger Shelly-/Fallback-Quellenvertrag nötig; Zeitalter/Messquellen-/Browserlatenz/Performance auf Pi 3B+ testen.
- Exit: 1-Hz-fester Aktualisierungszyklus sichtbare Seite, Rohquellen auch bei NIGHT/HOLD und vollständigen frischen/staleness Failures, gültige Time-/Validity-UI in Standard/Experte, minimale CPU/IO-Kosten, No-Regression.

### ZEC-BL-DIAG-GRID-STALE-001 – persistente Netzleistungs-Stale-Betriebsereignisse (NEU 19.10.2026)
- **Status 20.10.2026:** `IMPLEMENTED / TECHNICAL_PASS / GRID_STALE_REAL_NOT_EVALUABLE`, `implementation_state=implemented`; 155 Events ohne Stale/OPEN. Ursprünglich `IN_PROGRESS / REQUIRED_NEXT_RELEASE` am 19.10.2026.
- Zweck: ausbleibende Netzleistungsaktualisierung persistiert als eigener Incident mit Quelle, Alter, Reglerzustand; bei verfügbaren unabhängigen SMA-Receiver-Werten `SOURCE_STALE` von `CONTROLLER_PROCESSING_STALE` trennen; Debounce, single-open, resolved/recovered, keine pro-Zyklus-Ereignisflut. Auch bei Regler-Early-Return wirksam.
- Link: `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` funktional reparieren; `ZEC-BL-DIAG-001` Reason-/Stale-Anzeigensemantik weiterhin eigenständig. Dieser Diagnostikscope ersetzt **keinen** der beiden Fixes.
- Exit: mindestens Incident+Recovery bei Nacht/MIN_SOC mit lebendem SMA-RX, echter Sensorstale, initialer Startupphase, anderer Quelle, Modewechsel, SQLite-Restart und UI-Persistenz; realer Feldtest oder dokumentiertes `NOT_EVALUABLE`.

**Quellen-/No-Drop-Status:** Die früheren Ledgerabschnitte/IDs und die historische 87er-Aussage bleiben unverändert erhalten. Zwei neue eindeutige IDs additiv; nie eine Quellenbereinigung vor dem vollständigen `BACKLOG_NO_DROP_GATE`. Dokumentationsgate `ZEC-BL-DOC-ARCH-001` bleibt verbindlich.

### ZEC-BL-PROC-CHKPT-LIBRARY-001 – Extern verifizierte Checkpoint-Sicherung (NEU 19.10.2026)

- **Quellen-Übernahmestand 20.10.2026 nach Teilupdate:** `20_OF_25_VERIFIED / CORE_00_TO_07_ADOPTED / FINAL_S3_AND_EVIDENCE_AGGREGATE_PENDING_USER_UPLOAD`, Ziel `22_OF_25` nach diesem Paket. Hieraus folgt weder ein Produkt-Release-Rollback noch eine automatische PROJECT_SOURCE_ADOPTION_PASS-Behauptung.

- **Status 20.10.2026 (vorher):** `PROCESS_IMPLEMENTED / CP15_AND_RELEASE_LIBRARY_GATE_PASS / PROJECT_SOURCE_REPLACEMENT_PENDING`; die ursprüngliche CP03-Evidenz bleibt historische Provenienz. Source- und Releasebackup sind unabhängig in der Bibliothek byteidentisch verifiziert; die **neuen kanonischen Projektdateien sind erst nach Nutzerupload aktiv**.
- **Nutzerbeschluss 19.10.2026:** vollständige Entwicklungscheckpoints aus temporärem Working Tree **sofort in die persönliche ChatGPT-Bibliothek hochladen, unabhängig wieder materialisieren und Bytezahl/SHA256/ZIP-Integrität vergleichen**; `EXTERNALLY_SECURED` erst nach `CHECKPOINT_LIBRARY_GATE=PASS`. Kein weiteres wesentliches Coding bei ungesichertem Fortschritt. Normative Ausführung in `01` § 3 und `06` § 11; Einstieg `00` § 2c.
- **Konkrete Evidenz:** Checkpoint 03 am 19.10.2026 unter `ZEC - Zendure Energy Controller/Checkpoints/` erfolgreich hochgeladen und byteidentisch zurückgelesen (SHA256 `24b31fd0867ef770c6bbef43a5c942b31477d874fff8e3f5e0964daebb31c3fc`). Checkpoints 04–06 sind dadurch **nicht** wiedergefunden; keine falsche Rekonstruktion.
- **Retention:** keine automatische Löschung; bei Bedarf und mit expliziter Nutzerfreigabe unter Erhalt von Release-/Branch-/Rollback-/Handover-Ankern und allen nur dort erhaltenen Quellen, Tests und Entscheidungen. Bereinigung von Projektquellen/Planungsbelegen setzt zusätzlich `BACKLOG_NO_DROP_GATE=PASS` voraus.
- **Exit:** aktualisierte `00`/`01`/`05`/`06` in aktive Projektquellen übernommen und dort wiederauffindbar; künftig für **jeden** wesentlichen Sourcecheckpoint rücklesbarer PASS samt Evidenz. Kein finales `CLOSED`, solange die Übernahme nicht nachgewiesen ist.

## 2. Statusmodell

- `OPEN`: fachlich offen und grundsätzlich umsetzbar; vor Umsetzung Scope/Freigabe erforderlich.
- `DEFERRED`: bewusst zurückgestellt, nicht erledigt.
- `SPEC_NEEDED`: Thema ist beschlossen/erhalten, aber ein freigegebener implementierbarer Scope fehlt.
- `EVIDENCE_PENDING`: Implementierung existiert im Wesentlichen, aber ein geplanter realer Nachweis fehlt.
- `IN_PROGRESS`: aktiv freigegebener Entwicklungsblock.
- `CLOSED`: implementiert/abgeschlossen; Abschluss- und Releasebeleg bleibt dauerhaft erhalten.
- `SUPERSEDED`: durch spätere Architektur ersetzt; historische Provenienz bleibt erhalten.
- `REJECTED`: bewusst verworfen; Grund bleibt erhalten.

Zusätzlich kann `implementation_state` beispielsweise `none`, `partial` oder `implemented` sein. **Diskutiert**, **freigegeben**, **implementiert** und **real feldvalidiert** sind getrennte Aussagen.

## 3. Aktuelle Roadmap – priorisierte Sicht

**Verbindliches Realfeld-/Source-Delta 25.09.2026:** Der reale V17.0.2-Betrieb und die anschließende Sourceanalyse haben zwei eigenständige Defekte bestätigt. `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` ist **RELEASE_BLOCKER_NEXT_RELEASE**: bei aktivem Nachtfenster und erreichtem Zendure-`MIN_SOC` kehrt der aktuelle Pfad vor frischer Grid-Verarbeitung und normaler exportseitiger AUTO-Regelung zurück; dadurch kann realer PV-Export ungenutzt bleiben. `ZEC-BL-GRID-SMA-OBIS-001` ist **BUG_CONFIRMED / FIX_REQUIRED_NEXT_RELEASE**: der V17.0.2-SMA-Parser sucht Leistungs-OBIS-Bytefolgen global im Datagramm statt die Speedwire-/Protokoll-/OBIS-Struktur robust zu validieren. Der wiederholt verworfene Rohwert `-1.730.098,8 W` ist real belegt; seine exakte historische Raw-Frame-Ursache muss nicht als Vorbedingung für die strukturelle Parserkorrektur erneut eingefangen werden. Der bestehende 30-kW-Plausibilitätsfilter bleibt als zweite Schutzschicht erhalten.

**Release-Gate:** Kein nächster ZEC-Produktrelease darf freigegeben werden, solange **beide** Punkte nicht implementiert und regressionsgeprüft sind. Für `NIGHT-MINSOC-GRID` sind mindestens Nacht+MIN_SOC+Import, Nacht+MIN_SOC+Export, Import↔Export und Nachtende/Recovery nachzuweisen. Für `GRID-SMA-OBIS` sind mindestens valide Home-Manager-Frames, zusätzliche/unbekannte OBIS-Felder, 4-/8-Byte-Recordgrenzen, False-Signature-in-Payload, falsche Protokoll-ID, Truncation sowie die Seriennummernselektion der realen Zwei-SMA-Zähler-Topologie abzudecken.

**Verbindlicher Roadmap-/Strategieentscheid 18.10.2026 (überschreibt nur das bisherige Sequencing, nicht die Historie):** Nach Offline-Bewertung der 23 Herbsttage wird Adaptive-Lernen (A1) **DEFERRED / EVIDENCE_GAP**; S3, strategischer usable SOC (B2) und weiche Kapazitätsgewichtung (C1) sind **eigenständige** Funktions-/Spezifikationsscopes ohne notwendige Adaptive- oder High-SOC-Kopplung. S3 ist unmittelbar zu spezifizieren und als nächster freizugebender Funktionsblock vorgesehen; B2 und C1 benötigen je einen *zweck-/nutzenorientierten* Produktionsvertrag. Bei unverhältnismäßigem B2/C1-Aufwand wird Battery Care wegen Winterpriorität vorgezogen. Für jede neue policy-basierte Regelwirkung gelten nutzbarer Endzielwert und tatsächliche physische Wirkung als Wirksamkeitskriterium, kein alleiniger interner Sharewechsel. Verbindliche Freigabegrenze: kein produktiver Code allein durch diese Quellenkonsolidierung.

**Aktuelle priorisierte Roadmapsicht 18.10.2026:**

1. **Nächster Produktrelease – zwingend:** `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` beheben, alle vorhandenen Safety-/Regression-Gates; ohne beide kein Release-PASS.
2. **S3 eigenständig:** `ZEC-BL-CTRL-S3-001` – Saison-/Tagesprofile: Zweck, Runtimewirksamkeit aller vorgesehenen Keys, sichere Legacy-/Neuinstallationsmigration, zeitrichtige Kalender-/Timersemantik, UI-/Diagnosevertrag und No-Regression; vor Sourceänderung eigenständige finale Spezifikations-/Scopefreigabe.
3. **B2 eigenständig:** `ZEC-BL-CTRL-USABLE-SOC-001` – sinnvolle deterministische, kontextabhängige strategische Nutzung des diagnostisch bereits vorhandenen usable SOC, nicht pauschal Winter-only; konkrete Wirksamkeit und Geltungsgrenzen vor Coding.
4. **C1 eigenständig:** `ZEC-BL-CTRL-CAP-001` – optionale weiche Kapazitätsgewichtung `off|soft`, default `off`; übergreifenden erlaubten Aktionsraum prüfen, nicht unreflektiert auf High-SOC begrenzen; harte Invarianten bleiben erhalten.
5. **Winterpriorisiert Battery Care:** `ZEC-BL-BATCARE-001` – getrennte Zendure-Reserve-/SOC-Erhaltungsstrategie; **vorziehen**, wenn B2/C1 zeitlich unverhältnismäßig aufwendig werden. Netzladung ist gesondert freigabepflichtig und nicht implizit aktiviert.
6. **Adaptive bewusst DEFERRED:** `ZEC-BL-CTRL-ADAPTIVE-001` und `ZEC-BL-CTRL-001` – sämtliche Konzepte/Lern-/Replay-/Confidence-/Persistenzfragen und A1-Evidenz erhalten; Wiederaufnahme nur bei plausiblem Zusatznutzen und geprüftem Aktionsraum (gegebenenfalls jenseits High-SOC).
7. **Release-Dokumentationsvertrag:** `ZEC-BL-DOC-ARCH-001` – versionsgebundene aktuelle Architektur, Specs, ADR und niedrigaufwändige echte Historie im Source-`docs/`; ab nächstem Release; keine Vorbedingung für die S3-Fachspezifikation.
8. **Fast Capture Field/Evidence:** `ZEC-BL-CTRL-FASTCAP-001` Active-`FULL_IDLE` und bounded-/applicability-aware Forensik bleiben `EVIDENCE_PENDING`, sind keine Voraussetzung für getrennte S3-Konzeption.
9. **Verbleibende Frontend-/Storage-/Analyse-/Simulation-/Multi-/Release-Härtungen** verbleiben unverändert unter ihren bisherigen stabilen IDs, mit jeweiligem Implementierungs- und Feldevidenzstatus.

**Historischer Roadmap-Snapshot 23.09./25.09.2026, inzwischen im Sequencing abgelöst (Provenienz, nicht aktuelle Anweisung):**

**Roadmapstand 23.09.2026:** V17.0.1 ist real installiert und automatisiert FULL_READY feldabgenommen. V17.0.2 korrigiert ausschließlich drei real gefundene Fast-Capture-Evidenzdefekte und besitzt nach 157 Testdateien / 1169 Tests + 706 Subtests, identischem ResourceWarning-Lauf sowie statischen/Deployment-/Datenblatt-/Build-Evidence-Gates TECHNICAL BUILD PASS; finale Paket-/Fresh-extract-Gates folgen vor Veröffentlichung. `ZEC-BL-CTRL-FASTCAP-001` bleibt FIELD_PENDING, bis nach V17.0.2-Installation neue Shadow-Evidenz und anschließend ausdrücklich freigegebene begrenzte Active-Evidenz vorliegen. Desktop-Warning-Chip/Popover ist real visuell PASS; mobile Bottom-Sheet-Variante bleibt offen.

**Roadmapstand 22.09.2026 nach abgeschlossener V16.2.5-Feldentscheidung:** Das Update V16.2.4 → V16.2.5 ist real erfolgreich. Der konsolidierte automatische Feldlauf ist PASS; `controller_ready` war wegen `LIMIT_READBACK_CONVERGENCE` transient, `controller_readiness_acceptance=PASS TRANSITIONAL:LIMIT_READBACK_CONVERGENCE`. Instance Owner, Speicherstatuskarten-Geometrie, Mobile Settings, sichtbare Graph-Linienunterbrechung sowie die funktionale ein-/ausklappbare High-SOC-/Command-Warnung sind real beobachtet.

Die reale Sichtprüfung hat zwei klar isolierte Frontend-Restpunkte ergeben: (1) `ZEC-BL-GRAPH-GAP-001`: Cursor/Tooltip/Inspector müssen innerhalb bestätigter Evidence-Gaps einen ehrlichen Gap-/Empty-State statt Nearest-Sample-Werten bzw. Epoch-Nullzeit zeigen; (2) `ZEC-BL-UI-STATUS-003`: der persistente Warnhinweis soll im kompakten Zustand höhenneutral als Warning-Chip im Kartenkopf erscheinen, während Details Desktop als verankertes Popover und mobil als Bottom-Sheet/Modal außerhalb des normalen Kartenflows geöffnet werden. Der Nutzer hat am 22.09.2026 ausdrücklich entschieden, für diese zwei kleinen, bereits klar abgegrenzten UI-Härtungen **keinen separaten Hotfix-Zyklus** zu erzwingen. Sie werden im nächsten ohnehin anstehenden Release als eigenständige, regressionsgeprüfte Frontend-Subscopes mitgeführt und sind **keine Sequencing-Blocker**.

Das Sequencing-Gate ist am 22.09.2026 durch ausdrückliche Nutzerentscheidung geschlossen: **`ZEC-BL-CTRL-FASTCAP-001` wird als nächster Controllerblock umgesetzt; Fast Capture wird technisch und fachlich von `ZEC-BL-CTRL-ADAPTIVE-001` entkoppelt.** Die eingefrorene A400/R100-Spezifikation wurde gegen die reale V16.2.5-Codebasis revalidiert (`PASS_WITH_V16_2_5_INTEGRATION_DELTAS`). `controller_logic.py`, `ZendureController.py`, `command_lifecycle.py`, `config_validator.py` und `primary_storage_source.py` sind zwischen V16.0.2 und V16.2.5 byteidentisch; die notwendigen Deltas betreffen vor allem State-/Settings-/Measurement-/UI- und Feldevidenzverträge. Die revalidierte Spezifikation `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_2_5_REVALIDATED.md` ist Blockautorität. Der V17.0.0-Makro-Implementierungsscope wurde anschließend ausdrücklich freigegeben. Checkpoint A (Controllerkern/State/Differential-/Safetytests) ist fokussiert PASS mit 110 Tests + 11 Subtests; Checkpoint B (Settings/Validation, Measurement V4, Fast-Feldanalyse und V17-Feldabnahme) ist fokussiert PASS mit 114 Tests + 640 Subtests. Ein TECHNICAL BUILD PASS liegt noch nicht vor.

Adaptive bleibt vollständig erhalten, ist aber kein Vorläufer für Fast Capture. Nach Bereitstellung des Fast-Capture-Releases beginnt ein eigener Adaptive-Spezifikationsblock; reale Fast-Episoden dürfen dabei als Evidenzinput dienen. Adaptive-Controller-Sourcearbeit benötigt weiterhin Lernzustand/Persistenz/Reset, Confidence/Fallback, S3-Mapping, Capacity-Weighting-Vertrag und eigene explizite Freigabe.

Historische priorisierte Sicht vom 23.–25.09.2026 (durch Roadmapsicht 18.10.2026 hinsichtlich Adaptive/S3/B2/C1/Battery Care ersetzt):

1. **Zwingende Fixes im nächsten Produktrelease:** `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001`; Releaseblocker bis Implementierung und Regression beider Punkte.
2. **`ZEC-BL-CTRL-FASTCAP-001` – Fast Capture A400/R100:** Implementierung und allgemeine V17.0.2-Feldbasis PASS; Shadow-Gate PASS; reale Active-`NEAR_LIMIT`-Evidenz in den beobachteten Aspekten PASS. Active-`FULL_IDLE` sowie die abschließende Evidence-Tooling-Härtung bleiben EVIDENCE_PENDING.
3. **Verbindliche UI-Follow-ups im nächsten ohnehin anstehenden Release:** `ZEC-BL-GRAPH-GAP-001` Gap-aware Cursor/Tooltip/Inspector sowie `ZEC-BL-UI-STATUS-003` höhenneutraler Warning-Chip + Desktop-Popover/Mobile-Bottom-Sheet. Beide als isolierte Frontend-Deltas mit eigener Regression.
4. **`ZEC-BL-CTRL-ADAPTIVE-001` – Adaptive-Spezifikationsblock:** S3 + adaptive Strategie + weiche Kapazitätsgewichtung vollständig spezifizieren; dies darf parallel zur verbleibenden Fast-Capture-Feldevidenz erfolgen. Produktive Adaptive-Sourcearbeit bleibt separat freigabepflichtig und muss die beiden Next-Release-Fixes mitführen, falls sie den nächsten Produktrelease erzeugt.
5. **ZEC-BL-BATCARE-001 – Battery Care / Winter- und Reserve-SOC-Erhaltung** folgt gemäß bestehender Roadmap nach dem adaptiven Block; vor Implementierung ist aus dem erhaltenen Brainstorming eine explizit freigegebene Spezifikation zu erstellen.
6. **ZEC-BL-STORAGE-001 – Measurement-/SQLite-Storage-Lifecycle.** S4/S5/S6/S7/S9 gegen die aktuelle Codebasis inventarisieren und in sicheren Stufen umsetzen.
7. **ZEC-BL-ANALYSIS-HANDOFF-001 – Graph → Analyse-Service.**
8. **ZEC-BL-SIM-001 – kontrafaktische Regler-Simulation.**
9. **ZEC-BL-SCENARIO-001 – allgemeiner Szenarioeditor.**
10. **ZEC-BL-MULTI-001 – echter Multi-Zendure-Command-/Regelpfad.** Darstellung mehrerer Entities ist keine aktive Dual-Headunit-Regelung.
11. **ZEC-BL-REL-001 – repo-zentrierter/reproduzierbarer Releaseprozess / CI.**

Querschnittlich bleiben `ZEC-BL-PRIMARY-METADATA-001`, `ZEC-BL-UI-STATUS-EXPERT-001`, Diagnose-/Command-Langzeitevidenz, Lernwerkzeugabgleich und Storage-Langzeitperformance erhalten.

### 3.1 Historische S1–S9-Stufen – vollständige Reconciliation

| Stufe | historische Bedeutung | aktueller Ledgerstatus | Auflösung |
|---|---|---|---|
| S1 | Settings-Basis, UI und Legacy-Audit | CLOSED | in RC20/V12.11.x–V12.12.x produktiv umgesetzt; dauerhaft in der Closed-Historie erhalten |
| S2 | Primärspeicherintegration | CLOSED / SUPERSEDED BY V15 ARCHITECTURE | source-neutrale Primärspeicherintegration und direkte read-only Modbus-Anbindung in V15.0.0 schließen die alte S2-Kopplungslücke |
| S3 | Saison- und Tagesprofile | OPEN / SPEC_DRAFT, **jetzt eigenständiger Scope** | `ZEC-BL-CTRL-S3-001`; Adaptive-Umbrella-Anbindung vom 20.09.2026 historisch, ab 18.10.2026 in der Reihenfolge supersediert |
| S4 | SQLite-Pfad und `report_only` | OPEN / partial | `ZEC-BL-STORAGE-S4-001` |
| S5 | SQLite-Enforce | OPEN | `ZEC-BL-STORAGE-S5-001`; Bedeutung aus `conversations.json` wiederhergestellt |
| S6 | V4-Schutz, Katalog und Sicherheitsdialog | OPEN / partial | `ZEC-BL-STORAGE-S6-001` |
| S7 | V4 `compress_only` und Restore | OPEN | `ZEC-BL-STORAGE-S7-001` |
| S8 | Analyse- und Simulationspakete | PARTIAL / SPLIT | vorhandener Analysedienst ist produktiv; fehlende Graph-Übergabe `ZEC-BL-ANALYSIS-HANDOFF-001`, echte Simulation `ZEC-BL-SIM-001`, Szenarioeditor `ZEC-BL-SCENARIO-001` |
| S9 | V4-Retention Enforce | OPEN / nachgelagert | `ZEC-BL-STORAGE-S9-001` |

Damit ist keine historische S1–S9-Stufe mehr nur implizit oder unaufgelöst.

## 4. Offenes und zurückgestelltes Master-Ledger

### ZEC-BL-CTRL-ADAPTIVE-001 – historischer gemeinsamer Adaptive-Umbrella; aktueller Scope nur Adaptive (DEFERRED)

- **Aktueller Entscheid 18.10.2026:** `DEFERRED / EVIDENCE_GAP`, `implementation_state=none`; S3 und C1 **nicht** mehr verpflichtende Children bzw. technische Vorbedingungen. Der Umbrella-Zuschnitt vom 20.09.2026 und seine Detailanforderungen bleiben im folgenden Abschnitt ausdrücklich als Provenienz erhalten, sind aber als Sequencing-Anweisung supersediert. Adaptive-Wiederaufnahme soll Aktionsraum auch abseits High-SOC und tatsächlichen Zusatznutzen prüfen; 23-Tage-Analyse und A1-Brief dauerhaft referenzieren. Kein produktives Shadow-/Lern-Coding im nächsten Block.

#### Historische Umbrella-Spezifikation / Entscheidung 20.09.2026 (Sequencing supersediert)

- **Status:** SPEC_NEEDED / OPEN; Controller-Implementierung noch nicht begonnen. Nach Nutzerentscheidung vom 22.09.2026 ist Adaptive von Fast Capture entkoppelt und folgt als eigener Spezifikationsblock nach Bereitstellung des Fast-Capture-Releases.
- **Rolle:** Roadmap-/Umbrella-Eintrag für `ZEC-BL-CTRL-S3-001`, `ZEC-BL-CTRL-001` und `ZEC-BL-CTRL-CAP-001`. Die Child-IDs bleiben eigenständig erhalten und dürfen durch die Zusammenführung nicht verschwinden.
- **Entscheidung 20.09.2026:** S3 nicht separat vorab implementieren. Saisonale Faktoren und dynamische Tagesprofile sollen mit der adaptiven Lade-/SOC-/Ertragsstrategie sowie der weichen Kapazitätsgewichtung in einem konsistenten Regelmodell zusammengeführt werden, sofern die finale Lernmodell-Übergabe dies bestätigt.
- **Pflicht vor Sourceänderung:** Es existiert nach aktueller Quellenprüfung keine weitere verlorene/finale Adaptive-Spezifikation. Der nächste Adaptive-Arbeitsschritt ist daher bewusst **Spezifikation**, nicht Suche nach einem vorausgesetzten Artefakt. Neu zu erstellen sind mindestens: Mapping-Matrix vorhandene S3-Settings → aktive Nutzervorgabe / Modellinput / deterministischer Fallback / deprecated; Abdeckung von `CTRL-001` und `CTRL-CAP-001`; konkretes Optimierungsziel und Aktionsraum; Lernzustand/Persistenz/Versionierung/Reset; Inputvertrag; Confidence/Fallback; Hardwarewechsel-/Invalidierungsvertrag; Offline-/Replay-/Shadow-/Differential-Evidenz; Safety-/Hardwaregrenzen und reproduzierbare Entscheidungsprovenienz.
- **Simulation/Evidenz:** Der spätere produktive allgemeine Counterfactual-Simulator `ZEC-BL-SIM-001` bleibt ein eigener Roadmappunkt und ist nicht zwingende Vorbedingung für diesen Block. Vor produktiver Reglerwirkung sind dennoch belastbare simulationsnahe bzw. replay-/pretrainer-/shadowbasierte Nachweise auf realen Daten erforderlich.
- **Normative Grenzen:** Die bestehende Grundinvariante „aktuell vermeidbare Einspeisung vor strategischer Ladeverteilung“ bleibt erhalten. Adaptive/gelernte Logik darf harte Safety-, SOC-, Command-, Recovery-, Cross-Charge- und Hardwareschonungsregeln nicht überstimmen.
- **Versionsklasse:** erst mit finalem Runtime-Scope festlegen; ein echter neuer produktiver Lern-/Adaptionslayer ist nach `01_ZEC_PROJECT_RULES.md` als neues Entwicklungsthema zu bewerten, eine rein statische Parameternutzung gegebenenfalls anders.
- **Exit:** Child-IDs einzeln mit Implementierungs-/Evidenzstatus reconciliert; keine exponierte S3-Einstellung bleibt unbeabsichtigt wirkungslos; Lern-/Fallback-/Recovery-Verhalten und Hardware-/Konvergenzeigenschaften sind nachgewiesen.

### ZEC-BL-CTRL-S3-001 – Saison-/Tagesprofile Completion & Effectiveness

- **Status 20.10.2026:** `IMPLEMENTED / TECHNICAL_PASS / FIELD_EFFECT_PENDING`; finale Produktionsspezifikation 19.10. freigegeben, Runtime/Settings/Tests und Opt-in/Legacy-Migration in V17.1.0 real ausgeliefert. Reale HOLD-S3-Diagnose `season_requested=sma_priority`, `season_effective=legacy_parallel`, `NOT_APPLICABLE`; natürliche Harvest-Wirksamkeit noch nicht belegt. Die folgenden 18.10.-Aussagen sind **historische Ausgangsbefunde**.

- **Aktuelle Entscheidung 18.10.2026:** `OPEN / SPEC_DRAFT`, eigenständiger nächster Funktionsscope ohne Adaptive-Abhängigkeit; Zweck/Wirksamkeit, vollständige zehn S3-Settings, Legacy-Share-/Confirm-Migration, aktuelle `sma_priority`-New-Install-Default-Falle, `VAL-014` Jahreswechsel, Timergrenzen, Registry-ProductSurface, Testmatrix und transparente Nichtanwendbarkeit in `ZEC_S3_FACHLICHE_PRODUKTIONSSPEZIFIKATION_ENTWURF_20261018.md`. Der historische Child-/Sequencingtext darunter bleibt Provenienz, ist **nicht mehr aktuell**. Vor Reglercode: finale Spezifikation und explizite Scopefreigabe.


- **Historischer Status vor V17.1.0:** OPEN
- **Historische Roadmapbindung ab 20.09.2026:** Child-Scope von `ZEC-BL-CTRL-ADAPTIVE-001`; kein separater vorgelagerter S3-Release vorgesehen.
- **Historische Herkunft:** S3 `Saison- und Tagesprofile`; Settings-/RC19-Planung und spätere Completion-Audits.
- **Aktueller V16-Befund:** Registry und Validation enthalten Kalenderfenster, Tagesprofilzeiten und gestaffelte High-SOC-Entry-Confirm-Zeiten. Für repräsentative S3-Keys existiert außerhalb Registry/Validation/Tests kein Runtime-Consumer.
- **Risiko:** UI/Config kann eine Wirksamkeit suggerieren, die der reale Regler nicht vollständig besitzt.
- **Vor Umsetzung:** reale V16-Zielwert-/State-Machine-Analyse; historische harte Zeiten/Confirm-Werte gegen Zielsettings abgleichen; Zustand/Rechnung/Wirkung/Recovery; Konvergenz und Hardwareschonung.
- **Exit:** explizit nachweisen, welche S3-Settings runtimewirksam sind; Tests für Kalender über Jahreswechsel, Tagesgrenzen, Hold-/Confirm-Übergänge und No-Regression.

### ZEC-BL-STORAGE-001 – Measurement-/SQLite-Storage-Lifecycle

- **Status:** OPEN
- **Rolle:** Parent für die historischen S4/S5/S6/S7/S9-Stufen sowie Langzeitperformance und retention-aware Backfill.
- **Grundinvariante:** keine automatische Löschung/Kompression allein aufgrund vorhandener Settings. Jede destruktive Stufe benötigt Vorschau, Protection/Coverage, Restore und klare Provenienz.

#### ZEC-BL-STORAGE-S4-001 – S4 SQLite-Pfad & report_only
- **Status:** OPEN; `implementation_state=partial`.
- SQLite ist produktive Messdatenbasis; Pfad-/Writer-/Graphfunktionen existieren. Maintenance-Settings sind vorhanden, aber der historische S4-Lifecycle ist nicht als vollständig geschlossener Maintenancevertrag nachgewiesen.
- Vor S5 ist S4 gegen reale V16-Datenbankpfade, Status-Snapshot, Inventory/Long-run und Schutz gegen Controller-Blockierung abzuschließen.

#### ZEC-BL-STORAGE-S5-001 – S5 SQLite-Enforce
- **Status:** OPEN; `implementation_state=none/placeholder settings`.
- **Recoverybeleg:** OpenAI-Export definiert S5 eindeutig als `SQLite-Enforce`.
- V16 besitzt `MEASUREMENT_DB_MAINTENANCE_MODE` und Retention-Settings/Validation, aber keinen produktiven Retention-Enforcer.
- Muss Retention/Backfill, Online-Betrieb, DB-Locking, Crashsicherheit, Vacuum-/Compaction-Strategie und Restore berücksichtigen.

#### ZEC-BL-STORAGE-S6-001 – S6 V4-Schutz, Katalog & Sicherheitsdialog
- **Status:** OPEN; `implementation_state=partial`.
- Teile der Katalog-/Coverage-/Validation-Infrastruktur existieren. Vor einer Lösch-/Kompressionsstufe muss ein vollständiger, manipulations- und crashsicherer Bestandsschutz nachgewiesen werden.
- Protection muss u. a. aktive Datei, Incident-/Forensic-/Simulation-Coverage und explizite Schutzzeiträume respektieren.

#### ZEC-BL-STORAGE-S7-001 – S7 V4 `compress_only` & Restore
- **Status:** OPEN.
- Historischer Vertrag: geschlossene `.csv` streamingbasiert komprimieren, temporäres `.csv.gz.tmp`, Flush/fsync, vollständige Dekompressions-/SHA256-/gzip-CRC/EOF-Verifikation, atomisches Rename, Manifestumschaltung, Original erst ganz am Ende löschen.
- Toolchain muss `.csv` und `.csv.gz` transparent lesen: Analyse/Replay, Backfill, Import, Diagnosepakete und relevante Branchanalyse.
- Runtime-/Betriebsereignisse benötigen einen konsistenten Rotation-/gzip-Lifecycle; deren relevante Evidenz darf nicht früher verschwinden als zugehörige Measurements.

#### ZEC-BL-S8-001 – S8 Analyse- und Simulationspakete
- **Status:** OPEN; `implementation_state=partial`, historischer Sammelpunkt.
- Der reale Datenanalysedienst/Replay-Service ist produktiv vorhanden. Der historische S8-Rest wird bewusst auf drei konkrete Nachfolger aufgeteilt:
  - `ZEC-BL-ANALYSIS-HANDOFF-001` – Graph-Selection/Evidence-Handoff an Analyse;
  - `ZEC-BL-SIM-001` – kontrafaktische Regler-Simulation realer historischer Situationen;
  - `ZEC-BL-SCENARIO-001` – allgemeiner/synthetischer Szenarioeditor.
- S8 gilt erst als vollständig geschlossen, wenn diese Aufteilung fachlich abgeschlossen oder ausdrücklich anders entschieden wurde.

#### ZEC-BL-STORAGE-S9-001 – S9 V4-Retention Enforce
- **Status:** OPEN, absichtlich nachgelagert.
- Erst nach S6/S7, real verifiziertem Restore, Coverage-/Protection-Gates und expliziter Freigabe destruktiv aktivieren.
- Retention nach Alter/Gesamtgröße muss aktive/geschützte Dateien ausnehmen und fail-closed arbeiten.

#### ZEC-BL-STORAGE-BACKFILL-001 – retention-aware Backfill/Rebuild
- **Status:** OPEN; `implementation_state=partial`.
- **Normative Invariante:** Daten, die absichtlich durch Retention entfernt wurden, dürfen durch späteres Backfill nicht stillschweigend wieder permanent hergestellt werden.
- Graph Core V3 besitzt hierfür bereits Retention-Ledger/`PURGED_BY_RETENTION` und Reapply beim Rebuild. Der Vertrag muss über V4/SQLite/Graph/Restore hinweg konsistent werden.

#### ZEC-BL-STORAGE-GRAPH-001 – automatische Graph-Retention entscheiden
- **Status:** SPEC_NEEDED / DEFERRED.
- V14 implementierte Retention-Ledger-Semantik, aber ausdrücklich keine automatische Retentiondauer, keinen Scheduler und keine automatische VACUUM-Policy.
- Vor jeder Automatisierung müssen Highres-/1-Minuten-Langzeitbedarf, Speicherbudget, Coverage und Rebuildverhalten fachlich festgelegt werden.

#### ZEC-BL-STORAGE-PERF-001 – SQLite-/Storage-Langzeitverhalten
- **Status:** OPEN / observation.
- Langzeitperformance, Größenwachstum, Retention/Backfill und seltene Langläuferepisoden evidenzbasiert beobachten. Kurze Feldsnapshots sind kein Langzeitnachweis.

### ZEC-BL-ANALYSIS-HANDOFF-001 – Graph-Auswahl an bestehenden Analyse-Service

- **Status:** OPEN.
- **Produktkette:** Status → Graph-Exploration → Analyse-Handoff → bestehender Analysedienst.
- Historische Graphplanung spezifiziert die Aktion `In Analyse untersuchen`.
- Handoff soll ein reproduzierbares Untersuchungsobjekt übertragen, mindestens Zeitraum/Selection, Zeitzone, REAL-Dataset, Guided/Free-Kontext, relevante Series/Entities, historische Version/Config/Topologie, Coverage/Evidence und optional Fokuszeitpunkt.
- Der Graph entscheidet keine Kausalität; der Analysedienst bewertet nach Analyse-Regelwerk.
- Aktuell fehlt die Aktion; `replay_web.py` ist im Startpfad primär dateibasiert.

### ZEC-BL-SIM-001 – kontrafaktische Regler-Simulation auf realen Daten

- **Status:** SPEC_NEEDED / OPEN.
- **Frage:** „Was wäre in genau dieser real stattgefundenen Situation passiert, wenn andere Regelparameter bzw. eine andere freigegebene Reglerlogik gegolten hätten?“
- Muss reale Eingangsdaten, damalige Config/Topologie, Timer/Hysterese/Latches und bekannte/nicht beobachtbare Gerätezustände transparent behandeln.
- Deterministische Ergebnisse und approximierte Annahmen müssen getrennt markiert werden.
- Zielintegration: Reality vs Simulation A/B im Graphen vergleichbar; keine Simulation darf als reale Evidenz ausgegeben werden.
- Historischer Alias: S8 `Analyse- und Simulationspakete`; Analyseanteil existiert heute, echte Counterfactual-Simulation nicht.

### ZEC-BL-SCENARIO-001 – allgemeiner Szenarioeditor

- **Status:** DEFERRED / SPEC_NEEDED.
- Synthetische frei definierte Eingangssituationen sind von `SIM-001` zu trennen.
- Erst sinnvoll, wenn Simulationskern und Parametrisierung belastbar definiert sind.


### ZEC-BL-CTRL-FASTCAP-001 – Fast Capture A400/R100

- **Status:** IN_PROGRESS / EVIDENCE_PENDING; `implementation_state=implemented`; `technical_state=TECHNICAL_BUILD_PASS`; `field_state=SHADOW_PASS_ACTIVE_NEAR_LIMIT_PASS_FULL_IDLE_PENDING`; Releasebasis `V17.0.2 / v17.0.2-20260923`.
- **Provenienz:** Pretrainer V0.5 -> V0.6.1, Freeze-Spezifikation vom 19.09.2026, V16.2.5-Revalidierung vom 22.09.2026 und reale V17.0.2-Feldevidenz vom 23.–25.09.2026. Aktive Blockautorität: `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_2_5_REVALIDATED.md`.
- **Scope:** Fast-Capture-Overlay ausschließlich für `FULL_IDLE` und `NEAR_LIMIT`; `RESERVE_UNKNOWN` bleibt im normalen Baseline-Regelpfad. Produktionskandidat A400/R100. Strategische Baseline `B` und kurzfristiger Fast-Capture-Overlay `O` sind strikt getrennte Schichten.
- **Release-/Allgemeinfeldbasis:** V17.0.2 real installiert; allgemeiner V17-Feldlauf PASS / FULL_READY. `controller_logic.py` SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031`.
- **Shadow-Evidenz:** neuer V17.0.2-V4-Pfad real verwertbar. Ein natürlicher Shadow-Lauf mit zwei Episoden ist `PASS / SHADOW_ONLY`; ein zweiter Lauf ohne Episode korrekt `NOT_EVALUABLE`. Der definierte Shadow-Gate ist damit PASS.
- **Active-Evidenz:** begrenzter Active-Rollout wurde freigegeben. Ein erster unbeaufsichtigter Lauf war wegen fehlender natürlicher Episode für Fast Capture `NOT_EVALUABLE`; ein externer Watchdog beendete ihn aufgrund eines inzwischen als False Positive identifizierten `TRANSITIONAL:LIMIT_READBACK_CONVERGENCE` und stellte `shadow` korrekt wieder her. Spätere reale Active-Daten enthalten 23.794 Active-Mode-Zeilen, 501 Zeilen mit positivem Overlay, 20 erkannte Fast-Capture-Episoden und max. Overlay 1.642 W. Für frische `NEAR_LIMIT`-Episoden liegen reale Exportreduktion, Command-Tracking, Import-Guard/Recovery und Cross-Charge-Evidenz ohne bestätigten Command-Mismatch vor.
- **Noch offen:** eine belastbare Active-`FULL_IDLE`-Episode. Fehlende natürliche Episode bleibt `NOT_EVALUABLE`, niemals synthetischer PASS.
- **Evidence-Tooling-Fund 25.09.2026:** Analyzer-Hotfix2 meldet bei langen gemischten Active-Zeitfenstern `PRIMARY_RESERVE_MISMATCH` auch in Zyklen, in denen die Fast-Capture-Rechnung wegen Night/SOC/Cross-Charge/anderen Blockern nicht anwendbar ist; Calculation-Prüfungen müssen applicability-aware werden. Zusätzlich materialisiert der Analyzer große CSVs aktuell vollständig in RAM und ist deshalb auf dem produktiven Pi für lange Historien ungeeignet. Releaseintegrierte Langzeitanalyse muss streaming/bounded-memory arbeiten oder ausschließlich auf vorher begrenzten Extrakten laufen.
- **Feldevidenzvertrag:** Zustand, Rechnung, physikalische Wirkung und Recovery getrennt. Active muss reale Exportreduktion bzw. transparent nicht bewertbare Episoden, Import-Guard/Recovery, Command-Readback/Effect, Cross-Charge und Hardwareschonung episodespezifisch auswerten.
- **Sequenzgrenze:** Adaptive-Spezifikation darf parallel zur verbleibenden Fast-Capture-Feldevidenz fortgeführt werden. Adaptive-Sourcearbeit bleibt separat freigabepflichtig und darf Fast Capture nicht stillschweigend verändern.
- **Exit:** Active-`FULL_IDLE` ausreichend beobachtet oder transparent `NOT_EVALUABLE` bei klar dokumentiertem Beobachtungsfenster; Analyzer-Anwendbarkeit und ressourcensichere Langzeitanalyse korrigiert/regressionsgeprüft; Safety, Command-Effect und Hardware-Schonung separat belegt.

### ZEC-BL-PRIMARY-SMA-FLOOR-001 – Sunny-Island Entladeuntergrenze als Capability

- **Status:** CLOSED; `implementation_state=implemented`, `field_state=REAL_FIELD_PASS` in V16.1.0.
- **Reale Vorimplementierungs-Evidenz:** SMA Register `31009` (`Lower discharge limit for self-consumption range in %`, U32/FIX0/RO) lieferte am realen Sunny Island 19 %; FC03/FC04 identisch.
- **V16.1.0 Block A:** SMA-template-spezifische, read-only Capability `current_discharge_floor_soc`; getrennte Freshness/Validity/Invalidierung; diagnostischer normalisierter `primary_usable_soc_percent`; API/Status/Readiness/Connection-Test/Measurement-V4-Evidenz.
- **Safety-Grenze:** keine Reglerwirkung; `controller_logic.py` bleibt byteidentisch zu V16.0.2. Andere Primärspeicherprofile erhalten diese Capability nicht automatisch.
- **Settings-Vertrag:** kein editierbarer Floor, kein Override, kein On/Off-Schalter, keine ZEC-Saisonkurve; generische UI-/Help-Bezeichnungen werden auf „Primärspeicher“ neutralisiert; explizite Anzeigenamen bleiben erhalten.
- **Reale Feldabnahme 20.09.2026:** Update V16.0.2 → V16.1.0 erfolgreich; Capability auf realem `modbus_template`/Sunny Island `supported=true`, `fresh=true`, `valid=true`, Floor `19.0 %`; `primary_usable_soc_percent` real vorhanden/plausibel; Feldtool-Gate `primary_storage_sma_discharge_floor_capability=PASS`.
- **Abgrenzung der Feldabnahme:** globales `/ready` blieb während der Abnahme wegen eines bestehenden `INPUT_LIMIT`-/`ACTIVE_ACCEPTANCE_LIMITED`-Zustands `false`; dies ist kein Block-A-Pfad und wird separat unter `ZEC-BL-DIAG-FIELD-001` dokumentiert.

### ZEC-BL-CTRL-USABLE-SOC-001 – Block B: strategische usable-SOC-Integration

- **Aktueller Entscheid 18.10.2026:** `SPEC_NEEDED / OPEN` als unabhängiger deterministischer B2-Scope; diagnostischer usable SOC bleibt real implementiert, strategische Runtime-Wirkung **nicht**. Ganzjährige Anwendungsfälle untersuchen, Winter ist nur ein möglicher Kontext. Kein globaler RAW-SOC-Ersatz, kein aus Discharge-Floor erfundener Charge-Headroom, keine implizite Zendure-Netzladung. Die ältere Vorgabe „mit Adaptive zusammenführen“ gilt nur als historische Provenienz und ist im Sequencing abgelöst. Zweck, Nutzen, Kontext, Policy/Arbitration, Fallback und reale Wirksamkeit vor Coding klären.


- **Status:** DEFERRED / SPEC_NEEDED; `implementation_state=none`.
- **Provenienz:** Folgeblock der SMA-Capability-Entscheidung vom 19.09.2026.
- **Ziel:** den aus realem Roh-SOC und aktueller geräteseitiger Entladeuntergrenze abgeleiteten nutzbaren Primär-SOC gezielt in Winter-/Schwachertragsstrategie verwenden.
- **Abgrenzung:** kein globaler Ersatz des Roh-SOC. FULL/IDLE, High-SOC-/Taper-Erkennung, Lade-Headroom bis 100 %, Fast Capture sowie physische Safety-/Limitentscheidungen bleiben am realen Roh-SOC bzw. Leistungszustand.
- **Voraussetzung:** mit Adaptive-/Replay-Ergebnissen zusammenführen; Zustand, Rechnung, physikalische Wirkung, Konvergenz, Recovery und Hardwareschonung vor Reglerfreigabe separat belegen.

### ZEC-BL-CTRL-CAP-001 – echte weiche Kapazitätsgewichtung

- **Aktueller Entscheid 18.10.2026:** `SPEC_NEEDED / OPEN`, eigenständig von Adaptive/High-SOC und B2; explizites `off|soft`, Default `off` als Zielvertrag (Ist derzeit `diagnostic` ohne Sollwertwirkung); keine Nenn-kWh-Quotenautomatik. Nur bei validiertem Lade-Headroom, unabhängiger Aufnahmefähigkeit, tatsächlicher Allokationsfreiheit und nachweisbarer Endzielwertwirkung. Physische Export-/Safety-/Hardwaregrenzen haben Vorrang; Datenausfall -> neutral. Historischer Child-/Pretrainer-Text darunter als Provenienz erhalten, Sequencing supersediert.


- **Status:** SPEC_NEEDED.
- **Roadmapbindung ab 20.09.2026:** Child-Scope von `ZEC-BL-CTRL-ADAPTIVE-001`; die laufende Lernmodell-/Pretrainer-Arbeit ist primärer Spezifikationsinput.
- `HARVEST_CAPACITY_WEIGHTING_MODE` ist historisch bewusst diagnostisch geblieben; keine echte Reglerwirkung vortäuschen.
- Eine neue weiche Gewichtung ist eine Reglerstrategie. Vor produktiver Wirkung ist sie mit historischen Produktivdaten über belastbare Offline-/Replay-/Pretrainer-/Shadow- bzw. simulationsnahe Evidenz zu prüfen; der spätere allgemeine Produktiv-Simulator `ZEC-BL-SIM-001` ist dafür keine zwingende Vorbedingung. Danach Differential-/Konvergenz-/Hardwareschonungsbewertung und explizite Freigabe.

### ZEC-BL-CTRL-001 – ertrags-/SOC-bewusste Ladeverteilung weiterentwickeln

- **Aktueller Entscheid 18.10.2026:** `DEFERRED / EVIDENCE_GAP` als lernender Teil unter der erhaltenen Adaptive-Historie. 23-Tage-A1-Evidenz belegt begrenzte Wirksamkeit des bestehenden High-SOC-Share-Gates, jedoch keine bewiesene Überlegenheit einer alternativen Regelung; bei Wiedervorlage Architektur jenseits High-SOC und echte Reglerstellbarkeit kritisch prüfen. Kein Coding bis erneute Nutzen-/Scopeentscheidung.


- **Status:** OPEN.
- **Roadmapbindung ab 20.09.2026:** Child-Scope von `ZEC-BL-CTRL-ADAPTIVE-001`; nicht mehr als separater späterer Block hinter `SIM-001` geplant.
- Die Grundinvariante „aktuell vermeidbare Einspeisung vor strategischer Ladeverteilung“ ist bereits produktiv implementiert und darf nicht neu erfunden werden.
- Erweiterungsraum: adaptive/lernende Ladeannahme-/Taper-Kennlinie, batteriespezifische Anpassung, erweiterte SOC-/Ertragsstrategie.
- Vor produktiver Reglerwirkung: Lernzustand/Persistenz/Reset, Confidence/Fallback, belastbare Offline-/Replay-/Pretrainer-/Shadow-/Differential-Evidenz, Konvergenz/Oszillation, Zustand/Rechnung/Wirkung/Recovery und Hardwarebelastung.

### ZEC-BL-BATCARE-001 – Battery Care / Winter- und Reserve-SOC-Erhaltung

- **Aktuelle Winterpriorität 18.10.2026:** `SPEC_NEEDED`; nach S3 möglichst zeitnah, bei übergroßem B2/C1-Aufwand **vorziehen** statt komplexe Allokationsscopes vor Winter zu erzwingen. Primärer zu prüfender Zweck: Zendure in langen Schwachertragsphasen nicht unnötig auf sehr niedrigem SOC halten; reale Nutzerbeobachtung, dass bei ca. 9 % keine autonome Nachladung beobachtet wurde, ist keine Garantie über sämtliche BMS-Modi. Saison-Policy, PV-Vorrang, explizit genehmigte optionale Netzladung, Episode, Trigger/Ziel-SOC, Hysterese, Cross-Charge-Verbot, Hardware- und Recoveryvertrag vor Sourcearbeit spezifizieren. Keine Netzladefreigabe aus B2 oder C1 ableiten. Die historische „nach Adaptive“-Bindung unten ist durch diese Entscheidung hinsichtlich Reihenfolge supersediert.


- **Status:** SPEC_NEEDED.
- **Roadmappriorität ab 20.09.2026:** unmittelbar nach `ZEC-BL-CTRL-ADAPTIVE-001`, ausdrücklich wegen der zeitnahen Winterrelevanz.
- **Wichtig:** Es existiert keine freigegebene Battery-Care-Spezifikation. Der Chat vom 11.08.2026 wird als **Brainstorming-Provenienz** erhalten, nicht als normative Entscheidung.
- Recoverter Brainstorming-Input, ausdrücklich neu zu prüfen:
  - opt-in / default-off als Idee;
  - kalendergebundene Wirksamkeit über Jahreswechsel;
  - Trigger-SOC → Ziel-SOC als echte Episode/Hysterese statt Nachregeln am Ziel;
  - mögliche Policy-/Episode-Architektur statt komplett neuem gleichrangigem Hauptmodus;
  - Safety, MIN/MAX, Command-Guards/Recovery und Cross-Charge bleiben übergeordnet;
  - bei aktiver Episode und temporärer Ladesperre eher HOLD als unbeabsichtigtes Weiterentladen;
  - offene Grundsatzfrage, ob kontrollierte Netzladung für Reserveerhaltung zulässig sein soll; niemals SMA→Zendure-Cross-Charge;
  - eigener Battery-Care-Leistungscap als mögliche Hardwareschonungsoption;
  - Restart benötigt bei echter Hysterese möglicherweise restartfeste Episode-Provenienz, die selbst niemals ein Kommando autorisiert;
  - Leap-Day-/Kalendersemantik, SOC-Freshness, Exit-Neutralisierung, Events/Measurement/Settings und No-Regression sind zu spezifizieren.
- Beispielwerte aus dem Brainstorming (z. B. 12/20 %) sind **keine allgemeinen Softwaredefaults**.

### ZEC-BL-BATTERY-SOH-001 – diagnostische reale Kapazitäts-/Alterungserkennung (NEU 18.10.2026)

- **Status:** `DEFERRED / SPEC_NEEDED`; `implementation_state=none`; eigenständige Diagnostik, **nicht** B2/C1/Adaptive oder Battery Care automatisch integriert.
- **Provenienz:** Herbst-/Adaptive-Fachgespräch vom 18.10.2026; bisheriger Hinweis auf Ladeannahme-/Taperlernen unter `ZEC-BL-CTRL-001` ersetzt keine reale Energie-/SOH-Kapazitätsbestimmung.
- **Zweck:** langfristig erkennen, ob die unter definierten und vergleichbaren Bedingungen messbare effektive Batteriekapazität abnimmt. Messpunkt (AC/Batterieseite), Wirkungsgrad, BMS-SOC-Korrekturen, Temperatur, Anfangs-/End-SOC, Mindesthub, Metadatenqualität und Unsicherheit sind vor jeder quantitativen SOH-Aussage zu klären.
- **Nichtziele:** kein unmittelbares Ändern von SOC-, Batterie-, Lade-/Entlade- oder Commandgrenzen; keine Alterungsdiagnose aus bloßer Ladeleistungs-/Taperabweichung; kein Automatik-Ersatz der Nennkapazität in C1. Erst Datentauglichkeit prüfen; bei unzureichender Evidenz `NOT_EVALUABLE`.

### ZEC-BL-MULTI-001 – echter Multi-Zendure-Command-/Regelpfad

- **Status:** DEFERRED / SPEC_NEEDED.
- Graph/Entitymodell kann mehrere Zendures darstellen. Der produktive Commandpfad ist weiterhin auf eine aktive Controller-/`DEVICE_ID`-Instanz ausgelegt.
- Echte Zielallokation, Priorität, Safety, Readback, Wirkung, Ausfall einer Unit und gemeinsame Netzkonvergenz müssen separat spezifiziert werden.

### ZEC-BL-DOC-ARCH-001 – versionsgebundene Architektur-/Historien-Dokumentation in `docs/` (NEU 19.10.2026)

- **Status 20.10.2026:** `CLOSED / V17_1_0_DOC_GATE_PASS` für erstmalige technische Umsetzung; dauerhafte Releasepflicht weiterhin aktiv. Ursprünglich `OPEN / DOC_POLICY_DEFINED` zum Beschluss 19.10. (damals noch nicht im V17.0.2-Release).
- **Zweck:** Der Releasestand muss neben ausführbarem Code die fachliche Absicht, die tatsächlich implementierten Daten-/Regler-/Safety-/Commandpfade, Designentscheidungen und deren Historie ohne Abhängigkeit von einem Chat nachvollziehbar dokumentieren.
- **Releasepflicht ab nächstem Entwicklungs-/Produktrelease:** `docs/INDEX.md`, strukturierte `docs/architecture/`, `docs/specifications/`, `docs/decisions/`, `docs/history/` als schlanke, versions-/statusgetrennte Struktur; bei relevanten Sourceänderungen betroffene As-built-/Spec-/ADR-Dokumente gemeinsam aktualisieren. Source-/Manifest-/Hash-/Fresh-extract-Prüfung und `DOC_ARCH_HISTORY_GATE` gemäß `01` § 6b und `06` § 13 einführen. Bereits veröffentlichte V17.0.2-Dateien bleiben byteidentisch.
- **Historie ausdrücklich erwünscht und pragmatisch:** Existierende historische Original-Spezifikationen/Entscheidungen bevorzugt im Original erhalten und indizieren, zuerst `ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_0_2.md`. Die im Ledger belegte V16.2.5-Revalidierungsfassung fehlt als zugängliches Original (`MISSING_ORIGINAL`), darf nicht fingiert werden. Aus realem V17.0.2-Code abgeleitete aktuelle Architektur erhält eigenen `AS_BUILT`-Status. Ältere Entscheidungen mit belegter Provenienz gern ergänzen, ohne ein vollständiges retrospektives Großprojekt zu erzwingen.
- **Gates/No-Drop:** historisch nicht auffindbares Original allein kein Releaseblocker; fehlende/inkorrekte *aktuelle* As-built-Dokumentation einer relevanten Änderung oder falsche Releasebehauptung schon. Keine neue Roadmapautorität in `docs`, `docs/ZEC_Master_Backlog.md` bleibt Snapshot. Historische Quellen nicht vor bestandenem `BACKLOG_NO_DROP_GATE` entfernen.
- **Abgrenzung:** keine aktuell genehmigte Controller-/Installer-Sourceänderung, keine eigenständige Versionsvergabe durch die Quellenpflege; Umsetzung im nächsten ohnehin anstehenden Entwicklungs-/Releaseblock statt Verzögerung von S3/B2/C1/Battery Care.

### ZEC-BL-REL-001 – repo-zentrierter/reproduzierbarer Releaseprozess

- **Status:** DEFERRED.
- Historisches Ziel: repo-zentrierter Build, reproduzierbares ZIP, weniger manuelles Kopieren, perspektivisch GitHub/GitHub Actions.
- V16.2.0 enthält weiterhin keine `.github`-Automation. Umsetzung darf bestehende Fresh-extract-, Manifest-, Hash-, Test-, Datenblatt- und Feldgates nicht abschwächen.

### ZEC-BL-LEARN-001 – Lernwerkzeug V4.2.7 auf V16-Registry/Defaults abgleichen

- **Status:** OPEN.
- Strukturintegrität des XLSX ist belegt; Dashboard enthält noch historischen „Startwert V12.8.10“.
- Werte/Bezeichnungen gegen reale V16-Registry und `config.example.json` prüfen; keine anlagenspezifischen Werte als allgemeine Defaults übernehmen.

### ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001 – Nachtfenster + Zendure-MIN_SOC darf Grid/AUTO nicht blindlegen

- **Status 20.10.2026:** `FIX_IMPLEMENTED / TECHNICAL_PASS / NATURAL_NIGHT_MIN_SOC_EXPORT_FIELD_PENDING`; `implementation_state=implemented`, V17.1.0-Fix und deterministische Regressionsfälle PASS. Historische V17.0.2-Evidenz 25.09. bleibt, der damals geltende `RELEASE_BLOCKER_NEXT_RELEASE` ist technisch erfüllt.
- **Realer Fund:** Im aktiven Nachtfenster erreicht Zendure den globalen `MIN_SOC`. `pause_fixed_night_discharge_for_reserve_soc()` ruft `soc_limit_hold(... MIN_SOC ...)` auf und liefert `False`; `run_once()` kehrt dadurch vor `refresh_grid_power_for_display()`/`read_grid_power()` und vor der normalen AUTO-Regelung zurück. Der allgemeine Grid-State altert anschließend bis `stale`. Im beobachteten Fall fror der letzte Wert ab ca. 01:24 ein und wurde im ersten Zyklus nach dem konfigurierten Nachtende 05:30 wieder aktualisiert.
- **Control-Impact:** Der Defekt ist nicht nur UI-/Diagnosekosmetik. Entsteht bei `night_active && Zendure_SOC <= MIN_SOC` realer PV-Überschuss/Export, wird dieser im betroffenen Pfad nicht neu eingelesen und kann daher keine Zendure-Ladung auslösen. Das verletzt im betroffenen Zeitfenster die Invariante „aktuell vermeidbare Einspeisung vor strategischer Ladeverteilung“.
- **Abgrenzung:** `MIN_SOC` bleibt harte Entladegrenze und darf keine weitere Zendure-Entladung erlauben; Laden bei realem Export muss dagegen weiterhin möglich sein, sofern MAX_SOC, Command-, Cross-Charge- und sonstige Safety-Grenzen es erlauben. Der Primärspeicher-SOC ist kein Trigger dieses Fehlers. Fast Capture ist nicht ursächlich; im realen Incident war Fast-Capture-Wirkung 0 W.
- **Zielkorrektur:** Nacht-MIN_SOC darf die Entladung neutralisieren, aber nicht Grid-Telemetrie und exportseitige AUTO-Ladereaktion blindlegen. Der genaue Implementierungsweg ist im nächsten Release-Scope source-seitig zu bestimmen; eine reine Display-Refresh-Korrektur reicht **nicht**, wenn der AUTO-Ladepfad weiterhin vorzeitig verlassen wird.
- **Pflichttests:** mindestens (1) Nacht+MIN_SOC+Netzbezug => keine Entladung/korrekte Neutralisierung; (2) Nacht+MIN_SOC+PV-Export => frische Grid-Evidenz und zulässige Ladeentscheidung; (3) Wechsel Import↔Export bei MIN_SOC; (4) Nachtende 05:30/konfiguriertes Ende ohne Latch; (5) MAX_SOC-/Cross-Charge-/Command-Guard-No-Regression; (6) Status/Measurement/Reason bleiben aktuell und konsistent.
- **Exit:** Sourcefix + fokussierte Regression + vollständige Releasegates; reale Feldbeobachtung bei passender Low-SOC-/Nachtkonstellation oder ausdrücklich dokumentiertes `NOT_EVALUABLE`, falls die natürliche physische Exportepisode vor Release nicht entsteht. Technische Regression darf dadurch nicht entfallen.

### ZEC-BL-GRID-SMA-OBIS-001 – SMA-Speedwire-/OBIS-Parser strukturell härten

- **Status 20.10.2026:** `FIX_IMPLEMENTED / TECHNICAL_PASS / NATURAL_REOCCURRENCE_MONITORING`; `implementation_state=implemented`, V17.1.0 strukturierter Speedwire-/OBIS-Parser mit Negativtests PASS, real frische SMA-Grid-Werte im HOLD. Historischer V17.0.2-Fund bleibt dokumentiert; seine exakte Extremwertursache nicht rückwirkend als bewiesen behaupten.
- **Realer Fund:** Wiederholt tritt exakt `-1.730.098,8 W` als dekodierter Netzleistungsrohwert auf. `GRID_POWER_PLAUSIBILITY_MAX_ABS_W=30000` verwirft ihn korrekt, sodass der Extremwert nicht in AUTO-Regelung oder Glättung eingeht.
- **Bestätigter Sourcefehler:** V17.0.2 sucht die Gesamtwirkleistungs-OBIS-Kennungen `00 01 04 00` und `00 02 04 00` per globaler Bytefolgensuche im vollständigen UDP-Datagramm und liest die folgenden vier Bytes als Wert. Damit werden Speedwire-/Protokollstruktur, deklarierte Länge, echte OBIS-Recordgrenzen und 4-/8-Byte-Werttypen nicht ausreichend als Parservertrag erzwungen. Eine OBIS-ähnliche Bytefolge innerhalb eines anderen Payloadwertes kann dadurch prinzipiell fehlinterpretiert werden.
- **Topologie:** Im realen Netz existieren zwei SMA-Messgeräte: der für ZEC ausgewählte Sunny Home Manager mit integriertem Hausanschlusspunktzähler sowie ein zweiter Energy Meter für die drei Zaun-Wechselrichter. Die Seriennummernselektion bleibt erforderlich, ersetzt aber keine strukturelle Frame-/OBIS-Validierung.
- **Entscheidung 25.09.2026:** Ein 72-h-Raw-Frame-Auditor ist **keine Vorbedingung** für den Fix. Die Parserdefizienz ist unabhängig vom exakten historischen Raw-Frame reparaturwürdig. Ob genau der wiederkehrende Wert `-1.730.098,8 W` ausschließlich aus dieser Defektklasse stammt, bleibt bis zur Nachbeobachtung eine offene Kausalitätsdetailfrage.
- **Zielkorrektur:** SMA-/Speedwire-Frame und Protokolltyp strukturell validieren; Geräteidentität sauber lesen; OBIS-Datensätze sequentiell an Recordgrenzen dekodieren; 4-/8-Byte-Werttypen und Längen respektieren; unbekannte zusätzliche OBIS-Felder robust überspringen; verkürzte, inkonsistente oder fremde Frames verwerfen; konfigurierte Seriennummernselektion beibehalten; 30-kW-Plausibilitätsfilter als zweite Schutzschicht unverändert erhalten.
- **Pflichttests:** (1) bekannte valide Home-Manager-Telegramme liefern identische korrekte Leistung; (2) wechselnde OBIS-Reihenfolge/zusätzliche Felder; (3) `00 01 04 00` bzw. `00 02 04 00` innerhalb eines 8-Byte-Payloads erzeugt keinen False Match; (4) falsche Protokoll-ID => Reject; (5) Truncation/Längenfehler => Reject; (6) beide realen SMA-Seriennummern => nur ausgewählter Home Manager aktualisiert Grid Power; (7) Sentinel-/ungültige Werte; (8) Plausibilitätsfilter bleibt wirksam.
- **Feldevidenz nach Fix:** normaler SMA-Netzleistungspfad muss stabil bleiben; bestehende Logs auf erneutes Auftreten des Extremwertes beobachten. Verschwindet er über ein repräsentatives Betriebsfenster, stützt dies die konkrete Root-Cause-Zuordnung. Tritt er erneut auf, wird erst dann ein gezielter Raw-Frame-Capture notwendig.
- **Exit:** strukturierter Parser implementiert, fokussierte + vollständige Regression PASS, reale normale Netzleistungsmessung bestätigt; kein nächster Produktrelease mit unverändertem globalem Byte-Search-Parser.

### ZEC-BL-DIAG-001 – aktuelle Fehler vs. historisches `last_error`

- **Status:** OPEN / observation-hardening.
- Diagnosesemantik weiter schärfen, damit historische Fehler nicht als aktueller aktiver Incident erscheinen.
- **Realfund 25.09.2026:** Während `NIGHT_RESERVE_STOP`/`SOC_LIMIT_HOLD:MIN_SOC` und gleichzeitig stale Grid-Telemetrie zeigte die Statusoberfläche `HOLD – Grund: Netzleistung nahe 0 W`. Reason-Auflösung muss aktuelle operative Limiter-/Target-Final-Gründe gegenüber generischem/sticky HOLD-Kontext korrekt priorisieren und darf einen stale Netzleistungswert nicht als aktuellen fachlichen HOLD-Grund suggerieren.

### ZEC-BL-CMD-OBS-001 – Command-/Readback-Feldevidenz

- **Status:** OPEN / evidence.
- Command Effect, Readback, Resync und physikalische Wirkung weiter mit realen Episoden belegen. Zeitliche Reihenfolge allein ist kein Kausalitätsnachweis.

### ZEC-EV-OFFGRID-001 – kontrollierter realer Offgrid-Feldtest

- **Status:** EVIDENCE_PENDING / DEFERRED.
- Die Power-Semantik trennt `gridOffPower` von Hausnetz-/Packfluss und ZEC verändert die Offgrid-Konfiguration nicht.
- Historisch ausdrücklich offen: ungefährlichen Verbraucher am Offgrid-Ausgang real testen und belegen, dass Offgrid-Last nicht als Hausnetzentladung, Cross-Charge oder fehlgeschlagene Neutralisierung interpretiert wird.

### ZEC-BL-PRIMARY-METADATA-001 – technische Primärspeicher-Metadaten automatisch aus Gerät/Template

- **Status:** SPEC_NEEDED.
- **Provenienz:** Status-GUI-/V16.2.0-Scope vom 20.09.2026.
- **Ziel:** technische Eigenschaften wie nutzbare/nominale Kapazität, maximale Ladeleistung und maximale Entladeleistung sollen – soweit das konkrete Gerät sie belastbar bereitstellt – perspektivisch über Geräteprofile/Templates automatisch erfasst werden, statt dauerhaft manuell gepflegt werden zu müssen.
- **Vor Umsetzung zu entscheiden:** Source-vs.-manueller Fallback/Override-Vertrag, Freshness/Validity, Gerätewechsel/Invalidierung, Einheiten und Verhalten bei nur teilweise verfügbaren Capabilities.
- **Abgrenzung:** V16.2.0 implementiert ausschließlich optionale manuelle Status-/Diagnose-Fallbackwerte; daraus entsteht keine Reglerwirkung.

### ZEC-BL-DEP-002 – persistente Installationsreports

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.4 / v16.2.4-20260921`.
- **Umsetzung V16.2.4:** Der Installer schreibt den maschinenlesbaren Installationsreport atomar und timestamped persistent unter `/home/pi/Downloads`; `/tmp/zec_v16_2_4_install_report.json` bleibt ausschließlich Kompatibilitätskopie.
- **Feldtool-Vertrag:** Ein explizites `--install-report` gewinnt immer. Ohne expliziten Pfad wird der neueste persistente releasespezifische Report bevorzugt; nur wenn keiner vorhanden ist, darf die definierte `/tmp`-Kompatibilitätskopie verwendet werden.
- **Integrität:** Reportformat, Release-/Buildidentität und Installationsmodus werden fail-closed validiert. Beim Update wird die im Report referenzierte reale Rollback-Datei weiterhin über Pfad, Größe und SHA256 verifiziert.
- **Abgrenzung:** keine Änderung an Rollback-, Supportcapture-, Installationszustands-, Regler-, Command-, Safety- oder Recoverysemantik.
- **Technischer Exit V16.2.4:** vollständige Regression `1123 Tests + 698 Subtests PASS` über 150 Testdateien; identischer Lauf mit `ResourceWarning=error`; Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Artefakt-Transaktion, Datenblatt-, Build-Evidence-, Manifest-/Hygiene- und Fresh-extract-Gates PASS.
- **Realer Exit 22.09.2026:** Update V16.2.3 → V16.2.4 erfolgreich; persistenter Report `/home/pi/Downloads/zec_v16_2_4_install_report_20260921_232843.json` real gefunden und vom Feldtool ohne explizites `--install-report` bevorzugt; Report-SHA256 `778b0716fba2c79ff6f77f26e11b818fb08cee96b9e0630f7cbf8624280b5260`; reale Rollback-Datei SHA256 `8e541acdc71fffb4e97bb9ec0428eab575eba526eeacf4d1f32c28b0fbf77150`; `rollback_backup_integrity=RELEASE_BACKUP_EXACT`; Gesamtfeldlauf PASS. Damit CLOSED / REAL_FIELD_PASS.

### ZEC-BL-DEP-003 – V16.2.1 Manifest-/Deploymentvertrag und einmalige Fehlerbehandlung

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; technischer Fix ab V16.2.2, realer Exit mit `V16.2.3 / v16.2.3-20260921`.
- **Realer Fund 21.09.2026:** V16.2.1 bestand Package-/Fresh-Extract-Gates, enthielt aber fünf `.pytest_cache`-Dateien im Source-Manifest. Der Installer schließt `.pytest_cache/` beim Update/Fresh-Install bewusst aus und prüfte anschließend das unveränderte vollständige Manifest im Ziel; dadurch brach der reale Updatepfad V16.2.0 → V16.2.1 nach Backup und Copy mit fehlenden Manifestdateien ab.
- **Rollback-Evidenz:** automatischer Update-Rollback stellte V16.2.0 wieder her; `/health` meldete V16.2.0 alive=true, `/ready` true und keine failed_checks. V16.2.1 erhält daher keinen Real-Field-PASS.
- **Zweiter bestätigter Befund:** `set -E` vererbt den `ERR`-Trap in Subshells. Ein Fehler im Manifest-Subshell konnte Supportcapture/Rollback dort und anschließend nochmals im Hauptprozess auslösen; dies erklärt die zwei Diagnosepakete des realen Fehlversuchs.
- **V16.2.2-Scope:** volatile Cache-/Bytecode-/Runtime-DB-Artefakte fail-closed aus Release-Tree und aktuellem Manifest ausschließen; gemeinsamer Manifestverifier für Paket und Ziel; Paket-Preflight prüft Release-Hygiene vor jeder Mutation; reales rsync-Update und Fresh-Install werden gegen denselben Manifestvertrag regressionsgetestet; nur der Haupt-Shellprozess darf Supportcapture/Rollback finalisieren.
- **Abgrenzung:** keine UI-, Regler-, Command-, Safety- oder Recoverysemantikänderung; `controller_logic.py` muss byteidentisch bleiben. `ZEC-BL-DEP-002` wird in diesem Hotfix nicht stillschweigend mit umgesetzt.
- **Pre-Freeze-Evidenz:** vollständige Regression `1106 Tests + 698 Subtests PASS`, identischer Lauf mit `ResourceWarning=error`, Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Rollback, Datenblatt und reale rsync/Manifest-Regression für Update/Fresh PASS. Das neue Hygiene-Gate erkannte ein während QA entstandenes Runtime-SQLite-Artefakt fail-closed; dieses wurde vor Manifest/Paketbau entfernt.
- **Technical Exit:** paketierter Fresh-Extract ohne volatile Artefakte, Manifest/Hygiene, vollständige Regression `1106 + 698`, identischer ResourceWarning-Lauf, statische Gates, Deployment-Harness und Root-Rollback PASS.
- **Realer Exit 21.09.2026:** V16.2.3-Preflight und Update V16.2.0 → V16.2.3 erfolgreich; konsolidierte Feldabnahme insgesamt PASS. Exaktes Rollback-Backup SHA256 `d860ad8d3af8cdd31d6e568357509f6320258c2ef5d79e699e1a33e11ed8d518`. Damit ist der Manifest-/rsync-/Single-Finalization-Vertrag real bestätigt.

### ZEC-BL-UI-STATUS-002 – V16.2.0 Status-/SOC-Day-/Mobile-Settings-Härtung

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.0 / v16.2.0-20260920`.
- **Provenienz:** reale V16.1.0-Nutzung / Nutzerbefunde vom 20.09.2026.
- **Scope:** Primärspeicher-SOC-Ring-Layout; Tageswechsel-sicherer SOC-Day-Cache; „Jetzt“-Markierung nur am aktuellen Tag; mobile Settings-Suche mit erreichbarer Commit-Leiste; richtungsabhängige Restenergie und Leistungsbalken für beide Speicher; optionale Primärspeicher-Fallbackwerte für Kapazität und maximale Entladeleistung.
- **Safety:** reine UI-/Diagnose-/Settings-Metadaten-Erweiterung; `controller_logic.py` bleibt byteidentisch; neue Primärspeicherwerte besitzen keine Reglerwirkung.
- **Technischer Exit:** vollständige Regression `1098 Tests + 698 Subtests PASS`, identischer Lauf mit `ResourceWarning=error`, Browser-/Compile-/Deployment-/Datenblatt-/Fresh-extract-Gates PASS.
- **Realer Exit 20.09.2026:** Update V16.1.0 → V16.2.0 erfolgreich; Installer `ready=true`; konsolidierte read-only Feldabnahme insgesamt PASS mit allen 26 ausgewiesenen Checks PASS, einschließlich Releaseidentität, Controller-Readiness, Graph-/SOC-Day-/Settings-Verträgen, Installationsreport, Rollback-Backup und Performance-Budgets.

### ZEC-BL-DEP-004 – kanonischer maschinenlesbarer Build-Evidence-/Preflight-Vertrag

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.3 / v16.2.3-20260921`.
- **Fund 21.09.2026:** realer V16.2.2-`--preflight-only`-Lauf auf V16.2.0 brach vor jeder Produktivmutation ab, weil der Installer nicht vorhandene Freitextmarker in den vorhandenen grünen QA-Dateien verlangte. Diagnosebundle belegte `installed_identity=V16.2.0` und `rollback_result=not_required_preflight`.
- **Root Cause:** Build-Erzeugung und Installer hatten keinen gemeinsamen maschinenlesbaren Evidence-Vertrag; human-readable QA-Texte wurden als implizite Parser-API missbraucht.
- **V16.2.3-Scope:** `ZEC_BUILD_EVIDENCE_V1`; gemeinsamer `deployment_contract.py verify-build-evidence`; Installerdelegation ohne Freitextparsing; fail-closed Release-/Count-/ResourceWarning-Prüfung; finales Paketgate muss den Evidence-Teil des echten Installer-Preflights aus dem Fresh Extract ausführen.
- **Abgrenzung:** keine UI-, Regler-, Command-, Safety- oder Recoveryänderung; `controller_logic.py` bleibt byteidentisch. `ZEC-BL-DEP-002` bleibt separat offen.
- **Realer Exit 21.09.2026:** mutationsfreier V16.2.3-Preflight PASS; anschließendes Update V16.2.0 → V16.2.3 erfolgreich; Installationsreport SHA256 `7f727963537ca81c78184bdd28933ce24f5654f78a3c86126e5f0e66a98097ff`; Feldartefakt SHA256 `cd82a345765186104b9b6fbb485e69d0f43740f83d8bf81f70d104c95db5eab7`; Feldlauf insgesamt PASS. Damit ist der maschinenlesbare Build-Evidence-/Preflight-Vertrag real bestätigt.

### ZEC-BL-UI-SETTINGS-001 – Settings-Webmodell unterdrückt aktuelle produktive Releasefelder

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.4 / v16.2.4-20260921`.
- **Realer Fund 21.09.2026:** Nach erfolgreichem V16.2.3-Update fehlten `SECOND_BATTERY_CAPACITY_WH` und `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` auf der realen Settings-Webseite. Bei der Sourceverifikation wurde zusätzlich bestätigt, dass auch der produktive Aktivierungsschalter `SECOND_BATTERY_INTEGRATION_ENABLED` vom selben historischen S1/RC19-Filter betroffen war.
- **Root Cause:** Provenienzmetadaten `release_stage`/`origin` wurden fälschlich als Produkt-Surface-Autorität verwendet.
- **Umsetzung V16.2.4:** `SettingsRegistry` trennt explizit `SurfaceState` (`operational`/`target_only`) und Hardware-/Konfigurations-`Applicability`. `settings_model.py` und First-Install-Persistenz verwenden dieselbe zentrale operative Surface-Autorität. Nichtlegacy-Settings müssen explizit klassifiziert sein; unbekannte aktive/visible Kandidaten schlagen fail-closed fehl.
- **Hardwarevariabilität:** `SECOND_BATTERY_INTEGRATION_ENABLED` bleibt als operativer Einstieg unabhängig vom aktuellen Primärspeicherzustand erreichbar. Untergeordnete Primärspeicherfelder sind produktiv freigegeben, werden aber abhängig vom aktuellen Browser-Draft der Integration sichtbar. Die Topologie kann 1 oder 2 Zendure-Entities ausweisen; daraus entstehen ausdrücklich keine zweite Zendure-Commandkonfiguration und keine Freigabe von `ZEC-BL-MULTI-001`.
- **Negativvertrag:** spätere S3/S4/S6/S7-Zielsettings bleiben `target_only` und dürfen auch bei passender Hardware nicht produktiv exponiert werden.
- **Feldtool-Lücke geschlossen:** Die V16.2.4-Feldabnahme prüft live `/settings/model`, die drei erwarteten Primärspeicher-Controls, deren Surface-/Applicability-Vertrag sowie Negativproben für target-only Settings.
- **Safety:** keine Regler-, Command-, Safety- oder Recoveryänderung; `controller_logic.py` bleibt byteidentisch.
- **Realer Exit 22.09.2026:** konsolidierter V16.2.4-Feldlauf PASS; `primary_storage_settings_surface=PASS`; `SECOND_BATTERY_INTEGRATION_ENABLED`, `SECOND_BATTERY_CAPACITY_WH` und `SECOND_BATTERY_MAX_DISCHARGE_POWER_W` jeweils real `available=True`, `editable=True`, `applicable=True`, `surface_state=operational`. Manuelle UI-Prüfung bestätigte Kapazitätsvalidation und die daraus resultierende kWh-/Maximalleistungsanzeige auf der Sunny-Island-Karte. Damit CLOSED / REAL_FIELD_PASS.

### ZEC-BL-UI-SETTINGS-MOBILE-001 – Mobile Settings ohne horizontalen Content-Overflow

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; `technical_state=TECHNICAL_BUILD_PASS`; Release `V16.2.5 / v16.2.5-20260922`.
- **Implementierungsstand 22.09.2026:** responsiver Viewport-/Intrinsic-Width-Vertrag umgesetzt; Input/Einheit stapeln auf kleinen Viewports, lange Keys/Fehler/Meta-Pills brechen, Pinch-Zoom bleibt zulässig aber nicht erforderlich. Fokussierte UI-/Diagnose-Regression und vollständige Build-/Fresh-extract-Gates PASS.
- **Reale Feldabnahme 22.09.2026:** auf realem iPhone im Expertenmodus geprüft. Input, Einheit, langer technischer Key, Validierungsfehler, Meta-Pills, Standard/Experte-Umschalter und die feste Änderungsleiste bleiben innerhalb des nutzbaren Settings-Viewports erreichbar; der gezeigte absichtlich ungültige Draftwert wird vollständig und ohne horizontal abgeschnittenen Content dargestellt. Kein Commit des Testwerts.
- **Realer Fund 22.09.2026:** Auf dem iPhone laufen Settings-Controls, Einheit, Validierungsbox und teilweise der Standard/Experte-Umschalter rechts über den Viewport hinaus. Die Seite ist absichtlich nicht horizontal scrollbar; dadurch wird Inhalt abgeschnitten und ist nicht erreichbar.
- **Root-Cause-Richtung:** der mobile Scrollcontainer ist auf vertikale Interaktion begrenzt (`overflow-x:hidden` / vertikaler Touch-Pfad), während einzelne Settings-Layoutzeilen eine Mindest-/Intrinsic-Breite oberhalb des Viewports behalten.
- **Zielvertrag V16.2.5:** Settings-Content muss bei 320/375/390/430 CSS-Pixel vollständig innerhalb des Viewports bleiben; horizontales Scrollen oder Pinch-Zoom sind kein Ersatz für responsives Layout. Lange Keys, Fehlermeldungen, Einheiten, Meta-Pills und Standard/Experte-Umschalter müssen umbrechen bzw. in eine mobile Layoutvariante wechseln. `scrollWidth <= clientWidth` ist als Regression-Gate abzudecken.
- **Abgrenzung:** keine Settings-Semantik-, Validation-, Persistenz- oder Regleränderung.

### ZEC-BL-UI-STATUS-003 – Speicherstatuskarten-Konsolidierung und reale Layout-Completion

- **Status:** OPEN / REAL_FIELD_PASS_WITH_UI_FOLLOWUP; `implementation_state=implemented_v16_2_5_plus_followup`; `technical_state=TECHNICAL_BUILD_PASS`; Releasebasis `V16.2.5 / v16.2.5-20260922`.
- **Standardkartenvertrag:** große signierte Istleistung ohne zusätzliche Richtungsbeschriftung; einteiliger Leistungsbalken Laden grün links→rechts / Entladen orange rechts→links; W/kW relativ zur belastbaren Maximalleistung ohne Prozentlabel; `Ladegrenze`/`Entladegrenze`; `Noch ladbar`/`Noch entladbar` als SOC-Prozentpunkte plus kWh nur bei belastbarer Kapazität.
- **Kapazitätspriorität:** reale/source-seitige usable/effective Kapazität → belastbare Geräte-/Templatekapazität → manueller Fallback → keine kWh. Keine scheinpräzisen Ersatzwerte.
- **V16.2.5 real bestätigt:** Desktop und reales iPhone zeigen keine Footer-/Content-Überdeckung; `Noch ladbar` steht lesbar in der rechten Detailspalte, Leistungsbeschriftung/-balken bleiben lesbar. Eine reale aktive `HIGH_SOC_CHARGE_LIMITED`-/Ladeannahme-Warnung wurde am 22.09.2026 sowohl eingeklappt als auch ausgeklappt beobachtet: Warnung bleibt sichtbar, Details sind lesbar und auf-/zuklappbar, regulärer Inhalt wird nicht überdeckt.
- **Neues reales UX-Finding 22.09.2026:** Bereits die eingeklappte V16.2.5-Warnungsbox vergrößert die Speicherkarte und dadurch die gesamte obere Kartenreihe deutlich. Das widerspricht dem erreichten Ziel hoher vertikaler Informationsdichte, obwohl die funktionale Warnungs-Evidenz selbst PASS ist.
- **Freigegebener Follow-up-Vertrag:** aktiver Warnzustand höhenneutral als Warning-Chip im vorhandenen Kartenkopf, vorzugsweise mit fachlicher Kurzbezeichnung (`Begrenzt`, `Ladeannahme` o. ä.); bei mehreren aktiven Warnungen aggregierter Hinweis/Anzahl. Details werden außerhalb des normalen Kartenflows geöffnet: Desktop als an der Karte verankertes nicht-layoutverschiebendes Popover, mobil als touch-taugliches Bottom-Sheet bzw. kompaktes Modal. Schließen der Details darf die aktive Warnung nicht verbergen. Hover allein reicht nicht; Touch/Tastatur müssen funktionieren. Keine schwebende Box darf regulären Karteninhalt verdecken.
- **Sequencing-/Releaseentscheidung:** Für diesen Follow-up wird kein eigener Hotfix-Zyklus erzwungen. Er ist verbindlicher isolierter Frontend-Subscope des nächsten ohnehin anstehenden Releases und blockiert die Fast-Capture-vs.-Adaptive-Entscheidung nicht.
- **Expert-Slice:** der V16.2.4-Primärspeicher-Slice `Strategie & Diagnose` bleibt erhalten; der vollständige kartenübergreifende Expertenmodus bleibt unter `ZEC-BL-UI-STATUS-EXPERT-001` offen.
- **Safety:** reine UI-/Diagnosedarstellung; keine Regler-, Command-, Safety- oder Recoveryänderung; bis zu einem Controllerrelease-spezifisch anders freigegebenen Scope bleibt die bestehende Reglersemantik unberührt.
- **Follow-up-Exit:** eingeklappte aktive Warnung erzeugt keine zusätzliche Karten-/Gridhöhe; geöffnete Details verschieben das Seitenlayout nicht; Warnexistenz bleibt permanent sichtbar; Desktop/Mobile/Keyboard/Touch und Mehrfachwarnungsfall regressionsgetestet.

### ZEC-BL-DIAG-OWNER-001 – Produktive Instance-Owner-Evidenz im Statussnapshot

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; `technical_state=TECHNICAL_BUILD_PASS`; Release `V16.2.5 / v16.2.5-20260922`.
- **Implementierungsstand 22.09.2026:** die fünf Instance-Owner-Felder sind im allgemeinen `ControllerState.snapshot()` ergänzt; Lock-/Owner-Semantik unverändert. Fokussierte Regression sowie vollständige Build-/Fresh-extract-Gates PASS.
- **Realer Exit 22.09.2026:** produktiver Snapshot bestätigt `INSTANCE_OWNER_ACTIVE=True`, `INSTANCE_OWNER_PID=39159`, `INSTANCE_OWNER_BUILD_ID=v16.2.5-20260922`. Damit ist der V16.2.4-Falschzustand `Owner nicht bestätigt` im realen V16.2.5-Pfad behoben, ohne Änderung der Instance-Lock-/Single-Owner-Semantik.
- **Realer Fund 22.09.2026:** Die produktive V16.2.4-Instanz läuft gesund und `ready=true`, aber `Controller & Schnittstellen` zeigt `Owner nicht bestätigt`, `Prozess —`, `Build —`. Der Feldsnapshot bestätigt `instance_owner_active=False`, `instance_owner_pid=None`, leere Build-ID.
- **Sourceverifikation:** `ZendureController.py` setzt Owner-Status/PID/Build-ID beim erfolgreichen Instance-Lock; `readiness_snapshot()` exportiert sie. Der allgemeine `ControllerState.snapshot()`-Pfad für `/status-view-data` übernimmt diese Felder jedoch nicht vollständig, wodurch ein falscher Diagnosezustand entsteht.
- **Zielvertrag V16.2.5:** Instance-Owner-Evidenz muss in allen relevanten Status-/Readiness-Snapshots konsistent sein; die UI darf eine real bestätigte produktive Instanz nicht als unbestätigt darstellen. Keine Lock-/Single-Owner-Semantikänderung, nur Snapshot-/Diagnosekonsistenz.
- **Exit:** Regression über `/health`, `/ready`, `/status` und `/status-view-data` bzw. deren reale Datenpfade; produktive Ownerdaten konsistent, fehlende Ownerdaten weiterhin ehrlich als unbestätigt dargestellt.

### ZEC-BL-GRAPH-GAP-001 – echte Datenlücken unterbrechen numerische Graphlinien

- **Status:** OPEN / REAL_FIELD_PASS_WITH_UI_FOLLOWUP; `implementation_state=partial`; `technical_state=TECHNICAL_BUILD_PASS`; Releasebasis `V16.2.5 / v16.2.5-20260922`.
- **V16.2.5 real bestätigt:** bestätigte Nicht-AVAILABLE-Evidence erzeugt renderseitige `null`-Breaks; über bekannter Controller-Downtime ist die numerische Linie tatsächlich sichtbar unterbrochen. Es entstehen keine synthetischen Messwerte. Damit ist der primäre Graph-Gap-Fix real PASS.
- **Verbleibender Interaktionsfehler:** Beim Hover/Klick innerhalb einer bestätigten Lücke zeigt das synchronisierte Cursor-/Tooltip-Overlay weiterhin Werte des nächsten realen Messpunkts außerhalb der Lücke; der Inspector liefert zwar keine Messwerte, rendert bei `actual_ms=null` aber `01.01.1970, 01:00:00` statt eines ehrlichen Gap-/Empty-States.
- **Sourceverifikation:** `syncPlugin` und `updateCursorCards()` verwenden `nearestDatasetPoint()`/`nearestIndex()` ohne Evidence-Gap-Gate; die `y:null`-Breaks verhindern die Linie, nicht das Nearest-Sample-Overlay. `renderInspector()` wandelt `null` über `Number(null)` in `0` und erzeugt damit den Epoch-Zeitwert.
- **Follow-up-Zielvertrag:** Innerhalb bestätigter `GAP`/`NOT_INSTRUMENTED`/`PURGED_BY_RETENTION`-Intervalle dürfen Cursor, Tooltip, Marker und Inspector keinen realen Nachbarpunkt an den Cursorzeitpunkt projizieren. Stattdessen Gap-/Empty-State ohne synthetische Werte; außerhalb bestätigter Lücken bleibt die bisherige Nearest-Interaktion unverändert. Normale Sampling-Jittertoleranz darf nicht unnötig in Gap-Semantik umklassifiziert werden.
- **Sequencing-/Releaseentscheidung:** Der Restfehler ist ein isolierter UI-/Interaktionsdefekt und kein Daten-, Regler-, Command-, Safety- oder Recoveryfehler. Wegen der real bereits korrekten Linienunterbrechung wird kein eigener V16.2.6-Hotfix-Zyklus erzwungen. Der Fix ist verbindlicher, eigenständig regressionsgeprüfter Frontend-Subscope des nächsten ohnehin anstehenden Releases und blockiert die Fast-Capture-vs.-Adaptive-Entscheidung nicht.
- **Exit:** Query-/Frontend-Regression mit Vorher-/Nachherpunkten und echtem Gap; Linie, Hover/Cursor, Tooltip, Inspector und Coverage/Evidence semantisch konsistent; im nicht verfügbaren Intervall keine Nearest-Sample-Werte oder Marker am Cursor; kein Epoch-Nullzeit-Fallback; außerhalb des Gaps unveränderte Interaktion.

### ZEC-BL-UI-STATUS-EXPERT-001 – vollständiger Statusseiten-Experten-/Diagnosemodus

- **Status:** OPEN; `implementation_state=partial`; Roadmapposition nach V16.2.4 weiterhin nicht automatisch festgelegt.
- **V16.2.4-Stand:** `UI_MODE=standard|expert` steuert nun auf der Primärspeicherkarte einen echten sichtbaren Superset-Slice. Im Expertenmodus werden `Strategie & Diagnose` mit Harmonisierung, Harvest/Strategie, diagnostischem usable SOC und Quellenstatus kompakt gerendert; die Standardkarte bleibt unverändert schlank.
- **Vertrag:** Expert bleibt Superset von Standard. Kritische Warnungen und Standardinformationen verschwinden nicht; der Modus ändert niemals Regler-/Command-/Safety-Semantik und erzeugt keine neue externe I/O.
- **Weiter offen:** der kartenübergreifende Completion-Scope mit vertieftem Status-Snapshot, Freshness/Validity, Reason-/Limiter-/Sollwertpipeline, Command-Effect/Readback/Resync, Timing/Runtime, Events und kontextbezogenen Diagnosezugängen. Nur vorhandene belastbare Daten dürfen exponiert werden.
- **Interaktion/Privacy:** technische Details benötigen erkennbare responsive Zugänge; Hover allein reicht nicht. Secrets und rohe vertrauliche Konfiguration bleiben ausgeschlossen.
- **Exit des Gesamtpunkts:** `UI_MODE` wirkt nachweisbar kartenübergreifend; Expert ist vollständiges Superset; responsive/Accessibility-/Regressionstests decken beide Modi und Moduswechsel ab.

### ZEC-BL-DIAG-FIELD-001 – Feldabnahme-Tool an Release- und Readinessvertrag synchronisieren

- **Status:** CLOSED / REAL_FIELD_PASS; `implementation_state=implemented`; Release `V16.2.0 / v16.2.0-20260920`; **kein eigener Hotfix-Release**.
- **Fund V16.1.0 Realfeldabnahme 20.09.2026:** `tools/v16_field_acceptance.py` prüfte bei `SUPPORTED_UPDATE` noch hart auf V16.0.1 / `v16.0.1-20260915`, obwohl der V16.1.0-Installer korrekt ausschließlich V16.0.2 / `v16.0.2-20260917` als Updatequelle akzeptierte. Dadurch entstand ein falsches `install_report=FAIL` trotz realem Report `status=ok` für V16.0.2 → V16.1.0 und exakt verifiziertem Rollback-Backup.
- **Zweiter historischer Vertragsunterschied:** das Feldtool verlangte im Normalpfad strikt `ready=true`, während der Installer bereits eine gemeinsame releasespezifische READY/TRANSITIONAL/REJECT-Klassifikation besaß.
- **Umsetzung V16.2.0:** erwartete Updatequelle wird aus dem Installer-/Releasevertrag abgeleitet; Feldtool und Installer verwenden dieselbe sichere Readiness-Akzeptanzklassifikation, ohne Runtime-`/ready` abzuschwächen.
- **Realer Exit 20.09.2026:** reales Update V16.1.0 → V16.2.0 mit `FULL_READY`; Feldtool meldete `controller_ready: FULL_READY`, `controller_readiness_acceptance: READY:FULL_READY`, `install_report: PASS` und `rollback_backup_integrity: RELEASE_BACKUP_EXACT`; Gesamtfeldabnahme PASS.

### ZEC-EV-DEP-001 – reale Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Abnahme

- **Status:** DEFERRED durch Nutzerentscheidung vom 19.09.2026.
- Risiko bewusst akzeptiert; weiterhin erforderlich, aber bis auf weiteres kein Entwicklungsblocker.
- Offener Realpfad: read-only Uninstaller-Preflight, User-Data-Backup/Fresh-Reset, CLEAN_FRESH_INSTALL, Fresh Install, FIRST_INSTALL_SETUP, erster Settings-Commit, Restart NORMAL, Feldabnahme, abschließender Reset/Restore.

## 5. Dauerhaft geschlossene / supersedierte Entwicklungshistorie

Die folgenden Einträge bleiben bewusst im Master-Ledger. Die Liste ist auf die aus Release-Tree und Chat-Export belastbar recoverbaren größeren Schritte ausgerichtet.

| Ledger-ID | Release/Phase | Status | recoverbarer Abschlussinhalt |
|---|---|---|---|
| `ZEC-HIST-BASE-001` | frühe V12-Entwicklung | SUPERSEDED | lokale MQTT-/Zendure-Steuerung, frühe Shelly-/Graph-/Statusgrundlagen; in spätere Architektur überführt |
| `ZEC-HIST-MEAS-V3` | V12.9.x | SUPERSEDED | Measurement V3 als Diagnose-/Historienbasis; später durch V4 ersetzt |
| `ZEC-HIST-MEAS-V4` | V12.10/V12.13 | CLOSED | Measurement V4 als produktiver Diagnosevertrag; seit V12.13.0 V4-only Runtime, V3 nur offline/read-only |
| `ZEC-HIST-RC6` | V12.11.2-RC6 | CLOSED | UI-/Diagnose-Hotfix, Operational-Event-Semantik und Legacy-Statusreferenz |
| `ZEC-HIST-RC7` | V12.11.2-RC7 | CLOSED | MQTT-Freshness-0s-Fehler, Command-Lifecycle-/Timing-/Journaldiagnose |
| `ZEC-HIST-RC8` | V12.11.2-RC8 | CLOSED | SOC-Darstellung, stale Warnungsauflösung und UI/Diagnose/Installationsstabilisierung |
| `ZEC-HIST-RC9` | V12.11.2-RC9 | CLOSED | Replay-/Timing-/Status-/Logging-Diagnosepolish |
| `ZEC-HIST-RC10` | V12.11.2-RC10 | CLOSED | topologiefähige Statusseite und passiver Live-Preview-Dienst |
| `ZEC-HIST-RC11` | V12.11.2-RC11 | CLOSED | 0-W-Neutralisierung, Full-State-Resync, intentbasierter Effect-Timer, unabhängige Wirkungsklassifikation |
| `ZEC-HIST-RC12` | V12.11.2-RC12 | CLOSED | SmartMode-/Flash-Schutz, Command-State-Rücklesung, getrennte Netz-/Pack-/Offgrid-Powersemantik |
| `ZEC-HIST-RC13` | V12.11.2-RC13 | CLOSED | Neutralisierungs-Deduplizierung, Command-State-Gate, Trackingtoleranz, Publish-Evidenz |
| `ZEC-HIST-RC14` | V12.11.2-RC14 | CLOSED | High-SOC-Ladeannahme/Taper-Reklassifikation ohne Zielwertformeländerung |
| `ZEC-HIST-RC15` | V12.11.2-RC15 | CLOSED | Publish-Historie vs. Geräte-Readback getrennt, Late-Effect-/Recovery-Guard-Härtung |
| `ZEC-HIST-RC16` | V12.11.2-RC16 | CLOSED | `SMA_FULL_OR_IDLE` Delta→Absolutzielkorrektur |
| `ZEC-HIST-RC17` | V12.11.2-RC17 | CLOSED | Harvest 0-W-Netzziel/Export-Capture-Untergrenze, High-SOC-/Near-Limit-Allokation |
| `ZEC-HIST-RC18` | V12.11.2-RC18 | CLOSED | asynchroner lokaler Zendure-API-Worker; keine externe I/O im Regelzyklus |
| `ZEC-HIST-RC19` | V12.11.2-RC19 | CLOSED | Status-/Diagnose-Stabilisierung, Requested-vs-Applied, API-Worker-Sichtbarkeit |
| `ZEC-HIST-RC20` | V12.11.2-RC20/Fix6 | CLOSED | SettingsRegistry/UI, Config-Runtime, Preview/Commit, Restart, Last-Good/Recovery-Unterbau |
| `ZEC-HIST-V12_11_3` | V12.11.3 | CLOSED | Installer-Readiness-Akzeptanz sicherer transienter Commandzustände |
| `ZEC-HIST-V12_11_4` | V12.11.4 | CLOSED | mobile Settings/Modal/Event-Reconciliation/Warnzähler |
| `ZEC-HIST-V12_11_5` | V12.11.5 | CLOSED | Desktop-Settings-Shell, Nacht-HH:MM-Compoundfelder, Preview-422-UX, Adminaktionen |
| `ZEC-HIST-V12_11_6` | V12.11.6 | CLOSED | Settings-/Status-UX, lokale Validation, Default/Reset-Semantik, sichere Sentinelwerte |
| `ZEC-HIST-V12_11_7` | V12.11.7 | CLOSED | explizite Default-Provenienz/Reset-Policy und fail-closed FIRST_INSTALL_SETUP-Vertrag |
| `ZEC-HIST-V12_12_0` | V12.12.0 | CLOSED | strukturierte Settings-Hilfe & Guided Configuration |
| `ZEC-HIST-V12_12_1` | V12.12.1 | CLOSED | Help-/Terminologie-/Such-/Mobile-Quality-Fix |
| `ZEC-HIST-V12_12_2` | V12.12.2 | CLOSED | Single-Owner, monotone/fresh Harvest-Entry, Limiter-/Manifest-/SOC-UI-Härtung |
| `ZEC-HIST-V12_13_0` | V12.13.0 | CLOSED | Measurement V4-only / Legacy-V3-Runtime-Cleanup |
| `ZEC-HIST-V13_0_0` | V13.0.0 | CLOSED | benannte Konfigurationsstände, Import/Export, Portabilität, historische Config-/SOC-Timeline |
| `ZEC-HIST-V13_0_1` | V13.0.1 | CLOSED | Readiness-/Releaseidentitätsfix der V13-Linie |
| `ZEC-HIST-V13_0_2` | V13.0.2 | CLOSED | Config-State-/CSRF-/SQLite-Writer-/Backfill-Härtung |
| `ZEC-HIST-V13_0_3` | V13.0.3 | CLOSED | Config-Preview-UX-Hotfix und Feldabschluss vor Graph-Hauptblock |
| `ZEC-HIST-V14_0_0` | V14.0.0 | CLOSED | Graph Core V3, relationale Persistenz, Query/Catalog, Coverage/Evidence/Retention-Ledger, Inspector/Command-Follow/Episodenvergleich, Rebuild/Cutover |
| `ZEC-HIST-V14_1_0` | V14.1.0 | CLOSED | Greenfield Graph-UI/Analyse-Workspace |
| `ZEC-HIST-V14_1_1` | V14.1.1 | CLOSED | Installer-/Runtime-Root-Fix für Graphassets |
| `ZEC-HIST-V14_1_2` | V14.1.2 | CLOSED | explizite Selection, Zeitraum-/Episodenvergleich, synchronisierte Interaktion/Evidence-Segmente |
| `ZEC-HIST-V14_1_3` | V14.1.3 | CLOSED | Graph-State-History-Repair und Status-SOC-Responsiveness |
| `ZEC-HIST-V14_1_4` | V14.1.4 | CLOSED | Graph-/Status-Performance und UX-Polish |
| `ZEC-HIST-V15_0_0` | V15.0.0 | CLOSED | source-neutrale Primärspeicherarchitektur, EVCC/custom/Modbus-Template, read-only Modbus/TCP |
| `ZEC-HIST-V15_0_1` | V15.0.1 | CLOSED | Graph-/Analyse- und Primary-Settings-UX-Härtung |
| `ZEC-HIST-V15_0_2` | V15.0.2 | CLOSED | Graph-Interaktionsbugfixes / Detailausschnitt / Command-Follow-Layout |
| `ZEC-HIST-V15_0_3` | V15.0.3 | CLOSED | technisches Datenblatt dauerhaft in Releasevertrag integriert |
| `ZEC-HIST-V16_0_0` | V16.0.0 | CLOSED IMPLEMENTATION | brokerneutraler Installer/Fresh-Install/Uninstaller/Support-Grundvertrag; Real-Fresh-Evidenz siehe `EV-DEP-001` |
| `ZEC-HIST-V16_0_1` | V16.0.1 | CLOSED | Installer-Paketidentitäts-Hotfix |
| `ZEC-BL-DEP-001` | V16.0.2 | CLOSED | fail-closed Cleanup verwaister Python-Caches entfernter Quellbäume; realer Updatepfad bestätigt |
| `ZEC-HIST-V16_1_0` | V16.1.0 | CLOSED | SMA Sunny Island 31009 Capability, separate Freshness/Diagnose/usable SOC, source-neutrale Primärspeicher-Namenshygiene; keine Reglerwirkung; reales Update/Block-A am 20.09.2026 feldabgenommen. Rohes Feldtool `23 PASS / 2 FAIL`; beide FAILs als Toolvertrag-Abweichungen unter `ZEC-BL-DIAG-FIELD-001` belegt. |

## 6. No-Drop-/Reconciliation-Vertrag für dieses Ledger

Vor dem Entfernen/Archivieren einer Übergabe, Spezifikation, Work-Chat-Delta-Datei oder historischen Projektquelle müssen alle Planungsmarker und IDs gegen dieses Ledger reconciliiert werden. Mindestens zu prüfen:

```text
Backlog / Roadmap / offen / Restpunkt / später / perspektivisch
Nicht Bestandteil / deferred / TODO / Folgeblock / S1..S9
```

Jeder Fund benötigt genau eine Auflösung:

1. bestehender Master-Eintrag,
2. neuer Master-Eintrag, oder
3. explizit belegtes `CLOSED`, `SUPERSEDED` oder `REJECTED`.

Ein ungeklärter Fund bedeutet **BACKLOG_NO_DROP_GATE = FAIL** und blockiert die Quellenbereinigung.

## 7. Release-Evidenz und Changelog

Ab dem ersten Release nach dieser Kanonisierung wird eine Snapshot-Fassung dieses Master-Ledgers im Release-Tree mitgeliefert:

```text
docs/ZEC_Master_Backlog.md
```

Sie ist Entwicklungs-/Roadmap-Evidenz. Ein Release-Changelog kann aus den seit dem Vorgänger neu `CLOSED` gesetzten bzw. releasezugeordneten Einträgen abgeleitet werden. Das Changelog ersetzt das Ledger nicht; offene, zurückgestellte, supersedierte und verworfene Punkte bleiben im Master erhalten.

## 8. Recovery-Provenienz 19.09.2026

Der aktuelle Ledgerstand wurde aus folgenden Ebenen reconciliiert:

1. aktuelle kanonische Projektquellen;
2. verifiziertes V16.0.2-Release-ZIP und darin erhaltene Spezifikationen/Release-/Übergabeunterlagen;
3. `conversations.json` mit 34 systematisch geprüften ZEC-/Zendure-relevanten Chats;
4. aktueller V16.0.2-Implementierungsgegencheck.

Details: `ZEC_34_CHAT_RECONCILIATION_20260919.md`.

## 9. Roadmapentscheidung 20.09.2026 – Provenienz

Nutzerentscheidung im ZEC-Projekt am 20.09.2026 nach Recovery/Neuaufstellung des Master-Ledgers:

```text
(S3 + adaptive Strategie + Kapazitätsgewichtung)
→ Battery Care
→ Storage
→ Graph→Analyse-Handoff
→ Counterfactual Simulation
→ Szenarioeditor
→ Multi-Zendure-Commandbetrieb
→ Release/CI-Hardening
```

Begründung für die Zusammenführung des ersten Blocks: Im parallelen Projektchat **„Installierte PV Anlage“** wird das grundlegende Lernmodell für adaptive Lade-/SOC-/Ertragsstrategie und Kapazitätsgewichtung entwickelt; saisonale Faktoren und dynamische Tagesprofile sind Teil dieser Konzeption. Die finale Abdeckung ist erst mit der dortigen Abschlussübergabe verbindlich festzustellen. Bis dahin werden keine historischen Child-Scopes als erledigt markiert.

## 10. Projektquellen-Reconciliation 21.09.2026

Der V16.2.3-Technical-Freeze-Stand enthält maschinell inventarisiert **81 eindeutige stabile `ZEC-BL`/`ZEC-EV`/`ZEC-HIST`-IDs**. Die Post-Freeze-Reconciliation nach realer V16.2.3-Installation und manueller UI-Prüfung erhält sämtliche 81 IDs und ergänzt genau eine neue ID:

1. `ZEC-BL-UI-SETTINGS-001` – real bestätigter Settings-Webmodell-/Availability-Defekt für aktuelle produktive V16.2.0-Felder.

Fortgeschrieben, aber nicht entfernt oder umbenannt wurden insbesondere:

- `ZEC-BL-DEP-003` → `CLOSED / REAL_FIELD_PASS` durch erfolgreichen V16.2.3-Updatepfad;
- `ZEC-BL-DEP-004` → `CLOSED / REAL_FIELD_PASS` durch erfolgreichen V16.2.3-Preflight/Update;
- `ZEC-BL-UI-STATUS-003` → `OPEN`, `implementation_state=partial`, weil die manuelle UI-Prüfung nach automatischem PASS einen realen Surface-Defekt fand;
- `ZEC-BL-UI-STATUS-EXPERT-001` bleibt `OPEN / partial` und erhält den realen Primärspeicher-Superset-Befund;
- `ZEC-BL-CTRL-FASTCAP-001`, `ZEC-BL-CTRL-ADAPTIVE-001` und alle Child-/Folgepunkte bleiben vollständig erhalten; ihre nächste Reihenfolge wird nach dem unmittelbaren UI-/Settings-Bugfix explizit entschieden.

Damit enthält dieses Ledger nach Kanonisierung **82 eindeutige stabile IDs**. Keine Vorgänger-ID wurde entfernt. Die im Handover inventarisierten Planungsmarker sind entweder einem bestehenden Eintrag oder `ZEC-BL-UI-SETTINGS-001` zugeordnet.

**BACKLOG_NO_DROP_GATE = PASS**

### V16.2.4 Build-Reconciliation 21.09.2026

Der freigegebene V16.2.4-Block erzeugt **keine neue Ledger-ID**. Alle 82 zuvor kanonisierten stabilen IDs bleiben erhalten. Fortgeschrieben werden ausschließlich bestehende Punkte: `ZEC-BL-UI-SETTINGS-001`, `ZEC-BL-UI-STATUS-003`, `ZEC-BL-UI-STATUS-EXPERT-001` und `ZEC-BL-DEP-002`. Fast Capture, Adaptive samt Child-IDs, usable-SOC Block B, Primary Metadata und Battery Care bleiben unverändert recoverbar.

**BACKLOG_NO_DROP_GATE = PASS (82/82 IDs erhalten)**

### V16.2.4 Real-Field-/V16.2.5-Hotfix-Reconciliation 22.09.2026

Die reale V16.2.4-Abnahme erhält alle bisherigen **82** stabilen IDs und ergänzt für die manuell bestätigten neuen Defektklassen genau drei IDs:

1. `ZEC-BL-UI-SETTINGS-MOBILE-001`;
2. `ZEC-BL-DIAG-OWNER-001`;
3. `ZEC-BL-GRAPH-GAP-001`.

`ZEC-BL-UI-SETTINGS-001` und `ZEC-BL-DEP-002` werden durch reale V16.2.4-Evidenz auf `CLOSED / REAL_FIELD_PASS` fortgeschrieben. `ZEC-BL-UI-STATUS-003` bleibt erhalten und wird wegen der realen Karten-/Warnungsbefunde in den freigegebenen V16.2.5-Hotfix überführt. `ZEC-BL-UI-STATUS-EXPERT-001` bleibt `OPEN / partial`. Fast Capture, Adaptive samt Child-IDs, usable-SOC Block B, Primary Metadata, Battery Care und alle übrigen Vorgängerpunkte bleiben unverändert recoverbar.

Damit enthält das Ledger **85 eindeutige stabile IDs**. Keine Vorgänger-ID wurde entfernt oder umbenannt.

**BACKLOG_NO_DROP_GATE = PASS (82/82 Vorgänger-IDs erhalten; 3 neue IDs; Gesamt 85)**

### V16.2.5 Real-Field-Reconciliation 22.09.2026

Die reale Installation V16.2.4 → V16.2.5 und der konsolidierte automatische Feldlauf sind PASS. Die übergebene Evidence weist `controller_ready=WARN LIMIT_READBACK_CONVERGENCE`, aber `controller_readiness_acceptance=PASS TRANSITIONAL:LIMIT_READBACK_CONVERGENCE` aus; das entspricht dem bestehenden Readinessvertrag. Evidence-Archiv-SHA256: `b8b188f487f05eac5fcba8d94614ecb17731c88389708e84425113cf43cad239`.

Die anschließende manuelle Sichtprüfung und Nutzerentscheidung führen ohne neue Ledger-ID zu folgenden Fortschreibungen:

- `ZEC-BL-UI-SETTINGS-MOBILE-001` → `CLOSED / REAL_FIELD_PASS`;
- `ZEC-BL-DIAG-OWNER-001` → `CLOSED / REAL_FIELD_PASS`;
- `ZEC-BL-UI-STATUS-003` → funktionale V16.2.5-Warnungsdarstellung real PASS; neuer UX-Follow-up für höhenneutralen Header-Warning-Chip mit Desktop-Popover/Mobile-Bottom-Sheet bleibt `OPEN`;
- `ZEC-BL-GRAPH-GAP-001` → sichtbare Linienunterbrechung real PASS; Gap-aware Cursor-/Tooltip-/Inspector-Semantik bleibt `OPEN`.

Der Nutzer entscheidet am 22.09.2026 ausdrücklich, für die beiden isolierten UI-Restpunkte keinen eigenen Hotfix-Zyklus zu erzwingen. Beide werden verbindlich im nächsten ohnehin anstehenden Release separat regressionsgeprüft mitgeführt und blockieren die Fast-Capture-vs.-Adaptive-Sequencing-Entscheidung nicht. Damit ist das Sequencing-Gate freigegeben, ohne eine Reihenfolge vorwegzunehmen.

Alle bisherigen **85** stabilen IDs bleiben erhalten; keine ID wird entfernt, umbenannt oder durch die neue Feldbeobachtung ersetzt.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**

### Fast-Capture-Sequencing-/Revalidation-Reconciliation 22.09.2026

Die neutrale Gegenüberstellung Fast Capture versus Adaptive ist abgeschlossen. Der Nutzer bestätigt die technische Entkopplung und legt **Fast Capture A400/R100 als nächsten Controllerblock** fest. Die eingefrorene Produktionsspezifikation wurde gegen V16.2.5 revalidiert und um die releaseintegrierte Feldverifikationspflicht ergänzt. Adaptive bleibt mit sämtlichen Child-IDs erhalten und wird nach Bereitstellung des Fast-Capture-Releases als eigener Spezifikationsblock fortgeführt.

Es entsteht keine neue Ledger-ID: Die Verifikationslogik ist Bestandteil des Exit-/Evidenzvertrags von `ZEC-BL-CTRL-FASTCAP-001`, und die Adaptive-Spezifikationslücke bleibt unter `ZEC-BL-CTRL-ADAPTIVE-001` samt Child-IDs erhalten. Alle bisherigen **85** stabilen IDs bleiben unverändert.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**



### V17.0.0 Fast-Capture Checkpoint A/B Reconciliation 22.09.2026

Der freigegebene V17.0.0-Fast-Capture-Block bleibt unter der bestehenden ID `ZEC-BL-CTRL-FASTCAP-001`; es entsteht keine neue Ledger-ID. Checkpoint A implementiert Controllerkern/State und bestand die fokussierte Differential-/Safetyregression mit **110 Tests + 11 Subtests PASS**. Checkpoint B ergänzt Settings-/Validationvertrag, Measurement-V4-Evidenz, `tools/fast_capture_field_analysis.py`, `tools/v17_field_acceptance.py` und die Analysis-Package-Integration; die fokussierte Checkpoint-B-Regression bestand mit **114 Tests + 640 Subtests PASS**.

Die V16.2.5-Produktivbasis bleibt bis Release-/Feldfreigabe unverändert. Die zwei bekannten Frontend-Follow-ups bleiben unter `ZEC-BL-GRAPH-GAP-001` und `ZEC-BL-UI-STATUS-003` erhalten und bilden den nächsten isolierten Entwicklungscheckpoint. Vollständige Regression, ResourceWarning-, Syntax-, Manifest-, Fresh-extract- und Releasegates sind noch ausstehend; daher **kein TECHNICAL BUILD PASS**.

Checkpoint C setzt die zwei separat freigegebenen Frontend-Follow-ups um: Gap-aware Cursor/Marker/Inspector/Command-Follow/Comparison-Hover sowie den höhenneutralen Zendure-Warning-Chip mit Desktop-Popover/Mobile-Bottom-Sheet. Die fokussierte Checkpoint-C-Regression besteht mit **12 Tests PASS**.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**


### V17.0.1 Real-Field / V17.0.2 Fast-Evidence-Hotfix Reconciliation 23.09.2026

`ZEC-BL-CTRL-FASTCAP-001` bleibt dieselbe stabile Ledger-ID; keine neue Produkt-ID erforderlich. Reales V16.2.5 -> V17.0.1 Update PASS, automatischer V17-Feldlauf PASS und Runtime `FULL_READY`. Fast Capture wurde anschließend real auf `shadow` gesetzt. Ein Night-Mode-Snapshot bestätigte fail-closed `fast_capture_active=false`, Overlay 0 und `NIGHT_MODE`-Blockierung. Der Desktop-Warning-Chip/Popover unter `ZEC-BL-UI-STATUS-003` ist real visuell PASS; die mobile Bottom-Sheet-Variante bleibt Feld-Follow-up.

Beim ersten natürlichen Shadow-Evidenzversuch wurden drei Verifikationsdefekte des V17.0.1-Evidenzpfads real gefunden: (1) Fast-Capture-Runtimefelder fehlten in `ControllerState.record_graph_point()` und fielen in Measurement V4 dadurch auf `off`/0 zurück; (2) der Fast-Analyzer bewertete alle historischen Config-Snapshot-Versionen statt nur die von analysierten Rows referenzierten Config-Hashes und erzeugte `CONTROLLER_VERSION_MISMATCH`; (3) `create_zec_analysis_package.sh --latest-only` konnte unter `set -o pipefail` durch eine früh abbrechende Pipeline mit SIGPIPE/rc=141 enden. Die V17.0.1-Shadow-V4-Daten sind daher nicht als kanonischer Fast-Funktionsnachweis verwertbar. Active bleibt nicht freigegeben.

V17.0.2 ist als isolierter Evidence-/Tooling-Hotfix (+0.0.1) freigegeben: Fast-Felder werden cycle-exakt in den Measurement-V4-Zulauf übernommen; Analyzer-Versionsevidenz wird auf referenzierte Config-Hashes begrenzt und strukturelle Evidenz im Human-Report sichtbar; `--latest-only` wird pipefail-/SIGPIPE-sicher. A400/R100-Regler-, Command-, Safety-, Cross-Charge- und Recoverysemantik bleiben unverändert; `controller_logic.py` bleibt byteidentisch zu V17.0.1. Nach V17.0.2-Installation muss neue reale Shadow-Evidenz gesammelt werden, bevor ein begrenzter Active-Rollout überhaupt freigegeben werden kann.

**BACKLOG_NO_DROP_GATE = PASS (85/85 stabile IDs erhalten; 0 neue IDs)**


### V17.0.2 Fast-Evidence-Hotfix Technical-Build-Pass Reconciliation 23.09.2026

`ZEC-BL-CTRL-FASTCAP-001` bleibt dieselbe stabile Ledger-ID; keine neue Produkt-ID entsteht. V17.0.2 korrigiert die drei am realen V17.0.1-Shadow-Evidenzpfad gefundenen Defekte: cycle-exakte Fast-Felder werden in `record_graph_point()` und damit Measurement V4 transportiert; Analyzer-Versionsevidenz wird ausschließlich über von analysierten Rows referenzierte Config-Hashes gebildet und strukturelle Evidenz wird im Human-Report sichtbar; `create_zec_analysis_package.sh --latest-only` ist pipefail-/SIGPIPE-sicher.

Technischer Nachweis: fokussierte Regression **51 Tests PASS**; realer `--latest-only`-Shelltest mit >80 V4-Dateien PASS; vollständige Regression **157 Testdateien / 1169 Tests + 706 Subtests PASS**; identischer `-W error::ResourceWarning`-Lauf **1169 + 706 PASS**; Bash **13/13**, Browser-JavaScript **3/3**, Python Compileall, Deployment-Harness **11/11**, Datenblatt-Gate und maschinenlesbare Build-Evidence PASS. Das aktuelle 10-seitige Datenblatt wurde nach dem finalen Statusupdate vollständig gerendert und visuell geprüft. `controller_logic.py` bleibt SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031` und damit byteidentisch zu V17.0.1. Release-Hygiene, Source-Manifest 932/932, kanonischer ZIP-Root sowie Paket-/Fresh-extract-Manifest-, Build-Evidence- und Datenblatt-Gates sind im Release-Freeze PASS; nach dem Dokumentationsfreeze wird das exakt veröffentlichte ZIP neu gebaut und identisch verifiziert.

Reale V17.0.2-Installation und neue Shadow-Feldevidenz bleiben **FIELD_PENDING**. V17.0.1-Shadow-V4-Daten werden wegen des real nachgewiesenen Evidence-Pfadddefekts nicht als Fast-Funktionsnachweis verwendet. `active` bleibt nicht freigegeben. Der Desktop-Warning-Chip/Popover ist real visuell PASS; die mobile Bottom-Sheet-Variante bleibt als UI-Feldevidenz offen.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**


### V17.0.2 Final Package / Release Reconciliation 23.09.2026

Das exakt veröffentlichte Installerpaket `zendure_controller_v17_0_2.zip` hat SHA256 `82bd2db52a71b4a4e56f8e8c39e30511494fb02f8735909667052b73bd82f311` und Größe 14.402.481 Byte. Finaler Paketpfad: Release-Hygiene PASS; Source-Manifest **932/932 PASS**; kanonischer ZIP-Root `zendure_controller_v17_0_2/` PASS; ZIP-Integrität PASS; Fresh-extract Release-Hygiene PASS; Fresh-extract Manifest **932/932 PASS**; Build-Evidence PASS; Datenblatt-Gate PASS; Paket-Root-Verifikation PASS. Ein Build-Runtime-Lauf des echten Installers mit exakt diesem ZIP erreichte `Package-Identität: PASS`, Datenblatt PASS, Runtime-Readiness-Smoke PASS und Build-Evidence PASS und stoppte anschließend erwartungsgemäß am Host-Gate `Installer muss als Benutzer pi gestartet werden`; dies ist kein Ersatz für den realen Raspberry-Pi-Updatefeldtest.

`ZEC-BL-CTRL-FASTCAP-001` bleibt **IN_PROGRESS / TECHNICAL_BUILD_PASS / FIELD_PENDING**. V17.0.1 bleibt reale Runtimebasis bis zum erfolgreichen V17.0.2-Update. Danach müssen neue Shadow-Daten erzeugt werden; V17.0.1-Fast-V4-Evidence wird nicht wiederverwendet. `active` bleibt nicht freigegeben.

**BACKLOG_NO_DROP_GATE = PASS (85/85 IDs erhalten; 0 neue IDs)**

### V17.0.2 Nacht-MIN_SOC-/SMA-Parser-Reconciliation 25.09.2026

Die reale V17.0.2-Evidenz ergänzt genau zwei stabile Ledger-IDs:

1. `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` – real bestätigter Nacht-/MIN_SOC-Control-Gap; **RELEASE_BLOCKER_NEXT_RELEASE**.
2. `ZEC-BL-GRID-SMA-OBIS-001` – strukturell unzureichender SMA-Speedwire-/OBIS-Parser; **BUG_CONFIRMED / FIX_REQUIRED_NEXT_RELEASE**. Die exakte historische Raw-Frame-Ursache des wiederkehrenden Extremwertes ist keine Fix-Vorbedingung.

Alle bisherigen **85** stabilen IDs bleiben vollständig erhalten; keine Vorgänger-ID wurde entfernt oder umbenannt. Das aktuelle Ledger enthält damit **87 eindeutige stabile IDs**.

**BACKLOG_NO_DROP_GATE = PASS (85/85 Vorgänger-IDs erhalten; 2 neue IDs; Gesamt 87)**

### Projektquellen-/Realfeld-Synchronisation 25.09.2026

Die kanonischen Quellen `00`, `01`, `05`, `06` und `07` wurden auf die reale V17.0.2-Basis synchronisiert. Festgehalten sind insbesondere:

- V17.0.2 real installiert und allgemeiner Feldlauf PASS / FULL_READY;
- Fast-Capture-Shadow-Gate PASS; Active-`NEAR_LIMIT` in den beobachteten Aspekten real PASS; Active-`FULL_IDLE` weiterhin EVIDENCE_PENDING;
- Fast-Capture-Evidence-Tooling muss Calculation-Anwendbarkeit und bounded-memory-Langzeitanalyse härten;
- `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` sind zwingender Scope des nächsten Produktreleases;
- produktive Real-Pi-Analysen großer V4-Historien müssen streaming/bounded-memory erfolgen;
- Nomenklatur: „Fast Capture“, bei Platzknappheit „FastC“, nicht kontextlos „Fast“.

Keine der 85 Vorgänger-IDs wurde entfernt oder umbenannt. Die zwei neuen IDs bleiben stabil erhalten; Gesamtbestand 87.

**BACKLOG_NO_DROP_GATE = PASS (85/85 Vorgänger-IDs erhalten; 2 neue IDs; Gesamt 87)**


### Strategie-/Herbst-Reconciliation 18.10.2026

- Abgestimmte Richtungsentscheidung nach 23-Tage-Herbstanalyse: Adaptive-A1 begründet `DEFERRED/EVIDENCE_GAP`; `ZEC-BL-CTRL-S3-001`, `ZEC-BL-CTRL-USABLE-SOC-001` (B2) und `ZEC-BL-CTRL-CAP-001` (C1) eigenständige fachliche Scopes; Battery Care winterpriorisiert. Historischer 20.09.-Umbrella-Zuschnitt und spätere Vorgänger-Roadmap-Zitate bleiben als Provenienz erhalten, ihre Sequenz ist supersediert.
- Getrennte normative Ebenen: `05` alleinige Ledger-/Roadmapautorität; `ZEC_STRATEGIEARCHITEKTUR_ENTSCHEIDUNGSSTAND_20261018.md` hält fachliche Richtungsentscheidungen fest, **nicht** als freigegebene Implementierungsspezifikation; `ZEC_S3_FACHLICHE_PRODUKTIONSSPEZIFIKATION_ENTWURF_20261018.md` ist nicht freigegebener S3-Entwurf; `ZEC_A1_WIRKSAMKEIT_23T_DECISION_BRIEF_20261017.md` ist retrospektive Evidenz.
- Neues eigenständiges diagnostisches Forschungsthema `ZEC-BL-BATTERY-SOH-001` bewahrt die konkrete Kapazitätsalterungs-Frage, ohne sie stillschweigend als C1/Adaptive-Produktwirkung zu deklarieren.
- Zwei zwingende Fehlerkorrekturen `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` bleiben uneingeschränkte Next-Release-Blocker. Command-Episoden aus dem Oktober bleiben gezielte Analyse-/Recovery-Provenienz unter vorhandener Command-/Observability-Arbeit, ohne neuen pauschalen Pi-Langanalyseblock.
- Aktuelle Produktbasis bleibt V17.0.2; keine S3-/B2-/C1-/Adaptive-/Battery-Care-Sourceänderung, keine neue Runtime oder Release-PASS durch die Quellpflege.
- **BACKLOG_NO_DROP_GATE:** Alle **43** im gelieferten Ledgertext explizit vorhandenen stabilen ZEC-BL-/ZEC-EV-IDs bleiben erhalten; eine neue `ZEC-BL-BATTERY-SOH-001`, somit **44** textuell nachweisbare IDs. Die aus früheren Projektständen überlieferte Angabe „87 eindeutige IDs“ ist im aktuellen gelieferten Master-Ledger **nicht einzeln prüfbar**. Kein Dokument wird gelöscht, historische Entscheidungs-/Planungszeilen bleiben erhalten. Die historische 87er-Zählung ist bei späterer gezielter Auditierung zu klären, bevor Quellen entfernt/archiviert werden.

**BACKLOG_NO_DROP_GATE = PASS für 43/43 im aktuellen Ledgertext verifizierbare Vorgänger-IDs; 1 neue explizite ID; keine entfernten Quellen. Historischer 87/87-Vollbestand = NOT_EVALUABLE aus diesem Dateiinhalt; deshalb keine Quellenbereinigung zulässig, bevor die Diskrepanz geklärt ist.**


### Architektur- und Historien-Dokumentationsentscheid 19.10.2026

Der Nutzer bestätigt die künftige Versionierung wesentlicher technischer As-built-Dokumente, Produktionsspezifikationen und Architekturentscheidungen im Source-`docs/`, einschließlich möglichst leicht zu übernehmender historischer Originalunterlagen. Die damals noch nicht implementierte Fast-Capture-Spezifikation für V16.0.2 liegt wieder als Original vor; die V16.2.5-Revalidierung ist nur historisch belegt, als Original aktuell nicht verfügbar. Dies wird unter der stabilen neuen ID `ZEC-BL-DOC-ARCH-001` geführt; die Dokumentationspolicy ist in `01`/`06` festgelegt, die Integration in einen realen Release samt QA steht noch aus. Kein anderer Backlogpunkt wird geändert, gelöscht oder ersetzt. Die vorher textuell erkennbaren 44 eindeutigen ZEC-BL-/ZEC-EV-IDs bleiben erhalten; neu 1 -> 45 belegbare IDs. Der historisch genannte 87er-Gesamtbestand bleibt **nicht unabhängig verifiziert**, daher weiterhin keine Projektquellenbereinigung/History-Drops.
