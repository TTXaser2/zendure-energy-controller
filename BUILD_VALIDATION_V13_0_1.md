# Build Validation – Zendure Energy Controller V13.0.1

Stand: 11.08.2026

## Releaseidentität

```text
APP_VERSION       = 13.0.1
APP_VERSION_LABEL = V13.0.1
APP_BUILD_ID      = v13.0.1-20260811
```

## Hotfix-Scope

V13.0.1 basiert byte-/funktionsseitig auf V13.0.0 und behebt ausschließlich den fehlerhaften Post-Install-Identity-Vertrag:

- `tools/evaluate_installation_readiness.py` hatte in V13.0.0 weiterhin `12.13.0 / v12.13.0-20260811` hart codiert.
- Dadurch wurde selbst ein bereits `ready=true` laufender V13.0.0-Controller als `REJECT:IDENTITY` behandelt und nach Ablauf der Installations-Abnahme zurückgerollt.
- V13.0.1 liest die erwartete Zielidentität für die Readiness-Abnahme direkt aus der gemeinsam ausgelieferten `version.py`.
- Installer-Zielidentität, Paketidentität und Evaluator-Identität werden durch Regressionstests gegeneinander abgesichert.
- Der Measurement-V4→Graph-Config-Timeline-Backfill bleibt unverändert und läuft weiterhin erst nach erfolgreicher Installations-Abnahme; sein Fehler bleibt nichtfatal für Controller-Readiness.

## No-Regression

Keine fachliche Änderung an:

- AUTO / Harvest
- Cross-Charge
- NIGHT
- Command Lifecycle / Resync
- Single-Owner
- Measurement V4 / 246-249-Feld-Vertrag
- Config States / Import / Export / portable Profile
- Secret-, Migration-, CAS- und Last-Good-Vertrag
- Graphhistorie / Config-Timeline / Backfill-Algorithmus

Die geschützten Produktionsmodule werden gegen V13.0.0 byteidentisch geprüft; Details siehe `V13_0_1_TARGETED_PROTECTED_DIFF.md`.

## Tests

Vollständiger Buildlauf vor Packaging:

```text
unittest + error::ResourceWarning   783 / 783 PASS
pytest                             783 / 783 PASS
pytest subtests                    681 / 681 PASS
```

Zusätzliche V13.0.1-Hotfix-Regressionen prüfen insbesondere:

1. Evaluator-Identität entspricht `version.py`.
2. `13.0.1 / v13.0.1-20260811` + `ready=true` => `READY:FULL_READY`.
3. V13.0.0 bzw. fremde Identität => `REJECT:IDENTITY`.
4. Installer akzeptiert weiterhin nur die produktiv wiederhergestellte V12.13.0-Quellidentität.
5. Backfill liegt weiterhin nach erfolgreicher Readiness-Abnahme.

## Source-/Paketprüfung

Das finale Source-Manifest wird nach Abschluss aller Releaseartefakte neu erzeugt, anschließend vollständig mit `sha256sum -c` geprüft. Das finale ZIP wird danach frisch entpackt und die paketbezogenen Gates werden aus dieser Extraktion wiederholt.
