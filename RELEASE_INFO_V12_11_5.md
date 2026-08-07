# Release-Informationen – Zendure Energy Controller V12.11.5

## 1. Identität

```text
Version:  12.11.5
Label:    V12.11.5
Build-ID: v12.11.5-20260807
Typ:      reiner Bugfix
Basis:    V12.11.4 / v12.11.4-20260807
```

## 2. Korrekturen

- Desktop-Settings besitzen eine feste Shell; primär vertikal scrollt nur die rechte Contentfläche, die Sidebar bei Bedarf separat.
- Das Nachtfenster wird als zwei fachliche `HH:MM`-Felder für Start und Ende dargestellt; die vier bestehenden technischen Config-Keys bleiben unverändert und werden paarweise atomar übertragen.
- Der mobile Kategorien-Drawer besitzt einen robusten Body-Scroll-Lock, eigenen vertikalen Scrollbereich und Overscroll-Eindämmung ohne globale `touchmove`-Sperre.
- Fachlich blockierte `/settings/preview`-Antworten mit HTTP 422 werden als normaler Validierungsdialog mit vollständigen Issues, Feldmarkierung und Sprung zum betroffenen Setting dargestellt.
- `Last-Good-Pointer reparieren` wurde aus der globalen Change-Set-Leiste entfernt und befindet sich nur noch unter `Experte → System & Diagnose → Administrative Aktionen → Last-Good-Konfigurationsspeicher`.
- Kategorien ohne im aktuellen Modus sichtbare Settings zeigen einen erklärenden Empty-State; Navigationszähler zeigen die tatsächlich sichtbare Anzahl.

## 3. Sicherheitsabgrenzung

V12.11.5 ändert keine Regellogik, keine Zielwertformel und keinen Command-/Measurement-Vertrag. Insbesondere bleiben die geschützten Dateien byteidentisch zur V12.11.4-Basis:

```text
controller_logic.py
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
measurement_v4.py
measurement_v4_contract.py
```

Die serverseitige Last-Good-Pointer-Reparatur bleibt unverändert fail-closed. Das Frontend trifft keine Slotwahl.

## 4. Installer

Der Installer erkennt V12.11.4 / `v12.11.4-20260807` ausdrücklich als zulässigen Ausgangsstand. Preflight vor Dienststopp, vollständiges Rollbackbackup, bestehende idempotente Configmigration, lokale Abschlussprüfung und der produktiv bestätigte sichere Transitional-Readback-Vertrag bleiben erhalten.

## 5. Feldabnahme nach Installation

Mindestens prüfen:

- Version/Build-ID und Dienststatus;
- `/health` und `/ready`;
- Desktop-Scrollshell und Kategorie-Scroll-to-top;
- Nachtfenster mit Start/Ende als `HH:MM`;
- blockierter Previewdialog bei absichtlich ungültiger Mehrfeldkombination;
- Mobile-Drawer auf mindestens einem Smartphone;
- Empty-State `Kommandowirkung & Resync` im Standardmodus;
- Last-Good-Aktion nur im Experten-Adminbereich.
