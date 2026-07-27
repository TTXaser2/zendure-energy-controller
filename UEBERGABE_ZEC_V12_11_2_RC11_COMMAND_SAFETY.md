# Übergabe Zendure Energy Controller – V12.11.2-RC11
## Command Safety, Neutralization Watch, Effect Tracking und Recovery

**Stand:** 26.07.2026  
**Basis:** V12.11.2-RC10  
**Normative Analysegrundlage:** `ZEC_ANALYSE_REGELWERK.md`, Revision 1.1

## 1. Zweck

RC11 setzt ausschließlich die freigegebene Stufe A des P1-Robustheitsplans um. Die Settings-Neuentwicklung bleibt nach dem Cross-Charge-Settingsblock pausiert und vollständig erhalten.

## 2. Produktiver Auslöser

Am 25.07.2026 wurde das Ende der festen Nachtentladung korrekt erkannt und 0 W gesendet. Das Gerät entlud physisch ungefähr 400 W weiter; der SOC fiel von 36 % auf 10 %. RC10 überwachte Ziel 0 W nicht und konnte den vollständigen neutralen Gerätezustand nicht force-senden.

Im anschließenden Recovery-Lauf setzte jede Änderung des exakten Lade-Sollwerts den Effect-Timer zurück. Erst ein länger stabiler Sollwert von +2.397 W führte zu Mismatch und Full-State-Resync. 12,3 Sekunden nach diesem Resync setzte reale Ladung ein.

## 3. Implementierter Zielzustand

### 3.1 Command Contract

Jeder aktive Gerätewunsch wird als vollständiger Batch dokumentiert:

```text
Sequenz · Intent · AC-Modus · inputLimit · outputLimit · signed Ziel · Grund
```

### 3.2 Neutralisierung

Sicherheitsrelevante 0-W-Übergänge starten einen Watch. Ein Mismatch ist nach Default 30 Sekunden möglich. Der Recovery-Batch enthält AC-Modus und beide 0-W-Limits.

### 3.3 Aktive Ziele

Die Beobachtungsdauer folgt der Richtung CHARGE/DISCHARGE. Dynamische Wattänderungen derselben Richtung setzen sie nicht zurück. Teilwirkung bleibt offen und kann bei Persistenz einen Resync auslösen.

### 3.4 Leistungsrichtung

Explizite Rohsensoren bestimmen die Richtung. Ein isolierter `packInputPower` bleibt mehrdeutig. Die Sollrichtung darf die physische Richtung nicht allein beweisen.

### 3.5 Diagnose

Publish, Resync, physische Wirkung und Recovery sind getrennte Zustände. Ein offener Mismatch verhindert „System OK“.

## 4. Measurement V4

Der neue Standardheader enthält additive Felder für Command-Batch, Lifecycle, Effect, Neutralisierung, Power-Observation und Rohwerte. RC10-Dateien bleiben unverändert und werden durch eine neue RC11-Sitzungsdatei fortgesetzt.

## 5. No-Regression-Vertrag

Außerhalb der Intended Deltas müssen gegenüber RC10 unverändert bleiben:

- AUTO Import/Export und Deadband,
- aktiver Night-Festwert,
- feste manuelle Modi,
- Cross-Charge-Zielwertkorrektur,
- alle Harvest-Zweige und Zeitprofile,
- Safe-State-Eintritt,
- MQTT-Kommandotopics.

## 6. Folgeblöcke

Nach produktiver RC11-Validierung:

1. **RC-B:** absolutes `SMA_FULL_OR_IDLE`-Ziel mit vertrauenswürdiger Ladebaseline.
2. **RC-C:** lokale API in Hintergrundworker und Latest-Snapshot-Cache verschieben.
3. Danach Settings-Redesign an der konservierten Stelle fortsetzen.

## 7. Pflichtvalidierung im Realbetrieb

- Nachtende beziehungsweise bewusste Testneutralisierung auf tatsächliche physische 0-W-Wirkung prüfen.
- Recovery-Ereignislinie vollständig erfassen: Soll/Neutralisierung → Mismatch → Resync ausgeführt → Wirkung bestätigt.
- Bei mehrdeutigem `packInputPower` prüfen, dass keine falsche Richtung behauptet wird.
- Normale AUTO-, Night-, Fixed-, Cross-Charge- und Harvest-Episoden als No Regression bewerten.
- Jede Freigabe nach den vier Nachweisen des Analyse-Regelwerks durchführen: Zustand, Rechnung, Wirkung und Recovery.

## 8. Buildvalidierung

```text
python3 -m py_compile *.py tools/*.py     OK
node --check static/status_v2.js          OK
bash -n tools/update_zendure_controller.sh OK
python3 -m unittest discover -s tests -q  384 Tests, OK
```

Bekannter unveränderter Wartungspunkt: ältere SQLite-Tests melden unter Python 3.13 teilweise nicht geschlossene Testverbindungen als `ResourceWarning`; keine Testfehlfunktion.

## 9. Dateiänderungen gegenüber RC10

### Neu

```text
command_lifecycle.py
zendure_power_observation.py
tests/test_v12_11_2_rc11_command_safety.py
TECHNICAL_NOTES_V12_11_2_RC11.md
RELEASE_INFO_V12_11_2_RC11.md
UEBERGABE_ZEC_V12_11_2_RC11_COMMAND_SAFETY.md
```

### Fachlich geändert

```text
controller_logic.py
state.py
mqtt_bridge.py
config_manager.py
config.example.json
csv_logger.py
measurement_v4.py
measurement_v4_contract.py
operational_events.py
web_ui.py
status_page_v2.py
static/status_v2.js
version.py
README.md
README_INSTALLATION.md
```

Zusätzlich wurden bestehende Regressionstests auf die bewusst geänderte RC11-Semantik und die aktuelle Versionskennung angepasst.

### Gelöscht oder umbenannt

```text
keine Dateien
```
