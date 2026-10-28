# V18.0.0 – Sourcebasierter Update- und Feldtool-Kandidat CP28

**Stand:** 27.10.2026 · **Status:** `DEVELOPMENT_NOT_INSTALLABLE / RELEASE_HOLD / NO_PI_MUTATION`

Die reale Produktivversion ist **V17.1.3**. Das neue Entwicklungsthema Battery Care soll nach `01` §5 mit **V18.0.0** gebündelt werden. Die Kandidatenbuild-ID `v18.0.0-20261027` ist *nicht* final festgeschrieben.

## Vorbereiteter Upgradevertrag

| Feld | Vorgesehener Wert | Verifikation |
| --- | --- | --- |
| Ausgangsversion | `17.1.3` | exakter Product-Version-/Buildabgleich vor Dienststopp |
| Ausgangsbuild | `v17.1.3-20261022` | nicht V17.1.2 und nicht beliebige vorhandene Installation |
| Zielversion | `18.0.0` | noch nicht als Runtime/Release gebaut |
| Vorgesehenes Zielbuild | `v18.0.0-20261027` | provisorisch, beim Freeze neu abstimmen |
| Archivroot/-name | `zendure_controller_v18_0_0` | künftiger finaler ZIP-Vertrag |
| Manifest | `V18_0_0_SOURCE_MANIFEST.sha256` | fehlt absichtlich, Releasegate FAIL |
| Build-Evidence | `validation/V18_0_0_BUILD_EVIDENCE.json` | fehlt absichtlich, Releasegate FAIL |

`tools/install_zendure_controller_v18_candidate.sh` erbt den bewährten Preflight-Backup/Update/Rollback-/Supportbundle-Vertrag; alle V18-Schlüssel für Manifest/Build/Backup-/Updatequelle sind angepasst. **Die erste wirksame Anweisung nach dem Shell-Sicherheitsmodus ist ein unbedingter Exit 78**. Es existiert weder ein Aktivierungsflag noch ein gültiger Installationspfad. Dieser Kandidat darf nicht kopiert oder manuell entsperrt und auf einem Pi benutzt werden. Der reale kanonische Installer ist weiterhin V17.1.3.

`tools/v18_field_acceptance.py` enthält einen eigenen unbedingten Abnahmeblocker `v18_release_candidate_hold` für alle Phasen; im normalen Betrieb außerdem den ausdrücklich als `FAIL` ausgewiesenen Nachweisbedarf `battery_care_physical_effect`. Das Fieldtool versendet **keine** Steuerbefehle und ersetzt keine reale unabhängige Messung der Batterie-/Netzwirkung. Es ist ein **Entwicklungsartefakt**, keine Anleitung, es auf dem Pi aufzurufen.

## Release-Freeze-Aufgaben (unverändert obligatorisch)

- Finalen Buildzeitpunkt und V18-Runtimeidentität festlegen; neuen Installer erst **atomar** mit Runtime, Manifest, maschinenlesbarer Build-Evidence, technischen Datenblättern DOCX/PDF, Release-Dokumentation und vollständigem Code-/Installer-Testset zur Freigabe führen.
- `tools/verify_release_identity_readiness.py` muss danach **PASS** melden (allein noch kein Installationsgate), ebenso die echten Deployment-, Fresh-extract-, Clean-Fresh-, Rollback-, UI- und manuellen 22-UML-Gates. `BATTERY_CARE_ENABLED` bleibt ab Werk `false`.
- Die V18-Feldabnahme um eine gesonderte quellenfeste Batterie-Wirkungs- und Recovery-Evidenz erweitern; die beiden CP28-Blocker erst bei belegter Auflösung entfernen.
- Realen Raspberry Pi ausschließlich nach gesonderter Nutzerfreigabe und mit wiederaufnehmbarem Termius/iPhone-SSH- und Rollback-Konzept anfassen. Keine imaginären SSH-Daten, URLs oder Hardware-PASS behaupten.

Dieser CP28-Block ändert **keinen** Controller-/Command-/Safety-Algorithmus. Das Master-Ledger bleibt `05_ZEC_BACKLOG_AND_ROADMAP.md`; keine historische Quelle entfernt.
