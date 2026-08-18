# ZEC V13.0.3 – Release Information

**Release:** V13.0.3  
**Build-ID:** `v13.0.3-20260814`  
**Basis:** V13.0.2 / `v13.0.2-20260812`  
**Typ:** enger UI-/UX-Hotfix

## Scope

V13.0.3 korrigiert ausschließlich die Benutzerführung des Config-State-/Import-Preview-Workflows.

- Kontexttitel: `Konfigurationsstand prüfen` / `Import prüfen`.
- No-op zeigt `Keine Änderungen erforderlich` und genau eine sinnvolle Navigation.
- Kein deaktivierter `Speichern nicht möglich`-Button und keine bedeutungslosen Bestätigungscheckboxen bei No-op.
- Der bekannte V13.0.1→V13.0.2 Registry-Display-Metadata-Übergang wird als technischer Kompatibilitätsübergang klassifiziert, nicht als nutzerrelevante Migration.
- Der Parent zählt nur `user_migration_steps`; technische Übergänge erscheinen nicht als `1 Migration`.
- Interne Codes bleiben im Expertenmodus unter `Technische Details` diagnostizierbar.
- Echte Diffs, Validation, CAS, Commit und echte nutzerrelevante Warnungen/Bestätigungen bleiben erhalten.

## Nicht geändert

Keine Änderung an Regleralgorithmus, AUTO/Harvest/Cross-Charge/NIGHT, Command Lifecycle/Effect/Resync, Measurement V4, SQLite-Writer-/Backfill-Architektur, Last-Good-/Recovery-Vertrag, Graphdatenvertrag, Portabilitätsklassifikation oder Secret-Semantik.

## Installer

Der Installer akzeptiert ausschließlich V13.0.2 / `v13.0.2-20260812` als direkten Ausgangsstand und installiert V13.0.3 / `v13.0.3-20260814`.

Build-PASS ist nicht Produktiv-PASS. Die Feldabnahme erfolgt nach Installation gemäß `README_INSTALLATION.md`.
