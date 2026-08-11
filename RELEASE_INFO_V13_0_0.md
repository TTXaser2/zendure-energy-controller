# Release Info – Zendure Energy Controller V13.0.0

**Version:** `13.0.0`  
**Label:** `V13.0.0`  
**Build-ID:** `v13.0.0-20260811`

## Zweck

V13.0.0 ist der neue Entwicklungsblock **Konfigurationsstände / Import / Export** auf der produktiv und feldvalidierten Basis V12.13.0. Zusätzlich behebt der Release die nach V12.13.0 bestätigte Fehlerklasse, bei der gecachte SOC-Tagesgraphen aktuelle bzw. historische SOC-/Nacht-Overlays nicht korrekt zur damals wirksamen Konfiguration zuordnen konnten.

## Muss-Scope

1. benannte lokale Konfigurationsstände mit Name, Beschreibung, Quelle, Scope, Registry-/Schema-Metadaten und Integrität;
2. gemeinsamer Bundle-Vertrag `ZEC-CONFIG-BUNDLE` für Stand, Export, Import und teilbare Regelprofile;
3. Registry-basierte Scopeauswahl und explizite Portabilitätsklassifikation aller verwalteten Settings;
4. secretsicherer Standardexport sowie explizite Expert-Semantik für Secret-Export und Importoperationen `keep/replace/clear`;
5. Import ausschließlich über Kompatibilitätsprüfung, gemeinsame Migration, vollständige Servervalidierung, Diff, Bestätigung, CAS und atomischen Commit;
6. gehärteter Commit mit exakter Post-Write-Verifikation und atomischem Byte-Rollback bei Verifikationsfehler;
7. Last-Good-/Recovery-Vertrag unverändert getrennt von benannten Ständen und Importartefakten;
8. korrekte `configured`-/`effective`-/`pending_restart`-Semantik nach Stand-/Import-Commit;
9. transportables **Teilbares Regelprofil**, das ausschließlich explizit `portable_profile` klassifizierte Settings enthält;
10. historische SOC-Graph-Overlays aus `config_control_hash` und bestehenden V4-Config-Snapshots;
11. einmaliger idempotenter V4→Graph-Config-Timeline-Backfill beim Upgrade sowie danach inkrementelle Runtime-Pflege;
12. keine falsche Rückprojektion aktueller Config auf historische Tage; fehlende historische Config wird als unbekannt ausgewiesen.

## Quellkorrektur gegenüber der freigegebenen Spezifikation

Die tatsächliche V12.13.0-Registry enthält **191** aktive editierbare LIVE/RESTART-Settings, nicht 188. Die drei in der frühen Spezifikationszählung nicht erfassten, bereits in V12.13.0 vorhandenen Settings sind:

- `MEASUREMENT_LOG_RETENTION_MAX_AGE_DAYS`
- `MEASUREMENT_LOG_RETENTION_MAX_TOTAL_BYTES`
- `MEASUREMENT_LOG_RETENTION_PROTECT_HOURS`

V13.0.0 klassifiziert deshalb **191/191** verwaltete Settings explizit. Dies ist eine Korrektur der Bestandszählung, keine Erweiterung des freigegebenen Funktionsscopes.

## Registry-/Portabilitätsvertrag

```text
Settings gesamt        212
Verwaltete Settings    191
portable_profile        55
site_specific           60
local_runtime           68
non_transferable         7
secret                    1
Registry-Schema         1.24-v13.0
Registry-Contract SHA256
c1e13a7a1fd2968545bcf49073dc7b1d9e9dd7c71e0d002a45f50610d0780440
```

`MQTT_PASSWORD` bleibt das einzige Secret. Ein teilbares Regelprofil enthält keine Secrets, keine lokalen Runtimewerte und keine installations-/standortspezifischen Settings.

## Historischer Graphvertrag

Measurement V4 selbst bleibt unverändert. Die vorhandene Kombination aus `measurement_epoch_ms`, `config_control_hash` und `zec_config_snapshots.json` wird in eine separate kleine Graph-Config-Zeitachse überführt. Der Tagesdaten-Cache darf weiterhin historische SOC-Punkte cachen; die Konfigurationssegmente werden zeitbezogen aufgelöst. Ein Configwechsel innerhalb eines Tages erzeugt segmentierte Overlays.

Wenn ein historischer Hash nicht gegen einen Config-Snapshot auflösbar ist, zeigt ZEC für diesen Zeitraum keine erfundene Grenzlinie, sondern kennzeichnet die historische Konfiguration als nicht verfügbar.

## No-Regression

Nicht Gegenstand von V13.0.0 sind Änderungen an:

- AUTO-Regelalgorithmus;
- Harvest-Zielwertbildung;
- Cross-Charge-Regelalgorithmus;
- NIGHT-Regelalgorithmus;
- Command Lifecycle/Resync;
- Single-Owner-Steuerung;
- Measurement-V4-CSV-Contract.

Produktiv bleibt ausschließlich `ZEC-MEASUREMENT-V4`:

```text
Standard: 246 Felder
Extended: 249 Felder
```

Historische V3-Dateien bleiben offline/read-only; V13.0.0 führt keinen V3-Runtimepfad wieder ein.

## Abgrenzung

Der SHA-256 im Bundle ist ein Integritätsnachweis, kein Authentizitäts- oder Supply-Chain-Nachweis. V13.0.0 führt keine zusätzliche Installed-Tree-/Supply-Chain-Provenance ein.
