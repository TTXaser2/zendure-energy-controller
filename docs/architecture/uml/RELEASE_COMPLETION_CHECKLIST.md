# UML-Regleratlas – offene Freigabearbeiten vor dem nächsten Sammelrelease

**Status:** `UML_SOURCE_REVIEW_PASS / RELEASE_QA_PENDING / NOT_INSTALLABLE`, 22.10.2026.
**Produktionsbaseline:** veröffentlichtes V17.1.2; V17.1.3 ist ausschließlich der neue in Arbeit befindliche, noch nicht freigegebene Sammelrelease. Der ältere unautorisierte V17.1.3-CP02-Frontendkandidat ist keine Ausgangsautorität.
**Dauerauftrag:** `ZEC-BL-DOC-ARCH-001`; projektweite Normen `01` §6b, `06` §13.

## Vor finaler Paketierung zwingend

1. Erst nach Abschluss des fachlichen **gesamten** Releaseumfangs den definitiven Folgerelease-Build bestimmen; dann `version.py`, Release-README, Version-/Handbuch-/Datenblattreferenzen und den UML-Atlas *gemeinsam* für genau diese Sourcebasis neu prüfen.
2. **Alle 22 Diagramme einzeln** gegen konkrete Kontroll-/State-/Telemetry-/Command-Quellen und Tests fachlich abnehmen. Neue/relevante Quellendeltas seit V17.1.3 einschließen; keine semantische Freigabe aus erfolgreichem DOT-/SVG-Rendering ableiten. `CHANGE_IMPACT` dokumentiert alle IDs; Kennzeichnung `SOURCE_REVIEW_REQUIRED` bis zum tatsächlichen Review. Insbesondere S3 requested/effective/applicability; MIN_SOC-Exportpfad; Fast-Capture-B/O; neutralize/Readback; Grid-Stale und 1-s-Status getrennt beurteilen. `STRATEGIC_SHARE` ist nur Auswahlmarker.
3. Visuelle Prüfung **aller geänderten/neuen** Diagramme in lesbarer Zielgröße sowie stichprobenartig unveränderter Abbildungen. Große/zu breite Diagramme bei Bedarf vereinfachen oder in Teilblätter gliedern. DOT/SVG/PNG werden buildseitig gerendert, Pi benötigt keine Renderer. Historische PlantUML-Dateien bleiben `SECONDARY_UNVERIFIED`, bis tatsächlich separat mit PlantUML nachgeprüft.
4. Die tatsächlich gepflegten **aktuellen** Handbuch-/Datenblattfassungen für den neuen Release aktualisieren und geeignete Navigationsverweise/Übersichten einbauen. Das vorhandene V13.0.2-Handbuch nicht fälschlich zum aktuellen Handbuch umetikettieren; bei Bedarf neue aktuelle Benutzerhandbuchfassung mit gesondertem redaktionellem und visuellen Gate erstellen. Aktuelle DOCX/PDF-Versionen mit der dann realen Release-ID neu rendern und prüfen. Das veröffentlichte V17.1.2-Datenblatt bleibt unveränderliche Release-Provenienz.
5. Für das tatsächlich neue Release `docs/architecture/ZEC_<NEW>_As_Built.md` sowie `docs/releases/<new>/` und den dynamischen Release-Architekturvalidator bedienen. In Manifest und `RELEASE_TRACEABILITY` neue Sourceidentität/Hashes aktualisieren. Inhaltliche Claims `AS_BUILT_RELEASE_APPROVED` und pro Diagramm `SOURCE_REVIEW_PASS` **erst nach** dokumentierter fachlicher Freigabe und Reviewbeleg setzen.
6. Normale Regression, strenge `ResourceWarning=error`-Regression, DOT-/SVG-/PNG-/Link-/Hash-/Manifestsuite, DOCX/PDF-Rendering, frischen Extract der finalen Paketbytes, Datenblatt- und Dokumentationsgates voll durchlaufen. Aktuell erwarteter `DOC_UML_RELEASE_GATE=FAIL` wegen offener Fachabnahme ist **kein** Release-PASS.
7. Nach jedem größeren Quellblock vollständigen ZIP-Checkpoint extern in persönliche Bibliothek sichern, unabhängig per SHA256/Byte/CRC zurücklesen. Bestehende V17.1.3/CP02-Artefakte unverändert lassen. Projektquellen `00/01/05/06` werden als **Ersatz**, nicht zusätzliche Projektdateien, angeboten und müssen erst vom Nutzer tatsächlich übernommen werden.

## Verifikationsgrenzen

- Technischer UML-Gate kann mit `python3 -m tools.verify_uml_release --root . --technical-only --json` geprüft werden.
- Vollständiger Release-Gate `python3 -m tools.verify_uml_release --root . --json` und `tools/verify_arch_history.py` müssen bei fehlender fachlicher Freigabe weiter fail-closed bleiben.
- Dieses Dokument **autorisiert weder Controller-/Command-/Safetyänderungen noch eine zusätzliche Pi-Installation** und erzeugt keinen neuen Produktrelease.


**Update 22.10.2026:** 22/22 DOT-Source- und Visualreviews durchgeführt; Beleg `SOURCE_REVIEW_V17_1_3.md`; diese Checkliste beschreibt historisch die damaligen Reviewpflichten, nicht erneut offene UML-Einzelreviews. Die vollständige Release-QA und Fresh-extract-Abnahme bleiben unverändert zwingend.
