# ZEC V12.12.1 – Release Report

## Ergebnis

V12.12.1 **Settings Help & Mobile UX Quality Fix** ist buildseitig freigegeben. Der Release verarbeitet die Feldbefunde von V12.12.0 und lässt die geschützte Regel-/Command-/Measurementlogik unverändert.

## Implementierte Hauptpunkte

1. Konkrete Wirksamkeits-/Risikotexte für 62/62 RICH-Settings.
2. Benutzerfreundliche Terminologie plus Glossar im Handbuch.
3. Help-Modal-Scrollposition wird bei jedem neuen Aufruf zurückgesetzt.
4. Default-/Profil-Semantik strukturiert statt zusammengeklebtem Satz.
5. Suchranking nach Treffergüte; `Totzone`/`Deadband` priorisieren die Netztotzone.
6. Compound-Validation abstrahiert Nacht-Hour/-Minute-Keys vollständig.
7. Status-Info `Controller & Schnittstellen` intern scrollbar; internes Scrollen schließt es nicht.
8. Mobile Statusdarstellung als viewportnahes Info-Panel mit Close-Button.
9. Mobile Settings mit internem Content-Scrollowner; Topbar, Contextbar und Change-Bar bleiben erreichbar.
10. V12.12.1-Handbuch mit 17 Seiten und Glossar.
11. Installer-/Readiness-Identität auf V12.12.1 aktualisiert; V12.12.0 ist regulärer Ausgangsstand.

## Abnahme vor finalem ZIP

```text
unittest / ResourceWarning hard gate   709 / 709 PASS
pytest                                  709 / 709 PASS
pytest subtests                          677 PASS
Chromium Desktop + 3 Mobile Viewports   PASS
Handbuch DOCX/PDF 17 Seiten              PASS
```

## Browser-Limitierung

Kein automatisiertes WebKit-PASS: WebKit war in der Buildumgebung nicht installiert und konnte wegen fehlender Netzwerk-/DNS-Erreichbarkeit nicht nachinstalliert werden. Reale iPhone-Feldabnahme bleibt daher für die konkret gemeldeten iOS-Befunde relevant.

## Scope-Grenze

Nicht verändert:

- Regleralgorithmen;
- Harvest-Zielwertpipeline;
- Cross-Charge-Algorithmus;
- Command Lifecycle / Resync;
- Power Observation;
- Measurement V4;
- Excel-Lernsimulation.

## Restpunkte

- reale iPhone-Feldabnahme der beiden Mobile-Fixes;
- separater V4-only/V3-Legacy-Cleanup;
- spätere Konfigurationsstände/Import/Export;
- Graph-/Diagnoseausbau gemäß Roadmap.
