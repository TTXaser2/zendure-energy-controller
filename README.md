# Zendure Energy Controller V14.0.0

**Build-ID:** `v14.0.0-20260904-r2`

V14.0.0 ist der produktive Integrationsrelease des in WP1–WP9 aufgebauten Graph-/History-Unterbaus. Ausgangsbasis ist ausschließlich der verifizierte Produktivstand V13.0.3 / `v13.0.3-20260814`.

## 1. Hauptumfang

- Graph Core V3 als kompakte permanente historische Basis.
- V3 Query/Catalog, Entity-/Topology-Persistenz, Coverage/Evidence und Retention-Grundlagen.
- Konsolidierte bestehende History-Pfade einschließlich historisch korrekter MAX-SOC-Verläufe.
- Neuer Graph Workspace mit Guided-/Free-Modus.
- Cursor-Inspector und Command-Follow / Cause-Effect mit expliziter `NOT_EVALUABLE`-Semantik.
- Episodenvergleich Side-by-Side / Overlay mit persistierten Triggern und relativer `t=0`-Achse.
- Produktiver V14-Cutover als Rebuild aus Measurement V4 in eine separate V3-Kandidaten-DB.
- Atomarer Graphstore-Swap erst nach vollständiger Validierung.
- Separates rollbackfähiges DB/WAL/SHM-Backup mit Größen-/SHA256-Verifikation.
- Automatische Diagnosepakete bei Preflight- und Updatefehlern.
- Read-only V14-Feldabnahmewerkzeug.

## 2. Bewusst unverändert

V14.0.0 ändert nicht die fachliche Regler-, Command-, Safety- oder Hardware-Semantik. Insbesondere bleiben AUTO/Harvest/Cross-Charge/NIGHT, aktive Neutralisierung, Command-Effect/Readback/Resync und die Primärspeicherpriorität geschützt.

Measurement V4 bleibt unverändert bei 246 Standard- bzw. 249 Extended-Feldern und ist weiterhin die optionale Deep-Trace-/Rebuild-Evidenzschicht. Graph Core V3 und Measurement V4 besitzen getrennte Lifecycles.

## 3. Produktiver Cutover

Der Installer übernimmt keine Engineering-V3-Datenbank als Produktivwahrheit. Stattdessen:

1. Paket-/Source-/Syntax-/Test-Preflight vor Dienststopp.
2. vollständiges Rollback-Backup der V13.0.3-Installation und Root-Artefakte.
3. separates Backup des bestehenden Graphstores einschließlich WAL/SHM.
4. Rebuild von Graph Core V3 aus dem vorhandenen Measurement-V4-Bestand in eine Kandidaten-DB.
5. vollständige V3-Validierung.
6. atomare Aktivierung.
7. lokale Verifikation und Dienststart.
8. getrennte Prüfung von Controller-Readiness und Graph-History-Readiness.
9. automatischer Rollback bei echtem Installationsfehler.

## 4. Graph- und History-Vertrag

- Graph-History-Readiness beeinflusst die Controller-Readiness nicht.
- V3 ist der kanonische produktive History-Unterbau.
- Legacy-Lesewege bleiben nur als ausdrücklich gekennzeichnete Kompatibilität erhalten.
- Measurement V4 darf Graph/Inspector/Evidence anreichern, ist aber keine Voraussetzung für den normalen Graphbetrieb.
- Fehlende historische Entity-/Coverage-/Evidence-Daten werden nicht erfunden oder zwischen Episoden imputiert.
- Publish oder bloß gleichgerichtete Istleistung gelten nicht als Wirkungsnachweis.

## 5. Nicht festgelegt

V14.0.0 führt ausdrücklich keine eigenmächtig gewählte produktive Retentiondauer, keinen Retention-Scheduler und keine automatische VACUUM-Policy ein.

## 6. Installation und Abnahme

Verbindlich:

- `README_INSTALLATION.md`
- `RELEASE_INFO_V14_0_0.md`
- `BUILD_VALIDATION_V14_0_0.md`
- `V14_0_0_SOURCE_MANIFEST.sha256`

Nach erfolgreicher Installation ist die reale Feldabnahme mit `tools/v14_field_acceptance.py` auszuführen. Build-PASS ist nicht Produktiv-PASS.

## 7. Aktuelles Benutzerhandbuch

```text
docs/Zendure_Energy_Controller_Handbuch.pdf
```

Historische Release-, Spezifikations- und Validierungsdokumente bleiben im Paket als Entwicklungs-/Auditspur erhalten.
