# ZEC – UI, Settings & Diagnostics Contract

## AKTUELL – 29.10.2026: endgültige Battery-Care-UI-Freigabe / Diagnosescope

**Nächster ohnehin anstehender Produktrelease: sechs fachlich beschlossene UI-/Diagnoseänderungen (noch NICHT im produktiven V18 umgesetzt).** Die drei älteren verpflichtenden UX-Punkte `ZEC-BL-UI-SETTINGS-LOAD-ROBUST-001` (Antwort-/Schema-Guard, bounded Retry, manuelles Retry, Commit-Safety), `ZEC-BL-BATCARE-SEASON-UX-001` (`TT.MM.` sichtbare Eingabe, persistiert kompatibel `MM-DD`) und `ZEC-BL-PRIMARY-SOC-UPPER-DISPLAY-001` (100-%-initiale, NUR anzeigerelevante Obergrenze für alle Primärprofile, keine BMS-/Reglerwirkung) bleiben vollständig verbindlich.

**`ZEC-BL-BATCARE-STATUS-UX-001` – `SPEC_APPROVED / NEXT_RELEASE_MUST`:** Nutzer entscheidet Variante A ohne farbigen linken Balken. In der regulären Situation farbiges Shield-Check-Symbol + **„Battery Care · Schutz aktiv“**; bei anderen Situationen darf das Präfix „Battery Care“ entfallen, damit der konkrete wichtige Zustand vollständig lesbar bleibt. Nutzer-Funktionsname ausschließlich **„Battery Care“** (kein „Battery Care Mode“). Alle **sechs** realen Statussemantiken erhalten: `Reserve geschützt` (regulärer Schutzstatus), `PV-Vorrang angefordert`, `Netzpflege angefordert`, `Notladung angefordert`, `Derzeit ausgesetzt`, `Ladung nicht wirksam`. Unterschiedliche barrierearm unterstützte Icons/Farben und aussagekräftige Fachtexte; Warnungen, `Wirkung noch nicht bestätigt`, STOP-HOLD/Manuell-Priorität und persistierte Incident-/Readbackdetails niemals durch Ellipsis/Labelersetzung verschlucken. Das **bereits vorhandene blaue Info-Symbol oben rechts in der Zendure-Karte** bleibt der einzige, auffindbare Hilfe-Einstieg: vorhandenen „Zendure / Batterie“-Dialog um kontextabhängigen Battery-Care-Abschnitt mit Grund, Limits, angefordert-vs.-bewiesen, Warnungen und Experteninformationen erweitern. **Kein** zweites Info-Symbol, kein eigener versteckter Touchbereich am Status, keine zusätzliche Kartenhöhe; Mobile (320/375/390/430 px), Standard/Experte, Accessibility und Warnzustände testen. V18-Stand mit Tonstreifen bleibt bis zur Implementierung unverändert.

**`ZEC-BL-BATCARE-RESERVE-EVENT-001` – `SPEC_APPROVED / NEXT_RELEASE_MUST`:** Eigenständiges Betriebsjournalereignis **„Battery Care: Schutzreserve erreicht“** beim erstmalig bestätigten Eintritt in die wirksame Reservebegrenzung. Den SOC, R/effective floor, Limiter `BATTERY_CARE_RESERVE`, neutralisierenden Sollwert/Command-Lifecycle und die spätere echte **Istwirkung** gesondert kenntlich machen: „angefordert“ ist nicht „bestätigt“; bis Bestätigung nicht als vollzogen ausgeben, fehlgeschlagene/späte Wirkung diagnostisch sichtbar. Ereignis-Entprellung/episodenbasierte Deduplikation statt Eintrag je 3-s-Zyklus; Regelung und Command-API nicht ändern. Das Journal zeigt gegenwärtig nur zugehörige AUTO-/HOLD-Wechsel, obwohl Graph-V3 den Care-Grund dokumentiert.

**`ZEC-BL-UI-NIGHT-RESERVE-LABEL-001` – `SPEC_APPROVED / NEXT_RELEASE_MUST`:** Tooltip/Inspector des SOC-Tagesgraphen beschriftet `NIGHT_DISCHARGE_STOP_SOC_PERCENT` verständlich als **„Nachtreserve“**, nicht als generische „Reserve“. Das ist **nicht** R der Battery-Care-Policy; keine Änderung an Zahlen/Regeln/Floor-Rekonstruktion. Beispiel der Nutzeransicht: `Min 15 % · Max 99 % · Nachtreserve 35 %`.

**Feldevidenz:** Der natürliche SOC-R=17-%-Übergang am 29.10.2026 04:50:29 -> 04:50:35 belegt Anforderung und reale 0-W-Istwirkung, nicht die Care-Netzpflege-/Notladung. Siehe `07`, `05` und Evidenzanhang. Die älteren, ausdrücklich offenen A/B- und `DISCUSSION_PENDING`-Nachträge unterhalb dieser datierten Entscheidung bleiben nur Historie.


## AKTUELL – V18.0.0 UX-Feldbefunde und freigegebener nächster UI-Scope, 28.10.2026

- **Settings-Schema-/Verbindungsfehler:** Realer iPhone-Screenshot zeigt `Settings-Modell konnte nicht geladen werden: undefined is not an object (evaluating 'app.model.categories[0]')`. Mobilfunkempfang wurde als mögliche, **nicht gesicherte** Ursache vermutet. Pflicht nächster Produktrelease: Response-/Schema-Vollständigkeit vor Zugriff prüfen, bounded Retry nur bei transienten Fehlern, verständliche Fehlerfläche und direktes erneutes Laden. Fehlende/unvollständige Daten niemals als leere wirksame Settings abspeichern; bestehende unsaved-Changes-/Preview-/Commit-Safety schützen; Techdetails nur diagnostisch. Keine neuen Netzarchitekturmaßnahmen aus dem Screenshot ableiten. `ZEC-BL-UI-SETTINGS-LOAD-ROBUST-001`.
- **Battery-Care-Saisonfelder:** Vorher leere Eingabefelder ohne Formathinweis und intern MM-DD, für deutschsprachigen User schlecht erkennbar. Pflicht nächster Produktrelease: in der Oberfläche **`TT.MM.`** (z. B. `01.10.` und `28.02.`) einschließlich sichtbarer Eingabehilfe/Placeholder und zuverlässiger Eingabevalidierung; Umwandlung zur internen inklusiven jährlich wiederkehrenden **MM-DD**-Semantik ohne Controller-/Persistenzbruch. Ein nativer Datepicker verlangt typischerweise ein Jahr und ist deshalb **keine freigegebene Pflicht**; kalenderfreie Jahr-lose Maske bevorzugt, finalen UI-Vertrag ohne Zusatzaufwand erproben. `ZEC-BL-BATCARE-SEASON-UX-001`.
- **Primärspeicher SOC-Obergrenze:** Eine einheitliche **rein anzeigerelevante** Einstellung `SECOND_BATTERY_DISPLAY_MAX_SOC_PERCENT` (vorgeschlagen, technische Keyfreigabe durch Sourceintegration validieren), Default **100 %**, nutzerdefinierbar, ohne zusätzliche Statuskartenzeile. Die tatsächlich dynamisch per SMA/Primäradapter verfügbare untere Grenze (beobachtet 25 %) bleibt. Der obere Wert wird **nicht** als BMS-Hard-Limit oder echte Ladefreigabe ausgegeben, sondern im Settings-Hilfetext als Anzeige-/Rechenreferenz erklärt. Andere Primärspeicheranbindungen nutzen denselben Fallback; keine neue BMS-/evcc-/MQTT-Anbindung. Keine Auswirkung auf Harvest, Battery Care, Regel-/Command-/Safetygrenzen. Restkapazitäts-kWh nur bei belastbar bekannter Kapazität. `ZEC-BL-PRIMARY-SOC-UPPER-DISPLAY-001`.
- **Battery-Care-Status in Zendure-Karte – Gestaltung OFFEN:** V18 hat spezifisch `.zec-care-compact` (zweizeiliger Text, linker Tonstreifen) in der bestehenden freien Metrics-Fläche, **kein projektweit einheitlicher Statusstreifen-Standard**. Das allgemeine Statusfooter-mit-Statuspunkt-System, der Header-Warning-Chip und Settings-Statusbanner sind **andere** UI-Muster. Nutzer bevorzugt bei Variante A das Shield-Icon und **„Schutz aktiv“**, findet aber auch Variante B attraktiv; zu diskutieren sind hybride Umsetzung, „Battery Care“ vs. **„Battery Care Mode“**, einzeilig/responsive auch für lange wichtige Statusmeldungen, barrierearme Hilfe (eigener Tooltip oder bestehende Kartenhilfe), minimale Kartenhöhe, echte Statuswirkung statt falschem Wirksamkeitsversprechen. Keine vorzeitige Wahl A/B und **keine** stillschweigende Entfernung wichtiger Warn-/Anforderungstexte. Bestehende Stage-Statusnamen aus realem V18-`web_ui.py`: `Reserve geschützt`, `PV-Vorrang angefordert`, `Netzpflege angefordert`, `Notladung angefordert`, `Derzeit ausgesetzt`, `Ladung nicht wirksam`; Details wie `Wirkung noch nicht bestätigt`, `Manueller Modus hat Vorrang`, offene Notladevorfälle müssen erreichbar bleiben. `ZEC-BL-BATCARE-STATUS-UX-001` ist **DISCUSSION_PENDING**, noch keine Produktimplementierung freigegeben.
- **Realfeld positives Verhalten / geschlossen:** STOP-HOLD-Screenshot zeigt 0 W, manuelle STOP-Priorität über Care und Care-Aussetzung; später HOLD-Screenshot Care-Reserve-Status. SOC-Tagesgraph „Care-Details“ zeigt nach Bedienung die Care-Details; Nutzer akzeptiert Button ausdrücklich. `Care-Details`-Button ist **kein** UX-Fix-Auftrag; keine neuen dauerhaften Care-Linien in der Normalansicht erzwingen. Screenshot = begrenzte Status-/UI-Evidenz, kein umfassender physischer Hardwarebeleg.
- **Layout-Schutz:** Keine zusätzliche Höhe allein für Herkunftserklärungen der Primär-SOC-Obergrenze, und beim Battery-Care-Status möglichst kompakte einzeilige Darstellung; keine Cropping-/Ellipsis-Lösung, die schwere Warnungen oder Ladeanforderungssemantik unzugänglich macht. Auf 320/375/390/430 px sowie Desktop/Expert/Standard prüfen. Regler-/Safetyvertrag unverändert.

## AKTUELL – V17.1.3 Umsetzung und allgemeine Feldabnahme 23.10.2026

Die folgenden Abschnitte beschreiben den technischen/qualitativen Zielvertrag und historische noch offene Stufen. Der **neuere Umsetzungstand** ist nun V17.1.3: Settings-Hilfen und dynamische Metatexte wurden erneut überarbeitet, die 31 aktivierbaren Einstellungen erhielten ausdrückliche Nichtaktivierungs-/Aus-Erklärungen, und die Settings-/UI-Regressionssuite sowie das allgemeine Pi-Feldgate bestanden. Dies ist **kein** Nachweis individueller manueller Satz-für-Satz-Abnahme jedes Texts; neu beobachtete UX-Funde bleiben über `05` erfassbar.

Die kompakte Status-Netzkarte verwendet die kurze Minigraph-Erklärung, rechte Achse „Aktuellster Wert“; der eigentliche Minigraph bleibt bei **103 px**. Die synthetische responsive Geometrieprüfung bestand einschließlich Quellen-/Freshness-Zeile ohne Überlauf; bei Standard-Desktopbreite ca. 1280/1769 px wurden 300 px Kartenhöhe erreicht. Die reale Statusseiten-Screenshot-Evidenz vom 23.10.2026 zeigt eine kompakte obere Reihe und sichtbare Quelle. Keine UI-Layoutkorrektur darf künftig die Diagrammhöhe zugunsten von Fließtext reduzieren oder Frische-/Warninformationen beschneiden.

`ZEC-BL-UI-SETTINGS-HELP-001` und `ZEC-BL-UI-STATUS-COMPACT-001` sind technisch umgesetzt und allgemein feldabgenommen; die dauerhaften qualitativen Abnahmekriterien unten bleiben **auch für künftige Änderungen** verbindlich. V17.1.3 ist kein Regler-/Safety-Änderungsrelease.


**Stand:** 21.10.2026 – fachliche UX-Nachprüfung und verbindliche Qualitätskriterien; historische Vorversionen erhalten  
**Status:** kanonisch

## Verbindliche UX-Qualitätsergänzung – Feldbefund 21.10.2026

**Geltungsgrenze:** Reale V17.1.2-Runtime nun installiert mit allgemeinem `FULL_READY`-Feld-PASS. Die folgenden Anforderungen sind **fachliche Abnahmekriterien für einen erst noch freizugebenden Folgescope**, keine Aussage, dass der Produktcode bereits entsprechend überarbeitet oder ein neues Release freigegeben ist. Die zuvor technisch geprüften 190 Hilfen und 74 Bereichserklärungen sind **nicht automatisch qualitativ abgenommen**. Ein nicht genehmigter V17.1.3-UI-Kandidat ist eingefroren; keine Installationsautorität.

### A. Endnutzerverständliche Hilfe für jedes operative Setting

1. **Unterschiedliche Erklärungsebenen:** Bereichs-/Sektionshilfe beschreibt verständlich den *Gesamtzweck*, das Zusammenspiel der vorhandenen Einstellungen, die Bedingungen ihrer Relevanz und wichtige Konflikte. Sie ist kein Fließtext der Optionsliste eines einzelnen Schalters; diese gehört zur **Setting-Hilfe**. Komplexe Bereiche wie Tagesprofile, S3/Saison, Harvest, Fast Capture, Cross-Charge, Command-Recovery und Speicher-/Datenverwaltung dürfen bewusst längere, zusammenhängende Abschnitte erhalten.
2. **Individuelle Feldsemantik:** Jede Hilfe erklärt zuerst Wozu/was beeinflusst wird, dann exakte verfügbare Optionen oder Grenzwerte, **Verhalten bei Aus bzw. Nichtaktivierung**, wirksam/nicht wirksam, Voraussetzungen, Wechselwirkungen, Grenzen, Laufzeitwirkung/Neustart und ggf. nachvollziehbares Beispiel. Angeschaltete Option darf nicht mit physisch garantiertem Geräteseffekt verwechselt werden. Reine Diagnose- oder Speicherungseinstellungen ausdrücklich als solche kennzeichnen. Keine ungesicherten Defaultempfehlungen.
3. **Präzise UI-Namen:** Die Optionen müssen **genau mit den tatsächlichen Dropdown-/Toggle-Labels übereinstimmen**, in verständlichen Texten sichtbar als auswählbare Werte markiert, z. B. **„Aus“**, **„Shadow (nur Diagnose)“**, **„Aktiv“** bei `HARVEST_FAST_CAPTURE_MODE`; bloß `Aus; Shadow; Aktiv` im Fließtext, Fehlübersetzungen oder alte Namen sind nicht ausreichend. Auswahltexte und Metahinweise müssen denselben Vertrag besitzen.
4. **Keine unübersetzten Entwicklerbegriffe:** `FULL_IDLE`, `NEAR_LIMIT`, „Overlaywirkung“, „0-W-Neutralisierung“, „Hysterese“, „klassifizieren“, „Untertracking“, „Lade-/Entlade-Intent“, „Command-Wirksamkeitskontrolle“, „physisch bestätigt“ und ähnliche Wörter dürfen nicht unerläutert als Bedienerhilfe erscheinen. Stattdessen Zweck und beobachtbare Folge in Alltagssprache erläutern; technische Bezeichnungen höchstens **zusätzlich** in Experten-/Diagnosekontexten. Beispiel: „Hysterese“ = unterschiedliche Ein- und Ausschaltschwellen verhindern schnelles ständiges Umschalten. „0-W-Neutralisierung“ = ZEC fordert Leistung null an und prüft anschließend, ob das Gerät tatsächlich nicht mehr lädt/entlädt. `FULL_IDLE` = Primärspeicher voll und lädt praktisch nicht mehr; `NEAR_LIMIT` = fast an seiner Ladeleistungsgrenze.
5. **Linguistische Fachabnahme:** Grammatik, fehlende Verben (z. B. „voll **ist**“), Pronomen/Bezüge, konsistente Großschreibung, klare Einheiten/Zeiträume und Aussagen zur Nichtwirkung müssen in der tatsächlich gerenderten Oberfläche überprüft werden. Feldtexte **und** dynamische Chips/Default-/Sicherheits-/Apply-Hinweise unter Controls gehören in die Prüfung. Formulierungen wie „Aktivierung startet mit Overlay 0“ sind für Anwender durch die tatsächliche Bedeutung zu ersetzen: keine zusätzliche Ladeanforderung unmittelbar nach Aktivierung; schrittweise Erhöhung erst bei geeigneten frischen Messwerten.
6. **Quellen- und Sicherheitswahrheit:** Jede Erklärung wird gegen ihren tatsächlichen Source-Consumer und die SettingsRegistry, S3/Harvest-/Fast-Capture-Vorränge, Anwendbarkeit, Cross-Charge, Geräte- und SOC-Grenzen geprüft. `MAX_POWER_STEP_W` gilt nur für die normale Basis nach Smoothing je Regelzyklus; A400/R100 für die zusätzliche Fast-Capture-Rampe in W/s – kein garantiertes Netto-Plus und keine Empfehlung zur Erhöhung des globalen Steps.
7. **Exit:** Vollständiges Inventar aller aktuellen operativen Settings und Bereiche, prüfbare Zuordnung Feld→Verbraucher→Anzeigeoptionen→Text→Priorität/Nichtwirkung; automatische Vollständigkeits-, Label-, Jargon-Indikator-, Orthographie-/Placeholder-Gates; zusätzlich **manuelle fachliche Qualitätsprüfung in Standard/Experte, mobil und Desktop** mit Negativfällen. Automatische Texttests alleine sind niemals der Nachweis wirklicher Verständlichkeit. Solange offene Qualitätsbefunde bestehen: `FIELD_UX_REOPENED`, nicht `CLOSED`.

### B. Statusseiten-Dichte und Minigraph – eigene Regression

- Bei gleicher Desktopbreite und Messdatenlage dürfen längere Quellen-/Freshness- oder Diagrammerklärungen **nicht die gesamte Kartenzeile unnötig verlängern** und damit SOC-Tagesgraph und folgende Statusbereiche dauerhaft nach unten verschieben. Vorhandene Sichtbarkeit von Quelle, Datenalter, Freshness, Validity und Warnungen darf aber nicht durch starre Höhen, `overflow:hidden`, Überdeckung oder Kleinstschrift erkauft werden.
- Standarddarstellung des kleinen Verlaufs soll kompakt sein: **„Minigraph-Update 3 s · Livewert 1 s“**, vorausgesetzt beide Intervalle entsprechen dem aktuellen realen UI-Abfragevertrag. X-Achse statt „Jetzt“ verständlich als **„Aktuellster Wert“**; Detailsemantik zu 5-/15-Minuten-Rohkurven, 60-Minuten-Minutenwerten, aktuellen unvollständigen Intervallen, Tooltips, Messlücken und von der Livezahl abweichendem Verlauf bleibt über Info-/Tooltip-/Accessible-Text erreichbar. Kein irreführendes Gleichsetzen von Poll- und physischer Samplefrequenz.
- **Doppelte Abnahmedimension:** (1) keine abgeschnittenen Informationen, kein horizontaler Überlauf bei 320/375/390/430 px und langen Quellnamen, 5/15/60 min; (2) auf Desktop u. a. 1280 und ca. 1769 px reproduzierbarer Vorher-/Nachher-Geometrievergleich von Kartenhöhe, Zeilenende und vertikaler Position des SOC-Tagesgraphen mit geeigneter kompakter Referenz. Standard- und Expertenmodus, lange Providertexte, frische/stale Zustände, Schriftvergrößerung und barrierefreie Benennung sind einzubeziehen.
- **Freeze-/Scopegrenze:** CP02 `ZEC_V17_1_3_DEV_CHECKPOINT_02_COMPACT_LAYOUT_20261021.zip` ist extern gesichert, aber `FROZEN / NO_AUTHORIZATION / DEVELOPMENT_NOT_INSTALLABLE`. Seine bisherigen technischen/fokussierten Prüfungen ersetzen weder vollständige visuelle Abnahme noch Releasegates. Ob dieses Material später selektiv verwendet wird, ist Teil der **noch offenen Scopeentscheidung**, keine automatische Weiterentwicklungsfreigabe.
- **Releaseplanung:** Nicht wegen dieses nichtkritischen UX-Findings isoliert einen zusätzlichen produktiven Installations-/Abnahme-/GitHub-Zyklus erzwingen. Inhaltliche Bündelung weiterer vom Nutzer gewünschter Folgethemen **vor** Scopeabschluss und erst danach ausdrückliche Freigabe; keine neuen Controller-/Safetyfunktionen aus dieser UI-Anforderung.


## Neuester UI-/Settings-/Diagnose-Nachtrag – V17.1.2, 21.10.2026

- Aktuelle technische Releasebasis V17.1.2, real installierte Runtime weiterhin V17.1.1. Browser-/Quellvertrag der neuen UI-Funktionen ist im V17.1.2-ZIP getestet, jedoch noch nicht am produktiven Pi feldabgenommen.
- **190 operative Settings:** jede hat eine explizite Wirkungs-/Nichtwirkungs-/Vorrang-/Anwendbarkeitserklärung; 74 Bereichsbeschreibungen sind vorhanden. `MAX_POWER_STEP_W` begrenzt die normale Basis **nach** Glättung je Regelzyklus; Fast Capture A400/R100 regelt den **zusätzlichen** Overlay mit 400 W/s Attack und 100 W/s Release, und nur im zulässigen Active-Fall wird B+O angefordert. Vorrangige Schutz- und physische Limits gelten weiterhin. Keine Garantie eines Nettoleistungsanstiegs; keine Empfehlung, MAX_POWER_STEP_W dafür zu erhöhen.
- **Netzleistungs-Minigraph:** 60-Minuten-Ansicht mit gleicher Zeit-Minuten-Basis, ungemittelte Rohwerte und 5-/15-Minuten-Rohkurven bleiben für Diagnose und ehrliche Tooltips erhalten; Fehlbereiche werden nicht künstlich interpoliert. Frische Livezahl und Chart-Verlaufspunkt ausdrücklich verschieden.
- **Netzquellen-/Freshness-Anzeige:** Mobil-/Desktop-Layout ohne festes Height-Cropping; Firefox-/Safari-Feldwirkung ist noch nicht nachgewiesen. Synthetischer Chromium-Visual-Gate PASS für 320/375/390/430/1280 px × 5/15/60 min inkl. langem Providertext. Reale Pi-/Mobilgeräteabnahme noch offen.
- Die übrigen Standard-/Experten-, Warnings-, Source-Freshness-/Validity- und Control-Invarianten unten bleiben verbindlich.


## 0. V17.1.0 – aktuelle Status-/Freshness- und Minigraph-Semantik

- Reale aktuelle Version `V17.1.0`; die allgemeinen Standard-/Experten- und Warnungsverträge der folgenden Kapitel bleiben unverändert verbindlich.
- **Prominente Livewerte:** Frontend-Read-only-GET `/status-live-data` im Browser **1.000-ms-Intervall**. Live-Werte, echte Quellenfrische, Age, Provider und Validity dürfen niemals allein aus dem Clientpoll als „jede Sekunde neu gemessen“ bezeichnet werden. Normaler `/status-view-data`-Struktursnapshot hat einen eigenen 3.000-ms-Poll; der reale Reglerzyklus wird nicht beschleunigt.
- **Netzleistungs-Minigraph – derzeitige Implementierung:** Frontend-GET `/grid-mini-data` alle **10.000 ms**; im Backend 48 Punkte aus `state.graph_history`, meist Controllerzyklen statt unabhängiger Livegrid-Quellenwerte. Der Benutzer kann darum zeitlich abweichende Anzeige/Chart-Endwerte sehen. Diese Diskrepanz ist **im V17.1.0-Release vorhanden** (Real-Screenshot 20.10.2026) und steht als `ZEC-BL-UI-GRID-MINICHART-001` offen.
- **Verbindliche UX-Härtung für Folgeänderung:** Direkt und dauerhaft am Minigraphen, nicht nur im Infotooltip, die Semantik sichtbar machen, z. B. „Verlauf: letzte 48 Regler-Messpunkte · Aktualisierung alle 10 s“ und den letzten Chartwert eindeutig als *Verlaufspunkt* statt aktueller Grid-Istwert bezeichnen. Die Livezahl bleibt separat „Aktuell (1 s)“. Beschriftung muss bei später geänderter tatsächlicher Kadenz angepasst werden; `10 s` nicht als harte ewige Konstante dokumentieren.
- **Optionales schnelleres Graphdesign separat evaluieren:** für wirklich 1-Hz-korrelierte Kurve echten unabhängigen Grid-Livestream als eigene begrenzte Zeitserie nutzen (bei Reload/Retention/Freshness und Zeitachse definiert); keine 1-Hz-Werte künstlich aus Controller-3-s-Samples ableiten und keine stille Reglerintervallverkürzung. Poll-Änderung allein ersetzt keinen neuen Quellwert.
- **S3:** sichtbare Opt-in-Nichtanwendbarkeit/effektive Strategie, `NOT_APPLICABLE` in HOLD, keine behauptete physische Wirksamkeit ohne natürliche Harvest-Episode.
- **Grid-Stale:** Warnung/Incident mit echter open-/resolved-State-Quelle statt historischer Anzeigeerinnerung; keine lückenfüllende Kurveninterpolation.

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


## 11. Historischer V16.2.5-Implementierungsstand (von V17.1.0 abgelöst)

Der freigegebene V16.2.5-Hotfix ist source-seitig umgesetzt und besitzt TECHNICAL BUILD PASS; die reale V16.2.4 → V16.2.5-Feldabnahme bleibt ausstehend. Umgesetzt sind die Speicherstatuskarten-Geometrie und kompakte Warnungsdarstellung nach Abschnitt 7.1, der mobile Settings-Overflow-Vertrag nach Abschnitt 6, die Single-Owner-Snapshot-Konsistenz nach Abschnitt 9 sowie die renderseitige Gap-Unterbrechung nach Abschnitt 10. Die vollständige Statusseiten-Expertenmodus-Completion bleibt separat unter `ZEC-BL-UI-STATUS-EXPERT-001` offen.
