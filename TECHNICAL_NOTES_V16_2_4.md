# Technical Notes V16.2.4

## Settings Surface

`SettingsRegistry` führt `SurfaceState` (`operational`, `target_only`) und `Applicability`. Produktfreigabe, Hardware-/Config-Anwendbarkeit und Provenienz (`release_stage`, `origin`) sind getrennte Achsen. Nichtlegacy-Settings ohne explizite Surface-Klassifikation schlagen fail-closed fehl.

Primärspeicher-Unterfelder sind bei deaktivierter Integration im Weblayout nicht anwendbar, bleiben aber Teil des operativen Modells. Der Aktivierungsschalter bleibt erreichbar. Topologieinformation für ein oder zwei Zendure-Entities erzeugt keine zweite Commandkonfiguration.

## Status Expert Slice

Im Expertenmodus rendert die Primärspeicherkarte kompakt Harmonisierung, Harvest/Strategie, diagnostischen usable SOC und Quellenstatus. Standard bleibt unverändert. Der vollständige kartenübergreifende Expertenmodus bleibt offen.

## Deployment Evidence

Der Installer schreibt den Installationsreport atomar und timestamped persistent unter `/home/pi/Downloads`. `/tmp` ist Kompatibilitätskopie. Das Feldtool bevorzugt persistente Evidenz und prüft beim Update die reale Backup-Datei über Pfad, Größe und SHA256.

## Field Acceptance

Die V16.2.4-Abnahme prüft zusätzlich live `/settings/model`: erwartete Primärspeicher-Controls, Surface-/Applicability-Semantik und Negativproben für target-only Settings.


## Technical Build Evidence

V16.2.4 besteht 150 Testdateien mit `1123 Tests + 698 Subtests` sowohl normal als auch mit `-W error::ResourceWarning`. Bash-Syntax `13/13`, Browser-JavaScript `3/3`, Compileall, Deployment-Harness `11/11`, Root-Artefakt-Transaktion, Datenblatt-, Build-Evidence-, Manifest-/Hygiene- und Fresh-extract-Gates sind PASS. Der Reglerkern bleibt byteidentisch. Die reale V16.2.3 → V16.2.4-Feldabnahme steht weiterhin aus.
