# Battery Care – nicht installabler Entwicklungsstand CP01

- Fachlich freigegeben: 26.10.2026, `ZEC-BL-BATCARE-001`.
- Baseline: byteverifiziertes V17.1.3 Release, `v17.1.3-20261022`.
- Sourceblock 01: Cross-Charge-Vertrag §3a, historisches Master-Ledger unverlustig fortgeschrieben, reine Battery-Care-Domainfunktion mit Kalender-, Schwellen-, Drei-Stufen-, Vorrang-, Primärtopologie- und PV-Absolutleistungsentscheidungen; isolierte Unit-Tests.
- **NICHT produktiv wirksam**: `battery_care_policy.py` ist absichtlich noch nicht in `run_once`, Registry, UI, Persistenz, Eventstore, Graph oder Gerätepulisher integriert. Netzladung/Notladung bleibt im realen V17.1.3-Regler vollständig unangetastet.
- Vor Installierbarkeit fehlen Gesamtscope, vollständige Regression, Incident und Warnung, Settings Preview/Commit, Command Owner, UI/Graph, UML/Datenblatt-/Releasegates, Realhardware-Feldevidenz. Noch kein technischer Release-PASS.
- Der freigegebene Endvertrag ist `docs/specifications/ZEC_BATTERY_CARE_PRODUKTIONSSPEZIFIKATION_FINAL_20261025.md`; dessen historische Kopfzeile `NO_SOURCE_AUTHORIZATION` bezeichnet den Entstehungszeitpunkt. Aktuelle konkrete Sourcefreigabe im Addendum `05` vom 26.10.2026.

## CP02 – Settings, Registry und sichere Aktivierung

- Sieben neue Settings **innerhalb** `Leistungsgrenzen & SOC-Schutz` / `Battery Care – saisonaler Batterieschutz`.
- Produkt-/Migration-Default ausschließlich `BATTERY_CARE_ENABLED=false`; Saison/Reserve/Schwellen/Leistungscap `null` (keine historischen Beispielwerte).
- Reale Registry-/Import-/Parsing-/Validierungsintegration, SOC-Reihenfolge `E<N<R` mit Mindestabständen 2 Prozentpunkten, zulässige saisonale Kalendergrenzen, gemeinsamer Netzladecap und MAX_SOC-/MAX_CHARGE-Abhängigkeit.
- Aktivierung fordert im vorhandenen Preview-/Commit-Vertrag die ausdrückliche Bestätigung `VAL-BC-002` der möglichen Energieübertragung vom Primärspeicher zur Zendure im Notladefall.
- Bedienhilfen ausdrücklich zu Aus-Wirkung, Primärspeicher, Hersteller-App und Grenzen.
- **Erneut: NICHT INSTALLIERBAR.** Registry/Settings sind noch nicht mit dem realen Controllerverbraucher und der visuellen Settings-Diagnose im gesamten Sollscope verbunden. Kein freigegebenes Produktreleaseschema.

## CP03 – Settings-Regressionsreconciliation

- Die neue Sektion ist nun vollständig in der fehlerschließenden `settings_model`-Help-Matrix erläutert; der gesamte Settings-Model-Import funktioniert.
- Checked-in `generated/SETTINGS_REGISTRY_SNAPSHOT.json` auf 226 Registrierungswerte aktualisiert; 197 operative Einstellungen und 75 Sektionen sind quellen- und testgedeckt. Historische RC19-Defaults im eigenen Basissatz (190 Werte) bleiben separat erhalten.
- Angepasste Bestands-Vertragstests prüfen die additive Erweiterung, ohne alte Funktionen oder ihre vorhandenen Registry-IDs zu entfernen.
- Settings-Testauswahl: 105/105 PASS. Der gesamte V17.1.3-Testbestand und die neue Care-Controller-/UI-/Incident-Integration sind ausdrücklich weiterhin offen.
- CP03 weiterhin **DEVELOPMENT_NOT_INSTALLABLE**.

## CP04 – Persistenter Notlade-Fehler-Incident (Event-Journal-Vorbereitung)

- Die bestehende `OperationalEventJournal`-SQLite-Datenbank wird ohne separaten
  Eventstore genutzt: `event_type=battery_care_emergency_failure`, Warn-`status=open`.
- Ein Vorfall wird ausschließlich über das **zukünftig vom Regler-/Wirkungsmonitor
  ausdrücklich zu liefernde** Ereignis `care_emergency_failure_confirmed=True`
  mit eindeutigem `care_emergency_failure_event_id` und der zum Fehlerzeitpunkt
  gültigen `care_emergency_incident_reserve_soc` geöffnet. ACK, Publish, Status
  oder bloße Sollwerte genügen nicht. Bei fehlender Reserve/ID kein erfundener
  Incident-Wert; die noch zu bauende Controllerintegration muss echte Felder liefern.
- Ein laufender offener Vorfall kann nicht durch UI-, Kalender-, Care-Off-,
  STOP- oder Neustartzustände aufgelöst werden. Die Incident-Reserve bleibt
  gegen spätere Konfigurationssenkungen unverändert. Echte bestätigte Ladung
  bei noch nicht erreichtem R bleibt eine offene Warnung.
- Auflösung nur bei mindestens zwei unabhängig frischen unterschiedlichen
  SOC-Messsequenzen >= gespeichertem Incident-R, über mindestens 3 s;
  monotone Bestätigungen sind pro Prozess neu aufzubauen. Die Historie und
  ursprüngliche Failure-Evidenz bleiben nach Resolve erhalten. Wiederholte
  Level-Flags für dieselbe Fehler-ID öffnen niemals neu.
- Fokussierte neue Tests: **7/7 PASS**, bestehende Event-Regression **8/8 PASS**.
- **Status: SUBSYSTEM_PREPARED / NICHT INSTALLIERBAR.** Die reale Einbindung des
  Command-Effect-/SOC-Sample-Owners, weitere Policy-Sicherheit, grafische Anzeige,
  Monitoring und vollständige V17.1.3-Regression stehen aus. Ein konkreter
  Notlade-Fehler wird bislang vom produktiven Regler **nicht** gemeldet.

## CP05 – V17-Bestandsregression des erweiterten Registryvertrags

- Die erste umfassende `unittest discover`-Regression nach CP04 ergab bei
  951 Tests genau sechs Inventar-/Versions-Fails: 219→226 registrierte
  Settings, 199→206 managed Settings, 57→64 portable Keys, 31→32 aktive
  Boolesche Einstellungen sowie Schema 1.25→1.26. Keine der sechs
  Fehlermeldungen belegte einen Reglerdefekt. Alle Änderungen sind additiv
  durch die sieben neuen Battery-Care-Settings begründet.
- Beim Nachziehen der Booleans zeigte der Qualitätsgate zusätzlich eine
  **echte** fehlende explizite Aus-Wirkung des neuen Enable-Felds. Diese
  ist jetzt in `settings_help.py` im standardisierten `effect_disable`
  mit STOP-/Altverhaltens-/Warnfall-Unterscheidung ausgefüllt.
- Fokussierte Bestandschecks: `test_v17_1_3_help_copy_quality.py` 2/2,
  `test_v12_11_7_default_contract.py` 12/12 und komplette
  Settings-Auswahl 105/105 PASS; ein erneuter kompletter 951-Test-Lauf
  folgt auf den extern gesicherten CP05.
- **NOT_INSTALLABLE**: noch keine Battery-Care-Controllerintegration,
  echte Lade-/Cross-Charge-Funktion, SOC-Graph-/UI-/Incident-Effect-Verdrahtung
  und kein vollständiger Releasegate-PASS.

## CP06 – Dauerhafte SOC-Grenzen in beiden Speicherkarten, ohne Phantom-Primärmaximum

- Beide real dargestellten Speicherkarten zeigen unabhängig von der momentanen
  Lade-/Entladerichtung `Lade-/Entladegrenze` und `X % / Y %`.
- Die Zendure-Karte zeigt die bekannten **ZEC**-Grenzen; eine Care-Reserve
  wird erst nach ausdrücklich gemeldetem real wirksamem Controllerstatus
  (`care_policy_valid` und `care_in_season`) als Entladeboden dargestellt.
  Ein reines aktiviertes Setting gilt bewusst **nicht** als Funktionsnachweis.
- Die Primärspeicher-Karte erfindet keinen oberen SOC-Grenzwert. Ohne eine
  explizit valide frische Geräteobergrenze erscheint `— / 25 %` beziehungsweise
  `— / —` bei unbekanntem Floor. Verbleibende **ladbare** kWh werden ohne
  echte Obergrenze ebenfalls als `—` und nicht aus hypothetischen 100 % berechnet.
- Die bestehende directional remaining-energy-Anzeige und Leistungsbalken
  bleiben separat. Der SOC-Grenzen-Eintrag bleibt auch bei fehlenden
  verbleibenden kWh sichtbar. Kein zusätzlicher Footer oder neue Kartenreihe.
- Fokussierte Pytest-Abnahme 18/18 Tests und 3/3 Subtests **PASS**.
- Noch offen: responsive Geometrie/Desktop-/Mobilvergleich, realer Care-Status
  in der Zendure-Karte, die übrige Graph-/Incident-Integration und Live-Regler.
  **NOT_INSTALLABLE** bleibt unverändert.

## CP07 – Komplette `unittest`-Statusseitenreconciliation

- Erstes gesamtes CP06-`unittest discover`: 954/955 Tests bestanden.
  Der einzige Fehler war ein historischer RC3-Textassert auf das frühere
  Richtungsetikett `Ladegrenze`; die tatsächliche V17.1.3-UI wird nun absichtlich
  und gemäß freigegebenem Auftrag dauerhaft mit `Lade-/Entladegrenze` gerendert.
- Erwarteten UI-Wortlaut in `tests/test_v12_11_2_rc3_status_v2.py`
  korrigiert; keine neue Controllerfunktion und kein anderes UI-Layout.
- Vollständiger Regressionstest nach externem CP07-Checkpoint erneut auszuführen.
- **DEVELOPMENT_NOT_INSTALLABLE** bleibt bestehen.


## CP08 – Saisonale Entladegrenze in AUTO/NIGHT und Deadband-HOLD

- Die freigegebene Care-Reserve R erhöht ausschließlich bei explizit aktiviertem,
  vollständig valide konfiguriertem und lokal kalendarisch wirksamem Battery Care
  den normalen AUTO-/NIGHT-Entladeboden auf `max(MIN_SOC, R)`; höhere vorhandene
  NIGHT-Schutzgrenzen bleiben bestehen. Fehlende und ungültige Schwellen sowie
  deaktivierte/außersaisonale Konfigurationen erhalten den bisherigen Pfad.
- Der bisherige Deadband-HOLD-Zweig darf ein altes aktives Entladekommando bei
  `SOC <= R` nicht mehr halten. Vor Cross-Charge-/Fast-Capture-/Deadband-Dispatch
  wird ein vorhandenes Entladeziel über die **bestehende** SOC-Limit-/Command-
  Neutralisierung beendet. Danach erfolgen keine zyklischen 0-W-Zwangspublishes.
- Im NIGHT-Fenster ist bei `SOC <= R` keine Wiederaufnahme der AUTO-
  Hausverbrauchsentladung erlaubt. Echte PV-Einspeisung wird weiterhin vom
  unveränderten AUTO-Ladezweig verarbeitet; der explizite manuelle STOP und
  alle bestehenden SAFE_STATE-/Freshness-/BMS-Guards bleiben maßgeblich.
- Kein Battery-Care-Netz- oder PV-Sonderladekommando in diesem Block. Die drei
  Care-Ladestufen, Episoden- und Incident-Effect-Verdrahtung, die Status-/Graph-
  Integration und das vollständige Release-Gate stehen weiterhin aus.
- Zielmatrix `tests/test_battery_care_discharge_floor.py` plus bestehende NIGHT-
  und Operation-Priority-Regressions: **26/26 PASS** (fokussiert).
- **DEVELOPMENT_NOT_INSTALLABLE**; vollständige Regression nach externem CP08-
  Bibliothekscheckpoint ausführen. Reale physische Wirkung ist nicht belegt.

## CP09 – Wiederherstellung originaler Unix-Ausführungsrechte

- Der vollständige CP08-`unittest`-Lauf verarbeitete 968 Testfälle und meldete
  **2 Failures**: bestehende Deployment-/Crash-Tool-Shell-Skripte verloren beim
  Python-`ZipFile.extractall()` des CP07-Archivs ihre Unix-Execute-Bits.
  Das waren keine Battery-Care-Regelungstests.
- Die Unix-Permissions wurden anhand der **im CP07-ZIP gespeicherten**
  `ZipInfo.external_attr`-Metadaten für 46 bestehende Dateien restauriert;
  deren Inhaltsbytes blieben unverändert. Bei nachfolgenden Fresh-extract-
  Prüfungen sollen ZIP-Mode-Bits explizit geprüft und wiederhergestellt werden.
- Erneuter vollständiger Regressionstest erst nach unabhängig rückgelesenem
  Vollcheckpoint CP09; Status weiterhin `DEVELOPMENT_NOT_INSTALLABLE`.


## CP10 – Wirksame Care-Grenze in echtem ControllerState/Statussnapshot

- `ControllerState` und `snapshot()` liefern nun `care_policy_valid`,
  `care_in_season`, `care_effective_discharge_floor_soc` **aus dem wirklichen
  Controllerzyklus**. Die CP06-Statuskarten-Funktion benötigt somit keine
  synthetischen Client-Flags mehr, um die geprüfte saisonale Untergrenze
  anzuzeigen. Ein Settings-Enable allein erzeugt keinen Wirkungsstatus.
- Ohne frischen SOC, bei Care-Off, außerhalb Saison, in manuellen festen Modi,
  bei `STOP_HOLD`, Config/MQTT-Frühausstieg und bei `SAFE_STATE` wird keine
  vermeintlich aktive Care-Untergrenze ausgegeben. Ein höheres MIN_SOC bleibt
  in der sichtbaren kombinierten Grenze erhalten. Diese Felder belegen den
  Steuerpolicy-Zweig, **nicht** bereits physische Hardwarewirkung.
- 30 fokussierte Tests (inkl. bestehender SOC-Karten und NIGHT-Fix) PASS.
- Nicht Teil des CP10: echte PV-/Netzpflege-/Notladekommandos, persistentes
  Incident-Effect-Routing, Graphmarker, kompakter Care-Kartenstatus, finales
  Browser-/UML-/Datenblatt-/Release-Gate. `DEVELOPMENT_NOT_INSTALLABLE`.
