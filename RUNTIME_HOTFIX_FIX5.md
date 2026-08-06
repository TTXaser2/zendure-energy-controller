# RC20 Runtime-Hotfix Fix 5

**Build-ID:** `rc20-audit-fix5-20260806`

## Anlass

Beim ersten vollständig durchlaufenen RC19→RC20-Installationsversuch startete der
Controller, aber `/ready` lieferte einen HTTP-500-Fehler. `ControllerState.readiness_snapshot()`
las das nicht existierende Attribut `second_battery_valid`, obwohl das kanonische
State-Feld seit RC10 `second_battery_data_valid` heißt. Der Installer wartete deshalb
90 Sekunden und führte anschließend den vollständigen Rollback auf RC19 aus.

## Korrektur

- `readiness_snapshot()` verwendet nun ausschließlich `second_battery_data_valid`.
- Ein AST-Vertrag prüft, dass jede `self.<attribut>`-Lesung der gesamten
  `ControllerState`-Klasse entweder ein deklariertes Dataclass-Feld oder eine
  Klassenmethode ist.
- Ein Laufzeit-Smoke-Test erzeugt einen unveränderten `ControllerState`, ruft
  `readiness_snapshot()`, `build_health_payload()` und `build_ready_payload()` auf
  und prüft die vollständige strukturierte Antwort.
- Derselbe Smoke-Test läuft im Installer vor dem Stoppen der Dienste und erneut
  im finalen Installationsverzeichnis.
- Auch der zweite Testlauf im Installationsverzeichnis läuft mit
  `ZEC_INSTALLER_PREFLIGHT=1` und `ResourceWarning` als Fehler.

## Nicht verändert

AUTO-, NIGHT-, Harvest-, Cross-Charge-, Command-, MQTT- und Measurement-Regellogik
wurden nicht verändert. Der Fix betrifft ausschließlich die Readiness-Diagnose und
deren Installationsprüfung.
