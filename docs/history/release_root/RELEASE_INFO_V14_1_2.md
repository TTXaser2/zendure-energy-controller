# ZEC V14.1.2

## Zweck

Patchrelease zur Vervollständigung der Greenfield-Graph-Interaktion auf Basis der produktiven V14.1.1. Der Graph-Core-V3-Unterbau bleibt unverändert; die Änderungen liegen in der Präsentations- und Interaktionsschicht sowie in deren Installer-/Feldabnahmeverträgen.

## Nutzerbefunde und Korrekturen

- Der bisherige Analyse-Header war zu hoch und belegte unnötig Graphfläche. V14.1.2 verwendet eine kompakte Analyse-Toolbar; benutzerdefinierte Datumsfelder werden nur bei Bedarf eingeblendet.
- Der Episodenvergleich war räumlich zwischen rechter Kontextspalte und unterer Ausgabe getrennt. Vergleichsauswahl und Ausgabe bilden nun eine gemeinsame untere Analyse-Lane.
- Zusätzlich zum fachlichen t=0-Episodenvergleich gibt es einen echten Zeitraum-/Tagesvergleich für zwei frei wählbare Zeitfenster, nebeneinander oder überlagert.
- Zeitbereiche können explizit per Drag markiert werden. Die Markierung bleibt vom Zoom getrennt und kann zum Zoomen, Vergleichen oder Löschen verwendet werden.
- Leistung, SOC und Zustandslanes besitzen einen synchronen Zeitcursor. Native Chart.js-Hoverboxen sind deaktiviert; stattdessen zeigen ZEC-Cursorkarten die zeitgleich zugehörigen Werte und Zustände.
- `ⓘ`-Hilfen erklären nicht selbsterklärende Analysebegriffe und Interaktionen.
- Der WP9-Episodenvergleich liest den tatsächlichen API-Vertrag `episode.overview.relative_timestamps_ms` / `episode.overview.series`.
- Evidence wird als Segmentliste ausgewertet; `AVAILABLE`, echte `GAP`s, `NOT_INSTRUMENTED` und `PURGED_BY_RETENTION` werden fachlich unterschieden statt pauschal `—` zu zeigen.
- Die rechte Kontextspalte enthält nur noch `Inspector | Command | Daten`; Vergleich ist kein Kontext-Tab mehr.

## Upgradebasis

Unterstützte produktive Quelle: V14.1.1 / `v14.1.1-20260905`. Graph Core V3 wird erhalten und vor/nach der Installation read-only verifiziert. Kein Rebuild.

## Sicherheitsgrenze

Keine Änderung an Controller-, Command-, Safety- oder Hardwaresemantik. `controller_logic.py` bleibt geschützt und muss byteidentisch zur V14-Basis bleiben.

## Releaseidentität

- Version: `14.1.2`
- Label: `V14.1.2`
- Build-ID: `v14.1.2-20260905`
- Paketname: `zendure_controller_v14_1_2.zip`

Jede nachträgliche Sourceänderung nach Auslieferung dieses Pakets erfordert gemäß Releasevertrag mindestens V14.1.3.
