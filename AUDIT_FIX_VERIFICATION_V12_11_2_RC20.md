# Audit-Fix-Verifikation – Zendure Energy Controller V12.11.2-RC20

**Build-ID:** `rc20-audit-fix5-20260806`
**Ausgangspaket:** auditierter, nicht freigegebener RC20-Stand mit SHA256 `f401207efef3116aee558f709e0beffcc1880eddb91da513cc8f02c1b3bb785b`
**Dokumentierter Ursprung des Settings-Releases:** V12.11.2-RC19 plus S1.0 und S1.1; direkt gepatcht wurde das auditidentische übergebene RC20-Paket

## 1. Ergebnis

Alle 13 Befunde aus `AUDIT_ZEC_V12_11_2_RC20_CHAT_GEGEN_RELEASE_V1.0.md` wurden im Quellstand geschlossen und durch neue Negativ-, Integrations- oder Fault-Injection-Proben abgesichert.

| Befund | Status | Korrektur / Nachweis |
|---|---|---|
| RC20-AUD-001 | geschlossen | `/ready`, Startup-Recovery und Stable-Ready verwenden denselben bounded Vollnachweis aus Messdaten-, Command-, Readback-, Guard-, Lifecycle- und unabhängiger Leistungstelemetrie. Jede einzeln fehlende Command-Bedingung hält Recovery in `WAITING` und verhindert Promotion. |
| RC20-AUD-002 | geschlossen | Last-Good-Promotion läuft asynchron, daemonisiert und Single-Flight im Worker `zec-last-good-promotion`; der Regelzyklus wartet nicht auf Datei-I/O oder `fsync`. |
| RC20-AUD-003 | geschlossen | Bei invalider Primärconfig bleibt der exakte invalide Wert `configured`; `effective` stammt separat aus Last-Good. |
| RC20-AUD-004 | geschlossen | Pointer, Slot-Config und Slot-Manifest werden per `lstat` auf reguläre Datei, exakt `0600` und den erwarteten Owner/Group `pi:pi` geprüft. Symlink, falscher Owner oder `0644` blockieren den Slot. |
| RC20-AUD-005 | geschlossen | `GET /storage/status` kopiert nur einen In-Memory-Snapshot. `POST /storage/inventory-refresh` startet einen asynchronen Single-Flight-Scan. Der Legacy-Endpunkt `/measurements/availability` ist Snapshotadapter und führt keinen Vollscan im Request aus. |
| RC20-AUD-006 | geschlossen | Restart-Helper und sudoers-Fragment werden vor Veränderung samt Existenzzustand, Bytes, Rechten und Owner gesichert und bei jedem Installationsfehler exakt wiederhergestellt oder entfernt. |
| RC20-AUD-007 | geschlossen | Runtime-invalid arbeitet weiterhin mit dem letzten gültigen Snapshot und meldet jetzt `effective_source=last_valid_runtime`. |
| RC20-AUD-008 | geschlossen | Pointer-Repair besitzt UI-Aktion, explizite Bestätigung, One-Time-Token, Sessionbindung, vollständige CAS-Bindung an Store-/Slot-/Generation-/Typed-/Config-/Manifest-Revision, 60-s-Cooldown, Single-Flight und Auditereignis. |
| RC20-AUD-009 | geschlossen | Dienstneustart benötigt die Bestätigung `RESTART_SERVICE`; die UI meldet Erfolg erst nach `ready=true`, erwarteter Version und erwarteter Build-ID. Adminaktion wird auditiert. |
| RC20-AUD-010 | geschlossen | S1.7 besitzt eine explizite, idempotente 12-Key-Migrationsmatrix: zwei Transformationen, sechs Entfernungen ohne Runtimewirkung und vier bewusst bis S2 erhaltene Runtime-Kompatibilitätskeys. Unknown Keys und Secrets bleiben erhalten. |
| RC20-AUD-011 | geschlossen | Desktop-Suche als rechter Drawer, mobiles Vollbild-Suchpanel, mobile aufklappbare Kategorien, Status-/Versions-/Configquelle und Handbuchzugang im Header. |
| RC20-AUD-012 | geschlossen | Das versteckte Produktions-Template `legacy-settings-contract` wurde entfernt; Alt-UI-Tests prüfen jetzt das reale dynamische Settings-Modell. |
| RC20-AUD-013 | geschlossen | Build-, Release-, Technik-, Installations- und Übergabedokumentation beschreibt den tatsächlich erreichten Stand und die weiterhin erforderliche Produktivabnahme ohne Überzeichnung. |

## 2. Neue Audit-Gegenproben

`tests/test_v12_11_2_rc20_audit_fixes.py` und `tests/test_installer_root_artifact_transaction.sh` prüfen insbesondere:

- jedes einzelne Command-/Readback-/Guard-Gate gegen `/ready`, Recovery und Promotion;
- nicht blockierende Single-Flight-Promotion im dedizierten Worker;
- exakte configured/effective-Trennung bei Startup-Recovery;
- `0644`, falschen Owner und Symlink als blockierende Last-Good-Fehler;
- O(1)-Snapshotzugriff und Single-Flight-Refresh;
- vollständige Pointer-Repair-Bindung und Bestätigungszwang;
- Restart-Vertrag mit Version plus Build-ID;
- exakten Root-Artefakt-Rollback;
- idempotente S1.7-Migrationsmatrix;
- reale Desktop-/Mobil-Informationsarchitektur ohne Testleiche.

## 3. Nicht veränderte Produktivlogik

Die energetischen Zielwert- und Regelzweige für AUTO, NIGHT, Harvest, Cross-Charge, feste Modi, Command-Publishing, MQTT und Measurement wurden nicht fachlich verändert. `controller_logic.py` enthält ausschließlich die Integration des vollständigen Ready-Nachweises und der asynchronen Settings-Runtime-Beobachtung.

## 4. Installer-Hotfix nach erster Feldprobe

Die erste produktive Vorprüfung deckte eine unzulässige Node.js-Pflicht und einen durch `set -E` doppelt ausgelösten ERR-Handler auf. Der Hotfix entfernt Node.js als Installationsvoraussetzung, bindet stattdessen die Source-Manifest-Prüfung ein und trennt Vorprüfungsfehler strikt von der Produktivtransaktion. Drei Regressionstests sichern diese Verträge.

## 5. Restabnahme nach Installation

Buildseitig bestehen keine offenen Blocker. Auf dem produktiven Raspberry Pi bleiben die üblichen kontrollierten Abnahmen erforderlich:

1. Paket-SHA256 vor Installation prüfen;
2. exakten RC19→RC20-Lauf durchführen;
3. `/ready` auf Version, Build-ID und `ready=true` prüfen;
4. Settings-Seite Desktop/Mobil prüfen;
5. ungefährlichen Live-Key und restartpflichtigen Key prüfen;
6. Secrets, Unknown Keys und Migrationsergebnis kontrollieren;
7. Last-Good-Promotion nach 300 s unverändertem Stable-Ready prüfen;
8. Regelverhalten und Zendure-Kommandofrequenz gegen RC19 beobachten.
