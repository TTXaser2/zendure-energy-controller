# V13.0.2 – Audit benutzerseitiger Release-/RC-Bezüge

Stand: 12.08.2026

## Ziel

Benutzertexte beschreiben den aktuellen Funktions-, Bedien- und Diagnosevertrag. Historische Release-/RC-Erzählungen werden aus der normalen UI, Settings-Hilfe und dem aktuellen Benutzerhandbuch entfernt, sofern sie für die aktuelle Nutzung keinen konkreten Kompatibilitäts- oder Diagnosewert besitzen.

## Geprüfter Scope

Vollständig geprüft wurden die benutzerseitigen Texte aus:

- SettingsRegistry und projizierten Settings-/Hilfemetadaten,
- `config_manager.py`-Legacy-/Kompatibilitätsbeschreibungen, soweit sie noch in UI-Verträge einfließen,
- `settings_help.py`,
- `web_ui.py` und aktuelle Status-/Graphhilfen,
- `static/settings_v2.js` und `static/status_v2.js`,
- aktuellem Benutzerhandbuch `docs/Zendure_Energy_Controller_Handbuch.docx` / `.pdf`.

Zusätzlich wurden typische Muster `RC<n>` und `V12.x/V13.x` in den Produktionsquellen inventarisiert. Kommentare, Docstrings, interne Migrationskennungen und historische Metadaten wurden getrennt von tatsächlich gerenderten Benutzertexten bewertet.

## Umgeschriebene Benutzertexte

| Fundstelle | Vorher | V13.0.2 | Entscheidung |
|---|---|---|---|
| Command-Resync-Hilfe | `Standard in V12.11.2-RC1 ist aus ...` | `Standardmäßig ist die Option deaktiviert ...` | Entwicklungshistorie entfernt; aktuelles Verhalten erklärt. |
| Lokale Zendure-API | `Seit RC18 blockiert die lokale API den Regelzyklus nicht mehr.` | `Die lokale API arbeitet asynchron und blockiert den Regelzyklus nicht.` | Aktueller Laufzeitvertrag statt Einführungsversion. |
| Laufzeitdiagnose | `Dient der RC3-Timingdiagnose.` | `Dient der Laufzeit- und Timingdiagnose.` | Historischer RC-Bezug ohne Bedienwert entfernt. |
| SMA Socket-Modus | `Diagnose: RC3-kompatibel / SO_REUSEPORT best-effort` | `Diagnose: Wildcard-Bind + SO_REUSEPORT best-effort` | Technische Wirkung direkt benannt; interner Enum `rc3_compatible` bleibt stabil. |
| Measurement-Schema | `In V12.13.0 ein fester ... Kompatibilitätsmarker.` | `Fester ... Kompatibilitätsmarker.` | Aktueller V4-only-Vertrag beschrieben. |
| Primärspeicher-Integration Apply-Text | `RC19-Subscription-Kopplung ...` | `bei Änderung der Subscription-Konfiguration ...` | Fachliche Apply-Semantik statt Quellrelease. |
| Migration-only Apply-Text | `Aktiv in RC19 ...` | `Aktiver Kompatibilitätsparameter ...` | Aktueller Status statt historische Herkunft. |
| Statushilfe Local API | `Die HTTP-Abfrage läuft ab RC18 asynchron.` | `Die HTTP-Abfrage läuft asynchron.` | Aktueller Diagnosevertrag. |
| Benutzerhandbuch | versionspezifische Einführungs-/Upgradeformulierungen zu V13.0.0/V12.6 | zeitlose Beschreibung des aktuellen Funktionsstands bzw. `Upgrade mit vorhandener Measurement-V4-Historie` | Historische Releaseerzählung entfernt. |
| Benutzerhandbuch / UI | `teilbares Regelprofil` | `verteilbares Regelprofil` | Vereinbarte Benutzerterminologie. |

## Automatisierte Abschlussprüfung

Die Registry wird nicht als Quelltext-Stringscan bewertet, sondern über die tatsächlich benutzerseitig projizierbaren Felder (`label`, Apply-/Validierungs-/Default-/Dependency-Texte, Optionen sowie Rich-Help-Felder). Für diese Felder ergibt die V13.0.2-Regression **keinen unbegründeten `RC<n>`- oder historischen V12/V13-Versionsbezug**.

Das aktuelle 20-seitige Benutzerhandbuch enthält:

- `Benutzerhandbuch V13.0.2` als zulässige aktuelle Versionsidentität,
- keine RC-Bezüge,
- keine historische V13.0.0-/V12.6-Erzählung,
- die Benutzerbezeichnung `verteilbares Regelprofil`.

## Bewusst erhaltene, begründete Versions-/RC-Informationen

Folgende Klassen bleiben erhalten und sind **keine Benutzertext-Verstöße**:

1. **Aktuelle Releaseidentität** – `13.0.2`, `V13.0.2`, `v13.0.2-20260812` in Header, Status und Releasebelegen.
2. **Import-/Export-Kompatibilität** – Quellversion, Build-ID, Registry-/Schema-Version und Registry-Hash eines Config-Bundles.
3. **Installer-/Rollbackvertrag** – V13.0.1 als einzig zugelassene Upgradequelle für V13.0.2 sowie Zielversion/-Build.
4. **Interne stabile technische Kennungen** – z. B. Enum `rc3_compatible`, `origin='RC19'`, Migration-IDs und Migrationsmetadaten. Sie werden nicht als historische Benutzererklärung gerendert und bleiben zur Kompatibilität/Provenienz des internen Vertrags erhalten.
5. **Codekommentare/Docstrings und archivierte Release-/Technical-Notes** – nicht Teil der aktuellen Benutzeroberfläche; sie bleiben Entwicklungs-/Archivquellen.
6. **Aktuelle Registry-Schemaidentität `1.25-v13.0`** – technische Kompatibilitätsmetadaten, nicht Entwicklungserzählung.

## Ergebnis

**PASS.** Die bekannten Feldbeispiele wurden zeitlos umgeschrieben. Der Audit entfernt keine technisch notwendigen Versions-/Kompatibilitätsinformationen und benennt interne stabile Kennungen nicht unnötig um.
