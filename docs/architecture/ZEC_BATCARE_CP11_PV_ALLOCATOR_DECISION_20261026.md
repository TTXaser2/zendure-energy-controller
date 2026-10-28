# ZEC-BL-BATCARE-001 · Engineering CP11 – PV-Absolute-Arbitration

Status: **DEVELOPMENT_NOT_INSTALLABLE**, 26.10.2026. Ausgangsbasis: unabhängig rücklesegeprüfter Battery-Care-CP10, nicht produktive V17.1.3-Installation.

## Implementiert

- `battery_care_pv_allocation.py`: side-effect-free Stage-1-Arbiter mit signierten unabhängigen AC-Leistungen (`G>0` Import, `Pp/Pz>0` Ladung), `T=max(0,Pp+Pz-G)` und ABSOLUTEM Gesamtziel; normaler AUTO-Baseline-Zielwert wird nicht erneut auf `T` addiert.
- Attack nur nach zwei aufeinanderfolgenden frischen, **vollständig unterschiedlichen** Quellbeobachtungen mit monotonic elapsed und maximalem Beobachtungsgap; feste isolierte Zusatzrampe. Unfrische, mehrdeutige, negative Primär-/Zendure-Richtung, defekter Command-State → kein zusätzlicher Care-PV-Anteil.
- Deutlicher unerwünschter Import >100 W → Care-PV-Anteil sofort 0 W, erneuter Attack erst nach neuer nicht importierender Energiebilanz; normale Baseline bleibt unverändert. Bereits aktiver Fast-Overlay und Care dürfen später **nicht** addiert werden.
- Tests prüfen 900→0-W-Primärladung und →900-W-Zendure-Ladung, Import trotz rechnerisch unveränderter Bilanz, primäres Netzladen 600/600 W, Freshness/Replays, primäre Entladung und separate Baseline.

## Noch nicht implementiert / weder als PASS noch als wirksam behaupten

- Keine Verbindung mit `controller_logic.py::run_once/handle_charge`; noch keine neuen Gerätekommandos, keine physische Gerätewirksamkeit oder Import-Backoff-Feldevidenz.
- Live-Dispatch einschließlich Deadband und `low_surplus`, Cross-Charge-/Fast-Capture-Isolation, Care-Exit ohne Baseline-Leak, sowie eindeutige Istleistungs-/Freshness-Zuordnung und spätere Stufen 2/3 müssen gesondert geprüft werden.
- Die Felder `PvAllocation.physical_effect_proven=False` kennzeichnen ausdrücklich, dass Softwareziele keinen physischen Nachweis darstellen.

Dieser Architektur-Nachtrag ist additive Entwicklungsevidenz, nicht ein neuer Roadmapautoritätsstand; das Master-Ledger `05` und seine historischen IDs bleiben vollständig erhalten.
