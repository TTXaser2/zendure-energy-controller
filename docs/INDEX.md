# ZEC – Aktueller Architektur-/Historienindex V18.0.1

**Aktueller Source-Release:** V18.0.1 / `v18.0.1-20261102`. Versionsgebundenes As-built und aktuelle Diagramme wurden gegen denselben Kandidaten-Sourcebaum geprüft. Technisches Paket und reale Pi-Feldabnahme sind getrennte Gates.

- [Sourcegebundenes As-built V18.0.1](architecture/ZEC_V18_0_1_As_Built.md)
- [V18.0.1 Release-Informationen](releases/v18.0.1/RELEASE_INFO_V18_0_1.md)
- [V18.0.1 technische Hinweise](releases/v18.0.1/TECHNICAL_NOTES_V18_0_1.md)
- [V18.0.1 UML-Atlas 22 Blätter](architecture/uml/INDEX.md) und [per-Diagramm-Review](architecture/uml/SOURCE_REVIEW_V18_0_1_20261102.md)
- [Master-Backlog als Release-Snapshot](ZEC_Master_Backlog.md) – die Projektquelle 05 bleibt alleinige laufende Autorität.
- [Entscheidungen](decisions/README.md) / [Historische Originale](history/README.md) / [Spezifikationen](specifications/README.md)

---

## Historischer Architektur-/Releaseindex V17.1.3 und ältere Provenienz

# ZEC – Releasebezogener Architektur- und Historienindex

**Aktueller Source-Release:** V17.1.3 / `v17.1.3-20261022`. **Architekturstatus:** As-built bezogen auf diese Sourcebasis. **Nachweis:** technischer Build-/Feldstatus ausschließlich nach dokumentierten tatsächlichen Gates.

- [As-built V17.1.3](architecture/ZEC_V17_1_3_As_Built.md): Sourceunterschiede, Safety-Abgrenzung und QA-Vertrag.
- [V17.1.3 Release-Dokumentation](releases/v17.1.3/RELEASE_INFO_V17_1_3.md): aktueller releasegebundener Dokumentenstand.
- [As-built V17.1.1](architecture/ZEC_V17_1_1_As_Built.md): UI-Hilfe, Minigraph-Zeitmodell, unveränderte Controller-/Safetygrenzen.
- [Historische As-built V17.1.0](architecture/ZEC_V17_1_0_As_Built.md): S3, unabhängiges Live-Monitoring, SMA-Parser, Nacht-/MIN_SOC, Ereignis- und Diagnosepfade.
- [Fast Capture V17.0.2 – historischer Releasebezug](architecture/ZEC_Fast_Capture_V17_0_2.md): historisch versionierte Basis, nicht überschrieben.
- [Freigegebener finaler S3-Produktionsvertrag vom 19.10.2026](specifications/ZEC_S3_PRODUKTIONSSPEZIFIKATION_20261019.md).
- [ADR-0002 expliziter Saison-Opt-in](decisions/ADR-0002-S3-Legacy-Opt-in-20261019.md).
- [Retrospektiver ADR-0001 Fast Capture](decisions/ADR-0001-Fast-Capture-Overlay-retrospektiv.md).
- [Spezifikationen](specifications/README.md), [Entscheidungen](decisions/README.md), [historische Originale](history/README.md).
- [Release-Snapshot Master-Backlog](ZEC_Master_Backlog.md); Roadmapautorität bleibt allein die kanonische Projektquelle `05_ZEC_BACKLOG_AND_ROADMAP.md`.

**Historische Quellen:** Fast-Capture-Original V16.0.2 und S3-Entwurf V17.0.2 sind unverändert mit Originalstatus archiviert. Nicht vorhandene historische Originale werden nicht fingiert. Der vorherige Zwischenstand `architecture/ZEC_S3_und_Live_Status_CKP2.md` bleibt als Entwicklungsprovenienz **nicht** als heutiger As-built-Beleg; dessen dortige „noch nicht umgesetzt“-Liste wurde inzwischen source-seitig überholt.

**Wirkungsgrenze:** ZEC liefert nur Sollwerte/diagnostische Beobachtungen. Physischer Erfolg, Pi-Last und realer Update-/Fresh-Install-Status sind ausschließlich über gesonderte Feldabnahme nachzuweisen.

**Entwicklungsprovenienz vor V17.1.1:** [UX-Hilfen & Minigraph – Development 20.10.](architecture/ZEC_UX_HELP_MINIGRAPH_DEV_20261020.md). V17.1.1 ist als unmittelbar vorheriger Source-Release eingefroren; V17.1.3 wird in eigener As-built beschrieben.

**Aktueller UML-Regleratlas:** [22 Diagramme, DOT/SVG/PNG](architecture/uml/INDEX.md), [fachliches Einzelreview](architecture/uml/SOURCE_REVIEW_V17_1_3.md), vollständiger `DOC_UML_RELEASE_GATE` im Architekturvalidator.
