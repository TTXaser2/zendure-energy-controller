# ZEC – S3 Saison- und Tagesprofile: fachliche Produktionsspezifikation, Entwurf 1

**Stand:** 18.10.2026  
**Backlog:** `ZEC-BL-CTRL-S3-001`, eigenständig, ohne Adaptive-Abhängigkeit.  
**Quelle:** reale V17.0.2 `controller_logic.py`, `settings_registry.py`, `settings_validation.py`, `config.example.json`; kanonische Regeln 00–07; Strategieentscheidung 18.10.2026.  
**Status:** **SPEC_DRAFT / NICHT FREIGEGEBEN**; keine produktive Sourceänderung. Offene Policyfragen sind explizit markiert.

## A. Produktzweck / Problem / Nichtzweck

**Ist-Problem:** Runtime `_harvest_time_profile(cfg)` (V17.0.2, Zeilen 2977–2992) nutzt fixe lokale Uhrzeitfenster 09:30–11:30, 11:30–14:30, 14:30–18:00 und Confirm-Zeiten 60/30/15 s. Ein Defaultfenster außerhalb nutzt den Midday-Share und generischen Confirmwert. Die Legacy-Shares sind runtimewirksam, aber zehn angelegte S3-Settings sind `TARGET_ONLY`. `HARVEST_SEASON_MODE` hat drei Werte, jedoch noch keine geregelte Produktivwirkung. Die Settings können einen Scheinvertrag erzeugen, die Saison-/Zeitanpassung erfordert heute Sourceeingriffe.

**S3-Zweck:** Nutzerdefinierte, deterministische zeit- und kalenderabhängige Steuerung der bereits vorhandenen **strategischen** Harvest-Zulässigkeit und -Profilparameter; klare, sichtbare Erklärung warum ein Profil gewählt wurde und ob es den Endzielwert beeinflusste. Keine Ertragsvorhersage, kein Adaptive-Lernen, keine neue Zendure-Commandautorität und **kein** stillschweigendes Absenken von High-SOC-/SOC-/Export-Capture-/Cross-Charge- oder Hardwaregrenzen.

**Sinnhaftigkeitsprüfung:** Ein Profil ist nur wertvoll, wenn es eine nachvollziehbare Prioritätspolitik abbildet (z. B. vormittags primäre Reserve sichern, nachmittags zusätzliche Parallel-Ladechancen zulassen), nicht weil einzelne Stunden heute zufällig hartcodiert sind. Statische Zeitregeln sind eine *Nutzerpolicy*, kein behauptetes Solarertragsmodell. Unterschiede an nicht zulässigen oder von physikalischen Export-Capture-Grenzen dominierten Punkten sind ehrlich als nichtwirksam auszuweisen.

## B. Source-Mapping / 14 relevante Einstellungen

| Setting | V17.0.2-Ist | Ziel-/Produktvertrag |
|---|---|---|
| `HARVEST_SEASON_MODE` | `TARGET_ONLY`; Werte `sma_priority`, `parallel`, `calendar`; Registry `default_new_install=sma_priority`, RC19-Migrationstext `parallel` | reale **Saisonpolicy**, keine implizite Runtime-Umschaltung bei Altbestand |
| `HARVEST_SEASON_PARALLEL_START_MM_DD` | `TARGET_ONLY` / optional | Beginn des wiederkehrenden Kalenderfensters, inklusive |
| `HARVEST_SEASON_PARALLEL_END_MM_DD` | `TARGET_ONLY` / optional | Ende des wiederkehrenden Kalenderfensters, inklusive |
| `HARVEST_HIGH_SMA_SOC_PROFILE_START_TIME` | `TARGET_ONLY`, 09:30 | Tagesprofil Start |
| `HARVEST_HIGH_SMA_SOC_PROFILE_MIDDAY_START_TIME` | `TARGET_ONLY`, 11:30 | Morgen-/Mittaggrenze |
| `HARVEST_HIGH_SMA_SOC_PROFILE_AFTERNOON_START_TIME` | `TARGET_ONLY`, 14:30 | Mittag-/Nachmittaggrenze |
| `HARVEST_HIGH_SMA_SOC_PROFILE_END_TIME` | `TARGET_ONLY`, 18:00 | Tagesprofil Ende |
| `HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_MORNING_SECONDS` | `TARGET_ONLY`, 60 | morgens verwendete Eintrittsbestätigung |
| `HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_MIDDAY_SECONDS` | `TARGET_ONLY`, 30 | mittags verwendete Eintrittsbestätigung |
| `HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_AFTERNOON_SECONDS` | `TARGET_ONLY`, 15 | nachmittags verwendete Eintrittsbestätigung |
| `HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED` | Legacy hidden / runtimewirksam, true | nur explizit migrieren, keine unbeabsichtigte Änderung des deaktivierten Altbestands |
| `HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MORNING` | runtimewirksam, 0.60 | bestehender Share erhalten |
| `HARVEST_PRIMARY_CHARGE_TARGET_SHARE_MIDDAY` | runtimewirksam, 0.50 | bestehender Share / Defaultfenster erhalten |
| `HARVEST_PRIMARY_CHARGE_TARGET_SHARE_AFTERNOON` | runtimewirksam, 0.35 | bestehender Share erhalten |

Zusätzlich bleibt `HARVEST_HIGH_SMA_SOC_ENTRY_CONFIRM_SECONDS` als bestehender generischer Default außerhalb der Profilfenster wirksam, soweit die freigegebene Migration nichts anderes festlegt. Bestehende Entry-/Exit-SOC-, Hold- und Leistungsbedingungen bleiben unverändert. `HARVEST_CAPACITY_WEIGHTING_MODE` ist **nicht S3**; C1 ist ein eigenständiger Scope.

## C. Deterministische Profilzeit-Semantik (Entwurf)

- `T0 <= t < T1` -> morning / morning-share / morning-confirm; `T1 <= t < T2` -> midday; `T2 <= t < T3` -> afternoon; sonst `default` / legacy midday-share / generischer Confirmwert. `T0<T1<T2<T3` ist verpflichtend (VAL-013). Uhrzeitgrenzen lokal nach eindeutig dokumentierter Controller-Zeitzone; keine UTC/Local-Mischung.
- `t == T3` ist Default; Neustart an beliebiger Grenze darf keinen künstlichen Wechsel der physischen Kommandoautorität verursachen. Intervallverschiebung oder Uhrzeit-/DST-Sprung müssen deterministisch und ohne Endlosschleife sein; lokal doppelt auftretende Uhrzeiten wiederholen nur den Profilnamen, nicht künstlich bereits abgeschlossene Geräteaktionen.
- Legacy `HARVEST_HIGH_SMA_SOC_TIME_PROFILE_ENABLED=false`: vorhandenen Defaultpfad erhalten; dessen explizite Migration auf eine neue Produktoberfläche ist vor Freigabe zu definieren. Kein Ignorieren eines bisher wirksamen deaktivierten Legacy-Schalters.
- Profilzeit und eine bereits laufende High-SOC-Eintritts-/Hold-Bestätigung müssen wohldefiniert zusammenwirken. Kein künstliches Timer-Reset in jedem Regelzyklus bei Grenzwechsel; Wechselprofil nur nach explizit spezifizierter Transition-Policy.

## D. Saisonpolicy – beabsichtigter Vertrag; vor Sourceänderung zu schließen

V17.0.2-Registry nennt `sma_priority`, `parallel`, `calendar` und beschreibt deren Wirkung als **strategische High-SOC-Allokation**, nicht als Sperre von realem Restexport, Near-Limit oder Full/Overflow.

**Konzeptionelle Zuordnung zur Prüfung:**
- `parallel`: bestehende strategische Share-Verteilung ist innerhalb unverändert zulässiger High-SOC-Bedingungen erlaubt.
- `sma_priority`: strategische Parallel-Share-Verteilung wird zugunsten der Primärspeicherpriorität zurückgehalten; **physikalisch notwendiges Zendure-Export-Capture und Schutzpfade bleiben unverändert**.
- `calendar`: innerhalb zyklischer Inclusive-Saison gilt `parallel`, außerhalb `sma_priority`.

**OFFEN / FREIGABERELEVANT:** Die heutige produktive V17.0.2-Runtime **ignoriert** das neue Season-Setting; ihr bestehender High-SOC-Share-Pfad läuft mit historischer Priorisierung. `default_new_install=sma_priority` würde bei unmittelbarer Runtime-Aktivierung möglicherweise **das Produktdefaultverhalten ändern**. Der Migrations- und Defaultvertrag muss deshalb unterscheiden zwischen (1) bestehenden realen Installationen, (2) neuen Installationen und (3) bereits gespeicherten, bisher wirkungslosen `HARVEST_SEASON_MODE`-Werten. Der Nutzer muss eine beabsichtigte neue Betriebssemantik ausdrücklich erkennen/aktivieren können; **kein stiller Defaultshift**. Empfehlung als vorläufiger Entwurfsansatz: verhaltenskompatible Migration/opt-in zu neuer Saisonpolicy; produktiven New-Install-Default vor Codefreigabe fachlich festlegen.

**Kalendervertrag:** MM-DD wiederkehrend, Start und Enddatum **inklusive**, Start=Ende genau ein Tag. `start < end`: innerhalb bei `start<=heute<=end`. `start > end`: Jahreswechsel, innerhalb bei `heute>=start OR heute<=end`. 29.02. als Fenstergrenze aus Gründen konsistenter Wiederkehr über Nichtschaltjahre nicht zulässig (wie bisheriger Registry-Zieltext); fehlende/nichtparsebare Grenzen bei `calendar` sind blockierende Validierung, nicht stille Policy-Umschaltung. VAL-014 derzeit noch nur `start<=end`, muss zyklisch korrigiert werden. Die Bedeutung von 29.02. als tatsächlichem *Kalendertag innerhalb eines Intervalls* ist bei `calendar` mit nicht-29.02.-Grenzen normal; keine künstliche Unterbrechung der Saison an Schalttagen.

## E. Eingriffs- und Konfliktvertrag

S3 liefert ausschließlich die zulässige **Profil-/Policy-Wahl** für existierende strategische Harvest-Rechnung. Es erzeugt keinen eigenen AC-Befehl, keine externen Wetter-/Ertragsdaten und kein neues Laden aus dem Netz. Endzielwerte laufen durch vorhandene Export-Capture-Untergrenze, Fast Capture (separat), Cross-Charge- und Command-/Recovery-Guards sowie physische SOC-/Leistungsgrenzen. Bei nicht anwendbaren Hardware-/Betriebsbedingungen neutraler Fallback mit nachvollziehbarem Grund. Spätere B2-/C1-Module dürfen S3 nicht unkoordiniert überstimmen; gemeinsame Arbitration ist separate spätere Freigabe.

## F. Messbarkeit, Nutzen und Nichtbaukriterien

**Erforderliche Evidenz:** `effective_profile`, `season_requested`, `season_effective`, Gültigkeit/Saisonfenster, `share_before`, `share_after`, Profilconfirm, `branch_applicable`, `override_reason`, `final_zendure_target_w`, Outcome/Readback – Namen sind **Spezifikationsvorschläge**, keine aktuellen V4-Feldnamen. Wo S3 irrelevant ist (außerhalb High-SOC, Export-Capture dominiert, Primärspeicher nicht geladen), muss die Diagnose `NOT_APPLICABLE` oder klar begründete `OVERRIDDEN`-Semantik nutzen. Keine fiktive Produktivwirkung behaupten.

**Differentialtests:**
1. Baseline V17.0.2 an 09:29/09:30, 11:29/11:30, 14:29/14:30, 17:59/18:00 – identischer Share/Confirm bei unveränderter Konfiguration.
2. Änderung nur einer Tagesgrenze – nachvollziehbare Änderung nur in anwendbaren Fenstern; keine externe Safety-Regel betroffen.
3. Zeitprofil deaktiviert (Legacy-Schalter) und Restart einer aktiven Hold-/Confirm-Episode – verhaltensgleiche Baseline beziehungsweise explizit dokumentierte Transition.
4. `parallel`, `sma_priority`, `calendar` einzeln; kalendarisches Normal-/Jahreswechsel-Intervall, Start=Ende, Leap Day, fehlender Grenzwert, ungültige Werte – klare Validierung und fachliche Wirkung.
5. Gegenfälle mit Export trotz Lade-Headroom, MAX/MIN, Cross-Charge, Data-Stale, NIGHT, HOLD, FAST-CAPTURE, Command-Recovery – S3 darf bestehende Prioritäten nicht aushebeln.
6. Settings-/UI: TARGET_ONLY bis mit Runtime und Tests operativ freigegeben, Draft-/Preview-Validation, Import/Export, Migration, Test für neue und bestehende Installation, echte verständliche Hilfe-/Warnings.
7. Hardware-Konvergenz, Kommandovolumen, Zielwertrampen, Schalt-/Richtungswechsel und SOC-Folgeepisode im Offline-/Replay-/Feldtest nicht verschlechtert.

**No-Go:** Wenn eine Saison-/Zeit-Policy nur Scheinwirkung hat oder Default-/Bestandsmigration eine unerklärte/ungewollte Regleränderung verursacht, keine produktive Exposition und kein S3-Release-PASS. Keine Behauptung eines wetteradaptiven Optimierungseffekts ohne separate Evidenz.

## G. Offene fachliche Entscheidungen für finalen Scope

1. Exakte Semantik und UX für `sma_priority`/`parallel`/`calendar` unter Priorität „aktuell vermeidbare Einspeisung zuerst“, einschließlich Gating von strategischem Share gegenüber bereits normalem Primär-/Zendure-Laden.
2. Sichere Bestandsmigration **und** New-Install-Default bei bislang nicht wirksamem `sma_priority`, inklusive bereits persistierter aber ignorierter Season-Settings.
3. Timerverhalten bei live geänderten Profilgrenzen / laufender High-SOC-Confirm- oder Hold-Episode.
4. Finale Diagnosefelder und Sichtbarkeit (Status-/Expertenmodus, Settings Help/Warning, Messschemaadditivität).

**Nächster Schritt:** Die vier Entscheidungen anhand einer kleinen reproduzierbaren Zustandsmatrix schließen, daraus den finalen Implementierungs- und Testvertrag erstellen, danach explizite Sourcefreigabe. **Keine Implementierungsfreigabe aus diesem Entwurf ableiten.**
