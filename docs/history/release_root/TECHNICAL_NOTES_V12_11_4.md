# Technical Notes – V12.11.4

## 1. Mobile Category Drawer

Der Drawer besitzt einen expliziten offenen Zustand, einen eigenen Backdrop und synchronisierte ARIA-Attribute. Er wird nicht mehr nur über eine Desktop-Sidebar-Annahme gesteuert.

Schließpfade:

```text
Burger erneut
Backdrop
Kategorieauswahl
Escape
```

## 2. Modal Scroll Contract

Beim Öffnen der Änderungsprüfung wird die aktuelle Window-Scrollposition gespeichert und der Dokumenthintergrund fixiert. Der Dialog ist ein Flex-Container mit eigenem scrollbaren Body und festen Kopf-/Aktionsbereichen. Beim Schließen wird die Scrollposition wiederhergestellt.

## 3. Category Scroll Reset

Normale Kategorieauswahl ruft nach dem Rendern `scrollCategoryToTop()` auf. Suchtreffer behalten ihre gezielte Feldnavigation.

## 4. Event Reconciliation

Die Auflösung offener Incidents berücksichtigt neben dem aktuellen `dedupe_key` den kanonischen `event_type`. Dadurch können historische offene Zeilen mit älteren oder leeren Dedupe-Schlüsseln geschlossen werden. Andere Ereignistypen werden nicht berührt.

## 5. Manual Restart Action

Die administrative Aktion wird im Expertenmodus ausschließlich in der Kategorie `System & Diagnose` gerendert und verwendet den bereits bestehenden geschützten Restart-Endpunkt einschließlich Bestätigung, CSRF-/Origin-Prüfung, Single-Flight, Cooldown und anschließender Betriebsprüfung.

## 6. Responsive Contract

- Das Dokument selbst darf nicht horizontal überlaufen.
- Die globale Hauptnavigation bleibt ein bewusst horizontal scrollbarer Binnenbereich.
- Der mobile Settings-Kontextkopf nutzt zwei Zeilen.
- Der Kategorien-Drawer und sein Backdrop beginnen unterhalb der beiden globalen Kopfbereiche.

## 7. No-Regression

Byteidentisch zu V12.11.3 bleiben insbesondere:

```text
controller_logic.py
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
measurement_v4.py
measurement_v4_contract.py
```
