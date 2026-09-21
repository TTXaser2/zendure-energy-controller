# ZEC V16.2.2

## Zweck

V16.2.2 ist ein Deployment-/Release-Hygiene-Hotfix auf Basis des technisch gebauten V16.2.1. Die reale V16.2.1-Installation auf der produktiven V16.2.0-Basis scheiterte nach Backup/Copy, weil fünf `.pytest_cache`-Dateien im Source-Manifest standen, beim Deployment aber bewusst ausgeschlossen wurden. Der automatische Rollback stellte V16.2.0 vollständig und `ready=true` wieder her. V16.2.2 ersetzt das nicht feldfreigegebene V16.2.1-Paket.

V16.2.2 enthält unverändert auch den in V16.2.1 technisch implementierten Speicherstatuskarten-Bugfix.

## Hotfixumfang

- volatile Releaseartefakte wie `.pytest_cache`, `__pycache__`, Python-Bytecode und Runtime-Datenbanken sind im aktuellen Release-Tree fail-closed unzulässig;
- der aktuelle Source-Manifestvertrag wird durch einen gemeinsamen Python-Verifier geprüft;
- die Manifest-Erzeugung verweigert einen Tree mit verbotenen volatilen Artefakten;
- der Installer prüft die Paket-Hygiene bereits im mutationsfreien Preflight;
- reale `rsync`-Semantik für `SUPPORTED_UPDATE` und `CLEAN_FRESH_INSTALL` wird regressionsgetestet und muss mit dem Manifestvertrag kompatibel bleiben;
- die Installer-Fehlerbehandlung finalisiert Supportcapture und Rollback ausschließlich im Haupt-Shellprozess. Damit kann ein durch `set -E` vererbter `ERR`-Trap aus einem Subshell nicht mehr denselben Fehler ein zweites Mal finalisieren.

## Enthaltener V16.2.1-UI-Fix

- gemeinsamer Standardvertrag für Zendure- und Primärspeicherkarte;
- große signierte Istleistung;
- `Noch ladbar` / `Noch entladbar` in SOC-Prozentpunkten und bei belastbarer Kapazität zusätzlich kWh;
- Laden grün links→rechts, Entladen orange rechts→links;
- Harmonisierung/Harvest im Primärspeicher-Expertenkontext statt dauerhaft in der Standardkarte;
- keine Reglerwirkung aus den UI-/Kapazitäts-/Leistungsanzeigen.

## Schutzgrenze

Keine Änderung an Regelstrategie, Command-, Safety- oder Recoverysemantik. `controller_logic.py` bleibt byteidentisch zu V16.2.0 mit SHA256:

`d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`

## Releaseidentität

- Version: `16.2.2`
- Label: `V16.2.2`
- Build-ID: `v16.2.2-20260921`
- unterstützte reale Updatequelle: `16.2.0 / v16.2.0-20260920`
- Paket: `zendure_controller_v16_2_2.zip`

## Feldstatus

V16.2.1 erhält aufgrund des realen Installer-Fails keinen Real-Field-PASS. V16.2.0 bleibt bis zur erfolgreichen V16.2.2-Update-Feldabnahme die letzte real bestätigte Basis.
