# Release-Informationen – Zendure Energy Controller V12.11.4

## 1. Identität

```text
Version:  12.11.4
Label:    V12.11.4
Build-ID: v12.11.4-20260807
Typ:      Bugfix
Basis:    V12.11.3
```

## 2. Scope

- mobiles Kategorienmenü funktionsfähig;
- mobile Änderungsprüfung intern scrollbar und vollständig bedienbar;
- Hintergrundscrollen bei offenem Modal gesperrt;
- Kategorieauswahl beginnt am Kategorienanfang;
- alte offene MQTT-/Zendure-Telemetrieereignisse werden anhand des fachlichen Ereignistyps reconciled;
- Warnungszähler zwischen globalem Header und offenen Ereignisgruppen konsistent;
- geschützter manueller Dienstneustart in Expert → System & Diagnose;
- responsive Header- und Overflow-Korrekturen.

## 3. Nicht Bestandteil

- keine Regleränderung;
- keine neue Zielwertformel;
- keine Änderung des Command-Vertrags;
- keine Änderung von Readiness oder Installer-Abnahme;
- keine Settings-Hilfe-/Redaktionsneuentwicklung;
- keine Konfigurationsprofile;
- keine Graph-, Storage- oder Simulationsneuentwicklung.

## 4. Produktivabnahme

Nach Installation sind mindestens zu prüfen:

- Version und Build-ID;
- Dienst `active`;
- `/health` und `/ready`;
- mobiler Drawer;
- modale Änderungsprüfung;
- Kategorie-Scrollposition;
- offene Ereignisse;
- manueller Restart-Eintrag im Expertenmodus.
