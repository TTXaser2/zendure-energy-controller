# Technical Notes – Zendure Energy Controller V12.12.1

## 1. RICH-Help-Qualitätsvertrag

`SettingHelpSpec` enthält nun ein explizites `when_help`. Für alle 62 RICH-Settings werden konkrete Wirksamkeitsbedingungen und Risiko-/Sicherheitsinformationen erzwungen. Generische Fallbacktexte sind in diesen Kernfeldern nicht mehr zulässig.

## 2. Terminologie

Normale Benutzertexte verwenden verständliche deutsche Begriffe. Technische Begriffe bleiben dort erhalten, wo sie als Config-Key oder Expertenvertrag notwendig sind. Das Handbuch enthält ein Glossar und erklärt unter anderem SettingsRegistry ausdrücklich als internen ZEC-Einstellungskatalog und nicht als Windows-Registry.

## 3. Help-Modal

Der interne Scrollcontainer `#helpBody` wird bei jedem neuen Help-Ziel auf `scrollTop=0` gesetzt. Das gilt für Setting-, Kategorie-/Abschnittshilfe, Expert-Gate und `Warum?`-Navigation.

Default-/Profil-Semantik wird als strukturierte Key/Value-Darstellung gerendert; Einordnung und verfügbare Aktion sind getrennte Zeilen.

## 4. Search Ranking

Treffer werden nach Treffergüte gewichtet: sichtbarer Titel, exaktes Synonym, Config-Key, strukturierte Metadaten und erst danach allgemeiner Hilfetext/Formel. Dadurch rangiert `Netz-Totzone um 0 W` für `Totzone` und `Deadband` vor lediglich verwandten Einstellungen.

## 5. Compound-Validation

Hour-/Minute-Keys des Nachtfensters werden für Preview-Issues auf das logische HH:MM-Compoundfeld abgebildet. Benutzeraktionen zeigen keine technischen Komponenten wie `Start Minute`; `Warum?` öffnet die logische Hilfe `Startzeit des Nachtmodus` bzw. `Endzeit des Nachtmodus`.

## 6. Status-Info-Popover

`Controller & Schnittstellen` besitzt einen separaten scrollbaren Body und einen expliziten Close-Button. Scrollereignisse innerhalb des Popovers werden nicht mehr als externer Seitenscroll interpretiert. Desktop-Seitenscroll kann das Popover weiterhin schließen. Mobil wird ein viewportnahes Panel mit eigenem Scrollkontext verwendet.

## 7. Mobile Settings Scroll Owner

Bei Viewports bis 820 px besitzt `.settings-main` den vertikalen Scrollkontext. Die globale Topbar und Settings-Contextbar liegen außerhalb dieses Scrollowners; die Change-Bar bleibt fixed. Der Kategorien-Drawer sperrt den Content-Scroll und stellt dessen Position wieder her, statt den gesamten Body per `position:fixed` zu verschieben.

## 8. Handbuch

Das V12.12.1-Handbuch umfasst 17 verifizierte Seiten. Seiten 1–14 behalten die V12.12.0-Struktur; Seiten 15–17 enthalten `Begriffe und Abkürzungen` mit 44 Fachbegriffen/Abkürzungen.

## 9. Browserabnahme

Chromium prüft Desktop und mobile Viewports interaktiv. Ein automatisierter WebKit-Lauf war nicht verfügbar: in der Buildumgebung ist keine WebKit-Engine installiert; der Nachinstallationsversuch scheiterte an der Netzwerk-/DNS-Erreichbarkeit. Diese Limitierung wird nicht als WebKit-PASS dargestellt.

## 10. Version / Installer

```text
APP_VERSION       = 12.12.1
APP_VERSION_LABEL = V12.12.1
APP_BUILD_ID      = v12.12.1-20260810
```

Regulärer Installer-Ausgangsstand ist V12.12.0 / `v12.12.0-20260809`. Ältere ausdrücklich unterstützte Recovery-Ausgangsstände bleiben erhalten.
