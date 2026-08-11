# ZEC V13.0.0 – Konfigurationsstände / Import / Export und historisch korrekte SOC-Graph-Overlays

**Dokument:** umsetzungsreife Spezifikation zur Freigabe  
**Version der Spezifikation:** 1.1  
**Stand:** 11.08.2026  
**Zielrelease:** **V13.0.0**  
**Status:** **ZUR FREIGABE – NOCH KEINE CODEÄNDERUNG**

**Revision 1.1 gegenüber 1.0:** historische, zeitbezogene Graph-Overlays statt rückwirkender Current-Config-Overlays; einmaliger idempotenter V4→Graph-Timeline-Backfill; danach inkrementelle Timelinepflege; explizit transportables „Teilbares Regelprofil“ für systemübergreifenden Austausch.

---

## 1. Verbindliche Ausgangsbasis und verifizierte Identität

Diese Spezifikation basiert ausschließlich auf der tatsächlich geprüften Übergabe und der darin enthaltenen V12.13.0-Quellbasis.

### 1.1 Übergabepaket

Geprüftes Paket:

```text
ZEC_UEBERGABE_NAECHSTER_ENTWICKLUNGSCHAT_20260811(1).zip
SHA256 = fe95882df7755f7400d8ae71ebad36513d65a0c0b5af100247478a8a34d42b57
Größe  = 12.985.351 Bytes
ZIP-Test = PASS
PACKAGE_MANIFEST.sha256 = vollständig PASS
```

### 1.2 Verbindliche V12.13.0-Quellbasis

```text
QUELLBASIS/zendure_controller_v12_13_0.zip
SHA256 = e204aa270c517d2e9b1abfc8816075ca75c3194c7b0cf39f1b5b186f7c07213f
Größe  = 12.467.610 Bytes
Root   = zendure_controller_v12_13_0/
ZIP-Test = PASS
```

Tatsächlich aus `version.py` verifiziert:

```text
APP_VERSION       = 12.13.0
APP_VERSION_LABEL = V12.13.0
APP_BUILD_ID      = v12.13.0-20260811
```

Quellmanifest:

```text
V12_13_0_SOURCE_MANIFEST.sha256
368 / 368 Dateien PASS
SHA256 des Manifests = 8914049a0b1441844d8ef2ab646479d263e51b726af183fcc67020acb3492bd0
```

Unabhängig aus der frisch entpackten Quellbasis wiederholt:

```text
pytest --collect-only       748 Tests
pytest                      748 PASS
pytest subtests             677 PASS
unittest -W error::ResourceWarning
                            748 PASS
ResourceWarnings            0
```

### 1.3 Relevante tatsächlich verifizierte V12.13.0-Verträge

```text
SettingsRegistry schema_version           = 1.23-s1.1
SettingsRegistry source target SHA256      = f67b8d09ae9a433c4cb0d3a720a0961d5b2a824b120251a63f2b19885356274a
Settings insgesamt                         = 212
aktive, editierbare LIVE/RESTART-Settings  = 188
  davon Nicht-Secrets                      = 187
  davon Secrets                            = 1 (MQTT_PASSWORD)
CONFIG_RUNTIME_SCHEMA_VERSION              = 1
Preview-TTL                                = 300 s
Preview-Maximum                            = 64
MEASUREMENT_SCHEMA_VERSION                 = 4
V4 Standard                                = 246 Felder
V4 Extended                                = 249 Felder
```

Der V12.13.0-Settingspfad besitzt bereits:

- Registry als Schemaautorität;
- Whole-Candidate-Validierung;
- Preview vor Commit;
- Sessionbindung und Preview-TTL;
- exakte Dateirevision/CAS;
- atomischen Config-Write mit `0600`, `fsync` und `os.replace`;
- Secretoperationen `keep / replace / clear`;
- `configured / effective / pending_restart`;
- First-Install-Vertrag;
- Last-Good-A/B mit Current-Pointer und fail-closed Recovery.

V13.0.0 darf diese Verträge **erweitern und wiederverwenden, aber nicht durch einen parallelen zweiten Config-Schreibpfad umgehen**.

---

## 2. Ziel und Release-Scope

V13.0.0 führt als neues Entwicklungsthema eine sichere Verwaltung von Konfigurationsständen sowie Import und Export ein und behebt gleichzeitig den nach V12.13.0 bestätigten SOC-Tagesgraph-Cachefehler.

Der Release umfasst genau zwei fachliche Teilblöcke:

1. **Konfigurationsstände / Import / Export**
2. **SOC-Tagesgraph: historisch korrekte, zeitbezogene Konfigurations-Overlays mit einmaligem V4-Backfill und inkrementeller Timelinepflege**

Die Zielversion ist gemäß Projekt-Versionierungsregel **V13.0.0**.

---

## 3. Ausdrückliche Nicht-Ziele und No-Regression-Bereiche

### 3.1 Kein Regler-Redesign

Ohne eine im Build neu auftretende zwingende technische Abhängigkeit bleiben unverändert:

- AUTO_GRID_EXPORT / AUTO_GRID_IMPORT / HOLD;
- Harvest-Zielwertbildung und Delta-/Absolutwertsemantik;
- Harvest monotonic/fresh-distinct Zeitsemantik;
- Primärspeicherpriorität;
- Cross-Charge;
- NIGHT_DISCHARGE / Reserve / Neutralisierung;
- MAX_SOC-/MIN_SOC-Regelwirkung;
- Command Lifecycle / Effect / Resync;
- Single-Owner-Safety;
- physische Commandpfade.

Der Graphfix ist **reine Anzeige-/Payloadkorrektur** und darf die Regelung nicht verändern.

### 3.2 Measurement bleibt V4-only

Unverändert:

- produktiver Writer ausschließlich V4;
- `MEASUREMENT_SCHEMA_VERSION = 4`;
- Standardheader 246 Felder;
- Extendedheader 249 Felder;
- V3 nur offline/read-only;
- kein V3-Runtimefallback;
- kein Measurement-V5;
- V12.12.2-Manifest-/Rotation-/Close-Härtung.

Die noch ausstehende natürliche Feldbeobachtung einer Rotation bleibt Beobachtungspunkt; V13.0.0 erzwingt dafür keine Rotation.

### 3.3 Keine neue Supply-Chain-/Installed-Tree-Kryptographie

V13.0.0 führt **keine** Installed-Tree-Signaturen, Paket-Signaturinfrastruktur oder sonstige Supply-Chain-Provenance ein.

Die unten spezifizierte SHA-256-Prüfung für Konfigurationsbundles ist ausschließlich eine **Datei-/Payload-Integritätsprüfung**. Sie ist keine Echtheits- oder Urheberbescheinigung und kein Schutz gegen einen Angreifer, der Datei und Hash gemeinsam verändern kann.

### 3.4 Host-Freeze nicht als ZEC-Performancebefund behandeln

Der historische rund 14-minütige Ausreißer aus dem Raspberry-Backup-/Host-Freeze bleibt ausdrücklich außerhalb dieses Releases.

---

## 4. Begriffe und fachliche Semantik

### 4.1 Aktive verwaltete Settings

Ein Setting gehört zum V13-Konfigurationsstand-Scope, wenn die **aktuelle** `SettingsRegistry` alle folgenden Bedingungen erfüllt:

```text
lifecycle == "active"
editability == EDITABLE
apply_class in {LIVE_NEXT_CYCLE, RESTART_REQUIRED}
```

Nicht über die Konfigurationsstände verwaltet werden:

- `MIGRATION_ONLY`;
- `READ_ONLY`;
- `PROTECTED_ACTION`;
- `reserved_inactive`;
- versteckte Alt-/Migrationswerte, soweit sie nicht vorher von der Migrationsengine konsumiert werden;
- Deploymentkonstanten außerhalb des normalen Configvertrags.

Auf der verifizierten V12.13.0-Basis ergibt das **188 aktive verwaltete Settings**, davon **187 Nicht-Secrets und 1 Secret (`MQTT_PASSWORD`)**.

Die Zahl wird in Tests aus der Registryregel abgeleitet und nicht als dauerhaft magische Produktkonstante verwendet.

### 4.2 Konfigurationsstand

Ein Konfigurationsstand ist ein **benannter, nicht aktiver Snapshot der Nutzerkonfigurations-Intention**. Er ist:

- kein Ersatz für `config.json`;
- kein Last-Good-Slot;
- kein Recovery-Pointer;
- nicht automatisch aktiv;
- nicht automatisch auf das Gerät anzuwenden.

### 4.3 Export und Transportziel

Ein Export ist ein portables ZEC-Konfigurationsbundle. Er verwendet dasselbe fachliche Bundleformat wie ein lokaler Stand. V13.0.0 unterscheidet zwei fachliche Exportzwecke:

```text
artifact_kind = "export"            vollständiger Sicherungs-/Migrations-Export
artifact_kind = "portable_profile"  teilbares, installationsübergreifendes Regelprofil
```

Ein vollständiger Export dient primär Backup, Wiederherstellung oder kontrollierter Systemmigration. Ein `portable_profile` ist ausdrücklich dafür vorgesehen, eine bewährte Regel-/Strategieabstimmung an ein anderes ZEC-System oder einen anderen Benutzer weiterzugeben.

Transportabel bedeutet **importierbar**, nicht blind kompatibel: Auf dem Zielsystem gelten immer Registry-/Schema-Kompatibilität, Migration, vollständige Servervalidierung, Diff, Secretregeln, CAS und explizite Bestätigung.

### 4.4 Portabilitätsklassen

Die SettingsRegistry erhält für alle aktiven verwalteten Settings eine explizite Portabilitätsklassifikation. Zulässige Klassen:

```text
portable_profile   installationsunabhängige Regel-/Strategieparameter
site_specific      an Anlage, Netz, Hardware oder lokale Topologie gebunden
local_runtime      lokaler Host-/Pfad-/Schnittstellenkontext
secret             Secret; nie automatisch teilbar
non_transferable   darf nicht in ein teilbares Profil
```

Sicherheitsregel: **Default ist nicht transportabel.** Kein aktives verwaltetes Setting darf für V13.0.0 unklassifiziert bleiben; Tests erzwingen vollständige Registryabdeckung. Nur `portable_profile` darf automatisch in einem teilbaren Regelprofil enthalten sein.

Die Klassifikation ist Registryautorität und wird nicht durch UI-Kategorien, Namen oder Heuristiken abgeleitet.

### 4.5 Import

Ein Import ist das Einlesen eines Bundles oder – ausschließlich im Expertenmodus – einer unterstützten Legacy-`config.json`. Ein Import ist zunächst **nur Analyse/Preview**. Aktivierung erfolgt erst nach Migration, kompletter Servervalidierung, Diff und explizitem Commit.

### 4.6 Load/Laden eines lokalen Standes

Das Laden eines lokalen benannten Standes verwendet **denselben Preview-/Validation-/Commit-Kern wie ein Import**. Es gibt keinen direkten „Stand aktivieren“-Schreibpfad.

---

## 5. Scope-Modell

### 5.1 Scope-Modi

V13.0.0 unterstützt für lokale Stände/vollständige Exporte drei Scopeformen und für teilbare Regelprofile einen abgeleiteten vierten Modus:

```text
full_managed
categories
keys
portable_profile
```

`portable_profile` wird ausschließlich aus Registrykeys mit Portabilitätsklasse `portable_profile` gebildet. Die konkrete sortierte Keyliste wird beim Export materialisiert.

#### `full_managed`

Alle zum Erstellzeitpunkt aktiven verwalteten Registrysettings.

#### `categories`

Eine oder mehrere Registry-Kategorien. Der Bundle-Scope wird bei Erstellung zusätzlich als **konkrete sortierte Keyliste** materialisiert, damit der spätere Inhalt nicht still durch neue Settings derselben Kategorie verändert wird.

#### `keys`

Explizite konkrete Registrykeys.

### 5.2 Standard-/Expertenumfang

**Standardmodus:**

- `full_managed` als Default für lokale Stände/vollständige Sicherung;
- alternativ Auswahl ganzer fachlicher Kategorien;
- zusätzlich Exporttyp **„Teilbares Regelprofil“** mit automatisch registrygefiltertem `portable_profile`-Scope;
- keine Einzelkey-Auswahl;
- Secrets niemals exportieren/einbetten.

**Expertenmodus:**

- zusätzlich Einzelkey-Auswahl für lokale/vollständige Exporte;
- technische Scope- und Portabilitätsinformationen;
- `portable_profile` bleibt strikt Registry-gefiltert und darf auch im Expertenmodus keine `site_specific`, `local_runtime`, `secret` oder `non_transferable` Keys aufnehmen;
- optionaler Secret-Export nur für vollständige Exporte gemäß Abschnitt 9;
- Legacy-`config.json`-Import.

### 5.3 Keine versteckten Änderungen

Ein Stand darf Expert-/`protected_expert`-Settings enthalten, wenn diese zum gewählten Scope gehören. Im Standardmodus dürfen solche Werte beim Preview jedoch **nicht unsichtbar geändert** werden.

Der Diff zeigt deshalb auch Änderungen an Expertwerten mindestens in einem eigenen Block:

```text
Erweiterte Einstellungen aus diesem Stand
```

mit Label, Wirkung/Apply-Klasse und Risikohinweis. Technische Keys können im Standardmodus sekundär dargestellt werden; die Änderung selbst darf nicht verborgen sein.

### 5.4 Compound-Felder

UI-Compoundfelder wie Nachtstart/-ende werden beim Bundle auf die tatsächlichen zugrunde liegenden Registrykeys abgebildet. Das Bundleformat speichert keine rein visuellen Pseudokeys.

### 5.5 Abhängigkeiten

Abhängige Keys werden bei einem Teil-Scope **nicht still automatisch hinzugefügt**. Stattdessen entscheidet die vollständige Servervalidierung über die resultierende Gesamtkonfiguration. Dadurch bleibt der gewählte Scope transparent und Abhängigkeiten werden nicht unbemerkt mitübernommen.

---

## 6. Snapshot-Semantik: explizite Nutzerwerte statt Default-Pinning

### 6.1 Grundsatz

Ein Konfigurationsstand soll die **Nutzerintention** erhalten und nicht bei jedem Speichern alle aktuell aufgelösten Defaults dauerhaft in `config.json` festschreiben.

Daher speichert ein Bundle für Nicht-Secrets getrennt:

1. den vollständigen konkreten Scope;
2. die im Quellstand **explizit persistierten Werte** innerhalb dieses Scopes;
3. die im Quellstand aufgelösten `configured`-Werte für Preview/Drift-Erkennung.

Beispiel:

```text
Scope enthält MAX_SOC_PERCENT und MIN_SOC_PERCENT.
MAX_SOC_PERCENT war explizit 80.
MIN_SOC_PERCENT war nicht in config.json vorhanden und kam aus dem Registrydefault.

explicit_values:
  MAX_SOC_PERCENT = 80

resolved_values:
  MAX_SOC_PERCENT = 80
  MIN_SOC_PERCENT = 10
```

### 6.2 Ladeverhalten

Für jeden **Nicht-Secret-Key im zu ladenden Scope**:

1. aktuellen expliziten Key zunächst aus dem Kandidaten entfernen;
2. wenn im Bundle unter `explicit_values` enthalten, den migrierten expliziten Wert setzen;
3. wenn nicht enthalten, den aktuellen Registrydefault durch die normale Candidate-/Registrylogik erben lassen.

Dadurch wird die explizit-vs.-geerbte Nutzerintention reproduziert.

### 6.3 Default-Drift

Wenn ein Stand aus einer älteren Registry stammt und ein damals geerbter Wert unter der aktuellen Registry einen anderen Default ergibt, muss Preview dies melden:

```text
INHERITED_DEFAULT_CHANGED
```

Der Diff zeigt:

- aufgelösten Wert im Quellstand;
- aufgelösten Wert unter der aktuellen Registry;
- Hinweis, dass der Quellstand für diesen Key keinen expliziten Override enthielt.

Das ist **kein stiller Fehler** und kein automatisches Pinning des alten Defaults. Der Nutzer kann den Preview bewusst bestätigen oder abbrechen.

### 6.4 Aktuelle unbekannte Keys

Unknown Keys, die bereits in der aktuellen produktiven `config.json` vorhanden sind, werden durch Import/Load **unverändert erhalten**, solange sie nicht von der kanonischen Migrationsengine ausdrücklich konsumiert werden.

Das bestehende Unknown-Key-Erhaltungsprinzip bleibt erhalten.

---

## 7. Lokaler Speicher benannter Konfigurationsstände

### 7.1 Pfad

Der Store liegt relativ zur produktiven Config und ist kein neuer vom Nutzer editierbarer Reglerparameter:

```text
<config-dir>/config-states/
```

Produktiv damit:

```text
/opt/zendure-controller/config-states/
```

### 7.2 Rechte und Filesystem-Sicherheit

Verbindlich:

```text
Verzeichnis: 0700
Dateien:      0600
Owner:        derselbe produktive ZEC-Owner wie config.json (aktuell pi:pi)
```

- nur reguläre Dateien;
- keine Symlink-Auflösung als State-Datei;
- State-ID wird intern generiert und nicht aus dem Anzeigenamen als Pfad gebildet;
- Pfadtraversal über Name/Importfilename unmöglich;
- temporäre Datei im selben Verzeichnis;
- `fsync` Datei;
- `os.replace`;
- `fsync` Verzeichnis.

### 7.3 State-ID und Anzeigename

Jeder lokale Stand erhält eine opaque ID, z. B. UUIDv4:

```text
state_id = 128-bit UUID
filename = <state_id>.zec-config.json
```

Der vom Nutzer vergebene Name ist reine Metadateninformation.

Grenzen:

```text
name        1..80 Unicode-Zeichen
beschreibung 0..500 Unicode-Zeichen
```

Steuerzeichen werden abgewiesen. Whitespace am Anfang/Ende wird normalisiert.

### 7.4 Größen-/Anzahlgrenzen

V13.0.0:

```text
max. lokale Stände = 100
max. Bundlegröße   = 1 MiB
```

Diese Grenzen schützen UI und Parser vor unkontrollierter Dateimenge. Sie sind keine Reglerparameter.

### 7.5 Laufzeitentkopplung

Der State-Store wird **nicht** im Regelzyklus, Readinesspfad oder Startup-Recovery inventarisiert.

- Listing/Validierung nur bei explizitem UI-/API-Aufruf;
- defekter State-Store darf `/ready` nicht auf `false` setzen;
- ein beschädigter einzelner Stand beeinflusst den Controller nicht;
- keine automatische Last-Good- oder Config-Reparatur aus diesem Store.

### 7.6 Erstellen eines lokalen Standes

Ein lokaler Stand aus „aktuelle Konfiguration speichern“ darf nur aus einer **validen primären Konfiguration** erzeugt werden.

Bei:

- fehlender Primärconfig;
- Runtime-invalid Primärconfig;
- noch nicht abgeschlossenem First-Install

ist „Aktuellen Stand speichern“ blockiert und erklärt den Grund.

Ein **Import zur Reparatur** einer invaliden Primärconfig bleibt dagegen erlaubt, sofern der resultierende Gesamt-Kandidat vollständig valide wird.

### 7.7 Metadaten ändern / löschen

Rename/Beschreibungsänderung und Delete verwenden State-Datei-CAS gegen deren aktuelle SHA-256-/State-Revision.

Löschen verändert niemals `config.json`, Effective State oder Last-Good. Es erfordert eine explizite Bestätigung.

---

## 8. Einheitliches Bundleformat

### 8.1 Formatname

```text
ZEC-CONFIG-BUNDLE
format_version = 1
Dateiendung = .zec-config.json
```

### 8.2 Top-Level-Struktur

Normative Struktur:

```json
{
  "format": "ZEC-CONFIG-BUNDLE",
  "format_version": 1,
  "payload": {
    "artifact_kind": "named_state",
    "artifact_id": "0d3f9f0d-....",
    "name": "Sommerbetrieb 2026",
    "description": "Vor Änderung der Nachtreserve",
    "created_at_utc": "2026-08-11T12:34:56Z",
    "source": {
      "app_version": "12.13.0",
      "app_build_id": "v12.13.0-20260811",
      "settings_registry_schema_version": "1.23-s1.1",
      "settings_registry_sha256": "f67b8d09ae9a433c4cb0d3a720a0961d5b2a824b120251a63f2b19885356274a",
      "config_runtime_schema_version": "1",
      "configured_typed_revision": "...",
      "config_file_revision": "..."
    },
    "scope": {
      "mode": "full_managed",
      "categories": [],
      "keys": ["...konkrete sortierte Registrykeys..."]
    },
    "explicit_values": {
      "MAX_SOC_PERCENT": 80
    },
    "resolved_values": {
      "MAX_SOC_PERCENT": 80,
      "MIN_SOC_PERCENT": 10
    },
    "secrets": {
      "MQTT_PASSWORD": {
        "included": false,
        "source_state": "set"
      }
    }
  },
  "integrity": {
    "algorithm": "sha256",
    "canonicalization": "ZEC-CANONICAL-JSON-V1",
    "payload_sha256": "..."
  }
}
```

Zulässige `artifact_kind`-Werte in V13.0.0:

```text
named_state
export
portable_profile
```

Für `portable_profile` gilt zusätzlich:

```text
scope.mode = "portable_profile"
scope.keys = konkrete sortierte, beim Export materialisierte Registrykeys
Secrets = niemals enthalten
Nicht-portable Keys = Parser/Preview blockiert, auch bei manipuliertem Bundle
```

Die `source`-Metadaten bleiben erhalten, damit das Zielsystem Registry-/Schema-/Versionskompatibilität und Migration beurteilen kann.

### 8.3 Canonical JSON V1

Für `payload_sha256` wird **nur** das Objekt `payload` kanonisiert. Die bestehende ZEC-Kanonisierung wird wiederverwendet:

```text
UTF-8
ensure_ascii = false
sort_keys = true
separators = (",", ":")
abschließendes "\n"
SHA-256 über exakt diese Bytes
```

Dadurch gibt es keine zirkuläre Hashberechnung über das Integritätsfeld.

### 8.4 Parser-Härtung

Vor jeder Migration muss der Bundleparser mindestens abweisen:

- Datei > 1 MiB;
- ungültiges UTF-8;
- ungültiges JSON;
- Nicht-Objekt als Root;
- doppelte JSON-Keys;
- `NaN`, `Infinity`, `-Infinity`;
- falschen Formatnamen;
- nicht unterstützte `format_version`;
- fehlende Pflichtmetadaten;
- ungültige Scopeform;
- nicht eindeutige Keys;
- Hashmismatch;
- ungültige Secretstruktur.

### 8.5 Bedeutung der Integrität

`payload_sha256` bestätigt nur, dass das Payload seit der Hashbildung unverändert ist. Es ist **keine digitale Signatur**.

Die UI formuliert daher „Integrität geprüft“ und nicht „Quelle authentisch“.

### 8.6 Exportfilename

Empfohlen:

```text
zec-config-<slug-name>-YYYYMMDD-HHMMSS.zec-config.json
```

Der Dateiname ist Komfort, nicht Identität. Maßgeblich sind Format, `artifact_id` und Payloadhash.

---

## 9. Secret-Semantik

### 9.1 Bestehenden Secretvertrag beibehalten

V13.0.0 verwendet weiterhin ausschließlich:

```text
keep
replace
clear
```

Ein Secret darf nie über den generischen Non-Secret-Patchkanal laufen.

### 9.2 Lokale benannte Stände

Lokale benannte Stände speichern in V13.0.0 **keinen Secret-Klartext**.

Sie speichern nur den Quellzustand:

```json
"MQTT_PASSWORD": {
  "included": false,
  "source_state": "set"
}
```

Beim Laden eines lokalen Standes lautet die Operation zwingend:

```text
keep
```

Damit kann ein lokaler Stand nicht versehentlich MQTT-Zugangsdaten überschreiben oder leeren.

### 9.3 Standard-Export

Standardmodus exportiert niemals Secretwerte.

- Secretwert fehlt im Bundle;
- `source_state = set|empty` darf zur Information enthalten sein;
- Import daraus führt standardmäßig zu `keep`.

### 9.4 Experten-Export mit Secret

Im Expertenmodus darf der Nutzer bei `artifact_kind = "export"` optional „Secrets in Export aufnehmen“ wählen. Für `portable_profile` ist Secretexport ausnahmslos verboten.

Voraussetzungen:

- ausdrückliche Aktivierung pro Export;
- Warnung, dass der Wert **im Klartext** in der Exportdatei steht;
- separate Bestätigung;
- kein Speichern des Secretwerts in Logs, Operational Events oder UI-History;
- HTTP-Antwort `Cache-Control: no-store`;
- kein temporäres persistentes Serverfile für den Download.

Beispiel:

```json
"MQTT_PASSWORD": {
  "included": true,
  "source_state": "set",
  "value": "<secret>"
}
```

V13.0.0 führt hierfür **keine eigene Verschlüsselungsschicht** ein.

### 9.5 Import eines Bundles mit Secret

Selbst wenn ein Bundle Secretwerte enthält, ist das Defaultverhalten:

```text
keep current secret
```

Nur im Expertenmodus kann „Secrets aus Quelle übernehmen“ explizit aktiviert werden.

Dann gilt:

- Quellsecret gesetzt + Wert vorhanden → `replace`;
- Quelle ausdrücklich leer → `clear`;
- Secret nicht enthalten → `keep`;
- ungültige/inkonsistente Secretmetadaten → Preview blockiert.

`clear` benötigt die bereits etablierte ausdrückliche Bestätigung.

### 9.6 Secret-Diff

Nie Klartext anzeigen.

Erlaubte Darstellung:

```text
MQTT-Passwort: bleibt unverändert
MQTT-Passwort: wird ersetzt
MQTT-Passwort: wird geleert
```

Auch Candidate-, Preview- und Auditstrukturen dürfen den Wert nicht in serialisierbare Diagnoseobjekte übernehmen, sofern er dort nicht zwingend für den Commit benötigt wird. Der Previewrecord darf ihn nur sessiongebunden und kurzlebig im bestehenden In-Memory-Kontext halten.

---

## 10. Kompatibilitätsmodell

### 10.1 Autoritäten

Kompatibilität wird primär aus folgenden Feldern entschieden:

1. `format` / `format_version`;
2. `config_runtime_schema_version`;
3. `settings_registry_schema_version`;
4. `settings_registry_sha256`;
5. vorhandener expliziter Migrationspfad;
6. Quell-App-Version/Build als zusätzliche Evidenz und UI-Hinweis.

Die App-SemVer allein ist **nicht** die Configschemaautorität.

### 10.2 Direkt kompatibel

Direkte Kompatibilität liegt vor, wenn mindestens gilt:

```text
format_version == current supported format version
config_runtime_schema_version == current
settings_registry_sha256 == current registry hash
```

Eine andere Build-ID oder Patchversion ist dann kein automatischer Blocker.

Wenn die Quell-App numerisch neuer ist als die laufende App, wird zusätzlich gewarnt:

```text
SOURCE_APP_NEWER_SAME_CONFIG_SCHEMA
```

und eine Bestätigung verlangt.

### 10.3 Migration erforderlich

Wenn Registry-/Configschema vom aktuellen Stand abweichen, darf nur weitergearbeitet werden, wenn ein **explizit unterstützter Migrationspfad** existiert.

Die Migrationsengine liefert:

- `migration_steps`;
- konsumierte Legacykeys;
- umbenannte/transformierte Keys;
- verworfene obsolete Keys mit Begründung;
- Warnungen;
- resultierendes aktuelles Quellschema.

### 10.4 Nicht unterstützt / fail closed

Blockieren:

- unbekannte höhere Bundleformatversion;
- höheres/unbekanntes Config-Runtime-Schema ohne Migrationspfad;
- unbekannte neuere Registrystruktur ohne kompatiblen Pfad;
- Migration mit Mehrdeutigkeit oder Konflikt;
- Wertverlust, der nicht als definierte Migration ausgewiesen ist.

Keine „best effort“-Interpretation.

### 10.5 Registry-Drift

Ein abweichender Registryhash ist nicht automatisch ein Fehler, wenn ein definierter Migrationspfad existiert. Preview kennzeichnet dann:

```text
REGISTRY_DRIFT_MIGRATED
```

und zeigt die ausgeführten Schritte.

---

## 11. Eine gemeinsame Migrationsautorität

### 11.1 Kein doppelter Migrationscode

Die bereits vorhandene Migration, die u. a. folgende V12.13.0-/Legacyfälle kennt,

- Measurement-Schema 3 → 4;
- `ZENDURE_BATTERY_CAPACITY_KWH` → `..._WH`;
- `SMA_DISCHARGE_BLOCK_W` → `CROSS_CHARGE_SIGNIFICANT_W`;
- Entfernung nicht mehr wirksamer Legacykeys;
- Entfernung `SERVICE_RESTART_COMMAND`;
- Unknown-Key-Erhalt,

wird nicht separat für Import nachgebaut.

V13.0.0 soll die vorhandene Logik in eine **gemeinsame, pure/importierbare ConfigMigrationEngine** überführen bzw. die vorhandene Authority so kapseln, dass:

- Installer/CLI-Migration;
- Bundleimport;
- Legacy-Configimport

dieselbe Transformationslogik verwenden.

### 11.2 Reihenfolge

Importreihenfolge zwingend:

```text
1. Datei lesen / harte Parsergrenzen
2. Bundleintegrität prüfen
3. Quelltyp und Quellschema bestimmen
4. Source-Migration auf aktuelles Schema
5. importierbaren Scope bestimmen / Legacykeys klassifizieren
6. Quellwerte in aktuellen Candidate-Base integrieren
7. Secretoperationen anwenden
8. vollständige Registry-/Servervalidierung
9. Diff + ApplyPlan + pending_restart prognostizieren
10. expliziter Commit
```

**Migration findet damit vor dem Laden/Commit statt.**

### 11.3 Migration muss idempotent bleiben

Ein bereits aktueller Bundle-/Configstand darf durch erneute Migration nicht verändert werden.

---

## 12. Legacy-`config.json`-Import

### 12.1 Nur Expertenmodus

Eine rohe historische/aktuelle `config.json` ist kein ZEC-CONFIG-BUNDLE und besitzt keine Bundleintegritätsmetadaten.

Sie kann in V13.0.0 ausschließlich im Expertenmodus importiert werden.

Preview zeigt immer:

```text
LEGACY_RAW_CONFIG_NO_BUNDLE_INTEGRITY
```

### 12.2 Keine Direktübernahme

Auch Legacy-Raw-Import durchläuft:

- strikten JSON-Parser;
- aktuelle Migration;
- Registryklassifikation;
- vollständige Servervalidierung;
- Secretvertrag;
- Preview/Diff;
- CAS;
- atomischen Commit.

### 12.3 Legacy-Unknown-Keys

Imported Unknown Keys werden **nicht neu in die aktuelle Config geschrieben**.

- Standardmodus: Legacyimport ohnehin nicht verfügbar;
- Expertenmodus: Unknown Imports werden aufgelistet und standardmäßig blockiert;
- Nutzer kann ausdrücklich „unbekannte importierte Keys überspringen“ bestätigen;
- vorhandene Unknown Keys der aktuellen Zielconfig bleiben unabhängig davon erhalten.

Damit wird kein möglicherweise zukünftiger unbekannter Schlüssel still aktiviert.

### 12.4 Migration-only Werte

Migration-only Legacykeys dürfen von der Migrationsengine konsumiert werden. Nach erfolgreicher Migration dürfen sie nicht als aktiv importierbarer Scope erscheinen.

---

## 13. Preview-/Diff-Vertrag

### 13.1 Eine gemeinsame Previewengine

V13.0.0 darf für Import/Load keine separate verkürzte Validierungslogik implementieren.

Der bestehende `SettingsService`-Previewkern wird so refaktoriert/erweitert, dass folgende Quellen denselben Whole-Candidate-Weg benutzen:

```text
UI-Draft
lokaler Konfigurationsstand
ZEC-CONFIG-BUNDLE-Import
Legacy-config.json-Import
```

### 13.2 Preview-Bindungen

Ein gültiger Load-/Import-Preview ist mindestens gebunden an:

- Session;
- aktuelle Config-`base_revision` (exact-byte CAS);
- Source-Artifakt-ID;
- Source-Payload-SHA256;
- bei lokalem State dessen aktuelle State-Revision;
- ausgewählten Scope;
- Migrationsresultat;
- Secretentscheidungen;
- Candidate Typed Revision;
- erforderliche Confirmations;
- bestehendes TTL = 300 s.

### 13.3 Previewresponse

Mindestens:

```text
status = ready | blocked
preview_id
expires_at_epoch
base_revision
candidate_typed_revision
source_metadata
compatibility
migration_steps
scope
skipped_keys
unknown_source_keys
diff
issues
confirmations_required
apply_plan
pending_restart_after_commit
```

### 13.4 Vollständige Servervalidierung

Clientvalidierung bleibt UX-Hilfe. Maßgeblich ist die Servervalidierung des **vollständigen resultierenden Config-Kandidaten**.

Beispiele für weiterhin serverseitig blockierende Konflikte:

- Min-/Max-SOC-Konflikt;
- ungültiges Nachtfenster;
- Reserve außerhalb zulässiger Grenzen;
- widersprüchliche Source-/Schnittstellenparameter;
- fehlende First-Install-Pflichtfelder;
- Protected Action im normalen Configpfad;
- ungültiger Secretvertrag.

### 13.5 Diff

Diff ist `current configured` gegen `candidate configured`, nicht Dateibytes gegen Dateibytes.

Je Änderung mindestens:

- fachliches Label;
- Key;
- Kategorie;
- alter Wert;
- neuer Wert;
- Herkunft `explicit/inherited` soweit relevant;
- Apply-Klasse;
- Apply-Text;
- Risiko;
- bei Secret nur Operation, nie Wert.

### 13.6 Default-Drift und Migration getrennt darstellen

Preview unterscheidet sichtbar:

```text
Direkte Wertänderung aus Stand
Migration
Geänderter aktueller Default bei ursprünglich geerbtem Wert
Übersprungener Legacy-/Unknown-Key
```

### 13.7 Ungespeicherter Browser-Draft

Wenn auf der Settingsseite ungespeicherte Draftänderungen existieren, darf Load/Import nicht still darübergelegt werden.

UI verlangt zuerst:

```text
Änderungen speichern
oder
Änderungen verwerfen
```

Danach neuer Preview gegen die aktuelle Revision.

---

## 14. CAS-/Revision-/Commit-Vertrag

### 14.1 Exact-byte CAS bleibt Autorität

Commit verwendet die vorhandene `cas_revision()`-/Stable-Read-Semantik.

Unmittelbar vor Persistenz:

```text
re-read config.json
SHA-256/exact-byte revision vergleichen
```

Abweichung:

```text
HTTP/Service-Konflikt: CONFIG_REVISION_CONFLICT
keine Persistenz
Preview verwerfen
neuer Preview erforderlich
```

### 14.2 Source-CAS zusätzlich

Für einen lokalen Stand wird unmittelbar vor Commit dessen State-Revision/Payloadhash erneut geprüft.

Wurde der Stand seit Preview geändert oder gelöscht:

```text
CONFIG_STATE_REVISION_CONFLICT
```

kein Commit.

Für einen hochgeladenen Import wird der Preview an den serverseitig/sessiongebunden gehaltenen Quellhash gebunden; der Client kann beim Commit kein anderes Payload unterschieben.

### 14.3 Revalidation beim Commit

Auch nach gültigem Preview wird der Whole Candidate unmittelbar vor Write nochmals serverseitig validiert. Preview ist kein Freibrief für einen späteren ungeprüften Write.

### 14.4 Atomischer Write

Weiterhin:

```text
temp im gleichen Verzeichnis
0600
fsync(temp)
os.replace(temp, config.json)
chmod/ownership prüfen
fsync(config-dir)
reread exact bytes
```

### 14.5 V13-Härtung: Rollback bei Post-Write-Verify-Fehler

Der aktuelle V12.13.0-Code erkennt einen `CONFIG_POST_WRITE_VERIFY_FAILED`, stellt die vorherigen Bytes aber nicht selbst wieder her. V13.0.0 härtet diesen gemeinsamen Commitpfad.

Vor Replace werden die stabil gelesenen Altbytes gehalten.

Wenn der Post-Write-Reread die geschriebenen Bytes nicht exakt bestätigt:

1. Runtime übernimmt den neuen Candidate **nicht**;
2. vorhandene Altbytes werden über denselben atomischen Writepfad wiederhergestellt;
3. Wiederherstellung wird erneut exact-byte verifiziert;
4. Commit antwortet als Fehler.

Wenn vorher keine Config existierte (First-Install), wird die fehlgeschlagene neue Datei bestmöglich entfernt und das Verzeichnis synchronisiert.

Scheitert auch die Wiederherstellung:

```text
CONFIG_COMMIT_ROLLBACK_FAILED
```

- niemals Erfolg melden;
- tatsächlichen Configzustand neu einlesen;
- Config Health fail-closed bewerten;
- Runtime darf keinen unbestätigten Candidate als effective übernehmen.

Diese Härtung gilt anschließend für **alle** Settingscommits, nicht nur Import, weil alle denselben Persistenzpfad verwenden sollen.

### 14.6 Kein automatischer Neustart

Ein Import/Load startet den Controllerdienst nicht automatisch neu.

Restart-required Änderungen werden über das vorhandene `pending_restart`-Modell sichtbar und können anschließend über die bestehende geschützte Neustartaktion angewendet werden.

---

## 15. `configured / effective / pending_restart`

### 15.1 Erfolgreicher Commit

Nach Commit:

- `configured` = neuer validierter persistierter Nutzerstand;
- `LIVE_NEXT_CYCLE`-Änderungen gehen gemäß bestehendem RuntimeManager in `effective` über;
- `RESTART_REQUIRED` bleibt bis Neustart auf bisherigem Startup-Effective;
- `pending_restart_keys` wird neu berechnet.

### 15.2 Preview muss Neustartwirkung vorhersagen

Preview zeigt getrennt:

```text
Wirksam im nächsten Regelzyklus
Erfordert Controller-Neustart
```

und den erwarteten `pending_restart`-Status nach Commit.

### 15.3 Pending-Restart kann durch Rücknahme verschwinden

Wenn ein Stand einen restart-required Key wieder exakt auf den aktuell effektiven Wert zurücksetzt, muss dessen Pending-Restart-Eintrag ohne unnötigen Neustart verschwinden.

### 15.4 Invalid-primary Repair

Wenn die Primärconfig invalid ist, darf ein Import als Recovery-/Reparaturweg dienen:

- Candidate-Base = aktuell invalid gelesene Raw-Config gemäß bestehender Runtime-Semantik;
- CAS = Revision dieser Raw-Datei;
- Unknown Keys erhalten;
- Commit nur, wenn der **gesamte** resultierende Candidate valide ist.

First-Install bleibt ebenfalls vollständig servervalidiert; fehlende erforderliche Felder blockieren.

---

## 16. Last-Good-/Recovery-Wechselwirkungen

### 16.1 Strikte Trennung

Konfigurationsstände sind **niemals** Last-Good-Kandidaten.

Create/List/Rename/Delete/Export/Import-Inspect verändern nicht:

- Slot A;
- Slot B;
- Current-Pointer;
- Manifestgeneration;
- Recoveryeligibility.

### 16.2 Nach erfolgreichem Configcommit

Es gilt unverändert die existierende Last-Good-Promotion-Logik.

Insbesondere keine unmittelbare Promotion allein aufgrund eines erfolgreichen Importcommits.

Promotion erst nach den bereits etablierten Bedingungen, u. a.:

- Primärconfig valide;
- Effective Source = primary;
- NORMAL/Ready-Vertrag erfüllt;
- kein `pending_restart`;
- Stable-Ready-Nachweis 300 s;
- sonstige bestehende Eligibilitybedingungen.

Damit bleibt der bisherige Last-Good-Stand während der unmittelbaren Nach-Import-Phase als echter Recoveryanker erhalten.

### 16.3 Startup-Recovery unverändert fail closed

Invalides `config.json` nach Neustart verwendet weiterhin ausschließlich den bestehenden A/B-/Pointervertrag. Der neue State-Store wird dabei weder durchsucht noch automatisch geladen.

### 16.4 Pointer-Reparatur getrennt

Die geschützte Last-Good-Pointer-Reparatur bleibt eine administrative Recoveryaktion und wird weder durch „Stand laden“ noch durch Import ausgelöst.

---

## 17. UI-/UX-Vertrag

### 17.1 Platzierung

„Konfigurationsstände“ wird als eigene Funktion im Settingskontext integriert, **nicht** als künstlicher Registryparameter.

Empfohlen ist ein eigener Settings-Unterbereich/Toolbar-Einstieg:

```text
Settings → Konfigurationsstände
```

Die globale Navigation und Standard/Experte-Umschaltung bleiben erhalten.

### 17.2 Standardansicht

Mindestens:

- Liste lokaler Stände;
- Name;
- Beschreibung gekürzt;
- Erstellzeit;
- Quellversion;
- Scope-Zusammenfassung;
- Integritätsstatus;
- Aktionen: `Vorschau/Laden`, `Exportieren`, `Umbenennen`, `Löschen`;
- `Aktuellen Stand speichern`;
- `Importieren` für ZEC-CONFIG-BUNDLE;
- `Aktuelle Konfiguration exportieren`;
- `Teilbares Regelprofil exportieren` für systemübergreifenden Austausch, automatisch auf portable Registrykeys begrenzt.

Standard-Create:

- Defaultscope `full_managed`;
- optional Kategorien;
- keine Secrets.

### 17.3 Expertenansicht ergänzt

Zusätzlich:

- konkrete Keyliste;
- Einzelkey-Scope;
- Registryschema/-hash;
- Config-Runtime-Schema;
- Config-/Typed-Revision der Quelle;
- Bundle-Payloadhash;
- Portabilitätsklasse je Key und Ausschlussgrund nicht-portabler Werte;
- Migrationsreport;
- Default-Drift;
- übersprungene/Unknown Keys;
- optionaler Secret-Export;
- Secretübernahme beim Import;
- Legacy-`config.json`-Import;
- detaillierter ApplyPlan.

Expertenmodus bleibt Superset; Standardinformationen verschwinden nicht.

### 17.4 Status defekter lokaler Stände

Ein ungültiger/korrupt gewordener State wird in der Liste als nicht ladbar markiert, z. B.:

```text
Integritätsprüfung fehlgeschlagen
```

Er darf nicht zum Controllerfehler hochgestuft werden.

### 17.5 Mandatory Preview

Jede Lade-/Importaktion führt in denselben Änderungsdialog wie der bestehende Settingspreview bzw. eine konsistente Erweiterung davon.

Es gibt keinen Button, der einen Stand ohne Preview direkt aktiviert.

### 17.6 Responsive Verhalten

Pflichtsmokes mindestens:

```text
Desktop 1440×900
Mobil    390×844
```

- kein horizontaler Pageoverflow;
- Modal intern scrollbar;
- Commit/Abbrechen erreichbar;
- Hintergrund bei offenem Modal nicht mitscrollend;
- Kategorien-/State-Liste auf Mobile benutzbar.

### 17.7 Hilfe/Handbuch

Settings-Hilfe/Handbuch erhält mindestens:

- Was ist ein Konfigurationsstand?
- Unterschied Stand / Export / Last-Good;
- Scope;
- Preview/Diff;
- `configured/effective/pending_restart`;
- Secretverhalten;
- vollständiger Export vs. teilbares Regelprofil;
- weshalb anlagen-/hostbezogene Settings nicht automatisch übertragen werden;
- Integrität ≠ Authentizität;
- Legacyimport;
- Rollback-/Recoveryverhalten.

---

## 18. API-/Servicevertrag

Die konkrete interne Dateiaufteilung ist Implementierungsdetail; die folgenden fachlichen Operationen müssen existieren. Pfadnamen dürfen bei der Umsetzung nur aus zwingendem Frameworkgrund leicht angepasst werden, ohne Semantik zu ändern.

### 18.1 Lokale States

```text
GET    /config-states
POST   /config-states/create
PATCH  /config-states/{state_id}
DELETE /config-states/{state_id}
POST   /config-states/{state_id}/preview
POST   /config-states/{state_id}/export
```

### 18.2 Export/Import

```text
POST /config-export
POST /config-profile-export
POST /config-import/inspect
POST /config-import/{import_token}/preview
```

### 18.3 Commit

Bevorzugt bleibt **ein einziger Settings-Commitpfad**:

```text
POST /settings/commit
```

Ein Import-/State-Preview erzeugt einen normalen sessiongebundenen `preview_id`, der mit erweitertem Quellenbinding in denselben Commitpfad läuft.

### 18.4 Security für Weboperationen

- bestehender Session-/CSRF-/Origin-Vertrag;
- keine GET-Requests für mutierende Aktionen;
- `Cache-Control: no-store` für Preview, Import und Secret-Export;
- Importgröße vor Parse begrenzen;
- keine importierten Dateiinhalte in Logs schreiben;
- kein Multipart-Zwang, falls Browser-FileReader + begrenzter UTF-8-Body den bestehenden Stack einfacher hält.

### 18.5 Importtoken

`/config-import/inspect` erzeugt für einen valid geparsten Upload einen kurzlebigen, sessiongebundenen Token. Der Server hält entweder das begrenzte Payload oder dessen kanonisch geprüfte Repräsentation nur transient im Speicher.

Kein automatisches persistentes Ablegen eines Uploads.

Ein Import kann erst nach erfolgreichem Preview optional bewusst als lokaler Stand gespeichert werden; dabei werden Secrets wieder entfernt.

---

## 19. Audit-/Diagnosevertrag

### 19.1 Keine Secretwerte

Niemals Secretklartext in:

- Logs;
- Exceptions;
- Operational Events;
- Browserconsole;
- Diffresponse;
- Auditmetadaten.

### 19.2 Erfolgreicher Configcommit

Diagnostisch nachvollziehbar mindestens:

- Operation `settings_edit | config_state_load | config_import`;
- Quelle/State-ID ohne Dateiinhalte;
- Source-Payloadhash;
- alte Configrevision;
- neue Configrevision;
- neue Typed Revision;
- geänderte Keys;
- Migrationsteps;
- ApplyPlan;
- pending_restart;
- Zeitpunkt.

Ob diese Daten in bestehendes Audit-/Operational-Event-System oder einen settingsspezifischen Auditpfad gehen, wird bei der Implementierung an der vorhandenen Architektur ausgerichtet; **kein synchroner SQLite-/I/O-Pfad darf in den Regelzyklus gelangen**.

### 19.3 Fehlversuche

Parser-/Hash-/Validation-/CAS-Fehler dürfen diagnostisch klassifiziert werden, aber hochgeladene Configwerte und Secrets nicht vollständig loggen.

---

## 20. Fehler- und Rollbackszenarien

| Szenario | Erwartung |
|---|---|
| Bundle ungültiges JSON/UTF-8 | vor Migration blockieren; kein State/Config-Write |
| Duplicate JSON key | blockieren |
| Bundle >1 MiB | blockieren |
| Payloadhash falsch | `CONFIG_BUNDLE_INTEGRITY_FAILED`; blockieren |
| unbekannte Formatversion | blockieren |
| nicht migrierbares neueres Schema | blockieren |
| bekannte ältere Quelle | migrieren, Schritte anzeigen |
| aktueller Config-CAS ändert sich nach Preview | 409/`CONFIG_REVISION_CONFLICT`; kein Write |
| lokaler State ändert sich nach Preview | `CONFIG_STATE_REVISION_CONFLICT`; kein Write |
| Whole-Candidate-Validation blockiert | kein Commit-Previewtoken bzw. nicht committable |
| Bundle enthält Secret, Nutzer übernimmt es nicht | `keep`; aktuelles Secret unverändert |
| `portable_profile` enthält nicht-portablen oder Secret-Key | blockieren; nicht still übernehmen/überspringen |
| Secret `clear` gewählt | explizite Bestätigung; danach normaler Commit |
| Imported Unknown Key | Expert: blockiert oder explizit überspringen; nie neu persistieren |
| Zielconfig besitzt bestehenden Unknown Key | unverändert erhalten |
| Write scheitert vor Replace | Altconfig unverändert |
| Post-Write-Reread falsch | Altbytes atomisch wiederherstellen; Runtime unverändert |
| Rollback der Altbytes scheitert | fail closed, kein Erfolg, Config Health neu bewerten |
| erfolgreicher Commit mit Restartkeys | configured neu; effective für diese Keys alt; pending_restart true |
| State-Store defekt | Controller/Ready unbeeinflusst; Statefunktion zeigt Fehler |
| Importupload analysiert, aber nicht committet | keine Configänderung; kein persistentes Uploadfile |
| lokaler State gelöscht | keine Config-/Last-Good-Wirkung |
| Config nach Commit noch nicht stable-ready | Last-Good noch nicht promoten |

---

## 21. SOC-Tagesgraph: historisch korrekte Config-Overlays

### 21.1 Verifizierter V12.13.0-Befund

Die Produktivevidenz zeigt gleichzeitig:

```text
Zendure-Statuskarte: Max-SOC 80 %
SOC-Graph-Legende:   Max-SOC 99 %
Graphstatus:          Cache hit
```

Der ausgelieferte V12.13.0-Code bestätigt die unmittelbare Cacheursache: `build_storage_soc_day_payload()` cached das vollständige Payload einschließlich:

```text
thresholds.min_soc
thresholds.max_soc
thresholds.reserve_soc
night_window.start
night_window.end
```

Der Cache-Key enthält diese Werte nicht. Eine reine Lösung „bei jedem Response aktuelle Effective Config auf das gecachte historische Payload legen“ ist jedoch **nur für die Gegenwart korrekt und für historische Tage fachlich falsch**.

Beispiel:

```text
09.08.2026 wirksam: NIGHT_START = 21:30
11.08.2026 wirksam: NIGHT_START = 23:00
```

Der Graph des 09.08.2026 muss weiterhin 21:30 darstellen. Eine nachträgliche 23:00-Markierung wäre historische Verfälschung.

### 21.2 Bereits vorhandene historische Autorität in Measurement V4

V12.13.0 besitzt die für eine Rekonstruktion erforderliche Primärinformation bereits:

1. Jede Measurement-V4-Zeile enthält `config_control_hash`.
2. `zec_config_snapshots.json` ordnet diesem Hash einen regelrelevanten Config-Snapshot zu.
3. `CONTROL_SNAPSHOT_KEYS` enthält bereits mindestens:

```text
MIN_SOC_PERCENT
MAX_SOC_PERCENT
NIGHT_DISCHARGE_STOP_SOC_PERCENT
NIGHT_START_HOUR
NIGHT_START_MINUTE
NIGHT_END_HOUR
NIGHT_END_MINUTE
NIGHT_DISCHARGE_START
NIGHT_DISCHARGE_END
```

Der bestehende SQLite-Graphstore (`measurement_raw` / `measurement_1min`) speichert den `config_control_hash` dagegen noch nicht. Genau diese Verdichtungslücke wird in V13.0.0 geschlossen. Measurement V4 selbst bleibt unverändert V4-only; es entsteht kein V5-Schema.

### 21.3 Historische Overlay-Semantik

Graph-Overlays sind **zeitbezogene Effective-Config-Segmente**, keine Eigenschaften „des Tages“ und keine Eigenschaften der heute aktuellen Config.

Normative Overlaywerte je Segment:

```text
min_soc     = historisch gültiges MIN_SOC_PERCENT
max_soc     = historisch gültiges MAX_SOC_PERCENT
reserve_soc = historisch gültiges NIGHT_DISCHARGE_STOP_SOC_PERCENT
night_start = historisch gültiges NIGHT_START_HOUR:NIGHT_START_MINUTE
night_end   = historisch gültiges NIGHT_END_HOUR:NIGHT_END_MINUTE
```

Ändert sich ein Overlayparameter innerhalb eines Tages, muss die Darstellung segmentiert sein. Beispiel:

```text
00:00–17:00  MAX_SOC = 99 %
17:00–24:00  MAX_SOC = 80 %
```

Linie, Legende und Nachtfenster-Shading dürfen einen solchen Wechsel nicht rückwirkend über den ganzen Tag glätten.

### 21.4 Neue schlanke Graph-Config-Timeline

Der SQLite-Graphstore erhält eine kleine, von den Messpunkten getrennte Timeline, beispielsweise semantisch:

```text
graph_config_timeline
---------------------
effective_from_ms
config_control_hash
min_soc_percent
max_soc_percent
reserve_soc_percent
night_start_hhmm
night_end_hhmm
source
```

Die konkrete Tabellen-/Spaltenbenennung ist Implementierungsdetail; verbindlich sind Semantik und Eindeutigkeit.

Es wird **nur bei einem fachlich relevanten Hash-/Overlaywechsel** ein neuer Timelineeintrag erzeugt. Tausende identische Messzeilen erzeugen keine tausenden Configeinträge.

Timeline-Invarianten:

- monoton nach `effective_from_ms` sortierbar;
- gleicher Hash + gleiche Overlaywerte wird dedupliziert;
- ein Zeitsegment ist `[effective_from, next_effective_from)`;
- keine Timelinezeile darf einen fehlenden Snapshot durch aktuelle Config ersetzen;
- Timelinefehler dürfen den Controller-/Readinesspfad nicht blockieren.

### 21.5 Einmaliger externer V4→Graph-Timeline-Backfill

Für den bereits vorhandenen historischen Datenbestand wird V13.0.0 ein **idempotentes externes Maintenance-/Migrationstool** bereitstellen. Es ist keine normale dauerhaft benötigte Benutzer-Importfunktion.

Bevorzugter Arbeitsname:

```text
tools/backfill_graph_config_timeline.py
```

Der V13.0.0-Installer ruft dieses Tool nach Anlage/Upgrade der Graphstore-Struktur einmal kontrolliert auf. Es kann zusätzlich manuell erneut ausgeführt werden, ohne Duplikate oder semantische Änderungen zu erzeugen.

Backfillpipeline:

```text
vorhandene Measurement-V4-Dateien
  → Zeit + config_control_hash lesen
  → nur Hashwechsel materialisieren
  → Hash gegen zugehöriges zec_config_snapshots.json auflösen
  → Overlayparameter extrahieren
  → graph_config_timeline transaktional upserten/deduplizieren
  → Fortschritt/Abdeckung dokumentieren
```

Verbindliche Eigenschaften:

- read-only gegenüber historischen V4-Dateien und `zec_config_snapshots.json`;
- kein V3-Runtimepfad; V3 wird nicht als neue Runtimequelle eingeführt;
- kein Schreiben in Last-Good oder `config.json`;
- keine Gerätekommandos;
- Controller/Mosquitto werden für den Backfill nicht gestoppt;
- SQLitewrites in kleinen Transaktionen/batches;
- resumierbar bzw. vollständig wiederholbar;
- bei Abbruch bleibt vorhandene Timeline konsistent;
- nur eindeutig rekonstruierbare Abschnitte werden als historisch belegt markiert.

Das Tool ist der **einmalige Import/Backfill für den Altbestand**. Danach ist kein manueller Import für neue Daten nötig.

### 21.6 Laufende inkrementelle Pflege ab V13.0.0

Nach erfolgreichem Upgrade pflegt ZEC die Timeline automatisch weiter.

Autorität bleibt die tatsächlich effektive Runtimekonfiguration bzw. der dazugehörige V4-`config_control_hash`. Die Timelinepflege darf keinen zweiten Configzustand erfinden.

Mindestens gilt:

- bei einem neuen relevanten `config_control_hash`/Overlayzustand genau einen neuen Timelineeintrag anlegen;
- identische Zustände deduplizieren;
- bei einem erfolgreichen LIVE-Configwechsel muss die neue Overlaysemantik für den aktuellen Graph unmittelbar ab dem Wechselzeitpunkt verfügbar werden, ohne den historischen Tagesabschnitt davor umzuschreiben;
- Restart-required Semantik darf erst ab tatsächlicher Effective-Wirkung als historisch wirksam gelten;
- die Timelinepflege liegt außerhalb des Regelalgorithmus und darf dessen Reaktionszeit nicht beeinflussen.

Die Umsetzung kann den bestehenden Measurement-/Config-Snapshot-Pfad wiederverwenden oder einen schlanken Hook nach bestätigtem Effective-Configwechsel verwenden. Verbindlich ist, dass `configured` nicht fälschlich als bereits historisch `effective` behandelt wird.

### 21.7 Response- und Cachearchitektur

Der teure Tagesdaten-Cache bleibt für historische SOC-/Leistungspunkte erhalten.

Bevorzugt:

```text
cached base payload
  = historische Tagespunkte + statische Tages-/Storageinformationen

response payload
  = cached base payload
  + graph_config_segments für angefragten Zeitraum
  + daraus abgeleitete Overlaydarstellung
```

Die fünf Overlaywerte werden **nicht** einfach in den Tagesdaten-Cache-Key aufgenommen. Ein Configwechsel darf keinen unnötigen SQLite-Rebuild der SOC-Punkte erzwingen.

Für den aktuellen Zeitpunkt darf die aktuelle Effective Config nur das **gegenwärtige/finale Segment** ergänzen; sie darf niemals rückwirkend historische Segmente überschreiben.

### 21.8 Fehlende historische Zuordnung

Kann ein historischer `config_control_hash` nicht eindeutig gegen einen Snapshot aufgelöst werden, gilt:

```text
historische Konfiguration für diesen Zeitraum nicht verfügbar
```

Dann werden die nicht belegbaren Overlays für das betreffende Segment ausgelassen/als unbekannt markiert.

Verboten:

- Fallback auf heutige Effective Config für den historischen Abschnitt;
- Raten aus benachbarten Tagen ohne eindeutige Evidenz;
- stilles Übernehmen eines anderen Hash-Snapshots.

Messpunkte selbst bleiben darstellbar; nur die nicht belegbaren Konfigurations-Overlays verlieren für den betroffenen Abschnitt ihre Aussage.

### 21.9 Keine Regler-/Measurement-Wirkung

Der Fix verändert nicht:

- MAX_SOC-/MIN_SOC-Limiter;
- Nachtreserve;
- Nachtmoduszeiten;
- Controllerzielwerte;
- AUTO/Harvest/Cross-Charge/NIGHT;
- Command Lifecycle/Resync;
- Measurement-V4-Header 246/249;
- vorhandene historische V4-Dateien.

Er ergänzt ausschließlich Graphstore-/Payload-/Darstellungsmetadaten und den einmaligen Backfill.

### 21.10 Pflichtregressionen

Mindestens:

1. Historischer Tag mit `MAX_SOC=99` bleibt nach heutiger Änderung auf 80 weiterhin bei 99.
2. Aktueller Tag: Änderung `MAX_SOC 99→80` erzeugt ein neues Segment; Punkte vor Wechsel zeigen 99, danach 80.
3. Analog `MIN_SOC_PERCENT`.
4. Analog `NIGHT_DISCHARGE_STOP_SOC_PERCENT`.
5. Nachtstart `21:30→23:00`: historische Tage bleiben 21:30; aktueller Tag wird zeitbezogen segmentiert.
6. Analog Nachtende.
7. Tages-SOC-Punkte bleiben bei Overlaywechsel aus demselben Cache wiederverwendbar.
8. Kein zusätzlicher Tagesdaten-/SQLite-Punkte-Rebuild nur wegen Overlayänderung.
9. Backfill aus V4-Dateien erzeugt nur Hashwechsel, nicht jede Zeile.
10. Wiederholter Backfill ist idempotent und erzeugt keine Duplikate.
11. Abgebrochener Backfill kann sicher erneut gestartet werden.
12. Fehlender Snapshot → Segment „historische Konfiguration nicht verfügbar“, kein Current-Config-Fallback.
13. Manipulierter/fremder Snapshot-Hash wird nicht still akzeptiert.
14. Restart-required Wert wird nicht vor tatsächlicher Effective-Wirkung als historischer Overlaywechsel dargestellt.
15. Browser/UI: segmentierte Linie/Shading/Legende ist auf Desktop und Mobil verständlich.
16. Current-day Cache-Hit nach Configwechsel zeigt trotzdem das neue finale Segment, ohne frühere Tagessegmente umzuschreiben.

---

## 22. Vollständige Testmatrix V13.0.0

### 22.1 A – Basis-/Registryvertrag

- V12.13.0-Ausgangsbasis exakt verifiziert;
- Registry kann weiterhin eindeutig geladen werden;
- 212 eindeutige Registrykeys vor Featureänderung;
- Scope-Prädikat liefert auf unveränderter Registry 188 aktive verwaltete Settings;
- genau 1 Secret (`MQTT_PASSWORD`);
- migration/protected/read-only/reserved niemals im normalen State-Scope.

### 22.2 B – Bundleparser / Integrität

- gültiges Bundle roundtrip;
- Canonical-JSON-Hash reproduzierbar;
- einzelnes Byte/Wert geändert → Hashfail;
- invalid UTF-8;
- invalid JSON;
- Duplicate Key;
- Root kein Objekt;
- NaN/Infinity;
- >1 MiB;
- falsches Format;
- Formatversion zu neu;
- fehlende Pflichtfelder;
- ungültige Scopekeys;
- doppelter Scopekey;
- ungültige Secretmetadaten.

### 22.3 C – Scope / Snapshotintention

- `full_managed`;
- einzelne Kategorie;
- mehrere Kategorien;
- Expert-Einzelkeys;
- konkrete Keyliste bleibt im Bundle eingefroren;
- explizite Werte korrekt gespeichert;
- geerbte Werte nicht als explizit persistiert;
- `resolved_values` korrekt;
- Load entfernt Zieloverride für in Quelle geerbten Key;
- Load setzt Quelloverride für expliziten Key;
- Teil-Scope verändert keine Keys außerhalb Scope;
- Compoundfelder korrekt auf technische Keys;
- Dependency nicht still ergänzt;
- Whole-Candidate-Validation fängt resultierenden Konflikt;
- alle aktiven verwalteten Registrykeys besitzen eine Portabilitätsklasse;
- `portable_profile` enthält ausschließlich Registryklasse `portable_profile`;
- `site_specific`, `local_runtime`, `secret`, `non_transferable` werden sicher ausgeschlossen;
- manipuliertes Profil mit nicht-portablem Key blockiert;
- Profilimport auf anderem kompatiblen Registry-/Schema-Stand läuft durch denselben Migration-/Preview-/Diff-Vertrag.

### 22.4 D – Unknown-/Legacy-Semantik

- bestehender Unknown Target Key bleibt byte-/wertsemantisch erhalten;
- Imported Unknown in Bundle blockiert;
- Legacy-Unknown Expert blockiert;
- bestätigtes „Unknown überspringen“ verwirft nur Source-Unknown;
- Migration konsumiert bekannte alte Aliaskeys;
- Migration-only Key landet nicht im aktiven Scope.

### 22.5 E – Secrets

- lokaler State enthält nie Secretklartext;
- Standardexport enthält nie Secretklartext;
- Expert-Export ohne Option enthält nie Secret;
- Expert-Export mit Option enthält Secret und fordert Warnbestätigung;
- `portable_profile` enthält unabhängig vom Modus nie Secret;
- Secretimport default `keep`;
- explizites `replace`;
- explizites `clear`;
- `replace` ohne Wert blockiert;
- Secret nie im Diffklartext;
- Secret nie in Log/Event/Auditklartext;
- Secret-Bundle-Response `no-store`.

### 22.6 F – Kompatibilität / Migration

- gleiche Registry/hash direkt kompatibel;
- gleicher Configvertrag, andere Build-ID;
- Quell-App neuer + gleicher Confighash → Warnung/Confirmation;
- ältere bekannte Registry → Migration;
- Registry drift ohne Migrationspfad → blockiert;
- höheres Runtime-Schema ohne Pfad → blockiert;
- Migration idempotent;
- Measurement Marker 3 → 4 konsumiert;
- KWH→WH Legacyfall;
- SMA Alias→Cross-Charge Legacyfall;
- conflicting old/new aliases → fail closed;
- SERVICE_RESTART_COMMAND nicht wieder aktiv importiert;
- Default-Drift bei geerbtem Wert sichtbar.

### 22.7 G – Whole-Candidate-Validation

- Min >= Max blockiert;
- Nachtstart == Nachtende blockiert gemäß aktuellem Vertrag;
- Reservegrenzen;
- Source-/Grid-Abhängigkeiten;
- Cross-Field-Regeln;
- First-Install required keys;
- protected action blockiert;
- read-only/migration-only blockiert;
- server validation gewinnt gegen manipulierte Clientdaten.

### 22.8 H – Preview / Session / CAS

- TTL 300 s;
- Expired Preview;
- Session mismatch;
- Single-use Preview;
- Configrevision ändert sich vor Preview;
- Configrevision ändert sich nach Preview;
- State-Revision ändert sich nach Preview;
- Importtoken anderer Session;
- Importtoken abgelaufen;
- Sourcehash im Commit nicht austauschbar;
- Confirmation vollständig/unvollständig;
- kein Direct-Load ohne Preview.

### 22.9 I – Atomare Persistenz / Rollback

- normale Config 0600;
- atomischer Replace;
- Directory fsync;
- injectierter Fehler vor Replace → Altbytes unverändert;
- Post-Write-Verifikation fehlschlägt → Altbytes wiederhergestellt;
- Wiederherstellungsbytes exakt gleich vorheriger Datei;
- Rollbackfailure → kritischer Fehler/fail closed;
- Runtime `_set_valid_primary` erst nach erfolgreichem finalen Verify;
- First-Install-Fehlerpfad ohne Altdatei.

### 22.10 J – configured/effective/pending_restart

- nur Live-Keys;
- nur Restart-Keys;
- gemischter Import;
- pending_restart vorher false → true;
- pending restart key auf Effective zurückgesetzt → verschwindet;
- kein automatischer Dienstrestart;
- Settingsmodel aktualisiert nach Commit;
- invalid-primary Repair;
- First-Install Repair/Setup.

### 22.11 K – Last-Good / Recovery

- State create verändert Slots/Pointer nicht;
- State delete verändert Slots/Pointer nicht;
- Export/Import-inspect verändert Slots/Pointer nicht;
- Configcommit promotet nicht sofort;
- pending_restart blockiert Promotion;
- stabile Readyphase weiterhin 300 s;
- normaler späterer Promotionpfad funktioniert;
- State-Datei wird nie Startup-Recoverycandidate;
- defekter State-Store blockiert `/ready` nicht;
- Pointer-Reparatur unverändert separat.

### 22.12 L – UI Standard/Experte

Desktop 1440×900 und Mobil 390×844:

- Liste;
- Create;
- Kategorien-Scope;
- Expert Key-Scope;
- Rename;
- Delete confirmation;
- Bundleimport;
- Legacyimport nur Expert;
- Export;
- Secretwarnung;
- Mandatory Preview;
- Default-Drift;
- Migrationreport;
- Expertänderungen im Standarddiff sichtbar;
- Draft collision;
- Modal scrolling;
- kein horizontaler overflow;
- keine Browser-/Consolefehler.

### 22.13 M – Graphhistorie / Timeline / Cache-Regression

Alle Tests aus Abschnitt 21.10, insbesondere:

```text
historischer MAX-Wert bleibt historisch
aktueller MAX-Wechsel erzeugt Segment statt Rückwirkung
MIN/Reserve analog
Nachtstart/-ende historisch und intraday segmentiert
V4→Timeline-Backfill
Backfill idempotent/resumierbar
fehlender Snapshot ohne Current-Config-Fallback
historische points wiederverwendet
kein DB-Punkte-Rebuild durch Overlayänderung
UI segmentiert Linie/Legende/Fenster korrekt
```


### 22.14 N – Installer / Upgrade / Rollback

- V12.13.0 als direkter Ausgangsstand akzeptiert;
- `config.json` erhalten;
- Last-Good erhalten;
- `/opt/zendure-controller/config-states/` ausdrücklich erhalten;
- bestehende State-Dateien bei erneutem V13-Update nicht gelöscht;
- Backup des Installationsverzeichnisses umfasst vorhandenen State-Store;
- Installerrollback stellt vorherigen Installationsbaum inklusive vorhandener State-Dateien wieder her;
- Configmigration idempotent;
- Graph-Config-Timeline-Schema idempotent;
- einmaliger V4-Backfill wird kontrolliert ausgeführt;
- erneuter Backfill ist unschädlich/idempotent;
- Backfillfehler verändert historische V4-Dateien nicht und führt nicht zu Controller-/Ready-Fail;
- keine Node.js-Produktivvoraussetzung neu erzeugen.

### 22.15 O – No-Regression Regler/Safety/Measurement

- bestehende vollständige Testsuite;
- ResourceWarning=error;
- Command-/Cross-Charge-/Power-Observation geschützte Dateien nach Möglichkeit byteidentisch;
- `controller_logic.py` ausführbare Semantik unverändert, sofern nicht zwingend berührt;
- Single-Owner-Tests;
- V4-only statische Prüfung;
- Standardheader exakt 246;
- Extended exakt 249;
- `config_control_hash` bleibt Bestandteil V4;
- kein Measurement-V5 und keine Änderung der 246/249-Header durch Graph-Timeline.
- Headerhashes unverändert:

```text
STANDARD = 7842bfef39d47f93dc39689aa04da7658564af565e5051c24f90b32021d184a7
EXTENDED = 8f61d07e66428a6e8757333d35d5dd73dd3a0975ac9a16714b93dc9b86460e93
```

---

## 23. Release-/Exit-Gates für V13.0.0

Vor Freigabe mindestens:

### 23.1 Quell-/Syntaxgates

- neues V13-Source-Manifest vollständig PASS;
- ZIP-Test PASS;
- Python AST für alle Pythonfiles PASS;
- `python -m py_compile` PASS;
- JavaScript syntax check PASS;
- Shell `bash -n` PASS;
- JSON-Artefakte parsebar;
- erforderliche Dateimodi korrekt.

### 23.2 Tests

- vollständiger bestehender Testbestand + neue V13-Tests;
- `pytest --collect-only` dokumentiert;
- `pytest` vollständig PASS;
- Subtests vollständig PASS;
- `python -W error::ResourceWarning -m unittest ...` vollständig PASS;
- ResourceWarnings = 0.

### 23.3 Protected-Diff

Explizit dokumentieren:

- welche Regler-/Command-/Measurement-Dateien unverändert geblieben sind;
- Bytehash bzw. semantischer AST-Nachweis für geschützte Dateien, soweit passend;
- falls eine geschützte Datei aus zwingendem technischen Grund berührt wird: exakter Grund und Differentialtest.

### 23.4 Browser-/Integrationsgates

- Settings/Config-State UI Desktop/Mobile;
- echte APIintegration für Preview/Commit;
- State-Store Rechte;
- Bundle Roundtrip;
- Import-/Exportdownload;
- Graphroute echte Appintegration;
- Graphoverlay Cache-Hit-Regression.

### 23.5 Final-ZIP-Re-Extraction

Das finale V13.0.0-ZIP wird frisch entpackt. Paketbezogene Gates und Kern-Tests werden aus dieser Extraktion wiederholt.

### 23.6 Pflichtausgabe des Builds

Mindestens:

- vollständiger ZIP-Pfad/Dateiname;
- SHA256;
- Größe;
- ZIP-Root;
- Version/Build-ID;
- Source-Manifest;
- Test-/Collection-/Subtestzahlen;
- ResourceWarning-Ergebnis;
- Syntaxprüfungen;
- geänderte/neue/gelöschte Dateien;
- Protected-/No-Regression-Nachweise;
- Browser-/Integrationssmokes;
- Exit-Gate;
- bekannte Restpunkte;
- Installationsbefehle;
- Rollbackhinweis;
- Git-Commit-/Tag-Vorschlag.

---

## 24. Produktive Feldabnahme nach späterer Buildfreigabe und Installation

Build-PASS ist nicht Feld-PASS. Nach einer späteren Installation von V13.0.0 mindestens:

### 24.1 Identität / Basisgesundheit

```text
APP_VERSION = 13.0.0
APP_BUILD_ID = <finale Build-ID>
systemd active
/health OK
/ready entsprechend realem Runtimezustand
MEASUREMENT_SCHEMA_VERSION = 4
```

### 24.2 Konfigurationsstände

Sicherer Feldtest ohne Reglerumbau:

1. aktuellen Stand ohne Secrets speichern;
2. Stand auflisten und Integrität prüfen;
3. Export erstellen;
4. denselben Export importieren und Preview erzeugen – bei identischer Config idealerweise kein fachlicher Diff;
5. einen ungefährlichen UI-/Settingswert im bestätigten Scope ändern;
6. alten Stand laden → Preview muss exakten Diff zeigen;
7. erst nach bewusster Bestätigung committen;
8. `configured/effective/pending_restart` prüfen;
9. Last-Good-Pointer darf durch bloßes State-Handling nicht gewechselt haben.

Restart-required Feldtests nur an einem dafür geeigneten, sicheren Parameter und nur wenn für die Abnahme fachlich erforderlich.

### 24.3 Graphhistorie / Backfill

Mit vorhandenen Tages-/V4-Daten:

1. V13-Backfill aus vorhandenen Measurement-V4-Dateien und `zec_config_snapshots.json` ausführen;
2. Abdeckung und Timelineeinträge prüfen;
3. einen historischen Tag vor einer bekannten Configänderung laden → damalige Max-/Min-/Reserve-/Nachtwerte müssen erhalten bleiben;
4. aktuellen Graph laden und Tagescache aufbauen;
5. einen sicheren LIVE-Overlaywert ändern, bevorzugt MAX-SOC;
6. nächster Graphresponse darf `Cache hit` für die Tagespunkte haben, muss aber ein neues finales Configsegment zeigen;
7. frühere Punkte desselben Tages dürfen nicht rückwirkend den neuen Wert erhalten;
8. Statuskarte und **aktuelles** Graphsegment müssen übereinstimmen;
9. historischen Tag erneut laden → keine Rückwirkung der heutigen Änderung;
10. Backfill nochmals starten → keine Duplikate/semantische Änderung;
11. Wert anschließend nach Bedarf wieder auf Sollkonfiguration setzen.

Keine künstliche Measurementrotation nur für den separat offenen Manifest-Beobachtungspunkt.

---

## 25. Voraussichtlicher Implementierungszuschnitt

Noch **keine Codefreigabe**; dies ist nur der erwartete Zuschnitt zur Scopekontrolle.

Wahrscheinlich neu bzw. erweitert:

```text
config bundle/parser/integrity service        neu
config state store/service                    neu
settings_service.py                           shared preview extension
settings_runtime.py                           commit rollback hardening / safe persisted snapshot access
migration authority                          gemeinsame refactorisierte Engine
measurement_db.py                              Graph-Config-Timeline / Queries
tools/backfill_graph_config_timeline.py        einmaliger V4→Timeline-Backfill
web_ui.py                                     API + historische Graphsegmente + UI integration
static/settings_v2.js                         Config-State UI
static/settings_v2.css                        Layout
Handbuch/Hilfe                                neues Feature dokumentieren
tools/update_zendure_controller.sh            State-store preservation/upgrade tests
tests/...                                     neue V13-Matrix
version.py                                    erst beim tatsächlichen Build
```

Ohne zwingenden Grund **nicht** anzufassen:

```text
controller_logic.py
command_lifecycle.py
mqtt_bridge.py
cross_charge.py
zendure_power_observation.py
Measurement-V4 Headervertrag
```

Die konkrete Dateiliste wird erst beim Build aus der realen Implementierung abgeleitet und im Exit-Gate vollständig dokumentiert.

---

## 26. Abnahmekriterien / Freigabepunkt

Die Spezifikation ist zur Umsetzung freigegeben, wenn der Nutzer den gesamten V13.0.0-Block ausdrücklich bestätigt.

Mit dieser Makrofreigabe gilt dann:

- vollständige Umsetzung als ein Entwicklungsblock;
- keine unnötigen Mikrofreigaben innerhalb des bestätigten Scopes;
- Stopp und Rückfrage nur bei echtem Scopekonflikt, fehlender Primärquelle oder notwendiger Änderung eines ausdrücklich geschützten Regler-/Safety-Bereichs;
- keine produktive Installation durch den Build selbst.

Bis zu dieser ausdrücklichen Freigabe erfolgen **keine Codeänderungen und kein V13.0.0-Build**.

---

## 27. Konsolidierte Designentscheidungen zur Freigabe

Mit Freigabe dieser Spezifikation werden insbesondere folgende Punkte als bestätigt behandelt:

1. Zielrelease **V13.0.0**.
2. Ein gemeinsamer Config-Preview-/Commitpfad für UI-Draft, lokale Stände und Imports.
3. Scopeautorität = aktuelle Registry; aktuell 188 aktive editierbare LIVE/RESTART-Settings.
4. Snapshot bewahrt explizite Nutzerwerte und Scope; geerbte Defaults werden nicht unbemerkt dauerhaft gepinnt.
5. Default-Drift zwischen Versionen wird im Preview offengelegt.
6. Lokaler State-Store `/opt/zendure-controller/config-states/`, 0700/0600, entkoppelt vom Regel-/Readinesspfad.
7. Einheitliches `ZEC-CONFIG-BUNDLE` V1 mit SHA-256 über kanonisches Payload; Integrität, keine Authentizität.
8. Lokale Stände enthalten niemals Secretklartext.
9. Standardexport enthält niemals Secrets; optionaler Klartext-Secretexport nur Expert + ausdrückliche Warnbestätigung.
10. Import übernimmt Secrets standardmäßig nie; nur Expert opt-in über `replace/clear`, sonst `keep`.
11. Legacy-`config.json`-Import nur Expert und immer über Migration/Validation/Diff.
12. Imported Unknown Keys werden nicht neu persistiert; bestehende Unknown Target Keys bleiben erhalten.
13. Last-Good bleibt strikt getrennt und wird nicht durch Statehandling umgangen.
14. Shared Config-Commit wird um atomischen Rückrollversuch bei Post-Write-Verify-Fehler gehärtet.
15. Kein automatischer Dienstrestart nach Load/Import; bestehende `configured/effective/pending_restart`-Semantik bleibt maßgeblich.
16. Teilbare Regelprofile sind systemübergreifend transportabel, aber ausschließlich für Registrykeys der Klasse `portable_profile`; Zielsysteme verwenden immer Migration/Validation/Diff/CAS statt Blindübernahme.
17. SOC-Tagespunkte bleiben gecacht; SOC-/Nacht-Overlays werden als **historische Effective-Config-Segmente** dargestellt und niemals rückwirkend aus der heutigen Config überschrieben.
18. Der vorhandene V4-`config_control_hash` plus `zec_config_snapshots.json` ist Primärquelle für die Rekonstruktion des Altbestands.
19. V13.0.0 liefert einen einmaligen idempotenten externen V4→Graph-Timeline-Backfill; danach pflegt die Runtime die Timeline inkrementell weiter.
20. Fehlt historische Configevidenz, wird das Overlay als unbekannt markiert statt die aktuelle Config zu verwenden.
21. Keine Regler-, Command-, Single-Owner- oder Measurement-V4-Neuabstimmung; kein Measurement-V5.

**Status:** bereit zur Nutzerfreigabe; Implementierung noch nicht begonnen.
