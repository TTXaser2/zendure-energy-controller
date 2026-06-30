# Zendure Energy Controller V12.11.0-RC5

Lokaler MQTT-basierter Controller für Zendure SolarFlow 2400 AC+ mit Weboberfläche, Regelalgorithmus, ZEC-MEASUREMENT-V4-Messdaten-Logging, Cross-Charge-Schutz, lokaler Zendure-API als Telemetrie-Fallback, optionaler Analyse-Weboberfläche und systemd-Betrieb.

Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

Lizenziert unter AGPL-3.0-or-later. Siehe `LICENSE`, `NOTICE` und `DISCLAIMER.md`.

## Wichtige Änderungen in V12.11.0-RC5

V12.11.0-RC5 ist ein Hotfix-/Diagnoserelease nach dem RC4-Livetest. RC5 stellt das im Setup mit EVCC stabile RC3-kompatible SMA-Socketverhalten als Default wieder her (`SMA_ENERGY_METER_SOCKET_MODE=rc3_compatible`) und ergänzt Diagnosefelder für Socket-Modus, Reuse-Optionen, Bind-Adresse, Paketlücken und Paket-/Minutenrate.

Neu sind außerdem `SMA_ENERGY_METER_LOG_DIAGNOSTICS`, `SMA_ENERGY_METER_LOG_INTERVAL_SECONDS` und `SMA_ENERGY_METER_PACKET_GAP_WARN_SECONDS`. Bei aktivem Datei-Logging schreibt ZEC kompakte `[SMA_DIAG]`-Zeilen ins Runtime-Log. Das Diagnosepaket nimmt zusätzlich einen Status-Snapshot, eine SMA-Diagnosezusammenfassung und gefilterte SMA-Runtime-Ereignisse auf.

Bei `GRID_METER_SOURCE=sma_energy_meter_udp` ist der SMA-Listener automatisch aktiv. Der bisherige Passivschalter ist nur noch als zusätzliche passive SMA-Beobachtung relevant, wenn weiterhin die Shelly-kompatible HTTP-Quelle als Regelquelle genutzt wird.

## Wichtige Änderungen in V12.11.0-RC4

V12.11.0-RC4 ist eine Integrations- und Diagnose-Nacharbeit zu RC3. Der Live-Regelalgorithmus, Nachtmodus, Cross-Charge, Restüberschuss-Ernte, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

- SMA-Direktlistener koexistenzfreundlicher: `SO_REUSEPORT` wird nicht mehr standardmäßig gesetzt.
- Die Netzleistungsquelle wird auf Statusseite, State und V4-Measurement dynamisch angezeigt/geschrieben. Bei `GRID_METER_SOURCE=sma_energy_meter_udp` steht nicht mehr fälschlich `Shelly/UniMeter` bzw. `UNIMETER`, sondern SMA.
- Shelly-Kompatibilität bleibt erhalten: `GRID_METER_SOURCE=shelly_http` heißt nun neutral Shelly-kompatible HTTP-Quelle und kann echte Shelly Pro 3EM oder kompatible HTTP-Endpunkte nutzen.
- Die lokale Zendure-API-Telemetrie ist in Defaults/Beispielkonfiguration deaktiviert und erhält Fehler-Backoff, damit Timeouts nicht zu aggressiven Wiederholungsabfragen führen.
- UniMeter ist nicht mehr als bevorzugter UI-Begriff formuliert. Im getesteten Setup kann UniMeter deaktiviert bleiben, wenn ZEC direkt SMA liest und keine andere Komponente die Shelly-Emulation benötigt.

## Wichtige Änderungen in V12.11.0-RC3

V12.11.0-RC3 ergänzt auf Basis von RC2 die notwendige Absicherung der direkten SMA-Home-Manager-/SMA-Energy-Meter-Quelle für die Netzleistungsdaten. Die Shelly-kompatible HTTP-Quelle bleibt als alternative Regelquelle erhalten. Die neue SMA-Direktquelle kann zunächst passiv parallel beobachtet werden, um Zuverlässigkeit, Paketalter, Vorzeichen und Abweichungen zum bisherigen Shelly-kompatiblen HTTP-Pfad zu prüfen. Optional kann `GRID_METER_SOURCE=sma_energy_meter_udp` als experimentelle direkte Regelquelle gewählt werden; bei mehreren SMA Energy Metern wird die produktive Nutzung ohne Seriennummernfilter blockiert. Empfohlen ist zuerst ein Parallelvergleich über mehrere Stunden oder Tage.

Weitere RC3-Nacharbeit:

- Interface-Namen wie `eth0` werden für den Multicast-Join zu ihrer IPv4-Adresse aufgelöst.
- Empfangene SMA-Geräte werden mit Seriennummer/SUSy-ID in der Statuskarte angezeigt.
- Filter auf `SMA_ENERGY_METER_SERIAL` und optional `SMA_ENERGY_METER_SUSY_ID` schützen Anlagen mit mehreren Energy Metern.
- Produktive SMA-Direktregelung ohne Seriennummernfilter wird per Validator blockiert.

Weitere UI-Nacharbeit: Die Statuskarte „Konfigurationsstatus“ wurde ans Ende der Statusübersicht verschoben, damit Warnungen sichtbar bleiben, aber die primären Betriebswerte nicht verdrängen.

Neue relevante Settings:

```text
GRID_METER_SOURCE = shelly_http | sma_energy_meter_udp
SMA_ENERGY_METER_PASSIVE_ENABLED = true/false
SMA_ENERGY_METER_GROUP = 239.12.255.254
SMA_ENERGY_METER_PORT = 9522
SMA_ENERGY_METER_INTERFACE = optional, z. B. eth0 oder lokale IPv4
SMA_ENERGY_METER_SUSY_ID = optional, z. B. 372
SMA_ENERGY_METER_SERIAL = optional/empfohlen, z. B. 3011954105
SMA_ENERGY_METER_STALE_TIMEOUT_SECONDS = 15
```

## Wichtige Änderungen in V12.11.0-RC1

V12.11.0-RC1 ist ein Analyse-/Diagnose-/UI-/Validierungsrelease auf Basis von V12.10.0-RC10. Die Live-Regelstrategie bleibt unverändert: keine Änderung an AUTO, Restüberschuss-Ernte Entry/Stay/Exit, Cross-Charge, Nachtmodus oder MQTT-Kommandostruktur.

- Semantischer Settings-Validator erweitert: ERROR/WARNING/INFO unterscheiden blockierende Fehler, bewusst prüfbare Warnungen und reine Hinweise.
- Settings-Validierung trennt handlungsorientiert zwischen in Settings korrigierbaren Problemen und temporären Datenquellenproblemen, z. B. nicht aktuellen Zendure-MQTT-SOC-Werten.
- Statusseite zeigt einen kompakten Konfigurationsstatus und zusätzliche Local-API-Timing-Informationen.
- Analyse-/Replay-Seite wertet die Restüberschuss-Ernte automatisch aus: Harvest-Dauer, Zendure-/SMA-Ladung, Netzimport/-export, Segmente und direkte `REST_SURPLUS_HARVEST`-Phasen.
- Gegenfaktische Harvest-Schätzung ergänzt: geschätzter vermiedener Sofort-Export mit klar ausgewiesener Annahme, dass der Primärspeicher ohne Harvest zusätzlichen Überschuss bis zur Maximalleistung aufgenommen hätte.
- Harvest-Nutzen wird für Sommer-/Vollspeicher-Fälle verständlicher eingeordnet: vorgezogene Speicherung vs. wahrscheinlich dauerhaft zusätzliche Speicherung.
- Cross-Charge-/Harvest-Transition-Auswertung ergänzt: kurze Gegenflussphasen während Harvest werden mit Dauer, Energie und Maximalleistung bewertet.
- Local-API-Timing-Auswertung in der Analyse zeigt Zyklen >1s/>2s/>5s, Local-API-p95/max und häufigste langsamste Teilphasen.
- Settings-Seite strukturell bereinigt: Bereichs-Erläuterungsboxen, klarere Abstände vor Unterabschnitten, sinnvolle Einführung des Bereichs „Zweitbatterie“, Nachtmodus-Master-Schalter zuerst.
- Legacy-Parameter `SMA_DISCHARGE_BLOCK_W` / „Entlade-Blockgrenze (Legacy)“ wird nicht mehr in der normalen Settings-UI angezeigt; Migration/Kompatibilität bleiben erhalten.
- Keine Änderung an Harvest-Schwellen, Cross-Charge-Regelwirkung, MQTT-Topics oder Local-API-Architektur.





## Wichtige Änderungen in V12.10.0-RC10

V12.10.0-RC10 ist ein kleiner Nacharbeits-RC zu RC9. Die Harvest-Regelstrategie bleibt unverändert; verbessert werden Kontrast der Settings-Seite, Statusanzeige der Restüberschuss-Ernte in der SMA-/Zweitbatterie-Box, der Hinweistext der Nachtmodus-Prognose und die Config-Snapshot-Reproduzierbarkeit für Harvest-Settings.

V12.10.0-RC9 hat als einzige echte Regeländerung die Restüberschuss-Ernte bei Primärspeicher-Ladelimit eingeführt. V12.10.0-RC10 ändert diese Regelstrategie nicht, sondern verbessert Transparenz und Diagnose: Settings-Kontrast, Statusanzeige der Restüberschuss-Ernte, Nachtmodus-Prognosehinweise und Config-Snapshot-Reproduzierbarkeit.

- Neuer Settings-Hauptbereich „Zweitbatterie“ mit Unterabschnitten „Zweitbatterie-Messwerte“, „Cross-Charge-Schutz“ und „Restüberschuss-Ernte“.
- Restüberschuss-Ernte mit bewusst strengem Entry: Start erst nach stabiler Bestätigung, nicht nach einem einzelnen kurzen PV-/Last-Ausreißer.
- Während aktiver Ernte bleibt Zendure bewusst träger: Step-/Smoothing-Limits gelten weiter, damit der SMA/Primärspeicher der schnelle Regler bleibt.
- Der Modus bleibt großzügig aktiv, solange er dem System nicht schadet; bei Netzbezug, SMA-Entladung, stale Daten, SOC-Limit oder Safe-State wird reduziert bzw. beendet.
- V4-Measurement wurde um Harvest-Diagnosefelder erweitert, damit Entry, aktive Phase, Exit, Schwellen und Wirkung später sauber analysiert werden können.
- `target_final_reason` kennt nun `REST_SURPLUS_HARVEST`.
- Settings-Validierung prüft die wichtigsten Harvest-Querabhängigkeiten, z. B. fehlende maximale Primärspeicher-Ladeleistung, deaktivierten Cross-Charge-Schutz und ungünstige Schwellenkombinationen.
- Die Statusseite zeigt in der Nachtmodus-Box eine Prognose für das voraussichtliche Nachtmodus-Ende inklusive prognostiziertem SOC, sofern Kapazität, SOC und Entladeleistung bekannt sind.
- `/status` liefert die Controller-Version wieder explizit; Config-Snapshots werden bei Versionswechsel nicht mehr irreführend mit alter Version weitergeführt.
- Analyse-Preflight bei sehr kleinen Dateien wurde entschärft und Browser-Confirm-Popups wurden durch eine eingebettete Bestätigung im ZEC-Stil ersetzt.
- Timing-Detaildiagnose schreibt bei längeren Zyklen zusätzliche Phaseninformationen ins Runtime-Log.
- Keine Änderung an Harvest-Entry-/Stay-/Exit-Schwellen, MQTT-Topic-/Kommandostruktur, Nachtentladungsstrategie oder Local-API-Architektur.

## Wichtige Änderungen in V12.10.0-RC6

V12.10.0-RC6 ergänzt den symmetrischen Cross-Charge-Schutz in AUTO/HOLD: gegenläufige Flüsse zwischen Zusatzbatterie/SMA und Zendure werden in beiden Richtungen erkannt und proportional reduziert oder neutralisiert. Zusätzlich enthält RC6 Nacharbeiten an V4-Manifest/Mapping, Analyse-Service-Dateipfaden und Cross-Charge-Auswertung. NIGHT_DISCHARGE, feste manuelle Modi, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

- V4-Rotation ist manifestgeführt: Jede physische V4-CSV-Datei bekommt einen eigenen Manifest-Eintrag. Es werden keine versteckten `_1`/`_2`-Rotationsdateien ohne Manifest-Eintrag mehr erzeugt.
- Analyse-Service und `tools/replay_csv.py` bleiben V3/V4-strikt und können neue V4-Rotationsdateien vertraglich sauber auswerten.
- `tools/create_zec_analysis_package.sh` wird mitgeliefert: Default-Output `/home/pi/Downloads`, automatische Measurement-Pfad-Erkennung, alle V4-Dateien standardmäßig, Cleanup temporärer Arbeitsverzeichnisse nach ZIP-Erstellung, keine doppelte Runtime-Log-Kopie.
- Statusseite: Die Timing-Hauptkennzahl heißt `Aktive Zykluszeit` und nutzt dieselbe Timing-Struktur wie die Detailwerte. Technische Timing-Feldnamen werden nicht mehr direkt angezeigt.
- V4-Mapping: `control_effective_export_w` nutzt zusätzliche Fallbacks aus der Szenario-Rekonstruktion.
- Nachtmodus-Exit-Fix: Beim Verlassen der festen Nachtentladung wird ein alter Entlade-Sollwert einmalig auf 0 W neutralisiert, damit HOLD/Deadband ihn nicht weiterführen können. Diese Neutralisierung darf `MIN_COMMAND_CHANGE_W` übersteuern.
- Symmetrischer Cross-Charge-Schutz und Restüberschuss-Ernte bleiben für den nächsten Reglerlogik-RC geplant.
- Vollständiger Testlauf: 157 Tests OK.

## Wichtige Änderungen in V12.10.0-RC3

V12.10.0-RC3 stabilisiert das aktive V4-Logging. Die AUTO-Regelstrategie, der Nachtmodus, Cross-Charge-Logik, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert.

- V4-Logging über `MEASUREMENT_SCHEMA_VERSION=4`.
- Session-spezifische V4-CSV-Dateien verhindern, dass RC-/Service-Start-Segmente in derselben physischen Datei vermischt werden.
- V4 Standard-Header mit 116 Feldern und optionales Extended-Profil mit drei JSON-Spalten: Packtemperaturen, Headunit-Temperaturen, Zendure-MQTT-Gruppenstatus.
- Begleitdateien: `zec_measurement_manifest.json`, `zec_config_snapshots.json`, `zec_runtime_events.jsonl`.
- Manifest-Updates sind gepuffert/debounced; `MEASUREMENT_LOG_MODE=off` ist ein harter Logging-Bypass.
- Snapshot-Backfill ergänzt `CROSS_CHARGE_SIGNIFICANT_W` aus Legacy `SMA_DISCHARGE_BLOCK_W`.
- V4-Fail-Closed-Grundlogik: Wenn Manifest oder Config-Snapshot nicht geschrieben werden kann, pausiert nur das Measurement-Logging; die Regelung und MQTT-Kommandos laufen weiter.

## Wichtige Änderungen in V12.9.4

V12.9.4 ist ein kleiner Stabilitäts- und Diagnose-Feinschliff auf Basis von V12.9.3. Die AUTO-Regelstrategie, der Nachtmodus, die MQTT-Subscriptions, die MQTT-Kommandostruktur und das `ZEC-MEASUREMENT-V3`-CSV-Grundschema bleiben unverändert. Schwerpunkt ist die saubere Trennung von zyklischen Messdaten und Betriebsdiagnose beim Messdaten-Speicherziel.

- Keine neuen USB-/Fallback-Detailspalten im Measurement-CSV: V3-Daten bleiben während der laufenden Datensammlung konsistent.
- Messdaten-Statusbox auf der Statusseite kompakter und operativer: Modus, aktives Ziel, Pfad, Status, Fallback-Zähler, letzter Fallback-Zeitpunkt/-Grund, freier Speicher und Aufbewahrung.
- Die prominente Schema-Zeile wurde aus der Messdaten-Statusbox entfernt; das Schema bleibt unverändert `ZEC-MEASUREMENT-V3`.
- USB-/SD-Fallback-Diagnose wird als Betriebsdiagnose behandelt: konkrete Primary-Pfad-/Mount-/Schreibbarkeits-/Freispeicher-/Exception-Details werden bei Fallback-Ereignissen ins Runtime-Log geschrieben, sofern Datei-Logging aktiviert ist.
- Fallback-Ereignisse werden gezählt; ein dauerhaft aktiver Fallback erhöht den Zähler nicht pro Messzyklus, sondern nur beim neuen Ereignis bzw. bei geändertem Fehlerbild.
- Der umgebungsabhängige USB-Fallback-Test wurde isoliert; reale Mountpoints auf dem Raspberry Pi verfälschen diesen Test nicht mehr.
- Standard-Dateiname des Runtime-Logs für neue Konfigurationen ist konsistent `zendure_runtime.log`.
- Keine Änderung an Temperatur-Logging, Schema-Kürzung, Simulator, Analyse-Architektur oder finaler Excel-Lernsimulation.

## Wichtige Änderungen in V12.9.3

V12.9.3 ist ein Stabilitäts- und Analyse-Nacharbeitsrelease auf Basis von V12.9.0. Die AUTO-Regelstrategie, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben unverändert. Schwerpunkt sind Zendure-MQTT-Live-Diagnose nach Neustarts, ein robusterer Analyse-/Replay-Schutz und verständlichere Analyse-Diagramme.

- Zendure-MQTT Live-/Retained-/Partial-Stale-Erkennung ergänzt: Nach Raspberry-/Mosquitto-Neustart wird sichtbar, ob Zendure wirklich wieder frische nicht-retained Live-Werte liefert oder nur retained/alte/unvollständige Werte vorliegen.
- Statusseite zeigt den Zendure-MQTT-Live-Status kompakt mit Handlungshinweis. Warnungen verschwinden automatisch, sobald kritische Zendure-Gruppen wieder frisch und live sind.
- Analyse/Replay akzeptiert generisch nur gültige `ZEC-MEASUREMENT-V3`-Dateien; alles andere wird fail-closed abgelehnt.
- Analyse läuft nun in einem isolierten Worker-Prozess mit Timeout und Speicherlimit. Der Replay-Webdienst bleibt kontrollierend erreichbar und kann den Worker abbrechen, damit der Live-Controller geschützt bleibt.
- Pi-Safe-Grenzen wurden konservativer gesetzt; unsichere oder zu große Analysen werden nicht mehr grün bewertet.
- Analyse-Diagramme semantisch korrigiert: Prozentbalken werden bei Prozentwerten strikt 0–100 skaliert, Restkategorien werden sichtbar, Deadband-/Abweichungsursachen-Diagramme sind verständlicher.
- Betriebszustandsmatrix benennt Netzenergie eindeutig als `Netzbezug kWh` und `Einspeisung kWh` mit Info-Texten.
- Settings-Seite: Erklärungsbox für Messdaten-Modi und Aufbewahrung steht nun oberhalb der Messdaten-Eingabefelder.
- Update-Script bereinigt obsolete Tests im Zielverzeichnis, startet zuvor aktive Dienste nach erfolgreichem Update wieder und versucht bei Updatefehlern zuvor laufende Dienste wiederherzustellen.
- Kein V2-spezifisches Log-Cleanup mehr: V12.9.3 behandelt alte/ungültige Messdaten generisch als nicht-V3.
- Der Logger prüft eine vorhandene aktive Messdatei nur beim Öffnen/Initialisieren auf gültigen V3-Header. Bei ungültigem Header wird Logging pausiert und auf der Statusseite gewarnt; es wird nichts gelöscht und die Regelung läuft weiter.


## Wichtige Änderungen in V12.9.0

V12.9.0 ist ein bewusstes Breaking-Change-Grundlagenrelease für `ZEC-MEASUREMENT-V3`. Die AUTO-Regelstrategie, MQTT-Subscriptions und MQTT-Kommandostruktur bleiben fachlich unverändert; geändert wurde der Messdaten-/Logging-/Analysevertrag.

- Neues Messdaten-Schema `ZEC-MEASUREMENT-V3` mit Semikolon-Trennzeichen, Dezimalpunkt und einer Zeile pro Controller-Zyklus.
- Klare Trennung von Rohmesswerten, normalisierten Regler-Eingängen, Szenario-Basis ohne Zendure-Wirkung, Reglerentscheidung, Sollwert-Kaskade, tatsächlich gesendetem MQTT-Kommando, Istwirkung sowie Freshness-/Validity-Diagnose.
- Messdaten-Logging ist betriebslogisch über drei Modi steuerbar: `off`, `standard`, `extended`.
- `standard` enthält vollständige Reglerdiagnose inklusive `scenario_grid_without_zendure_w` und aggregierter Zendure-MQTT Live-/Retained-/Partial-Stale-Diagnose.
- `extended` ergänzt Detail-JSONs für Topic-/Pack-/Unit-/Limiter-/Freshness-Tiefenanalyse und spätere Simulator-/What-if-Arbeiten.
- Logging bleibt optional und nachgelagert: Schreibfehler, zu wenig freier Speicher oder deaktiviertes Logging dürfen die Regelung nicht blockieren.
- Settings-/Statusseite zeigen Schema, Modus, Logging-Status, freien Speicher und eine grobe geschätzte Aufbewahrungsdauer.
- Alte `CSV_LOG_*`-Config-Keys werden beim Laden/Update einmalig auf `MEASUREMENT_LOG_*` übersetzt.
- Analyse/Replay akzeptiert nur noch `ZEC-MEASUREMENT-V3`; ältere V2-Dateien werden bewusst nicht migriert oder analysiert.
- Finale Excel-Lernsimulation bleibt unverändert unter `tools/` enthalten.

## Wichtige Änderungen in V12.8.21

V12.8.21 war ein kleiner UI-/Dokumentations-Nacharbeitsrelease auf Basis von V12.8.20. Die AUTO-Regelstrategie, Statusseite, MQTT-Subscriptions, MQTT-Kommandostruktur, CSV-Schema und das Datenmodell blieben unverändert.

- UI-Hilfe-/Info-Texte auf der Analyse-Webseite wurden von historischen Versionsformulierungen bereinigt. Die Texte beschreiben direkt den aktuellen Funktionszustand.
- Der Hilfetext zu `NIGHT_DISCHARGE` beschreibt die Reserve-SOC-Semantik ohne Versionshistorie.
- High-SOC-Hinweise in der Analyse beschreiben die Einordnung als leichte Zusatzdiagnose ohne Versionsverweis.
- Neuer Test stellt sicher, dass Analyse-Hilfetexte keine historischen Formulierungen wie `Seit V...` oder `Ab V...` enthalten.
- Keine Änderung am Diagramm-Balkenlayout gegenüber V12.8.20.

## Wichtige Änderungen in V12.8.20

V12.8.20 ist ein gezieltes Analyse-/Diagramm-UI-Nacharbeitsrelease auf Basis von V12.8.19. Die AUTO-Regelstrategie, MQTT-Subscriptions, MQTT-Kommandostruktur und das CSV-Schema bleiben unverändert.

- Analyse-Webseite / Diagramme:
  - Balkenlayout nach dem abgestimmten Mockup-Prinzip umgebaut: Begriff und Balken stehen in der Hauptzeile, die Wert-/Prozentzeile steht darunter.
  - Lange Werttexte drücken die Balken nicht mehr seitlich zusammen; die Balkenbreite wird visuell unabhängig vom Textbereich dargestellt.
  - Mobile Darstellung robuster: Labels können umbrechen, Balken behalten eine definierte Breite, Werttexte stehen unterhalb.
- Info-Texte:
  - Fehlender Info-Text für `HOLD` ergänzt.
  - Die im Controller/Replay bekannten Betriebszustände und MQTT-Wirkungskategorien sind explizit mit Hilfetexten abgedeckt.
  - Neue Tests prüfen, dass bekannte Zustände nicht ohne Beschreibung in der Analyse auftauchen.
- Keine Änderung an Statusseite, Regelalgorithmus, Datenmodell oder CSV-Schema gegenüber V12.8.19.
- Finale Excel-Lernsimulation bleibt unverändert unter `tools/` enthalten.

## Wichtige Änderungen in V12.8.19

V12.8.19 ist ein bereinigtes UI-/Analyse-Nacharbeitsrelease auf Basis von V12.8.17. Die problematische V12.8.18-Nacharbeit wurde nicht als fachliche Basis weitergeführt; die betroffenen Punkte wurden neu und gezielter umgesetzt. Die AUTO-Regelstrategie, MQTT-Subscriptions, MQTT-Kommandostruktur und das CSV-Schema bleiben unverändert.

- Statusseite / Netzleistung:
  - Der Hauptwert der Karte `Netzleistung` zeigt wieder den aktuellen Shelly-/UniMeter-Rohmesswert, sofern dieser frisch verfügbar ist.
  - Grid wird in festen Modi, festem Nachtmodus und STOP/HOLD best-effort für Anzeige/CSV aktualisiert, ohne diese Modi von Grid abhängig zu machen.
  - AUTO-spezifische Diagnosewerte wie der geglättete AUTO-Regelwert werden in nicht aktiven Modi nicht mehr als statische Wattwerte präsentiert, sondern als `n.a. / nicht aktiv` gekennzeichnet.
  - Wenn Grid wirklich nicht frisch ist, wird kein alter Zahlenwert als normaler Hauptstatuswert angezeigt.
- Statusseite / Nachtmodus:
  - Infotext an die V12.8.17-Semantik angepasst: `NIGHT_DISCHARGE_STOP_SOC_PERCENT` pausiert nur die feste Nacht-Basisentladung; AUTO bleibt für Lastspitzen bis zum globalen `MIN_SOC_PERCENT` aktiv.
- Analyse-Webseite:
  - Die Auswahl-/Risikobox berechnet bei Mehrdatei-Auswahl den Zeitraum als globales Minimum aller Startzeitpunkte bis globales Maximum aller Endzeitpunkte. Invertierte Vorschau-Zeiträume bei rotierenden CSVs werden dadurch verhindert.
  - Der Diagramm-Bereich enthält spezifischere Info-Texte für Betriebszustände und MQTT-Wirkungskategorien.
  - Die mobile Balkendarstellung wurde stabilisiert, damit Labels, Werte, Balken und Info-Links nicht überlappen.
  - MQTT-Wirkungsbalken werden jetzt strikt nach absoluter Anzahl innerhalb des Blocks skaliert; `0 Kommandos` erzeugt keinen gefüllten Wertbalken.
  - Die Datenqualitätswarnung wurde konkretisiert: betroffene Felder, Anzahl/Prozent, SAFE_STATE-Anteil und Einordnung werden besser sichtbar.
- Finale Excel-Lernsimulation bleibt unverändert unter `tools/` enthalten.

## Wichtige Änderungen in V12.8.16

V12.8.16 ist eine gezielte Nacharbeit zur Nachtmodus-Reserve-SOC-Logik aus V12.8.15. Die AUTO-Regelstrategie bleibt unverändert:

- `NIGHT_DISCHARGE_STOP_SOC_PERCENT` arbeitet nun als laufende Untergrenze ohne Latch und ohne Hysterese.
- Wenn `SOC <= NIGHT_DISCHARGE_STOP_SOC_PERCENT`, wird die Nachtentladung gestoppt.
- Wenn der SOC später im selben Nachtfenster wieder `> NIGHT_DISCHARGE_STOP_SOC_PERCENT` ist und Nachtfenster, SOC-Freshness und MQTT-Kommandopfad gültig sind, darf die Nachtentladung wieder laufen.
- Die in V12.8.15 eingeführte Nachtfenster-Latch-Logik wurde entfernt, damit der Reserve-SOC keine einmalige Sperre für das gesamte Nachtfenster mehr ist.
- Latch-Diagnosefelder wurden aus Status-/Graph-/CSV-Datensatz entfernt; der Stop-Grund `NIGHT_RESERVE_SOC` bleibt erhalten.
- Settings-UI mit `hh:mm`-Zeitfeldern und automatischer Normalisierung aus V12.8.15 bleibt erhalten.
- Zusätzliche Tests sichern Stop bei `SOC <= Reserve-SOC`, Wiederanlauf bei `SOC > Reserve-SOC` im selben Nachtfenster, Stop-Grund-Reset und entfernte Latch-Felder ab.
- Keine Änderung an MQTT-Subscriptions, MQTT-Kommandostruktur oder AUTO-Regelstrategie.

## Wichtige Änderungen in V12.8.15

V12.8.15 erweitert den Nachtmodus und verbessert die Settings-Bedienung für Nachtzeiten. Die AUTO-Regelstrategie bleibt unverändert:

- Neuer optionaler Nachtmodus Reserve-/Stop-SOC `NIGHT_DISCHARGE_STOP_SOC_PERCENT`. Leer/`null` bedeutet: bisheriges Verhalten bleibt aktiv.
- Die Nachtentladung stoppt, sobald der globale `MIN_SOC_PERCENT`, der optionale Nachtmodus Reserve-SOC oder die konfigurierte Endzeit erreicht wird.
- Wenn der Nachtmodus Reserve-SOC erreicht wurde, bleibt die Nachtentladung per Latch für dieses Nachtfenster gestoppt. Dadurch startet sie nicht wegen kleiner SOC-Schwankungen erneut. Der Latch wird zurückgesetzt, sobald das Nachtfenster verlassen wurde.
- Status-/CSV-/Graph-Diagnosefelder für Nachtmodus Reserve-SOC, Latch und Stop-Grund ergänzt.
- Settings-Webseite zeigt Start- und Endzeit des Nachtmodus als zwei Felder im Format `hh:mm` statt vier getrennten Stunde-/Minute-Feldern. Intern bleiben die bisherigen Config-Felder erhalten.
- Uhrzeiteingaben wie `5:30` oder `23:0` werden beim Verlassen des Eingabefelds sichtbar zu `05:30` bzw. `23:00` normalisiert; ungültige Werte wie `24:00`, `12:75` oder `abc` werden abgelehnt.
- Validierung: `NIGHT_DISCHARGE_STOP_SOC_PERCENT` muss, wenn gesetzt, mindestens dem globalen Mindest-SOC entsprechen.
- Zusätzliche Tests für Nachtmodus-Reserve-SOC, Latch-Verhalten, Latch-Reset, Settings-Zeitfelder, Validierung und CSV-Felder.
- Keine Änderung an MQTT-Subscriptions oder MQTT-Kommandostruktur außerhalb der bestehenden Nachtmodus-Stop-/Hold-Logik.

## Wichtige Änderungen in V12.8.14

V12.8.14 ist ein minimaler Hotfix für die MQTT-Topic-Diagnoseseite und die Installations-/Testrobustheit. Die eigentliche Regelstrategie bleibt unverändert.

- Die MQTT-Diagnoseseite aktualisiert die sichtbare Tabelle nun automatisch per leichtem Polling, ohne die komplette Seite neu zu laden. Nach `Diagnosetabelle leeren` erscheinen neue MQTT-Werte dadurch ohne manuellen Browser-Refresh.
- Ein zusätzlicher Button `Aktualisieren` lädt die Diagnosezeilen bei Bedarf manuell nach.
- Neuer JSON-Endpunkt `/mqtt-diagnostics/data` liefert nur die aktuellen Diagnosezeilen und Metadaten für die Tabellenaktualisierung.
- Die V12.8.13-Routentests wurden so umgebaut, dass sie auf dem Raspberry Pi keine zusätzliche Test-only-Abhängigkeit `httpx` mehr benötigen.
- Zusätzliche Tests sichern Diagnose-Polling, Datenendpunkt, Headless-Verhalten und neue Werte nach Clear ab.
- Keine Änderung am Live-Regelalgorithmus.
- Finale Excel-Lernsimulation bleibt unverändert unter `tools/` enthalten.

## Wichtige Änderungen in V12.8.13

V12.8.13 ist ein minimaler Hotfix für die MQTT-Topic-Diagnoseseite aus V12.8.12. Die eigentliche Regelstrategie bleibt unverändert.

- Aufruf von `/mqtt-diagnostics` liefert wieder die Diagnose-Webseite statt `Internal Server Error`.
- Ursache war ein falscher Aufruf von `html_or_headless()` mit bereits erzeugtem HTML-String statt Page-Builder-Funktion.
- Der Button `Diagnosetabelle leeren` aus V12.8.12 bleibt erhalten.
- Zusätzliche echte FastAPI-Routentests sichern `GET /mqtt-diagnostics`, `POST /mqtt-diagnostics/clear` und Headless-Verhalten ab.
- Keine Änderung am Live-Regelalgorithmus.
- Finale Excel-Lernsimulation bleibt unverändert unter `tools/` enthalten.

## Wichtige Änderungen in V12.8.12

V12.8.12 ist ein begrenzter Diagnose-/Settings-UI-Hotfix und eine Nachhärtung von V12.8.11. Die eigentliche Regelstrategie bleibt unverändert.

- MQTT-Topic-Diagnoseseite hat nun einen Button `Diagnosetabelle leeren`. Der serverseitige Diagnosepuffer wird geleert; die Diagnose läuft weiter und neue MQTT-Werte erscheinen danach wieder in der Tabelle.
- Nach `Dienst jetzt neu starten` leitet die Settings-Webseite nun auf die Hauptseite `/` des konfigurierten Web-Ports weiter statt auf `/status`.
- Restart-Seite spricht nun von Hauptseite statt Statusseite und nutzt den absoluten Ziel-URL mit dem konfigurierten `WEB_PORT`.
- Zusätzliche Tests sichern den Diagnosepuffer-Clear, neue MQTT-Werte nach dem Leeren und den korrigierten Restart-Redirect ab.
- Keine Änderung am Live-Regelalgorithmus.
- Finale Excel-Lernsimulation bleibt unverändert unter `tools/` enthalten.

## Wichtige Änderungen in V12.8.11

V12.8.11 ist ein vorsichtiger Controller-Housekeeping-/Diagnose-Build mit Schwerpunkt Ablaufvertrag, Freshness-/Validitätsmodell und MQTT-Diagnosefilter. Der bestehende Regelalgorithmus bleibt fachlich erhalten; die Änderungen machen die Regelentscheidungen besser prüfbar und verhindern stale Diagnose-/CSV-Aussagen.

- Neuer schlanker Freshness-/Validitätsvertrag für externe Datenquellen: Grid/Shelly-UniMeter, Zendure-SOC, MQTT-Kommandopfad und Zweitbatterie/EVCC werden pro Zyklus mit `available`, `fresh`, `valid`, `used_for_control`, Alter und Grund bewertet.
- Zentrale `finish_cycle()`-/Housekeeping-Phase dokumentiert nun, welche Quellen ein Modus tatsächlich benötigt und welche davon fehlen oder stale sind. Nachtentladung bleibt dabei bewusst ohne Grid-Abhängigkeit.
- CSV-/Graph-Datensatz enthält zusätzliche Diagnosefelder für Datenqualität, genutzte Quellen und Missing-/Stale-Gründe.
- `effective_export_power_valid` wird in Modi ohne Grid-Regelpfad nicht mehr stale aus einem früheren AUTO-Zyklus weitergeführt.
- MQTT-Topic-Diagnosefilter korrigiert: Im Standardmodus `filtered` werden nur noch Nachrichten gespeichert/angezeigt, die wirklich zum konfigurierten MQTT-Filter passen.
- Neuer MQTT-Diagnose-Anzeigemodus `MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE`: `filtered` oder `all`. `all` zeigt bewusst alle empfangenen Controller-Topics für kurze Fehlersuche.
- MQTT-Wildcards `#` und `+` werden inklusive case-sensitiver Topic-Prüfung getestet; die Diagnose-Webseite weist auf Groß-/Kleinschreibung hin.
- Finale Excel-Lernsimulation `zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx` wird unverändert unter `tools/` mit ausgeliefert.
- Neue Tests sichern Mode-/Datenquellen-Vertrag, Freshness-Felder, CSV-Diagnosefelder und MQTT-Diagnosefilter ab.

## Wichtige Änderungen in V12.8.10

V12.8.10 ist ein kleiner Analyse-Webseiten-Hotfix ohne Änderung am Live-Regelalgorithmus:

- Info-Aufklapper im Diagramm-Bereich nutzen beim Öffnen die volle Breite des jeweiligen Diagramm-Elements. Dadurch bleiben Label, Balken und Werte stabil und die Erklärungstexte sind besser lesbar.
- Der Button `Analyse starten` wird sofort gesperrt, sobald sich die CSV-Auswahl ändert.
- Während die Auswahl-/Risikobox neu berechnet wird, zeigt der Button `Aktualisiere Dateiauswahl…`.
- Eine Analyse kann erst gestartet werden, wenn die Informationen zu den ausgewählten Dateien vollständig aktualisiert und gültig sind.
- Race-Condition-Schutz für schnelle Mehrfachänderungen der Dateiauswahl: veraltete Profilantworten werden ignoriert.

## Wichtige Änderungen in V12.8.9

V12.8.9 ist eine Analyse-Webseiten-Version mit Schwerpunkt Verständlichkeit, Bedienrückmeldung und Dark-Mode-Lesbarkeit:

- Extended-/Warn-Analysen geben wieder JSON-serialisierbare Auswahlprofile zurück; der Fehler `Object of type AnalysisLimits is not JSON serializable` ist behoben.
- Die Release-Hinweisbox wurde von der Analyse-Webseite entfernt; Release-Details stehen in README/Technical Notes.
- Auswahl-/Risikobox mit Überschrift und Erklärung ergänzt.
- Abbruch einer Analyse bestätigt nun klar, dass die Analyse abgebrochen wurde und eine neue Analyse gestartet werden kann.
- Kurzfazit-/Bewertungsboxen, Ampel-Badges und Statusbereiche wurden im Dark Mode kontrastreicher gestaltet.
- Ampelfarben sind systematischer: grün = ok, gelb/amber = prüfen, rot = kritisch, grau = nicht bewertbar.
- Info-Aufklapper sind layout-stabiler, damit Labels/Überschriften beim Öffnen nicht verrutschen.
- Diagrammblock semantisch überarbeitet: Abschnittserklärung, Info-Texte je Diagramm, Einheiten/Basiswerte direkt an den Balken, menschenlesbare Betriebszustandsdauer.
- Label `95%-Perzentil |Netz|` in der Soll-/Ist-Folge zu `95%-Perzentil Soll/Ist-Abweichung` korrigiert.
- Link `nach oben` führt wieder an den Seitenanfang.
- `zendure-replay.service`: `StartLimitIntervalSec`/`StartLimitBurst` stehen nun korrekt im `[Unit]`-Abschnitt; Kommentar zum optionalen Betrieb präzisiert.
- Keine Änderung am Live-Regelalgorithmus.

## Wichtige Änderungen in V12.8.8

V12.8.8 ist ein kleiner Hotfix für die Analyse-/Replay-Weboberfläche und korrigiert einen JavaScript-Syntaxfehler aus V12.8.7:

- Analyse-Button reagiert wieder zuverlässig.
- Status-/Fortschrittsanzeige und dynamische Auswahlprüfung initialisieren wieder korrekt.
- Dark-Mode-Kontrastkorrekturen aus V12.8.7 bleiben erhalten.

## Wichtige Änderungen in V12.8.7

V12.8.7 ist ein kleiner Hotfix für die Analyse-/Replay-Weboberfläche:

- Analyse-Startbutton wird robuster per JavaScript-Event angebunden.
- Status-/Fortschrittsbox ist im Dark Mode wieder gut lesbar.
- Fehler, Startstatus und Abschlussstatus werden deutlich sichtbar angezeigt.
- Änderung der CSV-Auswahl aktualisiert die Auswahl-/Risikobox dynamisch über `/selection-profile`.
- Der Startbutton wird abhängig von der gültigen Auswahl aktiviert bzw. deaktiviert.
- Keine Änderung am Live-Regelalgorithmus.

## Wichtige Änderungen in V12.8.6

V12.8.6 ist eine gezielte Hotfix-Version für Housekeeping und Ablaufkonsistenz im Live-Controller:

- Zweitbatterie-/SMA-Anzeigewerte werden nun auch in Nachtentladung, Stop/Hold und festen Modi aktualisiert.
- `update_sma_metrics()` wurde fachlich getrennt: Anzeige-/CSV-Ableitung läuft unabhängig von AUTO, Cross-Charge-Regelmetriken nur nach gültiger Grid-Messung im AUTO-Zweig.
- Zendure-Istleistung wird am Zyklusende erneut aus Rohsensoren und aktuellen Soll-Limits abgeleitet, damit Vorzeichen nach Moduswechseln nicht stale bleiben.
- Neue Freshness-/Validitätsfelder für Grid, Zweitbatterie und effective export helfen, Anzeige/CSV/Analyse sauberer zu interpretieren.
- Zweitbatterie-MQTT-Rohwerte werden unter `state.lock` aktualisiert.
- Zusätzliche Tests sichern frühe Return-Pfade und per-cycle Housekeeping ab.

## Wichtige Änderungen in V12.8.5

V12.8.5 ist eine Stabilitäts- und Bedienbarkeitsversion mit Schwerpunkt Analyse-/Replay-Sicherheit auf dem Raspberry Pi:

- Analyse-Weboberfläche startet Analysen nicht mehr automatisch beim Seitenaufruf. Eine Analyse beginnt erst nach explizitem Klick auf „Analyse starten“.
- Neue Pi-Safe-Analysegrenzen: standardmäßig 4 Dateien, 12 MiB Gesamtgröße und 40.000 Messpunkte.
- Erweiterter Analysemodus mit aktiver Warn-/Bestätigung: 5 Dateien, 18 MiB und 70.000 Messpunkte. Alles darüber wird lokal auf dem Raspberry Pi abgelehnt.
- Auswahlprüfung vor Analyse: Dateianzahl, Gesamtgröße, geschätzte Messpunkte, Zeitraum und Risiko-Klassifikation.
- Single-Flight-Lock: Reloads, Mehrfachklicks oder zweite Tabs starten keine parallelen Analysen.
- Analyse läuft in einem Hintergrundjob mit Status-/Phasenanzeige, deaktiviertem Startbutton und Abbrechen-Funktion.
- Analyse verwendet Snapshot-Kopien der CSV-Dateien statt direkt auf der aktiven Logdatei zu arbeiten.
- Report-Downloads (`report.txt`, `report.json`, `summary.csv`) verwenden das gecachte Analyseergebnis statt eine teure Neuanalyse zu starten.
- `zendure-replay.service` enthält Ressourcenschutz (`MemoryHigh`, `MemoryMax`, `CPUQuota`, niedrigere CPU-/I/O-Priorität), damit eine zu große Analyse nicht den gesamten Pi blockieren soll.
- Analyse-Dark-Mode nutzt `UI_DARK_MODE` aus `config.json`.
- Analyse-Kurzfazit wurde zu einem echten Gesamturteil mit Handlungsdruck erweitert; Blockeinleitungen und Info-Texte wurden ausgebaut.
- Vorzeicheninterpretation der Zendure-Istleistung bei Nachtentladung verbessert: positive interne Pack-&gt;Headunit-Leistung wird bei aktiver Entladeanforderung systemisch als Entladung dargestellt.
- Vorbereitung für `UI_MODE` (`standard`/`expert`) in der Config; vollständige Standard-/Expertenansicht bleibt als größerer UI-Block offen.

## Wichtige Änderungen in V12.8.4

V12.8.4 ist eine Bugfix-Version für die Ablaufreihenfolge des Live-Controllers:

- Nachtmodus ist nicht mehr von Shelly-/UniMeter-Netzleistungsdaten abhängig. Bei fehlender Netzmessung läuft die feste Nachtentladung weiter, sofern SOC und MQTT-Pfad gültig sind.
- Manuelle Betriebsarten `STOP_HOLD`, `FIXED_DISCHARGE` und `FIXED_CHARGE` werden vor der Shelly-/UniMeter-Abfrage behandelt und hängen dadurch nicht unnötig an der Netzleistungsmessung.
- Wenn ein Shelly-/UniMeter-Fehler im normalen Automatikbetrieb zum Safe-State führt, beendet der Regelzyklus sofort und läuft nicht mit altem/0-W-Netzwert weiter.
- Zusätzliche Tests sichern Nachtmodus, feste Entladung, feste Beladung, Stop/Hold und normales AUTO-Verhalten ab.
- Defaultwerte für neu erzeugte Konfigurationen sind im Produktivbetrieb weniger verbose: `DEBUG`, `LOG_VALUES`, `LOG_CONTROL`, `LOG_MQTT` und `LOG_SOC` sind standardmäßig `false`. Bestehende `config.json` bleibt unverändert.
- Keine Änderung an Priorität oder Ressourceneinstellungen des Replay-Service in V12.8.4; V12.8.5 ergänzt nun bewusst Ressourcenschutz für den Replay-Service.

## Wichtige Korrekturen seit V12.8.1 / V12.8.2

Die Zwischenversionen V12.8.1 und V12.8.2 korrigierten Analyse-Weboberfläche und Settings-UI:

- Cross-Charge-Ampel wird wieder als Badge statt als sichtbarer HTML-Code angezeigt.
- High-SOC-/Ladeannahme-Zustände werden lesbar statt als JSON/HTML-Escape ausgegeben.
- Controller-Link zur Analyse-Weboberfläche nutzt den dynamischen Host und den Analyse-Port 8090 bzw. `REPLAY_WEB_PORT`.
- Analyse-Tabellen enthalten anklickbare `info`-Erklärungen pro Begriff.
- Maximalwert der Messdaten-Rotationsdateien in den Settings auf 20 erhöht.
- Analyse-Weboberfläche und Textreport verwenden deutsche Zahlendarstellung mit Dezimalkomma. Technische Messdaten-CSV und JSON-Report bleiben unverändert mit Dezimalpunkt.
- V12.8.2 hatte die Schutzgrenze der Mehrdatei-Analyse auf maximal 20 CSV-Dateien erhöht; V12.8.5 reduziert diese Grenze wieder bewusst zugunsten der Raspberry-Pi-Betriebssicherheit.

## Wichtige Änderungen in V12.8

V12.8 erweitert gezielt die Analysefunktionen, ohne den Live-Regelalgorithmus zu verändern.

- Analyse-Weboberfläche V12.8 mit Mehrdatei-Auswahl für CSV-Dateien im Schema `ZEC-MEASUREMENT-V2`.
- Ursprüngliche V12.8-Schutzgrenzen waren 20 Dateien, 50 MB und 500.000 Messpunkte; V12.8.5 ersetzt diese Werte durch konservative Pi-Safe-/Extended-Grenzen.
- Datenqualitätsprüfung: Messdauer, `dt_s`, Datenlücken, fehlende Netz-/SOC-/Zendure-Istwerte, SAFE_STATE-Zeiten.
- Reglerqualitätsanalyse: mittlere/Median/95%-Netzabweichung, Zeit im Zielband, Netzbezug/Einspeisung über Schwellwert, MQTT-Kommandorate, Moduswechsel, Sollwertsprünge und Richtungswechsel.
- Erweiterte Cross-Charge-Analyse: Blockadezeit, kritische Überschneidung SMA-Entladung + Zendure-Ladung, Ampelbewertung und Ereignisliste.
- Nachtentladung und High-SOC werden angezeigt; High-SOC bleibt bewusst nur leichtgewichtig.
- Reports als Text, JSON und CSV-Summary.
- Controller → Analyse-Link nutzt nun dynamisch den aktuellen Hostnamen statt fest `127.0.0.1`.
- Analyse → Controller-Rücklink ergänzt.
- Statusseite: Diagnoseboxen umsortiert und Kurzverlauf-Graph mit stabiler Höhe gegen Layout-Sprünge.

## Messdaten und Analyse

- Aktuelles Messdatenformat seit V12.9.0: `ZEC-MEASUREMENT-V3` mit Semikolon-Trennzeichen und Punkt als Dezimalzeichen. Ältere V2-Dateien werden vom aktuellen Analyse-/Replay-Modus bewusst nicht mehr unterstützt.
- Konsistente signierte Leistungswerte:
  - Netzleistung: positiv = Netzbezug, negativ = Einspeisung.
  - Zendure-/Speicherleistung: positiv = Laden, negativ = Entladen.
- Graph-Konsolidierung: Zendure Sollleistung und Zendure Istleistung werden primär als signierte Linien dargestellt.
- Optionaler, separater Replay-/Analyse-Webdienst auf Port 8090 (`zendure-replay.service`). Der Live-Regler importiert keinen Replay-Code.
- Paketbereinigung: nur noch `tools/`, kein zusätzliches `Tools/`; nur noch `ZendureController.py`, keine doppelte Controller-Startdatei.

## Start

```bash
cd /opt/zendure-controller
python3 ZendureController.py
```

## Dienstbetrieb

Siehe `README_INSTALLATION.md`.

## Analyse-Weboberfläche

Die Analyse-Weboberfläche ist optional und getrennt vom Live-Regler:

```bash
sudo systemctl start zendure-replay.service
```

Aufruf standardmäßig:

```text
http://<RASPBERRY-IP>:8090
```

Die Hauptoberfläche verlinkt dynamisch auf den gleichen Host mit Port 8090. In der Analyseoberfläche gibt es einen Rücklink auf den normalen Controller-Port.

## Dokumentation

Das vollständige DOCX/PDF-Handbuch wurde für diesen Zwischenstand bewusst noch nicht neu erzeugt. V12.8 aktualisiert die technische Basis, README, Installationshinweise und technische Notizen. Eine vollständige Handbuch-Aktualisierung ist für den nächsten größeren stabilen Meilenstein vorgesehen.

## Wichtige Änderungen in V12.9.3

V12.9.3 korrigiert die V3-SOC-Auswertung der Analyse, justiert die lokale Pi-RAM-Preflight-Bewertung für kleine V3-Analysen nach und erweitert das Messdaten-Logging um SD-schonendere Schreibweise. Bool-Felder werden als `1`/`0` geschrieben, der Logger puffert ohne hartes `fsync` pro Messzeile und Messdaten können über Settings auf interne SD, externen Mountpoint/USB-Ziel oder benutzerdefinierten Pfad geschrieben werden. Bei externem Ziel ist ein begrenzter, sichtbarer SD-Fallback möglich. Die Regelstrategie bleibt unverändert.
