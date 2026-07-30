# Übergabe Zendure Energy Controller – V12.11.2-RC15
## Publish-/Readback-Isolation und Late-Effect-Neutralisierungsbarriere

**Stand:** 29.07.2026  
**Basis:** V12.11.2-RC14  
**Normative Grundlagen:** `ZEC_ANALYSE_REGELWERK_V1.1.md`, `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md`

## 1. Anlass

Die produktive RC14-FIXED_DISCHARGE-Episode zeigte zwei getrennte Fehler:

1. Ein abweichender Geräte-Readback überschrieb den lokalen Publish-Cache. Dadurch wurde ein unverändertes 2.000-W-Limit 157-mal normal wiederholt.
2. Das lange unwirksame Entladekommando wurde erst beim späteren Intentwechsel physisch wirksam. Vor Freigabe eines neutralen beziehungsweise gegenläufigen Folgeintents fehlte eine sicher bestätigte Nullbarriere.

Die Nutzeränderung von 2.000 auf 2.300 W war nicht ursächlich: Der nach bestehender Gerätebegrenzung resultierende Sollwert blieb unverändert −2.000 W.

## 2. RC15-Invarianten

- Publish-Historie und Geräte-Readback sind getrennte Evidenzebenen.
- Ein State-Readback darf keinen normalen Wiederholungspublish des unveränderten Sollwerts freigeben.
- Full-State-Recovery bleibt nach Cooldown erzwingbar.
- Der Late-Effect-Guard greift nur nach unaufgelöstem bestätigtem Aktiv-Mismatch und anschließendem Neutral-/Gegenrichtungswunsch.
- Gleiche Richtung und normal wirksame Richtungswechsel bleiben ohne Guard.
- Der Guard setzt nur beide Limits auf 0 und ändert `acMode` nicht für den Zwischenzustand.
- Freigabe erfolgt zeitbasiert mit monotonic elapsed time und mindestens zwei frischen unabhängigen Beobachtungen, nicht nach starrer Zykluszahl.
- Kein Guard-Latch und kein wiederholter Nullpublish.
- Persistente Geräteeigenschaften bleiben read-only.

## 3. Neue Diagnosefelder

```text
command_readback_matches_desired
command_readback_mismatch_fields
command_late_effect_guard_active
command_late_effect_guard_previous_intent
command_late_effect_guard_pending_intent
command_late_effect_guard_pending_target_w
command_late_effect_guard_duration_s
command_late_effect_guard_reason
command_late_effect_guard_activation_count
command_late_effect_guard_blocked_command_count
command_ac_mode_change_count
physical_power_direction_change_count
zendure_device_inverse_max_power_source
zendure_device_inverse_max_power_age_s
```

## 4. `inverseMaxPower`

Der Wert bleibt eine separat rückgelesene Gerätebegrenzung. Er ist nicht mit `outputLimit` gleichzusetzen und wird nicht als nachgewiesenes Hardwaremaximum bezeichnet. Herkunft, Quelle und Freshness werden diagnostisch getrennt; ZEC schreibt den Wert nicht.

## 5. Produktivtestpflichten

Nach Installation:

1. Version, Dienste, Flash-Schutz und vollständigen Command-State prüfen.
2. Neue RC15-Felder und RC15-V4-Header prüfen.
3. Sicherstellen, dass im AUTO-/Neutralbetrieb keine spontane Publish-Serie entsteht.
4. Erst danach kontrollierte kurze feste Entladung mit kleiner Leistung und sauberem Rückweg zu AUTO prüfen.
5. Kein Geräte-Mismatch künstlich provozieren.
6. Bei natürlichem Mismatch prüfen:
   - keine normalen Limitpublishes im Regelraster;
   - nur Full-State-Resyncs nach Cooldown;
   - Guard nur beim Neutral-/Gegenrichtungswechsel;
   - Freigabe erst nach frischem 0/0-Readback und stabiler physischer Nullwirkung.
7. Der noch offene RC14-High-SOC-Ladeendtest bleibt erforderlich.

## 6. No-Regression

Unverändert bleiben müssen:

- AUTO-, NIGHT-, HOLD- und Festmodus-Zielwertbildung;
- RC14-High-SOC-Acceptance;
- Flash-Schutz und Command-State-Gate;
- Neutralization-Dedupe;
- symmetrischer Cross-Charge-Schutz;
- alle Harvest-Formeln;
- Offgrid-Trennung;
- finale Excel-Lernsimulation.

## 7. Weiterer Entwicklungsweg

```text
RC15 installieren und Command-Safety prüfen
→ gemeinsamer RC14/RC15-Ladeendtest
→ RC-B SMA_FULL_OR_IDLE-Absolutziel
→ RC-C asynchrone lokale Zendure-API
→ Settings-Redesign
```

Keine Folgeversion oder Scope-Erweiterung ohne ausdrückliche Freigabe.
