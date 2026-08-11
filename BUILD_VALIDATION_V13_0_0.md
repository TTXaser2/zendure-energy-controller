# Build Validation – Zendure Energy Controller V13.0.0

## Identität

```text
APP_VERSION       = 13.0.0
APP_VERSION_LABEL = V13.0.0
APP_BUILD_ID      = v13.0.0-20260811
```

Verifizierte Buildbasis:

```text
zendure_controller_v12_13_0.zip
SHA256 e204aa270c517d2e9b1abfc8816075ca75c3194c7b0cf39f1b5b186f7c07213f
V12.13.0 source manifest 368 / 368 PASS
```

## Pre-Package-Teststand

```text
pytest collection               775
pytest                           775 / 775 PASS
pytest subtests                  681 / 681 PASS
unittest ResourceWarning=error   775 / 775 PASS
ResourceWarnings                0
Python AST                      165 PASS
python -m py_compile            165 PASS
JavaScript / node --check         2 / 2 PASS
Shell / bash -n                   8 / 8 PASS
Restart-Helper / bash -n          1 / 1 PASS
JSON                              6 / 6 PASS
V13 HTTP route smokes             4 / 4 PASS
```

Neue V13-spezifische Regressionen:

```text
Atomic commit / backfill           4 PASS
Config states / import / export   14 PASS + 4 subtests
HTTP route integration             4 PASS
Graph config timeline              5 PASS
```

## Registry-/Bundle-Vertrag

```text
Settings gesamt                   212
Verwaltete LIVE/RESTART-Settings 191
portable_profile                   55
site_specific                      60
local_runtime                      68
non_transferable                    7
secret                               1
Registry-Schema             1.24-v13.0
Registry-Contract SHA256
c1e13a7a1fd2968545bcf49073dc7b1d9e9dd7c71e0d002a45f50610d0780440
```

Die Abweichung von der frühen Spezifikationszählung 188→191 ist eine gegen die reale V12.13.0-Registry nachgewiesene Bestandskorrektur. Alle 191 verwalteten Settings sind in V13.0.0 explizit einer Portabilitätsklasse zugeordnet.

`ZEC-CONFIG-BUNDLE` V1 ist strikt geparst, größenbegrenzt, duplicate-key-sicher, Registry-/Schema-kompatibilitätsgebunden und mit kanonischem Payload-SHA-256 versehen. Der Hash ist Integritäts-, nicht Authentizitätsnachweis.

## Secret-/Import-/Commit-Vertrag

- benannte Stände und teilbare Regelprofile enthalten keinen Secret-Klartext;
- Standardimport verwendet `keep`; `replace`/`clear` sind explizite Expert-Operationen;
- `clear` erfordert eine zusätzliche Commit-Bestätigung;
- Preview-/Diff-/Auditdaten geben Secret-Klartext nicht zurück;
- Importtoken sind TTL-begrenzt und an die CSRF-/Browsersession gebunden;
- State-Revision und Primärconfig-CAS werden beim Commit erneut geprüft;
- atomischer Config-Write wird exakt reread-verifiziert;
- Post-Write-Mismatch restauriert die zuvor gelesenen Originalbytes atomisch;
- scheitert auch die Rollback-Verifikation, geht der Configzustand fail closed.

## Last-Good-/Recovery-No-Regression

Named States und Importartefakte sind niemals Last-Good-Recoverykandidaten. Ein erfolgreicher Import/Load promoviert Last-Good nicht direkt. Der bestehende Stable-Ready-/Eligibility-Vertrag bleibt unverändert maßgeblich.

## Historischer SOC-Graph

- Tagespunkte bleiben cachebar;
- Config-Overlays werden über eine separate `graph_config_timeline` zeitbezogen aufgelöst;
- Quelle sind vorhandener Measurement-V4-`config_control_hash` und `zec_config_snapshots.json`;
- Configwechsel innerhalb eines Tages erzeugen segmentierte Overlays;
- historische Tage verwenden niemals die aktuelle Config als Fallback;
- fehlende historische Snapshots werden transparent als unbekannt markiert;
- der einmalige V4-Backfill ist idempotent und disk-/streamingbasiert;
- Backfillfehler sind nichtfatal für einen ansonsten gesunden V13-Installations-/Ready-Zustand;
- zukünftige Timeline-Pflege erfolgt asynchron und nur bei Hashwechsel.

## V4-Contract-No-Regression

```text
Standard fields: 246
Standard header SHA256: 7842bfef39d47f93dc39689aa04da7658564af565e5051c24f90b32021d184a7
Extended fields: 249
Extended header SHA256: 8f61d07e66428a6e8757333d35d5dd73dd3a0975ac9a16714b93dc9b86460e93
```

`measurement_v4.py`, `measurement_v4_contract.py` und `csv_logger.py` sind byteidentisch zu V12.13.0. Historische V3-Dateien bleiben ausschließlich offline/read-only; kein V3-Runtimepfad wurde wieder eingeführt.

## Protected-Core-No-Regression

Byteidentisch zu V12.13.0 sind insbesondere:

```text
controller_logic.py
cross_charge.py
command_lifecycle.py
instance_owner.py
measurement_v4.py
measurement_v4_contract.py
csv_logger.py
state.py
mqtt_bridge.py
zendure_power_observation.py
```

Die Hashwerte sind in `V13_0_0_TARGETED_PROTECTED_DIFF.md` dokumentiert.

## UI-/Integration-Smoke

Die neuen Config-State-/Export-/Profil-/Importpfade wurden über die echte `create_app()`-Routenintegration mit CSRF-/Sessionvertrag getestet. `settings_v2.js` und `status_v2.js` bestehen `node --check`.

Ein Chromium-Struktur-Smoke mit serverseitig erzeugtem HTML und ausgeliefertem CSS wurde bei 1440×900 und 390×844 für Status und Settings ausgeführt: kein horizontaler Overflow und keine Browser-Console-/Page-Errors. Die Buildumgebung blockiert direkte Chromium-Navigation zu localhost mit `ERR_BLOCKED_BY_ADMINISTRATOR`; deshalb wird ausdrücklich **kein vollständiger Live-Navigation-/Pixel-Fidelity-PASS** behauptet. Die FastAPI-Routen selbst sind separat integriert getestet.

## Handbuch

Das Benutzerhandbuch wurde auf V13.0.0 erweitert. DOCX und PDF besitzen **20 Seiten**; alle 20 gerenderten Seiten wurden visuell auf Überlagerungen, abgeschnittene Inhalte und Versionsreste geprüft. Der früh entdeckte V12.13-Footerrest wurde vor der finalen Prüfung korrigiert.

## Installer

Der Updater akzeptiert ausschließlich die verifizierte Quelle:

```text
12.13.0 / v12.13.0-20260811
```

und installiert ausschließlich:

```text
13.0.0 / v13.0.0-20260811
```

V12.12.x-/RC-Quellen werden nicht als V13-Upgradebasis akzeptiert. Config, Last-Good, Messdaten, Config-Snapshots, Operational Events und `config-states/` werden gesichert/erhalten. Der historische Graph-Backfill läuft nach erfolgreicher Runtime-Abnahme und ist bei Fehler nicht rollback-auslösend.

## Final-ZIP-Gate

Alle wesentlichen Gates werden nach Packaging aus einer frischen Extraktion des finalen ZIP erneut ausgeführt. Der Release ist erst nach diesem zweiten Durchlauf final freigegeben.

## Paket-Scope gegenüber V12.13.0

```text
NEW                 18
CHANGED             37
DELETED              0
Source manifest     386 / 386
```

Die vollständige Dateiliste steht in `V12_13_0_TO_V13_0_0_CHANGED_FILES.txt`.
