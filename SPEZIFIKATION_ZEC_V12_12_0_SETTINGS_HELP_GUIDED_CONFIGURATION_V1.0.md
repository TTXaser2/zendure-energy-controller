# SPEZIFIKATION ZEC V12.12.0 – Settings Help & Guided Configuration

**Dokument:** `SPEZIFIKATION_ZEC_V12_12_0_SETTINGS_HELP_GUIDED_CONFIGURATION_V1.0.md`  
**Stand:** 09.08.2026  
**Status:** vollständiger Spezifikationsentwurf zur fachlichen Abnahme; noch keine Implementierungsfreigabe  
**Zielrelease:** V12.12.0  
**Entwicklungsthema:** Settings Help & Guided Configuration  

---

## 1. Verbindliche Quellbasis

Die Spezifikation wurde direkt aus dem finalen, in V12.11.7 ausgelieferten Quellpaket abgeleitet.

- Quellpaket: `zendure_controller_v12_11_7.zip`
- SHA256: `99caee1848cd5d7af3a241b8e1bf00de8724df4c7e9244cb8b186a11798edd67`
- Version: `12.11.7`
- Label: `V12.11.7`
- Build-ID: `v12.11.7-20260808`
- Source-Manifest: 334 Einträge
- Registry-Schema: `1.22-s1.1`
- Settings gesamt in der Registry: **212**
- aktuell operativ auf der Settings-Seite projizierte Settings: **171**
- davon Standard: **58**
- davon Expert/Protected/Deployment: **113**
- operative Kategorien: **12**
- operative Abschnitte: **69**

Zusätzliche normative Grundlage:

- `01_ZEC_PROJECT_RULES.md`
- `02_ZEC_CURRENT_STATE_AND_ARCHITECTURE.md`
- `03_ZEC_CONTROL_AND_SAFETY_INVARIANTS.md`
- `04_ZEC_UI_SETTINGS_AND_DIAGNOSTICS_CONTRACT.md`
- `05_ZEC_BACKLOG_AND_ROADMAP.md`
- `06_ZEC_RELEASE_AND_HANDOVER_PROCESS.md`
- `ZEC_ANALYSE_REGELWERK_V1.1.md`
- `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md`

Bei Konflikten gilt die im Projektregelwerk definierte Priorität: aktuelle produktive Evidenz / aktuelle Codebasis vor Spezifikation, danach kanonische Dauerquellen und normative Regelwerke.

---

## 2. Ausgangslage V12.11.7

V12.11.7 besitzt bereits eine funktional belastbare Settings-Architektur:

- `SettingsRegistry` als Schemaautorität,
- typisierte Werte und Codecs,
- Standard-/Expertenmodus,
- fachliche Kategorien und Abschnitte,
- Preview/Commit statt Direktpersistenz,
- clientseitige Basisvalidierung plus serverseitig authoritative Validierung,
- Apply-/Restart-Semantik,
- Default-/Provenienzklassen,
- sichere Reset-Policies,
- First-Install-Vertrag,
- Last-Good-/Recovery-Integration,
- Suchfunktion,
- responsive Desktop-/Mobile-UI.

Die Hilfefunktion ist dagegen noch nicht registry-nativ strukturiert:

1. Von 171 operativen Settings beziehen **152** ihre aktuelle Kurzbeschreibung aus `CONFIG_SCHEMA.description`.
2. **19** operative Settings – fast vollständig Harvest-Parameter – fallen mangels Beschreibung auf `validation_text` zurück. Dadurch stehen dort Wertebereichs-/Validierungssätze an Stelle einer echten Erklärung.
3. Kategoriegruppen, Kategoriebeschreibungen, Abschnittsreihenfolgen, Label-Overrides und UI-Dependency-Regeln liegen derzeit teilweise in `settings_model.py` statt in der Registry-Domain.
4. Es existieren **31** direkte UI-Dependency-Regeln, aber **104** operative Settings besitzen semantische `dependency_keys`.
5. Die Suche berücksichtigt aktuell im Wesentlichen Label, Beschreibung, Config-Key und Kategorie; strukturierte Hilfetexte, Abschnitte, Synonyme, Abhängigkeiten und Rechenbegriffe werden nicht indexiert.
6. Es gibt noch keine setting-spezifischen `i`-Detaildialoge, keine Kategorie-/Abschnittshilfe und keine strukturierte Darstellung von Erhöhen/Verringern, Override-Priorität, Rechenbeispiel oder Risiko.

V12.12.0 soll diese Lücke schließen, ohne die Regellogik zu verändern.

---

## 3. Ziele V12.12.0

### 3.1 Primärziel

Jede sichtbare Einstellung soll aus derselben fachlichen Quelle beantworten können:

- **Was steuert diese Einstellung?**
- **Wann wirkt sie und wann nicht?**
- **Was verändert ein höherer bzw. niedrigerer Wert?**
- **Welche anderen Einstellungen begrenzen, aktivieren, überschreiben oder benötigen sie?**
- **Welche Default-/Profil-/Sentinel-Semantik besitzt sie?**
- **Welche Validierungs- und Sicherheitsgrenzen gelten?**
- **Welches Risiko besteht bei einer Fehlkonfiguration?**
- **Gibt es ein belastbares Rechen- oder Anwendungsbeispiel?**
- **Wo steht der vertiefende Zusammenhang im Handbuch?**

### 3.2 Sekundärziele

- Hilfe und Suche werden aus Registry-Metadaten erzeugt, nicht aus parallel gepflegten UI-Textinseln.
- Nutzer sollen wirkungslose oder übersteuerte Einstellungen vor dem Speichern besser erkennen.
- Bestehende serverseitige Validation/Warnungen werden verständlicher in die Settings-Navigation eingebunden.
- Standardmodus bleibt einfach; Expertenmodus liefert zusätzliche technische Details, ohne widersprüchliche Inhalte.
- Der aktuelle Default-/Provenienzvertrag aus V12.11.7 bleibt vollständig erhalten.

---

## 4. Ausdrückliche Nicht-Ziele

V12.12.0 ändert **nicht**:

- Live-Regelalgorithmus,
- Zielwertbildung,
- Harvest-Allokation,
- Cross-Charge-Regellogik,
- Command-Lifecycle/Resync-Verhalten,
- SmartMode-/AC-Mode-Vertrag,
- Measurement-V4-Writer oder Measurement-V4-Contract,
- V3-Legacy-Unterbau,
- Last-Good-Recovery-Algorithmus,
- First-Install-Defaultvertrag,
- produktive Nutzerwerte,
- automatisch eine Einstellung aufgrund einer Hilfemeldung.

V12.12.0 darf reine Registry-/UI-Metadatenfehler korrigieren, wenn dadurch keine Runtime-Semantik geändert wird. Jede notwendige Änderung in geschützten Regler-/Command-/Measurementdateien wäre ein Scope-Konflikt und muss vor Umsetzung separat freigegeben werden.

---

## 5. Grundprinzipien für Hilfetexte

### 5.1 Keine erfundenen Empfehlungen

Eine Hilfe darf einen Wert nur als Empfehlung oder Standard bezeichnen, wenn die Registry ihn ausdrücklich als belastbaren `PRODUCT_DEFAULT` oder als benannten `PROFILE_PRESET` führt.

Nicht zulässig sind Aussagen wie:

- „400 W sind ein sinnvoller Nachtwert“,
- „2100 W ist die empfohlene Ladeleistung“,
- „15 % / 99 % sind Standard-SOC-Grenzen“,
- „192.168.0.40 ist die normale Broker-IP“.

Installations-, Anlagen- und Nutzerwerte werden als solche bezeichnet.

### 5.2 Default-Semantik muss sichtbar bleiben

Die V12.11.7-Klassen werden unverändert respektiert:

- `PRODUCT_DEFAULT`
- `PROFILE_PRESET`
- `SAFE_SENTINEL`
- `INSTALLATION`
- `AUTO_OR_UNSET`
- `LEGACY_INTERNAL`

Der Hilfe-Dialog erklärt diese Semantik dort, wo sie relevant ist. Ein sicherer Sentinel ist **kein empfohlener Betriebswert**.

### 5.3 Wirkung nur behaupten, wenn sie eindeutig ist

Für numerische Settings wird „höher / niedriger“ nur angezeigt, wenn die Richtung fachlich belastbar und im Code bzw. in bestehender Validierung/Dokumentation belegt ist.

Bei nicht monotonen oder kontextabhängigen Parametern muss ausdrücklich stehen:

> Keine allgemeine lineare Wirkung. Die Wirkung hängt von … ab.

### 5.4 Keine zirkulären oder physikalisch ungesicherten Aussagen

Hilfetexte zur Kommandowirkung unterscheiden Publish, Richtungsreaktion, Zielwerttracking und Systemziel. Ein gesendetes Kommando oder richtige Richtung darf nicht als vollständige Wirkung bezeichnet werden.

### 5.5 Hardwareschonung

Hilfetexte dürfen nicht behaupten, eine Softwareaktion entspreche einem Relais-/Schützvorgang oder einem Zellzyklus, sofern das nicht belegt ist. Zulässig sind Formulierungen wie „mehr Command-Publishes“, „häufigere Zieländerungen“ oder „potenziell höhere C-Rate“, sofern dies aus der Konfiguration folgt.

---

## 6. Registry-Erweiterung – Zielvertrag

### 6.1 Registry bleibt Single Source of Truth

Die Hilfemetadaten müssen in der Settings-Domain liegen. `settings_model.py` darf sie nur projizieren und nicht erneut fachlich formulieren.

Die derzeit in `settings_model.py` liegenden UI-Metadaten sollen soweit sinnvoll in die Registry-Domain überführt werden:

- Kategoriegruppen,
- Kategoriebeschreibungen,
- Abschnittsmetadaten und -reihenfolge,
- Label-Overrides,
- direkte UI-Abhängigkeitsbedingungen.

### 6.2 Neue fachliche Strukturen

Vorgesehen sind logisch mindestens folgende immutable Strukturen:

```text
CategorySpec
SectionSpec
SettingHelpSpec
HelpDependency
HelpExample
HandbookRef
```

Die konkrete Python-Ausprägung darf während der Umsetzung technisch angepasst werden, solange der folgende fachliche Vertrag vollständig erhalten bleibt.

### 6.3 `SettingHelpSpec`

Jedes der 171 operativen Settings erhält mindestens:

```text
short_help
extended_help
help_level
search_terms
handbook_ref
```

Für fachlich relevante Settings zusätzlich:

```text
effect_increase
effect_decrease
effect_enable
effect_disable
option_help
dependency_help
override_help
risk_help
example
formula_text
guidance_rule_ids
evidence_refs
```

Felder dürfen `None` sein, wenn eine Aussage fachlich nicht sinnvoll ist. Fehlende Aussage ist besser als erfundene Aussage.

### 6.4 `HelpDependency`

Abhängigkeiten werden nicht nur als Keyliste, sondern mit Beziehungstyp beschrieben. Mindestens folgende Relationstypen:

```text
REQUIRES
ENABLES
GATES
LIMITS
OVERRIDES
OVERRIDDEN_BY
PAIRED_WITH
SOURCE_FOR
DIAGNOSTIC_ONLY
RESTART_COUPLED
```

Beispiel:

```text
HARVEST_PRIMARY_CHARGE_FLOOR_RATIO
  OVERRIDDEN_BY -> HARVEST_PRIMARY_CHARGE_FLOOR_W

NIGHT_DISCHARGE_POWER_W
  LIMITS -> MAX_DISCHARGE_POWER_W
  GATES  -> NIGHT_DISCHARGE_ENABLED
```

### 6.5 `HelpExample`

Rechenbeispiele sind statisch und deterministisch. Sie dürfen keine aktuellen Hauswerte automatisch als Empfehlung verwenden.

Struktur:

```text
title
inputs
calculation
result
interpretation
```

Beispiele sollen ausdrücklich als Beispiel und nicht als Empfehlung gekennzeichnet sein.

### 6.6 `evidence_refs`

Intern gepflegte Quellenreferenzen, z. B.:

```text
CONFIG_SCHEMA.description
settings_validation:VAL-011
config_validator:AGGRESSIVE_CONTROL_PARAMS
controller_logic:_rest_surplus_thresholds
controller_logic:smooth_transition
SPEZIFIKATION_ZEC_V12_11_2_RC13_COMMAND_SAFETY_FOLLOWUP
```

Sie dienen Wartbarkeit und Tests. Sie müssen im Standardmodus nicht sichtbar sein; im Experten-Hilfedialog kann optional ein technischer Abschnitt „Quelle/Vertrag“ erscheinen.

---

## 7. Kategorie- und Abschnittshilfe

### 7.1 Abdeckung

V12.12.0 muss Hilfemetadaten für alle **12 operativen Kategorien** und alle **69 operativen Abschnitte** bereitstellen.

### 7.2 Kategoriehilfe – Mindestinhalt

Jede Kategorie erklärt:

1. Zweck der Kategorie,
2. welche Regel-/Systemfunktion sie beeinflusst,
3. welche Schutz-/Prioritätsregeln übergeordnet gelten,
4. ob Einstellungen live oder nach Neustart wirken können,
5. welche typischen Abhängigkeiten zur nächsten Kategorie bestehen.

### 7.3 Verbindliche fachliche Kernaussagen je Kategorie

#### Betriebsart & manuelle Steuerung

- `AUTO` nutzt die normale Netzleistungsregelung.
- `STOP_HOLD` und feste manuelle Modi haben Vorrang vor AUTO.
- Ein manueller Modus ungleich `AUTO` verhindert den Nachtmodus in diesem Zyklus.
- Feste Lade-/Entlademodi verwenden feste Leistungsziele bis zum Ziel-SOC und übersteuern die normale Netzregelung.
- Safe-State und harte SOC-/Gerätegrenzen behalten Vorrang.

#### Leistungsgrenzen & SOC-Schutz

- Lade-/Entladegrenzen sind installations-/geräteabhängig und keine universellen Defaults.
- `MIN_SOC_PERCENT` und `MAX_SOC_PERCENT` sind harte Schutzgrenzen.
- Manuelle und Nachtziele müssen innerhalb der globalen Grenzen bleiben.

#### AUTO-Regelung

- Netzabweichung wird nicht blind in einem Schritt kompensiert.
- Mittelwert, Totzone, Gain, Smoothing und Step begrenzen gemeinsam Reaktionsgeschwindigkeit und Ruhe.
- `MIN_COMMAND_CHANGE_W` beeinflusst Publish-Auflösung, nicht die interne Sollwertrechnung.
- Größere Reaktionsgeschwindigkeit ist nicht automatisch bessere Regelung.

#### Nachtbetrieb

- Nachtbetrieb ist eine **feste Basisentladung**, keine netzleistungsnachgeführte AUTO-Entladung.
- Der Leistungswert ist nutzerspezifisch und besitzt keinen universellen Betriebsdefault.
- Start/Ende dürfen über Mitternacht laufen.
- Bei erreichtem optionalen Reserve-SOC wird die feste Nacht-Basisentladung pausiert; normale AUTO-Regelung darf im selben Nachtfenster weiterhin Lastspitzen bis zur globalen `MIN_SOC_PERCENT`-Grenze behandeln.
- Beim Verlassen der festen Nachtentladung ist die 0-W-Neutralisierung aktiv sicherheitsrelevant.

#### Primärspeicher & SMA

- Die Datenquelle liefert Zustands-/Leistungsdaten des Primärspeichers für Cross-Charge/Harvest.
- Vorzeichen- und Einheitsnormalisierung ist sicherheitsrelevant.
- Profil `EVCC Standard` und benutzerdefinierte Topics sind unterschiedliche Datenquellenpfade.
- Keine Sollrichtung darf eine mehrdeutige Istleistungsrichtung zirkulär bestätigen.

#### Harvest / Restüberschuss

- Primärspeicher hat grundsätzlich Vorrang.
- Harvest darf nur Restüberschuss bzw. ausdrücklich spezifizierte Parallel-Harvest-Leistung nutzen.
- `REST_SURPLUS_MIN_EXPORT_W` ist eine Eintrittsschwelle, **kein gewünschter Restexport**.
- Floor/Restart/Near-Limit müssen als geordnete Primärspeicher-Schwellen verstanden werden.
- Ein positiver W-Override ersetzt den zugehörigen Ratio-Wert.
- High-SOC Eintritt/Austritt bilden eine Hysterese.
- Tageszeitprofil verändert Primärspeicher-Zielanteil und teilweise Entry-Bestätigungszeit.
- Delta und absoluter Zielwert dürfen nicht verwechselt werden.

#### Cross-Charge-Schutz

- Cross-Charge ist symmetrisch und reduziert konflikthaften Zendure-Sollwert proportional; der Schutz kehrt nicht selbstständig die Richtung um.
- Sollwertseitiger Gegenfluss und tatsächlich beobachteter Gegenfluss sind getrennte Dinge.
- Freshness der Zweitbatteriedaten ist sicherheitsrelevant.
- Bei aktiver Schutzfunktion muss `CROSS_CHARGE_SIGNIFICANT_W > 0` sein.

#### Kommandowirkung & Resync

- Publish ist kein Wirkungsnachweis.
- Diagnose unterscheidet Richtungsreaktion, Zielwerttracking und Systemziel.
- Sollwerte unter `COMMAND_EFFECT_MIN_TARGET_W` sind nicht robust bewertbar.
- Wirksame Tracking-Toleranz ist das Maximum aus absoluter W-Toleranz und relativer Prozenttoleranz.
- 0-W-Neutralisierung ist aktives Kommando.
- Resync-/Force-Resend-Parameter beeinflussen Recovery-Aktivität und dürfen nicht als normale Reglerdynamik beschrieben werden.

#### Zendure-Geräte

- Device-ID und Batterie-/Kapazitätsdaten sind installationsabhängig.
- Kapazität dient u. a. Prognose/Diagnose und darf nicht erfunden werden.

#### Schnittstellen & Datenquellen

- MQTT ist Command-/Telemetriepfad.
- Netzleistungsquelle ist eine explizite Anlagenentscheidung.
- SMA-Direktquelle und Shelly-kompatibler HTTP-Pfad besitzen unterschiedliche Voraussetzungen.
- Lokale Zendure-API kann je nach Konfiguration primär, ergänzend oder Fallback-only sein; Timeoutwerte sind mit Regelintervall abzustimmen.

#### Messdaten & Speicherung

- Measurement V4 ist produktive Grundlage.
- Logging ist nachgelagert und darf die Regelung nicht blockieren.
- `standard`, `extended` und `off` unterscheiden Umfang und Speichervolumen.
- Storage-Fallback muss sichtbar sein.

#### System & Diagnose

- Diagnose-/Loggingparameter ändern nicht automatisch die physische Regelfunktion.
- Administrative Aktionen sind keine normalen Settings-Änderungen.
- Neustart und Last-Good-Pointer-Reparatur bleiben geschützte, explizite Aktionen.

---

## 8. Hilfetiefen

### 8.1 BASE – alle 171 operativen Settings

Pflicht:

- `short_help`
- `extended_help`
- Default-/Provenienzbeschreibung
- Apply-/Restart-Hinweis
- Wertebereich / Enum-Bedeutung
- relevante Abhängigkeiten als Links
- `handbook_ref` oder explizit „kein belastbarer Handbuchanker vorhanden“
- `search_terms`

### 8.2 RICH – Prioritätsbereiche, 62 Settings

Verbindliche Prioritätskategorien gemäß UI-Vertrag:

- Betriebsart & manuelle Steuerung: 7
- Leistungsgrenzen & SOC-Schutz: 4
- AUTO-Regelung: 9
- Nachtbetrieb: 7
- Harvest / Restüberschuss: 19
- Cross-Charge-Schutz: 3
- Kommandowirkung & Resync: 13

Zusätzlich zu BASE:

- Wirkung bei Erhöhung/Verringerung oder Enable/Disable,
- konkrete Override-/Prioritätssemantik,
- Risikoerklärung,
- mindestens ein belastbares Beispiel je fachlichem Parametercluster,
- Guidance-Regeln bei wirkungslosen/übersteuerten Kombinationen,
- Formel bzw. Rechenlogik, wo sie aus dem Code eindeutig ableitbar ist.

### 8.3 RICH für weitere sehr-hohe Risiken

Außerhalb der sieben Prioritätskategorien erhalten alle operativen Settings mit `risk = Sehr hoch` ebenfalls mindestens Risiko-, Abhängigkeits- und Wirkungsdetails.

---

## 9. Setting-Detaildialog (`i`-Modal)

### 9.1 Öffnung

Jede operative Setting-Karte erhält rechts am Titel einen dezenten `i`-Button.

- kein Browser-Systemdialog,
- eigener ZEC-Modalvertrag,
- `aria-label="Hilfe zu <Label>"`,
- Tastatur: Enter/Space öffnet, Escape schließt,
- Fokus bleibt im Modal gefangen und kehrt danach zum auslösenden Button zurück.

### 9.2 Desktop

- Breite ca. 680–760 px,
- max. Höhe 80–85 vh,
- interner Scrollkontext,
- Hintergrund gesperrt,
- keine Änderung der Seiten-Scrollposition.

### 9.3 Mobil

- nahezu volle Breite,
- maximale Viewporthöhe,
- eigener Scrollbereich,
- dauerhaft erreichbare Schließen-/Navigationsaktion,
- kein Scroll-Chaining in den Hintergrund.

### 9.4 Aufbau

Reihenfolge:

1. **Titel + Kategorie / Abschnitt**
2. **Kurz erklärt**
3. **Wann wirkt die Einstellung?**
4. **Wirkung bei Änderung**
5. **Abhängigkeiten & Overrides**
6. **Grenzen / Validierung**
7. **Risiko / Sicherheitswirkung**
8. **Beispiel / Rechnung** (wenn vorhanden)
9. **Default-/Profil-Semantik**
10. **Wirksamkeit nach Speichern**
11. **Verwandte Einstellungen** – klickbare Navigation
12. **Handbuch**
13. im Expertenmodus optional **Technischer Vertrag**: Config-Key, Typ, Validator-IDs, Evidence-Refs

Leere Abschnitte werden nicht angezeigt.

---

## 10. Kategorie- und Abschnitts-`i`

### 10.1 Kategorie

Der Kategorie-Header erhält einen `i`-Button. Der Dialog erklärt Zielbild und Prioritäten der gesamten Kategorie.

### 10.2 Abschnitt

Jede Abschnittsüberschrift erhält einen kleinen `i`-Button, sofern SectionHelp vorhanden ist. Die Abschnittshilfe erklärt insbesondere den Zusammenhang der darunterliegenden Parameter.

Beispiel `Primärspeicher-Schwellen`:

```text
Floor <= Restart <= Near-Limit <= maximale Primärspeicher-Ladeleistung
```

und:

```text
positiver W-Override > 0 ersetzt den zugehörigen Ratio-Wert
```

---

## 11. Suchindex

### 11.1 Erweiterte Suchfelder

Die lokale Settings-Suche indexiert künftig:

- UI-Label,
- Config-Key im Expertenmodus,
- Kategorie,
- Abschnitt,
- `short_help`,
- `extended_help`,
- `search_terms`,
- Namen verknüpfter Einstellungen,
- Synonyme und fachliche Begriffe,
- Formel-/Override-Begriffe.

### 11.2 Sichtbarkeitsvertrag

- Standardmodus liefert keine ausschließlich als Expert sichtbaren Settings als Suchtreffer.
- First-Install-Pflichtsettings bleiben entsprechend dem V12.11.7-Vertrag sichtbar.
- Secret-Werte werden niemals indexiert; nur Label/Hilfe eines Secret-Settings darf durchsuchbar sein.

### 11.3 Suchsynonyme – Beispiele

```text
DEADBAND_W:
  Totzone, Deadband, Nullzone, 0 W, Restabweichung

CONTROL_GAIN:
  Verstärkung, Gain, Reaktion, Nachregelung

CROSS_CHARGE_SIGNIFICANT_W:
  Cross-Charge, Gegenfluss, Umladen, Schwelle

HARVEST_PRIMARY_CHARGE_FLOOR_RATIO:
  Floor, Mindestladeanteil, Primärspeicher, SMA, Verhältnis

COMMAND_EFFECT_TOLERANCE_W:
  Tracking, Toleranz, Soll-Ist, Wirkung
```

### 11.4 Trefferanzeige

Jeder Treffer zeigt:

- Label,
- Kategorie / Abschnitt,
- einen kurzen passenden Textausschnitt,
- optional den Treffergrund („gefunden über: Hysterese“),
- Sprung zur Einstellung.

---

## 12. Guided Configuration – Grundvertrag

### 12.1 Keine automatische Konfigurationsänderung

Guidance darf niemals selbst Werte ändern oder speichern.

### 12.2 Zwei Ebenen

#### Ebene A – sofortige, deterministische UI-Guidance

Darf clientseitig aus Registry-Metadaten und aktuellem Draft abgeleitet werden, wenn keine Runtime-/Netzwerkprüfung nötig ist.

Beispiele:

- Master-Schalter aus → abhängiger Parameter „derzeit ohne Wirkung“.
- W-Override > 0 → zugehöriges Ratio „derzeit übersteuert“.
- EVCC-Profil gewählt → Custom-Topicfelder „für dieses Profil nicht verwendet“.
- Measurement Logging `off` → Storageparameter „derzeit ohne Wirkung“.
- lokale API deaktiviert → API-Timeouts „derzeit ohne Wirkung“.
- manueller Modus `AUTO` → feste Lade-/Entladeprofile „gespeichert, aber derzeit inaktiv“.
- Nachtmodus aus → Nachtwerte „gespeichert, aber derzeit inaktiv“.

Diese Hinweise ersetzen keine Validation.

#### Ebene B – authoritative Preview-Guidance

Cross-Field-, Safety-, Runtime-, Storage- und Netzwerkprüfungen bleiben serverseitig und erscheinen beim vorhandenen „Änderungen prüfen“-Preview.

Bestehende `ERROR`, `WARNING`, `INFO`, `CONFIRM`, `RESTART` und `ACTION`-Semantik bleibt erhalten.

Es wird **kein** automatisches serverseitiges Voll-Preview bei jedem Tastendruck eingeführt, weil Preview Preflights/Netzwerk-/Storageprüfungen enthalten kann.

---

## 13. Geführte Hinweise – verpflichtende Regeln aus bestehender Evidenz

V12.12.0 muss bereits vorhandene, eindeutig definierte Warn-/Info-Regeln in der Hilfe referenzieren und im Preview verständlich verlinken.

### AUTO-Regelung

- `DEADBAND_W < 20`, `CONTROL_GAIN > 0.5`, `MAX_POWER_STEP_W > 300` → aggressive Kombination warnen.
- `MOVING_AVERAGE_SAMPLES > 30` → deutliche Trägheitswarnung.
- `INTERVAL_SECONDS <= 1`, `MOVING_AVERAGE_SAMPLES <= 2`, `SMOOTHING_FACTOR >= 0.8` → sehr schnelle Stellkonfiguration warnen.
- `MIN_COMMAND_CHANGE_W > MAX_POWER_STEP_W` → kleine Steps können häufig unterdrückt werden.
- `MIN_COMMAND_CHANGE_W > 2 × DEADBAND_W` → reduzierte Publish-Frequenz / verzögerte Feinkorrektur informieren.

### Harvest

- Entry-Bestätigung `< 2 × INTERVAL_SECONDS` → kurze Ereignisse können zu früh aktivieren.
- Entry-Bestätigung `> 180 s` → kurze nutzbare Fenster können verpasst werden.
- `MIN_COMMAND_CHANGE_W > REST_SURPLUS_MIN_EXPORT_W` → kleine Harvest-Korrekturen können unterdrückt werden.
- `REST_SURPLUS_MIN_EXPORT_W < DEADBAND_W` → zulässige Speziallage erklären; kein Fehler.
- `MAX_POWER_STEP_W < REST_SURPLUS_MIN_EXPORT_W` → bewusst langsame Aufnahme warnen.
- `SMOOTHING_FACTOR < 0.10` oder `INTERVAL_SECONDS >= 10` → Harvest reagiert träge.
- positiver Floor/Restart/Near-Limit-W-Override → Ratio ist nicht wirksam; Effective Source = absolute W.

### Nachtmodus

- aktiviert + Leistung 0 → blockierend.
- Leistung > `MAX_DISCHARGE_POWER_W` → blockierend.
- Reserve-SOC < `MIN_SOC_PERCENT` → blockierend.
- Reserve-SOC > `MAX_SOC_PERCENT` → warnen, weil feste Nachtentladung früh oder gar nicht startet.

### Cross-Charge

- Schutz aktiv + `CROSS_CHARGE_SIGNIFICANT_W <= 0` → blockierend gemäß aktueller ConfigValidation.
- `SECOND_BATTERY_STALE_TIMEOUT_SECONDS < 5` → Warnung vor unnötig frühem Blockieren bei kurzen MQTT-Pausen.

### Command Effect / Resync

- Cooldown 0 → deutliche Resync-/Publish-Sturmwarnung gemäß Registry-Vertrag.
- kurze Retry-/Freshness-/Neutralization-Zeiten müssen als zusätzliche Command-/Recovery-Aktivität beschrieben werden.
- `COMMAND_EFFECT_FORCE_RESEND_SECONDS` wirkt effektiv nicht früher als `COMMAND_EFFECT_TIMEOUT_SECONDS` plus bestehende Cooldown-/Mismatchbedingungen.

### lokale Zendure-API

- Control-Timeout-Cap >= 75 % des Regelintervalls → Laufzeitwarnung.
- Full Timeout >= Regelintervall → Warnung vor verlängerten Zyklen, sofern API im relevanten Pfad genutzt wird.

Automatisierte Guidance darf ausschließlich Schwellen verwenden, die in aktueller Codebasis/Validatoren bereits explizit definiert sind. Für qualitative Texte ohne definierte Schwelle wird keine neue Schwelle erfunden.

---

## 14. Fachlich verbindliche RICH-Hilfe – AUTO

### 14.1 `CONTROL_GAIN`

Kurzinhalt:

- Anteil der aktuellen Netzabweichung, der in die nächste rohe Zielwertkorrektur eingeht.

Belegtes Rechenbeispiel:

```text
letzte Ladeanforderung = 600 W
wirksamer Export       = 500 W
CONTROL_GAIN           = 0,30

rohes Ziel = 600 W + 500 W × 0,30 = 750 W
```

Danach wirken Maximalleistung, Smoothing, Step-Limit, Cross-Charge und Commandpfad.

Wirkungsrichtung:

- höher → schnellere/kräftigere Korrektur, potenziell nervöser;
- niedriger → sanftere/langsamere Korrektur.

### 14.2 `SMOOTHING_FACTOR`

Codevertrag:

```text
smoothed = old × (1 - factor) + target × factor
```

- `1.0` → keine zusätzliche Glättung,
- kleiner → stärker geglättet / langsamer.

### 14.3 `MAX_POWER_STEP_W`

- begrenzt Änderung des Zielwerts je Regelzyklus,
- größere Werte ermöglichen schnelleres Nachführen,
- kleinere Werte begrenzen Leistungsänderungen stärker.

Die Hilfe zeigt zusätzlich die nominale maximale Änderungsrate:

```text
MAX_POWER_STEP_W / INTERVAL_SECONDS = W/s
```

als reine Orientierung; tatsächlicher Zyklusabstand kann durch aktive Arbeit länger sein.

### 14.4 `DEADBAND_W`

- innerhalb `|grid_power| <= DEADBAND_W` wird normal HOLD bevorzugt,
- größer → mehr tolerierte Restabweichung / weniger Nachregelung,
- kleiner → engeres 0-W-Ziel / höhere Empfindlichkeit gegen Rauschen.

Harvest kann in ausdrücklich spezifizierten Spezialzweigen innerhalb der normalen Totzone weiterarbeiten; dies muss im Modal erwähnt werden.

### 14.5 `MIN_COMMAND_CHANGE_W`

- ist Publish-/Command-Auflösung, kein Zielwert-Limiter,
- größer → weniger kleine MQTT-Leistungsupdates,
- kleiner → feinere Aktualisierung, mehr Publishes.

### 14.6 `MOVING_AVERAGE_SAMPLES`

- größer → längeres effektives Beobachtungsfenster und träger,
- kleiner → schneller, stärker von Einzeländerungen beeinflusst.

Näherung im Modal:

```text
ungefähres Fenster = Samples × Regelintervall
```

### 14.7 `MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W`

- normale AUTO-Ladung startet erst, wenn wirksamer Überschuss ausreichend groß ist,
- wirksame normale Freigabeschwelle ist mindestens `max(DEADBAND_W, MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W)`.

### 14.8 `SMA_GUARD_RAMP_DOWN_W`

- Schrittweite beim Abbau einer bestehenden AUTO-Ladung in dafür vorgesehenen Ramp-down-Pfaden,
- nicht mit allgemeinem `MAX_POWER_STEP_W` gleichsetzen.

### 14.9 `INTERVAL_SECONDS`

- nominale Pause / Zyklusbasis,
- tatsächlicher Zyklusabstand = aktive Arbeit + Wartezeit,
- beeinflusst zusammen mit Samples, Step und Freshness die reale Reaktionsdynamik.

---

## 15. Fachlich verbindliche RICH-Hilfe – Nacht / manuelle Modi / Limits

### 15.1 Priorität

Modal und Kategoriehilfe müssen sichtbar machen:

```text
Safe-/Schutzbedingungen
→ manueller Modus, wenn MANUAL_MODE != AUTO
→ Nachtmodus, wenn MANUAL_MODE == AUTO und Nachtfenster aktiv
→ normale AUTO-Regelung
```

### 15.2 Feste Leistungen

`MANUAL_FIXED_*_POWER_W` und `NIGHT_DISCHARGE_POWER_W` sind feste Leistungsziele, keine 0-W-Netzreglerwerte.

Insbesondere Nacht:

> Eine feste Nachtentladung wird nicht fortlaufend anhand der Haus-Netzleistung nachgeführt. Ein zu hoch gewählter Wert kann deshalb bei geringer Hauslast zu Netzeinspeisung führen. Der Wert muss zur eigenen Anlage und Lastsituation passen und besitzt keinen universellen Betriebsdefault.

### 15.3 Ziel-SOC

- feste Entladung: Ziel muss innerhalb der globalen SOC-Grenzen und unter aktuellem SOC liegen, bevor gestartet wird;
- feste Ladung: Ziel muss innerhalb der globalen SOC-Grenzen und über aktuellem SOC liegen, bevor gestartet wird.

### 15.4 Nacht-Reserve-SOC

- optional,
- `None` bedeutet keine zusätzliche Nachtreserve über `MIN_SOC_PERCENT` hinaus,
- bei Erreichen wird die feste Nacht-Basisentladung pausiert,
- AUTO darf im selben Fenster weiterarbeiten, solange globale Schutzbedingungen dies erlauben.

### 15.5 Zeitfenster

Die vier technischen Hour-/Minute-Keys bleiben intern erhalten, die Hilfe ist jedoch an die zwei logischen Compoundfelder gekoppelt:

- Startzeit,
- Endzeit.

Start und Ende dürfen nicht identisch sein. Über-Mitternacht-Fenster sind zulässig.

---

## 16. Fachlich verbindliche RICH-Hilfe – Harvest

### 16.1 Zielbild

Harvest darf Restexport bzw. ausdrücklich spezifizierte Parallel-Harvest-Leistung aufnehmen, ohne die Primärspeicherpriorität strategisch zu verletzen.

Die Hilfe muss klar zwischen folgenden Begriffen unterscheiden:

```text
Eintrittsschwelle
Primärspeicher-Floor
Restart-Schwelle
Near-Limit-Schwelle
SMA-Zielanteil
Restexport
Zendure-Delta
absoluter Zendure-Zielwert
```

### 16.2 Floor / Restart / Near-Limit

Bei vorhandener maximaler Primärspeicher-Ladeleistung `Pmax` gilt ohne positiven W-Override:

```text
Floor     = Pmax × Floor-Ratio
Restart   = Pmax × Restart-Ratio
NearLimit = Pmax × Near-Limit-Ratio
```

Validierungsinvariante:

```text
0 <= Floor <= Restart <= NearLimit <= Pmax
```

Ein positiver absoluter W-Wert ersetzt den zugehörigen Ratio-Wert.

### 16.3 Rechenbeispiel

Nur als Beispiel, nicht Empfehlung:

```text
Pmax Primärspeicher = 2400 W
Floor-Ratio         = 0,30
Restart-Ratio       = 0,85
Near-Limit-Ratio    = 0,95

Floor     = 720 W
Restart   = 2040 W
NearLimit = 2280 W
```

Wird z. B. `HARVEST_PRIMARY_CHARGE_RESTART_W = 1900` gesetzt, ist für Restart der Ratio-Wert nicht wirksam.

### 16.4 High-SOC-Hysterese

Invariante:

```text
Exit < Enter <= Full-SOC <= 100 %
```

- `Enter` bestimmt Eintritt in den High-SOC-Bereich,
- `Exit` verhindert sofortiges Flattern beim Unterschreiten des Eintrittswerts,
- `Full-SOC` kennzeichnet den Voll-/Idle-Zweig.

### 16.5 `HARVEST_HIGH_SMA_SOC_MIN_EXPORT_W`

- ist Eintritts-/Eligibility-Schwelle,
- **kein gewünschter verbleibender Export**.

### 16.6 `REST_SURPLUS_MIN_EXPORT_W`

- Mindest-Netzexport für den Near-Limit-/Restüberschuss-Eintritt,
- ebenfalls kein Netz-Zielwert.

### 16.7 Entry-Bestätigung / Hold

`REST_SURPLUS_ENTRY_CONFIRM_SECONDS` bestätigt Near-Limit-/Restexportzustände über Zeit.

`HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS` ist kontextabhängig: Bei aktivem Zeitprofil verwendet die Laufzeit in den aktuellen festen Profilfenstern teilweise profilbezogene Bestätigungszeiten; außerhalb bzw. bei deaktiviertem Profil greift der konfigurierte Wert. Die Hilfe darf daher nicht behaupten, der Wert sei in jeder Tageszeit unmittelbar wirksam.

`HARVEST_HIGH_SMA_SOC_HOLD_SECONDS` ist keine maximale Aktivdauer. Der Wert hält einen zuvor aktiven Harvest-Zustand nach kurzfristigem Wegfall der Eligibility begrenzt aufrecht, solange insbesondere die Exit-SOC-Bedingung nicht verletzt ist.

### 16.8 Tageszeitanteile

Die drei operativ sichtbaren Shares werden als Anteil der verfügbaren Primärspeicher-/Gesamtleistung erklärt, nicht als direkter Zendure-Sollwert.

Ein höherer Primärspeicher-Zielanteil reserviert in der betreffenden Strategie grundsätzlich mehr Leistung für den Primärspeicher und entsprechend weniger für den Zendure-Anteil, vorbehaltlich Export-Capture und anderer Limiter.

### 16.9 Absolut-/Delta-Semantik

Das Help-Modal muss bei Harvest ausdrücklich warnen:

> Ein Restexportwert ist nicht automatisch ein absoluter Zendure-Sollwert. In relevanten Zweigen wird ein absoluter Zielwert aus bereits wirksamer Zendure-Ladung und weiter vorhandenem Export bzw. aus der jeweiligen Allokationsrechnung gebildet.

---

## 17. Fachlich verbindliche RICH-Hilfe – Cross-Charge

### 17.1 `CROSS_CHARGE_SIGNIFICANT_W`

Runtime-Vertrag:

- Engage-Schwelle = konfigurierter Wert,
- interne Release-Hysterese = `max(20 W, Engage / 2)` bei Engage > 0.

Beispiel:

```text
Engage = 80 W
Release = 40 W
```

Wichtig: Die aktuelle ConfigValidation blockiert bei aktivem Cross-Charge Werte `<= 0`. Der bestehende Registry-Text „0 bedeutet Reaktion auf jeden nichtnulligen Gegenfluss“ ist deshalb für die operative UI irreführend und muss in V12.12.0 **nur als Metadatenkorrektur** bereinigt werden. Es erfolgt dadurch keine Änderung an der Controllerlogik.

### 17.2 Symmetrische Korrektur

Die Hilfe erklärt:

- Konflikt wird nur behandelt, wenn Zweitbatterieleistung und Zendure-Ziel gegengerichtet sind,
- Ziel wird proportional reduziert,
- der Cross-Charge-Schutz kehrt die Richtung nicht selbstständig um,
- frische/valide Zweitbatteriedaten sind erforderlich.

### 17.3 Stale-Block

`SECOND_BATTERY_STALE_BLOCK_CHARGE` ist konservativer Fallback bei fehlenden frischen Daten. Abschalten darf nicht als „Performance-Optimierung“ dargestellt werden, sondern als Reduktion eines Schutzmechanismus.

---

## 18. Fachlich verbindliche RICH-Hilfe – Command Effect / Resync

### 18.1 Qualitätsstufen

Die Hilfe verwendet folgende Semantik:

1. Publish ausgeführt,
2. Richtungsreaktion beobachtet,
3. Sollwerttracking innerhalb Toleranz,
4. Systemziel plausibel erreicht.

### 18.2 Mindest-Sollwert

`COMMAND_EFFECT_MIN_TARGET_W` ist **keine Mindestleistung des Geräts**. Unterhalb dieser Diagnosegrenze ist die Wirkung lediglich nicht robust bewertbar.

### 18.3 Mindest-Istleistung

`COMMAND_EFFECT_MIN_W` kennzeichnet eine belastbare Richtungsreaktion, noch kein vollständiges Sollwerttracking.

### 18.4 Tracking-Toleranz

Verbindliche Formel:

```text
wirksame Toleranz = max(
  COMMAND_EFFECT_TOLERANCE_W,
  abs(target_w) × COMMAND_EFFECT_TOLERANCE_PERCENT / 100
)
```

Beispiel:

```text
Sollwert = 2000 W
abs. Toleranz = 80 W
relative Toleranz = 10 % = 200 W
wirksam = 200 W
```

### 18.5 Timeout / Force Resend / Cooldown

- `COMMAND_EFFECT_TIMEOUT_SECONDS` bestätigt persistente Nichtwirkung desselben Intents; kleine Sollwertänderungen derselben Richtung starten die Episode nicht ständig neu.
- `COMMAND_EFFECT_FORCE_RESEND_SECONDS` darf nicht als normale periodische Wiederholung erklärt werden, sondern als Recovery bei anhaltender Nichtwirkung.
- `COMMAND_RESYNC_COOLDOWN_SECONDS` begrenzt identische Recovery-Wiederholungen.
- `COMMAND_NEUTRALIZATION_TIMEOUT_SECONDS` überwacht aktive sicherheitsrelevante 0-W-Neutralisierung.

### 18.6 Command-State / Flash-Schutz

Hilfe muss zwischen dynamischen SmartMode-Kommandos und persistenten Geräteeinstellungen unterscheiden. Keine unbelegte Aussage über Flash-Schreibvorgänge.

---

## 19. Nicht-priorisierte Kategorien – Mindestanforderung

Für die übrigen 109 operativen Settings gilt BASE-Hilfe. Zusätzlich müssen bei technischen Expert-Settings klar erkennbar sein:

- reine Diagnosewirkung vs. Regelwirkung,
- Neustartpflicht,
- Datenquellenabhängigkeit,
- Storage-/Logging-Auswirkung,
- optionale vs. zwingende Identifikatoren,
- Read-only / deployment / administrative Semantik.

Insbesondere bei SMA-Direktquelle, MQTT, Local API, Measurement und Replay dürfen Hilfetexte nicht aus alten Installationsannahmen abgeleitet werden.

---

## 20. Handbuchanker – aktueller Befund und Ziel

### 20.1 Aktueller Befund

Das derzeit ausgelieferte generische Handbuch `docs/Zendure_Energy_Controller_Handbuch.pdf` bezeichnet sich noch als **V12.6** und enthält veraltete bzw. inzwischen unzulässige Pseudodefaults, u. a.:

- `MQTT_BROKER = 192.168.0.40`,
- `SHELLY_IP = 192.168.0.40`,
- alte Lade-/Entladegrenzen,
- alte SOC-/Reglerwerte,
- historische Keys und frühere UI-/Settings-Semantik.

Daher darf V12.12.0 **nicht blind** auf diese veralteten Inhalte verlinken.

### 20.2 V12.12.0-Vertrag

Handbuchanker werden erst aktiv angezeigt, wenn der referenzierte Handbuchabschnitt im selben Release aktualisiert und mit V12.12.0 fachlich konsistent ist.

V12.12.0 umfasst deshalb einen **Dokumentationsabgleich** des generischen Handbuchs mindestens für:

- Settings-Seite,
- Default-/Provenienzsemantik,
- First Install,
- AUTO-Regelparameter,
- manuelle Modi,
- Nachtmodus,
- Cross-Charge,
- Harvest,
- Command Effect / Resync,
- Measurement V4 / Storage-Grundlagen.

Die generischen Dateien

```text
docs/Zendure_Energy_Controller_Handbuch.docx
docs/Zendure_Energy_Controller_Handbuch.pdf
```

müssen denselben fachlichen Stand tragen.

### 20.3 Technischer Linkvertrag

`HandbookRef` enthält mindestens:

```text
section_id
section_title
page
```

UI-Link:

```text
/manual.pdf#page=<page>
```

Die Seite ist buildseitig gegen die tatsächlich ausgelieferte PDF zu verifizieren. Nicht vorhandene/ungeprüfte Seiten dürfen keinen aktiven Link erzeugen.

---

## 21. Standard- vs. Expertenmodus

### Standard

Zeigt:

- verständliche Kurz-/Langhilfe,
- Wirkung,
- relevante Abhängigkeiten,
- Risiko in nutzerverständlicher Form,
- Beispiel,
- Default-/Profil-Semantik,
- Handbuchlink.

Verbirgt grundsätzlich:

- interne Validator-IDs,
- Evidence-Refs,
- technische Config-Key-Details, sofern das Setting nicht ohnehin technisch exponiert ist.

### Experte

Zusätzlich:

- Config-Key,
- Typ / Codec,
- Validator-IDs,
- strukturierte Beziehungstypen,
- technische Formeln,
- Evidence-Refs bzw. Vertragsquelle,
- ausführlichere Runtime-/Recovery-Hinweise.

Experte ist weiterhin Superset des Standardmodus.

---

## 22. Compound-Felder

Logische UI-Felder dürfen weiterhin mehrere technische Keys abbilden.

Nachtzeit:

```text
NIGHT_START_HOUR + NIGHT_START_MINUTE -> Startzeit
NIGHT_END_HOUR   + NIGHT_END_MINUTE   -> Endzeit
```

Die Hilfe wird an das logische Compoundfeld gebunden; keine vier nahezu identischen Benutzer-Modals.

Die zugrundeliegenden technischen Keys bleiben im Expertenvertrag nachvollziehbar.

---

## 23. Guided-Navigation

Abhängigkeiten im Hilfe-Modal sind klickbar.

Beispiel:

```text
Nachtentladeleistung
  begrenzt durch → Maximale Entladeleistung
```

Klick führt zu `MAX_DISCHARGE_POWER_W`, wechselt falls nötig Kategorie und scrollt/fokussiert die Einstellung.

Im Standardmodus darf der Sprung zu einer nur im Expertenmodus sichtbaren Einstellung nicht heimlich den Modus umschalten. Stattdessen:

> „Diese abhängige Einstellung ist nur im Expertenmodus sichtbar.“

mit expliziter Aktion **„Im Expertenmodus anzeigen“**.

---

## 24. Preview-Integration

Bestehende Issues bleiben die authoritative Speichersperre.

V12.12.0 ergänzt:

- Issue zeigt zugehörige Einstellung und optional „Warum?“ → öffnet deren Help-Modal.
- Bei Multi-Key-Issue werden alle beteiligten Settings als Links angeboten.
- INFO/WARNING wird visuell von blockierendem ERROR getrennt.
- `effective_source` wie `absolute_w` wird im Help-Kontext erklärt.
- Commitverhalten bleibt unverändert.

---

## 25. Datenmodell / API-Projektion

Das Settings-Modell liefert für Kategorie, Abschnitt und Setting nur redaktionssichere Hilfedaten.

Pro Setting mindestens:

```json
{
  "help": {
    "level": "base|rich",
    "short": "...",
    "extended": "...",
    "effect_increase": null,
    "effect_decrease": null,
    "effect_enable": null,
    "effect_disable": null,
    "dependencies": [],
    "override": null,
    "risk": null,
    "example": null,
    "search_terms": [],
    "handbook": null
  }
}
```

Experten-only technische Felder dürfen serverseitig abhängig vom UI-Modus projiziert oder clientseitig nur im Expert-Template angezeigt werden. Secret-Inhalte sind ausgeschlossen.

---

## 26. Performance- und Sicherheitsvertrag

- Keine externe Websuche oder KI-Laufzeitfunktion.
- Hilfetexte sind statische Registry-Daten.
- Keine Datenbankabfrage pro Help-Modal.
- Kein Netzwerk-Preflight beim Öffnen einer Hilfe.
- Suche bleibt lokal auf dem bereits geladenen Settings-Modell.
- Kein blockierender Zugriff im Controller-Regelzyklus.
- Keine zusätzlichen MQTT-Kommandos durch Hilfe/Guidance.
- Keine zusätzlichen persistenten Geräteschreibvorgänge.
- Kein Einfluss auf Readiness oder Command-Gate.

---

## 27. Barrierefreiheit / UX

Pflicht:

- vollständige Tastaturbedienung,
- sichtbarer Fokus,
- semantische Buttons,
- `aria-modal`, `aria-labelledby`,
- keine reine Farbcodierung für Risiko/Warning,
- mobile Scrollsperre wie im bestehenden Modalvertrag,
- Textbreite so begrenzen, dass lange Hilfen lesbar bleiben,
- Code/Formeln monospace, aber nicht als unstrukturierter Fließtext,
- Tabellen auf Mobil ggf. als gestapelte Key/Value-Blöcke.

---

## 28. Bekannte Quellkonflikte / Errata, die V12.12.0 dokumentarisch bereinigen muss

### 28.1 `CROSS_CHARGE_SIGNIFICANT_W`

Registry-Validationtext V12.11.7 suggeriert, `0` bedeute Reaktion auf jeden nichtnulligen Gegenfluss. Der aktuelle `config_validator` blockiert bei aktivem Cross-Charge jedoch `<= 0`.

V12.12.0 folgt für die Benutzerhilfe dem tatsächlich speicherbaren Vertrag:

> bei aktivem Cross-Charge muss der Wert > 0 sein.

Nur Registry-/Hilfetext korrigieren; keine Controllerlogikänderung.

### 28.2 Handbuch V12.6

Das generische Handbuch enthält alte nutzer-/anlagenspezifische Defaults. Diese dürfen nicht in V12.12.0-Hilfe übernommen werden. Dokumentation muss aktualisiert werden, bevor Handbuchlinks aktiv werden.

### 28.3 19 Description-Fallbacks

19 operative Settings nutzen aktuell `validation_text` als sichtbare Beschreibung. V12.12.0 ersetzt dies durch echte `short_help`-Texte; `validation_text` bleibt für Validierung zuständig.

---

## 29. Testvertrag V12.12.0

### 29.1 Registry-Tests

- 212/212 SettingSpecs weiterhin eindeutig.
- 171/171 operative Settings besitzen gültiges `help`.
- 12/12 operative Kategorien besitzen CategoryHelp.
- 69/69 operative Abschnitte besitzen SectionHelp.
- 62/62 Prioritätssettings besitzen RICH-Hilfe.
- alle sehr-hohen operativen Risiken außerhalb der Prioritätsbereiche besitzen Risiko-/Abhängigkeitsdetails.
- kein `INSTALLATION`-Setting enthält in der Hilfe einen erfundenen empfohlenen Wert.
- `SAFE_SENTINEL` wird nie als empfohlener Betriebswert bezeichnet.
- `PROFILE_PRESET` wird als Profilwert, nicht als universeller Default bezeichnet.
- Dependency-Links zeigen nur auf existierende Registry-Keys.
- HandbookRefs zeigen nur auf vorhandene, buildseitig verifizierte PDF-Seiten.

### 29.2 Inhalts-Invarianten

Mindestens Tests für:

- Nachtleistung: kein universeller Default, feste statt netzgeregelte Leistung.
- Nachtreserve: Pause der festen Basisentladung; AUTO-Folgepfad korrekt beschrieben.
- Harvest: `REST_SURPLUS_MIN_EXPORT_W` kein gewünschter Restexport.
- Harvest: positiver W-Override übersteuert Ratio.
- Harvest: Floor <= Restart <= Near-Limit.
- `CONTROL_GAIN` Beispiel stimmt mit Codeformel.
- `SMOOTHING_FACTOR` Formel stimmt mit `smooth_transition`.
- Cross-Charge Release-Hysterese korrekt beschrieben.
- Command-Toleranzformel korrekt.
- `COMMAND_EFFECT_MIN_TARGET_W` nicht als Gerätemindestleistung beschrieben.
- Publish nicht als Wirkungsnachweis bezeichnet.

### 29.3 UI-/Browser-Smokes

Desktop mindestens 1440×900; Mobil mindestens 360×800, 390×844, 430×932.

Prüfen:

- Setting-`i` öffnet richtige Hilfe.
- Kategorie-/Abschnitts-`i` funktionieren.
- Modal schließt per X, Escape, Backdrop gemäß Vertrag.
- Fokusmanagement.
- Hintergrundscroll gesperrt.
- kein horizontales Overflow.
- Suche findet Treffer über Synonyme/Helptext.
- Standard findet keine Expert-only Settings.
- Dependency-Link navigiert korrekt.
- Guided „derzeit ohne Wirkung“ reagiert auf Draftänderungen.
- Override-Anzeige Ratio/W aktualisiert sich ohne Speichern.
- Preview-Issue → „Warum?“ öffnet passende Hilfe.
- keine Console-/Page-Errors.

### 29.4 Regression

Vollständiger bestehender Testbestand plus neue V12.12.0-Tests.

Geschützte Dateien müssen byteidentisch zur V12.11.7-Basis bleiben, sofern der Scope nicht vorher explizit erweitert wird:

```text
controller_logic.py
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
measurement_v4.py
measurement_v4_contract.py
```

Auch die Excel-Lernsimulation bleibt unverändert, sofern keine separate Freigabe erfolgt.

---

## 30. Build-/Release-Gate

Für V12.12.0 gelten die üblichen Projektpflichten:

- verifizierte V12.11.7-Basis,
- isoliertes Arbeitsverzeichnis,
- Manifestprüfung,
- Python-/JS-/Shell-/JSON-Syntax,
- vollständige unittest-/pytest-Suite,
- `ResourceWarning=error`,
- neue Registry-/Help-/Browser-Tests,
- No-Regression-Bytevergleich,
- finales ZIP erneut frisch entpacken und daraus prüfen,
- vollständige Änderungsliste,
- SHA256,
- Größe,
- Root-Verzeichnis,
- Version/Build-ID,
- Exit-Gate,
- Installations-/Rollbackbefehle.

Build-PASS ist nicht Feld-PASS. Nach Installation sind mindestens Version, `/health`, `/ready`, Settings-Hilfe, Suche und Guided-Preview real im Browser zu prüfen.

---

## 31. Voraussichtlicher Datei-Scope bei Umsetzung

Voraussichtlich erlaubt/geplant:

```text
settings_registry.py
settings_model.py
settings_validation.py          # nur wenn reine Metadaten-/Issue-Verknüpfung nötig
config_validator.py             # keine neue Regellogik; bestehende Guidance nur referenzieren/ggf. Text bereinigen
static/settings_v2.js
static/settings_v2.css
web_ui.py                       # nur Settings-/Handbuchprojektion falls erforderlich
generated/SETTINGS_REGISTRY_SNAPSHOT.json
README.md
README_INSTALLATION.md
RELEASE_INFO_V12_12_0.md
TECHNICAL_NOTES_V12_12_0.md
BUILD_VALIDATION_V12_12_0.md
ZEC_V12_12_0_RELEASE_REPORT.md
neue Tests
```

Dokumentationsscope:

```text
docs/Zendure_Energy_Controller_Handbuch.docx
docs/Zendure_Energy_Controller_Handbuch.pdf
```

Nicht ohne neue Freigabe:

```text
controller_logic.py
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
measurement_v4.py
measurement_v4_contract.py
```

---

## 32. Umsetzungsreihenfolge

1. Registry-/Help-Datenmodell und Validator für Help-Metadaten.
2. Kategorie-/Section-Metadaten aus `settings_model.py` konsolidieren.
3. BASE-Hilfe für alle 171 operativen Settings.
4. RICH-Hilfe für die 62 priorisierten Settings.
5. statische Guidance-Beziehungen und Override-Semantik.
6. Help-Modal, Category-/Section-Info.
7. Suche erweitern.
8. Preview-/Issue-Verlinkung.
9. Handbuch V12.12.0 aktualisieren und Anchor-Map validieren.
10. Registry-/Content-/UI-/Browser-Tests.
11. vollständige Regression / No-Regression / Release-Gate.

Keine Mikrofreigaben innerhalb dieses Blocks, sobald die Spezifikation als Ganzes freigegeben ist.

---

## 33. Fachliche Abnahmekriterien

V12.12.0 ist fachlich erfüllt, wenn:

1. für jedes operative Setting eine nachvollziehbare Hilfe vorhanden ist;
2. kein Hilfetext alte haus-/anlagenspezifische Pseudodefaults als Empfehlung wiedereinführt;
3. die sieben Prioritätsbereiche ihre wesentlichen Wirkungsrichtungen, Abhängigkeiten und Risiken erklären;
4. Ratio/W-Override-Semantik insbesondere in Harvest sofort verständlich wird;
5. Settings-Suche auch über fachliche Begriffe/Synonyme zuverlässig funktioniert;
6. Guided Configuration wirkungslose/übersteuerte Kombinationen sichtbar macht, ohne Werte automatisch zu ändern;
7. serverseitige Validation weiterhin alleinige authoritative Speichersperre bleibt;
8. das Handbuch im selben Release fachlich zum Settings-Stand passt;
9. Live-Regelalgorithmus und geschützte Command-/Measurementpfade unverändert sind;
10. alle Build-/Regression-/Browser-Gates PASS sind.

---

## 34. Spezifikationsstatus / offene Entscheidungen

Nach der Analyse der V12.11.7-Registry bestehen **keine fachlich zwingenden Einzelentscheidungen**, die vor der Umsetzung settingweise mit dem Nutzer geklärt werden müssen.

Die folgenden Entscheidungen sind in diesem Entwurf bereits festgelegt und sollten bei Freigabe als Makroentscheidung gelten:

- alle 171 operativen Settings erhalten Hilfe;
- 62 priorisierte Settings erhalten RICH-Hilfe;
- keine Laufzeit-KI / kein externer Hilfedienst;
- keine automatischen Konfigurationsänderungen durch Guidance;
- keine neuen Warnschwellen ohne bereits vorhandene Evidenz;
- Handbuchanker nur auf im selben Release aktualisierte/verifizierte Inhalte;
- V3-Legacy-Cleanup bleibt außerhalb V12.12.0;
- geschützte Regler-/Command-/Measurementdateien bleiben unangetastet.

Damit ist V12.12.0 als klar abgegrenzter Implementierungsblock spezifizierbar.

---

## Anhang A – Registry-Inventur

Die vollständige maschinenlesbare Inventur der 171 operativen V12.11.7-Settings liegt separat in:

`V12_12_0_SETTINGS_HELP_INVENTORY.csv`

Enthalten sind pro Setting:

- Kategorie,
- Abschnitt,
- Key,
- UI-Label,
- Sichtbarkeit,
- Typ,
- Risiko,
- Apply-Klasse,
- Default-/Resetklasse,
- Help-Level,
- Abhängigkeitsanzahl,
- Validator-IDs,
- Herkunft der aktuellen Beschreibung,
- aktuelle Beschreibung,
- Validationtext,
- Dependencytext.

