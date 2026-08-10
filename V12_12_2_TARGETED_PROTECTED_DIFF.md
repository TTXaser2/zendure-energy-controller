# V12.12.2 – Targeted Protected-Diff / No-Regression

**Vergleichsbasis:** V12.12.1 / `v12.12.1-20260810`

## 1. Geschützte Dateien

Zwei bisher geschützte Dateien werden in V12.12.2 aufgrund ausdrücklich bestätigter Produktivbefunde gezielt geändert:

- `controller_logic.py`: ausschließlich Harvest-Zeit-/Observation-Semantik, Harvest-Current-State-Reset und Netzleistungs-Samplezeit für Distinctness;
- `measurement_v4.py`: ausschließlich Manifest-Rotation/Rowcount/Clean-Close-Lifecycle.

Unverändert/byteidentisch bleiben:

```text
command_lifecycle.py
6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176

mqtt_bridge.py
ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791

cross_charge.py
cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7

zendure_power_observation.py
ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a

measurement_v4_contract.py
4896dc12c3810ed06614e9f0504d94bcd7252857348a6366bb52ebec92cc0f27

tools/zendure_regelung_lernwerkzeug_v4_2_7_final.xlsx
15f699008c82fe71367604fcb97e1900c023fe8929b40d3fc7210ee2117e79fe
```

Gezielt geänderte Dateihashes:

```text
controller_logic.py
V12.12.1 435a6d30975bf4673e6640e98761b95d178fd4075cfed84d2fbeffcd30a4ea3b
V12.12.2 52f5311eecad93626480536c06e99e1bfe84ec9b2a20493815fc03a7ebed3526

measurement_v4.py
V12.12.1 374687009b19c51551b3a65763a73ee7c257a716a000aca8fc19aff3c251dd81
V12.12.2 070dfb02ed78899869a1b5188076c6a62d9245ae9fbb0c67cd59eab8cf565564
```

## 2. AST-Differential – nicht betroffene Reglerpfade

Die normalisierte AST-Repräsentation folgender Methoden ist V12.12.1 → V12.12.2 identisch:

```text
_apply_symmetric_cross_charge_limit
2e07140a233581a73d4bb03c3ed3de1a4da1219563e04a980132a725445a6842

_rest_surplus_charge_pressure_target
65069746d40d3740f789d90b94fd84d8ff755b30f985a2cc0b1ecba1310404c9

handle_manual_fixed_discharge
851757c2f617665de950154ee184ad384fd8dad16e254d4f300640964f74b252

handle_manual_fixed_charge
eeb707c3835e65410dc9652d70182ce59375ac877206eaf3309e6083732d4a8e

handle_night_mode
7b82988ec1cd3446a3a99bf53e24534816a456342631ca0af7fcf9baa7dadf6e

handle_discharge
43084c9d225f0db46495660f1234782ee71389b4852c43ddf71735083ab9c9fc

update_command_effect_monitor
5ee62a44d6fc3567807985707688d81a5463b11e28bac5fbfabf815856f61483

_publish_command_batch
034620f785507d7624ff3a3a3ab68151c53e5f39c6182664fbff314d6f850498
```

Damit bleibt insbesondere die eigentliche Harvest-Zielwertfunktion `_rest_surplus_charge_pressure_target()` unverändert.

## 3. Measurement-V4-Contract

`measurement_v4_contract.py` ist byteidentisch. Headerumfang bleibt:

```text
standard  246 Felder
extended  249 Felder
```

Die Änderung betrifft ausschließlich Manifest-Lifecycle-Metadaten, nicht das V4-Zeilenschema.

## 4. Testvertrag

Zusätzlich zum vollständigen bestehenden Testbestand werden gezielt abgedeckt:

- Single Owner gleiches/anderes CWD, Race, Clean Restart, Hard-Kill-Recovery, rejected main before runtime;
- Harvest nominale Zeit, Jitter, duplicate observations, Host-Stall, Hold, Wall-Clock-Sprung und Reset;
- sticky current `harvest_limiter_reason`;
- Manifest clean close, open/crash-distinguishability, Size-Rotation, exakter Rowcount und kein Finalizer-Dateivollscan;
- Desktop-Info-Panel click-pinned;
- mobile SOC-Details außerhalb des Canvas.
