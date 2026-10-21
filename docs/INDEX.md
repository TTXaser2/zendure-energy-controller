# ZEC – Releasebezogener Architektur- und Historienindex

**Aktueller Source-Release:** V17.1.1 / `v17.1.1-20261020`. **Architekturstatus:** As-built bezogen auf diese Sourcebasis. **Nachweis:** technischer Build-/Feldstatus ausschließlich nach dokumentierten tatsächlichen Gates.

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

**Entwicklungsprovenienz vor V17.1.1:** [UX-Hilfen & Minigraph – Development 20.10.](architecture/ZEC_UX_HELP_MINIGRAPH_DEV_20261020.md). Aktueller Produktstand wird getrennt in As-built V17.1.1 beschrieben.
