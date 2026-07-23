# Zendure Energy Controller V12.11.2-RC8 – Installation und Betrieb

## 1. Update installieren

Die Datei `zendure_controller_v12_11_2_rc8.zip` unverändert nach `/home/pi/Downloads/` kopieren und ausführen:

```bash
cd /home/pi/Downloads
/opt/zendure-controller/tools/update_zendure_controller.sh v12_11_2_rc8
```

Das Update-Skript erstellt automatisch ein vollständiges Installationsbackup und sichert die produktive `config.json` separat.

## 2. Ready-Check

Das Update-Skript wartet nun bis zu 20 Sekunden auf gültiges JSON von `/ready`.

Erfolgsabschluss:

```text
Update abgeschlossen und Ready-Check erfolgreich.
```

Zusätzliche manuelle Prüfung:

```bash
systemctl status zendure-controller.service --no-pager -l
curl -fsS http://127.0.0.1:8080/ready | python3 -m json.tool
```

Browser anschließend aktualisieren:

```text
Desktop: Strg+F5
iOS: Seite neu laden; bei Bedarf Tab schließen und neu öffnen
```

## 3. Erwartete RC8-Anzeigen

- Der SOC-Tagesgraph zeigt konsistente Lade-/Entladephasen deutlich weniger treppenartig.
- Echte lange Plateaus, Datenlücken, Richtungswechsel und größere Sprünge bleiben sichtbar.
- Tooltip und Datenbank zeigen weiterhin die gespeicherten Original-SOC-Werte.
- Unter `Aktiver Gesamtdurchlauf` erscheint beispielsweise:

```text
Zyklusabstand ca. 2,05 s · aktive Arbeit 2,4 %
```

- Die Farbpunkte vor den Timing-Teilphasen entsprechen exakt den Segmentfarben im gestapelten Balken.
- Der Verteilungsbalken enthält nur synchrone Teilphasen; SQLite bleibt separat als asynchrone Hintergrundarbeit.
- Eine rote Slow-Cycle-Kennzeichnung erscheint nur bei Überschreitung von `SLOW_CYCLE_WARN_MS`.
- Eine alte gelbe MQTT-Unsicherheitswarnung verschwindet, sobald Sollwert 0 W und frische Gerätewirkung innerhalb der Toleranz neutral sind.

## 4. Migration

- Keine Konfigurationsmigration erforderlich.
- Keine Datenbankmigration erforderlich.
- Keine Änderung des Messdaten- oder Ereignisschemas.

## 5. Hinweise

Einzelne ältere SQLite-Tests können unter neueren Python-Versionen weiterhin `ResourceWarning: unclosed database` ausgeben. Dies ist ein bestehender Test-/Wartungspunkt und kein Laufzeitfehler des produktiven SQLite-Workers. Maßgeblich ist der Abschluss der Tests mit `OK`.
