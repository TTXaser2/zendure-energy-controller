# ZEC V14.0.0 – Release Information

**Release:** V14.0.0  
**Build-ID:** `v14.0.0-20260904-r2`  

> Build R2 replaces the pre-install candidate `v14.0.0-20260904`. The first candidate aborted safely before service stop on the real Pi because the installer incorrectly re-ran build tests whose modules import the optional development dependency `pytest`. R2 removes test-framework execution from the productive installer. Build/Fresh-ZIP test evidence remains manifest-protected; the Pi preflight uses only production dependencies, standard-library/runtime smokes, config/cutover preflight and source-manifest verification.
**Basis:** V13.0.3 / `v13.0.3-20260814`  
**Typ:** Major Feature / Graph-History-Plattform + produktiver Cutover

## Umfang

V14.0.0 führt den in WP1–WP9 aufgebauten historischen V3-Unterbau produktiv zusammen:

- Graph Core V3 Live Writer und Query/Catalog;
- Entity-/Topology-Persistenz;
- Coverage/Evidence/Retention-Grundlagen;
- konsolidierte bestehende History-Pfade;
- Guided/Free Graph Workspace;
- Cursor-Inspector und Command-Follow;
- Episodenvergleich Side-by-Side / Overlay;
- produktiven V4→V3-Rebuild/Cutover mit atomarer Aktivierung;
- getrennte Graph-History-/Controller-Readiness;
- automatisches Diagnosepaket bei Installationsfehlern;
- read-only Feldabnahmewerkzeug.

## Datenmigration

V14 übernimmt keine Engineering-V3-Datenbank. Der produktive Graphstore wird aus dem vorhandenen Measurement-V4-Bestand in einer separaten Kandidaten-DB neu erstellt, vollständig validiert und erst danach atomar aktiviert.

Die alte DB einschließlich WAL/SHM wird separat gesichert. Backup und Restore werden über Größe und SHA256 verifiziert. Beschädigte Restorequellen werden vor jeder Umschaltung abgewiesen.

## No-Regression

Keine fachliche Änderung an Live-Regelalgorithmus, AUTO/Harvest/Cross-Charge/NIGHT, Primärspeicherpriorität, Command Lifecycle/Effect/Readback/Resync, Safety oder Hardwareschonung.

Measurement V4 bleibt 246 Standard / 249 Extended.

## Bewusst nicht Bestandteil

- keine eigenmächtig gewählte produktive Retentiondauer;
- kein Retention-Scheduler;
- keine automatische VACUUM-Policy.

## Installation

Der Installer akzeptiert ausschließlich V13.0.3 / `v13.0.3-20260814` als direkten Ausgangsstand. Details und Feldabnahme: `README_INSTALLATION.md`.

Build-PASS ist nicht Produktiv-PASS. Die reale Installation und Feldabnahme auf dem Pi bleiben ein separates Release-Gate.
