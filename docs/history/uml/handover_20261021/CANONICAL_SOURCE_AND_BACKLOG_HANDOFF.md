# Änderungen an kanonischen Projektquellen – genaue Zielanweisung an Hauptentwicklungszweig

**Status:** übergabefähiger **Änderungsvorschlag**, nicht bereits in den Projektquellen umgesetzt. Nutzerentscheidung: UML samt Erweiterungen und Pflege wird dauerhafter Releasebestandteil.

## 1. Backlogautorität: `05_ZEC_BACKLOG_AND_ROADMAP.md`

Vor jeder Ledgeränderung aktuelle `05` vollständig lesen und auf neueren Stand prüfen. Der bestehende Eintrag **`ZEC-BL-DOC-ARCH-001`** ist bereits `CLOSED / V17_1_0_DOC_GATE_PASS` bezüglich erstmaliger Architektur-/Historieninfrastruktur, aber eine **dauerhafte Releasepflicht**. Der neue UML-Auftrag ist **nicht** dadurch automatisch implementiert. Empfohlen:

- Unter `ZEC-BL-DOC-ARCH-001` einen ausdrücklich als **OPEN / IMPLEMENTATION_PENDING** markierten Unter-Scope „UML-Regleratlas – dauerhafte releasegebundene Dokumentationspflicht“ aufnehmen, mit Nutzerentscheidung 21.10.2026, Referenz V0.4-19-Diagramm-Ausgangsstand, Abgleich V17.1.0 und künftigen Release-Gates.
- Wenn der aktuelle Ledger die getrennte Verfolgbarkeit eines eigenständigen Release-Gates benötigt, kann stattdessen/ergänzend eine **neue eindeutige Child-ID** gewählt werden, z. B. `ZEC-BL-DOC-UML-001` – **nur nach Prüfung auf existierende gleiche ID**. Es ist hier **kein** kanonischer Eintrag erzeugt worden.
- Pflicht-Ergebniskriterien: sourceverifizierter aktueller Atlas im `docs/`-Releasebaum, vollständig gerenderte/verlinkte Diagramme, Handbuch-/Dokumentationshinweise, fortlaufende Impact-Pflege pro relevantem Entwicklungsblock, neues UML-Gate in Release-/Fresh-extract-Prozess, Full Sourcecheckpoint & Bibliotheks-Readback.
- Abschlussstatus erst nach realer Implementierung/technischem Releasegate; **Dauerpflicht** danach nicht durch `CLOSED` als erledigt-forgotten behandeln.
- Nie `05` durch `docs/ZEC_Master_Backlog.md` ersetzen; letzteres bleibt nur Release-Snapshot.

## 2. Arbeitsregeln: `01_ZEC_PROJECT_RULES.md` §6b

Ergänzen, nicht ersetzt: „Zum vollständigen versionsgebundenen As-built-Bestand gehört der UML-Regleratlas samt maschinenlesbaren Diagrammquellen, vorgerenderten Ansichten, Traceability und Release-Metadaten. Im Scope jeder relevanten fachlichen Sourceänderung sind betroffene Diagramme nachzuführen oder mit fachlich begründetem `REVIEWED_UNCHANGED` zu bestätigen. Die ausgewählten Bedien-/Handbuchabbildungen/Verweise werden aktuell gehalten. Keine aus Altversion stammende Grafik ohne Sourceabgleich als aktuelle As-built ausliefern.“

Weder Source-/Code-/Safety-Freigabe noch neue Modellgenerationsbindung aus dieser Ergänzung ableiten. Bei größerem sourceänderndem Entwicklungsblock aktive Modelleinstellung / High-Reasoning-Fähigkeit zu Beginn einmal prüfen und Nutzerbestätigung dokumentieren, sofern noch nicht erfolgt.

## 3. Releaseprozess: `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md` §13

Den vorhandenen `DOC_ARCH_HISTORY_GATE` um `DOC_UML_RELEASE_GATE` erweitern (nicht ablösen): vollständige Releasefassung unter `docs/architecture/uml/`, Diagramm-Metadaten/Source-Nachweise, aktuelle Links/Grafiken, Render-/Integritätsprüfung, Fachreview, Manifest- und Fresh-extract-Gates, kein Renderer auf Pi nötig. Jede Releasescope-Planung erfasst UML-Impact; kein aktuelles Diagramm darf ohne Änderung/Review aus einer älteren Sourcebasis übernommen werden.

Beide existierenden Querschnittsverträge bleiben erhalten: `BACKLOG_NO_DROP_GATE` für historische Quellen-/Provenienzbereinigung und `CHECKPOINT_LIBRARY_GATE` für jeden wesentlichen sourceverändernden Block.

## 4. Index/Status: `00_ZEC_PROJECT_SOURCE_INDEX.md`, `02`, `07`

`00` sollte **auf den bestehenden** UML-/Dokumentationsvertrag bzw. dessen Eintrag in `05` und `01`/`06` verweisen; vermeide eine zusätzliche aktive Project-Quelle nur für den UML-Atlas, wenn derselbe Inhalt in der aktuellen Release-Source unter `docs/` verbleiben kann (begrenzte Projektdateislots). `02` ergänzt nur bei tatsächlicher fachlicher Architekturänderung und entsprechendem Code-Nachweis. `07` bleibt Autorität für Release-/Feldevidenz: Dokumentations-QA ist kein realer physikalischer Regel-PASS.

## 5. Source-Release-/Dokumentationsdateien

Mindestens:
- `docs/INDEX.md` (neuer UML-Einstieg), `docs/architecture/README.md`, releasegenaue As-built-Datei;
- Root-`README.md` (kurzer UML-Verweis);
- tatsächlich gepflegte Handbuch-DOCX/PDF und ggf. Datenblatt-DOCX/PDF mit nutzbaren Referenzen; V12.6-Altanleitung nicht stillschweigend als aktuelle Handbuchautorität interpretieren;
- Manifest-/Releasebuild-/Tests/Dokumentationsgate; `docs/ZEC_Master_Backlog.md` aktualisierter **Snapshot**.

**Gezielter Nebendefekt bei Sourceprüfung:** Das ausgelieferte V17.1.0-`docs/architecture/README.md` listet S3 noch als geplanten As-built-Abschnitt („noch nicht erstellt“), während `docs/INDEX.md` bereits auf `docs/architecture/ZEC_V17_1_0_As_Built.md` mit S3-Implementierungsbezug verweist. Im neuen Dokumentationsblock die Architektur-README auf den tatsächlich ausgelieferten Stand harmonisieren und Regression aufnehmen; keine V17.1.0-ZIP-Mutation.

## 6. Prozesssicherheit/No-Drop

Für diese **Übergabe** werden keine Projektquellen geändert/gelöscht; daher kein Bereinigungs-`BACKLOG_NO_DROP_GATE` ausgelöst. Im Hauptzweig bei tatsächlicher Integration alle bisherigen Ledger-IDs und offenen Punkte unverändert erhalten. Falls historische Planungs-/Übergabequellen entfernt/archiviert werden sollen, zuerst das vollständige Gate nach `01` §6a und `06` §7 durchlaufen und erforderlichen Reconciliation-Nachweis führen.

Quellenauflage und Archiv-Duplikation vermeiden: **Der UML-Atlas als Release-`docs/` ist die installierbare/lieferbare Dokumentation, nicht eine eigene zweite Roadmap-/Produktionsautorität.**
