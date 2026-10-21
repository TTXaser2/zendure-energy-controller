# Fast Capture – implementierter Architekturstand V17.0.2

**Dokumenttyp:** `AS_BUILT`-Quellenkurzbefund für V17.0.2, erstellt 19.10.2026; **STAGING für nächsten Release, vor Übernahme neu revalidieren**.  
**Source:** `controller_logic.py` SHA256 `113cb9cc60475cb59294bf07ab750e63580b59112f178948b7e386fd0539b031` aus Release-ZIP SHA256 `82bd2db52a71b4a4e56f8e8c39e30511494fb02f8735909667052b73bd82f311`.  
**Ledger:** `ZEC-BL-CTRL-FASTCAP-001`.  
**Feldlage:** V17.0.2 allgemeine Feldabnahme PASS/FULL_READY; Fast Capture Shadow PASS, Active-NEAR_LIMIT in beobachteten Aspekten PASS, Active-FULL_IDLE weiter `EVIDENCE_PENDING` (nicht als feldvalidiert behaupten).

## Zweck und Architekturgrenze

Fast Capture nimmt kurzfristigen aktuellen Export bei bestätigter Primärspeicher-Sättigung (`FULL_IDLE`) oder Primärspeicher-Leistungsgrenze (`NEAR_LIMIT`) über ein positives **Overlay O** zusätzlich zum normalen AUTO-/Harvest-Baselineziel **B** auf. Kein zweiter Controller, kein Entladepfad und keine Umgehung der vorhandenen Cross-Charge-/Safety-/Command-Pipeline. `RESERVE_UNKNOWN` hat kein Fast-Overlay.

## Quellmapping und implementierte Konstanten

- `controller_logic.py`: `FAST_CAPTURE_ATTACK_W_PER_S=400`, `FAST_CAPTURE_RELEASE_W_PER_S=100`, Mindestexport 100 W, Import-Abbruch 100 W, FULL-SOC 99 %, Idle-Power 100 W, Full-Idle-Confirm 15 s, Near-Limit-Margin 150 W, Observation-Gap 10 s.
- Steuerung: `_fast_capture_mode`, `_fast_capture_prepare_mode`, `_fast_capture_observation_timing`, `_fast_capture_step` sowie Guards in `run_once` (u.a. Non-AUTO, NIGHT, Cross-Charge).
- `settings_registry.py`: `HARVEST_FAST_CAPTURE_MODE=off|shadow|active`.
- `state.py`, `measurement_v4.py`: getrennte Fast-Capture-Baseline-/Overlay-/Zielwert-/Blockgrund-/Episodenfelder.
- Geregelter Commandversand bleibt beim zentralen vorhandenen Commandpfad; Fast Capture publiziert keine eigenständigen direkten MQTT-Kommandos.

## Daten-/Geltungs- und Wirkungskette

1. AUTO-/Harvest-Baseline aus regulärer Regelung, dann vorhandene Limiter und Smoothing-/Step-Semantik.
2. Nur bei gültiger/frischer Grid-, Primärspeicher-, Zendure-SOC-/Leistungsevidenz sowie erlaubter Command-/Cross-Charge-Situation Zustand `FULL_IDLE`, `NEAR_LIMIT` oder `RESERVE_UNKNOWN` bestimmen. Full-Idle benötigt frische Zeitfortschreibung.
3. Zusätzlichen Overlay unter Primär-Reserve, Zendure-Headroom und A400/R100 berechnen; Import-/Safety-Hard-Abort entfernt O sofort.
4. `B+O` nach bestehenden Leistungs-, Cross-Charge- und Command-Guards anwenden; Baselinezustand bleibt vom Overlay getrennt und darf nicht rückgekoppelt werden.
5. `off` keine Fast-Wirkung; `shadow` berechnet/diagnostiziert ohne Fast-Zielwertwirkung; `active` kann den finalen Ladezielwert verändern. Messfelder und Readback/Leistungswirkung separat auswerten.

## Geschützte Grenzen

Kein Fast-Overlay bei nicht freigegebenen Betriebszuständen, MAX-/MIN-SOC-Guards, invaliden Daten, Cross-Charge oder unsicherem Commandpfad. Volatile Leistungsgrenzen, aktueller Geräte-Readback, Hardware- und Netzbezugsregeln bleiben maßgeblich. Kein frei erfundener Acceptance-/SOH-Clamp.

## Historische Spezifikation vs. produktiver Stand

Die [V16.0.2-Originalspezifikation](../history/specifications/ZEC_FAST_CAPTURE_A400_R100_PRODUKTIONSSPEZIFIKATION_V16_0_2.md) beschreibt den damaligen **Sollzustand** und meldet „noch nicht implementiert“. Seit V17 ist Fast Capture real implementiert; V17.0.2 repariert den Mess-/Analyse-Evidenztransport. Die im Master-Ledger belegte V16.2.5-Revalidierung ist als Original derzeit nicht auffindbar (`MISSING_ORIGINAL`). Ein Revalidierungsdokument darf weder fingiert noch aus dieser Kurzbeschreibung rückwirkend als ursprüngliche Fassung deklariert werden.
