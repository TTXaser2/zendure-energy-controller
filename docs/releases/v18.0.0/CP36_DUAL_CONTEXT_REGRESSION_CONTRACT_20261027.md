# CP36 – Historische V17-Regression und echte V18-Staging-Regression

**Entwicklungsstand 27.10.2026 · `DEVELOPMENT_NOT_INSTALLABLE` · ohne Produktfreigabe**

## Ausgangsfehler und vollständige Ermittlung

Das CP35-Gate erkannte zunächst drei kontradiktorische V17.1.3-spezifische Testfixtures. Nachdem die drei korrigiert waren, führte die tatsächliche V18-Staging-Suite 1.167 Tests aus und meldete weitere 37 fehlgeschlagene Release-/Installer-/Quellenprovenienztests. Die finale CP36-Korrektur verallgemeinert daher den Testkontext in den nachgewiesenen Testmethoden und nicht nur die ersten drei Dateien.

## Testvertrag

- Die ursprünglichen V17.1.3-Testkörper wurden **nicht gelöscht oder übersprungen**. Auf dem V17.1.3-Entwicklungsquellbaum werden sie weiterhin mit den ursprünglichen konkreten Assertions ausgeführt.
- Auf dem V18-Stagingbaum verzweigen die 37 nachweislich unzutreffenden Rootversion-/Legacyinstaller-/Entwurfsprovenienz-Testmethoden zu expliziten V18-Aussagen: **Version 18.0.0, vorläufige Build-ID, V17.1.3-Upgradequelle, Hard-Hold/Exit 78, fehlendes Execute-Bit, vorhandene Rollback- und Evidenzhaken, geprüfte Staging-Datenblattbindung und gesperrte Original-Draft-Provenienz**. Die übrigen Testkörper bleiben auf beiden Quellbäumen unverändert.
- Diese V18-Verzweigung ist **eine Testsemantik-Anpassung, kein Nachweis**, dass alle historischen V17-Installationsspezialfälle mit einem ausführbaren V18-Installer geprüft wurden. Insbesondere wird kein Release oder Rollback freigegeben. Die weitere echte Installer-/Rollback-Abnahme bleibt offen.
- `tools/v18_staging_regression_gate.py` erlaubt die vormals beanstandete V17-Staging-Erzeugung im Testkörper ausschließlich bei belegtem V17-Branch; auf V18 wird ein temporäres gesäubertes Staging-Provenienzabbild geprüft. Flüchtige SQLite-/Log-Testdateien werden ausgeschlossen, das originale Stagingarchiv bleibt unverändert.
- Neue Negativtests erzwingen genau erlaubte V17/V18-Testroots und erkennen gefälschte Versionsidentitäten.

## Echte Build-Evidence bleibt offen

CP36-Regressionslogs können die **Regressionsbereitschaft** des vorläufigen V18-Stagingbaums belegen, **niemals einen produktionsfreigegebenen V18-Build**. Das `validation/V18_0_0_BUILD_EVIDENCE.json` bleibt im Staging auf `BLOCKED` und wird in CP36 nicht zu `PASS` umgeschrieben; Installer-Exit 78, `MANUAL_UML_REVIEW=PENDING`, V18-Datenblatt `ENTWURF`, vollständige Fresh-/Update-/Rollback-Tests sowie unabhängige reale Battery-Care-Wirkung weiter offen.

CP35-Original und sämtliche kanonischen Backlog-IDs bleiben erhalten. Keine Quellenbereinigung; kein aus dem Produktiv-Pi bezogener Wirksamkeitsnachweis.
