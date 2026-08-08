# Technical Notes – V12.11.7

## 1. Default-Provenienz als Registry-Vertrag

`SettingSpec` trägt ab V12.11.7 explizite Metadaten für die Herkunft und die zulässige Resetsemantik eines Settings.

Defaultklassen:

```text
PRODUCT_DEFAULT   getesteter allgemeiner Produktwert
PROFILE_PRESET    Wert eines bewusst gewählten Profils/Strategiepresets
SAFE_SENTINEL     sicherer Ausgangszustand, keine Betriebswertempfehlung
LEGACY_INTERNAL   Migration/Deployment/Kompatibilität; kein Benutzerdefault
INSTALLATION      anlagen-, hardware- oder nutzerspezifisch
AUTO_OR_UNSET     bewusst nicht gesetzt bzw. automatisch abgeleitet
```

Reset-Policies:

```text
DEFAULT
CLEAR
AUTO
PROFILE
NONE
```

Die Registry bleibt die Autorität; `settings_model.py` leitet die UI ausschließlich aus diesen Metadaten ab.

## 2. Bootstrap, Migration und Produktdefault sind getrennt

V12.11.7 behandelt drei zuvor vermischte Rollen getrennt:

```text
bootstrap_value
    sicherer Ausgangswert für eine fehlende Erstkonfiguration

default_rc19 / historische Migrationswerte
    ausschließlich Kompatibilitäts-/Migrationssemantik

product_default
    optionaler, tatsächlich allgemeiner Produktstandard
```

Das historische Feld `default_new_install` bleibt aus Kompatibilitätsgründen erhalten, ist aber nicht mehr die First-Install-Autorität.

`config_manager.DEFAULT_CONFIG` bleibt als Legacy-/Runtime-Kompatibilitätsmap für bestehende Aufrufer erhalten. Der Settings-/First-Install-Vertrag wird durch `SettingsRegistry` bestimmt.

## 3. Server-seitige Reset-Policy

Bis V12.11.6 schützte vor unzulässigen Defaultresets primär die UI. Der generische API-Operator `reset_default` konnte bei editierbaren Nicht-Secret-Settings weiterhin `default_new_install` einsetzen.

Ab V12.11.7 prüft `settings_service.py` die Registry-`reset_policy` serverseitig:

- `NONE` → blocking issue `RESET_NOT_ALLOWED`;
- `DEFAULT` → definierter Produkt-/Sentinelwert;
- `CLEAR` / `AUTO` → definierte Leersemanik;
- `PROFILE` → Registry-definierter Profilwert.

Damit ist die UI nicht mehr die einzige Schutzschicht.

## 4. First-Install State Machine

Fehlt `config.json`, liefert `SettingsRuntimeManager` einen diagnostischen Bootstrap-Snapshot und Startupmodus:

```text
FIRST_INSTALL_SETUP
control_allowed = false
```

Preview und Commit laufen mit `ValidationContext(first_install=True)`. Ein First-Install-Kandidat wird aus dem kanonischen Bootstrapvertrag aufgebaut und nicht durch historische Migrationsdefaults ersetzt.

Pflichtwerte müssen ausdrücklich im First-Install-Draft vorkommen. Quellabhängige Pflichtparameter werden ebenfalls validiert.

Erst nach:

```text
expliziter Eingabe
→ vollständigem Preview
→ Validation
→ atomischem Commit
→ erneut gültigem Runtime-Load
```

kann der normale Startupmodus erreicht werden.

## 5. Preview-/Commit-Kontext

Der validierte `ValidationContext` wird im `PreviewRecord` gespeichert und beim Commit wiederverwendet. Dadurch bleiben First-Install- und Preflightbedingungen zwischen Preview und Commit identisch; ein Commit kann nicht versehentlich mit einer schwächeren oder anderen Kontextsemantik revalidiert werden.

CAS-/Revisionprüfungen bleiben unverändert Bestandteil des Commitvertrags.

## 6. Neutraler `config.example.json`

Anlagenabhängige Werte werden nicht länger als scheinbare Empfehlungen ausgeliefert. Unter anderem sind neutralisiert:

```text
DEVICE_ID
MQTT_BROKER
MQTT_USER
GRID_METER_SOURCE
SHELLY_IP
MAX_CHARGE_POWER_W
MAX_DISCHARGE_POWER_W
MIN_SOC_PERCENT
MAX_SOC_PERCENT
SECOND_BATTERY_DISPLAY_NAME
ZENDURE_LOCAL_IP
```

`MEASUREMENT_LOG_MODE` ist im neutralen First-Install-Template `off`.

Die Datei ist damit eine Setup-Vorlage und nicht automatisch eine produktiv freigabefähige Konfiguration.

## 7. Bestehende Installationen

Eine vorhandene gültige `config.json` wird durch V12.11.7 nicht anhand des neuen Bootstrap-/Produktdefaultvertrags umgeschrieben. Insbesondere bleiben individuelle Leistungs-, SOC-, Nacht-, MQTT- und Measurementwerte erhalten.

Die bestehende RC19→RC20-Migration bleibt idempotent und ist nicht zur Defaultnormalisierung erweitert worden.

## 8. No-Regression-Abgrenzung

Nicht verändert werden:

- AUTO-, HOLD-, NIGHT- und feste Regleralgorithmen;
- Harvest-Zielwertbildung;
- Cross-Charge;
- SmartMode-/Flash-Schutz;
- Command-State, Readback, Effect, Resync und Late-Effect-Guard;
- Zendure Power Observation;
- Measurement-V4-Writer und -Contract;
- V3-Legacy-Reader/-Writer-Aufräumarbeiten;
- Excel-Lernsimulation.
