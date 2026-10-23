# Release-Gate für versionierten UML-Regleratlas

**Vorgeschlagen:** `DOC_UML_RELEASE_GATE` als **integraler Teil** des vorhandenen `DOC_ARCH_HISTORY_GATE`; nicht eine parallele Dokumentationsinstanz. Implementierung und präzise Namen gegen aktuelle Buildtools verifizieren.

## A. Deterministisches Build-/Package-Gate – maschinell

1. **Bestand:** Alle im UML-Manifest `current` gekennzeichneten IDs besitzen mindestens eine editierbare, tatsächlich kanonisch benannte Diagrammquelle sowie ein validiertes SVG. PNG nur für die Diagramme, die es als Benutzer-/Handbuch-Fallback brauchen; bei Übernahme der 19 Altdiagramme sind ihre bestehenden PNGs mitzuführen, solange nicht ausdrücklich anders dokumentiert. Index/README/Release-Traceability/Change-Impact/Manifest vorhanden, nicht leer.
2. **Releaseidentität:** `APP_VERSION`, Build-ID und UML-As-built-Metadaten stimmen mit dem gerade gebauten Source-Tree überein. Keine feste Einprogrammierung von `V17.1.0` als ewig gültiger Wert. Altversionen dürfen explizit nur als `HISTORICAL` referenziert sein.
3. **Referenzen:** `docs/INDEX.md`, `docs/architecture/README.md`, lokale MD- und HTML-Linkziele, SVG/PNG-Dateien, Bildreferenzen aus dem aktuellen Handbuch / optionalen As-built-Querverweisen sind innerhalb der entpackten Release-Dateien erreichbar. Kein absoluter Sandbox-Pfad oder nur auf einem Entwicklerrechner erreichbarer Link.
4. **Sourceintegrität:** Diagramm-Sources und Renderoutputs mit SHA256 im Manifest. Originale nicht stillschweigend verändern. Für veränderte kanonische `.dot`-Quellen `dot`-Syntax/Rendering beim Build testen; SVG als XML parsen; PNG öffnen/Format prüfen. `.puml`-Quellen **nur dann als verifiziert ausweisen**, wenn sie mit PlantUML gegen definierte Version/Syntax erfolgreich gerendert wurden; andernfalls als `SECONDARY_UNVERIFIED` kennzeichnen oder später formal validieren. Ein erfolgreich gerendertes `.dot` validiert **nicht** automatisch das `.puml`.
5. **Abdeckung:** `CHANGE_IMPACT.md` enthält für jede zum Release gehörende Diagramm-ID genau einen aktualisierten Status `UPDATED|NEW|REVIEWED_UNCHANGED|HISTORICAL_ONLY`, Release-ID, fachlichen Source-Verweis, Reviewdatum und ggf. bewussten Geltungsausschluss. Kein vom Controllerdelta betroffenes Diagramm ohne Review.
6. **Packaging:** Quellen, SVGs, ggf. PNGs, Navigation und Traceability müssen im Source-/Paketmanifest enthalten sein. Nach Erzeugung des finalen Installer-ZIPs aus frischem Extract Verzeichnisbaum, Hashes, Links und UML-Gate erneut prüfen. V17.1.0-ZIP mit bereits veröffentlichter Identität nicht verändern.
7. **Runtimefreiheit:** kein zur Anzeige benötigtes Graphviz, PlantUML, Node.js, Browser-Netzwerk-CDN oder Python-Zusatzmodul auf dem Ziel-Pi voraussetzen. HTML offline anzeigen; SVG aus ZIP direkt zugänglich. Render-Tooling nur Buildzeit.
8. **Sicherheit/Hygiene:** keine echten privaten IP-/Geräte-IDs, passwortähnlichen Werte, produktiven `config.json`-Inhalte oder personenbezogene V4-Rohdaten unredigiert in Diagrammquellen/Meta aufnehmen. Beispielwerte ausdrücklich als synthetisch deklarieren.

## B. Fachliche As-built-Abnahme – reviewpflichtig

1. Aktueller Regelzweig samt Zustands- und Zielwertsemantik gegen **konkrete Produkt-Source** prüfen; nur gegen Altatlas prüfen reicht nicht.
2. Priority/Safety-Schranken: Export-Capture-Untergrenze, MIN/MAX, Cross-Charge, Nacht-/Manual-Neutralisierung, Commandwirkung/Resync, Fast B/O sauber getrennt.
3. Releaseunterschiede explizit modellieren: insbesondere V17.1.0 S3 opt-in/Saison, 1-Hz-UI vs. Quellen-/Regelzyklus, NIGHT/MIN_SOC/Grid und OBIS; spätere Controller-Releases jeweils eigenständig.
4. Drei Ebenen auseinanderhalten: **(a)** Source-as-built, **(b)** hypothetische/synthetische Rechenbeispiele, **(c)** reale Feldevidenz. `NOT_EVALUABLE` nicht als `PASS` auflösen.
5. Diagrammlesbarkeit: Schriftgröße, Kanten, Ausfransungen, Überlappungen, deutschsprachige Terminologie, Legende und klares Ziel. Für übergroße Diagramme in mehrere Blätter aufteilen. SVG/PNG visuell stichprobenartig (alle geänderten/neuen) prüfen.
6. Alle existierenden Diagramme erhalten reviewfähige Deltaentscheidung: `UPDATED`, `REVIEWED_UNCHANGED` oder `HISTORICAL_ONLY` mit nachvollziehbarer Begründung.

**Ein rein automatisches PASS garantiert keine mathematische/physikalische Richtigkeit.** Dafür ist ein dokumentiertes fachliches Review vor Source-Freeze erforderlich.

## C. Vorgeschlagene Testfälle

- Fehlende Diagrammquelle / fehlendes gerendertes SVG / leere `INDEX.md` → FAIL.
- `manifest.json` deklariert falsche Version oder Source-SHA → FAIL.
- Broken `docs/INDEX.md` → UML link oder ungültiges relatives HTML/SVG → FAIL.
- Kompromittiertes/ungültiges SVG und DOT-Syntaxfehler → FAIL.
- Neue S3-/Harvest-Sourceänderung ohne betroffene 03/04/14/16/18/19 im Impact-Bericht → FAIL.
- Übernahme von V0.4 Blatt 19, das die Zeitfenster als **hardcoded aktuell** darstellt, obwohl V17.1.0 Runtime S3-Settings nutzt → fachlich FAIL.
- `HARVEST_SEASON_POLICY_ENABLED=false` als faktisch wirksame `sma_priority` darstellen → fachlich FAIL.
- Fehlender Nachweis der tatsächlichen PlantUML-Verifikation bei behauptetem `.puml`-PASS → FAIL beziehungsweise Eigenschaft ehrlich `SECONDARY_UNVERIFIED`.
- Reine Source-/Dokumentenänderung ohne UML-Wirkung, aber dokumentiert `REVIEWED_UNCHANGED` → PASS, sofern prüfbar.
- Fresh-extract verliert SVG/Querverweise oder Manifest-Dateien → FAIL.
- Dokumentation sagt `FULL_IDLE Active field PASS` trotz offener natürlicher Episode → fachlich FAIL.

## D. Exit- und Protokollpflicht

Der technische Releasebericht enthält künftig: `DOC_ARCH_HISTORY_GATE`, `DOC_UML_RELEASE_GATE`, Anzahl `CURRENT/HISTORICAL`, `UPDATED/NEW/REVIEWED_UNCHANGED`, sourcebezogene Prüfbasis, Render-/Syntax-/SVG-/HTML-/Link-/Hash-/Fresh-extract-Resultate, manuelle Sichtprüfung, offene Abweichungen und Begründungen. Ein negatives UML-Gate blockiert den **vollständigen Release-PASS**; es erzeugt keinen Regler-/Hardwarefehlerstatus. Bei Versionen, für die UML als Pflichtbestandteil beschlossen ist, ist `NOT_EVALUABLE` kein vollständiger Release-PASS.

`CHECKPOINT_LIBRARY_GATE` bleibt **unverändert separat und zwingend**: vollständiges ZIP des Arbeitsstands in persönliche Bibliothek, unabhängiger Download/Materialisierung und byteidentischer SHA/CRC-Nachweis nach `01` §3 und `06` §11. Ein lokaler ZIP-Link ist kein externer Checkpoint.
