**V18.0.0 Field-Install-Kandidat – reale Batterie-/Rollback-Wirkung PENDING.** Technische Architektur entspricht dem CP42-Battery-Care-Code; Installer und Releaseunterlagen für diesen Build ergänzt.

# ZEC V18.0.0 – sourcebasiertes Battery-Care-As-built (Entwicklungsentwurf)

> **DEVELOPMENT_NOT_INSTALLABLE** · **MANUAL_UML_REVIEW_PENDING** · **PHYSICAL_EFFECT_NOT_VERIFIED**  
> Planungs-/Entwicklungsquellen für V18.0.0, keine freigegebenen Produktunterlagen, kein Feld-PASS.

**Produktiver Iststand:** V17.1.3 / `v17.1.3-20261022`. **Geplante Zielversion:** V18.0.0 / `v18.0.0-20261027` (Build-ID nur vorläufig). Die tatsächliche Runtime-Kennung und der freigegebene Standardinstaller tragen weiterhin V17.1.3. Dieses Dokument beschreibt den verifizierbaren *Entwicklungs-Sourcecode*, nicht bereits ein ausgeliefertes V18-Produkt.

## Regler- und Hardwarevertrag

- Die bereits vorhandene S3-/AUTO-/NIGHT-Steuerung, `MIN_SOC`, SMA-Speedwire/OBIS, Shelly-kompatibler HTTP-Messpfad, Cross-Charge-Arbitration, Command-Readback, Fast Capture und Fehler-/Stale-Schutz bleiben die vorhandene Reglerbasis. Keine neue Battery-Care-Command-Owner-Instanz.
- `battery_care_policy.py` implementiert `CareConfig`/`CareObservation`/`CareEpisode`/`CareDecision`, saisonale Entscheidung und Stufen. Die Einstellungen bleiben standardmäßig **OFF**, und unvollständige/ungültige Aktivierung scheitert geschlossen. Ausgewertet werden `R` (Reserve), `N` (Netzpflegetrigger) und `E` (Notladetrigger) mit `E < N < R` und konfigurierter Hysterese.
- `controller_logic.py` erzwingt die Entlade-Untergrenze in AUTO/NIGHT, verwaltet PV- und Netz-/Notladeanforderungen und führt alle Befehle über den bestehenden zentralen `_publish_signed_target`-Pfad und Safety-Arbitration. PV-Shadow-Entscheidungen und versendete Ladeanforderungen sind **keine** physikalische Ladebestätigung.
- `battery_care_pv_allocation.py` berechnet absolute PV-Zielwerte aus getrennt frischen Messwerten; die rechnerische Summe `Pp + Pz - G` ist lediglich ein Schätzwert und beweist keine unabhängige PV-Produktion. `battery_care_grid_observation.py` verwendet Grid-/Zendure-/Primärspeicherfrische, wo diese tatsächlich verfügbar und unterstützt ist; Stufe 3 kann die ökonomische Cross-Charge-Sperre umgehen, nicht jedoch Device-, Safety- oder Command-Gates.
- `battery_care_episode_store.py` persistiert nur die Episodenabsicht und die beim Start geltende Zielreserve; keine alten Publish-Ziele oder alte Bestätigungsproben werden beim Restart übernommen. Defekte SQLite-Persistenz darf keine ungesicherte zusätzliche Grid-Care-Kommandofreigabe erzeugen. STOP/Care-Off beendet laufende Care-Commandabsichten.
- `operational_events.py` dokumentiert bestätigte Notlade-Command-Effect-Fehler dauerhaft und getrennt je Failure-ID mit ursprünglichem Schutzreserve-Bezug; echte frische und unterscheidbare SOC-Beobachtungen sind für Recovery erforderlich. CP19-Write-through reduziert das normale Journalintervall, ersetzt nicht physische Wirksamkeitsnachweise.

## Status, Diagnose und Graph

- `status_page_v2.py` und `static/status_v2.js` kennzeichnen **angefordert** statt **wirksam**; mehrere offene Notladevorfälle bleiben getrennt in der Ereignisliste.
- `battery_care_graph_history.py` und `web_ui.py` zeigen historische AUTO- und NIGHT-Grenzen ausschließlich dort, wo Konfiguration, Betriebsmodus und Messabschnitt historisch nachweisbar sind. Alte unbekannte Daten bleiben unbekannt. Die Care-Details zeigen N-/E-Konfiguration und persistierte Ereignismarker.
- `battery_care_stage_events.py` akzeptiert nur zwei verschiedene abgeschlossene Reglerzyklen als Stufenwechsel; reine ACKs, PV-Shadow-Kandidaten und Wiederholungen derselben Snapshot-ID reichen nicht. Marker belegen **Reglerprovenienz**, keine physische Wirkung.

## Topologien, Voraussetzungen und Grenzen

Unterstützte Hardwarepfade und Softwarevoraussetzungen sind **vor Release-Freeze** aus realen Settings-, Geräteprofil-, Messpfad- und Feldtests erneut zu inventarisieren; kein neues Topologiesupportversprechen entsteht durch diesen Entwurf. Bestehende Messpfade **SMA-Speedwire/UDP** und **Shelly-kompatibles HTTP** dürfen aus dem finalen Datenblatt nicht verschwinden. Primärspeicher-Untergrenzen werden nur verwendet, wenn vom konkreten angebundenen Pfad tatsächlich unterstützt und frisch.

## Source-Traceability und Freigabe

Die Datei `docs/releases/v18.0.0/CP29_SOURCE_TRACEABILITY_20261027.json` inventarisiert die tatsächlichen SHA256 der relevanten Entwicklungsdateien. Jede spätere Änderung invalidiert diesen Entwurf bis zum erneuten Audit. Frühere V17.1.3-As-built-Unterlagen bleiben historische, unveränderte Releaseprovenienz.

**Erforderlich vor Release:** finale V18-Laufzeitidentität, Source-Manifest, validierte `ZEC_BUILD_EVIDENCE_V1`, DOCX und daraus gerendertes PDF mit Source-/Hardware-Nachweis, vollständige 22-UML-Fachreview, Versions-/Fresh-Extract-/Rollback-/Installer-Gates, reale Hardware- und Battery-Care-Wirksamkeitsabnahme. Kein installierbares V18-ZIP aus diesem Dokument ableiten.
