# ZEC Status UI Preview

Der Status-Vorschaudienst rendert dieselbe Statusseite wie der produktive Controller, verwendet aber ausschließlich synthetische Live-Daten.

## Sicherheitsgrenzen

Der Dienst:

- startet keine Controllerinstanz,
- verbindet sich nicht mit MQTT,
- sendet keine Zendure-Kommandos,
- liest und schreibt keine `config.json`,
- schreibt weder Measurement- noch Ereignisdatenbanken,
- läuft separat auf Port 8091.

Das gelbe Banner `UI-VORSCHAU · Simulierte Speicher- und Statusdaten · keine Steuerwirkung` bleibt dauerhaft sichtbar.

## Szenarien

- `zendure_only`: eine Zendure-Unit ohne Primärspeicher
- `dual_zendure_primary`: zwei Zendure-Units mit Primärspeicher

## Start per systemd

Die Unit wird vom RC10-Update installiert, aber nicht automatisch aktiviert:

```bash
sudo systemctl start zendure-status-preview.service
systemctl status zendure-status-preview.service --no-pager -l
```

Browser:

```text
http://<PI-IP>:8091/
```

Dauerhaft aktivieren ist für die reine UI-Prüfung nicht erforderlich. Nach Abschluss:

```bash
sudo systemctl stop zendure-status-preview.service
```

## Direkter manueller Start

```bash
cd /opt/zendure-controller
python3 tools/status_preview.py --host 0.0.0.0 --port 8091
```

Optionaler Dark-Mode-Test:

```bash
python3 tools/status_preview.py --host 0.0.0.0 --port 8091 --dark
```

## Verhältnis zum realen Betrieb

Der Preview-Dienst nutzt dieselben produktiven Renderingpfade. Für eine spätere reale Installation ohne Primärspeicher versteht die Statusseite den Snapshotwert `primary_storage_present=false` sowie den UI-only Config-Override:

```json
"STATUS_PRIMARY_STORAGE_PRESENT": false
```

Der Override beeinflusst nur die Darstellung. Er deaktiviert keine Datenquelle oder Regelfunktion. Die reale Steuerung zweier Headunits ist nicht Bestandteil des Preview-Dienstes.
