# V13.0.2 – Targeted Protected-Core Diff

Basis: V13.0.1 (`v13.0.1-20260811`)
Ziel: V13.0.2 (`v13.0.2-20260812`)

Diese Datei dokumentiert die byteweise Prüfung ausdrücklich geschützter Produktionspfade.

| Datei | V13.0.1 SHA256 | V13.0.2 SHA256 | Ergebnis |
|---|---|---|---|
| `controller_logic.py` | `ef0ba82838154911b257644dd2f53d44497685c6f825244c863e2072b7a1853c` | `ef0ba82838154911b257644dd2f53d44497685c6f825244c863e2072b7a1853c` | **BYTEIDENTISCH** |
| `cross_charge.py` | `cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7` | `cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7` | **BYTEIDENTISCH** |
| `command_lifecycle.py` | `6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176` | `6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176` | **BYTEIDENTISCH** |
| `instance_owner.py` | `8cc37d63b002b5b299fcbe5c98b77aa62022dd577b740d780ea77193af5ebac1` | `8cc37d63b002b5b299fcbe5c98b77aa62022dd577b740d780ea77193af5ebac1` | **BYTEIDENTISCH** |
| `measurement_v4.py` | `3f17f532a252e04a5a0973ff8c41197709a0addaae85e61b8399350913f38563` | `3f17f532a252e04a5a0973ff8c41197709a0addaae85e61b8399350913f38563` | **BYTEIDENTISCH** |
| `measurement_v4_contract.py` | `f5314e291616d6db55212baa722ff299aefc41d8aaae0c0fffd2b064befdb1ed` | `f5314e291616d6db55212baa722ff299aefc41d8aaae0c0fffd2b064befdb1ed` | **BYTEIDENTISCH** |
| `measurement.py` | `8f82bbdc07f9e9d5d1a98028260275cbb3564609d3889d96ec0272d10852dcbd` | `8f82bbdc07f9e9d5d1a98028260275cbb3564609d3889d96ec0272d10852dcbd` | **BYTEIDENTISCH** |
| `csv_logger.py` | `b2272829d2aa89883c630faa897c524287070123fad42e0cf51c21b133d1b5a1` | `b2272829d2aa89883c630faa897c524287070123fad42e0cf51c21b133d1b5a1` | **BYTEIDENTISCH** |
| `mqtt_bridge.py` | `ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791` | `ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791` | **BYTEIDENTISCH** |
| `zendure_power_observation.py` | `ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a` | `ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a` | **BYTEIDENTISCH** |
| `settings_runtime.py` | `7710a872c7b74e8020ef7514c083239010233a2f92cf51f539f8c1b3290ea22c` | `7710a872c7b74e8020ef7514c083239010233a2f92cf51f539f8c1b3290ea22c` | **BYTEIDENTISCH** |
| `settings_apply_policy.py` | `1335075e0e0518a1e2c830d93615880e10ac91e8bae0f308ec04a93b6be7e77a` | `1335075e0e0518a1e2c830d93615880e10ac91e8bae0f308ec04a93b6be7e77a` | **BYTEIDENTISCH** |

## Ergebnis

- Geschützte Kernpfade geprüft: **12/12**.
- Ergebnis: **alle byteidentisch**.
- Damit wurden AUTO-/Harvest-Rechenlogik, Cross-Charge, NIGHT/Command-Lifecycle, Single-Owner, Measurement-V4-Vertrag und der Last-Good-Runtimekern in diesen Pfaden durch V13.0.2 nicht verändert.
- Absichtlich geändert wurden ausschließlich die freigegebenen V13.0.2-Hotfixpfade (SQLite-Writer/Backfill-Koordination, Config-State/Import/CSRF/UI, Graphlegende, Benutzertexte, Version/Installer und Tests/Dokumentation).
