# ZEC V16.1.0

## Zweck

V16.1.0 ist eine rückwärtskompatible funktionale Erweiterung des source-neutralen Primärspeicherpfads. Für das SMA-Sunny-Island-Modbus-Template wird die aktuell geräteseitig wirksame untere Entladegrenze als optionale read-only Capability erfasst und diagnostisch als normalisierter nutzbarer SOC verfügbar gemacht. Die Live-Regelstrategie bleibt unverändert.

## Block A

- SMA Sunny Island Register `31009`, FC03, U32/FIX0, read-only;
- Capability `current_discharge_floor_soc` ausschließlich im passenden Geräteprofil;
- eigener Poll-/Freshness-/Validity-Zustand; Capability-Fehler machen den bestehenden Pflichtpfad aus Leistung/SOC nicht automatisch ungesund;
- Invalidierung bei Quellen-/Profilwechsel, damit kein alter SMA-Wert in andere Quellen leakt;
- diagnostischer `primary_usable_soc_percent = clamp((raw_soc-floor)/(100-floor)*100, 0..100)` bei frischen gültigen Daten;
- Status/API/Readiness-Diagnose, Connection-Test und Measurement V4 um Floor-/usable-SOC-Evidenz erweitert;
- generische Settings-/Help-Sprache auf „Primärspeicher“ neutralisiert, Legacy-Keys bleiben kompatibel;
- `SECOND_BATTERY_DISPLAY_NAME` hat für neue Defaults keinen SMA-spezifischen Namen mehr; explizite Nutzerwerte bleiben erhalten.

## Explizite Nicht-Ziele

- keine Reglerwirkung durch Floor oder usable SOC;
- keine selbst berechnete saisonale ZEC-Kurve;
- kein editierbarer Floor, kein Override und kein On/Off-Schalter;
- keine automatische Capability für EVCC/custom/andere Geräteprofile;
- keine Änderung von FULL/IDLE-, Taper-, High-SOC-, Fast-Capture- oder Safety-Entscheidungen.

## Schutzgrenzen

`controller_logic.py` ist gegenüber V16.0.2 byteidentisch; SHA256:

`d243945adbb04dfa19fa915f8f32cafb375b7258888b2ecd6fb7a064cdea99ff`

Block B – die spätere strategische Verwendung des nutzbaren Primär-SOC in Winter-/Schwachertragslogik – ist ausdrücklich nicht Bestandteil von V16.1.0 und bleibt im Master-Backlog erhalten.

## Releaseidentität

- Version: `16.1.0`
- Label: `V16.1.0`
- Build-ID: `v16.1.0-20260919`
- unterstützte Updatequelle: ausschließlich `16.0.2 / v16.0.2-20260917`
- Fresh Install: ausschließlich bei real erkanntem `CLEAN_FRESH_INSTALL`
- Paket: `zendure_controller_v16_1_0.zip`

## Produktivfreigabe

Technische Build-/Fresh-Extract-Gates werden in `BUILD_VALIDATION_V16_1_0.md` dokumentiert. Ein vollständiger PRODUCTIVE-PASS ist ohne die reale V16.1.0-Update-Feldabnahme und ohne die separat zurückgestellte Clean-Fresh-/FIRST_INSTALL_SETUP-/Uninstaller-Gesamtabnahme nicht zulässig.
