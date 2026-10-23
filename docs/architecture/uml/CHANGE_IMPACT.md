# UML Change-Impact – Abgleich V17.1.3 – Source- und Visualreview abgeschlossen

**Reviewstatus:** technische Zuordnung / visuelle und fachliche Source-Endabnahme PASS; releasebezogene QA folgt. Altdiagramme gegen V17.0.2, neuer Sourcebezug V17.1.3.

| ID | Status | Prüfthema und Entscheidung | Fachreview |
|---|---|---|---|
| 01 | UPDATED | S3 ist kein eigener current_mode; Grid-Stale ist Ereignis. | `SOURCE_REVIEW_PASS` |
| 02 | UPDATED | NIGHT/MIN_SOC entkoppelt fixe Entladung von zulässiger Grid-Verarbeitung. | `SOURCE_REVIEW_PASS` |
| 03 | UPDATED | S3-Saisonwirkung gilt nur bei opt-in und ist nachrangig zum Export-Capture-Floor. | `SOURCE_REVIEW_PASS` |
| 04 | UPDATED | Profil/Bestätigungsdauer sind konfigurierbare S3-Werte. | `SOURCE_REVIEW_PASS` |
| 05 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 06 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 07 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 08 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 09 | UPDATED | Getrennte 1-s-Live- und 3-s-Minigraph-Polls; Stale-Diagnose. | `SOURCE_REVIEW_PASS` |
| 10 | UPDATED | MIN_SOC blockiert Entladung, nicht die gesamte Netzverarbeitung. | `SOURCE_REVIEW_PASS` |
| 11 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 12 | REVIEWED_UNCHANGED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 13 | UPDATED | Zeitprofil-Confirm ist konfigurierbar. | `SOURCE_REVIEW_PASS` |
| 14 | UPDATED | Saisonpolicy kann strategischen Share unterdrücken. | `SOURCE_REVIEW_PASS` |
| 15 | UPDATED | S3 nur Strategieebene, kein Safety-/Command-Override. | `SOURCE_REVIEW_PASS` |
| 16 | UPDATED | Runtimekonfigurierbare Zeitgrenzen anstelle der fixen Altuhrzeiten. | `SOURCE_REVIEW_PASS` |
| 17 | UPDATED | V17.1.3 Sourceconsumer weiterhin unter Schutzinvarianten; keine zusätzliche UML-Änderung abgeleitet. | `SOURCE_REVIEW_PASS` |
| 18 | UPDATED | S3 requested/effective und applicability als eigene Diagnosedimension. | `SOURCE_REVIEW_PASS` |
| 19 | UPDATED | S3 opt-in und konfigurierbare Tagesprofile ersetzen hardcoded-only-Altmodell. | `SOURCE_REVIEW_PASS` |
| 20 | NEW | Opt-in/Saisonpolicy gegenüber V0.4 erforderlich. | `SOURCE_REVIEW_PASS` |
| 21 | NEW | Sourcepoll vs. Regler- und Minigraph-Takt unterscheidbar. | `SOURCE_REVIEW_PASS` |
| 22 | NEW | Stale-Ereignis-Debounce und Controllerunabhängigkeit. | `SOURCE_REVIEW_PASS` |
