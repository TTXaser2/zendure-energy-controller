# V13.0.3 – Targeted Protected Differential

Vergleich gegen die verifizierte V13.0.2-Quellbasis. Alle unten aufgeführten Dateien sind SHA256-identisch.

| Datei | V13.0.2 SHA256 | V13.0.3 SHA256 | Ergebnis |
|---|---|---|---|
| `controller_logic.py` | `ef0ba82838154911b257644dd2f53d44497685c6f825244c863e2072b7a1853c` | `ef0ba82838154911b257644dd2f53d44497685c6f825244c863e2072b7a1853c` | PASS – byteidentisch |
| `cross_charge.py` | `cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7` | `cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7` | PASS – byteidentisch |
| `command_lifecycle.py` | `6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176` | `6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176` | PASS – byteidentisch |
| `instance_owner.py` | `8cc37d63b002b5b299fcbe5c98b77aa62022dd577b740d780ea77193af5ebac1` | `8cc37d63b002b5b299fcbe5c98b77aa62022dd577b740d780ea77193af5ebac1` | PASS – byteidentisch |
| `measurement_v4.py` | `3f17f532a252e04a5a0973ff8c41197709a0addaae85e61b8399350913f38563` | `3f17f532a252e04a5a0973ff8c41197709a0addaae85e61b8399350913f38563` | PASS – byteidentisch |
| `measurement_v4_contract.py` | `f5314e291616d6db55212baa722ff299aefc41d8aaae0c0fffd2b064befdb1ed` | `f5314e291616d6db55212baa722ff299aefc41d8aaae0c0fffd2b064befdb1ed` | PASS – byteidentisch |
| `measurement.py` | `8f82bbdc07f9e9d5d1a98028260275cbb3564609d3889d96ec0272d10852dcbd` | `8f82bbdc07f9e9d5d1a98028260275cbb3564609d3889d96ec0272d10852dcbd` | PASS – byteidentisch |
| `csv_logger.py` | `b2272829d2aa89883c630faa897c524287070123fad42e0cf51c21b133d1b5a1` | `b2272829d2aa89883c630faa897c524287070123fad42e0cf51c21b133d1b5a1` | PASS – byteidentisch |
| `mqtt_bridge.py` | `ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791` | `ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791` | PASS – byteidentisch |
| `zendure_power_observation.py` | `ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a` | `ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a` | PASS – byteidentisch |
| `measurement_db.py` | `265dba3ce4a2d3ca53c7d82fbd22679168cdc3ec9413a4006b80c104faf33a9d` | `265dba3ce4a2d3ca53c7d82fbd22679168cdc3ec9413a4006b80c104faf33a9d` | PASS – byteidentisch |
| `measurement_db_maintenance.py` | `b8046138115a4205b80f24f17b49fbfeaea01031366cccedc9998bd615b3764a` | `b8046138115a4205b80f24f17b49fbfeaea01031366cccedc9998bd615b3764a` | PASS – byteidentisch |
| `graph_config_timeline.py` | `10778412120e5c2712ab3a20a3ce082b8c96c59968298251734d779d2653d9ba` | `10778412120e5c2712ab3a20a3ce082b8c96c59968298251734d779d2653d9ba` | PASS – byteidentisch |
| `tools/backfill_graph_config_timeline.py` | `81ab6196fc688cf542c5ffcbb768e2140d7f48430829f75a510d93122e75ba8c` | `81ab6196fc688cf542c5ffcbb768e2140d7f48430829f75a510d93122e75ba8c` | PASS – byteidentisch |
| `config_manager.py` | `0b8b61530c9eefa58347825e9fdb99ef75da2f2cc0769983855e7fef3fc11b68` | `0b8b61530c9eefa58347825e9fdb99ef75da2f2cc0769983855e7fef3fc11b68` | PASS – byteidentisch |
| `settings_runtime.py` | `7710a872c7b74e8020ef7514c083239010233a2f92cf51f539f8c1b3290ea22c` | `7710a872c7b74e8020ef7514c083239010233a2f92cf51f539f8c1b3290ea22c` | PASS – byteidentisch |
| `settings_model.py` | `068dc93d64c6dfd53468cf7139ffe47ddfb72796ed0a8360b245409cd7f0c350` | `068dc93d64c6dfd53468cf7139ffe47ddfb72796ed0a8360b245409cd7f0c350` | PASS – byteidentisch |
| `web_ui.py` | `dbec6763521a6f1801850860dcaa89bb41762ee718fff8982815a19f5842ed1f` | `dbec6763521a6f1801850860dcaa89bb41762ee718fff8982815a19f5842ed1f` | PASS – byteidentisch |

Damit bleiben Regleralgorithmus, Cross-Charge, Command Lifecycle, Instance Ownership, Measurement V4, SQLite-/Backfill- und Last-Good-/Recovery-Verträge außerhalb des V13.0.3-Hotfixes unverändert.
