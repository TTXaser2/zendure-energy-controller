# Zendure Energy Controller V16.2.5

**Build-ID:** `v16.2.5-20260922`  
**Status:** **TECHNICAL BUILD PASS** – vollständige Regression, ResourceWarning-, Manifest-/Hygiene-, Datenblatt-, Deployment- und Fresh-extract-Gates sind bestanden. Reale V16.2.4 → V16.2.5-Feldabnahme anschließend erforderlich.

## Scope

V16.2.5 ist ein enger UI-/Diagnose-Hotfix aus realer V16.2.4-Nutzung:

- Speicherstatuskarten ohne Footer-/Content-Overlap; `Noch ladbar/entladbar` in der rechten Detailspalte, lesbarer Leistungsbereich;
- aktive High-SOC-/Command-Warnungen kompakt sichtbar, Langtext aufklappbar statt die Karte zu überdecken;
- Mobile Settings ohne unerreichbaren horizontalen Content-Overflow bei kleinen Viewports;
- konsistente Instance-Owner-Evidenz im allgemeinen Statussnapshot;
- numerische Graphlinien werden an bestätigten Evidence-/Coverage-Gaps sichtbar unterbrochen, ohne synthetische Messwerte;
- reguläre reale Updates verwenden dokumentarisch den kombinierten SHA/ZIP → normaler Installer → interner Preflight → bei PASS Installation-Ablauf.

## Nicht geändert

Regler-, Command-, Safety- und Recoverysemantik bleiben unverändert. Fast Capture, Adaptive, strategischer usable SOC, Battery Care und automatische Primärspeicher-Metadaten sind nicht Bestandteil dieses Releases. `controller_logic.py` muss byteidentisch bleiben.
