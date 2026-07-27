# Übergabe Zendure Energy Controller – V12.11.2-RC12
## Command Contract, Flash-Schutz, Power-Semantik und Offgrid-Vorbereitung

**Stand:** 27.07.2026  
**Basis:** V12.11.2-RC11  
**Status:** Build- und Regressionstestvalidiert; Produktivvalidierung ausstehend

## 1. Anlass

Die RC11-Produktivprüfung zeigte:

- `smartMode=0` war aktiv, während ZEC dynamische Leistungslimits schrieb.
- Die offizielle Zendure-Semantik empfiehlt `smartMode=1` für häufige Änderungen ohne Flash-Persistenz.
- Eine kontrollierte einmalige MQTT-Aktivierung wurde auf dem produktiven Gerät über MQTT und lokale API bestätigt und änderte keine anderen Gerätewerte.
- `outputPackPower` wurde in RC11 falsch als Entladung interpretiert; der Produktivfall erzeugte dadurch `CONFLICT`.
- Die geplante spätere Nutzung der Offgrid-Steckdose verlangt eine Trennung von Hausnetz-, Batterie- und Notstromlast.

## 2. Produktiv verifizierter Vertrag

Gerät:

```text
HEC4NENCN492025
```

Command-Topics:

```text
Zendure/switch/HEC4NENCN492025/smartMode/set
Zendure/select/HEC4NENCN492025/acMode/set
Zendure/number/HEC4NENCN492025/inputLimit/set
Zendure/number/HEC4NENCN492025/outputLimit/set
```

Zulässige Payloads beziehungsweise Bereiche:

```text
smartMode: ON / OFF
acMode: Input mode / Output mode
inputLimit: 0–2400 W, Schritt 1 W
outputLimit: 0–2400 W, Schritt 1 W
```

RC12 verwendet nur `smartMode=ON`; `OFF` ist im Runtime-Pfad technisch gesperrt.

## 3. Implementierte Hardware-Schutzmaßnahmen

- Kein aktiver dynamischer Sollwert ohne frisch bestätigtes `smartMode=1`.
- Kein Runtime-Pfad zum Deaktivieren von Smart Mode.
- Nur aktives Limit bei stabiler Richtung und bestätigten Gegeninvarianten.
- Full-State-Abgleich gedrosselt über 30-Sekunden-Retry-Fenster.
- Gerätecaps ausschließlich read-only.
- Keine Änderung der Offgrid-Konfiguration.
- Keine Verwendung von `writeRsp=0` als Erfolgsnachweis.
- Command-State-Rücklesung und physische Wirkung bleiben getrennte Nachweise.

## 4. Offgrid-Modell

```text
Netzport:
  gridInputPower / outputHomePower

Batterie:
  outputPackPower / packInputPower

Notstromausgang:
  gridOffPower
```

Die Offgrid-Last darf nicht als Hausnetzentladung, Cross-Charge oder fehlgeschlagene netzseitige Neutralisierung gelten.

## 5. Produktivtestpflichten

### 5.1 Unmittelbar nach Installation

- Version RC12 bestätigt.
- `zendure_flash_protection_active=true`.
- `zendure_command_smart_mode=1`.
- `zendure_command_state_complete=true` nach der kurzen Startphase.
- Kein wiederholter `SMART_MODE_ENABLE_SENT`-/Full-State-Spam.

### 5.2 Normale Regelung

- Gleichgerichtete Zieländerungen erzeugen primär `COMMAND_LIMIT_UPDATED`.
- Richtungswechsel setzt AC-Modus, Gegenlimit 0 und aktives Limit vollständig.
- Gerätecap 2000 W Entladung wird nicht überschritten, solange das Gerät diesen Wert meldet.
- 0-W-Neutralisierung bleibt physisch wirksam.

### 5.3 Zendure-Neustart/Reconnect

- Command-State wird ungültig.
- ZEC aktiviert `smartMode=1` neu und wartet auf Rücklesung.
- Keine dynamischen Limits vor Flash-Schutzbestätigung.
- Nach bestätigtem Zustand wird die aktuelle Intention wiederhergestellt.

### 5.4 Offgrid-Test – erst später mit ungefährlichem Verbraucher

- `gridOffPower` steigt entsprechend der Last.
- `packInputPower` kann steigen, ohne dass `outputHomePower` steigt.
- Netzseitige Neutralisierung bleibt bestätigt, wenn `gridInputPower` und `outputHomePower` innerhalb der Toleranz liegen.
- Cross-Charge und Harvest verwenden keine Offgrid-Last als Hausnetzfluss.
- Offgrid-Modus wird von ZEC nicht verändert.

## 6. No-Regression-Vertrag

Unverändert bleiben sollen:

- normale AUTO-Zielwertbildung vor Gerätecap-Klemmung,
- Nacht-Festwert und Reserve-SOC,
- feste Modi,
- symmetrischer Cross-Charge-Schutz,
- Harvest-Entry/-Hold/-Exit und alle Formeln außer der neuen Command-/Power-Bewertung,
- Safe-State-Eintrittsbedingungen,
- lokale API-Architektur.

## 7. Nicht Bestandteil

- `SMA_FULL_OR_IDLE`-Absolutzielkorrektur,
- asynchroner Zendure-API-Worker,
- produktive Aktivierung der Offgrid-Steckdose,
- Änderung von `gridOffMode`,
- Settings-Redesign.

## 8. Buildvalidierung

```text
python3 -m py_compile *.py tools/*.py      OK
node --check static/status_v2.js           OK
bash -n tools/update_zendure_controller.sh OK
python3 -m unittest discover -s tests -q   399 Tests, OK
```

## 9. Dateien

### Neu

```text
tests/test_v12_11_2_rc12_command_contract.py
TECHNICAL_NOTES_V12_11_2_RC12.md
RELEASE_INFO_V12_11_2_RC12.md
UEBERGABE_ZEC_V12_11_2_RC12_COMMAND_CONTRACT_FLASH_OFFGRID.md
```

### Fachlich geändert

```text
command_lifecycle.py
controller_logic.py
measurement.py
measurement_v4.py
measurement_v4_contract.py
mqtt_bridge.py
operational_events.py
state.py
zendure_power_observation.py
config_manager.py
config.example.json
web_ui.py
status_page_v2.py
static/status_v2.js
README.md
README_INSTALLATION.md
version.py
bestehende Regressionstests mit bewusst geänderter Semantik
```

### Gelöscht oder umbenannt

```text
keine Dateien
```
