# Release Info – Zendure Energy Controller V12.11.2-RC19

## Zweck

RC19 ist ein eng begrenzter **Status-/Diagnose-Stabilisierungsrelease** auf Basis von RC18. Er korrigiert irreführende Statusaussagen, stale abgeleitete Kapazitätswerte, fehlende Requested-vs-Applied-Diagnose in festen Modi und die unvollständige Darstellung des asynchronen Local-API-Workers.

## Intended Delta

- exakte Intent-/Pfadtoken statt unsicherer Teilstringprüfung;
- `DISCHARGE` wird nicht mehr als `CHARGE` klassifiziert;
- `STOP_HOLD` wird als manueller Neutralzustand dargestellt;
- Restkapazität bis Max-SOC wird in jedem Zykluspfad aktualisiert;
- feste Modi führen angefordertes und wirksames Ziel getrennt;
- Config-/Gerätecap wird mit eindeutigem Grund angezeigt;
- Fixed-Mode-Prognose verwendet die wirksame, gecappte Leistung;
- Local-API-Worker, Snapshot, Quelle und Timing werden in der modernen Statusseite sichtbar;
- Installer wartet auf JSON `ready=true`, nicht nur auf eine erreichbare `/ready`-Antwort.

## Zusätzliche Vorabprüfung

Die statische Pfadprüfung fand zwei weitere Fehler derselben Klasse:

1. `DISCHARGE_CONTROL` konnte wegen des Wortteils `CHARGE` fälschlich als exportbasierte Ladeentscheidung markiert werden.
2. Ein frischer Local-API-Snapshot konnte als technische Einschränkung erscheinen, weil die UI einen Textvergleich statt des Zustands-Tons verwendete.

Beide Punkte sind in RC19 korrigiert.

## Sicherheitsabgrenzung

RC19 verändert keine Harvest-, AUTO-, NIGHT-, Cross-Charge-, Command-, Resync-, Neutralisierungs-, Flash-Schutz- oder Offgrid-Regel. Read-only Zendure-Gerätecaps werden weiterhin nicht beschrieben. Die Änderungen an festen Modi erhalten lediglich die bereits angewandte Begrenzung als Diagnosepipeline; das publizierte Ziel bleibt identisch zum RC18-Verhalten.

## Measurement V4

Keine Schemaerweiterung und keine Headerrotation:

```text
Standard: 246 Felder · Hash 7842bfef39d47f93
Extended: 249 Felder · Hash 8f61d07e66428a6e
```

## Produktivstatus

Build- und Regressionstestvalidiert. Produktive UI-/Fixed-Mode-Endabnahme nach Installation ausstehend.
