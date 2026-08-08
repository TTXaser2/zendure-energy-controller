# Releasebericht – Zendure Energy Controller V12.11.7

## 1. Zweck

V12.11.7 schließt die nach V12.11.6 identifizierte Default- und First-Install-Vertragslücke. Ziel ist nicht, neue Betriebswerte festzulegen, sondern zu verhindern, dass historische, anlagenspezifische oder migrationsbedingte Werte als allgemeine Produktdefaults interpretiert werden.

## 2. Wichtigste Korrekturen

1. **Default-Provenienz für alle 212 Settings** – Produktdefault, Profilpreset, Sentinel, Installation, Auto/Unset und Legacy/Internal sind explizit klassifiziert.
2. **Serverseitige Reset-Sicherheit** – `reset_default` kann Installations-/Anlagenwerte nicht mehr auf historische Pseudodefaults setzen.
3. **Fail-closed First Install** – fehlende `config.json` startet in `FIRST_INSTALL_SETUP`; das Control-Gate bleibt geschlossen.
4. **Explizite Anlagen-/Safetywerte** – Device-ID, Broker, Netzquelle, Leistungs- und SOC-Grenzen müssen bewusst gesetzt werden.
5. **Kontextidentischer Commit** – First-Install-/Preflight-Kontext des Preview wird beim Commit wiederverwendet.
6. **Neutrale Beispielkonfiguration** – keine Haus-IP, keine allgemeingültig behaupteten Leistungs-/SOC-Werte.
7. **Bestandsinstallationen bleiben unverändert** – kein Umschreiben vorhandener Nutzerwerte aufgrund neuer Defaultmetadaten.

## 3. Defaultklassen

Die finale Registry-Klassifikation umfasst alle 212 Settings:

```text
PRODUCT_DEFAULT   91
PROFILE_PRESET    45
SAFE_SENTINEL     28
LEGACY_INTERNAL   24
INSTALLATION      13
AUTO_OR_UNSET     11
--------------------
Gesamt            212
```

Kein Setting bleibt ohne Default-Provenienz.

Der Vertrag unterscheidet zusätzlich die erlaubte Resetaktion:

```text
DEFAULT
CLEAR
AUTO
PROFILE
NONE
```

Damit beschreibt `Default` nicht länger zugleich Bootstrap, Migration, Benutzerempfehlung und Reset-Ziel.

## 4. First-Install-Verhalten

Bei fehlender `config.json`:

```text
Config Health     = missing
Startup Mode      = FIRST_INSTALL_SETUP
Control Allowed   = false
```

Die UI zeigt einen Setup-Hinweis. Anlagenabhängige Enumfelder besitzen bei fehlender Auswahl einen expliziten Platzhalter statt stiller Vorauswahl.

Ein erfolgreicher erster Commit erzeugt eine kanonische Konfiguration, die nach einem erneuten Load denselben NORMAL-Zustand und dieselben gesetzten Werte liefert.

## 5. Sicherheitsabgrenzung

V12.11.7 ändert keine Reglerformel und keine Geräteaktion. Alle Änderungen liegen in SettingsRegistry, SettingsRuntime/Service/Validation/Model, Setup-Template, UI-Darstellung, Installeridentität, Tests und Release-Dokumentation.

Die geschützte Regler-/Command-/Measurement-Schicht wird byteidentisch gegen V12.11.6 geprüft.

## 6. Measurement

Aktive Produktivgrundlage bleibt Measurement V4. Der separat geplante Legacy-V3-Cleanup ist ausdrücklich nicht Teil dieses Releases.

## 7. Restpunkte

Bewusst offen bleiben:

- V4-only/V3-Legacy-Cleanup als eigener Measurement-/Replay-Block;
- Measurement-Storage-Härtung;
- benannte Konfigurationsstände und Import/Export;
- Graph-/Experten-/Simulationsfolgeblöcke.

## 8. Datei-Scope

Fachlich geändert werden ausschließlich Settings-/Config-/UI-Vertragsdateien, Version/Installer, Tests und Release-Dokumentation. Die vollständige Liste steht in:

```text
V12_11_6_TO_V12_11_7_CHANGED_FILES.txt
```

Die geschützten Regler-/Command-/Measurementdateien sind nicht Bestandteil des Deltas.

## 9. Build- und ZIP-Abnahme

```text
Source-Manifest                 334/334 PASS
Python-Syntax                   148/148 PASS
JavaScript-Syntax                 2/2 PASS
Shell-Syntax                      9/9 PASS
JSON                              6/6 PASS
unittest                        682/682 PASS
ResourceWarning=error           682/682 PASS
pytest                          682/682 PASS
pytest Subtests                 677/677 PASS
Browser-Smokes                  PASS
Protected Byte Identity           7/7 PASS
Excel Byte Identity             PASS
```

Die Abnahme wurde direkt aus einer frischen Extraktion des finalen Release-ZIPs wiederholt.
