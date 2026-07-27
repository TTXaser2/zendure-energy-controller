# Zendure Energy Controller V12.11.2-RC12

## Aktueller Release

V12.11.2-RC12 ist der sicherheitsorientierte Nacharbeitsrelease zu RC11. Er setzt den auf dem produktiven SolarFlow 2400 AC+ verifizierten Zendure-MQTT-Command-Vertrag um und schützt dynamische Regeländerungen vor unbeabsichtigten persistenten Flash-Schreibvorgängen.

Wesentliche Änderungen:

- Aktive Lade- und Entladebefehle werden erst freigegeben, wenn `smartMode=1` frisch rückgelesen wurde.
- Der produktive ZEC-Laufzeitpfad kann `smartMode` ausschließlich aktivieren; `smartMode=OFF` ist im Runtime-Setter gesperrt.
- Bei unveränderter Richtung wird nach bestätigtem Command-State nur das aktive Leistungslimit aktualisiert.
- Start, Reconnect, Richtungswechsel, unsicherer Command-State und Recovery verwenden einen vollständigen Modus-/Limit-Abgleich; redundante `smartMode`-Schreibvorgänge werden vermieden, wenn `smartMode=1` bereits frisch bestätigt ist.
- `chargeMaxLimit` und `inverseMaxPower` werden ausschließlich gelesen und als zusätzliche Zielwertgrenzen berücksichtigt.
- ZEC schreibt weder `inverseMaxPower`, `chargeMaxLimit`, `gridOffMode`, `socSet`, `minSoc` noch andere dauerhafte Gerätekonfigurationen.
- Zendure-Leistungsflüsse werden elektrisch getrennt modelliert: Netzport, Batterie und Offgrid-Ausgang.
- `outputPackPower` gilt korrekt als Batterieladung, `packInputPower` als Batterieentladung und `gridOffPower` bleibt eine eigene Offgrid-Last.
- Eine aktive Offgrid-Last kann eine netzseitige 0-W-Neutralisierung nicht mehr fälschlich widerlegen.
- High-SOC-Ladeannahmebegrenzung wird von einem verlorenen Command-State unterschieden.
- Ein Mismatch, der durch einen neuen Sicherheitsintent beendet wird, gilt nicht mehr fälschlich als wiederhergestellt.
- Full-State-Resync und Full-State-Sicherheitsneutralisierung besitzen getrennte Publish-Ereignisse.
- Measurement V4 erhält additive Command-Readback-, Flash-Schutz-, Gerätecap- und Offgrid-Felder. RC10- und RC11-Dateien bleiben unverändert erhalten; RC12 beginnt automatisch eine neue Header-Sitzung.

Ausführliche Informationen:

```text
TECHNICAL_NOTES_V12_11_2_RC12.md
RELEASE_INFO_V12_11_2_RC12.md
UEBERGABE_ZEC_V12_11_2_RC12_COMMAND_CONTRACT_FLASH_OFFGRID.md
```

## Sicherheitsabgrenzung

RC12 kann keine absolute Garantie gegen jeden Geräte- oder Flashdefekt geben. Die Implementierung minimiert das Risiko jedoch durch eine harte Runtime-Invariante: Dynamische Leistungsänderungen werden nur bei frisch bestätigtem `smartMode=1` ausgeführt; persistente Geräteeinstellungen werden nicht durch ZEC verändert.

Bei einer sicherheitsrelevanten Neutralisierung hat das unverzügliche Setzen beider Limits auf 0 W Vorrang. Falls `smartMode` zu diesem Zeitpunkt nicht bestätigt ist, sendet ZEC zuerst `smartMode=ON` und anschließend den neutralen vollständigen Zustand über denselben MQTT-Client. Dadurch wird eine Sicherheitsneutralisierung nicht durch eine fehlende Rücklesung blockiert.

## Bewusst nicht enthalten

- Korrektur der absoluten `SMA_FULL_OR_IDLE`-Zielwertformel,
- asynchrone Entkopplung der lokalen Zendure-API,
- Änderungen an der Offgrid-Konfiguration,
- Wiederaufnahme des pausierten Settings-Redesigns.

## Installation

Siehe `README_INSTALLATION.md`.
