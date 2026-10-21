# ZEC – Control & Safety Invariants

**Stand:** 17.09.2026  
**Status:** kanonisch und normativ

## 1. Primärziel

ZEC minimiert vermeidbare Netzeinspeisung bzw. Netzbezug innerhalb der verfügbaren Speicherleistung, ohne Schutzgrenzen, Primärspeicherpriorität, Cross-Charge-Schutz oder Hardwarelebensdauer zu verletzen.

## 2. Primärspeicherpriorität / Harvest

- Der Primärspeicher besitzt grundsätzlich strategische Priorität.
- **Aktuell vermeidbare Einspeisung hat Vorrang vor strategischer Ladeverteilung.** Zendure darf nicht prophylaktisch zurückgehalten werden, wenn dadurch aktuell nutzbarer PV-Überschuss eingespeist wird und Zendure noch Ladeleistung sowie SOC-/Leistungs-Headroom besitzt.
- Strategische Ladeverteilung darf nur innerhalb des Leistungsanteils erfolgen, dessen Umverteilung keine aktuelle Einspeisung verursacht.
- Für Restexportzweige muss klar zwischen Delta und absolutem Zielwert unterschieden werden.
- Bei `SMA_FULL_OR_IDLE` und geeigneten Restexportfällen ist ein absolutes Zendure-Ziel aus bereits wirksamer Zendure-Ladung plus verbleibendem Export abzuleiten, soweit keine andere spezifizierte Allokation greift.
- Bei `SMA_NEAR_LIMIT` müssen Primärspeicheranteil, Zendure-Anteil und Restexport energetisch zusammenpassen; Floor/Restart/Near-Limit/Share dürfen nicht doppelt angewandt werden.
- High-SOC-Harvest benötigt korrekte Eintritts-/Austrittshysterese, Zeitprofil sowie Leistungs-/Kapazitätsgrenzen.
- Eine strategische Share-Rechnung darf eine physikalisch notwendige Export-Capture-Untergrenze nicht unterschreiten.
- Diagnose von Ladeannahme/Taper ist von einer selbstlernenden oder strategisch verändernden Reglerfunktion zu trennen. Diagnoseerkenntnisse dürfen nicht stillschweigend die Sollwertstrategie ändern.

## 3. Cross-Charge

- Cross-Charge-Schutz ist symmetrisch zu behandeln.
- Sollwertseitiger Gegenfluss und tatsächlich beobachteter Gegenfluss sind getrennte Sachverhalte.
- Gegenfluss wird proportional neutralisiert bzw. reduziert; keine unnötigen zyklusweisen Vollneutralisierungen.
- Mehrdeutige Telemetrie darf nicht durch die Sollrichtung zirkulär als korrekt bestätigt werden.

## 4. Nachtmodus

- Nachtmodus besitzt definierte Start-/Endzeit, Entladeleistung und Reserve-SOC.
- Verlassen des Nachtmodus erfordert aktive 0-W-Neutralisierung und sauberen Übergang zu AUTO/HOLD.
- Reserve-SOC und globales MIN_SOC sind harte Grenzen.
- Ein nutzerspezifischer Nacht-Leistungswert ist kein allgemeiner Default.

## 5. SOC-/Limitsemantik

- Erreichen von MAX_SOC oder MIN_SOC ist bei gesunden Daten ein normaler begrenzender Betriebszustand, kein generischer Datenfehler.
- SAFE_STATE bleibt echten Daten-, Command-, Integrations- oder Laufzeitfehlern vorbehalten.
- Schutzlimiter müssen Grund und Exitpfad eindeutig ausweisen.

## 6. Command Safety / Wirkung / Resync

- Publish ist kein Wirkungsnachweis.
- Kommandowirkung wird mindestens in Richtung, Sollwerttracking und Systemziel getrennt bewertet.
- Kleine Sollwerte unter Diagnosegrenze sind `not_evaluable`, nicht automatisch „effective“.
- Variable Sollwerte innerhalb derselben Intention dürfen einen persistenten Nichtwirkungsfall nicht durch Timer-Reset verdecken.
- 0-W-Neutralisierung ist ein aktives Kommando und benötigt Wirkungskontrolle.
- Bei bestätigter Nichtwirkung muss ein vollständiger State-Resync möglich sein: SmartMode, AC-Modus und beide Limits.
- Late-Effect-/Recovery-Guards müssen alte verspätete Gerätezustände erkennen, ohne normale Regelung dauerhaft zu blockieren.

## 7. SmartMode / Gerätevertrag

- ZEC steuert Zendure im erforderlichen SmartMode-/AC-Mode-Vertrag.
- Command-State muss `smartMode`, `acMode`, `inputLimit`, `outputLimit` frisch und konsistent rücklesen können.
- Richtungsinvariante: im Input-/Lademodus ist das Gegenlimit 0; im Output-/Entlademodus entsprechend das Ladegegenlimit 0.

## 8. Hardware- und Batterieschonung

Jede Regler-/Recovery-/Neutralisierungsänderung ist auf zusätzliche Belastung zu prüfen:

- zusätzliche Energiezyklen;
- unnötige Lade-/Entladerichtungswechsel;
- vermeidbare 0-W-Zwischenzustände;
- wiederholte AC-Mode-Wechsel;
- häufige persistente Geräteschreibvorgänge;
- höhere C-Raten;
- tiefere SOC-Hübe;
- längere hohe SOC-/Temperaturphasen;
- zusätzliche thermische Zyklen;
- neue Oszillation oder unnötige Rampenaktivität.

Schutzmechanismen sollen nur in nachgewiesenen Fehlerzuständen greifen, mit monotonic elapsed time und frischen unabhängigen Beobachtungen. Normale AUTO-/HOLD-/Harvest-Regelung darf dadurch nicht unnötig träger werden.

## 9. Analysepflicht

Für jeden relevanten Regelzweig gelten die vier Nachweise des `ZEC_ANALYSE_REGELWERK_V1.1.md`: Zustand, Rechnung, physikalische Wirkung und Recovery.
