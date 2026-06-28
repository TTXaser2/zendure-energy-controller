# TECHNICAL NOTES – V12.10.0-RC10

## Ziel

V12.10.0-RC10 ist ein kleiner Nacharbeits-RC auf Basis von RC9. Die Harvest-Regelstrategie selbst wird nicht verändert. Der Fokus liegt auf Transparenz, UI-Lesbarkeit und reproduzierbarer Diagnose.

## Änderungen

- Settings-Dark-Theme: Abschnitts-/Infoboxen im Bereich „Zweitbatterie“ nutzen nun kontrastreiche dunkle Karten statt heller Boxen mit blasser Schrift.
- Statusseite: Restüberschuss-Ernte wird in der SMA-/Zweitbatterie-Statusbox angezeigt, getrennt nach Konfiguration, Bereitschaft und Aktivität/Entry-Fortschritt.
- Nachtmodus-Prognose: Fehlende Voraussetzungen werden genauer benannt; bei fehlender Prognosekapazität verweist die Meldung ausdrücklich auf `Settings → Nachtmodus`.
- Config-Hash: Harvest-relevante Parameter sind nun im `config_control_hash` enthalten, damit Config-Snapshots nach Aktivierung/Änderung der Restüberschuss-Ernte nicht irreführend alte Parameter zeigen.

## Nicht geändert

- Keine Änderung an Entry-/Stay-/Exit-Strategie der Restüberschuss-Ernte.
- Keine neue Regelstrategie.
- Keine MQTT-Topic- oder Kommandostrukturänderung.
- Keine vollständige allumfassende Settings-Querabhängigkeitsprüfung; diese bleibt als eigenes Backlog-Thema bestehen.
