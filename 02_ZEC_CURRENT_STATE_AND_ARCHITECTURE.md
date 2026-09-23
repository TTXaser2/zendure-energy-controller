# ZEC – Current State & Architecture

**Stand:** 22.09.2026  
**Status:** kanonischer aktueller Architekturstand; versionsspezifische Feldidentität siehe `07_ZEC_CURRENT_RELEASE_AND_FIELD_STATUS.md`

## 1. Systemkontext

ZEC ist eine lokale Speichersteuerung für einen aktiv gesteuerten Zendure-Speicher und kann optional einen Primärspeicher koordinieren. Im aktuellen produktiven Anlagenkontext läuft ZEC auf einem Raspberry Pi 3B+; Mosquitto und EVCC sind dort ebenfalls vorhanden. Der V16-Deploymentvertrag setzt jedoch keinen lokalen Mosquitto-Dienst als Installationsvoraussetzung voraus.

Unterstützte Netzleistungsmesspfade umfassen:

- SMA Energy Meter / Sunny Home Manager über Speedwire/UDP;
- Shelly Pro 3EM bzw. Shelly-kompatiblen HTTP-Messpfad.

Der aktuelle Primärspeicher kann source-neutral angebunden werden. Unterstützte Profile im V16-Sourcebestand sind:

- `evcc_standard`;
- `custom` für benutzerdefiniertes MQTT;
- `modbus_template` für direkte Modbus-TCP-Anbindung.

Im real abgenommenen aktuellen System läuft `modbus_template` mit einem SMA Sunny Island über `192.168.0.76:502`, Unit-ID 3. Der Darstellungsname des Primärspeichers ist konfigurierbar; beim Modbus-Template kann ein Template-Default als Fallback dienen.

V16.1.0 erweitert die Template-Architektur um optionale read-only Geräte-Capabilities. Das Profil `sma_sunny_island` stellt `current_discharge_floor_soc` über Register `31009` (FC03, U32/FIX0) bereit. Pflichtpoll für Primärspeicher-Leistung und Roh-SOC sowie Capability-Poll besitzen getrennte Freshness-/Validity-Zustände. Ein Capability-Fehler macht einen ansonsten gesunden Pflichtpfad nicht automatisch ungesund; alte Capability-Werte werden bei Freshness-Verlust oder Quellen-/Profilwechsel invalidiert.

Aus frischem Roh-SOC und frischer Entladeuntergrenze kann diagnostisch `primary_usable_soc_percent = clamp((raw_soc-floor)/(100-floor)*100, 0..100)` gebildet werden. Diese Größe besitzt in V16.1.0 **keine Reglerwirkung** und ersetzt den Roh-SOC weder für FULL/IDLE-, Taper-/High-SOC-, Fast-Capture- noch Safety-/Limitentscheidungen.

## 2. Primärziel und Reglerbild

ZEC minimiert vermeidbaren Netzbezug und vermeidbare Netzeinspeisung innerhalb der verfügbaren Speicherleistung und Schutzgrenzen. Primärspeicherpriorität, Cross-Charge-Schutz, Commandwirkung und Hardwareschonung bleiben verbindliche Nebenbedingungen.

Für strategische Ladeverteilung gilt zusätzlich die normative Grenze:

> Aktuell vermeidbare Einspeisung hat Vorrang vor strategischer Ladeverteilung.

Der aktuelle V16-Regler enthält hierfür bereits eine Export-Capture-Untergrenze in relevanten Harvest-/High-SOC-Pfaden. Strategische Shares dürfen nicht dazu führen, dass aktuell nutzbarer Überschuss eingespeist wird, obwohl Zendure noch Ladeleistung und Headroom besitzt.

## 3. Settings-/Config-Architektur

Kanonischer Vertrag:

- `SettingsRegistry` ist Schemaautorität für Typ, Default, Bereich, Kategorie, Abschnitt, Sichtbarkeit, Apply-/Restart-Semantik und strukturierte Hilfemetadaten.
- `config.json` enthält persistierte Nutzerwerte und bleibt manueller Recoveryweg.
- `configured` = konfigurierte/persistierte Nutzersicht.
- `effective` = tatsächlich laufende Werte.
- `pending_restart` kennzeichnet Änderungen, deren Wirkung einen Dienstneustart erfordert.
- Ab V16.2.4 sind Produktfreigabe und aktuelle Hardware-/Konfigurationsanwendbarkeit getrennt: `SurfaceState=operational|target_only` bestimmt, ob ein Setting im Release überhaupt produktiv angeboten werden darf; `Applicability` bestimmt, ob ein operatives Setting in der aktuellen Topologie/Config sinnvoll sichtbar ist. `release_stage` und `origin` sind Provenienz, keine UI-Freigabeautorität.
- Die Primärspeicher-Aktivierung bleibt als operativer Einstieg erreichbar; abhängige Primärspeicherfelder reagieren auf den aktuellen Browser-Draft. Eine Darstellung von zwei Zendure-Entities erzeugt keine zweite Commandkonfiguration und schließt `ZEC-BL-MULTI-001` nicht.

Persistenz-/Validierungsprinzipien:

- Whole-File-Transaktion;
- exact-byte bzw. revisionsgebundene CAS-Prüfung;
- atomische Persistenz mit restriktiven Dateirechten;
- Unknown-Key-Erhalt;
- Secret-Redaktion und getrennte Secretoperationen `keep/replace/clear`;
- Preview vor Commit;
- keine stille Reparatur;
- Runtime-invalid verwendet den letzten gültigen Effective-Snapshot statt eine invalide Primärconfig aktiv zu übernehmen.

Die früher geplante strukturierte Settings-Hilfe ist produktiv umgesetzt. Die Registry besitzt Hilfemetadaten, Kategorie-/Abschnittshilfen und Handbuchreferenzen; die UI verwendet diese für geführte Erläuterungen.

## 4. Konfigurationsstände / Import / Export

Benannte Konfigurationsstände sowie Export-/Importpfade sind produktiv umgesetzt. Laden erfolgt nicht als blindes Direktaktivieren, sondern über Inspect/Preview, Migration/Validation/Diff und expliziten Commitvertrag. Secretschutz, CSRF- und SQLite-Härtung gehören zum bestehenden Vertrag.

## 5. Last-Good-/Startup-Recovery

ZEC besitzt einen A/B-Last-Good-Store mit Current-Pointer und manifest-/revisionsgebundener Validierung.

Grundsätze:

- Startup-Recovery ist zunächst passiv und sendet keine Gerätekommandos.
- `ready=false`, bis der vollständige Recovery-/Readiness-Preflight bestanden ist.
- Fehlt oder versagt der Current-Pointer, werden beide Slots unabhängig vollständig geprüft.
- Genau ein eindeutiger gültiger Slot darf als Recoverycandidate dienen.
- Sind beide gültig, entscheidet ausschließlich eine eindeutig höhere kompatible Manifest-Generation.
- Ambiguität, unbekanntes/invalide Generationsformat, Overflow oder inkonsistente Revisionen führen fail closed.
- Keine Auswahl anhand von mtime, Dateigröße, Dateiname oder vermuteter Schreibreihenfolge.
- Pointer und Slots werden im Startup nicht automatisch repariert.

Pointer-Reparatur ist ausschließlich eine geschützte Adminaktion mit vollständigem Reread, CAS und Auditierung.

## 6. Readiness-/Command-Nachweis

Readiness darf nicht allein aus MQTT-Verbindung oder Statusflags abgeleitet werden. Sie umfasst mindestens:

- frische Netzleistungsmessung;
- frischen Zendure-SOC;
- erforderliche Primärspeicher-/Cross-Charge-Daten; optionale Geräte-Capabilities wie der SMA-Entladefloor sind davon getrennte Diagnostik und keine eigenständige Readiness-Pflicht;
- verfügbaren und validen Commandpfad;
- vollständigen Command-State (`smartMode`, `acMode`, Input-/Output-Limit);
- statische Invarianten;
- Desired/Readback bzw. einen ausdrücklich erlaubten sicheren transienten Readbackzustand;
- keine aktiven harten Command-Guards;
- frische unabhängige Zendure-Leistungstelemetrie;
- gesunden Controllerzustand.

Publish ist kein Wirkungsnachweis. Commandwirkung wird mindestens in Richtung, Sollwerttracking und Systemziel getrennt bewertet. Kleine Sollwerte unter Diagnosegrenze sind `not_evaluable`.

## 7. Measurement / Storage

Measurement-V4 ist produktive Grundlage. V16.1.0 führt **254 Standard- bzw. 257 Extended-Felder**; die historischen RC17/RC16/RC15-Schemata bleiben bei Rekonstruktion mit **238/228/217** Feldern kompatibel. Floor-/usable-SOC-Felder sind additive Diagnoseevidenz und ändern keine Reglersemantik. Für SQLite/Measurement-Storage gelten:

- keine teuren Vollinventuren im normalen Request-/Regelpfad;
- Storage-Status aus gecachtem Snapshot;
- Vollscan/Inventory-Refresh asynchron und Single-Flight;
- SQLite als persistente Messdatenbasis;
- Online-Snapshot-/VACUUM-INTO-artige Verfahren dürfen produktive Regelung nicht stoppen.

Graph Core V3 ist die aktuelle persistente Graphbasis. Bestehende Historie wird bei Updates geschützt/preserviert.

## 8. Graph-/Diagnosearchitektur

Produktiv vorhanden sind unter anderem:

- Graph Core V3;
- freie Serienauswahl und geführte Ansichten;
- benutzerdefinierte Zeiträume;
- Inspector;
- Command-Follow;
- Episodentrigger und Episodenvergleich;
- Side-by-Side/Overlay-Verträge;
- Coverage-/Evidence-Badges;
- Status-SOC-Tagesdaten aus Graph Core V3.

Controller-Readiness und Graph-Readiness sind getrennte Verträge. Ab V16.2.5 werden bestätigte Coverage-/Evidence-Gaps renderseitig als `null`-Breaks in numerische Haupt-, Command-Follow- und Vergleichsserien eingespeist; die realen Messpunkte bleiben unverändert, es entstehen keine synthetischen Messwerte. Normale Sampling-Jittertoleranz bleibt über den bestehenden Evidence-Vertrag erhalten.

## 9. UI-Grundarchitektur

Status, Graph und Settings verwenden eine gemeinsame globale Navigation. Standard/Experte ist der normative Superset-Vertrag: Expertenmodus ergänzt Details; Standardinformationen und kritische Warnungen verschwinden nicht.

**V16.2.4-Implementierungsstand:** `UI_MODE=standard|expert` ist in Registry/Config vorhanden. Die Primärspeicherkarte rendert im Expertenmodus einen sichtbaren kompakten Superset-Slice `Strategie & Diagnose` mit Harmonisierung, Harvest/Strategie, diagnostischem usable SOC und Quellenstatus; die Standardkarte bleibt schlank. Das ist ausdrücklich **keine** vollständige Implementierung des kartenübergreifenden Statusseiten-Expertenmodus; der Completion-Scope bleibt unter `ZEC-BL-UI-STATUS-EXPERT-001` offen.

Die Settings-Domain ist fachlich kategorisiert, registry-getrieben und verwendet Preview/Commit statt Direktpersistenz. Administrative Aktionen wie Dienstneustart und Last-Good-Pointer-Reparatur sind von normalen Settingsänderungen getrennt.

V16.2.5 führt die bereits im Readiness-Pfad vorhandene Single-Owner-Evidenz (`instance_owner_active`, PID, Build-ID, Since, Lock-Pfad) zusätzlich konsistent über den allgemeinen `ControllerState.snapshot()` in `/status-view-data`; der eigentliche Instance-Lock- und Single-Owner-Vertrag bleibt unverändert.

Herstellerneutrale Primärspeicher-Funktionen werden in UI und Hilfe als „Primärspeicher“ bezeichnet; bestehende technische Legacy-Keys mit `SMA` bleiben aus Kompatibilitätsgründen erhalten. Für neue Installationen ist `SECOND_BATTERY_DISPLAY_NAME` leer. Die Namensauflösung bleibt: expliziter Nutzerwert vor Template-Default vor neutralem Fallback „Primärspeicher“. Der SMA-Entladefloor ist keine editierbare Einstellung und besitzt keinen Override-/On-Off-Schalter.

Seit V16.2.1 verwenden Zendure- und Primärspeicherkarte in der Standardansicht denselben Speicherstatusvertrag: SOC, prominent signierte Istleistung, Zustand, relevante Lade-/Entladegrenze, `Noch ladbar`/`Noch entladbar` als SOC-Prozentpunkte und – bei belastbarer Kapazität – zusätzlich kWh sowie einen richtungsabhängigen Leistungsbalken. Laden füllt grün links→rechts, Entladen orange rechts→links. Fehlende Kapazitäts-/Maximalleistungsdaten blenden ausschließlich die abhängige Zusatzanzeige aus. Reale/source-seitige Kapazitätsdaten haben Vorrang vor manuellen Fallbackwerten. V16.2.5 ordnet die Restenergie der rechten Detailspalte zu, vergrößert die Lesbarkeit der Leistungsdarstellung und entfernt starre Kartenhöhen, die Inhalt/Footer/Warnungen überlagern konnten. Aktive Command-/Limiter-Warnungen bleiben kompakt sichtbar und besitzen aufklappbaren Langtext. Die mobile Settings-Oberfläche wird zugleich auf viewportbreiten Inhalt ohne abgeschnittene horizontale Überläufe gehärtet.

## 10. Deploymentarchitektur ab V16

Kanonische Werkzeuge:

- `tools/install_zendure_controller.sh`;
- `tools/uninstall_zendure_controller.sh`;
- `tools/update_zendure_controller.sh` nur als Kompatibilitätswrapper.

Gemeinsame Zustände:

- `SUPPORTED_UPDATE`;
- `CLEAN_FRESH_INSTALL`;
- `AMBIGUOUS_OR_PARTIAL_INSTALL` – fail closed.

Installer/Uninstaller besitzen mutationsfreie Preflights. Clean Fresh Install startet ohne erfundene Produktivkonfiguration in `FIRST_INSTALL_SETUP`; Regelung bleibt gesperrt, bis ein gültiger erster Settings-Commit erfolgt ist.

Seit V16.2.2 gilt zusätzlich ein gemeinsamer fail-closed Release-/Manifest-Hygienevertrag: volatile Cache-/Bytecode-Artefakte und Runtime-Datenbanken sind im Release-Tree bzw. aktuellen Source-Manifest unzulässig. Paket-Preflight und Zielprüfung verwenden denselben Manifestverifier; die reale `rsync`-Semantik für Update und Fresh Install wird gegen diesen Vertrag regressionsgetestet. Installerfehler werden trotz `set -E` nur im Haupt-Shellprozess einmalig mit Supportcapture/Rollback finalisiert. Diese Härtung ändert keine Regler-, Command-, Safety- oder Recoverysemantik.

Seit V16.2.3 gilt zusätzlich ein kanonischer maschinenlesbarer Build-Evidence-Vertrag `ZEC_BUILD_EVIDENCE_V1`. `tools/deployment_contract.py verify-build-evidence` ist die gemeinsame Verifier-Autorität für Releaseversion, Label, Build-ID, PASS-Status, Testdateianzahl, vollständige Regression und den identischen `ResourceWarning=error`-Lauf. Human-readable QA-Dateien sind keine Parser-API. Der echte Installer-Preflight muss denselben Verifier auf dem finalen Fresh Extract aufrufen.

Ab V16.2.4 wird der maschinenlesbare Installationsreport atomar und timestamped persistent unter `/home/pi/Downloads` geschrieben; `/tmp` bleibt Kompatibilitätskopie. Das Feldabnahmetool bevorzugt ohne expliziten Pfad die persistente releasespezifische Evidenz und prüft beim Update weiterhin die reale Rollback-Datei gegen Pfad, Größe und SHA256. Die V16.2.4-Feldabnahme prüft zusätzlich die reale `/settings/model`-Surface statt nur statische Guidance-Texte.

Der reale Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Gesamtpfad ist automatisiert abgedeckt, aber noch nicht vollständig auf echter Hardware produktiv abgenommen. V16.2.4 wurde real erfolgreich von V16.2.3 installiert; der automatische Feldlauf bestand 27/27 Checks mit `FULL_READY`. V16.2.4 ist damit die aktuelle real bestätigte Runtimebasis. V16.2.5 besitzt TECHNICAL BUILD PASS und ändert keine Deploymentsemantik; für die reale Freigabe ist weiterhin ein Update V16.2.4 → V16.2.5 mit UI-/Diagnosefeldabnahme erforderlich. Siehe `05` und `07`.
