# ZEC Battery Care – Releasevorbereitung V18.0.0 (Entwurf)

**Status:** `DEVELOPMENT_NOT_INSTALLABLE` · **Stand:** 27.10.2026 · **Quelle:** CP26 (SHA256 `03075f2c2a2a16669e2399e6c5af7462c826282b12f9ccc71d2e748e22808844`).

## Versionsentscheidung und Evidenzgrenze

Gemäß `01_ZEC_PROJECT_RULES.md` §5 ist Battery Care ein neues Entwicklungsthema nach der zuletzt produktiven V17.1.3: daher **vorgeschlagene nächste Hauptversion V18.0.0**. `v18.0.0-20261027` ist ausschließlich eine **vorläufige Prüfreferenz**, **kein** veröffentlichter oder eingefrorener Build. Das finale Builddatum wird beim tatsächlichen Release-Freeze festgelegt, einschließlich *erneuter* Ausführung sämtlicher Identitätsgates. Keine RC-Nummer; keine Verwendung der bereits veröffentlichten V17.1.3-Identität für einen neuen Build.

Die produktive Runtime auf dem Pi bleibt `V17.1.3 / v17.1.3-20261022`. Der V17.1.3-Installer ist auf `V17.1.2 / v17.1.2-20261021 → V17.1.3 / v17.1.3-20261022` spezialisiert und darf **nicht** lediglich mit einer umbenannten ZIP-Datei für Battery Care genutzt werden.

## Erforderliche atomare Umstellung vor einem releasefähigen Paket

| Bestandteil | Erforderliches Verhalten beim tatsächlichen V18.0.0-Release | CP27 |
| --- | --- | --- |
| `version.py` | `18.0.0`, `V18.0.0`, eindeutige finale Build-ID | bewusst unverändert |
| `tools/install_zendure_controller.sh` | exaktes Ziel V18.0.0 + Build, unterstützte Updatequelle **V17.1.3 / v17.1.3-20261022**, korrekter ZIP-Root/Manifest; keine Schreibaktion vor Preflight | bewusst unverändert |
| Manifest / Build-Evidence | `V18_0_0_SOURCE_MANIFEST.sha256`, `validation/V18_0_0_BUILD_EVIDENCE.json`, vollständige SHA/CRC/Fresh-extract- und Reproduzierbarkeitsprüfung | ausstehend |
| Feldabnahme | Versions-/Build-gebundenes `tools/v18_field_acceptance.py` mit realen, vorerst nicht erfüllten PV-/Netzpflege-/Notlade-Evidenzpunkten | ausstehend |
| Release-Dokumente | `README_INSTALLATION_V18_0_0.md`, kanonisches `README_INSTALLATION.md`, `README.md`, `docs/INDEX.md`, `docs/releases/v18.0.0/{RELEASE_INFO,TECHNICAL_NOTES,BUILD_VALIDATION}_V18_0_0.md`, `docs/architecture/ZEC_V18_0_0_As_Built.md` | ausstehend |
| Datenblatt | DOCX + PDF nur aus finalen Source- und Geräteprofilen; Metadaten-SHA, V18.0.0/Build; Pflichtpfade SMA-Speedwire **und** Shelly-HTTP | ausstehend |
| UML | 22 Diagramme gegen finalen Controller, aktualisierte Manifest-Identität, **echte manuelle fachliche Source-/Visualfreigabe** | technische CP26-Quelle vorhanden, manuell offen |
| Deployment-/Recovery | Fresh-extract, `SUPPORTED_UPDATE`, `CLEAN_FRESH_INSTALL`, fail-closed Partial State, SQLite-Migration, Rollback, Portvarianten, Supportbundle ohne Secrets; echte Clean-Fresh-Pi-Prüfung gesondert | ausstehend |
| Realfeld | Nutzerfreigabe vor Installation; danach echter Ladeeffekt, Command-Wirkung, Power-Cut- und Restart-Recovery nur mit realer Messung | `NOT_EVALUABLE` |

## Eigenständiges Identitätsgate in CP27

`tools/verify_release_identity_readiness.py` erfasst **mutationsfrei** Identitätswidersprüche. Beispiel eines erwarteten **FAIL** beim derzeitigen Entwicklungsbaum:

```bash
python3 tools/verify_release_identity_readiness.py \
  --root . --candidate-version 18.0.0 \
  --candidate-build v18.0.0-20261027 \
  --source-version 17.1.3 --source-build v17.1.3-20261022 --json
```

Ein zukünftiger `PASS` dieses Werkzeugs bedeutet ausschließlich **Identitätskonsistenz**. Weder Release-Build-PASS noch Installierbarkeit, Hardware-Sicherheit, physische Battery-Care-Wirksamkeit oder Produktivabnahme werden daraus abgeleitet. Alle regulären Gates aus `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md` bleiben zusätzlich verpflichtend. Das Werkzeug erzeugt **keine** Ausgabe- oder Datendatei, ändert keine Konfiguration und sendet keine Kommandos.

## Keine verdeckte Freigabe

- `BATTERY_CARE_ENABLED` bleibt standardmäßig `false`.
- Der produktive Raspberry Pi wird in CP27 nicht berührt.
- Keine Releaseversion oder Installationsanleitung als final ausgeben, solange Manifest-/Source-/Dokument-/Installer- und Wiederherstellungsgates fehlen.
- Das Master-Ledger bleibt unter `05_ZEC_BACKLOG_AND_ROADMAP.md` die einzige Roadmapautorität. Der releasegebundene Snapshot ist erst zum Source-Freeze zu erstellen.
