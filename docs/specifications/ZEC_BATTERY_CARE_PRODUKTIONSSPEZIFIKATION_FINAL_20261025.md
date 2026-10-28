# ZEC Battery Care – finale fachliche Produktionsspezifikation

**Dokumentstand:** 25.10.2026 · **Ledger:** `ZEC-BL-BATCARE-001`  
**Status:** `SPEC_FINAL / FACHLICHER_SCOPE_KONSOLIDIERT / NO_SOURCE_AUTHORIZATION`  
**Verbindliche Produktbasis:** ZEC V17.1.3, Build `v17.1.3-20261022`, Release-Archiv `zendure_controller_v17_1_3.zip`, SHA256 `54b3aa6ee6063bdbf91f428258baca38f6bbdd4a6c5a4c0741159fb7dd5a6d8e`; `controller_logic.py` SHA256 `8bf439456e773aa84097e54059b3da1065deac5200d9304c0dc5960a5e24b1d7`. Reale allgemeine Pi-Feldabnahme vom 23.10.2026: `FULL_READY` / `READY:FULL_READY` / `RELEASE_BACKUP_EXACT` PASS; **Battery Care weder implementiert noch feldgeprüft**.

> **Freigabegrenze:** Der Benutzer hat das fachliche Battery-Care-Konzept inklusive der letzten UI-/Warning-Entscheidung bestätigt und die Erstellung dieser finalen Spezifikation samt externem Checkpoint beauftragt. Dies ist **keine** ausdrückliche Autorisierung zur Sourceänderung oder Freigabe einer produktiven Netzladefunktion. Für Sourceentwicklung ist eine neue explizite Gesamt-Scopefreigabe erforderlich, zuvor die im ZEC-Projekt vorgeschriebene Modell-/Thinking-Prüfung.

## 1. Quellenrangfolge, Zweck, Provenienz

1. `00_ZEC_PROJECT_SOURCE_INDEX.md`, aktuelle kanonische `01`–`07`, insbesondere alleinige Master-Ledger-Autorität `05`, zusätzlich `ZEC_ANALYSE_REGELWERK_V1.1.md` und `ZEC_HARDWARESCHONUNG_REGELWERK_V1.0.md`.
2. Veröffentlichte, SHA256-/ZIP-CRC-verifizierte reale V17.1.3-Sources und ihr `docs/architecture/uml/`-Atlas (22 DOT-Quellen); keine hypothetische zukünftige Runtime als As-built ausgeben.
3. `ZEC_BATCARE_CONCEPT_CHECKPOINT_01_20261025.zip` als gesicherte fachliche Beschlussprovenienz (SHA256 `2133b2863d4167e9d1c89c56bebc31a602b88a302357e5460dd1b6934e9ae177`), `ZEC_BATCARE_PV_UMLENKUNG_QUELLENANALYSE_20261025.md`, ursprünglicher Entwurf vom 23.10., Brainstorming vom 11.08. und die ausdrücklichen Nutzerentscheidungen bis einschließlich 25.10.2026 (Statuskarte, Graph, App-Grenzen, persistent bleibender Notladevorfall).
4. Zendure-Herstellerinformation zu Benutzer-Lade-/Entladegrenzen: https://wiki.zendure.com/de/solarflow-2400-ac-plus/software-setup und App-Handbuch; dies begründet die **Einschränkung**, dass App-/BMS-Grenzen ZEC-Anforderungen begrenzen können. Es belegt **nicht**, dass ZEC diese Herstellergrenzen vollständig auslesen oder überschreiben kann.

**Produktzweck:** Ein für winterliche oder anderweitig ertragsschwache Phasen separat zuschaltbarer, zuverlässiger Schutz vor langem sehr niedrigem Zendure-SOC, mit möglichst geringem Netzbezug, intelligenter PV-Nutzung und Rücksicht auf die Gesamtanlage. Besonders große PV-Anlagen sollen die Funktion abschalten können, um kein unbenötigtes nutzbares Speichervolumen zu reservieren. Ein privates Ein-Nutzer-System, angemessene 80/20-Verhältnismäßigkeit statt unbegrenzter Sonderfalloptimierung.

**Nichtziele:** neuer Hauptbetriebsmodus, zweiter MQTT-/Command-Owner, schreibende SMA-/Primärspeichersteuerung, Ertrags-/SOC-Prognose, separates Adaptive/B2/C1/SOH-Feature, Stromtarifoptimierung, zusätzliches Notlade-Energiebudget, verpflichtende Push-/Mail-/Messenger-Infrastruktur, ungefragte Zendure-App-Konfigurationsänderung. Vorhandene Hardware-/BMS-/Command-/Installer-Schutzinvarianten bleiben maßgeblich.

## 2. Verbindliche Grundpolitik und drei Stufen

**Beispiele 20 / 15 / 12 % dienen ausschließlich der Anschaulichkeit und sind keine freigegebenen Standardwerte.** Für jede Installation sind Reserve `R`, regulärer Nachladetrigger `N` und Notladetrigger `E` explizit, geprüft und in sinnvoller Reihenfolge zu konfigurieren. Eine initiale Installation oder Migration schaltet Battery Care **nicht automatisch** ein.

- Globale Aktivierung: `enabled=false` per Default. Wirksamkeit nur im eigenständigen jährlichen inklusiven Kalenderfenster; S3-Saisonpolitik bleibt unabhängig.
- Im wirksamen Zeitraum gilt für normale AUTO-Entladung sowie feste NIGHT-Entladung **ohne Absenkung bestehender Untergrenzen**: `SOC_discharge_floor_effective = max(MIN_SOC_PERCENT, R)`; weitere höhere explizit aktive Night-/Schutzgrenzen bleiben bestehen. Bei `SOC <= effective_floor` keine erneute reguläre Hausverbrauchsentladung, bestehender Exit-/0-W-Command-/Readbackvertrag gilt. Die Differenzen R→N→E dienen **nicht** als absichtlich nutzbare AUTO-Energie, sondern puffern Eigenverbrauch/Selbstentladung/SOC-Korrekturen.
- **Stufe 1 (PV-Vorrang):** Unter `R` wird vorhandene verlässlich umverteilbare PV-Ladeleistung bevorzugt zur Zendure gelenkt, auch wenn sie aktuell den integrierten Primärspeicher lädt. Nicht nur Netzeinspeisung nutzen; SMA-Ladesockel in dieser Care-PV-Allokation **0 W zulässig**, keine dauerhafte künstliche SMA-Mindestladung. Vorrang endet bei bestätigtem `SOC >= R`; normaler AUTO-/S3-/Harvest-/Export-Capture-Betrieb darf danach Zendure mit PV weiterladen. Keine Anforderung für Sonderladen bei `SOC >= R`.
- **Stufe 2 (reguläre Netzpflege):** Bei bestätigtem `SOC <= N` kontrollierte Ladeepisode **bis R** mit konfigurierbarem moderatem gemeinsamem Netzladeleistungscap, sobald die einfachen, topologiegeeigneten Freigabebedingungen erfüllt sind. Nicht bereits bei N beenden. Kein komplexes opportunistisches Probeladen außerhalb dieser Rahmenbedingungen.
- **Stufe 3 (Notladung):** Bei `SOC <= E` unmittelbare Ladeanforderung **bis R**, ohne neue Bestätigung oder wirtschaftlichen SMA-/Cross-Charge-Gate. Eine mögliche SMA→Zendure-Energieübertragung ist hier als eng begrenzte Ausnahme ausdrücklich in Kauf genommen. Keine zusätzliche kWh-, Zeit-, SOC-Hub-Budgetschranke, die die Notladung vor R beendet. Geräte-, BMS-, Temperatur-, SOC-/Command-Safety und tatsächliche AC-Versorgung dürfen **nicht** ausgehebelt werden. Ein gesendetes Kommando garantiert keine physische Ladung.
- **Manueller STOP:** Ein bewusst ausgelöster `STOP_HOLD` ist absolut und blockiert sämtliche neuen Battery-Care-Ladeanforderungen einschließlich Notladung. Manuell gewählte feste Modi werden nicht heimlich in AUTO umgestellt; ihr Vorrang/deren diagnostisch erkannte Einschränkungen sind in der Status-/Warnlogik transparent. Globale harte BMS-/SOC-Grenzen gelten weiter. Die bestehende manuelle Fixmodussemantik wird nicht stillschweigend erweitert.

## 3. Settings- und Grenzvertrag

### 3.1 Operative Bedienfelder

In der **bereits vorhandenen** Kategorie `Leistungsgrenzen & SOC-Schutz` einen **eigenen Abschnitt** `Battery Care – saisonaler Batterieschutz` schaffen, keine neue Hauptkategorie. Bestehenden `SettingsRegistry`-/Preview-/Commit-/Migration-Vertrag übernehmen; UI- und Servervalidierung konsistent, Server maßgeblich. Vorgesehene **neue**, noch nicht existierende interne Schlüssel (exakte Namen vor Implementation in Registry prüfbar fixieren):

| Schlüssel | Anzeige | Wirkung |
|---|---|---|
| `BATTERY_CARE_ENABLED` | Battery Care aktivieren | Opt-in, `false` Bestands-/Neuinstallation; Aus=keine Care-Policy |
| `BATTERY_CARE_SEASON_START_MM_DD` | Saisonbeginn | jährlich wiederkehrender inklusiver Tag |
| `BATTERY_CARE_SEASON_END_MM_DD` | Saisonende | jährliches Ende, Jahreswechsel möglich |
| `BATTERY_CARE_RESERVE_SOC_PERCENT` | Geschützte Reserve | R: wirksame saisonale AUTO-/NIGHT-Untergrenze, PV-/Netz-Ladeziel |
| `BATTERY_CARE_GRID_TRIGGER_SOC_PERCENT` | Netzpflege ab | N: reguläre Netzladeepisode |
| `BATTERY_CARE_EMERGENCY_SOC_PERCENT` | Notladung ab | E: unmittelbar eskalierender Notlade-Trigger |
| `BATTERY_CARE_GRID_CHARGE_MAX_POWER_W` | Maximale Netzladeleistung | gemeinsamer positiver Power-Cap für Stufe 2/3, zusätzlich zu Hardwarelimits |

Kein zusätzlicher Schalter pro Stufe: die bewusste Aktivierung von Battery Care einschließlich der verständlich offengelegten Nachlade- und Notladefolgen ist die Nutzerentscheidung. Bei alten Konfigurationen dürfen fehlende Care-Schwellen **niemals** über stillschweigende Werte eine automatische Ladefunktion aktivieren. Technisch gültige, aber unvollständige deaktivierte Alt-Konfigurationen bleiben lauffähig; **Aktivierung** erst nach vollständiger expliziter und gültiger Eingabe aller relevanten Werte. Die Beispielwerte R=20/N=15/E=12, Saison 01.11.–28.02. und 300 W sind **keine Defaults**.

### 3.2 Validierung

- SOC-Werte: ganzzahlige Prozentpunkte, `0 <= E < N < R <= MAX_SOC_PERCENT` und innerhalb des vom ZEC unterstützen SOC-Bereichs; zwecks Vermeidung enger Triggerflanken gilt mindestens **2 Prozentpunkte Abstand** `N-E >= 2` und `R-N >= 2` als fachlicher Implementierungsvertrag. Ungültige Vorschau/Commit blockieren, kein stiller Clamp. Größere Abstände sind frei wählbar; SOC-Quantisierung und Wiederholungsbeobachtungen verhindern Oszillation.
- Wenn die normale `MIN_SOC_PERCENT` höher als `R` liegt, gilt ihr höherer Entladeboden weiter; verständlicher Preview-Hinweis, dass Care die Entladung nicht weiter einschränkt. Falls `MAX_SOC_PERCENT` nicht oberhalb R liegt, blockierende Validierung. Die tatsächlichen App-/BMS-Grenzen können abweichen.
- Leistungscap: positiver Wattwert nur im zulässigen ZEC-Geräte-/elektrischen Leistungsbereich; niemals oberhalb der verfügbaren `MAX_CHARGE_POWER_W` bzw. tatsächlichen Ladefreigabe anfordern. Keine ungenutzten Schatten-Settings, keine separate PV-Powercap als zusätzliche Nutzerpflicht.
- Datum `MM-DD`, Start-/Endtag inklusive, Fenster über Jahreswechsel unterstützt, Start=Ende ist ein Kalendertag; 29.02. als Grenzdatum gemäß bestehender S3-Kalenderkonvention **nicht zulässig**, tatsächlicher 29.02. innerhalb eines gültigen Spannenfensters eingeschlossen. Lokalzeit der ZEC-Runtime, sauberer DST-/Mitternachtswechsel, keine zeitbasierten wiederholten Startkommandos.
- Settings-Import/-Export, Draft/Preview/Commit, disable/reenable, Restart, Erstinstallation und Alt-Konfig-Inkompatibilität testen. Der Aktivierungsschalter darf nicht ohne die offengelegte Stufe-3-Cross-Charge-Folge speicherbar sein.

### 3.3 Bedienhilfen / Zendure-App-Wahrheit

Bereichshilfe in verständlichem Deutsch: Zweck, winterlicher Energie-/Eigenverbrauchskompromiss, Auswirkung bei `Aus`, Dreistufenlogik, Saison, Wechselwirkung mit AUTO/NIGHT/S3 und Primärspeicher. Jede Feldhilfe beschreibt reale Wirksamkeit/Nichtwirkung und wohin die Energie fließt; Begriffe nur im Expertenkontext technisch benennen. Dynamische Preview-Zusammenfassung, z. B. für **vom Nutzer gesetzte Beispielwerte**: „Im gewählten Zeitraum wird die Zendure ab 20 % vor weiterer normaler Entladung geschützt. Unterhalb dieser Reserve erhält sie verfügbare Solarenergie bevorzugt. Ab 15 % darf sie bei geeigneten Bedingungen bis 20 % aus dem Netz geladen werden. Bei 12 % fordert ZEC die Ladung auch dann an, wenn hierfür Energie aus einem Primärspeicher stammen kann.“

**Verbindlicher Hinweis:** „Die Zendure-App und die Geräteelektronik können eigene minimale und maximale Ladezustandsgrenzen festlegen. Diese können ZEC-Lade- oder Entladeanforderungen begrenzen. Battery Care ändert diese Einstellungen nicht und kann sie nicht verlässlich übersteuern.“ Wenn App-Limits nicht readbackfähig verfügbar sind, weder behaupten, dass ZEC sie kennt, noch fiktive effektive Werte anzeigen. Bei vermuteter App-Sperre als mögliche Ursache der Nichtwirkung benennen, nicht als bewiesen.

## 4. Policy-, Episoden- und Prioritätsmodell

Ein gemeinsamer **Battery-Care-Policy-/Episode-Owner** innerhalb des bestehenden Controllerpfads; keine neue `MANUAL_MODE`-/Hauptmodus-Ausprägung und keine direkte Gerätepublizierung. Minimaler Zustand: `OFF`, `OUT_OF_SEASON`, `RESERVE_PROTECTED`, `PV_PRIORITY`, `GRID_WAITING`, `GRID_CHARGING`, `EMERGENCY_CHARGING`, `PAUSED_DATA_OR_DEVICE`, `COMPLETED` sowie gesonderter persistenter Warn-Incident. Statuslabel ≠ physische Wirkung; `GRID_CHARGING` bezeichnet nur die tatsächlich nachgewiesene Ladung, sonst `REQUESTED/PENDING` diagnostisch getrennt halten. Stufe 3 hat gegenüber Stufe 2 höhere Eskalationspriorität, `SOC>=R` schließt aktive Ladeepisode mit geeigneter Abschlussbeobachtung.

**Start-/Exit-Kontrakt:** Eintritt und Exit nur mit frischen, voneinander unterscheidbaren SOC-Quellbeobachtungen und monotonic elapsed time; identische MQTT-Daten niemals mehrfach als Bestätigung zählen. Bei E wird ohne unnötige Warte-/Cooldownphase eine sichere Ladeanforderung ausgelöst, die realen Hardware-/Command-Guards bleiben wirksam. Bei Stufe 2 bleibt eine einmal erlaubte, wirksame Nachladeepisode bis R bestehen, ohne periodisch am N-Wert zu toggeln; bei E eskaliert sie in Stufe 3. Bei SOC/R-Zielerreichen wird eigene Zusatzautorität aufgehoben und mit existierenden Richtungs-/Neutralisierungs-/Readbackregeln zur Baseline gewechselt. Kein bloßer Reasonwechsel als physikalischer Moduswechsel.

**Restart:** Persistenz nur für aktive Episode/Intention, Eskalation, unveränderte Settings-/Saison-Provenienz und nicht behobenen Warn-Incident; kein persistenter per-Zyklus-Geräte-Sollwert. Nach Neustart frische Daten, wirksame Konfiguration und Command-State neu prüfen, dann Episode rekonstruieren; keine blinde alte Ladung senden. Warnvorfall übersteht Neustart, Konfigänderung, Saisonende und UI-Quittierung. Nach Saisonende **keine neue normale Care-Episode**; eine bereits aktive Notladeepisode darf bis R fortgeführt werden (sonstige alte Care-Allokation endet mit definierter Rückgabe zur normalen Regelung). Ein ausdrückliches Ausschalten des Schalters beendet Care-Kommandos; ein bereits offener ungelöster Warnvorfall bleibt erkennbar. Manueller STOP bricht aktive Care-Kommandos ab, Vorfall bleibt erhalten.

**Safety-Arbitration:** harte Daten-/Geräte-/BMS-/Command-Schutzfunktionen > manueller STOP > zulässige Care-Notladungs-/Netz-/PV-Stufen > normale AUTO-/S3-/Harvest-Priorisierung für umverteilbare Energie. Eine tatsächlich wirksame höhere allgemeine Entladegrenze wird durch keine Care-Regel abgesenkt. NIGHT-Festentladung bei effektiver Reserve stoppen, AUTO im Night-Fenster darf diese Reserve nicht erneut entladen. Manueller Fixmodus bleibt bestehende explizite Benutzervorgabe; offenlegen, wenn deshalb Care keine Ladeautorität hat; nie falschen „geschützt“-Status zeigen, wenn dessen Wirkung nicht durchsetzbar ist.

## 5. Stufe 1 – PV-Umlenkung ohne SMA-Sockel

### 5.1 Energiebezugsrahmen und Delta-/Absolutsemantik

In ZEC: `G>0` = Netzimport, `G<0` = Export; `Pp>0` = **tatsächlich gemessene** integrierte Primärspeicherladung, `Pp<0` = Primärentladung; `Pz>0` = **unabhängig physisch beobachtete** Zendure-Ladung. Weder gewünschte Richtung noch Command-Zielwert dürfen die Ist-Richtung zirkulär bestätigen. Für hinreichend korrelierte, gültige und frische AC-Leistungsreferenzen:

```
Pp_charge = max(0, Pp)
Pz_charge = max(0, Pz)
T = max(0, Pp_charge + Pz_charge - G)   # ABSOLUTE Bilanzschätzung
Z_care_abs = clamp(T, 0, allowed_zendure_charge_limit)
```

**Kein Harvest-SMA-Ladesockel**, Residualfloor 0 W für die Care-Strategie; vorhandene physischen Rampen, reale Import-/Cross-Charge-Beobachtung und Geräte-Limits sind die Rücksicherung. `T` ist kein neuer perfekter PV-Sensor: zeitversetzte Quellen und Wandlerverluste sind zu beachten; bei frischem belegtem SMA-**Netzladen** (z. B. `Pp=+600`, `G=+600`, `Pz=0`) ist `T=0`, also keine irrtümliche PV-Umlenkung.

**Absoluter Zielwert:** `Pz` ist bereits enthalten; `last_input_power` und Export nicht ein zweites Mal addieren. ZECs bereits existierende `HARVEST_PRIMARY_CHARGE_FLOOR_RATIO/W`-Strategie dient als Methodikvorbild, aber keine funktional unpassende Vergewaltigung der bisherigen Harvest-API. Implementierungsentscheidung rein technisch: bestehende Hilfsfunktionen wiederverwenden, wo ihre Semantik passt; ansonsten isolierter kleiner Care-Kandidat. **Ein** gemeinsamer finaler Command-Owner.

### 5.2 Ein-/Ausgangskontrolle, tatsächliche Physik

Nur bei `enabled && in_season && SOC<R`, geeignetem AUTO-Pfad, ausreichender SOC-/Grid-/Zendure-Ist-/Primärleistungs-Frische und tatsächlich plausibler Ladeleistung. Keine High-SMA-SOC-Schwelle für den Care-Vorrang. Im Deadband muss der Care-Pfad überhaupt erreichbar sein (`run_once()` heute sonst `handle_deadband()`), ebenso bei ansonsten `low_surplus` in `handle_charge()`. In Zendure-only-Konfiguration keine angenommene unsichtbare Primärladung; regulärer Export Capture bleibt wirksam.

Bei 900 W SMA-Ladung und ca. 0 W Netzfluss ist bis zu ~900 W Zendure-Ziel **zulässig**, schrittweise per bereits bewährter Limit-/Smoothing-/Power-Step-Semantik. Ein fixes „690 W bleiben immer beim SMA“ ist für Care ausgeschlossen. Während der Übernahme muss physische SMA-Ladung zurückgehen; kurze Überlagerung/Netzimport oder Gegenladung sind vertretbar. **Anhaltenden unerwünschten zusätzlichen Netzimport aktiv zurückregeln**, nicht allein der absoluten Bilanz `T` vertrauen. Besonders wichtig: `Pp=+900, Pz=+900, G=+900` ergibt rechnerisch weiter `T=900` – ohne zusätzlichen Rohimport-/Reaktions-Guard würde der Regler Netzbezug halten. Deshalb:

1. Positive Zielerhöhung nur nach neuen unabhängigen frischen Proben mit plausibel vorhandener umverteilbarer Ladung/Export; kontrollierte moderat ansteigende Rampe ohne aggressives Fast-Capture-A400-Doppeltuning.
2. Frischen Roh-Netzimport vor der Glättung für schnelle Gegenreaktion benutzen. Bei deutlichem/persistierendem Import wird **nur der zusätzliche Care-PV-Anteil** schneller begrenzt und nötigenfalls pausiert; auf neue passende Energiebilanz warten, nicht unmittelbar identisch neu angreifen. Bestehende normale Export-Capture-/Safetyfunktion wird dadurch nicht fälschlich auf 0 gesetzt.
3. Bei Primärentladung/stale Daten/richtungsunklarer Zendure-AC-Wirkung keine neue strategische Care-PV-Umlenkung; wirksame höhere Entladegrenze bleibt erhalten. Kein direkter SMA-Schreib-/Pollpfad.
4. Kein unnötiger `acMode`-Wechsel, 0-W-Zwischenzustand, Richtungs-Ping-Pong oder zyklusweises Wiederholungspublish.
5. Soll-Ist- und Energiekonvergenz anhand unabhängiger Quelle, Ziel, Gerät-Ist und Netz-/Primärreaktion beweisen; nicht aus einem positiven Softwareziel Wirkung ableiten.

**Fast Capture und Harvest:** Bei aktivem Care-PV-Absolutziel darf derselbe bereits allokierte Export nicht nochmals in `B + Fast_O` erscheinen; den Fast-Overlay entsprechend unterdrücken/ablösen und diagnostisch nachvollziehen. Normales AUTO-/S3-Baseline-Signal getrennt von Care-Kandidat und Fast-Anteil halten, damit Care beim `SOC>=R` nicht durch gespeicherte `last_input_power` in die Folgeregelung einsickert. Bei Care-Abschaltung/Exit normale Fast-Capture- und S3-Logik unverändert wiederherstellen. Keine dauerhafte Änderung bestehender globaler Harvest-/Fast-Konfigwerte.

## 6. Stufe 2 und 3 – Netzladefreigabe nach Anlagentopologie

| Tatsächliche ZEC-Topologie/Quellenlage | Stufe 1 | Stufe 2 ab N | Stufe 3 ab E |
|---|---|---|---|
| Zendure ohne Primärspeicher | vorhandener PV-Export via normale Aufnahme | Netzpflege ohne Primärfloor erlaubt | sofortige sichere Ladung bis R |
| Eingebundener SMA Sunny Island, frische Floor-Capability `current_discharge_floor_soc` (Register `31009`) | SMA-PV-Ladung bis 0 W strategisch umlenkbar | bevorzugt bei `SMA_SOC <= saisonaler Entladeboden` und beobachteter Nichtentladung; sonst warten | kein Floor-/SMA-/Cross-Charge-Wirtschaftsgate |
| Eingebundener nicht-SMA-Primärspeicher, Leistungs- aber keine Floor-Capability | tragfähige AC-Referenz erforderlich | einfaches neutrales/ladefähiges, nicht entladendes Primärfenster; keine Sonderprobeladungen | laden, auch bei fehlender Primärinformation |
| Physisch vorhandener, in ZEC absichtlich nicht integrierter Primärspeicher | keine erfundene Allokation; realen Export nutzen | Netzladung zulassen; mögliche fremde Speicherenergie wird als Nutzerkonsequenz akzeptiert | laden |
| Eingebundener Primärspeicher mit stale/invaliden Messwerten | keine neue PV-Umlenkung | pausieren (außer bereits gesicherte eindeutige Zendure-only-Situation) | laden, sofern Zendure/Gerät und AC sicher |
| Zendure-Telemetrie/AC-/Command-State unsicher, BMS-Ladefreigabe fehlt | keine zusätzliche Ladung | keine aktive unsichere Ladung | keine unmögliche/unsichere Ladung vortäuschen, persistente Warnung |

Nur **eine** begrenzte `grid_charge_power_cap_w`-Anforderung für beide Netzstufen, bis R. Anforderung gemäß bestehendem SmartMode-/Input-/Output-/AC-Mode- und Full-State-Readbackvertrag über `_publish_signed_target` und Recovery, keine direkte „Notfall-MQTT“-Abkürzung. Netzbezug in Stufe 2/3 ist **beabsichtigt**, daher gerade **nicht** durch die PV-Import-Rücknahmeregel aus §5 zu neutralisieren. In Stufe 3 nur die **wirtschaftliche Cross-Charge-Vetoentscheidung** ausnehmen; alle tatsächlichen Sicherheitsprüfungen bleiben. Kein unbegrenztes Kommandoflut- oder Restart-Loop-Verhalten.

**Begrenzung der Garantiesprache:** Hersteller-App-/Geräte-SOC und BMS können Ladung sperren; fehlende Versorgung, fehlende Ladeannahme und Hardwaretemperaturlimits sind nicht softwareseitig „zwingend“ überwindbar. Bei Nichtwirkung persistente aktive Incident-Warnung statt fiktivem Erfolgsstatus.

## 7. Statusseite, Karten und SOC-Graph

### 7.1 Zendure-Statuskarte

**Keinen neuen Footer und keine zusätzliche Kartenreihe.** Battery-Care-Kurzstatus in den vom Nutzer im realen V17.1.3-Mobilscreenshot rechts unter den bisherigen Kennwerten markierten freien Bereich, maximal kompakt ein Statusstatement und bei Platz eine kurze Zielzeile, responsiv ohne Abschneiden, Überlauf oder Vergrößerung der gesamten oberen Kartenreihe. Beispiele: `Battery Care · Reserve geschützt`, `PV-Vorrang`, `Wartet auf PV`, `Netzpflege`, `Notladung`, `Ladung nicht wirksam`. Nur anzeigen, wenn aktiviertes **Kalenderfenster** derzeit gilt oder eine außerhalb des Fensters fortgeführte Notladeepisode noch läuft; **Ausnahme:** ungelöste Battery-Care-Sicherheitswarnung bleibt sichtbar, auch außerhalb des Fensters, bei manuellem STOP oder nach Deaktivierung. Ein global aktivierter, aber aktuell außersaisonaler Schalter erzeugt **keine** permanente normale Statuskartenanzeige. Produktive Statuswerte niemals allein aus Client-Polling als neue Messung darstellen.

### 7.2 Beide Speicherkarten – allgemeiner, Battery-Care-unabhängiger UI-Auftrag

Das bisher bedarfsabhängige `Entladegrenze ...` durch **dauerhaft sichtbares** `Lade-/Entladegrenze   X % / Y %` ersetzen – bei Zendure **und** bei jeder tatsächlich dargestellten Primärspeicherkarte, unabhängig von momentaner Lade-/Entladerichtung. X und Y müssen aus **für das jeweilige Gerät bekannten und semantisch gültigen** oberen/unteren SOC-Grenzen stammen. Bei Zendure ist die Care-effektive **ZEC-Entladegrenze** im Saisonfenster zu zeigen, sonst die normale ZEC-Grenze; bei Kenntnis exakter App-/BMS-Grenzen dürfen diese erklärt, aber niemals erfunden werden. Bei SMA/anderen Primärspeichern **keine fiktive obere Ladegrenze (z. B. 99 %)** anzeigen, falls nur Roh-SOC oder eine Entladefloor-Capability verfügbar ist: `— % / <bekannte Untergrenze>` beziehungsweise `— / —` bei unbekannten Werten plus verständlicher Info-/Expertentext zu Quelle und Gültigkeit. Ob die Untergrenze ein saisonaler SMA-Eigenverbrauchs-Floor und **nicht** BMS-Hardlimit ist, ausdrücklich kennzeichnen. Kein unzutreffender „gleicher Max-SOC für beide Speicher“.

Bestehender SOC-Kreis, Istleistung, Zustand, `Noch entladbar/ladbar`, Telemetrie/Freshness-Zeile und Info-Popover bleiben erhalten. 320/375/390/430/1280/1769 px und Standard/Experte regressionsprüfen; keine Diagrammhöhe/Informationen opfern, um Text unterzubringen.

### 7.3 Operational Events, Warnchips und Graph

Ereignisse nur an bedeutenden Übergängen (Debounce/Dedupe, kein 3-s-Spam): Feature/Saison, Reserve aktiv, PV-Vorrang Start/Ende, Netzpflege Start/Ende, Notladung Start/Ende, Ladeanforderung nicht wirksam, Wiederherstellung, Abbruch/STOP/Configänderung. Farbliche Hervorhebung: normale Schutz-/PV-/Netzpflegeinformation dezent positiv, Notladung auffällig aber **nicht automatisch Fehlermeldung**, unbehobene Wirkungslosigkeit echte Warnfarbe. Bestehendes Warning-Chip/Popover bzw. mobiles Bottom-Sheet nutzen, kein Push/Mail.

SOC-Tagesgraph: normale Ansicht maximal eine dezente **wirksame Zendure-Entladegrenzenlinie** mit zutreffender Beschriftung, Expertenansicht zusätzlich N/E-Schwellen und Episode-/Ereignismarker. Care-spezifische Linien nur für tatsächlich im dargestellten Zeitraum wirksame Kalender-/Fortführungsepisoden, nicht ganzjährig wegen bloß `enabled=true`. Historische Linien/Marker nutzen damals gültige Config-/Saisongültigkeit (nicht nachträglich heutige Schwellen auf alte Tage projizieren). Sichtbarer Verlauf und Gerätereadback jeweils zeitlich wahrheitsgemäß; Messlücken nicht interpolieren, keine zusätzliche 1-Hz-Controller-/Pi-Messlast.

## 8. Persistenter Notladefehler – verbindlicher Incident-Vertrag

**Kernentscheidung 25.10.2026:** Wenn Notladung angefordert wird, aber nach vorhandener angemessener Command-/Wirkungsfrist nicht physisch wirksam wird oder mit bestehender Recovery dauerhaft nicht funktioniert, **persistenten ungelösten Sicherheitswarnvorfall** öffnen. Ein MQTT-Publish, ACK, Kommandoreadback oder kurze positive Istladung ist **kein** Nachweis wiederhergestellter Reserve.

- **Sichtbar offen lassen** über Controllerrestart, UI-Schließen/Quittieren, erneute Ladeversuche, vorübergehende Ladung, Saisonende, manuelles Care-Off und ausdrücklichen STOP hinweg. Popover-Schließen bedeutet nur „gelesen“, niemals „resolved“. Farbe und aufklappbare Detailanzeige konsistent mit bestehendem UI-Warnvertrag.
- **Automatisch erst dann schließen**, wenn ein frischer, valider Zendure-SOC `>=` der beim Incident maßgeblichen geschützten Battery-Care-Reserve `R` mit mehreren **distinct** Beobachtungen stabil bestätigt wird (nicht zwingend `R+1` wegen ganzzahliger SOC-Ablesung). Konfigurationssenkung, Default-/Saisonwechsel und ein einzelner SOC-Sprung dürfen einen offenen Vorfall nicht künstlich beseitigen. Die beim Incident gespeicherte Schutzreserve ist die Recovery-Referenz; Konfig-/Zieländerungen werden im Vorfall dokumentiert und dürfen nicht zum stillen Löschen führen.
- Liegt bestätigte physische Ladung wieder an, SOC aber noch unter R: im Vorfalltext `Ladung wiederhergestellt – Schutzreserve noch nicht erreicht`; Warnchip bleibt aktiv bis Zielerreichung.
- Besteht darüber hinaus ein **separater Geräte-/Commandfehler** fort, bleibt dessen eigenständige Warnung auch nach SOC-Recovery bestehen; Battery-Care-Incident kann dann mit dokumentiertem SOC-Nachweis abgeschlossen werden, ohne andere Fehler fälschlich zu schließen.
- Unfrischer SOC macht Recovery **nicht bewertbar**, niemals automatisch erfolgreich. Keine Zeit- oder Auto-Acknowledge-TTL. Historisches Start-/Retry-/Wirksamkeits-/Ziel-/Resolve-Protokoll auch nach Schließen erhalten; im Incident u. a. Zeitpunkt, Episode, damaliges R, niedrigster beobachteter SOC, ursprünglicher Failure-Grund, letzte bestätigte Wirkung, Resolve-Zeitpunkt.
- Beispieltexte: `Battery Care: Notladung nicht erfolgreich`, `Schutzreserve noch nicht wiederhergestellt`, `Letzte Ladeanforderung nicht wirksam`; **keine** Verschleierung mit `System OK`, wenn ein ungelöster Care-Warnvorfall besteht. Kein zweiter Eventstore, wenn bestehende persistente Event-/Incident-Infrastruktur ausreichend ist.

## 9. V17.1.3 Sourceintegration und Release-UML

Quellgenaue Eintrittsstellen aus verifiziertem V17.1.3-Archiv (Sollintegrationslandkarte, **nicht** bereits umgesetzt):

| Source | Bedeutung / Pflichtänderungswirkung |
|---|---|
| `controller_logic.py:833+ run_once` | Policy/Reserve vor NIGHT- und AUTO-Dispatch; Care-Ladepfad auch im Deadband erreichbar; manuelle/STOP- und Safe-State-Vorränge |
| `:4334+ handle_night_mode`, `:4373+ handle_discharge` | effektiver max(MIN_SOC,R)-Floor, korrekter neutralisierender Exit auch während NIGHT |
| `:4437+ handle_charge` | Care-Absolute-PV-Kandidat neben Baseline, S3/Harvest/Fast-Isolation und Side-Effects/Power Limits |
| `:3793+ _rest_surplus_charge_pressure_target`, `:3705+ _harvest_physical_reference` | Vorbild physische, absolute Leistungsbilanz/Confidence; Care-SMA-Floor **nicht** übernehmen |
| `:1594+ _apply_symmetric_cross_charge_limit` | PV-/Stufe-2-Schutz und eng spezifizierte Stufe-3-Ausnahme; gewöhnliche Cross-Charge-Invariante unverändert außerhalb dieser Ausnahme |
| `:2174+ _publish_signed_target` | zentraler SmartMode-/AC-/Limits-/Full-State-/Readback-/Effect-/Recovery-Owner |
| `settings_registry.py`, `settings_validation.py`, `config.example.json` | echte operative Settings und UX-Texte, Validierung, sichere Migration/default-off, kein TARGET_ONLY-Scheinsetting |
| `web_ui.py`, `static/status_v2.js`, Templates/CSS, Graph-/Event-/Measurement-Pfade | kompakte Anzeigen in beiden Speicherkarten, Notlade-Warning-Persistenz, Historie, Expertenindikatoren und responsive Prüfung |
| `docs/architecture/uml/` und `docs/architecture/` | 22-blättriger V17.1.3-As-built-Regleratlas: neue relevante Control-/Safety-/Status-Traceability + aktualisierte SVG/PNG, Manifest, Review-Matrix, Index; nicht betroffene Blätter mit `REVIEWED_UNCHANGED` |

Vor Sourceentwicklung die **explizite Ausnahme zum bislang pauschalen Cross-Charge-Verbot** in `03_ZEC_CONTROL_AND_SAFETY_INVARIANTS.md` und den entsprechenden Ledger-/Releasevertrag als kontrolliertes fachliches Delta fortschreiben; Master-Ledger `05` bleibt einzige Autorität, kein Ersetzen durch diese Spezifikation. `BACKLOG_NO_DROP_GATE` vor Entfernen/Archivieren historischer Quellen. Reale Sources/Tests müssen bestimmen, ob die Strategie baulich aus vorhandenen Harvest-Hilfsfunktionen oder sauberer separater Care-Funktion umgesetzt wird – **Methodikreuse, keine erzwungene Codekopplung**.

## 10. Mess-/Diagnose- und physischer Wirkungsnachweis

Additive strukturierte Datenfelder/Events (exakte Namen im Sourceblock festzulegen, keine fiktiven V17.1.3-Felder): `care_enabled`, `care_in_season`, `care_config_revision`, `care_stage`, `care_episode_id`, `care_R/N/E`, `effective_zendure_discharge_floor`, `care_soc_fresh`, `primary_floor_capability_valid`, `primary_power_w`, `zendure_physical_power_w`, `raw_grid_power_w`, `normal_baseline_w`, `care_absolute_candidate_w`, `care_import_backoff_w`, `care_final_command_w`, `care_command_readback_status`, `care_physical_effect_category`, `care_pv_shift_applicability`, `care_reason`, `care_emergency_incident_open`, `care_emergency_incident_recovery_target_soc`, `care_incident_resolved_at`.

Vier Nachweise **getrennt** für jede Stufe (Norm `ZEC_ANALYSE_REGELWERK_V1.1`): (1) Zustand/Entry/Hysterese/Exit, (2) mathematische absolute Zielwertbildung/Leistungsbilanz mit Vorzeichen und Limits, (3) real gemessene Zendure-/Primär-/Grid-/SOC-Wirkung, (4) Readback-/Mismatch-/Neutralisierungs-/Resync-/Recovery-Verhalten. Kein `effective`, wenn nur Publish/ACK vorliegt. Bei `0 W` tatsächliche Neutralisierung messen. Energie/SOC über Zeit plausibilisieren; große SOC-Sprünge/mehrdeutige Messrichtungen kennzeichnen, nicht wegmitteln. Baseline vs. Care-Variante vergleichen: unnötiger Import, Richtungstransitionen, AC-mode-Änderungen, 0-W-Batches, Mismatch-Resyncs, SoC-Hub, zusätzliche kWh, Temperatur- und Command-Volumen. Kein erfundener Verschleiß durch jede MQTT-Nachricht; geräteseitiges Flash/Relais nur mit Evidenz behaupten.

## 11. Verbindliche Test-/Feldabnahmematrix

1. **Default-/Migration-Differential:** disabled und out-of-season bit-/fachlich identische AUTO/HOLD/NIGHT/FIXED/STOP-, S3/Harvest/Fast-/Cross-Charge-Commandausgänge wie V17.1.3; frische und fehlende Settings, Import/Preview/Commit, Restart, 29.02./31.12./01.01., Zeitzonengrenze/DST.
2. **SOC-/Timer-Boundaries:** E±1,N±1,R±1, Mindestabstände 2 pp und ungültige/gleiche Schwellen, normale MIN_SOC über/unter R, MAX_SOC, stales/replayed SOC, multiple distinct samples, Nachtreserve-/NIGHT→AUTO-Transition, Soll/Ist getrennt.
3. **Stufe 1:** 900→0-W-Pp↔0→900-W-Pz im Deadband, 200-W-PV-Abfall, Netzbezug trotz unveränderter SMA-Ladung, Primärnachtladung 600 W aus 600 W Grid, gemischter Export/High-SOC/S3, Fast Active/Shadow/off, frische/alte AC-Richtung, Cross-Charge optional aus, Zendure-only, nach Exit kein Baseline-Leck oder zweiter Export-Overlay.
4. **Stufe 2:** Sunny Island an/über Floor und echte 0-W-/Entladesignale, primär ohne Floor, kein Primärspeicher, absichtlich nicht integriert, Datenstale, Netzladungs-Wirkung, Wiederanlauf/Hold bis R; keine künstliche Triggerflanken-Oszillation.
5. **Stufe 3:** E-Entry sofort (abgesehen von bestehenden Safe-/Command-Gates); akzeptierte SMA→Zendure-Episode auch bei gesperrtem optionalen allgemeinen Cross-Chargepfad; bis R statt bloß E oder N; manueller STOP beendet Kommando, keine BMS- oder SmartMode-Umgehung; kein Full-State-Publish-Sturm; Recovery bei nicht umgesetztem Kommando.
6. **Warn-Incident:** kein Laden/kein Wirkungseffekt; persistent durch Neustart, Saisonende, Browserquittung, Care-Off, STOP und neuen Ladeversuch; bei partieller SOC-Erholung weiterhin offen; erst frischer mehrfach bestätigter SOC `>= Incident-R` resolve; parallel bestehende Commandfehler bleiben separat; historischer Audit-Eintrag immer erhalten.
7. **UI/Graph:** beide Speicherkarten `Lade-/Entladegrenze`, Primary upper unbekannt=`—`, dynamischer ZEC-Floor, Care-Status im markierten freien rechten Bereich, keine zusätzliche Footerhöhe, warn popover mobil/Desktop, Farbdifferenzierung, nur saisonal aktive Linien/Markers mit historischer Config, 320/375/390/430/1280/1769 px, Status 1-Hz-Poll ≠ neue Samplefrequenz.
8. **QA/Release:** sämtliche projektspezifischen Tests normal + `ResourceWarning=error`, Controller- und Command-Regression, Browser-Smokes, Langzeit-Pi-Budget, No-Drop-/UML-/As-built-/Datenblatt-/Installer-/Manifest-/Source-Freeze-/Checkpoint-Library-/Fresh-Extract-/Release-Library-Gates. Kein künstlicher Echtfeld-PASS bei ausbleibender natürlicher PV-/Notladeepisode: `NOT_EVALUABLE` kennzeichnen. Nur nötige begrenzte reale Pi-Tests und nach ausdrücklicher Implementierungs- und Installationsfreigabe.

## 12. No-Drop-, Status- und Übergabevertrag

- Diese Spezifikation ersetzt **inhaltlich** den überholten frühen Battery-Care-Entwurf vom 23.10., **löscht ihn aber nicht**. Historisches Brainstorming, ursprünglicher Entwurf und CP01 bleiben unveränderte Provenienz. Der finale Spezifikationsstand ist für künftige Entwicklung als Sollvertrag gedacht, **nicht** als bereits aktualisierte `05`-Ledgerautorität oder tatsächliche Implementierung.
- `ZEC-BL-BATCARE-001`: fachlicher Entwurf jetzt vollständig konsolidiert, **Sourceentwicklung noch nicht freigegeben**. `ZEC-BL-CTRL-USABLE-SOC-001` (B2), `ZEC-BL-CTRL-CAP-001` (C1), `ZEC-BL-CTRL-ADAPTIVE-001`, `ZEC-BL-CTRL-S3-001`, `ZEC-BL-BATTERY-SOH-001` sowie alle übrigen historischen Ledger-IDs bleiben unverändert.
- Zusätzlicher UI-Auftrag `Lade-/Entladegrenze` für beide Karten ist Bestandteil **dieses** zukünftig separat ausdrücklich freizugebenden Battery-Care-Gesamtscopes, auch wenn Battery Care später ausgeschaltet ist; keine eigene Roadmapbereinigung und kein isolierter Releasezwang.
- Vor späterem Coding: kanonische Quellen 00–07 gegen den dann aktuellen Stand lesen, reale Sourcebasis aus Releases/ hashverifizieren, aktuelles leistungsfähiges Reasoning-/Thinking-Setting durch Nutzer bestätigen, **finalen Macro-Scope ausdrücklich freigeben lassen**, Sicherheitsspezifikation/No-Drop anpassen; dann Sourceblöcke nach jedem größeren Arbeitsschritt vollständig extern sichern mit SHA256, ZIP-CRC, Manifest und unabhängigen Bibliotheks-Readbacks. Keine ungesicherten weiteren Entwicklungsblöcke.

**Ergebnis dieses Artefakts:** `SPEC_FINAL` als dokumentiertes fachlich abgeschlossenes Zielbild. **Nicht**: `SOURCE_APPROVED`, `IMPLEMENTED`, `TECHNICAL_BUILD_PASS` oder `REAL_FIELD_PASS`.
