# ZEC – UI, Settings & Diagnostics Contract

**Stand:** 22.09.2026  
**Status:** kanonisch

## 1. Standard/Experte

- Expertenmodus ist Superset des Standardmodus.
- Kritische Warnungen bleiben immer sichtbar.
- Kategorien bleiben fachlich identisch; Expertenmodus ergänzt technische Parameter und Diagnosedetails.
- Kategorien ohne sichtbare Standardfelder zeigen einen erklärenden Empty-State statt leerer Fläche.

### 1.1 Statusseiten-Expertenmodus – Zielvertrag und aktueller Gap

`UI_MODE=standard|expert` ist ein fachlicher Darstellungsvertrag und kein Reglerparameter. Für die Statusseite gilt:

- **Standard:** betriebliche Kerninformationen, Gesundheitszustände, Warnungen und handlungsrelevante Hinweise bleiben klar, kompakt und vollständig.
- **Experte:** dieselben Standardinformationen bleiben erhalten; zusätzlich werden technische Diagnoseebenen zugänglich.
- Expertendetails sollen vorhandene Status-/Diagnosedaten wiederverwenden und keine dritte unabhängige Diagnosewelt oder neue Reglerlogik schaffen.
- Vertiefende Informationen gehören in klar erkennbare Detailflächen bzw. aufklappbare Kontexte statt dauerhaft jede Statuskarte zu überladen. Die konkrete Modal-/Sidepanel-/Inline-Ausprägung ist vor Implementierung responsive und barrierearm festzulegen.
- Geeignete Expertendetails umfassen, soweit für die jeweilige Karte vorhanden und fachlich belastbar: Roh-/Quellstatus, Freshness/Validity und Datenalter, interne Reason-/Limiterinformationen, Sollwertpipeline, Command-Effect-/Readback-/Resync-Zustand, Timing-/Runtime-Diagnose, relevante Ereignisse sowie kontextbezogene Sprünge zu Graph, Analyse oder Settings.
- Secrets, rohe vertrauliche Konfiguration und rein interne Daten ohne stabilen Diagnosevertrag werden nicht durch den Expertenmodus exponiert.
- Ein Wechsel des UI-Modus verändert niemals Controller-/Command-/Safety-Semantik.

**V16.2.4-Stand:** Registry und Helptext führen `UI_MODE`, und die Primärspeicherkarte rendert im Expertenmodus nun einen sichtbaren kompakten Superset-Slice `Strategie & Diagnose` mit Harmonisierung, Harvest/Strategie, diagnostischem usable SOC und Quellenstatus. Die Standardkarte bleibt unverändert schlank. Der vollständige kartenübergreifende Statusseiten-Expertenvertrag ist weiterhin **nur teilweise** umgesetzt. Completion: `ZEC-BL-UI-STATUS-EXPERT-001`.

## 2. SettingsRegistry als UI-Quelle

Die `SettingsRegistry` ist Quelle für Typ, Default, Bereich, Kategorie, Abschnitt, Sichtbarkeit, Apply-/Restart-Semantik und strukturierte Hilfemetadaten.

Die UI darf technische Config-Keys zu logischen Compoundfeldern zusammenfassen, wenn dies fachlich sinnvoll ist. Beispiel: Nachtstart und Nachtende als `HH:MM`-Felder bei intern getrennten Hour-/Minute-Keys.

Produktive Nutzer-/Anlagenwerte dürfen nicht als allgemeine Defaults in Registry oder Hilfe übernommen werden.

Ab V16.2.4 sind zwei Achsen strikt getrennt:

- **Product Surface:** `SurfaceState=operational` erlaubt produktive Exposition; `target_only` bleibt unabhängig von Hardware/Modus verborgen. `release_stage`/`origin` sind nur Provenienz.
- **Applicability:** Ein operatives Setting kann abhängig von aktueller Hardware/Config nicht anwendbar sein. Der Primärspeicher-Aktivierungsschalter bleibt erreichbar; untergeordnete Primärspeicherfelder folgen dem aktuellen Draft des Schalters. Eine 1-/2-Zendure-Topologie darf keine nicht freigegebene zweite Commandkonfiguration erzeugen.

Nichtlegacy-Settings ohne explizite Product-Surface-Klassifikation sind fail-closed zu behandeln. SettingsModel, First-Install-Persistenz und UI verwenden dieselbe Registry-Autorität.

## 3. Strukturierte Hilfe – produktiver Vertrag

Die früher geplante Hilfeerweiterung ist umgesetzt. Registry/UI unterstützen insbesondere:

- Kategorie- und Abschnittshilfe;
- `short_help` und `extended_help`;
- Wirkungs-/Abhängigkeitserklärungen;
- Risiko-/Warnhinweise;
- Rechen-/Formeltexte, wo fachlich erforderlich;
- Handbuchreferenzen und Such-/Navigationsbezug.

Help-Metadaten müssen denselben fachlichen Vertrag wie die SettingsRegistry verwenden und dürfen keine zweite unabhängige Defaultlogik bilden.

## 4. Preview-/Commit-Vertrag

- Bearbeitung erfolgt zunächst als Draft im Browser.
- „Änderungen prüfen“ verwendet Preview-/Validation, nicht Direktcommit.
- Fachlich blockierte Validierung ist ein normaler Previewzustand und wird im Änderungsdialog verständlich dargestellt.
- Blocking Issues markieren betroffene Felder, nennen die Ursache und verhindern Commit.
- Clientvalidierung verbessert UX, ersetzt niemals Servervalidierung.
- Revision-/CAS-Konflikte, Berechtigungsfehler und echte Transport-/Serverfehler werden getrennt behandelt.
- Commit erst nach expliziter Bestätigung.

## 5. Konfigurationsstände / Import / Export – produktiver Vertrag

Benannte Konfigurationsstände sowie Import/Export sind umgesetzt. Es gelten:

- Laden niemals blind sofort aktivieren;
- Inspect/Preview vor Commit;
- Registry-/Schema-Migration, vollständige Validierung und Diff;
- explizite Bestätigung;
- atomisches Speichern und Rollbackvertrag;
- Secrets standardmäßig nicht exportieren;
- CSRF-/Autorisierungs- und SQLite-Härtung beibehalten.

## 6. Responsive Layout

Desktop:

- globale Navigation fix;
- Settings-Toolbar fix;
- linke Kategorienavigation fix bzw. intern scrollbar;
- rechter Contentbereich primär vertikal scrollbar;
- Change-Set-Leiste fix.

Mobil:

- globale Navigation darf intern horizontal scrollbar sein;
- Kategorien-Drawer besitzt eigenen Scrollkontext;
- bei offenem Drawer/Modal kein Scroll-Chaining in den Hintergrund;
- Änderungsmodal intern scrollbar, Aktionen dauerhaft erreichbar;
- der eigentliche Settings-Content darf bei 320/375/390/430 CSS-Pixel **keinen horizontal abgeschnittenen Inhalt** erzeugen. Controls, Einheit, Validierungsfehler, technische Keys, Meta-Pills und Standard/Experte-Umschalter müssen innerhalb des Viewports umbrechen oder in eine mobile Layoutvariante wechseln; horizontales Scrollen oder Pinch-Zoom sind kein Ersatz für responsives Layout;
- als Regression-Gate gilt für den Settings-Content `scrollWidth <= clientWidth` in den unterstützten mobilen Viewportbreiten.

## 7. Primärspeicher-Darstellung und Capability-Diagnostik

- Der Primärspeicher besitzt einen durchgängigen auflösbaren Darstellungsnamen.
- Ein explizit konfigurierter Name hat Vorrang.
- Bei `modbus_template` darf der Template-Default als Fallback dienen.
- Fehlt beides, ist ein neutraler Fallback wie „Primärspeicher“ zu verwenden.
- Für neue Installationen ist der Default von `SECOND_BATTERY_DISPLAY_NAME` leer; vorhandene explizite Nutzerwerte werden nicht umgeschrieben.
- Status-, Settings- und Graphoberflächen sollen denselben aufgelösten Namen verwenden.
- Herstellerneutrale Funktionen und Hilfetexte verwenden „Primärspeicher“; technische Legacy-Keys mit `SMA` bleiben zur Konfigurationskompatibilität bestehen.
- Die SMA-Sunny-Island-Capability `current_discharge_floor_soc` ist read-only und **keine** editierbare Einstellung. Es gibt dafür keinen manuellen Override, keinen On/Off-Schalter und keine benutzerseitige Saisonkurve.
- Status/API/Connection-Test dürfen Capability-Support, Wert, Freshness/Validity, Alter/Quelle und den diagnostischen `primary_usable_soc_percent` anzeigen. Ein Ausfall dieser optionalen Capability darf eine ansonsten gesunde Primärspeicherverbindung nicht allein als ungesund klassifizieren.
- Der diagnostische usable SOC ersetzt in V16.1.0 nicht den realen Roh-SOC für Regler-, FULL/IDLE-, Taper-/High-SOC-, Fast-Capture- oder Safetyentscheidungen.

### 7.1 Gemeinsamer Speicherstatuskarten-Vertrag ab V16.2.1

Für Zendure und Primärspeicher gilt in der Standardansicht derselbe fachliche Kern:

- großer Roh-SOC-Kreis;
- prominent signierte `Istleistung`; das Vorzeichen bleibt sichtbarer Richtungsanker;
- gemeinsame Bezeichnung `Zustand`;
- je nach Leistungsrichtung `Ladegrenze` oder `Entladegrenze`;
- `Noch ladbar` / `Noch entladbar` als **SOC-Prozentpunkte** zur relevanten Grenze;
- bei belastbarer Kapazität zusätzlich die daraus abgeleitete Restenergie in kWh;
- einteiliger Leistungsbalken mit konkreter Leistung gegen die jeweilige Maximalleistung: Laden grün links→rechts, Entladen orange rechts→links; keine zusätzliche Leistungs-Prozentzahl.

Für Restenergie gilt die Datenpriorität: belastbare reale/source-seitige usable/effective Kapazität vor anderen Geräte-/Templatewerten vor manuellem Fallback. Fehlt eine belastbare Kapazität, bleibt die Prozentpunkt-Angabe sichtbar und nur kWh entfällt. Fehlt die zur aktuellen Richtung gehörige Maximalleistung, entfällt nur der Leistungsbalken. Es werden keine scheinpräzisen Ersatzwerte erzeugt.

Für die Karten-Geometrie gilt ab der V16.2.5-Härtung zusätzlich:

- `Noch ladbar` / `Noch entladbar` gehört in die rechte Detailspalte zusammen mit Istleistung, Zustand und Lade-/Entladegrenze; links bleiben SOC-Ring sowie ausreichend lesbare Leistungsbeschriftung und Leistungsbalken;
- die Karte darf keine starre Höhe verwenden, die regulären Inhalt, Leistungsbalken, Footer oder Warnungen überlagert. Eine gemeinsame Mindesthöhe ist zulässig; bei zusätzlichem Inhalt wächst die Karte;
- Leistungsbeschriftung und Restenergie müssen mobil ohne Kleinstschrift lesbar bleiben;
- aktive Command-/Limiter-Warnungen bleiben sichtbar, dürfen die Speicherkarte aber nicht großflächig überdecken. Der Standard ist ein kompakter Warnzustand mit aufklappbarem Langtext; Einklappen darf die Existenz der aktiven Warnung nicht verbergen.

Die intern/API-/Measurement-seitig vorhandene normalisierte Primärspeicher-usable-SOC-Größe bleibt diagnostisch erhalten, wird aber nicht als konkurrierender Prozentwert in der Standardkarte dargestellt. Primärspeicher-spezifische Harmonisierung und Harvest-Rechnung bleiben fachlich erhalten und sind im Expertenkontext zugänglich.

## 8. Administrative Aktionen

Administrative Aktionen sind keine normalen Settings-Änderungen.

Unter `Experte → System & Diagnose → Administrative Aktionen` gehören insbesondere:

- geschützter Controller-Dienstneustart;
- Last-Good-Pointer-Reparatur.

Last-Good-Pointer-Reparatur ändert nicht die Nutzerkonfiguration, sondern Recovery-Metadaten und ist nur nach vollständiger Revalidation/CAS/Audit zulässig.

## 9. Operational Events / Warnungen

- Historische Ereignisse werden nicht gelöscht.
- Ein fachlich behobener Incident wird auf `resolved` gesetzt.
- Live-Warnungszähler zählen nur aktive Warnungsgruppen und bleiben zwischen Header und Eventkarte semantisch konsistent.
- Diagnosetexte müssen aktuellen Fehler von historischem `last_error` unterscheiden können.
- Single-Owner-/Produktivinstanz-Evidenz muss über die relevanten Status-/Readiness-Snapshots konsistent weitergereicht werden. Ein gesund laufender, real gelockter Controller darf im UI nicht allein wegen fehlender Snapshotfelder als `Owner nicht bestätigt` erscheinen; fehlende Ownerdaten müssen umgekehrt weiterhin ehrlich als unbestätigt dargestellt werden.

## 10. Graph-/Diagnosevertrag

Die aktuelle Graphoberfläche basiert auf Graph Core V3 und unterstützt freie/geleitete Ansichten, Zeiträume, Inspector, Command-Follow, Episodentrigger und Episodenvergleich.

- Graph-/Evidence-Status darf Controller-Readiness nicht ersetzen.
- Command-Follow darf zeitliche Folge nicht automatisch als physikalische Kausalität ausgeben.
- Coverage-/Evidence-Badges müssen Datenabdeckung und Belegqualität sichtbar machen.
- Diagnose- und UI-Texte müssen `not_evaluable` von echter Wirksamkeit unterscheiden.
- Bestätigte Coverage-/Evidence-Gaps, Controller-Downtime oder Retention-Lücken dürfen in numerischen Graphserien nicht als gemessene Kontinuität erscheinen. Der Dataset-/Renderpfad muss an echten Lücken ein Break-/Null-Segment erzeugen; es werden keine synthetischen Messwerte zur Überbrückung erzeugt. Normale Sampling-Jittertoleranz darf nicht unnötig in Lücken umklassifiziert werden.


## 11. V16.2.5 – technischer Implementierungsstatus

Der freigegebene V16.2.5-Hotfix ist source-seitig umgesetzt und besitzt TECHNICAL BUILD PASS; die reale V16.2.4 → V16.2.5-Feldabnahme bleibt ausstehend. Umgesetzt sind die Speicherstatuskarten-Geometrie und kompakte Warnungsdarstellung nach Abschnitt 7.1, der mobile Settings-Overflow-Vertrag nach Abschnitt 6, die Single-Owner-Snapshot-Konsistenz nach Abschnitt 9 sowie die renderseitige Gap-Unterbrechung nach Abschnitt 10. Die vollständige Statusseiten-Expertenmodus-Completion bleibt separat unter `ZEC-BL-UI-STATUS-EXPERT-001` offen.
