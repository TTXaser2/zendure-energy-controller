# ZEC – Release & Handover Process

Stand: 11.09.2026
Status: kanonisch – inklusive dauerhaftem Datenblatt-Releasevertrag

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
- Installationsbefehle
- Rollbackhinweis
- Git-Commit-/Tag-Vorschlag

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

## 5. Feldabnahme

Build-PASS ist nicht gleich Produktiv-PASS.

Nach Installation mindestens:

- Version/Build-ID
- Dienststatus
- `/health`
- `/ready`
- für den Release relevante Funktions-/UI-Pfade
- reale physikalische Wirkung bei Regler-/Commandänderungen

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

Der neue Chat verwendet diese Übergabe als verbindlichen Startpunkt.

## 7. Projektquellenpflege

Nach Abschluss größerer Blöcke prüfen, ob neue dauerhafte Entscheidungen in die kanonischen Quellen gehören. Versionsspezifische Releasebelege anschließend aus aktiven Projektquellen entfernen und extern archivieren, sobald ihre dauerhaften Aussagen kanonisiert wurden.

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
- Standardsupportbundle enthält keine rohe Konfiguration/Secrets;
- Uninstaller-Preflight ist mutationsfrei; Fresh-Reset endet in CLEAN_FRESH_INSTALL;
- Benutzerdatenbackup und optionaler Measurement-Einschluss entsprechen ihrem Vertrag;
- bestehende Diagnose-/Analysefunktionen bleiben regressionsfrei.

Vor PRODUCTIVE-PASS eines erstmalig Fresh-Install-fähigen Hauptreleases ist zusätzlich mindestens ein echter Clean-Fresh-Install-Feldtest auf einem vorbereiteten Raspberry-Pi-OS-System ohne aktive ZEC-Installation Pflicht. Ein Build-/Harness-/Dry-Run-Nachweis ersetzt diesen realen Feldtest nicht.
