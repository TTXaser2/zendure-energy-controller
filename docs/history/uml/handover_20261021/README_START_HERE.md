# ZEC – UML-Regleratlas als dauerhafter Releasebestandteil

**Handover:** 21.10.2026 · **Herkunft:** ZEC UML-Regleratlas V0.4 (19 Diagramme, im vorangegangenen UML-Chat erzeugt) · **Ziel:** Hauptentwicklungszweig · **Status:** VERBINDLICHER NUTZERWUNSCH / ÜBERGABEVERTRAG, **noch nicht in Produkt-Sources implementiert**.

## Was ist beschlossen?

Der aktuelle UML-Regleratlas und künftig gepflegte/ergänzte Diagramme sollen fester, versionierter und **releasegenau verifizierter** Bestandteil des ZEC-Sourcebaums, der Installations-Releases und der passenden technischen Dokumentation werden. Pflege darf bei Weiterentwicklung nicht vergessen werden. Die Atlas-Grafiken sollen sowohl elektronisch als auch ohne Spezialwerkzeuge nutzbar bleiben. Es geht **um Dokumentation und Releaseprozess**, nicht um neue Reglersemantik.

## Sofort im Hauptentwicklungszweig

1. `STARTPROMPT_HAUPTENTWICKLUNG.md` als Startprompt verwenden.
2. `ZEC_UML_RELEASE_INTEGRATION_CONTRACT.md` und `V17_1_0_IMPACT_AND_SOURCE_MATRIX.md` vollständig lesen.
3. **Zuerst** kanonische Quelle `00_ZEC_PROJECT_SOURCE_INDEX.md`, dann `01`/`02`/`03`/`04`/`05`/`06`/`07` und den realen aktuellen Sourcefreeze einlesen; durch diese Übergabe werden sie nicht ersetzt.
4. **Originales** `ZEC_UML_REGLERATLAS_V0_4.zip` aus dem UML-Chat zur Verfügung stellen bzw. aus dem nachweislich vorhandenen Originalspeicher beziehen, SHA256 prüfen, dann gegen aktuelle Sources reconciliieren. Dieses ZIP ist **nicht** im vorliegenden Handover enthalten, da es im aktuellen Dateisystem nicht zugänglich ist; keine Rekonstruktion der unverifizierten Originalbytes behaupten.
5. Einbindung/Automatisierung auf dem aktuellen Releasezweig verifizieren und beim **nächsten neu gebauten** Release mit ausliefern. Keine Veränderung der bereits veröffentlichten V17.1.0-Release-Identität.

## Verifizierte Ausgangsbasis (21.10.2026)

- Aktuelle reale Runtime V17.1.0 / Build `v17.1.0-20261019`; Installation und allgemeine Feldabnahme FULL_READY PASS; einzelne Funktions-Feldevidenzen noch ausstehend.
- Originalrelease `zendure_controller_v17_1_0.zip` SHA256 `11dddaaaa7831e2339a19b9b7f46412ee72f35917935b7292a005a47bfe61669`; im aktuellen Arbeitskontext **selbst nachgeprüft**.
- Sourcebaum enthält schon `docs/INDEX.md`, `docs/architecture/`, `docs/specifications/`, `docs/decisions/`, `docs/history/`, `tools/verify_arch_history.py` und `tests/test_v17_1_0_documentation_consistency.py`.
- Bestehende Master-Ledger-ID `ZEC-BL-DOC-ARCH-001` und Prozesspflichten `01` §6b / `06` §13 sind die Grundlage dieser Erweiterung.
- **Altatlas V0.4:** aus vorausgegangenem Chat berichtet: 19 Diagramme, V17.0.2-Sourcebasis, ZIP-Name `ZEC_UML_REGLERATLAS_V0_4.zip`, behauptete SHA256 `1b1229b8958bafbd69cd676a1986e77605dd09673847b6872ef54481a4a8a4c5`, Größe 7.790.684 Byte. **Nicht hier erneut byteverifiziert**. Falls der Originalhash nicht passt: STOP/Verifikation, nicht automatisch übernehmen.

## Inhalt des Übergabepakets

- `ZEC_UML_RELEASE_INTEGRATION_CONTRACT.md`: verbindlicher Funktions-/Quell-/Release-/Lifecycle-Vertrag.
- `V17_1_0_IMPACT_AND_SOURCE_MATRIX.md`: vollständige Prüfung der 19 Bestandsblätter + V17.1.0-Neuerungen.
- `UML_RELEASE_GATE_SPECIFICATION.md`: Build-/Fresh-extract-/fachliche Abnahmekriterien.
- `CANONICAL_SOURCE_AND_BACKLOG_HANDOFF.md`: vorgeschlagene präzise Einträge in `05`, `01`, `06`/Verweis `00`, ohne Änderungen vorwegzunehmen.
- `STARTPROMPT_HAUPTENTWICKLUNG.md`: direkt nutzbarer Makroauftrag.
- `RELEASE_V17_1_0_SOURCE_VERIFICATION.md`: real geprüfte Dateipfade und Befunde.
- `MANIFEST.sha256`: lokale Inhaltsintegrität der Markdown-Dateien des Handover-Pakets; **kein** Library-Checkpoint-Gate.

**Wichtig:** Dieses Paket ist eine gebrauchsfertige Übergabe und kein neuer ZEC-Sourcecheckpoint. Es wurden weder Produkt-Sources noch kanonische Projektquellen verändert. Eine externe Bibliotheks-Checkpoint-Freigabe wird hier nicht behauptet.
