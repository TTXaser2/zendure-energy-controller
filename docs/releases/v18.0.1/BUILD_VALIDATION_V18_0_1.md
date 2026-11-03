# V18.0.1 Build-/Release-Gates (ENTWURF)

`RELEASE_HOLD / DEVELOPMENT_NOT_INSTALLABLE` bis zur tatsächlich abgeschlossenen full+ResourceWarning=strict Regression, finaler Manifestprüfung, versioniertem Datenblatt DOCX/PDF mit Render-/Inhaltsprüfung, 22 UML-Blättern mit manueller Quellen-/Bildprüfung, Installer-/Rollback-/Fresh-Extract-Gates, Source-Checkpoint-Bibliotheksrücklese sowie ausdrücklicher Freigabe.

Keine V18.0.0-QA als V18.0.1-PASS übernehmen.

## CP15 vorbereiteter Dual-Status-Verifikationsvertrag

Der neue V18.0.1-Test prüft entweder das nicht installierbare `RELEASE_HOLD`-Staging bei `ZEC_BUILD_EVIDENCE_V1=BLOCKED` oder den vollständig releaseten Installer bei validem `status=PASS`. Ein Zustand mit freiem Installer und BLOCKED-Build-Evidenz muss FAIL ergeben. Die finale Build-Evidenz wird erst aus realen finalbaumbezogenen beiden Läufen fortgeschrieben; kein Vorab-PASS aus CP14.

## CP16 – vorbereiteter versionsgenauer technischer Paketfreeze

Das Source-Manifest und `ZEC_BUILD_EVIDENCE_V1` werden nach dem Nachweis beider CP14-Regressionsvarianten in einer neuen finalisierungsfähigen Quellkopie erstellt. **Pflicht:** Beide Varianten auf den exakten CP16-Quellen erneut ausführen und danach frisch extrahiertes finales ZIP separat verifizieren. Ein QA-Bericht aus CP14 allein ist keine Freigabe der geänderten CP16-Bytes.
