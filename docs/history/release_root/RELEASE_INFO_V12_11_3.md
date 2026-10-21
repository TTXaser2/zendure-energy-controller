# Release-Informationen – Zendure Energy Controller V12.11.3

**Version:** `12.11.3`  
**Build-ID:** `v12.11.3-20260806`

## Zweck

Bugfix für den Installations-Abnahmevertrag. V12.11.2 Fix 6 wurde nach technisch erfolgreichem Start zurückgerollt, wenn `/ready` innerhalb von 90 Sekunden ausschließlich wegen eines dynamischen INPUT_LIMIT-/OUTPUT_LIMIT-Readback-Versatzes oder eines ungefährlichen Command-Beobachtungszustands noch nicht global grün war.

## Neue Abnahme

`ready=true` bleibt der bevorzugte vollständige Nachweis. Alternativ darf der Installer einen stabilen sicheren Übergangszustand akzeptieren, wenn alle kritischen Daten-, Controller-, Command-Path- und statischen Command-State-Prüfungen gesund sind und ausschließlich ein Limit-Readback beziehungsweise ein ungefährlicher Beobachtungszustand offen ist.

Harte Rollbackgründe bleiben insbesondere SAFE_STATE, Controllerfehler, fehlende/stale Pflichtdaten, unvollständiger Command-State, SmartMode-/AC-Mode-/Gegenlimit-Invariante, bestätigte Nichtwirkung, Late-Effect-Guard oder andere fehlgeschlagene Pflichtchecks.

Der Regleralgorithmus und die Fix-6-UI-/Event-/Storage-Änderungen sind unverändert.
