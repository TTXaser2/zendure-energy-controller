# UML Source-Traceability – V17.1.3 source-reviewed

Der 22-Blatt-Review ist in [SOURCE_REVIEW_V17_1_3.md](SOURCE_REVIEW_V17_1_3.md) dokumentiert. SHA256 bezieht sich auf exakt die vorhandenen DOT-/SVG-Bytes.

| ID | DOT SHA256 | SVG SHA256 | Source-Consumer |
|---|---|---|---|
| 01 | `d7acd1294af4c5a41c4db410efbef6b31de4ed03831b5df136ea211710b46bee` | `5682e896acee5f440aced254239e06e6d72c3ce674d2a3fcc8e2d19514ce6cc0` | `controller_logic.py::run_once`, `state.py::ControllerState` |
| 02 | `846f845eac43427ba950b5253ea01ac7fdbc4a1f3f0f94efffae4fee88a6cf95` | `c955b194b20c7868acfedfea7c18f0d232d34a113f484a3bc90112b93e30a782` | `controller_logic.py::run_once`, `controller_logic.py::handle_night_mode` |
| 03 | `ae4f12850bcc79034f0fd2a9acce168f31a6bb554b383464fdace89beb8d210b` | `88db5aa083357daa1023594750a0cd22594ddd081078d495a425a6d37debd279` | `controller_logic.py::_harvest_time_profile`, `controller_logic.py::_s3_season_policy`, `controller_logic.py::handle_charge` |
| 04 | `82ecbaf77d6ea0a375f5d4aec63034228f9118294be94a96d51537ce29d4670c` | `3f9df1b42768a6ddb3f03989fcc7d80d98f07ac443850bdea0d709ef9aaec624` | `controller_logic.py::_harvest_time_profile`, `controller_logic.py::update_rest_surplus_harvest_state` |
| 05 | `7915af462359d0b1c4fa5af63931a0eb119781250a0ffc4094ac4e35a92e4815` | `27fe634b3fe1bee8d26eae697cab583f4abb9efe7b16f004b6a10eea86f77f07` | `controller_logic.py::handle_charge`, `state.py::ControllerState` |
| 06 | `3bfedf7ff66de2550d8eaa159124e8cb16d411f7cbd87cad4e550ce1661340b3` | `2bd7aa38a2cef161177a701db7555bb98b8df98e6b9c0376d144e771ab5a0cfb` | `controller_logic.py::handle_charge`, `controller_logic.py::_apply_symmetric_cross_charge_limit` |
| 07 | `26df4bd752b482e9e880e9fcebb90ec61799d86f6853c9d07cec38f219a45cd7` | `21e9e33d3d72090f897ecb788d7ff3a74ee4573c0c4a9b25f2d82dc01af6f939` | `command_lifecycle.py`, `controller_logic.py::_publish_signed_target` |
| 08 | `c4a3aae108bc978fa85c86ae0b49308235315c05bc5d55740cb45faa51ff4ca1` | `2fd7eb541efcf7c938f3c7474123dc575868a3ea5d89f272365da4ab65878a7e` | `command_lifecycle.py`, `controller_logic.py::run_once` |
| 09 | `83cb64e86afd1857fa77edc6b326e66d6e0d338609223df25bb0086e14fd7837` | `05e0f48475d2ae81a141972904df227063c2958df8c4aa54e79e0852e646c4f2` | `controller_logic.py`, `web_ui.py::build_grid_mini_payload`, `operational_events.py` |
| 10 | `ee4cce6de11dabd74eee57d5c4edae038aa7bbba824471cc5fbf592a136ef3ae` | `b99fc33dfb069e55d096783784dbb33e32916010694536cf5e419c36da975350` | `controller_logic.py::run_once`, `controller_logic.py::handle_discharge` |
| 11 | `982cd07b9ef6285cffc353a09c429d4d4d5a7e7ec2689577df81b5df229a3324` | `99e1b89f81032bd5ff9f240131900c5476be15a59cf3bf5fa2fe956acaf25037` | `controller_logic.py::handle_charge` |
| 12 | `4e1ce1cc42bc9dd93a19785d8ea20a4d0ecfc447638789aa40c58610bd7f6e5d` | `cae645b2b5951d3168b428f66e52e9f2a448cfc013ee742573fe92473aec771d` | `controller_logic.py::handle_discharge` |
| 13 | `3485557412ee7b804902ea9c84b59007abd704afc5cefb9f542391e332f91e8e` | `521a40aac39ada410c4ef3bb03ce092c39ff14c5f7f2de26f90bf828084637c9` | `controller_logic.py::_harvest_time_profile`, `controller_logic.py::handle_charge` |
| 14 | `de0e5e56bf8a0385a48f19132e4a995d825ef9d0c09e2c3fde2f221b06c07a82` | `983b3da464e06a1f11734442f5981782cf7d1d5edcf1f4e5fa09b451a019d7db` | `controller_logic.py::handle_charge`, `controller_logic.py::_s3_season_policy` |
| 15 | `97955a95ec10f060a00e3fd528d5fc9d13552bc05795adc9d12d574b8d9474cb` | `6bea45bc1a602958cc60038ae186ea3d8c61eee1d39c8c4e6b94767a65ec1743` | `controller_logic.py::run_once`, `controller_logic.py::handle_charge` |
| 16 | `d3cd2982fbacb491a2006935087a56d8f80d2c8de363a2a11485c4c3bd032bce` | `3f1e30bfd43ffe6d3e911637281b270c80095f6916ff9c0f0e0bb9e736edb178` | `controller_logic.py::_harvest_time_profile`, `controller_logic.py::_s3_season_policy` |
| 17 | `e2725413f87698a74bd7d470e7744d3117ca0e3b1689db935a538fcd33ccf72e` | `996d9768a339a44d99d52494ae59934fd86f356b85edc74ef0f8e4ea2cd6e408` | `controller_logic.py::handle_charge` |
| 18 | `e7203b74b2199d103ac24e125f241ca29cd231b5feb1ec2d32dad74a7a999d4f` | `fbf507b8ca30f5796cda6e8ec13a485c608fecd45b745802a1d0e55fea6de201` | `state.py::ControllerState`, `controller_logic.py::_s3_season_policy` |
| 19 | `24980e984b7f76bd69c354e55f3e220bd47516ae330704e8e456d40d911a571f` | `f20b8bfaf2010d71a33ff3969c6f6d01743301150b2f228a601eecbb7144b33f` | `controller_logic.py::_harvest_time_profile`, `controller_logic.py::_s3_season_policy` |
| 20 | `845be4ea251c2a380b91a48da8770f109f79da7be8be7841de43072bb2b56329` | `3c6ead9f363ec4bdf5d1382ab798767a0fdb61d661017c6d8239fce01676e68f` | `controller_logic.py::_s3_season_policy`, `controller_logic.py::_s3_calendar_parallel` |
| 21 | `c67bf3f3f6f043a9ad0b6abb232ee61b63c7b9d8cfb743a713e637715501677b` | `82bee3bb977c555ee57ec40ad4313d93c6d242e9cc09024525c4eb82e82a2d7f` | `static/status_v2.js`, `web_ui.py::build_grid_mini_payload`, `operational_events.py` |
| 22 | `7a1ff5e050201973d618e231c47a08fd282a474b51948f1f9619c9fd1616fa6c` | `a9342d817b4932b70e36a902fb140077b157cddb56040ce1bddd2fedddc9dc7d` | `operational_events.py`, `state.py` |


## CP19 – Entwicklungsdifferenz, nicht Bestandteil von V17.1.3

- **08:** `controller_logic.py::_mark_mismatch`; `operational_events.py::persist_confirmed_emergency_failure`; `operational_events.py::_observe_battery_care_incident`; `state.py::ControllerState` – Event-ID und Zielreserve, WAL/FULL-Sofort-Commit, Retry nach DB-Fehler.
- **09:** `controller_logic.py`; `operational_events.py` – Notladefehler synchron/Recovery asynchron, gemeinsamer Operational-Events-Store.
- **01–07, 10–22:** in CP19 `REVIEWED_UNCHANGED`, unveränderte DOT/SVG/PNG-Basis V17.1.3. Alle CP19-Diagramme sind Entwicklungs-As-built; `MANUAL_RELEASE_GATE=PENDING`.

## CP26 – tatsächliche Battery-Care-Quellenprovenienz (Entwicklung, nicht Release)

Alle neuen Source-Symbole wurden gegen die aktuelle CP25-Python-AST geprüft; DOT/PNG/SVG-Hashes stehen zusätzlich im aktualisierten Manifest. `MANUAL_SOURCE_AND_VISUAL_REVIEW=PENDING`.

- **01 UPDATED:** `battery_care_policy.py::decide_care`, `controller_logic.py::_battery_care_grid_dispatch`.
- **02 UPDATED:** `battery_care_stage_events.py::observed_care_stage`, `controller_logic.py::run_once`.
- **03 UPDATED:** `battery_care_pv_allocation.py::allocate_care_pv`, `battery_care_grid_observation.py::observe_grid_policy`.
- **04 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.
- **05 UPDATED:** `battery_care_pv_allocation.py::allocate_care_pv`.
- **06 UPDATED:** `controller_logic.py::_battery_care_grid_dispatch`.
- **07 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.
- **08 UPDATED:** `operational_events.py::persist_confirmed_emergency_failure`, `operational_events.py::_observe_battery_care_incident`.
- **09 UPDATED:** `battery_care_policy.py::decide_care`, `battery_care_episode_store.py::CareEpisodeStore`, `operational_events.py::_observe_battery_care_stage`, `battery_care_graph_history.py::care_day_lines`.
- **10 UPDATED:** `controller_logic.py::_battery_care_reserve_soc`.
- **11 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.
- **12 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.
- **13 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.
- **14 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.
- **15 UPDATED:** `battery_care_policy.py::decide_care`, `controller_logic.py::_battery_care_grid_dispatch`.
- **16 UPDATED:** `battery_care_stage_events.py::observed_care_stage`, `operational_events.py::_observe_battery_care_stage`.
- **17 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.
- **18 UPDATED:** `battery_care_stage_events.py::observed_care_stage`, `battery_care_graph_history.py::care_day_incidents`.
- **19 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.
- **20 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.
- **21 UPDATED:** `state.py::ControllerState`, `operational_events.py::_observe_battery_care_stage`.
- **22 REVIEWED_UNCHANGED:** vorhandene Source-Verweise im Manifest; keine CP26-Syntax-/Hashänderung.

## V18.0.1 – vorläufige Sourcebindungen

Release: V18.0.1 / v18.0.1-20261102; `controller_logic.py`, `operational_events.py`, `web_ui.py`, `status_page_v2.py`, `settings_registry.py`, `static/settings_v2.js` und `tools/zec_battery_care_7d_readonly.py` sind die veränderten Implementierungsflächen. Die vorhandenen Diagramme haben noch keinen finalen semantischen/sourcegebundenen manuell freigegebenen V18.0.1-Review; der Release-Gate bleibt FAIL.

## V18.0.1 CP12 current rendered assets

| ID | DOT SHA256 | SVG SHA256 | PNG SHA256 |
|---|---|---|---|
| 01 | `27f365a982139f258e7f88ffc2a7c4a59143be9f4b10884080360657fc04181f` | `58b89c46322354f6eaa729fb009473b3f4934041dd3483a3c619bb29d7db3a54` | `fcc6a46c666cd4708158b1c4f6c88ef078e19cdc101bc44f6db0a9349c2d775a` |
| 02 | `4e0d4f8360bad129d61ac51d2e9d21824a05c6ec04cba714a0c4d736ec80d925` | `cebc2e6e268c0b20132e661880055cd6998deef323ccb841a007eecb58ef4a00` | `87f8f0f9f466703e0e6deec9b1758c0f20b1c6ad2a0f9224a066a697f22da04c` |
| 03 | `26028c948d433b743b18484d356f1e9013b103dd923d9006ed1a98ccf97d98b6` | `ae65358f84bf1a9d46349875090702ed05a47c282a040903896085a0dcba6069` | `3e6447a363a50b90552024978d6f995eb9ababede91ffea6f6d26932a7b170aa` |
| 04 | `39a0e93b4bbafc7da9e6e37c1d8e4951bf7e70323eedaf36314c4df62b4a03a8` | `4111841c9daa618a9f19484f61396a878c8c6ff8ed6d2e11205cdb1c41eaa9b1` | `52dea7cea5d50f88e44b1c8d2d8287a2d8a62cb3985d27771a8376415681121f` |
| 05 | `2a5aef1e664dbe7148f4ff38202b98e7f55ec6d6b21f0b1ab220ec3e398ab6c8` | `a066109a010bea45629ad6d65d15efdf1a4eac5e83f0a5330a490e42b40ad8e4` | `0301a4508cf18f0dba404bf66c1c8f992e17fd581dcb8ef852cee4d5c1a8590d` |
| 06 | `d8a0e735044940b00246d7461c0898a22912b4ce8e01cf830a0b550f3f9ca40b` | `07281668c359fc2a96d6b439898b791802a22665f25ab0657b7b1d8052101353` | `28096b7f2882a5e62b5a04e82a5a2afbbb1e6cd6bc9cfd8cfdc615d23c012861` |
| 07 | `26df4bd752b482e9e880e9fcebb90ec61799d86f6853c9d07cec38f219a45cd7` | `21e9e33d3d72090f897ecb788d7ff3a74ee4573c0c4a9b25f2d82dc01af6f939` | `83aee7f0097d58f694ca2963c1f83f901d64e9ed1e8ae9d0fa730bb39695eb04` |
| 08 | `fd9a87f15b3b2bca27e7bf0a7288e17b490c8586541ca3d9f9adb02523ac6451` | `dc28e6ac9c2ebcef12f19835fadae8b7c344cd7d9695abefea7f69fec397c39b` | `1713df677e1e95d5f5b854603eca179fe01076fca36c7086e4e3bfa8343ed79e` |
| 09 | `274e96770d536c6b7d968888b7714f0c2f06f79e3be781929f999cb9a96965ac` | `75a66a30589f3e72f0e8dffbbc6425507e7af059d2008ac2c50d354748b9dcc0` | `0f1ef5476165018791e7943ee6f279522a4dfc99ad5df4cb4d2eae1a64400cd5` |
| 10 | `c229936813bc08a7867046d52ef11834e6d73a7ab7865b85fc68d1f70567cae1` | `a24ba4b1e3f4ddf3e499bc9b6b83aa6f717eba7a865026742ca45edaf4d35225` | `d5c86b70766bc74ea5b609dbef8b147b9948239f78fd5d4780a8f3449e3b2a36` |
| 11 | `982cd07b9ef6285cffc353a09c429d4d4d5a7e7ec2689577df81b5df229a3324` | `99e1b89f81032bd5ff9f240131900c5476be15a59cf3bf5fa2fe956acaf25037` | `f0cd9137e23bd6e2b28488e961cc520400591e60b58317f4261cdbc0e3481cd3` |
| 12 | `4e1ce1cc42bc9dd93a19785d8ea20a4d0ecfc447638789aa40c58610bd7f6e5d` | `cae645b2b5951d3168b428f66e52e9f2a448cfc013ee742573fe92473aec771d` | `fe85edff3d08c208d44df790f589056c492fe6375ba623d471ad4517f931e138` |
| 13 | `7adf2f15a71773a099f9158865c4d2b534c5cad1c0aafeba4708d08a7b239d7f` | `4d1ee593015390b9bddbfe1912731891e3c0078b2e0ba07a85925f870d1d9b63` | `ac22b4556ab3a76d05990094c21985b13758eef6974d890dae105bc1d5b876e2` |
| 14 | `a9704b26c7454eab9c4050caf318f56ba29ed28338df30ab87515ee128e3dc77` | `828d7e0be5ea901eb1bab63415171e35279cc4eb48e3b87667c1563f5c708ac3` | `8ace5fdc3c17615e747ca3f6444ee54bf20dc25110707230bd83828a6566bd2c` |
| 15 | `00b2f82079ac8be3f6626602610c3c374d5b5abab86e702bfa769ab5cd0bc145` | `49e167619ff27f5724463c698b3d4ac3f0472b9e5c7bcfb7056ac9216bb9d1a9` | `eb7b3c7f3fe7c11f45c69dad7fe3596493ae5b85728b3ee497a622226159af1d` |
| 16 | `8f495fa39576f6a7bf49ea54c5fee6100b919e0afede00fe284efe10277bc4fc` | `ff625ac70b00c27fc5fff1656dbf2767e2e1dd92bd57ef9ffb6bfb30d0719196` | `1ff4e7944a933c2f171bf65fa0f8dbd524d02e8b0d449e16e465a731c82718b3` |
| 17 | `e2725413f87698a74bd7d470e7744d3117ca0e3b1689db935a538fcd33ccf72e` | `996d9768a339a44d99d52494ae59934fd86f356b85edc74ef0f8e4ea2cd6e408` | `66dfcb86e0b6d9cc65e27c1652ca1da8303f90c652b8ed57b5ae642376f74a34` |
| 18 | `99dca905d18fd96c9a8e3ec33d6ee118e4cc2c768445cc17eeb3bb2ff088f2ca` | `2b2f6d04847c96ecc0d8d699a5a80acea86ec9bdcaa2312b16bd814648149e7b` | `496eb652333cea792894877020a32d89e7ef763a18a63da2014d25eff47e843c` |
| 19 | `7c361dd038b0a79babe5907ee3a572748d47626ed47d492b8c4c681383c9e0df` | `8d00b100526da3ac956ac61b5289d7bdfab5476184bd443673791e1a929a45c6` | `f56c4352613881f260dd448238dcffdc61552517a1fac9b9d0201be134aaaa7d` |
| 20 | `03962f2e3296dfcb4d2d3dfca7990532116ef824afc0e13908b22cca6ccce9e4` | `65bbacb3bc88956f34507103d7026d9731046cb5015291f411c726253a87c889` | `ff648751c7ca6a2a149cc0a38c1c905aa485e923b5e3731fefe4b0beffd0b010` |
| 21 | `1435ee37987552f0051d4838007702fe84db610f89944620f3100e2afbc97eff` | `81c9ea9e679dbd9b17ee9be81628bff0f94464604d69c12fb1c880ba7804f23c` | `43608cf03afa9d4b7d2d59b874ea12967063e4b3d2385ec6aeb380d32eaa6367` |
| 22 | `e5a7930fc776abce131b63469f3dfcbfad2e28cad73c2962fa1cb5df8d550780` | `5185c20661348593518144f107edcd9cf36e5015f1ab4b81bea9326588a81ec9` | `062cfe2f7cc4c58882ef72610a60d60ffc64cf4644d689274577377b4206950f` |

The V17.1.3 SHA table above remains historical provenance, not the current V18.0.1 artifact digest. Semantic/manual release gate remains PENDING.

## V18.0.1 manuelle Quell-/Bildreview-Provenienz

22 Einzelbewertungen: `SOURCE_REVIEW_V18_0_1_20261102.md`; aktueller Reviewstand im versionierten `manifest.json`. Build/Installer-Releaseberechtigung bleibt bis zu eigenen Gates offen.
