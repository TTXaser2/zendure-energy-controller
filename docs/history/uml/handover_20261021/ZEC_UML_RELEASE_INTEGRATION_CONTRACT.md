# ZEC UML-Regleratlas – verbindlicher Integrations- und Pflegevertrag

**Datum:** 21.10.2026 · **Status:** von Nutzer gewünschter dauerhafter Releaseumfang; Umsetzung im Hauptentwicklungszweig noch offen. **Referenz:** Altatlas V0.4, 19 Diagramme, basiert auf V17.0.2; aktuelle reale Software V17.1.0.

## 1. Ziel und Abgrenzung

Der bestehende ZEC UML-Regleratlas wird kein einmaliger Chat-Anhang mehr, sondern ein **erster as-built-Dokumentationsbestand** mit versionierten Diagrammquellen, fertigen Abbildungen, Navigationsindex, Source-Traceability und releasebezogener Änderungsprüfung. Mit **jedem** künftigen Produktrelease ist er in passender Fassung vorhanden. Änderungen an relevanter Regel-/Sicherheits-/Command-/Integrationslogik lösen eine fachliche UML-Impact-Prüfung **im selben Entwicklungsblock** aus; nach Bedarf werden Bestandsdiagramme geändert und neue ergänzt. Dokumentations-only-Releaseänderungen ohne fachlichen Diagrammdelta benötigen einen dokumentierten `REVIEWED_UNCHANGED`-Nachweis, nicht sinnlose Gesamterneuerung.

**Nicht Teil dieses Blocks:** Controller-/Safety-/Command-Semantik ändern, einen zweiten Dokumentations- oder Roadmap-Owner schaffen, neue Produkt-Web-UI-Funktion behaupten, bestehende ausgelieferte ZIPs nachträglich mutieren, alte V17.0.2-Diagramme unbesehen als V17.1.0-As-built ausgeben.

## 2. Ausgangsbefund und Übernahmereihenfolge

- Aktuelle Quelle: `zendure_controller_v17_1_0.zip` (SHA256 `11dddaaaa7831e2339a19b9b7f46412ee72f35917935b7292a005a47bfe61669`); Sourceversion/Basis bei Hauptzweigstart erneut prüfen.
- Bestehende Dokumentationsarchitektur: `docs/INDEX.md`, `docs/architecture/`, `docs/specifications/`, `docs/decisions/`, `docs/history/`; bestehendes `DOC_ARCH_HISTORY_GATE` nutzen und **erweitern**, kein konkurrierender Parallelvertrag.
- V0.4-Original als **historisch versionierten Ausgangspunkt** einlesen, nicht neu erfinden. ZIP, inneres `CHECKSUMS.sha256`, Inventar/README/Traceability nach Extraktion validieren. `.dot` war grafisch gerendert, SVG und PNG geprüft; **PlantUML `.puml` war damals nicht syntax-render-geprüft**, nicht als validiert behaupten.
- V0.4-Quellen sind gegen V17.1.0 **vollständig fachlich zu reconciliieren**. Dabei markieren: identisch gültig, nur Wortlaut/Version anpassen, inhaltlich korrigieren, neu ergänzen, als V17.0.2-Historie erhalten.
- Keine Quelle nach der Migration löschen/überschreiben, bevor Provenienz und Backlog-/No-Drop-Regeln beachtet sind.

## 3. Verbindliche Zielstruktur im versionierten Source-Root

```text
docs/
  INDEX.md                                    # bestehender zentraler Dokuindex; UML verlinken
  architecture/
    README.md                                 # bestehende As-built-Navigation; UML verlinken
    ZEC_<RELEASE>_As_Built.md                 # bestehender releasegenauer Text; UML-Querverweise
    uml/
      README.md                               # Begriffslexikon, Status, Lesewege, Lizenz/Herkunft
      INDEX.html                              # offline und aus Fresh Extract funktionsfähig
      INDEX.md                                # ohne Browser lesbar
      RELEASE_TRACEABILITY.md                 # diagram_id -> Sourcepfad/Symbole/Tests/Datum/Basis
      CHANGE_IMPACT.md                        # Diagramm-Review des konkreten Releases
      diagrams/
        01_...dot                             # editierbare kanonische Quelle, je Diagramm festlegen
        01_...puml                            # nur falls toolseitig validiert oder als sekundär markiert
        ...
      rendered/
        01_...svg                             # vektorielle, direkt nutzbare Abbildung
        01_...png                             # für DOCX/PDF/Fallback, falls erforderlich
      manifest.json                           # Version, IDs, Status, Autorität, Quellen/Hashes
  history/
    uml/
      README.md                               # provenance V0.4/V17.0.2 und Nachfolgestände
  Zendure_Energy_Controller_Handbuch.docx      # bestehende Dokumente prüfen
  Zendure_Energy_Controller_Handbuch.pdf
  ZEC_Technisches_Datenblatt.docx/pdf         # bestehender eigenständiger Vertrag bleibt
  ZEC_Master_Backlog.md                      # bestehender Snapshot, keine Roadmapautorität
```

Pfade sind ein **konkreter Vorschlag**, keine Aufforderung vorhandene Dateien zu löschen. Auf bestehende Verzeichnisnamen/-Konventionen abstimmen; bei Abweichung denselben Funktionsvertrag belegen. Die komplette aktuelle UML-Auslieferung liegt **im Release-ZIP**, nicht ausschließlich in der Projekt-Dateiliste oder einer Chat-Library. **Kein Graphviz/PlantUML/Node.js zur Anzeige auf dem Raspberry Pi nötig**: HTML/SVG/PNG müssen bereits im Build vorliegen. Renderer nur buildseitig.

Originalatlas V0.4 als historische Provenienz erhalten: mindestens Quelle/Originalhash/Status/Quelle-zu-Nachfolger-Mapping und tatsächlich gesichertes Original im unabhängigen Archiv; vollständig mehrfach in jedem späteren Installer-ZIP zu duplizieren ist nicht zwingend. Für die aktuelle Releasefassung zählen allein die nach V17.1.0/relevantem Nachfolgerelease verifizierten Quellen.

## 4. Pflegeverantwortung im Entwicklungsworkflow

**Vor jeder fachlichen Sourceänderung:** im Scope/Checkpointplan betroffene Diagramm-IDs markieren. Besondere Trigger: Betriebsmodus und Dispatch; Harvest/High-SOC/S3; Netzein-/export-Mathematik; MIN/MAX_SOC; Night; Fast Capture; Cross-Charge; Command Lifecycle; Readback/Effect/Recovery; Primärquellen und Netz-SMA/Shelly; Status-/Diagnosefelder, wenn sie in Diagrammen auftauchen; Battery Care/B2/C1/Adaptive sofern später implementiert.

**Bei Implementierung:** Quellpfade, Methoden, Guards, zeitliche Semantik, Migrations-/Defaultverhalten, Grenzen, Datenprovenienz und physische Wirkung sorgfältig abgleichen. Abgeleitete Sollmathematik und illustrative Beispielzahlen als solche markieren. Keine implizite Gleichsetzung von `current_mode`, Harvest-Branch, Profil/Season, `STRATEGIC_SHARE`, Fast-Capture-State und Command-Effekt.

**Vor Source-Freeze:** aktualisierte Diagramm-Source + gerenderten Zielstand + technische Traceability + Dokumentationsindex + ausgewählte Handbuchverweise im selben Checkpoint sichern. Eine dokumentierte Review-Tabelle aller Diagramme ist Pflicht; nicht geänderte Blätter dürfen byteidentisch bleiben, müssen aber geprüft sein.

**Nach Release:** Original des ausgelieferten UML-Snapshots bleibt zusammen mit dem Source-Release unverändert. Nachfolger verändern nur ihren eigenen Source-Tree. Handbuch-/Querverweis-Pflege wird zu einem wiederkehrenden Schritt des Release-Freeze, nicht einem optionalen späteren Chatprojekt.

## 5. Zielgruppen und Verweise

- `docs/INDEX.md`: auffindbarer „UML-Regleratlas“ mit Einstieg und konkretem Release-/As-built-Status.
- `docs/architecture/README.md` / `ZEC_<RELEASE>_As_Built.md`: technische Verweise auf Modus-, Ablauf-, Pipeline-, Guards-, Hardware- und S3-Blätter; alle internen Links relativ und im final entpackten ZIP funktionsfähig.
- Haupt-`README.md`: kurzer Abschnitt „Technische Architektur und UML“ mit Link auf `docs/architecture/uml/INDEX.md` bzw. `INDEX.html`.
- **Benutzerhandbuch:** technisch lesbare ausgewählte Überblicksgrafiken einbinden oder mit stabilem Kapitel-/Dokumentverweis auf den Atlas zeigen (z. B. Regelzyklus, Betriebszustände, Ladezielpipeline, Sicherheit); kein ungefragtes Einbinden aller 19+ Großdiagramme in das Handbuch. Tatsächlich gepflegte aktuelle Handbuchfassung und DOCX/PDF-Buildprozess zuerst prüfen; die V12.6-Altunterlagen als historische Dokumente behandeln.
- Technisches Datenblatt: knapper Hinweis auf Architektur-/UML-Dokumentation, ohne den Datenblatt-Istzustand oder die getrennten DOCX/PDF-Gates zu verwässern.
- Optional Settings-Hilfe/Expertenmodus: nur echte offline/online erreichbare, unterstützte Links; keine neue UI-Funktion ohne eigenen freigegebenen Scope.

## 6. Wahrheits-, Versionierungs- und Evidenzregeln

- Dokumente nennen **konkretes Release/Build**, Diagramm-ID/-Version, `AS_BUILT|HISTORICAL|ILLUSTRATIVE|DRAFT`, tatsächlich verifizierten Sourcebereich und Test-/Feldbezug. `AS_BUILT` ist Sourcewahrheit, **nicht automatisch reale Funktionsfeldabnahme**.
- S3 in V17.1.0: Zeitgrenzen sind **konfigurierbare Runtimeinputs** mit 09:30/11:30/14:30/18:00 als verhaltenskompatiblen Defaults; Confirm/Share ebenso. Saisonpolicy `HARVEST_SEASON_POLICY_ENABLED=false` default/Legacy; `season_requested` und effektiv `legacy_parallel` sind auseinanderzuhalten. `STRATEGIC_SHARE` ist `target_selected_by`, **kein current_mode**.
- Fast-Capture-`FULL_IDLE` vs. Harvest-`SMA_FULL_OR_IDLE` und Fast-`NEAR_LIMIT` vs. Harvest-`SMA_NEAR_LIMIT` nicht verwechseln. Overlay `O` vs. Baseline `B` getrennt; Export-Capture-Floor, Cross-Charge und Hard-Safety bleiben höhere Einschränkungen.
- NIGHT/MIN_SOC/Grid-Verarbeitung gemäß V17.1.0 nicht mit veralteter V17.0.2-Branch-Skizze darstellen; reale Naturnachweise separat offen.
- `GRID_STALE`-Ereignis ≠ Regelmodus; `/status-live-data`-Browser-Poll 1 s ≠ Device-Neumessung 1 Hz und ≠ 3-s-Regelzyklus; SMA strukturierte OBIS-Parsergrenzen als Sourceabsicherung unterscheiden.
- Kommando-Publish/Readback/physische Wirkung/Recovery bleiben vier getrennte Ebenen. Offene `NOT_EVALUABLE`-Feldevidenz in keiner Grafik als reale Wirksamkeit/PASS ausweisen.
- Adaptive/B2/C1/Battery Care aktuell **nicht** durch S3 oder UML als aktive, freigegebene Controllerfunktionen beschreiben.

## 7. Verbindliche Abgabe des Hauptentwicklungszweigs

- Vollständiges **neues** source-/releasegenaues UML-Inventar mit ≥19 reconciliierten Bestandsdiagrammen, begründetem Zuwachs, editierbaren Quellen und Anzeigeformaten;
- gepflegte `docs`-Indices, reale Crosslinks und geeignete Handbuch-/Datenblatt-Verweise;
- dokumentiertes `CHANGE_IMPACT` und `RELEASE_TRACEABILITY`, alte Atlas-Provenienz;
- automatisch und fachlich geprüfter, in den Release-Workflow integrierter `DOC_UML_RELEASE_GATE` plus bestehender `DOC_ARCH_HISTORY_GATE`;
- Tests einschließlich negativer Cases und Fresh Extract des **finalen unveränderlich veröffentlichten neuen** Release-ZIPs;
- vollständiger Sourcecheckpoint, Library-Upload + byteidentischer Readback gemäß `01` §3, SHA256, Test-/Gateprotokoll und No-Drop-/Ledgerstatus;
- **keine** zusätzliche Reglerlogikänderung allein aus dem Dokumentationsprojekt.

Dieses Makroziel ist als Nutzerentscheidung bindend. Technischer Implementierungs-Scope muss vom Hauptentwicklungszweig auf der tatsächlich aktuellen Sourcebasis überprüft und bei Bedarf konkretisiert werden; geschützte Controlleränderungen bleiben separat freigabepflichtig.
