# ZEC V12.11.2-RC20 Fix 6 – UI-, Ereignis- und SOC-Recovery-Bericht

## 1. Ausgangsbefund

Der produktive Fix-5-Stand war technisch gesund, blieb aber bei erreichtem Maximal-SOC im Modus `SAFE_STATE`. Sämtliche Daten- und Command-Gates waren gleichzeitig grün, `consecutive_errors=0`, es fehlten keine Pflichtquellen und der einzige aktive Limiter war `MAX_SOC`. Zusätzlich blieben historische MQTT- und Telemetrieereignisse als offen sichtbar, obwohl die aktuellen Liveprüfungen gesund waren.

## 2. Ursachen

1. `MAX_SOC` und `MIN_SOC` verwendeten denselben `safe_state()`-Pfad wie echte Störungen. Ein erwarteter Schutzgrenzzustand machte dadurch `/ready` falsch-negativ.
2. Der Event-Journal-Resolver schloss nur die jüngste offene Zeile. Mehrere ältere offene Zeilen desselben Dedupe-Schlüssels konnten dauerhaft als aktive Fehler bestehen bleiben.
3. Beim ersten gesunden Zustand nach Prozessstart fand keine vollständige Reconciliation historischer offener Ereignisse statt.
4. Settings und Graph verwendeten nicht durchgängig dieselbe globale Navigation und Statusampel wie die Statusseite.
5. Das Settings-Innenlayout verschwendete Breite und koppelte Label/Hilfe optisch von Eingabefeldern ab.
6. Der Preview-Abbruch aktualisierte die Aktionsleiste nicht.
7. Der Storage-Snapshot war als HTTP-Leseweg O(1), der Hintergrundaufbau scannte aber weiterhin unveränderte Bestände erneut.

## 3. Umsetzung

### Regelzustand

- Erwartete SOC-Grenzen neutralisieren auf 0 W und wechseln nach `HOLD`.
- Limiter, Regelgrund, technischer Pfad und letzte Aktion bleiben sichtbar.
- `safe_state_counter` wird nicht erhöht.
- Fehlender oder staler SOC bleibt echter `SAFE_STATE`.

### Ereignisse

- Ein gesunder Zustand schließt alle offenen Zeilen desselben Dedupe-Schlüssels.
- MQTT wird beim ersten gesunden Livebild sofort reconciled.
- Zendure-Telemetrie wird nach dem vorhandenen Stabilitätsfenster reconciled.
- Historische Zeilen bleiben in der Datenbank und werden nur auf `resolved` gesetzt.
- Aktive offene Fehler/Warnungen steuern die globale Statusampel aller Hauptseiten.

### Gemeinsame UI

- Status, Graph und Settings verwenden dieselbe Topbar.
- Der Punkt neben „Status“ zeigt live `ok`, `warn`, `bad` oder `unknown`.
- Settings nutzt die verfügbare Breite.
- Jede Setting-Kachel ordnet Label, Erklärung, Eingabe und Metadaten vertikal zu.
- Zwölf Kategorie-Icons ersetzen die radiobuttonähnlichen Markierungen.
- Die Preview kann nach Abbruch ohne künstliche Zwischenänderung erneut geöffnet werden.
- Dienstneustart erscheint nur bei tatsächlich ausstehendem Neustart.
- Primärspeicher-Langtexte sind gestapelt und umbrechen kontrolliert.

### Storage

- Persistenter Inventarcache auf Basis Größe und `mtime_ns`.
- Manifestdaten werden für bekannte Dateien übernommen.
- Nur neue, geänderte oder unbekannte Dateien werden gescannt.
- Cachewrite erfolgt atomar inklusive `fsync`.

## 4. Nicht-Ziele und Invarianten

- Keine Änderung der energetischen Zielwertformeln.
- Keine Änderung von Harvest-, Cross-Charge-, Command- oder MQTT-Strategien.
- Keine zusätzlichen Lade-/Entladerichtungswechsel.
- SOC-Grenzneutralisierung sendet nur den bereits erforderlichen 0-W-Schutzübergang.
- Echte Daten- und Commandfehler bleiben fail-closed.

## 5. Ergebnis

```text
Build-ID:                            rc20-audit-fix6-20260806
unittest:                            635 bestanden
unittest ResourceWarning=Error:      635 bestanden
pytest:                              635 bestanden
pytest-Subtests:                     677 bestanden
Browser-Pageerrors:                  0
HTTP-Smoke:                          PASS
```

**Exit-Gate: PASS für kontrollierte Fix-5→Fix-6-Installation.**
