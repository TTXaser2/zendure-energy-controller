# Technical Notes – V12.11.2-RC20

**Build-ID:** `rc20-audit-fix6-20260806`

## 1. Schemaautorität und Parsing

`settings_registry.py` enthält immutable `SettingSpec`s. Runtime-JSON ist kein unabhängiges Schema. Codecs sind key-spezifisch und lehnen mehrdeutige Typkonvertierungen, Clamp, Min/Max-Tausch und Default-Ersatz für invalide vorhandene Werte ab. Issues sind strukturiert und enthalten keine Secretwerte.

## 2. Configzustände

```text
configured = exakte Nutzer-/Primärquelle, einschließlich sichtbar invalider Werte
effective  = tatsächlich laufender, vollständig validierter Snapshot
pending    = restartpflichtige Differenz zwischen configured und effective
```

Bei einer später invaliden Datei bleibt `effective_source=last_valid_runtime`. Bei Startup-Recovery bleibt die invalide Primärconfig als `configured` sichtbar; Last-Good ist ausschließlich `effective`.

## 3. Vollständiger Ready-Nachweis

`ControllerState.readiness_snapshot()` liefert einen kleinen, bounded Snapshot ohne Graph-/Eventkopien und ohne I/O. `build_ready_payload()` prüft:

- MQTT-Verbindung;
- frische und valide Netzleistung;
- frischen und validen Zendure-SOC;
- bei aktivem Cross-Charge frische unabhängige Zweitbatteriedaten;
- verfügbaren, frischen und validen Commandpfad;
- vollständigen Command-State;
- frischen `smartMode=1`-Readback;
- gültigen `acMode` mit neutralisiertem Gegenlimit;
- Übereinstimmung von Desired und Readback, sobald ein Desired-State existiert;
- keine offene Uncertain-, Not-Effective-, Resync-/Verifying- oder Late-Guard-Episode;
- valide unabhängige Zendure-Leistungstelemetrie;
- keinen SAFE_STATE und keinen Controllerfehler.

Derselbe Nachweis steuert `/ready`, Startup-Recovery und die 300-s-Stable-Ready-Promotion.

## 4. Asynchrone Last-Good-Promotion

Der Controlleraufruf plant höchstens einen Worker `zec-last-good-promotion`. Config-, Manifest- und Pointer-Schreibvorgänge samt `fsync` laufen ausschließlich dort. Ein geänderter Safety-Proof oder ein fehlendes Gate setzt den Stable-Ready-Timer zurück. Promotion ist bei pending-restart, invalider Primärconfig, Recoverybetrieb oder nicht primärer Effective-Quelle ausgeschlossen.

## 5. Last-Good-Dateisicherheit

Pointer, Slot-Config und Slot-Manifest werden vor der Inhaltsvalidierung mit `lstat` geprüft:

```text
Dateityp: reguläre Datei
Modus:    exakt 0600
Owner:    pi:pi
```

Symlinks, abweichende Rechte oder Eigentümer machen den Slot blockierend ungültig.

## 6. Storage-Inventar

`StorageInventory` hält einen thread-sicheren Snapshot. `GET /storage/status` und der Legacyadapter kopieren nur diesen Snapshot. Startup-Worker und CSRF-/Origin-geschütztes `POST /storage/inventory-refresh` aktualisieren Single-Flight. Ein persistenter Cache übernimmt unveränderte Dateien über Größe und `mtime_ns`; das Measurement-Manifest liefert bekannte Zeilen- und Zeitgrenzen. Nur neue, geänderte oder unbekannte Dateien werden eingelesen.

## 7. Adminaktionen

Pointer-Repair bindet das One-Time-Token an Session, Store-Revision, Zielslot, Generation, Typed-Revision, Config-Hash und Manifest-Hash. Commit erfordert `REPAIR_POINTER`, besitzt 60-s-Cooldown und Single-Flight.

Dienstneustart erfordert `RESTART_SERVICE`. Die UI pollt `/ready` höchstens 90 s und akzeptiert Erfolg nur bei:

```text
ready = true
version = 12.11.2-rc20
build_id = rc20-audit-fix6-20260806
```

Beide Aktionen erzeugen Auditereignisse.

## 8. Installertransaktion

Vor Produktivänderungen erfolgen Source-Manifest-, Python-, Shell-, Unit-Test- und Config-Migrationspreflight. Die JavaScript-Syntax ist ein Build-Gate; bei vorhandenem Node.js wird sie auf dem Pi zusätzlich geprüft, ohne daraus eine Produktivabhängigkeit zu machen. Vorprüfungsfehler verlassen den Installer ohne Dienststopp. Prüf-Subshells deaktivieren den ERR-Trap explizit; zusätzlich unterdrückt ein `BASH_SUBSHELL`-Gate jede verschachtelte Handlerausführung. Der Rollback-Handler läuft dadurch ausschließlich einmal im Hauptprozess. Nach dem vollständigen `/opt`-Backup sichert der Installer zusätzlich den exakten Zustand von:

```text
/usr/local/sbin/zendure-controller-restart
/etc/sudoers.d/zendure-controller
```

Der Rollback stellt vorhandene Dateien byte-, mode- und ownergetreu wieder her oder entfernt sie, wenn sie vorher nicht existierten.

## 9. S1.7-Legacyentscheidung

Zwölf Keys sind explizit klassifiziert: zwei konfliktfreie Transformationen, sechs Entfernungen ohne Runtimewirkung und vier bewusste Runtime-Kompatibilitätskeys bis S2. Die Migration materialisiert keine Defaults, verändert keine Unknown Keys und ist idempotent.


## Installer-Hotfix Fix 4 (06.08.2026)

- Der Restart-Route-Test ist hostunabhängig und modelliert den fehlenden Helper explizit.
- Installer-Selbsttests setzen `ZEC_INSTALLER_PREFLIGHT=1`; echte Restart-Subprozesse sind damit technisch gesperrt.
- `ResourceWarning` wird im Preflight als Fehler behandelt.
- Laufzeitdaten unter `logs/` und SQLite-Artefakte sind vom Releasepaket ausgeschlossen.
- Event-Journal-Dateien der Installer-Selbsttests werden ausschließlich unter `/tmp/zec-installer-preflight-<PID>/` angelegt.

## Runtime-Hotfix Fix 5 (06.08.2026)

Der vorherige Build las in `ControllerState.readiness_snapshot()` einmal `self.second_battery_valid`; deklariert und in allen produktiven Aktualisierungspfaden verwendet wird jedoch `self.second_battery_data_valid`. Dadurch war der Prozess lebendig, aber `/ready` warf `AttributeError` und der Installer rollte nach 90 Sekunden korrekt auf RC19 zurück. Fix 5 verwendet das kanonische Feld und ergänzt einen statischen sowie einen dynamischen Startpfadvertrag.


## UI-, Ereignis- und SOC-Recovery Fix 6 (06.08.2026)

- Status, Graph und Settings verwenden dieselbe globale Topbar und eine live aktualisierte Statusampel neben „Status“.
- Erwartete `MIN_SOC`-/`MAX_SOC`-Grenzen führen zu neutralem `HOLD` statt zu einem Fehler-`SAFE_STATE`; fehlende/stale Pflichtdaten bleiben fail-closed.
- Verwaiste offene MQTT-/Zendure-Telemetrieereignisse werden bei stabil gesundem Livezustand vollständig auf `resolved` gesetzt, ohne die Historie zu löschen.
- Settings nutzt die verfügbare Breite, ordnet Label/Hilfe/Input/Metadaten vertikal zu, verwendet zwölf fachliche Icons und erlaubt nach Preview-Abbruch eine erneute Prüfung.
- Das Storage-Inventar verwendet einen persistenten inkrementellen Cache und scannt nur neue oder geänderte Dateien.
- Unterstützte Installerquellen sind RC19 oder exakt RC20 Fix 5; Ziel ist `rc20-audit-fix6-20260806`.
