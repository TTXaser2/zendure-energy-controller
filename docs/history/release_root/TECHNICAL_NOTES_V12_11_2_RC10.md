# Technische Hinweise V12.11.2-RC10

## 1. Zweck und Abgrenzung

RC10 schließt die Statusseitenrunde mit einem topologiefähigen Renderer und einem passiven Live-Vorschaudienst ab. Das Release verändert weder Controllerzustandsmaschine noch Regelalgorithmus.

Unterstützte UI-Topologien:

```text
A: 1× Zendure, kein Primärspeicher
B: 1× Zendure, Primärspeicher vorhanden  (bestehender Produktivfall)
C: 2× Zendure, Primärspeicher vorhanden
```

Mehr als zwei Zendure-Units bleiben bewusst außerhalb des unterstützten Modells.

## 2. Gemeinsames Topologie-ViewModel

`build_status_view_payload(...)` liefert neu:

```json
"topology": {
  "primary_storage_present": true,
  "zendure_unit_count": 1
}
```

Die Primärspeicherstruktur enthält zusätzlich `present`. Bei nicht vorhandenem Primärspeicher werden ihre fachlichen Werte neutral beziehungsweise leer geliefert und keine vermeintliche Stale-Warnung erzeugt.

Der Tagesgraph-Payload enthält `primary_storage_present`. Die JavaScript-Seite erzeugt Legende, Linie und Tooltip-Zeile des Primärspeichers nur, wenn dieser Teil der Topologie ist.

Die Anwesenheit wird in dieser Priorität bestimmt:

```text
1. expliziter Snapshotwert primary_storage_present
2. UI-only Config-Override STATUS_PRIMARY_STORAGE_PRESENT
3. Kompatibilitätsdefault true
```

Der Default `true` verhindert eine sichtbare Änderung bestehender Installationen. Cross-Charge- oder Harvest-Schalter werden bewusst nicht als Hardwareerkennung missbraucht.

## 3. Zwei Zendure-Units

Der bereits vorhandene Unit-Pfad wird nun durch das explizite Topologie-ViewModel und die Vorschau validiert:

- maximal zwei Units,
- zwei SOC-Ringe,
- Name, SOC, Istleistung, Ziel, Kapazität und Zustand je Unit,
- gemeinsame Systemzusammenfassung,
- getrennte SOC-Reihen im Tagesgraph.

RC10 implementiert keine Aufteilung oder Versendung realer Kommandos an eine zweite Headunit. Der Renderer ist vorbereitet, sobald ein reales Backend `zendure_units_json` beziehungsweise äquivalente Unit-Daten liefert.

## 4. Passiver Vorschau-Dienst

Neue Dateien:

```text
tools/status_preview.py
tools/status_preview_scenarios.py
tools/STATUS_PREVIEW_README.md
systemd/zendure-status-preview.service
```

Der Dienst läuft standardmäßig auf Port 8091 und verwendet:

- `render_status_page_v2(...)`,
- `static/status_v2.css`,
- `static/status_v2.js`,
- synthetische, zeitlich bewegte Status-, Mini-Graph- und SOC-Tagesdaten.

Er importiert keine Controller-, MQTT-, State-, CSV- oder Datenbankkomponente. Es existieren ausschließlich GET-Routen:

```text
/
/status-view-data
/grid-mini-data
/storage-soc-day-data
/favicon.svg
/health
/ready
```

Das Banner kennzeichnet die Vorschau dauerhaft. Die systemd-Unit ist ressourcenbegrenzt und gehärtet (`CPUQuota`, `MemoryMax`, `NoNewPrivileges`, `ProtectSystem=strict`).

## 5. Sicherheitsbetrachtung

### Kein Latch

Es wird kein persistenter Reglerzustand erzeugt. Die Szenariowahl ist nur ein Query-Parameter des Vorschau-Dienstes.

### Keine Race Condition

Der Vorschauprozess besitzt keine Referenz auf den produktiven `ControllerState`. Seine Payloads werden rein funktional aus Zeit und Szenarioschlüssel erzeugt. Die produktive Topologie wird pro Snapshot gelesen und nicht in globalen Steuerzustand geschrieben.

### Keine Prioritätsumkehr

Weder Vorschau noch Renderer nehmen an Controllerentscheidungen teil. Es gibt keinen Aufruf aus dem Regelzyklus und keinen synchronen Netzwerkzugriff aus der Controllerlogik.

### Kein Eingriff in MQTT-Dedupe oder Resync

Der Vorschaudienst erzeugt keinen MQTT-Client und kann weder Kommandos senden noch Dedupe-/Resync-Zustände verändern.

## 6. Nicht-Ziele

Nicht Bestandteil von RC10:

- reale Multi-Headunit-Regelung,
- allgemeiner Szenario-Editor,
- Integration mit dem späteren Simulationsdienst,
- Settings-Redesign,
- Graph-Seiten-Redesign,
- Expertenansicht,
- Änderung der produktiven Hardwarekonfiguration.

## 7. Tests

Neue Regressionstests decken ab:

- Topologie mit und ohne Primärspeicher,
- Unterdrückung falscher Primärspeicherwarnungen,
- Primärspeicherreihe im Tagesgraph,
- Single- und Dual-Zendure-Vorschau,
- dynamische synthetische Daten,
- ausschließlich lesende Preview-Routen,
- gemeinsame CSS-/JavaScript-Ressourcen,
- nicht automatisch aktivierte und gehärtete systemd-Unit,
- rückwärtskompatible Darstellung der bestehenden Topologie.
