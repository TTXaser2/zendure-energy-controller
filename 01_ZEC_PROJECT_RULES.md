# ZEC – Projektregeln

**Stand:** 19.10.2026  
**Status:** kanonisch

## 1. Zweck

Dauerhafte Arbeits-, Freigabe-, Sicherheits-, Quellen- und Sicherungsregeln für den Zendure Energy Controller (ZEC). Versionsspezifischer Release-/Feldstatus gehört in `07_ZEC_CURRENT_RELEASE_AND_FIELD_STATUS.md`.

## 2. Grundregel für Änderungen

- Keine Sourceänderung und keine neue Controller-Version ohne vorherige Analyse, Scopebeschreibung und ausdrückliche Freigabe des Nutzers.
- Bugberichte, Screenshots, Funde und Ideen zunächst analysieren, fachlich einordnen und als Scope oder Backlogpunkt festhalten.
- Eine erteilte Makrofreigabe gilt für den vollständig beschriebenen Block; innerhalb dieses Scopes keine unnötigen Mikrofreigaben.
- Bei Scopekonflikt, fehlender Grundlage oder notwendiger Änderung ausdrücklich geschützter Bereiche vor der Änderung stoppen und konkret abstimmen.
- Bei Bugfix-/Härtungsreleases ausdrücklich nachweisen, ob der Live-Regelalgorithmus unverändert bleibt.
- Keine stillschweigenden Änderungen an Reglerstrategie, Prioritäten, Safety- oder Recoverysemantik.

## 3. Verbindliche Datensicherung bei Entwicklung – Bibliotheks-Checkpoint-Gate (Beschluss 19.10.2026)

**Kein Entwicklungsfortschritt darf ausschließlich in einem temporären Chat-, Sandbox- oder Working-Tree-Dateisystem existieren.** Ein erzeugtes ZIP oder ein Sandbox-Downloadlink gilt ausdrücklich **nicht** als extern gesichert. Der verbindliche Primärweg für Entwicklungscheckpoints ist die persönliche ChatGPT-Bibliothek im Ordner `ZEC - Zendure Energy Controller/Checkpoints/` (kein Project-Quellenordner und keine produktive Pi-Installation). Diese Regel setzt **keine** Änderung der Projekterinnerung und keinen manuellen Zwischen-Download voraus.

### 3.1 Checkpoint-Zeitpunkte und Umfang

- Nach jedem größeren sourceverändernden Arbeitsblock und vor umfangreicher Folgeentwicklung, längerer Analyse, Dokumentation oder vollständiger QA seit wesentlichen ungesicherten Sourceänderungen: **sofort vollständiges Checkpoint-ZIP** des isolierten aktuellen Entwicklungs-Working-Trees erstellen; enthalten sind alle relevanten Sources, Tests, technische Dokumentation, Build-/Manifest-/Versionsgrundlagen und nötigen Verifikationsartefakte. Keine nur inkrementellen Patches als alleiniger Rettungsanker.
- Archiv mit eindeutigem Projekt-/Branch-/Block-/Checkpoint-/Datumsnamen; nicht überschreiben. ZIP-Integrität/CRC, Root, Umfang/Manifest, Bytezahl und SHA256 der lokalen Ausgangsdatei prüfen. Keine realen Secrets, produktiven `config.json`-Inhalte, Tokens oder unnötigen Runtime-/Messdaten in eine ungeschützte Sicherung aufnehmen; nötigenfalls vor dem Upload sichere Datentrennung/Redaktion prüfen, ohne erforderliche Entwicklungsquellen auszulassen.
- **Unmittelbar im selben Checkpoint-Block** das vollständige ZIP in den genannten persönlichen Bibliotheksordner hochladen. Dort das genaue Bibliotheksobjekt unabhängig per Ordnerliste auffinden, als *raw file* in ein getrenntes Verzeichnis zurücklesen und dessen **SHA256, Bytezahl, ZIP-/CRC-Integrität** mit dem ursprünglichen ZIP vergleichen. Prüfprotokoll mit Timestamp, Checkpointidentität, SHA256, Größe, Bibliothekspfad, Rücklese- und Gate-Ergebnis anlegen und ebenfalls in der Bibliothek sichern.
- `CHECKPOINT_LIBRARY_GATE=PASS` und `EXTERNALLY_SECURED` sind **ausschließlich** bei nachweislich erfolgreichem Upload **und byteidentischem Rücklesen** zulässig. Zwischenstände heißen `LOCAL_ONLY`, `UPLOAD_PENDING` oder `LIBRARY_UNVERIFIED` und dürfen niemals als extern gesichert oder als abgeschlossene Sicherheitsmaßnahme dargestellt werden. Ein Test-PASS des Produkts folgt aus dem Checkpoint-Gate nicht.
- Bei fehlenden Berechtigungen, Quota, Verbindungsfehlern, Upload-/Materialisierungsfehlern oder Hashabweichung gilt `CHECKPOINT_LIBRARY_GATE=FAIL`: **keine weitere wesentliche Sourceentwicklung**, keinen längeren Folgeblock und keine Releasefreigabe durchführen; Fehler offenlegen, den vorhandenen lokalen Stand erhalten und einen neuen unabhängigen, nachweislich haltbaren Sicherungsweg **mit dem Nutzer abstimmen**. Keine stillschweigende Ausnahme oder optimistische Recoveryannahme.
- Vor einem Chatwechsel oder Wiederanlauf: **letzten nachweislich rückgelesenen Bibliothekscheckpoint** identifizieren und seine SHA256/ZIP-Integrität erneut prüfen. Historische Chataussagen, nicht rückgelesene Sandbox-Links und nur angekündigte spätere Checkpoints sind keine Sourcebasis. Ein neuer Checkpoint darf den gesicherten Vorgänger niemals stillschweigend ersetzen.

### 3.2 Aufbewahrung und Bereinigung der Bibliothek

- Die Bibliothek hat **planabhängige Speichergrenzen**; Belegung/Restplatz im ChatGPT-Webinterface unter `Bibliothek → Speicher` prüfen. Ohne bekannte Kontingentinformationen keine Behauptung über verfügbaren Restplatz.
- Speicherprüfung bei größeren Releases, etwa quartalsweise oder bei erkennbar knapper Kapazität; nicht nach jedem Checkpoint. **Keine automatische Löschung** allein aufgrund von Alter, Dateiname, Nummer, Upload-Erfolg eines Nachfolgers oder einer vermuteten Speicherquote.
- Mindestens erhalten: aktuelle veröffentlichte Release-/Rollbackbasis, aktuell letzte vollständig verifizierte Entwicklungsbasis je aktivem Zweig, relevante Release-Freeze-/Handover- und vor risikoreichen Änderungen erzeugte Anker sowie zunächst mindestens die letzten **fünf** verifizierten Vollcheckpoints des aktiven Zweigs, soweit verfügbar. Auch ältere Checkpoints bleiben erhalten, solange sie einzige Träger eines abweichenden Branches, offenen Nachweises oder nicht andernorts gesicherter Artefakte sind.
- Bereinigung **nur nach ausdrücklicher Nutzerfreigabe**, erfolgreicher Verifikation von Nachfolger/gesicherter Releasebasis, dokumentiertem SHA-/Inhalts-/Ledger-/Provenienzabgleich und einer Liste der konkret vorgeschlagenen Löschobjekte. Für die Entfernung historischer Projektquellen, Spezifikationen oder Übergaben muss zusätzlich `BACKLOG_NO_DROP_GATE=PASS` nach § 6a gelten. Das Master-Ledger `05` und historische Planungsentscheidungen werden niemals durch ZIP-Retention gelöscht.
- Löschen eines Bibliotheksobjekts ist **kein** Bereinigen einer kanonischen Projektquelle und keine Erlaubnis, Projektquellen oder Backlogpunkte zu entfernen. Die Bibliothek ist ein unabhängiger Sicherungsort innerhalb desselben ChatGPT-Kontos, jedoch kein versprochener unternehmensunabhängiger Offsite-/Disaster-Recovery-Service; separate lokale Release-/Pi-Backups bleiben sinnvoll.

Bei Fragen zur verbleibenden Arbeitsreserve sind **statt Spekulationen über den Chat** zu nennen:

1. Identität, SHA256, Speicherort, Rücklesegate und Zeitpunkt des letzten nachweislich extern gesicherten Checkpoints;
2. ob seitdem source-relevante Änderungen erfolgt sind;
3. ob vor weiterer Arbeit zuerst ein neuer Bibliotheks-Checkpoint nötig ist.

## 4. Arbeitsregel für Chats

- Ein Chat bearbeitet möglichst genau einen Release oder einen klar abgegrenzten Entwicklungsblock.
- Kontextgröße, parallele Stränge, Artefaktmenge und Eindeutigkeit der Quellbasis aktiv überwachen.
- Chatwechsel frühzeitig vor einem größeren Build oder Kontextverlust vorbereiten.
- Vor dem Wechsel vollständige Übergabe mit Codebasis + SHA256, freigegebenem Scope, Entscheidungen, Feldstatus, offenen Punkten, Build-/Abnahmecheckliste, Roadmap und Startprompt erzeugen.
- Im neuen Chat wird ausschließlich von der übergebenen/verifizierten Basis weitergearbeitet; historische Chats sind keine implizite Sourcebasis.
- Bei Real-Pi-Arbeit bevorzugt genau einen ausführbaren mutationsrelevanten Schritt pro Interaktion geben und anschließend die vollständige Ausgabe auswerten.
- Für regulär freigegebene reale Updates ist der Standardablauf **kombiniert**: Paket-SHA/ZIP prüfen, frisch entpacken und den normalen Installer starten. Der Installer führt seinen vollständigen internen Preflight aus und setzt die Installation nur bei `PREFLIGHT_RESULT=PASS` / `SAFE_TO_INSTALL=yes` unmittelbar fort. Ein separater vorangestellter `--preflight-only`-Lauf ist im Normalfall nicht erforderlich und wird nur für ausdrücklich mutationsfreie Diagnose-, Vertrags- oder Fehleranalysezwecke verwendet. Sicherheits-/Preflight-Gates werden dadurch niemals übersprungen.

## 5. Release-Versionierung

Seit V12.11.3 gilt ohne RC-Nummerierung:

- Bugfix / Hotfix / Korrektur / reine Härtung: `+0.0.1`
- rückwärtskompatible funktionale Weiterentwicklung innerhalb des Themas: `+0.1.0`
- neues Entwicklungsthema: `+1.0.0`
- bei Erhöhung einer höheren Stelle werden niedrigere Stellen zurückgesetzt.

Jeder Release besitzt eindeutige Version, Label und Build-ID. Ein bereits ausgeliefertes Paket wird niemals unter derselben Releaseidentität verändert.

## 6. Quellen- und Konfliktprinzip

Bei Widersprüchen gilt die Rangfolge aus `00_ZEC_PROJECT_SOURCE_INDEX.md`. Insbesondere:

- aktuelle reale Sources und aktuelle reale Evidenz schlagen ältere Übergaben;
- Spezifikationen sind keine Implementierungsnachweise;
- ältere Work-Chat-Deltas werden nach Kanonisierung aus den aktiven Projektquellen entfernt;
- produktive Nutzer-/Hauswerte sind keine allgemeinen Softwaredefaults.

## 6a. Persistentes Master-Backlog und No-Drop-Gate

`05_ZEC_BACKLOG_AND_ROADMAP.md` ist das dauerhafte Master-Ledger der Produktentwicklung. Es enthält nicht nur aktuelle offene Punkte, sondern auch recoverbare `DEFERRED`, `SPEC_NEEDED`, `EVIDENCE_PENDING`, `CLOSED`, `SUPERSEDED` und `REJECTED`-Einträge mit Provenienz. Ein relevanter Punkt darf nicht durch Quellenbereinigung oder Releasewechsel verschwinden.

Vor dem Entfernen/Archivieren einer Übergabe, Spezifikation, Work-Chat-Delta-Datei oder historischen aktiven Projektquelle ist zwingend ein **BACKLOG_NO_DROP_GATE** auszuführen:

1. alle Backlog-/Roadmap-IDs und Planungsmarker wie `offen`, `Restpunkt`, `später`, `perspektivisch`, `Nicht Bestandteil`, `TODO`, `Folgeblock` sowie historische Stufenbezeichnungen wie `S1..S9` inventarisieren;
2. jeden Fund genau einem bestehenden/neuen Master-Ledger-Eintrag oder einem belegten `CLOSED`/`SUPERSEDED`/`REJECTED`-Status zuordnen;
3. historische Diskussion/Brainstorming, fachliche Freigabe, Implementierung, Buildnachweis und Feldevidenz nicht miteinander gleichsetzen;
4. ungeklärter Fund = `BACKLOG_NO_DROP_GATE=FAIL`; die Quelle darf dann noch nicht entfernt werden.

Das Master-Ledger wird bei jedem künftigen Release als Snapshot im Release-ZIP mitgeliefert.

## 6b. Releasegekoppelte Architektur-, Spezifikations- und Historienpflege (Beschluss 19.10.2026)

**UML_RELEASESTANDARD_APPROVED_20261022 – dauerhaft:** Ab dem nächsten neu gebauten Produktrelease gehört ein versionierter, gegen den aktuellen Sourcebaum geprüfter UML-Regleratlas als verbindlicher Teil des bestehenden releasegekoppelten As-built zu `docs/architecture/uml/`. Zum Pflichtumfang gehören kanonische editierbare Diagrammquellen, ohne Pi-Renderer lesbare SVG/PNG, offline-Index, nachvollziehbare Source-Traceability, Änderungs-/Review-Matrix und Integritätsmanifest. Relevante Control-/Safety-/Command-/Integration-/Statusänderungen aktualisieren betroffene Diagramme **im selben Entwicklungsblock**; nicht betroffene Blätter erhalten `REVIEWED_UNCHANGED` mit Sourcebegründung. Historische UML-Originale sind Provenienz und dürfen nicht ungeprüft als aktueller As-built ausgegeben werden. Handbuch-/Datenblattverweise zum konkreten Release pflegen. Vollständige Abnahme nach `06` §13 und bestehendem Checkpoint-/No-Drop-Vertrag; diese dauerhafte Dokumentationsfreigabe autorisiert keine eigenständige Controller-/Safety-Semantikänderung und keinen zusätzlichen Sofort-Release.

- Die zum konkret ausgelieferten Softwarestand passende **technische As-built-Dokumentation** gehört dauerhaft in den versionierten Sourcebaum unter `docs/` und wird mit jedem relevanten Release mitgeliefert. Sie beschreibt reale Funktionsgrenzen, Zustands-/Datenflüsse, Schutz-/Command-Verantwortlichkeiten, Settings-/Diagnosevertrag, Sourceverweise und Release-/Buildzuordnung. Keine Implementierungsbehauptung aus einem Entwurf ableiten.
- **Spezifikationen** (Draft/freigegeben/implementiert/historisch), **Architekturentscheidungen** einschließlich Alternativen, **As-built-Architektur** und **historische Belege** sind getrennt zu kennzeichnen und gegenseitig zu verlinken. Das historische Original wird nie stillschweigend in eine aktuelle Freigabespezifikation umetikettiert.
- Zu einem größeren Funktions-/Architekturblock gehören: fachlicher Zweck, erwarteter bzw. belegter Nutzen, Anwendbarkeit/Nichtfälle, Safety-/Hardwaregrenzen, reale Eingriffs- und Beobachtungspfade, relevante Entscheidungen sowie Abnahmekriterien. Bei Änderungen die entsprechenden `docs/`-Quellen **im selben Entwicklungsblock** aktualisieren, vor Source-Freeze gegen Code/Tests diffen.
- **Historie ausdrücklich erwünscht:** leicht zugängliche vorhandene Original-Spezifikationen, ADR-/Entscheidungsbelege und releasebezogene Architekturstände mit Originalname, Datum, Herkunft, Releasebezug, Hash (soweit verfügbar) und Status in `docs/history/` bzw. `docs/decisions/` übernehmen oder referenzieren. Chronologie/Versionsdeltas nur soweit verlässlich belegbar und mit vertretbarem Aufwand. Fehlende Originale als `MISSING_ORIGINAL` kennzeichnen; Rekonstruktionen als solche ausweisen, keine künstlichen „Originale“ herstellen und kein aufwendiges Rückwärtsprojekt als allgemeines Releasegate.
- Trennung der Autoritäten: `05_ZEC_BACKLOG_AND_ROADMAP.md` bleibt alleinige Master-Ledger-/Roadmapautorität; `docs/ZEC_Master_Backlog.md` ist ein eingefrorener Release-Snapshot. Die reale Sourcebasis schlägt ältere historische Spezifikationen.
- Dokumentationspflege ist Bestandteil künftiger Entwicklungs-/Release-Checkpoints und unterliegt Source-Manifest-, SHA256-/ZIP-/Fresh-extract-Integrität. Das formale Gate und die minimalen Dateitypen sind in `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md` § 13 beschrieben. Keine nachträgliche Änderung bereits ausgelieferter ZIP-Dateien unter derselben Versions-/Buildidentität.

## 7. Build- und Releasepflichten

Vor technischer Freigabe mindestens:

- isolierte Arbeitsbasis aus verifizierter Quelle;
- SHA256-/Paket-/Manifestprüfung;
- vollständige bestehende Tests plus neue Regressionstests;
- Syntax-/Compileprüfungen;
- `ResourceWarning=error`-Gate;
- No-Regression-/Differentialnachweise für geschützte Bereiche;
- finales ZIP erneut frisch extrahieren und paketbezogene Gates darauf ausführen;
- vollständige Änderungsliste;
- dokumentierter Exit-Gate-Status und bekannte Restpunkte;
- Installations- und Rollbackhinweise;
- aktuelles technisches Datenblatt gemäß `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md`.

Build-PASS ist nicht gleich Produktiv-PASS.

## 8. Sicherheits- und Betriebsprinzipien

- Fail closed bei Ambiguität in Recovery-, Deployment- und Safetyentscheidungen.
- Keine stillen Reparaturen kritischer Konfigurationen oder Recovery-Metadaten.
- Sicherheitsrelevante Null-/Neutralbefehle sind aktive Kommandos und müssen in Wirkung und Recovery beobachtet werden.
- Keine unnötigen Command-Wiederholungen, Richtungswechsel oder Hardwarezyklen.
- Keine blockierenden externen Operationen im Regelzyklus.
- Spezifische Anlagenwerte dürfen nicht als neutrale Defaultempfehlung in die Software einfließen.
- Änderungen am Regler-/Commandpfad müssen `03_ZEC_CONTROL_AND_SAFETY_INVARIANTS.md`, Analyse-Regelwerk und Hardwareschonungs-Regelwerk erfüllen.


## 8a. Ressourcensichere Analyse auf dem produktiven Raspberry Pi

Der produktive Raspberry Pi 3B+ ist zugleich Regelungs-, EVCC- und Analysehost. Diagnose darf den Regelbetrieb nicht durch ungebundene Ressourcenbelegung beeinträchtigen. Verbindlich gilt:

- große Measurement-V4-/Log-Historien ausschließlich **streaming- bzw. bounded-memory** verarbeiten;
- keine vollständige Historie per `list(rows)`, DataFrame oder vergleichbarer Materialisierung in RAM laden;
- Analysewerkzeuge mit internem Vollhistorien-Load dürfen auf dem produktiven Pi nur gegen vorher begrenzte Ausschnitte ausgeführt werden;
- für lange Zeiträume bevorzugt erst ressourcenschonend extrahieren/verdichten und die fachlich schwere Analyse anschließend auf dem begrenzten Artefakt durchführen;
- Ringpuffer, Ausgabedateien und temporäre Artefakte begrenzen; bei langen passiven Läufen Rotation/Größenlimit vorsehen;
- CPU-/I/O-intensive read-only Analysen auf dem Real-Pi mit niedriger Priorität (`nice`/`ionice`) und, soweit sinnvoll, mit Zeit-/Speichergrenzen ausführen;
- ein Analyseprozess darf weder ZEC noch EVCC, MQTT, Netztelemetrie oder andere produktive Dienste durch RAM-/Swap-/I/O-Druck faktisch außer Betrieb setzen;
- bei unbekanntem Ressourcenverhalten eines neuen Tools zuerst einen kleinen repräsentativen Ausschnitt oder einen synthetischen Stresstest verwenden;
- nach einem Analyseabbruch oder Reboot Ursache und Datenintegrität prüfen, bevor derselbe Analyseweg erneut ausgeführt wird.

Auslöser dieser Regel ist der reale Vorfall vom 25.09.2026: ein unbounded Python-V4-Analysepfad materialisierte vollständige Row-Dictionaries über einen langen Zeitraum, worauf der Raspberry Pi nicht mehr erreichbar war und neu gestartet werden musste. Ein Kernel-OOM-Beleg blieb wegen fehlender historischer Journal-Evidenz offen; der ressourcenproportionale Analyseansatz gilt unabhängig davon als unzulässig.

## 9. Antwort- und Ausführungsstil

- Kommunikation bevorzugt Deutsch, technisch präzise und handlungsorientiert.
- Raspberry-Pi-Anweisungen als Bash, nicht PowerShell.
- Bei komplexer technischer Arbeit geschlossene Arbeitspakete und konsolidierte Befehlsblöcke.
- Keine Behauptung über Artefakte, Dateien, Builds oder Testergebnisse ohne tatsächlich zugängliche Evidenz.
- Funktionsbezeichnung in Prosa/Logs/Reports: **„Fast Capture“**; **„FastC“** nur bei echter Platzknappheit; **„Fast“ allein** vermeiden. Bestehende technische Keys/Fieldnamen werden nicht umbenannt.
