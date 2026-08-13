# Release Info – Zendure Energy Controller V13.0.2

**Version:** `13.0.2`  
**Label:** `V13.0.2`  
**Build-ID:** `v13.0.2-20260812`

## Zweck

V13.0.2 ist ein konsolidierter Hotfix auf der produktiven V13.0.1-Codebasis. Er behebt die in der Feldabnahme gefundenen Robustheits- und UX-Fehler der neuen Konfigurationsstands-/Importfunktion sowie den nach Installations-Backfill nicht selbstheilenden SQLite-Writer. Zusätzlich korrigiert er die historische Graphlegende und bereinigt unbegründete historische Release-/RC-Bezüge in aktuellen Benutzertexten.

## Kernkorrekturen

- SQLite-Writer behält fehlgeschlagene Batches, rollt fehlerhafte Transaktionen zurück, verwirft die Connection und versucht mit frischer Connection erneut.
- Persistente Writerdiagnose mit `last_error`, Fehlerzeit, Folgefehlerzähler und `write_stale` nach 120 s trotz neuer Messpunkte.
- Runtime-Writer und historischer Config-Timeline-Backfill koordinieren die produktive DB über einen kurzen Interprozess-Maintenance-Lock; langes CSV-Scanning erfolgt außerhalb des DB-Locks über eine temporäre Staging-DB.
- Backfill meldet NUL-Zeichen, Parse-/Lesefehler und Problemdateien statt betroffene Dateien still zu überspringen.
- Lokale benannte Config-Stände und Austauschprofile trennen `artifact_kind` und Scope korrekt: ein lokaler Stand bleibt `named_state`, auch wenn sein Scope nur verteilbare Settings umfasst.
- Sicher erkannte beschädigte Config-State-Dateien können revisions-/SHA-gebunden gelöscht werden, ohne sie zuvor semantisch als ladbaren Stand akzeptieren zu müssen.
- Config-State/Import-Modal erhält Parent-/Child-Navigation; `Zurück`, Rename/Delete und Preview verlieren den Parentdialog nicht mehr. Fehler erscheinen im aktiven Modal.
- CSRF-Lebenszyklus: aktueller Model-Token hat Vorrang; bei `CSRF_TOKEN_INVALID` erfolgt einmalig Model-Refresh plus exakt ein Retry.
- Leerer/neutraler Preview ist nicht commitfähig; kein Commit-Token und kein aktiver Speichern-Pfad.
- `INHERITED_DEFAULT_CHANGED` verwendet die kanonische Settings-/Runtime-Auflösung und erzeugt keinen False Positive für abgeleitete Kompatibilitätswerte.
- Benutzerterminologie `verteilbares Profil/Regelprofil`.
- Historische Graphlegenden deduplizieren nur unmittelbar aufeinanderfolgende gleiche Werte; Rückkehrfolgen wie `99 % → 80 % → 99 %` bleiben erhalten.
- Aktuelle UI-, Hilfe- und Handbuchtexte beschreiben den heutigen Funktionsvertrag statt unnötiger Release-/RC-Geschichte; Details siehe `V13_0_2_USER_TEXT_AUDIT.md`.

## Registry-Kompatibilität

Durch die bereinigten öffentlichen Registry-Anzeigetexte ändert sich der öffentliche Registry-Hash. V13.0.2 verwendet `settings_registry_schema_version = 1.25-v13.0` und akzeptiert zusätzlich **ausschließlich** die exakt bekannte V13.0.1-Kombination

```text
schema = 1.24-v13.0
hash   = c1e13a7a1fd2968545bcf49073dc7b1d9e9dd7c71e0d002a45f50610d0780440
```

als geprüften Display-Metadata-Kompatibilitätsübergang. Beliebige andere Registry-Abweichungen bleiben fail closed.

## No-Regression

Keine fachliche Änderung an:

- AUTO-/Harvest-Zielwertbildung,
- Cross-Charge,
- NIGHT,
- Command Lifecycle / Effect / Resync,
- Single-Owner,
- Measurement-V4-Feldvertrag 246/249,
- Last-Good A/B und dessen Promotion-/Recoveryvertrag,
- Secret `keep/replace/clear`,
- den historischen Graphdaten bzw. der Config-Timeline-Semantik selbst.
