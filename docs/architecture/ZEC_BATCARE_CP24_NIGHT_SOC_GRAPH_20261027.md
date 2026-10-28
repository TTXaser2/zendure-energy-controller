# ZEC Battery Care – CP24, historisch belegte NIGHT-Untergrenze

**Stand:** 27.10.2026 · `ZEC-BL-BATCARE-001` · `ENGINEERING_AS_BUILT / DEVELOPMENT_NOT_INSTALLABLE`

## Quellengebundene Regel

`battery_care_graph_history.care_day_lines()` verwendet unverändert ausschließlich die damals gespeicherten CP22-Konfigurationssegmente und die tatsächlich aufgezeichneten SOC-Tagesgraph-Modusproben. Für `AUTO` gilt `max(MIN_SOC, R)`, für das **explizit beobachtete** `NIGHT_DISCHARGE` innerhalb des historisch aufgezeichneten gültigen lokalen Nachtfensters `max(MIN_SOC, R, NIGHT_DISCHARGE_STOP_SOC_PERCENT)`; wenn die Night-Stop-Grenze damals nicht konfiguriert war, bleibt `max(MIN_SOC, R)` maßgeblich. Historische Nicht-NIGHT-Modi beweisen niemals eine feste NIGHT-Entladung. Ein einzelner Nachtmesspunkt, Modewechsel, STOP, ein Gap größer als drei Minuten, ein fehlerhaftes Nachtfenster oder ein fehlender Care-Konfigurationsnachweis erzeugen keine durchgehende NIGHT-Linie. Über Mitternacht reichende Nachtfenster werden in zwei lokale Tagesabschnitte getrennt; es werden keine NIGHT-Linien über den Tagesrand hinaus fortgeführt. Nachtreserve über R bleibt erhalten, die Policy wird nicht abgesenkt.

## Graph und API

- Tages-API liefert nur bei belegtem Modus eine `configured_seasonal_night_policy` mit `night_floor_soc` und gemeinsamer `effective_discharge_floor_soc`; bestehende `configured_seasonal_auto_policy` erhält ebenfalls letzteren Wert, ihr `auto_floor_soc` bleibt rückwärtskompatibel.
- Standardansicht zeichnet maximal **eine Art** zusätzliche Care-Entladegrenzenlinie, über die zeitlich getrennten AUTO- bzw. NIGHT-Abschnitte; Legende und Tooltip kennzeichnen `AUTO` oder `NIGHT`, die historische Grenze ausdrücklich als **rekonstruierte Policy**. `Care-Details` behält die N/E-Linien und ausschließlich tatsächlich persistierte Fehlervorfall-/Recovery-Marker.
- Die CPU-/DB-/Sampling- und Controller-Dispatch-Pfade bleiben unverändert. Keine neue 1-Hz-Messung oder Ereignissynthese. Serverseitiger und clientseitiger SOC-Tagescache wurden für den geänderten historischen Linienvertrag versioniert.

## Nicht behauptete Wirksamkeit und offene Fachpunkte

Die gerenderte Untergrenze belegt nur, welche ZEC-Schwelle **nach belegtem Modus und historischer Konfiguration** rechnerisch galt. Sie bestätigt weder Gerätedurchsetzung, physische Batterieladung noch einen Hersteller-/BMS-Grenzwert. Insbesondere fehlen für positive Start-/Endmarker der Care-PV-, Netzpflege- und Notladephasen weiterhin eigenständig persistierte Reglerereignisse. Diese müssen über den vorhandenen Operational-Event-Store mit Debounce/Dedupe und stabiler Episoden-ID geschaffen werden; reine SOC-Übergänge, hypothetische Shadow-Ziele und MQTT-ACKs bleiben als Marker unzulässig. Reale Pi-/iPhone-Feld-, manuelle UML-/Dokumentations-, Installer-, Backup-/Rollback- und Release-Gates stehen aus. Produktiv bleibt V17.1.3. Das Checkpoint-, Manifest-, Regression- und Browsergate wird nur nach tatsächlich erfolgter Prüfung als PASS ausgewiesen.
