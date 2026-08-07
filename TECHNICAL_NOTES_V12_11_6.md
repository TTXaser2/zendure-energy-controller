# Technical Notes – V12.11.6

## 1. Client-/Server-Validierung

Der Browser validiert nur deterministische Einzelwerte frühzeitig. Die serverseitige Settings ValidationEngine bleibt authoritative. Es wird keine zweite komplexe Regelengine in JavaScript eingeführt.

Clientseitig unmittelbar geprüft werden:

```text
NUMBER_INVALID
VALUE_BELOW_MIN
VALUE_ABOVE_MAX
ENUM_INVALID
TIME_FORMAT_INVALID
```

Ein Server-Preview `HTTP 422 + status=blocked + issues[]` bleibt ein fachlicher Previewzustand und kein Transportfehler.

## 2. Default-UI-Vertrag

`settings_model.py` erzeugt für jedes dargestellte Setting eine reine UI-Policy `default_ui`. Diese verändert weder configured noch effective.

Klassen:

```text
default       echter, sicher rücksetzbarer Produktdefault
clear         semantisches Entfernen / automatische Ableitung
installation  installationsabhängig; kein Reset
reference     Ausgangs-/Referenzwert; keine universelle Empfehlung
none          kein allgemeiner Default / Secret / nicht editierbar
```

Der generische Resetbutton erscheint nur, wenn die Policy eine explizite sichere Aktion und einen Wert bereitstellt.

## 3. Neuinstallationswerte fester Profile

`config_manager.DEFAULT_CONFIG`, `config.example.json` und `settings_registry.default_new_install` verwenden 0 W für feste Nacht-/manuelle Leistungsprofile. `default_rc19` bleibt unverändert, damit Migrationshistorie und bestehende Konfigurationen nicht als neue Empfehlung umgedeutet werden.

Die bestehenden Validatoren verhindern die Aktivierung eines entsprechenden festen Modus ohne positive konfigurierte Leistung.

## 4. Admin-Modals

Die native Browserfunktion `confirm()` wird auf der Settings-Seite nicht mehr verwendet.

Controller-Neustart:

- genau eine strukturierte Bestätigung;
- Warnung über Draft nur bei tatsächlich offenen Änderungen;
- danach bestehender geschützter Restart-Helper und Ready-Poll.

Last-Good-Pointer:

- unveränderte serverseitige Preview-/Commit-Endpunkte;
- Frontend zeigt ausschließlich das serverseitig bestimmte Ziel und dessen Identität;
- Frontend wählt keinen Slot.

## 5. Status-Info-Popover

`status_v2.js` hinterlegt für `Controller & Schnittstellen` strukturierte JSON-Daten im DOM. `setupInfoPopovers()` rendert daraus sichere DOM-Knoten mit `textContent`; andere Info-Popover behalten ihren bisherigen Textfallback.

Die Abschnitte sind:

```text
Aktueller Regelzyklus
Statistik · jüngste Durchläufe
Lokale Zendure-API
Einordnung
```

## 6. Ordering

Die fachliche Reihenfolge wird als UI-only Mapping in `settings_model.py` geführt. Registry-Keys, Codecs, serverseitige Semantik und Persistenzreihenfolge werden nicht verändert.

## 7. Installer

Normaler Quellstand ist V12.11.5 / `v12.11.5-20260807`. Der Readiness-Klassifizierer erwartet V12.11.6 / `v12.11.6-20260808`. READY-/TRANSITIONAL-/REJECT-Logik bleibt unverändert.
