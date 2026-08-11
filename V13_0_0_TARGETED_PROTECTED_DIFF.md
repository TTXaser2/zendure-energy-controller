# V13.0.0 – Targeted Protected Diff / No-Regression-Nachweis

Vergleichsbasis ist das unveränderte, erneut aus dem verifizierten Quell-ZIP extrahierte V12.13.0 mit SHA256:

`e204aa270c517d2e9b1abfc8816075ca75c3194c7b0cf39f1b5b186f7c07213f`

## Byteidentische geschützte Kernmodule

Die folgenden Dateien sind zwischen V12.13.0 und V13.0.0 byteidentisch:

```text
controller_logic.py             ef0ba82838154911b257644dd2f53d44497685c6f825244c863e2072b7a1853c
cross_charge.py                 cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7
command_lifecycle.py            6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176
instance_owner.py               8cc37d63b002b5b299fcbe5c98b77aa62022dd577b740d780ea77193af5ebac1
measurement_v4.py               3f17f532a252e04a5a0973ff8c41197709a0addaae85e61b8399350913f38563
measurement_v4_contract.py      f5314e291616d6db55212baa722ff299aefc41d8aaae0c0fffd2b064befdb1ed
csv_logger.py                   b2272829d2aa89883c630faa897c524287070123fad42e0cf51c21b133d1b5a1
state.py                        5d3eb4a5e34da7018bf8dc069d7dca99bde8a2bb5fef328ffe13fdc5e1d1572a
mqtt_bridge.py                  ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791
zendure_power_observation.py    ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a
```

Damit werden insbesondere AUTO/Harvest/Cross-Charge/NIGHT/Command-Lifecycle/Single-Owner und der V4-CSV-Writer/-Contract nicht durch eine Implementierungsänderung in diesen Kernmodulen berührt.

## Measurement-V4-Contract

```text
Standard fields: 246
Standard header SHA256: 7842bfef39d47f93dc39689aa04da7658564af565e5051c24f90b32021d184a7

Extended fields: 249
Extended header SHA256: 8f61d07e66428a6e8757333d35d5dd73dd3a0975ac9a16714b93dc9b86460e93
```

Die Werte sind identisch zu V12.13.0.

## Gezielte notwendige Änderungen

`measurement_db.py` ist bewusst nicht byteidentisch, weil V13 die bereits vorhandene `config_control_hash`-Information asynchron in die neue Graph-Config-Timeline überführt. Dies ändert weder die V4-Zeile noch Header, Feldzahl oder Writer-Contract.

`web_ui.py` und `static/status_v2.js` ändern ausschließlich die Graph-Payload-/Darstellungslogik für die zeitbezogenen historischen Overlays sowie die neuen Settings-/Import-/Export-Routen. Die Reglerzielwertbildung bleibt davon getrennt.
