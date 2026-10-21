# ZEC – A1-Wirksamkeit im Herbst: Architektur-Entscheidungsbrief

**Datum:** 17.10.2026 · **Projektbasis:** V17.0.2 · **Status:** READ_ONLY / ARCHITECTURE_EVIDENCE, keine produktive Freigabe.

## 1. Fragestellung und Ergebnis

Kann eine adaptive Variation des strategischen Primärspeicher-Shares innerhalb unverändert deterministischer High-SOC-Eintrittsbedingungen (A1) anhand der realen September-/Oktober-Daten sinnvoll wirken?

**Antwort:** A1 besitzt einen technisch realen, aber begrenzten Aktionsraum. Der für den Winter besonders relevante Fall eines knappen Ertragstags liegt häufig außerhalb des unveränderten High-SOC-Zweigs. Die Daten liefern **keinen Nachweis einer kausalen Verbesserung** durch A1; ein aufwendiges produktives Lernmodell vor Battery Care ist derzeit nicht hinreichend begründet. Dagegen sind deterministische S3-Wirksamkeit, verhaltenskompatible Konfiguration und ein minimaler Shadow-/Evidenzvertrag begründet.

## 2. Evidenz

- Quellen: zwei nutzerseitig bereitgestellte, auf SHA256 geprüfte ZEC-Autumn-Minutenarchive für 24.09.–16.10.2026; `ZEC_HERBSTANALYSE_23T_KONSOLIDIERT_20261017.md`; produktiver V17.0.2-Kern `controller_logic.py` aus verifiziertem Release-ZIP.
- 646.890 zugrunde liegende V4-Rohzeilen, 33.115 von 33.120 Kalenderminuten mit mindestens einer Aggregatzeile. Genau fünf vollständig fehlende Minuten am 25.09. Nicht jede Minute weist für jedes Feld ausreichende Freshness/Validity nach.
- `HIGH_SMA_SOC` in 1.706 unterschiedlichen Minuten als Rechenzweigmarker; `STRATEGIC_SHARE` in 725 unterschiedlichen Minuten als Zielwertauswahlmarker. Gemischte Marker innerhalb einer Minute sind **keine** zyklusgenaue Gleichzeitigkeit.
- In den 7 Tagen, an denen **keiner** der Speicher 98 % Tagesmaximal-SOC erreichte, gab es zusammen 132 Minuten mit `STRATEGIC_SHARE`. An drei Tagen (24.09., 08.10., 13.10.) trat **überhaupt kein** `HIGH_SMA_SOC`-Rechenzweig auf; A1 könnte dort bei unverändertem Eintrittsvertrag nicht eingreifen.
- Der aktuelle Code berechnet in erlaubten High-SOC-Zweigen bei gültiger physikalischer Referenz: `total = primary_charge + zendure_charge + export`; `primary_share_target = min(primary_max, max(primary_floor, share*total))`; `zendure_share_target = max(0,total-primary_share_target)`; `candidate = max(zendure_share_target, zendure_actual_charge + export)`. Die Export-Capture-Untergrenze bleibt dominant. Das Kommando unterliegt anschließend weiteren Schutz-, Rampen-/Power- und Fast-Capture-Stufen.

## 3. Offline-Sensitivität (kein physikalischer Replay)

Das V17.0.2-Rechenverfahren wurde auf **1.008 eindeutigen Minuten** mit eindeutigem High-SOC-Zweig, mathematischer Rekonstruktionsabweichung <10 W, mindestens 80 % Command-Path-Eligibility und vorhandenem Grid-/Geräte-Power-Sample ausgewertet. Die derzeitige Primärspeicher-Maximalleistung 2.300 W, die Floor-Ratio 0,30 sowie die Zendure-Grenze von 2.400 W wurden aus der referenzierten produktiven Konfiguration verwendet. Primärspeicher-Share wurde isoliert hypothetisch um ±0,10 verändert; nach dem `max` mit Export-Capture wurde lediglich der **einfache** Zendure-2.400-W-Cap nachgebildet.

| Variation des Primär-Shares | Minuten mit hypothetisch ≥50 W unterschiedlichem Zielwert (nach einfachem Hardware-Cap) |
|---|---:|
| −10 Prozentpunkte (mehr strategische Zendure-Ladung) | 226 von 1.008 |
| +10 Prozentpunkte (weniger strategische Zendure-Ladung) | 139 von 1.008 |

**Auf den sieben knappen Tagen** liegen innerhalb dieses engen, streng rekonstruierbaren Teilfensters nur **5 bzw. 1** Minuten mit der jeweiligen ≥50-W-Sensitivität. Das ist eine **Filter- und Augenblicksaussage**, keine belastbare obere Grenze für Energiegewinne oder Folgen einer anderen Strategie, weil vergangene Messwerte bei veränderten Kommandos nicht unverändert bleiben würden. Die anschließende dynamische Reglerkette, Geräteleistung, SOC-Entwicklung, Hardwareschonung und die tatsächliche PV-Gesamterzeugung werden hier nicht simuliert. Es wird deshalb **keine kWh-Ersparnis** behauptet.

## 4. Qualitative Bewertung

1. **Wirkungsfähigkeit:** JA. A1 kann in geeigneten High-SOC-Episoden reale Sollwertänderungen auslösen.
2. **Breiter winterrelevanter Handlungsspielraum:** NEIN, aus den untersuchten Daten nicht belegt; an drei knappen Tagen war der erlaubte Regelzweig abwesend.
3. **Beleg einer Ertrags-/SOC-Verbesserung gegenüber V17:** NEIN, aktuell nicht vorhanden.
4. **Risiko einer unnötigen Eingriffskomplexität:** REAL, da Restexport-Floor, vorhandene Ladeleistungsgrenzen, Fast Capture und Konvergenz bereits viel des Handlungsspielraums binden.
5. **Handlungsempfehlung:** S3-Konfigurierbarkeit und Saisonfenster vollständig, verhaltenskompatibel und getestet abschließen; A1-/B1-/C1-Regelmodell nur mit default-off und zunächst Shadow/Diagnose vorbereiten. Die produktive A1-Aktivierung erst nach engem Differential-Gate mit real nachgewiesenem Nettoeffekt. **Battery Care priorisieren**, statt zusätzliche Ertragsanalysen als vorgeschaltetes Dauergate zu verlangen.

## 5. Sequencing/Releasehinweis (Vorschlag, noch keine Roadmapänderung)

- Nächster Release: die **zwei verpflichtenden Fixes** `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` inkl. Regression. Dazu, bei ausdrücklicher Entwicklungsfreigabe, die abgeschlossene S3-Funktion sowie A1/B1/C1 nur nach risikoarmem, explizitem Scope; bestehende funktionierende Regeln unverändert per Default.
- Anschließend Battery Care `ZEC-BL-BATCARE-001` direkt spezifizieren/implementieren, dessen Winterrelevanz im Master-Backlog ausdrücklich belegt ist. Sollte dafür der produktive Lernlayer aus dem Adaptive-Umbrella zeitlich zurückgestellt werden, muss `05_ZEC_BACKLOG_AND_ROADMAP.md` **explizit** aktualisiert werden; es darf dabei keine Ledger-ID oder offene Evidenz verschwinden.
- Neue Command-/Readback-Funde vom 05.10. bleiben im Backlog zu reconciliieren, werden aber **nicht** als generelle Vorbedingung für den A1-Architekturbeschluss verwendet. Kritische reale Command-Safety-Funde sind isoliert nach Severity abzuarbeiten.
- Keine Sourceänderung vorgenommen, kein Pi-Aufruf benötigt.

## 6. Grenzen

Die aggregierten Minuten sind stichprobengewichtete Mittel, nicht zeitgewichtete Energieintegrale oder ein vollständiger Closed-Loop-Replay. Die V4-PV- und Hausleistungsfelder sowie primary_remaining_capacity_kwh sind im verwendeten Export nicht mit validen Daten belegt. Eine kausale Ertragsverbesserung bzw. SOH-Schätzung ist nicht beweisbar. Eine A2-Erweiterung (lernbasierte Entry-Gates) wird aus dieser Datenlage **nicht** automatisch empfohlen, da sie zusätzliche Hysterese-/Zustandsrisiken erzeugt.
