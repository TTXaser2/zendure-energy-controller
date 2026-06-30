# Technical Notes V12.11.0-RC3

V12.11.0-RC3 ist ein Sicherheits-/Diagnosefix für die in RC2 eingeführte direkte SMA-Home-Manager-/SMA-Energy-Meter-Netzleistungsquelle.

## Ziel

RC2 konnte die SMA-Direktquelle grundsätzlich passiv starten, war aber für Installationen mit mehreren SMA Energy Metern noch nicht ausreichend abgesichert. In der Nutzerinstallation existieren zwei SMA-Messquellen: der Netzbezugszähler/Home-Manager-Zähler und ein weiterer Energy Meter für den PV-Zaun. Die produktive Regelquelle muss eindeutig den Netzbezugspunkt auswählen.

## Änderungen

- Interface-Namen wie `eth0` werden nun für den Multicast-Join zu ihrer lokalen IPv4-Adresse aufgelöst.
- Der UDP-Socket setzt zusätzlich best-effort `SO_REUSEPORT`, damit paralleles Mitlesen neben UniMeter wahrscheinlicher funktioniert.
- SMA-Telegramme dekodieren nun zusätzlich:
  - SUSy-ID
  - Seriennummer
  - Quell-IP
- Neue Filter-Settings:
  - `SMA_ENERGY_METER_SUSY_ID`
  - `SMA_ENERGY_METER_SERIAL`
- Empfangene SMA-Geräte werden intern gesammelt und auf der Statusseite angezeigt.
- Die Statuskarte „SMA Direktquelle“ zeigt nun:
  - Interface und aufgelöste IPv4
  - konfigurierte Filter
  - ausgewähltes Gerät
  - erkannte Geräte mit Seriennummer/SUSy-ID/Wert/Alter
  - ignorierte Pakete
- Validator blockiert produktive SMA-Direktregelung ohne Seriennummernfilter.
- Passive Diagnose ohne Seriennummer bleibt erlaubt, weist aber auf die notwendige Filterung bei mehreren Energy Metern hin.

## Empfohlene Konfiguration für die Nutzerinstallation

```text
GRID_METER_SOURCE = shelly_http
SMA_ENERGY_METER_PASSIVE_ENABLED = true
SMA_ENERGY_METER_GROUP = 239.12.255.254
SMA_ENERGY_METER_PORT = 9522
SMA_ENERGY_METER_INTERFACE = eth0
SMA_ENERGY_METER_SUSY_ID = 372
SMA_ENERGY_METER_SERIAL = 3011954105
```

Shelly/UniMeter bleibt damit Regelquelle; SMA direkt wird nur parallel beobachtet.

## Nicht geändert

- Keine Änderung an AUTO-Regelstrategie.
- Keine Änderung an Restüberschuss-Ernte Entry/Stay/Exit.
- Keine Änderung an Cross-Charge-Regelwirkung.
- Keine Änderung an Nachtmodus-Regelwirkung.
- Keine Änderung an Zendure-MQTT-Kommandostruktur.
- Kein automatischer Wechsel auf SMA direkt.

## Tests

- `python3 -m py_compile *.py tools/*.py` → OK
- `python3 -m unittest discover -q` → 197 Tests OK
- `bash -n tools/create_zec_analysis_package.sh` → OK
