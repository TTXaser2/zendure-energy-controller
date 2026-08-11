# V13.0.0 – Implementierungsnotizen zur freigegebenen Spezifikation V1.1

Die freigegebene Spezifikation bleibt als unverändertes Artefakt im Release erhalten:

`SPEZIFIKATION_ZEC_V13_0_0_KONFIGURATIONSSTAENDE_IMPORT_EXPORT_UND_SOC_GRAPH_HISTORIE_V1_1.md`

SHA256 der freigegebenen Datei:

`188c972b044ab5ebb4520e596ddd46c19497ce333a1703a978867a3cfa3caa45`

## Bestandszählung

Bei der Umsetzung gegen die tatsächlich verifizierte V12.13.0-Codebasis wurde festgestellt, dass die Registry 191 statt der in der Spezifikation genannten 188 aktiven editierbaren LIVE/RESTART-Settings enthält. Die Differenz besteht ausschließlich aus drei bereits vorhandenen V4-Archivpflege-Settings. Daher klassifiziert die Implementierung 191/191 Settings explizit.

## Graph-Backfill

Der vereinbarte einmalige historische Import ist als idempotentes externes Maintenance-Tool umgesetzt. Es verarbeitet ausschließlich V4-Zeilen mit `measurement_epoch_ms` und `config_control_hash`, nutzt die vorhandenen Config-Snapshots, schreibt nur die separate Graph-Config-Timeline und verändert weder Measurement V4 noch Primärconfig, Last-Good oder Gerätekommandozustände.

Der Installer behandelt einen Backfill-Fehler als nichtfatal: Ein ansonsten gesunder V13-Controller wird deshalb nicht zurückgerollt. Fehlende historische Overlays bleiben transparent unbekannt und können durch erneuten idempotenten Backfill später ergänzt werden.

## Import-/Export-Kern

Named State, Voll-Export, teilbares Regelprofil und Import verwenden denselben Bundle-/Migration-/Preview-/Validation-/CAS-Kern. Ein Stand oder Import ist niemals Last-Good und wird niemals direkt aktiv geschaltet. Last-Good-Promotion bleibt vollständig dem bestehenden Stable-Ready-/Eligibility-Vertrag überlassen.
