# ZEC – Release & Handover Process

Stand: 19.10.2026
Status: kanonisch – inklusive dauerhaftem Datenblatt-, Release-Hygiene- und Build-Evidence-Vertrag

## 1. Entwicklungsblock starten

Vor Codeänderung:

1. aktuelle Quellbasis tatsächlich zugänglich machen
2. Version, Build-ID und SHA256 verifizieren
3. freigegebenen Scope lesen
4. geschützte Bereiche und No-Regression-Anforderungen bestimmen
5. bestehende Tests/Syntax/Manifest prüfen
6. isoliertes Arbeitsverzeichnis anlegen

Keine behauptete Wiederverwendung verlorener oder nicht zugänglicher interner Artefakte.

## 2. Umsetzung

- freigegebenen Block eigenständig vollständig umsetzen
- keine Mikrofreigaben für bereits entschiedene Details
- bei Scope-Konflikt oder notwendiger Änderung geschützter Bereiche stoppen
- keine produktive Installation durch den Build selbst

## 3. Exit-Gate

Pflichtausgabe mindestens:

- vollständiger ZIP-Pfad/Dateiname
- SHA256
- Größe
- ZIP-Root
- Version und Build-ID
- Test- und Collectionzahlen
- pytest-Subtests
- ResourceWarning-Ergebnis
- Syntaxprüfungen
- geänderte/neue/gelöschte Dateien
- No-Regression-/Byteidentitätsnachweise
- Browser-/Integrationssmokes
- Exit-Gate
- bekannte Restpunkte
- Master-Backlog-/Changelog-Delta und `BACKLOG_NO_DROP_GATE`-Status
- bei mitgelieferten Analyse-/Forensikwerkzeugen: dokumentierter bounded-memory-/Langzeitvertrag oder explizit begrenzter Einsatzbereich
- Installationsbefehle
- Rollbackhinweis
- Git-Commit-/Tag-Vorschlag
- letzte Checkpointidentität samt SHA256, Bibliothekspfad und `CHECKPOINT_LIBRARY_GATE`-Nachweis (bei wesentlichen seitdem erfolgten Änderungen neuer Gate-Lauf nötig)

Das finale ZIP selbst erneut entpacken und daraus die Releasegates wiederholen bzw. die paketbezogenen Gates verifizieren.

## 4. Installerprinzip

- Preflight vor Dienststopp
- vollständiges Rollback-Backup
- Config-/Root-Artefakt-Backup
- idempotente Migration
- finale lokale Prüfung im Installationsverzeichnis
- Dienststart
- bounded Installationsabnahme
- automatischer Rollback bei echtem Fehler
- Node.js darf auf dem Pi keine Produktivvoraussetzung sein, wenn JS buildseitig per Manifest abgesichert ist
- **Regulärer Real-Update-Ablauf:** Paket-SHA/ZIP prüfen, frisch entpacken und den normalen Installer einmal starten. Dieser führt den vollständigen internen Preflight vor jeder Mutation aus und setzt bei PASS unmittelbar Backup/Installation/Abnahme fort. Ein separater `--preflight-only`-Zwischenschritt ist nur für gezielte mutationsfreie Diagnose-/Vertragsprüfungen erforderlich; der kombinierte Ablauf überspringt kein Preflight- oder Sicherheitsgate.

## 5. Feldabnahme

Build-PASS ist nicht gleich Produktiv-PASS.

Nach Installation mindestens:

- Version/Build-ID
- Dienststatus
- `/health`
- `/ready`
- für den Release relevante Funktions-/UI-Pfade
- reale physikalische Wirkung bei Regler-/Commandänderungen

### 5.1 Produktiv-Pi-Analyse und Forensik

Read-only bedeutet nicht automatisch betriebssicher. Analyse-/Forensikwerkzeuge, die auf dem produktiven Raspberry Pi laufen, müssen zusätzlich ressourcensicher sein:

- große Measurement-V4-/Log-Historien nur streaming/bounded-memory; keine ungebundene Vollmaterialisierung in Listen/DataFrames;
- lange Zeiträume zuerst ressourcenschonend filtern/verdichten; fachlich schwere Analyzer anschließend gegen begrenzte Artefakte ausführen, sofern der Analyzer intern Vollmaterialisierung verwendet;
- neue oder geänderte Langzeittools benötigen vor Real-Pi-Einsatz einen fokussierten Ressourcen-/Stresstest oder einen kleinen repräsentativen Vorlauf;
- auf dem Real-Pi niedrige CPU-/I/O-Priorität und, wo sinnvoll, explizite Zeit-, Speicher- und Ausgabegrenzen;
- passives Monitoring muss Logrotation/Größenlimits besitzen und darf keine konkurrierenden Netzwerk-Consumer erzeugen, sofern derselbe Telemetriepfad bereits produktiv gebunden ist;
- ZEC-/EVCC-/MQTT-Verfügbarkeit hat Vorrang vor Analysekomfort. Ein Tool, das den Host durch RAM-/Swap-/I/O-Druck unbenutzbar machen kann, ist für lange Real-Pi-Zeitfenster nicht freigabefähig.

Realfund 25.09.2026: Ein unbounded V4-Analysepfad mit vollständigen Python-Row-Dictionaries führte während der Analyse zu einem nicht mehr erreichbaren Raspberry Pi und erforderte einen Reboot. Ein nachfolgender Streaming-Extractor verarbeitete denselben Untersuchungsgegenstand bounded. Dieser Vorfall ist dauerhaft als Prozessleitplanke zu berücksichtigen.

## 6. Chatwechsel / Übergabe

Frühzeitig wechseln, wenn:

- Kontext stark angewachsen ist
- mehrere Entwicklungsstränge zusammenlaufen
- die Quellbasis unübersichtlich wird
- ein größerer nächster Build bevorsteht
- viele Artefakte/Tests/Entscheidungen im Chat akkumuliert sind

Vor dem Wechsel Übergabepaket erstellen mit:

- aktueller Codebasis + SHA256
- Spezifikation / Freigabestatus
- aktueller produktiver Identität
- relevante Feldabnahme
- bereits geschlossene Punkte
- offene Befunde
- Build-/Abnahmecheckliste
- Roadmap
- Startprompt
- bibliotheksgesicherte, erneut lesbare letzte vollständige Entwicklungsbasis mit SHA256 und Gate-Protokoll

Der neue Chat verwendet ausschließlich den neu gelesenen, hashverifizierten Archivstand als verbindliche Sourcebasis; fehlende spätere Arbeit wird nicht behauptet.

## 7. Projektquellenpflege und Backlog-Reconciliation

Nach Abschluss größerer Blöcke prüfen, ob neue dauerhafte Entscheidungen in die kanonischen Quellen gehören. Versionsspezifische Releasebelege können anschließend extern archiviert werden, **aber erst nach bestandenem Reconciliation-Gate**.

### 7.1 Master-Ledger

`05_ZEC_BACKLOG_AND_ROADMAP.md` ist die persistente Ledger-Autorität. Die Roadmap wird daraus abgeleitet. Relevante Punkte werden bei Abschluss nicht gelöscht, sondern auf `CLOSED`, `SUPERSEDED` oder `REJECTED` gesetzt und behalten Provenienz/Releasebezug.

### 7.2 BACKLOG_NO_DROP_GATE

Vor dem Entfernen/Archivieren einer Übergabe, Spezifikation, Work-Chat-Delta-Datei oder früheren aktiven Quelle:

1. Planungsmarker/IDs inventarisieren (`Backlog`, `Roadmap`, `offen`, `Restpunkt`, `später`, `perspektivisch`, `Nicht Bestandteil`, `TODO`, `Folgeblock`, `S1..S9` usw.);
2. jeden Fund gegen das Master-Ledger reconciliieren;
3. neue Punkte mit stabiler ID anlegen;
4. erledigte/ersetzte/verwarfene Punkte mit Beleg erhalten;
5. ungelöste Funde blockieren die Quellenbereinigung.

Eine manuelle Aussage „die wichtigen Punkte sind übernommen“ ist kein ausreichender Nachweis.

### 7.3 Master-Backlog als Releaseevidenz

Ab dem ersten Release nach Kanonisierung dieses Vertrags muss der Release-Tree enthalten:

```text
docs/ZEC_Master_Backlog.md
```

Die Datei ist ein Snapshot des kanonischen Ledgers zum Releasezeitpunkt und muss durch Source-/Package-Manifest sowie Fresh-extract-Gates erfasst sein. Sie darf offene/DEFERRED/SPEC_NEEDED-Einträge enthalten.

Ein nutzerlesbares Changelog kann aus den seit dem Vorgänger neu abgeschlossenen/releasezugeordneten Ledger-Einträgen abgeleitet werden. **Das Changelog ersetzt das Master-Ledger nicht.**

## 8. Technisches Datenblatt – dauerhafter Releasevertrag

Das technische ZEC-Datenblatt ist Bestandteil der Definition eines vollständigen Releases. Ab dem ersten Release nach Kanonisierung müssen im ausgelieferten Release-Tree immer beide aktuellen Fassungen vorhanden sein:

```text
docs/ZEC_Technisches_Datenblatt.pdf
docs/ZEC_Technisches_Datenblatt.docx
```

### 8.1 Inhaltsvertrag

- Das Datenblatt beschreibt ausschließlich den Ist-Zustand des konkret ausgelieferten Releases. Es ist kein Changelog und enthält keine Versionshistorie oder Vergleiche mit Vorgängerversionen.
- Releaseversion, Build-ID und Nachweisstatus müssen dem tatsächlich gebauten Paket entsprechen. Ein PRODUCTIVE-PASS darf nur genannt werden, wenn die reale Feldabnahme dieses Releases vorliegt.
- Hardware- und Softwarevoraussetzungen sowie die tatsächlich unterstützten Anlagenkonstellationen sind Pflichtbestandteile.
- Bestehende produktive Funktionen bleiben im Datenblatt enthalten, solange sie nicht tatsächlich aus dem Produkt entfernt oder als nicht mehr unterstützt beschlossen wurden. Ein Entwicklungsblock darf vorhandene Funktionen nicht allein wegen fehlender Änderung aus dem Datenblatt verdrängen.
- Solange beide Pfade produktiv unterstützt werden, gehören zur Netzleistungsmessung ausdrücklich SMA Energy Meter / Sunny Home Manager über Speedwire/UDP sowie Shelly Pro 3EM bzw. ein Shelly-kompatibler HTTP-Endpunkt.
- Theoretisch mögliche oder nur darstellbare Topologien dürfen nicht als aktiv unterstützt bezeichnet werden, wenn der zugehörige Regel-/Commandpfad nicht produktiv belegt ist.

### 8.2 Pflegezeitpunkt

Nach Stabilisierung des Releaseumfangs und vor dem finalen Source-Freeze/Installer-ZIP ist das Datenblatt gegen reale Sources, Settings/Profile bzw. Geräteprofile, unterstützte Hardwarepfade, Tests und den vorhandenen Feldnachweis zu aktualisieren. DOCX und daraus erzeugtes PDF werden vollständig gerendert und visuell geprüft.

### 8.3 Automatisierte Gates

Das Release-Gate muss mindestens maschinell bestätigen:

1. beide kanonischen Datenblattdateien existieren und sind nicht leer;
2. beide sind durch Source-/Package-Manifest bzw. paketbezogene Integritätsprüfung erfasst;
3. DOCX und Datenblatt-Metadaten tragen die aktuelle Releaseversion und Build-ID;
4. das Datenblatt enthält die Pflichtbereiche Hardware, Software, Anlagenkonstellationen und Netzleistungsmessung;
5. SMA-Speedwire und Shelly-kompatibler HTTP-Messpfad sind enthalten, solange beide produktiv unterstützt werden;
6. bekannte ältere ZEC-Releaseidentitäten stehen nicht als Produktidentität im aktuellen Datenblatt;
7. Fresh-extract des finalen Installer-ZIPs enthält und validiert beide Dokumente.

Die Automatisierung ersetzt nicht die fachliche und visuelle Review des Datenblatts.

### 8.4 Exit-Gate

Das Exit-Gate nennt den Datenblattstatus ausdrücklich. Ein Release ist dokumentarisch unvollständig und darf kein vollständiges Release-PASS erhalten, wenn DOCX/PDF fehlen, nicht zum Release passen, die Pflichtinhalte nicht abdecken oder die Fresh-extract-Prüfung des Datenblatts nicht PASS ist.

## 9. Deployment-Suite, Fresh Install und Support-Hardening

Ab V16.0.0 ist der kanonische Deployment-Einstiegspunkt:

```text
tools/install_zendure_controller.sh
```

`tools/update_zendure_controller.sh` darf als rückwärtskompatibler Wrapper fortbestehen, ist aber nicht mehr der kanonische Installername. Zum Deployment-Vertrag gehört außerdem:

```text
tools/uninstall_zendure_controller.sh
```

### 9.1 Installationszustände

Installer und Uninstaller verwenden denselben Installationszustandsvertrag:

```text
SUPPORTED_UPDATE
CLEAN_FRESH_INSTALL
AMBIGUOUS_OR_PARTIAL_INSTALL
```

`AMBIGUOUS_OR_PARTIAL_INSTALL` ist fail-closed. Ein Update darf niemals automatisch in einen Fresh Install umgedeutet werden. Historische Backup-/Supportartefakte außerhalb der aktiven Installation zählen nicht als aktive Installation.

### 9.2 Mutationsfreier Preflight

Installer und Uninstaller müssen einen `--preflight-only`-Pfad besitzen. Dieser prüft den realen Installationszustand und die für den jeweiligen Lauf erforderlichen Voraussetzungen, verändert aber keine produktiven ZEC-Dateien, Dienste oder Konfiguration. Persistentes Preflight-/Installerlogging ist zulässig und ausdrücklich erwünscht.

Für den Installer umfasst der Preflight mindestens Paket-/Manifest-/Datenblattintegrität, Installationszustand, erforderliche Systemwerkzeuge/Pythonmodule, Zielpfade, WEB_PORT-Vertrag und Portbelegung. Fehlende Pakete werden nicht automatisch installiert; stattdessen wird vor jeder Produktivmutation mit einem konsolidierten Copy-Paste-Installationshinweis abgebrochen.

Ab V16.2.2 gehört zum Paket-/Manifestvertrag zusätzlich eine **fail-closed Release-Hygiene**: `.pytest_cache`, `__pycache__`, Python-Bytecode, sonstige volatile Toolcaches und Runtime-Datenbanken dürfen weder im freizugebenden Release-Tree noch im aktuellen Source-Manifest enthalten sein. Manifest-Erzeugung, Paket-Preflight und Zielprüfung müssen denselben Pfad-/Hygienevertrag verwenden. Ein Deployment darf nicht Dateien absichtlich ausschließen, die das anschließend geprüfte Zielmanifest weiterhin verlangt. Für Deployment-Suite-Änderungen ist dieser reale Copy-/Manifestvertrag für `SUPPORTED_UPDATE` und `CLEAN_FRESH_INSTALL` automatisiert nachzuweisen.

Ab V16.2.3 besitzt die Build-Testevidenz zusätzlich einen **kanonischen maschinenlesbaren Vertrag** (`ZEC_BUILD_EVIDENCE_V1`). Installer und Paketgates dürfen human-readable QA-Dateien nicht als implizite Parser-API verwenden. Maßgeblich ist der gemeinsame Verifier `tools/deployment_contract.py verify-build-evidence`. Er prüft fail-closed mindestens Releaseversion, Label, Build-ID, globalen PASS-Status, positive Testdateianzahl, vollständige Regression, identische Test-/Subtestzahlen im `ResourceWarning=error`-Lauf und die explizite Warnungssemantik `error::ResourceWarning`. Der echte Installer-Preflight muss genau diesen Verifier auf dem finalen Fresh Extract aufrufen; ein isoliert getesteter Verifier ohne Preflight-Integration reicht nicht als Releasegate.

### 9.3 Clean Fresh Install

Ein Clean Fresh Install erzeugt keine erfundene Produktivkonfiguration. Vor dem ersten gültigen Settings-Commit startet ZEC in `FIRST_INSTALL_SETUP` mit:

```text
/health alive=true
/settings erreichbar
config_health=missing
control_allowed=false
ready=false
```

`ready=false` ist in dieser Phase erwarteter Erfolg. MQTT-Verbindungsaufbau wird in `FIRST_INSTALL_SETUP` ausgesetzt; der Web-/Settingspfad bleibt verfügbar. Der Controllerdienst besitzt keine systemd-Abhängigkeit zu einem konkreten MQTT-Brokerdienst.

Ein optionaler Fresh-Install-`--web-port` muss im Bereich 1024..65535 liegen. Bis zum ersten kanonischen Settings-Commit darf ausschließlich `WEB_PORT` über das First-Install-Bootstrapartefakt autoritativ sein. Der erste Commit übernimmt den Wert in `config.json`; bis zum erforderlichen Neustart bleibt `control_allowed=false`.

### 9.4 WEB_PORT und dynamischer lokaler Endpunkt

Installer, Uninstaller und Support-/Diagnosewerkzeuge dürfen die lokale ZEC-API nicht hart auf Port 8080 voraussetzen. Maßgeblich ist der tatsächlich wirksame lokale Webendpoint aus Produktivkonfiguration, First-Install-Bootstrap oder dem dokumentierten Default. Portänderungen müssen serverseitig vor einem Neustart auf zulässigen Bereich und Bindbarkeit geprüft werden.

### 9.5 Uninstaller und Benutzerdatensicherung

Der Uninstaller darf ausschließlich ZEC-eigene aktive Artefakte entfernen. Betriebssystem, Netzwerk, MQTT-Broker, EVCC, allgemeine Python-/Systempakete und andere Anwendungen bleiben unangetastet.

Vor einer Entfernung ist eine lokale, restore-orientierte Benutzerdatensicherung standardmäßig aktiv. Sie darf echte Konfigurationsdaten enthalten und ist deshalb ausdrücklich kein extern teilbares Supportbundle. Ein Opt-out muss explizit und stärker bestätigt werden. Große Measurement-/Deep-Trace-Daten werden nur auf ausdrückliche Anforderung in dieses Backup aufgenommen.

Ein `--fresh-install-reset` ist erst erfolgreich, wenn der gemeinsame Zustandsdetektor anschließend `CLEAN_FRESH_INSTALL` meldet.

### 9.6 Secretsicherer gemeinsamer Supportvertrag

Fresh-Install-Fehler, Updatefehler und manuelle Third-Party-Supporterfassung verwenden einen gemeinsamen secretsicheren Diagnosekern. Das standardmäßig extern teilbare Support-ZIP darf keine rohe `config.json` enthalten. Bei Installerfehlern wird der Fehlerzustand vor einem Rollback erfasst; das Rollbackresultat wird anschließend demselben Diagnosevorgang hinzugefügt und das Bundle danach finalisiert.

Pflichtinhalte soweit verfügbar: Release-/Buildidentität, dynamischer lokaler Webendpoint, Dependency-Matrix, systemd/journald, HTTP-Snapshots, Installerlog und Bundlemetadaten.

### 9.7 Release- und Feldgates

Zusätzlich zu den allgemeinen Releasegates müssen Releases mit Änderungen an der Deployment-Suite mindestens automatisiert nachweisen:

- CLEAN_FRESH_INSTALL, SUPPORTED_UPDATE und fail-closed Partial-State;
- Fresh Install mit Defaultport und alternativem WEB_PORT;
- Ports <1024 sowie belegte Ports blockiert;
- kein lokaler Mosquitto als Installationsvoraussetzung;
- fehlende Runtimeabhängigkeit führt vor Mutation zum erklärten Preflight-Abbruch;
- FIRST_INSTALL_SETUP ohne MQTT-Connect und mit gesperrter Regelung;
- erster Settings-Commit übernimmt Bootstrapwerte; Restart führt in NORMAL;
- Update funktioniert mit Standard- und abweichendem WEB_PORT ohne harte `:8080`-Annahme;
- Fehlerzustand wird vor Rollback erfasst und Rollbackresultat im selben Supportvorgang dokumentiert;
- ein einzelner Installerfehler finalisiert Supportcapture/Rollback genau einmal; vererbte `ERR`-Traps aus Subshells dürfen keinen zweiten Diagnose-/Rollbackvorgang auslösen;
- Standardsupportbundle enthält keine rohe Konfiguration/Secrets;
- Uninstaller-Preflight ist mutationsfrei; Fresh-Reset endet in CLEAN_FRESH_INSTALL;
- Benutzerdatenbackup und optionaler Measurement-Einschluss entsprechen ihrem Vertrag;
- Build-Testevidenz wird über den kanonischen maschinenlesbaren Evidence-Vertrag geprüft; der echte Paket-Preflight ruft denselben Verifier auf und parst keine Freitextmarker;
- bestehende Diagnose-/Analysefunktionen bleiben regressionsfrei.

Vor PRODUCTIVE-PASS eines erstmalig Fresh-Install-fähigen Hauptreleases ist zusätzlich mindestens ein echter Clean-Fresh-Install-Feldtest auf einem vorbereiteten Raspberry-Pi-OS-System ohne aktive ZEC-Installation Pflicht. Ein Build-/Harness-/Dry-Run-Nachweis ersetzt diesen realen Feldtest nicht.

## 10. Persistente Installations- und Feldevidenz

Maschinenlesbare Installationsreports und andere Nachweise, die für eine spätere Feldabnahme benötigt werden, dürfen nicht ausschließlich in flüchtigen Pfaden wie `/tmp` liegen.

Ab V16.2.4 ist dieser Vertrag produktiv umgesetzt:

- der Installer schreibt den maschinenlesbaren Installationsreport atomar und timestamped persistent in den bestehenden Download-/Evidence-Bereich `/home/pi/Downloads`;
- `/tmp` ist ausschließlich zusätzliche Kompatibilitätskopie und keine primäre Evidenzquelle;
- ein explizites `--install-report` des Feldabnahmetools gewinnt immer; ohne expliziten Pfad wird der neueste persistente releasespezifische Report bevorzugt, danach ausschließlich die definierte `/tmp`-Kompatibilitätskopie;
- Reportformat, Zielrelease, Build-ID und Installationsmodus werden fail-closed geprüft;
- bei Updates werden Backup-Pfad, SHA256 und Größe aus der realen referenzierten Datei verifiziert;
- fehlende Evidenz wird als WARN/FAIL gemäß Vertrag ausgewiesen und niemals synthetisch als Originalartefakt rekonstruiert.

Nach einer realen Feldabnahme sind flüchtige `/tmp`-Artefakte vor Neustart, Cleanup oder destruktivem Test in ein persistentes, gehashtes Evidenzarchiv zu sichern.

## 11. Externe Entwicklungscheckpoint-Pflicht – CHECKPOINT_LIBRARY_GATE

**Normative Ausführung: `01_ZEC_PROJECT_RULES.md` § 3.** Nach jedem größeren Sourceblock und vor weiterer umfangreicher Arbeit ist ein vollständiges, ZIP-/CRC-geprüftes Checkpointarchiv mit SHA256 zu erstellen, in `ZEC - Zendure Energy Controller/Checkpoints/` der **persönlichen ChatGPT-Bibliothek** hochzuladen und **unabhängig als raw file zurückzulesen**. SHA256, Datei-Bytezahl und ZIP-Integrität müssen exakt übereinstimmen. Vollständige Sources, Tests, Dokumente, Manifest-/Buildgrundlagen und notwendige Evidenz sichern; Produktivdaten und Secrets nicht ungeschützt beifügen.

Die Checkpoint-Evidenz nennt `CHECKPOINT_LIBRARY_GATE=PASS|FAIL|NOT_EVALUABLE`, Dateiname, SHA256, Größe, Arbeitsbasis, Zeitstempel, Bibliothekspfad, Uploadobjekt/Referenz, Rücklesetest sowie seitdem erfolgte Änderungen. `EXTERNALLY_SECURED` darf nur bei `PASS` behauptet werden; `LOCAL_ONLY`, `UPLOAD_PENDING`, `LIBRARY_UNVERIFIED` und Sandbox-Downloadlinks sind **keine** externen Sicherungen.

**Harter Entwicklungsgate:** Nach wesentlichen ungesicherten Änderungen keine weiteren Sourceblöcke, längeren QA-/Dokumentationsphasen, Chatübergaben als 'gesichert' oder Release-Freeze. Bei fehlendem Bibliothekszugriff, Quota, Uploadfehler, fehlendem Rücklesen oder Hashabweichung `FAIL` und stoppen; eine alternative nachweislich dauerhafte Sicherung nur nach Nutzerabstimmung. Beim Wechsel in einen neuen Chat die letzte gesicherte Archivkopie **aus der Bibliothek** wieder einlesen und verifizieren, statt nur dem Chatprotokoll zu vertrauen.

**Retention:** Keine ungefragte Löschung. Quartalsweise, bei größeren Releases oder bei Kapazitätswarnungen eine Bestands-/Speicherprüfung anbieten. Vor einer manuell freigegebenen Bereinigung Nachfolger, Rollback-, Branch-, Evidenz- und Backlog-/No-Drop-Anker prüfen; mindestens letzte fünf verifizierte Checkpoints des aktiven Zweigs sowie Release-/Freeze-Anker erhalten. Bibliothek/Projektquellen sind unterschiedliche Speicherflächen. Jede tatsächliche Löschung wird separat mit Objekt, Umfang und Grund dokumentiert.

## 12. Master-Backlog-/Changelog-Gate

Für jeden Release nach Einführung dieses Vertrags gilt zusätzlich:

- `docs/ZEC_Master_Backlog.md` existiert und ist nicht leer;
- Snapshot und kanonisches Master-Ledger stimmen für den Releasefreeze in ID/Status/Provenienz überein;
- alle im Entwicklungsblock neu entstandenen offenen Punkte sind im Ledger enthalten;
- offene Ledgerpunkte mit `RELEASE_BLOCKER_NEXT_RELEASE` oder `FIX_REQUIRED_NEXT_RELEASE`, die dem anstehenden Produktrelease zugeordnet sind, blockieren Source-Freeze/Release-PASS bis Implementierung und gefordertem Regressionnachweis;
- alle im Release abgeschlossenen Punkte besitzen Release-/Buildbezug;
- `BACKLOG_NO_DROP_GATE=PASS` für alle im Zuge des Releases entfernten/archivierten Übergaben/Overlays;
- Fresh-extract enthält den Snapshot und Manifestprüfung deckt ihn ab;
- ein optionales Changelog wird aus dem Ledger abgeleitet und darf keine offenen/verworfenen Punkte aus dem Ledger löschen.


## 13. Architektur-/Spezifikations-/Historien-Dokumentation im Source-Release (Beschluss 19.10.2026)

**UML_RELEASESTANDARD_APPROVED_20261022 – zusätzliche Pflicht zu §13.3:** Ab dem nächsten neu gebauten Produktrelease enthält das vorhandene Release-`docs/architecture/uml/` den UML-Regleratlas als Teil des `DOC_ARCH_HISTORY_GATE`. `DOC_UML_RELEASE_GATE` prüft fail-closed Release-/Buildidentität, ≥19 vollständig aufgelöste Altblatt-IDs mit editierbaren kanonischen DOT-Quellen, offline SVG/ggf. PNG, konsistente Hashes, Syntax, Dokument-/HTML-/Handbuch-Links, belegte Source-Traceability, Status-/Impactentscheidung aller Blätter und aktuelle fachliche Reviewfreigabe. `.puml` nur bei tatsächlicher PlantUML-Verifikation als geprüft behaupten; ansonsten `SECONDARY_UNVERIFIED` oder historische Originale. Alle ausgelieferten Sources/Renderartefakte müssen im Source-/Paketmanifest und im frisch entpackten finalen ZIP nachvollziehbar geprüft werden. Prüfwerkzeuge laufen beim Build; kein Graphviz/PlantUML/Node.js auf dem Produktiv-Pi erforderlich. **Das bestehende Release-Gate bleibt bei fehlender fachlicher Abnahme FAIL**, auch wenn reine Render-/Hashgates technisch PASS sind. Dokumentationsgates beweisen keine reale Hardwarewirkung. Diagramm-Impact wird bereits im Sourceblock berücksichtigt; kein separates Freigabe- oder Roadmap-System, keine rückwirkende Änderung bereits ausgelieferter Release-ZIPs. Der bestehende `BACKLOG_NO_DROP_GATE` und `CHECKPOINT_LIBRARY_GATE` bleiben verbindlich.

### 13.1 Geltung und Struktur

Ab dem **nächsten Entwicklungs-/Produktrelease**, ohne rückwirkende Veränderung des veröffentlichten V17.0.2-Pakets, wird die technische Dokumentation in `docs/` mit Sources, Checkpoint und Release versioniert. Die bewährten bestehenden Benutzerhandbücher, das technische Datenblatt und `docs/ZEC_Master_Backlog.md` bleiben erhalten.

Empfohlene, schrittweise einzuführende Pfade:

```text
docs/INDEX.md
docs/architecture/        # As-built der tatsächlich implementierten, relevanten Funktionen
docs/specifications/      # produktive/freigegebene Spezifikationen, Version/Status klar markiert
docs/decisions/           # ADR / retrospektiv belegte Architekturentscheidungen
docs/history/             # alte Original-Specs, belegte ältere Stände, Provenienzindex
```

Alle Pfade sind relativ zum Source-Root. Alle Links müssen nach Fresh-extract innerhalb des ZIPs auflösbar sein, sofern ihr Ziel Teil des Releasebaums ist. Die konkrete Benennung darf aus Kompatibilitätsgründen abweichen, sofern die semantischen Dokumenttypen sauber trennbar bleiben.

### 13.2 Dokumentstatus, Wahrheit und Historienübernahme

- `AS_BUILT`: aktuell gegen Release-/Sourceversion geprüfte Beschreibung, keine Behauptung einer Feldfreigabe.
- `SPEC_DRAFT`: fachlicher Entwurf, keine Sourcefreigabe.
- `SPEC_APPROVED`: ausdrücklich für ihren Block freigegebener Sollvertrag, nicht automatisch Implementierungsnachweis.
- `HISTORICAL_ORIGINAL`: unveränderte archivierte Originalquelle; ihr damaliger Status bleibt erhalten.
- `RETROSPECTIVE_RECONSTRUCTION`: kenntlich gemachte nachträgliche Zusammenfassung mit belegten Referenzen, nicht als historisches Original ausgeben.
- `MISSING_ORIGINAL`: historisch belegter Verweis ohne verfügbare Originalbytes; darf nicht als eingebettet/prüfbar gelten.

Jedes wesentliche Dokument erhält Titel, Dokumenttyp/Status, Basisrelease/-build bzw. Geltungsbereich, Datum, relevanten Source-/Test-/Evidenzbezug und Verknüpfung zum Master-Ledger soweit einschlägig. Der `docs/INDEX.md` ist ein laufend gepflegter Navigations- und Zustandsindex, **keine zweite Roadmap**.

Historische Originale sind bei vertretbarem Aufwand aufzunehmen. Beginn mit der **vorhandenen Fast-Capture-V16.0.2-Originalspezifikation** (unverändert; noch nicht implementiert im damaligen Dokument), einem expliziten V16.2.5-Revalidierungsverweis mit `MISSING_ORIGINAL` und einer gegen V17.0.2 geprüften As-built-Beschreibung; später S3. Nachträglich leicht greifbare Spezifikationen/Entscheidungen können fortlaufend ergänzt werden; keine Pflicht zur spekulativen Vollrekonstruktion aller alten Releases vor dem nächsten Feature-/Winterrelease.

### 13.3 Scope und Release-Gates

1. Im Scope-/Checkpointplan kennzeichnen, welche Module/Regelkontrakte, Diagramme, Architekturdokumente, Specs oder ADR durch den Sourceblock betroffen sind. Größere neue Funktionen erfordern einen As-built-Eintrag bzw. ein begründetes Update; kleinere reine UI-/Hotfixarbeiten erfordern mindestens Prüfung/Änderungsvermerk, nicht blind eine vollständige Neudokumentation.
2. Bei Source-Freeze Ist-/Sollstatus gegen tatsächliche Code-Consumer, Settings-Registry, Limits, Tests, relevante Feldnachweise und releasegenaue Buildidentität prüfen. `AS_BUILT` darf keinen nur vorgeschlagenen Zweig als aktiv ausweisen. Unreconciled-Mismatch = Dokumentationsgate FAIL für den betroffenen Scope.
3. Dateien und Querverweise in Source-/Paketmanifest sowie finaler ZIP-/Fresh-extract-Integrität prüfen. Einfache Link-/Existenz-/Status- und Hashprüfungen werden in den Release-Workflow integriert. Nicht existierende historische Originale dürfen explizit als `MISSING_ORIGINAL` referenziert werden, nicht als erfolgreicher Dateilink.
4. Der freigegebene Sollvertrag und dessen Änderungen gegenüber der implementierten Realität müssen nachvollziehbar sein. Ein `docs/`-Original darf nicht stillschweigend überschrieben oder aus der Historie entfernt werden; Ergänzungen sind als neue Version oder nachvollziehbares Addendum vorzunehmen.
5. Die vollständige technische Dokumentation einschließlich nachvollziehbarer, **mit vertretbarem Aufwand verfügbarer** Historie wird im jeweiligen Checkpoint/Release mitgeliefert. `docs/ZEC_Master_Backlog.md` bleibt ein Snapshot; an Ledger/Prozessquellen gilt weiterhin `BACKLOG_NO_DROP_GATE` vor Entfernung/Archivierung.
6. Exit-Bericht nennt `DOC_ARCH_HISTORY_GATE=PASS|FAIL|NOT_EVALUABLE`, vorhandene/fehlende Historienbelege und vorgenommene Änderungen. `NOT_EVALUABLE` darf nicht als vollständiger Release-PASS etikettiert werden, wenn aktuelle As-built-Dokumentation verpflichtend betroffen ist. Fehlende *historische* Originale sind bei dokumentierter Suche/Provenienz dagegen kein pauschales Releasehindernis.

**Abgrenzung:** Diese Prozessänderung implementiert selbst keinerlei Regler-/Installeränderung; die erforderlichen Build-Harness-/Manifest-Checks werden im ersten betroffenen künftigen Sourceblock konkret integriert und regressionsgeprüft. Bekannte Fixpflichten `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` bleiben davon unabhängig bestehen.
