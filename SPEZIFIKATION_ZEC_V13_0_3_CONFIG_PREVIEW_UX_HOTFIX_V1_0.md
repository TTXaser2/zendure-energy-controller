# ZEC V13.0.3 – Config-State-/Import-Preview UX-Hotfix

**Version der Spezifikation:** 1.0  
**Datum:** 14.08.2026  
**Status:** umsetzungsreif zur Audit-/Buildfreigabe  
**Quellbasis:** V13.0.2 / `v13.0.2-20260812`

---

## 1. Ziel

V13.0.3 korrigiert ausschließlich die Benutzerführung des bereits funktionierenden
Konfigurationsstand-/Import-Preview-Workflows.

Der Backendvertrag von V13.0.2 – Integrität, Registry-/Schema-Kompatibilität,
Migration, Validation, Diff, CAS, Commit und Modalstack – bleibt erhalten.

Der Hotfix darf keine neue Config-Architektur und keine neue Controllerfunktion einführen.

---

## 2. Feldbefund

### 2.1 Backend korrekt

Produktiv bestätigt:

- V13.0.1-`named_state` kann unter V13.0.2 kompatibel eingelesen werden.
- V13.0.1-`portable_profile` mit 55 Scope-Keys kann unter V13.0.2 eingelesen werden.
- identischer Stand erzeugt keine wirksame Konfigurationsänderung.
- No-op-Commit ist gesperrt.
- `Zurück` kehrt in den Parent-Dialog zurück.

### 2.2 UX falsch

Der No-op-Preview zeigt derzeit interne Warn-/Kompatibilitätscodes:

```text
REGISTRY_DISPLAY_METADATA_V13_0_2
CONFIG_IMPORT_MIGRATED
```

und erzeugt dafür Bestätigungscheckboxen.

Die normale Benutzeransicht beantwortet damit nicht verständlich:

- Was wird geändert?
- Muss ich etwas tun?
- Ist das Profil kompatibel?
- Ist eine Migration von Regelwerten erfolgt?
- Warum soll ich Hinweise bestätigen, obwohl gar kein Commit möglich ist?

Der Parent kann zudem `1 Migration` anzeigen, obwohl nur ein technischer
Registry-Display-Metadata-Kompatibilitätsübergang stattfand.

---

## 3. UX-Grundprinzip

**Interne technische Zustände sind keine Benutzerentscheidungen.**

Die normale UI zeigt:

1. Ergebnis in verständlicher Sprache.
2. Tatsächliche Konfigurationsänderungen.
3. Tatsächlich relevante Risiken/Warnungen.
4. Nur dann eine Bestätigung, wenn der Benutzer eine echte Entscheidung treffen muss.

Technische Codes bleiben für Diagnose/Experten verfügbar, sind aber nicht primäre UX.

---

## 4. Kontextbezogene Überschrift

Der generische Titel:

```text
Änderungen prüfen
```

wird für Config-State-/Import-Kontexte ersetzt.

Mindestens:

```text
gespeicherter Stand:
Konfigurationsstand prüfen

Dateiimport:
Import prüfen
```

Normale Settings-Draft-Preview außerhalb dieses Workflows darf seinen bestehenden,
fachlich passenden Titel behalten.

---

## 5. No-op-Preview

Wenn keine wirksame Änderung existiert:

### 5.1 Primärtext

Gespeicherter Stand:

```text
Keine Änderungen erforderlich

Dieser Konfigurationsstand entspricht der aktuellen wirksamen Konfiguration.
Es werden keine Einstellungen geändert.
```

Verteilbares Profil / Import:

```text
Keine Änderungen erforderlich

Dieses Profil entspricht für die enthaltenen Einstellungen der aktuellen
wirksamen Konfiguration. Es werden keine Einstellungen geändert.
```

### 5.2 Aktionen

Bei No-op:

- keine Commit-Schaltfläche;
- kein deaktiviertes `Speichern nicht möglich`;
- keine Bestätigungscheckboxen;
- genau eine passende Navigation:
  - `Zurück`, wenn ein Parent-Workflow existiert;
  - andernfalls `Schließen`.

### 5.3 Technische Details

Optional:

```text
Technische Details
```

aufklappbar, standardmäßig geschlossen.

Dort dürfen enthalten sein:

- interne Reason-/Issue-Codes;
- Quellversion;
- Registry-/Schema-Version;
- Migrationsschritte;
- technische Kompatibilitätsentscheidung.

---

## 6. Kompatible ältere Quelle

Wenn ein State/Profil aus einer älteren, ausdrücklich kompatiblen Quelle stammt,
aber keine nutzerrelevanten Regelwerte geändert werden:

Normale Benutzerinformation, z. B.:

```text
Kompatibel eingelesen

Dieser Konfigurationsstand stammt aus einer kompatiblen älteren ZEC-Version.
Er wurde erfolgreich eingelesen. An den wirksamen Regelwerten sind keine
Änderungen erforderlich.
```

bzw. für Profil:

```text
Dieses Profil stammt aus einer kompatiblen älteren ZEC-Version und wurde
erfolgreich eingelesen. Für die enthaltenen Einstellungen sind keine Änderungen
erforderlich.
```

Nicht prominent anzeigen:

```text
REGISTRY_DISPLAY_METADATA_V13_0_2
CONFIG_IMPORT_MIGRATED
```

Diese Codes gehören nur in technische Details.

---

## 7. Migration – Benutzersemantik

### 7.1 Zwei Klassen

Intern sind mindestens zu unterscheiden:

**A. Technischer Kompatibilitätsübergang**

Beispiele:

- Registry-Display-Metadata-Kompatibilität;
- interne Versionsnormalisierung ohne Änderung der fachlichen Werte;
- rein technische Anpassung, die keine Nutzerentscheidung erfordert.

**B. Nutzerrelevante Migration**

Beispiele:

- Key wurde auf neuen Key übertragen;
- Einheit/Format wurde transformiert;
- alter Wert musste semantisch angepasst werden;
- Auswahl oder Verhalten kann sich fachlich unterscheiden.

### 7.2 Parent-Dialog

`N Migrationen` darf in der normalen UI nur Klasse B zählen.

Ein reiner Klasse-A-Übergang darf nicht als `1 Migration` dargestellt werden.

Technische Gesamtanzahl kann optional im Expertendetail auftauchen.

---

## 8. Bestätigungscheckboxen

Checkboxen sind ausschließlich zulässig, wenn:

- Commit prinzipiell möglich ist;
- eine konkrete nutzerrelevante Änderung oder ein Risiko existiert;
- die Bestätigung fachlich erforderlich ist.

Unzulässig:

```text
Hinweis CONFIG_IMPORT_MIGRATED wurde geprüft und wird bewusst bestätigt.
```

wenn:

- keine wirksame Änderung existiert;
- der Code nur einen technischen Kompatibilitätszustand beschreibt.

Benutzertext einer echten Bestätigung muss das konkrete Risiko in Alltagssprache nennen.

---

## 9. Preview mit echten Änderungen

Bei echten Änderungen bleibt der V13-Preview-/Validation-Vertrag erhalten.

Darstellung:

- verständliche Zusammenfassung;
- Diff alt → neu;
- Apply-/Restart-Semantik;
- Blocking Issues;
- echte Warnungen;
- nur tatsächlich notwendige Bestätigungen;
- `Speichern` nur nach erfüllten Voraussetzungen.

Interne Codes können ergänzend in technischen Details vorhanden sein.

---

## 10. Fehlerdarstellung

Der V13.0.2-Vertrag bleibt:

- Fehler einer Modalaktion im aktiven Modal;
- Toast nur ergänzend;
- Parent-Modalstack bleibt erhalten.

V13.0.3 darf diesen Fix nicht regressieren.

---

## 11. Standard/Experte

Normale Benutzeransicht bleibt verständlich und frei von internen Codes.

Im Expertenmodus darf ein zusätzlicher, standardmäßig geschlossener Bereich
`Technische Details` angeboten werden.

Expertenmodus ist Superset, aber technische Codes ersetzen niemals die
verständliche Primärinformation.

---

## 12. Nicht Bestandteil von V13.0.3

Nicht implementieren:

- neue Config-State-/Importfunktion;
- neue Bundle-Version;
- Änderung der 55 portablen Registry-Keys;
- Secret-Semantikänderung;
- Registry-/Schema-Migrationsarchitektur;
- Regleralgorithmus;
- Measurement V4;
- SQLite-/Backfill-Architektur;
- Last-Good;
- Graph-Redesign;
- Statusseiten-Expertenansicht;
- S2-/S3-Completion-Audits;
- S4/S5/S6/S7/S9 Storage-Gesamtblock;
- S8 Replay-/Simulation;
- Battery Care Mode.

---

## 13. Pflicht-Testmatrix

### 13.1 No-op named_state

V13.0.1-State unter V13.0.3:

- kompatibel;
- kein `INHERITED_DEFAULT_CHANGED`;
- keine wirksame Änderung;
- Titel `Konfigurationsstand prüfen`;
- klare No-op-Aussage;
- keine Checkbox;
- kein Commitbutton;
- `Zurück` → Parent.

### 13.2 No-op portable_profile

V13.0.1-Profil mit 55 Keys:

- kompatibel;
- keine wirksame Änderung;
- Titel `Import prüfen`;
- klare No-op-Aussage;
- kein `1 Migration` für reinen Display-Metadata-Übergang;
- keine Checkbox;
- technische Codes nur im Expertendetail;
- `Zurück` → Parent.

### 13.3 Echte Änderung

Fixture mit mindestens einem realen Wertunterschied:

- Diff sichtbar;
- verständliche Feldnamen;
- commitfähig nach Validation;
- keine irrelevanten Bestätigungen.

### 13.4 Echte nutzerrelevante Migration

Fixture mit fachlicher Migration:

- Migration in Benutzeransicht verständlich beschrieben;
- Parent zählt diese Migration;
- ggf. echte Bestätigung möglich.

### 13.5 Technischer Kompatibilitätsübergang

- intern weiterhin vollständig diagnostizierbar;
- normale UI zählt ihn nicht als nutzerrelevante Migration;
- kein Bestätigungszwang.

### 13.6 Regression

- Modalstack;
- CSRF-Refresh/Retry;
- No-op serverseitig nicht commitfähig;
- beschädigte States;
- portable-profile-Export;
- V13.0.1-Kompatibilitätsvertrag;
- aktuelle Registry-/Schema-Prüfung.

---

## 14. No-Regression-Gates

Geschützt:

```text
controller_logic.py
cross_charge.py
command_lifecycle.py
instance_owner.py
measurement_v4.py
measurement_v4_contract.py
SQLite Writer-/Backfill-Vertrag
Last-Good-/Recovery-Vertrag
```

Soweit der reale Code eine Änderung geschützter Pfade zwingend erfordern würde,
vor Implementierung stoppen und Scope-Konflikt melden.

---

## 15. Release-/Exit-Gates

Mindestens:

- vollständige bestehende Tests;
- neue V13.0.3-UX-Regressionen;
- `-W error::ResourceWarning`;
- Python AST / `py_compile`;
- JavaScript Syntax;
- Shell Syntax;
- JSON;
- Source-Manifest;
- geänderte/neue/gelöschte Dateien;
- No-Regression-Differential;
- HTTP-Route-Smokes;
- Desktop- und Mobilstruktur des Preview-Modals;
- finales ZIP frisch entpacken und erneut prüfen;
- vollständige Final-Validation;
- Installations-/Rollbackhinweis.

---

## 16. Feldabnahme

Nach Installation mindestens:

1. Version/Build-ID.
2. `/ready`.
3. SQLite-Writer bleibt gesund.
4. V13.0.1-Standard-Konfiguration → Preview:
   - verständliches No-op;
   - keine Checkboxen;
   - `Zurück` funktioniert.
5. V13.0.1-`zec-regelprofil.zec-config.json` → Preview:
   - verständliches No-op;
   - kein irreführendes `1 Migration`;
   - technische Codes nicht in Primäransicht.
6. mindestens ein echter Settings-/Config-Diff zeigt weiterhin sinnvollen Commitpfad.
7. keine Regression des Modalstacks/CSRF.

---

## 17. Freigabe

Diese Spezifikation ist umsetzungsreif.

Vor Codeänderung ist im neuen Chat noch erforderlich:

- reale V13.0.2-Quellbasis verifizieren;
- tatsächlichen Render-/API-Pfad kurz gegen diese Spezifikation auditieren;
- eine einzige Makro-Buildfreigabe einholen.
