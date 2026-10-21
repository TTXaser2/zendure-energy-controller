# ADR-0001 – Fast Capture als positives Baseline-Overlay

**Status:** `RETROSPECTIVE_RECONSTRUCTION`, dokumentiert 19.10.2026, **kein im September erzeugtes Original-ADR**.
**Belege:** unveränderte Fast-Capture-V16.0.2-Originalspezifikation, reale V17.0.2-Sources und `ZEC-BL-CTRL-FASTCAP-001` im Master-Ledger.

## Problem

Der bisherige AUTO-/Harvest-Pfad war durch globale Glättung/Step-Limits bei kurzfristigen, nachweislich für Zendure verfügbaren Restüberschüssen begrenzt; eine globale Beschleunigung hätte die allgemeine Konvergenz und Hardwarebeanspruchung beeinflusst.

## Verfolgte Entscheidung

Fast Capture wurde als **zusätzlicher, nur positiv ladender A400/R100-Overlay** für `FULL_IDLE` und `NEAR_LIMIT` entworfen und in V17 implementiert. Baseline und Overlay bleiben in Zustand/Rechnung getrennt. Die normalen Safety-/Cross-Charge-/Commandgrenzen behalten Vorrang.

## Abgrenzte Alternativen (Quelleninhalt / nachträglich eingeordnet)

- **Globales Hochsetzen der AUTO-Rampe:** im Original explizit ausgeschlossen.
- **Eigenständiger zweiter Vollregler oder separater Command-Publisher:** im Original explizit ausgeschlossen.
- **Fast Capture in `RESERVE_UNKNOWN`:** im Original ausdrücklich nicht Teil des bestätigten Scopes.
- **Lernendes Acceptance-/SOH-Modell als harter Clamp:** im Original ausdrücklich ausgeschlossen.

## Folgen/Evidenz

V17.0.2 ist allgemeine Feldbasis PASS; Fast Capture `NEAR_LIMIT` besitzt partielle reale Active-Evidenz, `FULL_IDLE` bleibt im Feld `EVIDENCE_PENDING`. Diese ADR ersetzt weder Implementierungsdokumentation noch nachträgliche Feldevidenz.
