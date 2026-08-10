# ZEC V12.12.0 – Release Report

## Ergebnis

V12.12.0 **Settings Help & Guided Configuration** ist buildseitig freigegeben. Der Release erweitert die Settings-/Dokumentationsschicht und lässt die geschützte Regel-/Command-/Measurementlogik unverändert.

## Implementierte Hauptpunkte

1. Registry-native Help-Domain für alle 171 operativen Settings.
2. 62 priorisierte RICH-Hilfen für sicherheits-/regelungsrelevante Bereiche.
3. Kategorie- und Abschnittshilfe für 12 Kategorien und 69 operative Abschnitte.
4. Strukturierte ZEC-Hilfemodals mit Dependencies, Overrides, Risiken, Formeln, Beispielen und Handbuchanker.
5. Erweiterte Suche über Hilfetexte, Synonyme, Abhängigkeiten und Formeln.
6. Deterministische Guided-Configuration-Hinweise ohne automatische Configänderung.
7. Preview-Issues mit direkter `Warum?`-Navigation in die passende Setting-Hilfe.
8. Aktuelles 14-seitiges V12.12.0-Handbuch als DOCX/PDF.
9. Korrektur des widersprüchlichen Hilfs-/Validierungstexts für `CROSS_CHARGE_SIGNIFICANT_W`; keine Algorithmusänderung.
10. Version-/Installer-/Readiness-Identität auf V12.12.0 aktualisiert.

## Abnahme

```text
unittest / ResourceWarning hard gate   698 / 698 PASS
pytest                                  698 / 698 PASS
pytest subtests                          677 PASS
Browser Desktop + 3 Mobile Viewports     PASS
Handbuch DOCX/PDF 14 Seiten              PASS
```

Die finalen paketbezogenen Hash-/Manifest-/Syntax-/Byteidentitätswerte werden aus der frisch extrahierten Release-ZIP bestimmt und sind Bestandteil der externen Releaseübergabe.

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

- separater V4-only/V3-Legacy-Cleanup;
- spätere Konfigurationsstände/Import/Export;
- Graph-/Diagnoseausbau gemäß Roadmap.
