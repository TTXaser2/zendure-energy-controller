# ZEC V16.2.3 – Technical Notes

## Root Cause des V16.2.2-Preflight-Fails

Die ausgelieferten Dateien `validation/V16_2_2_FULL_TEST.txt` und `validation/V16_2_2_RESOURCEWARNING_TEST.txt` enthielten die vollständige grüne QA in human-readable Form (`Result: PASS`, Test-/Subtestzahlen und `Mode: pytest -W error::ResourceWarning`). Der Installer verlangte dagegen andere, nie erzeugte Freitextmarker (`RELEASE:`, `STATUS:`, `RESOURCEWARNING:`). Dadurch wurde eine korrekte Build-Evidenz fälschlich als unvollständig bewertet.

Der Fehler trat im mutationsfreien Preflight auf. Die reale produktive Installation blieb V16.2.0; `rollback_result=not_required_preflight`.

## V16.2.3 Build-Evidence-Vertrag

`tools/deployment_contract.py` definiert `ZEC_BUILD_EVIDENCE_V1` als einzige maschinenlesbare Installer-Autorität. Der Verifier prüft Releaseversion, Label, Build-ID, globalen PASS-Status, positive Testdateianzahl, vollständigen Testlauf, identischen ResourceWarning-Lauf und explizit `error::ResourceWarning`.

Der Installer ruft ausschließlich `verify-build-evidence` auf. Human-readable QA-Dateien bleiben Releaseevidenz für Menschen, sind aber kein Parservertrag mehr.

## No-Regression

V16.2.2-Manifest-/Release-Hygiene und einmalige Fehlerfinalisierung bleiben unverändert enthalten. Der Speicherstatuskarten-Stand aus V16.2.1 bleibt ebenfalls unverändert. `controller_logic.py` bleibt byteidentisch.
