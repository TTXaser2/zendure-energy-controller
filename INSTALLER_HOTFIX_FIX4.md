# RC20 Installer-Hotfix Fix 4

**Build-ID:** `rc20-audit-fix4-20260806`

## Auslöser

Der produktive Raspberry Pi besaß bereits den festen Restart-Helper. Der Test `test_restart_route_fails_closed_when_fixed_helper_is_unavailable` prüfte den Hostzustand statt den benannten Fehlerzweig explizit zu simulieren. Dadurch lief der Erfolgszweig, lieferte ein Python-`dict` und startete einen verzögerten Helper-Prozess. Das führte gleichzeitig zum Assertionfehler und zur `ResourceWarning`.

## Korrektur

- Der Test mockt den fehlenden Helper explizit und ist hostunabhängig.
- Installer-Selbsttests setzen `ZEC_INSTALLER_PREFLIGHT=1`.
- `trigger_service_restart()` startet unter diesem Guard niemals einen Subprozess.
- Eventjournal-Dateien des Preflights werden unter `/tmp/zec-installer-preflight-<PID>/` isoliert.
- `ResourceWarning` wird im Installer-Testlauf als Fehler behandelt.
- `logs/`, SQLite-Dateien, Caches und Bytecode werden nicht paketiert.

## Verifikation

```text
unittest:          621 bestanden
pytest:            621 bestanden
pytest-Subtests:   677 bestanden
ResourceWarnings:    0
```
