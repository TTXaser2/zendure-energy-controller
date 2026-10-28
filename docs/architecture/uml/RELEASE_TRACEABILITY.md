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
