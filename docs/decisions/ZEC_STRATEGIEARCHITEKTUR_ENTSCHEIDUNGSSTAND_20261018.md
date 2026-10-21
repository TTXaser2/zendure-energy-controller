# ZEC – Strategische Ladeallokation: konsolidierter Entscheidungs- und Konzeptstand

**Stand:** 18.10.2026  
**Status:** fachlich abgestimmte **Richtungsentscheidungen** mit noch offenen Produktionsspezifikationen; **keine Source-/Produktfreigabe**  
**Bezug:** `05_ZEC_BACKLOG_AND_ROADMAP.md` (alleinige Backlog-/Roadmapautorität), V17.0.2 reale Implementierung, Herbstanalyse 24.09.–16.10.2026, `ZEC_A1_WIRKSAMKEIT_23T_DECISION_BRIEF_20261017.md`.

## 1. Warum diese Architekturentscheidung?

Der produktive ZEC-Regler zeigt in der realen Herbstperiode überwiegend gutes Ladeverhalten. Eine neue Funktion hat **keine Daseinsberechtigung allein durch technische Realisierbarkeit**. Sie benötigt ein konkretes Problem, nachweisbaren Zusatznutzen, zulässigen Aktionsraum, neutralen Fallback und No-Regression bezüglich Safety, Export Capture, Fast Capture, Cross-Charge, Command/Readback/Recovery sowie Hardware- und Batterieschonung.

Gleichzeitig sind die derzeitigen High-SOC- und Harvest-Zweige nicht als unveränderliche Architekturaxiome zu behandeln. Alternative **strategische Allokationspolicies** jenseits des historischen High-SOC-Zweigs sollen geprüft werden, ohne einen konkurrierenden zweiten Zendure-Command-Owner oder neuen unkontrollierten Hauptmodus zu schaffen.

**Normativ für künftige Scopes:** aktuell vermeidbare Einspeisung geht strategischer Umverteilung vor; die reale Steuerautorität und alle physischen/harten Grenzen bleiben beim vorhandenen Regler.

## 2. Entkoppelte Gegenstände und Geltungsbereiche

| Ledger-ID | Gegenstand | Entscheidung 18.10.2026 | Scope-Status |
|---|---|---|---|
| `ZEC-BL-CTRL-ADAPTIVE-001`, `ZEC-BL-CTRL-001` | Lernende/prognostische Strategieregelung (bisher A1) | **DEFERRED / EVIDENCE_GAP**, kein Coding im nächsten Block; späteren Aktionsraum auch jenseits High-SOC prüfen | Später erneut zu spezifizieren |
| `ZEC-BL-CTRL-S3-001` | Konfigurierbare Zeitfenster, Bestätigungszeiten und Saisonpolicy | Eigenständig, zeitnah vollständig konzipieren und danach separat freigeben/umsetzen; **nicht** von Adaptive abhängig | Spezifikationsentwurf vorhanden |
| `ZEC-BL-CTRL-USABLE-SOC-001` | Deterministische, strategische Verwendung des bereits diagnostisch vorhandenen usable Primär-SOC (früher B2) | Eigenständig und **nicht auf Winter beschränkt**; konkrete sinnvolle Anwendungsfälle und Policy vor Coding herleiten | SPEC_NEEDED |
| `ZEC-BL-CTRL-CAP-001` | Weiche Kapazitätsgewichtung (früher C1) | Eigenständig von Adaptive **und** vom High-SOC-Zweig; `off|soft`, default `off`, nur bei belastbaren Daten und echter wirksamer Allokationsfreiheit | SPEC_NEEDED |
| `ZEC-BL-BATCARE-001` | Battery Care / Winter-/Reserveerhaltung insbesondere Zendure | Winterpriorisiert; eigene Policy-/Erhaltungsstrategie statt Nebenprodukt von B2 | SPEC_NEEDED |
| `ZEC-BL-BATTERY-SOH-001` | Diagnostische Abschätzung von realer Kapazität/Alterung | Separates optionales Forschungsthema, keine automatische Korrektur von Control-/SOC-Limits; Messqualitäts-/Methodenprüfung nötig | DEFERRED / SPEC_NEEDED |

Historische Entscheidung **20.09.2026** (gemeinsamer Adaptive-Umbrella S3+C1+Lernen) wird durch die ausdrückliche Nutzerentscheidung **18.10.2026** im *Sequencing* abgelöst, bleibt als Provenienz im Ledger erhalten. S2 bezeichnet die geschlossene Primärspeicherintegration; S3 ist die offene Saison-/Tagesprofil-Completion.

## 3. Herbst-Evidenz und Adaptive-Wiedervorlage

Aus den vorhandenen 23 Tagen 24.09.–16.10.2026: 646.890 Rohzyklen; 7 Tage, an denen keiner der Speicher 98 % erreichte; HIGH-SOC-Rechenzweig in 1.706 Minuten, `STRATEGIC_SHARE` in 725 Minuten. Auf den 7 knappen Tagen 132 Share-Minuten, auf 24.09., 08.10. und 13.10. keine. Am 13.10. betrug der maximale Primär-SOC rund 88 %, dennoch kein High-SOC-Zweig: **die reine 75-%-Eintrittsschwelle erklärt die Nichtanwendbarkeit nicht hinreichend**.

In einer statischen, vereinfachten Share-Sensitivitätsrechnung für 1.008 rekonstruierbare High-SOC-Minuten führten +/-10 Prozentpunkte Primärshare in 226/139 Minuten zu >=50 W abweichendem gekappten Zielwert. Dies ist **kein kausaler Hardware-/Ertrags-Gegenbeleg**, sondern ein Nachweis des begrenzten Stellraums.

Konsequenz: Die bisherige Adaptive-A1-Implementierung ausschließlich im alten High-SOC-Share-Pfad ist aktuell nicht als vorrangiges Produktprojekt gerechtfertigt. Keine automatische High-SOC-Vorverlegung; bestehende Eintrittslogik auf ihren ursprünglichen Zweck/ihre tatsächlichen Gating-Bedingungen prüfen. Bei Wiederaufnahme mögliche übergreifende Strategieebene, ohne neue Safety-/Command-Autorität, explizit gegentesten. Kein lernendes Shadow/Active-Coding im nächsten Entwicklungsrelease; alle Lernzustands-, Confidence-/Fallback-, Replay-/Pretrainer-/Persistenz- und Reset-Anforderungen bleiben erhalten.

Datenlimits: 23 Tage reichen nicht für garantierte Saisonverallgemeinerung; PV-/Hausleistung im V4-Datensatz nicht vollständig unabhängig nachweisbar, Minutendaten nicht kausal; reale Command-/MIN_SOC-/SMA-Parser-Findings als Störfaktoren gesondert führen.

## 4. S3 – Zweck und Wirksamkeit

**Problem:** Hartcodierte Fenster (09:30/11:30/14:30/18:00) und Entry-Confirm-Zeiten (60/30/15 s), teilweise bereits angelegte `TARGET_ONLY`-Settings, wirkende Legacy-Shares, aber keine vollständig wirksame und verständliche Saisonpolicy. Konfiguration kann derzeit Wirksamkeit suggerieren.

**Zweck:** Ein nachvollziehbares, deterministisches und vom Nutzer konfigurierbares zeit-/saisonabhängiges **Profil der bestehenden strategischen Harvest-Priorisierung**; kein Wetterorakel und keine automatische Ertragsprognose. Zeit-/Saisonänderungen müssen auf anwendbare Fälle begrenzt bleiben; Export Capture und Hardware-/Safety-Pfade dürfen nicht zurückgesetzt werden.

**Gate:** Altbestand bei unveränderten Settings differential verhaltensgleich; Settings-Wirkung und Nichtwirkung klar anzeigen, Migrationsdefault sicher; Zeit-/Kalender-Rollover, Hysterese, Restart/Recovery, Messdiagnose und Tests. Siehe `ZEC_S3_FACHLICHE_PRODUKTIONSSPEZIFIKATION_ENTWURF_20261018.md`.

## 5. B2 – usable SOC, nicht bloß Winterheuristik

Bereits diagnostisch verfügbar: `primary_usable_soc_percent=clamp((raw_soc-floor)/(100-floor)*100,0..100)` bei frischem SMA-Capability-Floor. Dieser beschreibt nutzbaren **Entlade**-SOC relativ zur geräteseitigen Entladeuntergrenze. Er ist weder Ladekapazität noch alternative physische SOC-Definition.

**Zwecksuche (offen):** Erkennen und möglicherweise berücksichtigen, ob ein Primärspeicher mit nominell hohem Roh-SOC dennoch wenig für Eigenverbrauch freigegebene Reserve hat. Potenziell ganzjährig für Analyse, strategiebezogene PV-Ladepriorisierung und Reserveplanung relevant. Jede produktive Prioritätswirkung muss einen **zusätzlichen** Nutzen gegenüber Roh-SOC-/Ladeannahmeregeln zeigen und darf vorhandene Export-Capture-/SMA-/BMS-Grenzen nicht unterlaufen. Unfrische/unsupported Floor-Daten -> neutraler Fallback; keine globalen RAW-SOC-Schwellen ersetzen. Nicht identisch mit der aktiven Zendure-Reservepflege von Battery Care.

**Offen vor Umsetzung:** genaue Use Cases, Prioritäts-/Hysteresepolicy, erlaubte Modi, physische Umverteilbarkeit, Größen-/Grenzsemantik, Konflikt mit S3/C1/Battery Care, reproduzierbarer realer Zusatznutzen.

## 6. C1 – weiche Gewichtung, nicht Kapazitätsproportionalität

**Zweck:** Bei knapper Ladeenergie und physisch vorhandener Wahl zwischen zwei ladefähigen Speichern soll eine valide Größeninformation über deren *freien Lade-Headroom* eine nachweislich nützlichere Priorisierung ermöglichen. Nicht nur im High-SOC-Zweig und nicht rein proportional nach Nenn-kWh.

Datenbasis: belastbare Primärspeicher-/Zendure-Kapazität, Roh-SOC, jeweilige Ladeobergrenze, Freshness und Ladeannahme. **SMA-Entladefloor gehört nicht zur Lade-Headroom-Berechnung.** Gerätemetadaten, Template, Fallback haben unterscheidbare Vertrauensstufen; leere/zweifelhafte Daten -> neutral, niemals Kapazität=0 unterstellen. `off|soft` mit Default `off` als vorläufiger Vertrag; konkrete Korrekturschranken gehören zur getrennten Produktionsspezifikation und dürfen nicht aus einer früheren Modellskizze ungeprüft übernommen werden. Effekt auf **finalen** Sollwert und physische Leistung nachweisen, nicht nur internen Share.

## 7. Battery Care – separate Winterpriorität

SMA wendet geräteseitig eine variable Entladeuntergrenze an; dies ist nicht gleichbedeutend mit vollständiger ZEC-Batteriepflege. Reale Nutzerbeobachtung: Zendure zeigte auch bei ca. 9 % SOC keine eigenständige Nachladung; dies beweist nicht, dass Firmware/BMS niemals Schutzmechanismen auslösen.

Eigener zu spezifizierender Produktzweck: Vermeidung unnötig langer tiefer Zendure-SOC-Phasen bei wenig PV, saisonale Entladebegrenzung, kontrollierte Reserveerhaltungs-/Nachladeepisode mit **PV-Vorrang** und Netzladung **nur bei gesonderter ausdrücklicher Freigabe und sicherem physischem/Kommandopfad**, Trigger/Ziel-SOC, Hysterese, Leistungscap, Restart-/Abort-/Exit-Vertrag, Cross-Charge-Ausschluss und Hardwareschonung. 9 %, 12 % oder 20 % sind keine pauschal freigegebenen Defaults. Battery Care ist keine implizite Folge der B2-Capability und erbt keine Nutzereinwilligung für Netzladung.

## 8. Verbindliche fachliche Produktionsspec-Gates pro eigenständigem Block

1. **Zweck und Problem:** Was ist heute nachweisbar unzureichend; was ist ein konkreter, quantifizierbarer Nutzen?
2. **Anwendbarkeit:** Welche Topologien, Betriebsmodi, Datenqualitäten, SOC-/Ladezustände sind zulässig; was sind klare Nichtfälle?
3. **Policy und physische Stellbarkeit:** Welche zulässige Endzielwertveränderung kann ZEC tatsächlich herbeiführen? Welche Phasen sind trotz anderslautender Zwischenberechnung nicht beeinflussbar?
4. **Priorität/Arbitration:** Keine doppelte B2+C1-Primärpriorität, S3 ist Zeit-/Saison-Kontext, keine zweite Commandinstanz; Safety, Cross-Charge, Export Capture, MIN/MAX, Fast Capture gehen vor.
5. **Fallback und No-Regression:** Schalter off, historische Default-/Bestandsmigrations-Gleichheit, ungültige oder stale Daten, Controller-/Gerätetransitionen, Netzimport/Export und Hardwarebeanspruchung.
6. **Evidenz/Exit:** Soll-Ist/Readback/Recovery und tatsächlich wirksamer Endzielwert, Differential-/Boundarytests, sinnvoller Nutzen; bei Nichtnachweis `off`/`DEFERRED` statt künstlichem Aktivierungserfolg.

Kein weiterer mehrwöchiger Pi-Datenanalyseblock als generelle Entwicklungs-Vorbedingung; vorhandene V4-Auszüge verwenden. Auf dem Raspberry Pi nur begrenzte Streamingdiagnostik.

## 9. Zeitliche Reihenfolge und Releasegates

- **Jetzt:** Projektquellenreconciliation, dann S3-Fachspezifikation/Sourcefreigabe und Umsetzung als eigenständiger Scope.
- **Danach:** B2 und C1 **separat fachlich spezifizieren**, bei belastbarem Nutzen/source-seitig kleinem und sicheren Scope implementieren; nicht zwangsläufig ein einziger Releasescope.
- **Zeitkritisch:** Battery-Care-Spezifikation/Implementierung vor Winter priorisieren; wenn B2/C1 den Fortschritt unverhältnismäßig blockieren, Battery Care **vorziehen**.
- **Nächster Produktrelease:** Die bestehenden **verpflichtenden** Fixes `ZEC-BL-CTRL-NIGHT-MINSOC-GRID-001` und `ZEC-BL-GRID-SMA-OBIS-001` implementieren und regressionsprüfen; weitere Command-Beobachtungen unter vorhandenem Ledger konservieren, kein neuer unbounded-forensischer Vorlauf.
- **Später:** Adaptive-Aktionsraum und Nutzennachweis neu bewerten. Kein automatischer Wiedervorlage-Zeitpunkt nötig.

**Freigabegrenze:** Dieses Dokument hält abgestimmte fachliche Richtungsentscheidungen fest, **ist aber nicht die Produktionsspezifikation für S3, B2, C1, Battery Care oder Adaptive**. Änderungen an Reglercode, Settings, Runtime oder Installer benötigen eine getrennte Freigabe. Ältere Konzeptentwürfe und Herbstberichte bleiben Provenienz; `05` bleibt alleinige Ledgerautorität.
