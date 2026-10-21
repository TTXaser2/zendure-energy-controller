# ZEC V14.1.1

## Zweck

Patchrelease für den im ersten V14.1.0-Feldinstallationsversuch gefundenen Installer-Pfadkontextfehler.

## Feldbefund

Der V14.1.0-Preflight las die produktive `/opt/zendure-controller/config.json`, führte die Graph-V3-Verifikation jedoch aus dem entpackten Paketverzeichnis aus. Bei relativer `MEASUREMENT_LOG_DIR=logs` wurde deshalb fälschlich eine DB unter `/home/pi/Downloads/.../logs/zec_measurements.sqlite3` gesucht und `NOT_V3` gemeldet. Die produktive V14.0.0/V3-DB blieb unverändert und gesund.

## Korrektur

- `v14_cutover.py verify/preflight` besitzen einen expliziten `--runtime-root`.
- Installer und automatische Installationsdiagnose pinnen die Prüfung auf `/opt/zendure-controller`.
- Die V3-Verifikation öffnet die bestehende Datenbank ausschließlich read-only; sie führt keine Schema-/WAL-Initialisierung aus.
- Regressionstest reproduziert den exakten Staging-CWD-Fehler und verifiziert die Korrektur.
- Keine Änderung an Controller-, Command-, Safety- oder Hardwaresemantik.

## Upgradebasis

Unterstützte produktive Quelle für diese Installation: V14.0.0 / `v14.0.0-20260904-r2`.
