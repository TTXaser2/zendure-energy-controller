# CP34 – V18-Staging-Datenblattbindung (technischer Entwicklungsvertrag)

**Status: DEVELOPMENT_NOT_INSTALLABLE · RELEASE_HOLD · Stand 27.10.2026.**

Quellautorität: vollständiges CP33-ZIP (SHA256 `9ff49012643ffb1683aa0915e5f8ca057cf025283fa04050f612f24ecd5b011b`). Der CP33-Datenblattentwurf ist in `docs/releases/v18.0.0/` als DOCX, PDF und unveränderte JSON-Provenienz vorhanden; **nicht** im veröffentlichten kanonischen Produktdatenblattpfad `docs/ZEC_Technisches_Datenblatt.*`.

`tools/prepare_v18_staging_tree.py` validiert die ursprünglichen CP33-Datenblattdokumente und 14 Source-/drei Vorgänger-Datenblatt-SHA256 vor der Staging-Erzeugung. Im separaten Stagingbaum bleibt der ursprüngliche Provenienzdatensatz erhalten. `validation/V18_0_0_STAGING_DATASHEET_BINDING.json` notiert ausschließlich die beiden zulässigen Identitätsänderungen `version.py` und `tools/install_zendure_controller.sh`, je mit CP33-Original- und V18-Staging-SHA256. Die übrigen 12 Ursprungsquellhashes sowie DOCX, PDF, drei Vorgängerartefakte bleiben unverändert. Der Stagingprüfer verweigert die Gültigkeit bei jedem unerwarteten Unterschied. Das Staging-Source-Manifest umfasst auch diese neue Bindungsdatei.

**Unveränderte harte Sperren:** Standardinstaller `exit 78` vor produktiver Aktion und ohne Ausführungsbit; `V18_0_0_BUILD_EVIDENCE.json` mit `status=BLOCKED`, beide Finalbaum-Regressionen `NOT_RUN_ON_FINAL_TREE`; Release-Identitätsprüfung `FAIL`; reale PV-/Netzpflege-/Notlade-Wirksamkeit `NOT_VERIFIED`; manuelle UML-Review `PENDING`.

Der Staging-Integritäts-PASS beweist ausschließlich **Byteidentität, Source-Provenienz und wirksame Nichtinstallierbarkeit**. Er ist kein Test von Backup, Systemd, MQTT, Hardware, Rollback, Installer oder Release-Freigabe. Finale Version/Freigabe nur nach den unabhängigen Gates in `06` und `05`.
