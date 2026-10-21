# Zendure Energy Controller V16.2.4

**Build-ID:** `v16.2.4-20260921`  
**Status:** **TECHNICAL BUILD PASS** – reale V16.2.3 → V16.2.4-Feldabnahme ausstehend.

## Scope

V16.2.4 behebt den real auf V16.2.3 gefundenen Settings-Surface-Defekt, ergänzt einen begrenzten sichtbaren Primärspeicher-Expert-Slice und schließt den persistenten Installationsreport-Punkt `ZEC-BL-DEP-002`.

- expliziter Settings-Product-Surface-/Applicability-Vertrag statt S1/RC19-Provenienzfilter;
- produktive Primärspeicher-Aktivierung, Kapazität und maximale Entladeleistung korrekt im Webmodell;
- S3/S4/S6/S7-Zielsettings bleiben fail-closed verborgen;
- 1-/2-Zendure-Topologie ohne neue Multi-Zendure-Commandsemantik;
- Expert-Slice `Strategie & Diagnose` für den Primärspeicher;
- Live-`/settings/model`-Feldgate;
- persistenter atomarer Installationsreport unter `/home/pi/Downloads` mit `/tmp`-Kompatibilitätskopie.

## Nicht geändert

Regler-, Command-, Safety- und Recoverysemantik bleiben unverändert. Fast Capture, Adaptive, strategischer usable SOC, Battery Care und automatische Primärspeicher-Metadaten sind nicht Bestandteil dieses Releases. `controller_logic.py` bleibt byteidentisch.


## Technischer Nachweis

150 Testdateien, vollständige Regression `1123 Tests + 698 Subtests PASS` und identischer `ResourceWarning=error`-Lauf. Bash `13/13`, Browser-JS `3/3`, Compileall, Deployment-Harness `11/11`, Root-Artefakt-Transaktion, Datenblatt-, Build-Evidence-, Manifest-/Hygiene- und Fresh-extract-Gates sind PASS.
