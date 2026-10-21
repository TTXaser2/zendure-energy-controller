# ZEC S3 – Saison- und Tagesprofile: Produktionsvertrag

**Stand:** 19.10.2026 · **Basis:** verifiziertes ZEC V17.0.2, Build `v17.0.2-20260923` · **Ledger:** `ZEC-BL-CTRL-S3-001` · **Status:** `SPEC_FINAL / USER_MACRO_SCOPE_20261019` – fachlich geschlossener Implementierungsvertrag, nicht bereits implementiert oder feldfreigegeben.

## 1. Produktzweck und messbare Sinnhaftigkeit

S3 schließt die funktionale Lücke zwischen teilweise freigegebenen, aber tatsächlich wirkungslosen Settings und der heutigen hartcodierten Tages- und Saisonprofilebene. Der Nutzer kann eine **deterministische, bewusst gewählte** Prioritätspolitik konfigurieren; dies ist keine Wetterprognose, kein Adaptive-Modell, kein zweiter Regler oder eigenständiger Gerätebefehl. Der primäre direkt nachweisbare Nutzen ist **wirksame, reproduzierbare Konfigurierbarkeit und nachvollziehbare Diagnostik**, nicht eine unbewiesene Ertragssteigerung. Abnahme: unveränderte Bestandskonfiguration ist zu V17.0.2 differential verhaltensgleich; explizite, gültige Settingsänderung verändert in nachweisbar geeigneten Fällen allein die strategische Profilebene; Endkommando und tatsächlich physischer Effekt bleiben getrennt sichtbar.

## 2. Tagesprofile

`T0=09:30`, `T1=11:30`, `T2=14:30`, `T3=18:00` sind historische kompatible Defaults. Strict `T0<T1<T2<T3`. Alle Fenster links inklusive, rechts exklusiv. `T0≤t<T1`: Morgen (`share=0.60`, `confirm=60s`); `T1≤t<T2`: Mittag (`0.50`,`30s`); `T2≤t<T3`: Nachmittag (`0.35`,`15s`); sonst Default (bestehender Mittag-Share und generische Confirm-Zeit). Der bisher wirksame `HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED=false` liefert den unveränderten generischen Defaultzweig. Lokale Systemzeitzone wie bereits V17.0.2, DST-Wiederholung erzeugt kein künstliches physisches Handeln. Profile verwenden die zehn bestehenden S3-Settings als tatsächliche Runtimeinputs, in vorhandenen gültigen Konfigurationen exakt kompatibel zum Hardcode.

## 3. Saisonpolicy und sichere explizite Aktivierung

Drei vorhandene Policywerte: `parallel`: historisch bestehende strategische Share-Allokation in unverändertem High-SOC-Gate; `sma_priority`: im strategischen High-SOC-Share-Zweig keine zusätzliche Umlenkung zu Zendure, **aber bestehendes physisches Export Capture bleibt uneingeschränkt zugelassen**; `calendar`: `parallel` innerhalb des konfigurierten wiederkehrenden Intervalls, sonst `sma_priority`. Der Saisonmodus ändert nicht Fast Capture, SMA_NEAR_LIMIT, SMA_FULL_OR_IDLE, Export-Capture, MIN/MAX-SOC, Cross-Charge, Night, Safe State oder Device-/Commandgrenzen.

**Kritischer Migrationsschutz:** `HARVEST_SEASON_MODE` wurde in V17.0.2 bereits persistiert, aber ignoriert; sein `sma_priority`-Default darf nach Update nicht plötzlich wirksam werden. Deshalb ein **separater expliziter Saisonpolicy-Aktivierungsschalter** `HARVEST_SEASON_POLICY_ENABLED` (bool, default `false` für Bestands- und Neuinstallationen). Solange `false`, bleibt die Season-Auswahl lediglich diagnostisch, effektive Semantik `legacy_parallel`; die beobachtete saisonal effektive Strategie ist verhaltensgleich zur V17.0.2-Baseline. Nur nach bestätigtem Enable im Settings-Preview/Commit darf die validierte bestehende Modusauswahl ihre neue Wirkung entfalten. Kein impliziter Opt-in durch ehemals gespeicherte ignorierte Werte; ein explizites Enable muss auch bei importierten Konfigurationsständen angezeigt und validiert werden. Bei abgeschalteter S3-Saisonpolicy sind vorhandene `sma_priority`-Defaultwerte folgenlos.

## 4. Kalender, Zeit und Validierung

Grenzen `MM-DD` bezeichnen jährlich wiederkehrende Tage, jeweils einschließlich. Start < Ende normales Fenster; Start > Ende über Jahreswechsel mit OR-Semantik; Start = Ende ein Tag. `29.02.` ist als Grenze unzulässig, aber ein normaler Schalttag zwischen gültigen Grenzen bleibt enthalten. Bei `calendar` sind beide Grenzen und gültige Daten zwingend; `VAL-014` verweigert Commit bei fehlenden oder ungültigen Grenzen, `VAL-013` bei nicht streng geordneten Zeitgrenzen. Alte, ungenutzte Settings dürfen ohne expliziten Saison-Enable nicht nachträglich durch neue Calendar-Validation eine bestehende gültige Runtime zerstören; beim Enable beziehungsweise Änderung von `calendar` muss sie strikt gelten. Runtimeinvalid verhindert aktive Änderung, letzter gültiger Effective-Snapshot bleibt maßgeblich.

## 5. Zustands-/Timer- und Schutzvertrag

Nur existierende monotone Zeit-/distinct-observation-Mechanismen fortführen. Reine Tagesprofilgrenze ändert den `entry_confirm_s`-Zielwert, setzt einen bereits gültigen Confirm-/Hold-State nicht zyklusweise zurück und autorisiert weder allein einen neuen Modus noch einen Publish. Nach tatsächlicher Zeit-/Policyänderung gilt neue Grenz-/Bestätigungssemantik frühestens auf einer neuen frischen Beobachtung. Bei aktiver Hold-Phase bleiben alte No-Regression-/Recoveryguards maßgeblich. Szenarien mit Source-Stale, invaliden Daten oder explizitem Saison-/Configwechsel erhalten neutralen/sauberen Fallback; kein rückwirkendes künstliches Anrechnen der Uhrzeit. Strategy-Share nur im bisher erlaubten High-SOC-Zweig; aktuell vermeidbarer Export hat Vorrang.

## 6. Einstellungen, UI, Diagnose

Alle zehn vorhandenen S3-`TARGET_ONLY`-Keys dürfen erst zusammen mit funktionierendem Runtime-Consumer, Validation und Tests zu `operational` wechseln. Der neue Saison-Enable ist klar als sicherheits-/wirksamkeitsrelevanter opt-in Standard-Schalter zu kennzeichnen; Season-Mode-/Window-Felder müssen semantisch und abhängig vom ausgewählten Modus im Draft sichtbar bleiben. Hilfen nennen ausdrücklich den bisherigen kompatiblen Legacybetrieb, effektiven Modus, Zeitfenster, Confirm, tatsächliche Branch-Anwendbarkeit und nachrangige Rolle gegenüber Export Capture. Additive Diagnostics: angefordertes/effective Saisonprofil, Tagesprofil, gewählter Share, Confirm, Applicability `NOT_APPLICABLE|APPLIED|OVERRIDDEN`, Overridegrund und finaler Sollwert. Keine Behauptung von produktivem Share-Effekt, wenn Export Capture dominiert; bei nicht verfügbaren Quellen ehrlich stale/unbekannt.

## 7. Technische Abnahmematrix

1. V17.0.2-Baseline differential an allen vier Grenzzeiten (jeweils -1/0/+1 min), in deaktiviertem Zeitprofil sowie Legacy + persistiertem `sma_priority` bei Saison-Enable=false.
2. `parallel`, `sma_priority`, `calendar` bei High-SOC mit und ohne wirksamen Share, bei Netzausfuhr, Fast Capture, full/idle/near-limit, ungenügendem Headroom und nicht verfügbaren physischen Referenzen.
3. Jahreswechsel/gleiches Datum/Schalttag/fehlende Grenzen/ungültige Values/Import-Preview/Commit/Restart; kein Scheinsetting oder unerwarteter Defaultshift.
4. Monotone Confirm/Hold-Transition bei Tagesprofilgrenzen, Zeitrückstellung und Quelle-Stale. Kein zusätzliche Publish-/Mode-/AC-Richtungswechsel; Device-Limits und Hardware-/Cross-Charge-Guards unverändert.
5. Status/Expert-Diagnose, Settings-Help, additive Messschemas, Simulations-/Differential-/Feldevidenz getrennt; aktuelle Daten nicht aus falschen historischen Annahmen ableiten.

## 8. Gemeinsamer nächster Release (separat freigegebene Subscopes, nicht S3 selbst)

Zusätzliche ausdrückliche Nutzeranforderung 19.10.2026: Die Statusseite aktualisiert wichtige Netz-, Primärspeicher- und Zendure-Istgrößen **fest jede Sekunde**, unabhängig von Controllerzustand und Control-Zyklus. Der 1-Hz-Refresh liefert Quelle, Zeitpunkt, Alter, Freshness/Validity; abgelaufene Daten bleiben als stale und werden nicht als frischer neuer Messwert ausgegeben. SMA-UDP-Receiver/MQTT-/Modbus-Collector bleiben read-only Datenautorität; keine neue Hardwarepollrate über den bloßen UI-Wunsch; schlankes eigenes Monitoring ohne erhöhte Reglertaktung. Ein sichtbarer Browser-Poll allein ist kein Beweis einer neuen Sensorprobe. Betriebsereignis `GRID_STALE`/`GRID_PROCESSING_STALE` bei abnormal alter Telemetrie mit Quellen-Differential, Hysterese, open/resolve, kein 3-s-Flutmechanismus. Die bestehenden `NIGHT-MINSOC-GRID`- und `GRID-SMA-OBIS`-Fixes sind unabdingbarer Next-Release-Scope, ebenso vereinbarte UI-Restpunkte und releaseintegriertes `docs/`-Gate. Resource budgets Pi 3B+ und vollständige Regression/Checkpoint/Fresh Extract gelten ohne Ausnahme.

**Freigabegrenze:** Dies ist ein kompletter Sollvertrag zur Umsetzung auf V17.0.2, kein Beleg, dass alle Funktionstests, Paket- oder Feldevidenzen bereits PASS sind. Für finalen Produktrelease sind sämtliche separaten Block- und Release-Gates abzuarbeiten.
