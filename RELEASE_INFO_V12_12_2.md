# Release Info – Zendure Energy Controller V12.12.2

**Version:** `12.12.2`  
**Label:** `V12.12.2`  
**Build-ID:** `v12.12.2-20260810`

## Zweck

V12.12.2 ist ein konsolidierter Safety-/Diagnose-/UI-Bugfix auf Basis V12.12.1. Er übernimmt vier bestätigte V12.12.0-Produktivbefunde zusätzlich zu zwei bereits im Entwicklungschat bestätigten Feldbefunden.

## Muss-Scope

1. hostweit eindeutige Single-Instance-/Command-Owner-Garantie;
2. Harvest Entry/Hold mit monotoner realer Zeit plus frischen/distinkten Beobachtungen;
3. Current-State-Semantik für `harvest_limiter_reason`;
4. korrekte Measurement-Manifest-Semantik für Rotation, finalen Rowcount und Clean-Close;
5. klickfixiertes und tatsächlich scrollbareres Desktop-Panel `Controller & Schnittstellen`;
6. mobile SOC-Messwerte angedockt unter dem Plot statt als verdeckender Floating-Tooltip.

## Abgrenzung

Nicht Bestandteil sind der externe 14-Minuten-Host-Freeze, allgemeines Regler-/Harvest-/Cross-Charge-/NIGHT-Tuning, zusätzliche Installed-Tree-/Supply-Chain-Provenance, V3-Legacy-Cleanup und Änderungen an nicht ausreichend beobachteten Branches ohne neue Evidenz.

## Measurement

Produktiver Vertrag bleibt `ZEC-MEASUREMENT-V4`; Header/Feldschema werden nicht geändert. Der Writer-Lifecycle des Manifests wird korrigiert.
