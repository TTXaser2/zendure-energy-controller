## CP33-Quellennachtrag – 27.10.2026

Der gesonderte dreiseitige V18.0.0-Datenblattentwurf liegt unter `ZEC_Technisches_Datenblatt_V18_0_0_ENTWURF.docx` und `.pdf` in diesem Verzeichnis. Er wurde aus DOCX gerendert und auf allen drei Seiten visuell geprüft; `ZEC_Technisches_Datenblatt_V18_0_0_ENTWURF.provenance.json` verbindet die Dateien mit 14 exakten Source-Digests sowie dem unveränderten V17.1.3-Datenblatt. `tools/verify_v18_datasheet_draft.py` ist nur ein read-only Entwurfsintegritätsgate. **Keinerlei Freigabe des produktiven Releases**: finale Identität, Datenblatt-Fachreview, UML, Installer-/Rollback- und reale Battery-Care-Wirkungsabnahme bleiben offen.

# V18.0.0 – Datenblatt-Quellenmatrix (nicht final)

> **DEVELOPMENT_NOT_INSTALLABLE** · **MANUAL_UML_REVIEW_PENDING** · **PHYSICAL_EFFECT_NOT_VERIFIED**  
> Planungs-/Entwicklungsquellen für V18.0.0, keine freigegebenen Produktunterlagen, kein Feld-PASS.

Das **kanonische Release-Datenblatt ist weiterhin V17.1.3** (`docs/ZEC_Technisches_Datenblatt.docx` und `.pdf` mit `docs/ZEC_Technisches_Datenblatt.release.json`). Dieser Entwurf ersetzt diese Artefakte nicht. Vor Freigabe müssen DOCX und PDF neu aus tatsächlich supporteten V18-Sources erzeugt, gerendert und visuell geprüft werden.

| Pflichtbereich | Quellen- und Evidenzbezug | V18-Freigabe |
|---|---|---|
| Releaseidentität | `version.py`, Installer, Source-Manifest, `ZEC_BUILD_EVIDENCE_V1` | PENDING |
| Hardware-/Softwarevoraussetzungen | `README_INSTALLATION_V17_1_3.md`, aktuelle Geräte-/Profilregistry, Installer-Preflight | PENDING_NACHWEIS |
| Topologien: eine/zwei Zendure, mit/ohne Primärspeicher | Aktive Geräteprofile, konkrete Command-Gates und real getestete Topologien | PENDING_NACHWEIS |
| Netzleistungsmessung SMA Energy Meter / Sunny Home Manager | SMA-Speedwire/UDP und OBIS-Interpreter sowie realer Messpfad | PENDING_NACHWEIS |
| Netzleistungsmessung Shelly Pro 3EM / kompatibles Messgerät | Shelly-kompatibler HTTP-Endpunkt, tatsächlicher Runtimepfad | PENDING_NACHWEIS |
| Battery Care, Reserve, PV, Netzpflege, Notladung | `battery_care_policy.py`, `controller_logic.py`, realer Command-/Hardware-Effekt | PHYSICAL_EFFECT_NOT_VERIFIED |
| Ereignis-/Graphprovenienz | `operational_events.py`, `battery_care_graph_history.py`, `battery_care_stage_events.py` | UNITTEST_BASIS_ONLY |
| Recovery, Installer und Rollback | `battery_care_episode_store.py`, Installer, SQLite, Backup-/Recoverytools | PENDING_REALFELD |

Die finale Darstellung darf nur aktuelle Funktionen beschreiben, keine Versionsgeschichte oder behauptete Erweiterung gegen V17.1.3. **MANUAL_UML_REVIEW_PENDING** und **DEVELOPMENT_NOT_INSTALLABLE** bleiben gültig.
