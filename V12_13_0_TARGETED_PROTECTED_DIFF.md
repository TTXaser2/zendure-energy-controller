# V12.13.0 – Targeted Protected-Diff / No-Regression

Basis: V12.12.2 / `v12.12.2-20260810`  
Ziel: V12.13.0 / `v12.13.0-20260811`

## 1. Dateihashes

| Datei | V12.12.2 | V12.13.0 | Bewertung |
|---|---|---|---|
| `command_lifecycle.py` | `6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176` | `6399fe4413e0f6dc1bf05daef826816e387f6306c03cfc184fcb2f3ffb1c2176` | byteidentisch |
| `mqtt_bridge.py` | `ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791` | `ec54d6b23192ea5f5cc6e30bcacdcff6bb368a870bd0126941d3206e52f2d791` | byteidentisch |
| `cross_charge.py` | `cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7` | `cd077e43cb36fa3f9ab519a92ee468650bbdb516c4905254b0547a721723e5c7` | byteidentisch |
| `zendure_power_observation.py` | `ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a` | `ff17a74ff8f228d15598a96d776160edbfe30c1bf491e6db71e4b43b04a3150a` | byteidentisch |
| `controller_logic.py` | `52f5311eecad93626480536c06e99e1bfe84ec9b2a20493815fc03a7ebed3526` | `ef0ba82838154911b257644dd2f53d44497685c6f825244c863e2072b7a1853c` | nur Docstring; semantische AST ohne Docstrings identisch |
| `measurement_v4.py` | `070dfb02ed78899869a1b5188076c6a62d9245ae9fbb0c67cd59eab8cf565564` | `3f17f532a252e04a5a0973ff8c41197709a0addaae85e61b8399350913f38563` | nur Kommentar/Dokumentation; semantische AST ohne Docstrings identisch |
| `measurement_v4_contract.py` | `4896dc12c3810ed06614e9f0504d94bcd7252857348a6366bb52ebec92cc0f27` | `f5314e291616d6db55212baa722ff299aefc41d8aaae0c0fffd2b064befdb1ed` | nur V4-Schemaidentitätskonstanten ergänzt; Header separat geprüft |

## 2. Measurement-V4-Feldvertrag

- Standard: 246 Felder; V12.12.2 `7842bfef39d47f93dc39689aa04da7658564af565e5051c24f90b32021d184a7`; V12.13.0 `7842bfef39d47f93dc39689aa04da7658564af565e5051c24f90b32021d184a7`.
- Extended: 249 Felder; V12.12.2 `8f61d07e66428a6e8757333d35d5dd73dd3a0975ac9a16714b93dc9b86460e93`; V12.13.0 `8f61d07e66428a6e8757333d35d5dd73dd3a0975ac9a16714b93dc9b86460e93`.
- Standard identisch: **True**.
- Extended identisch: **True**.

Neu sind ausschließlich die kanonischen Konstanten `MEASUREMENT_SCHEMA_NAME="ZEC-MEASUREMENT-V4"` und `MEASUREMENT_SCHEMA_VERSION=4`.

## 3. Regler-/Command-No-Regression

- `controller_logic.py` semantische AST (Docstrings entfernt) V12.12.2: `06bd07541629036af46e3ff6be1ba78212fdf94ec74226cf438e82634de3f562`
- `controller_logic.py` semantische AST (Docstrings entfernt) V12.13.0: `06bd07541629036af46e3ff6be1ba78212fdf94ec74226cf438e82634de3f562`
- `measurement_v4.py` semantische AST (Docstrings entfernt) V12.12.2: `601278a8be603d6f8556cca5e946b8dec948f5e87098c7614481e6e1ab039804`
- `measurement_v4.py` semantische AST (Docstrings entfernt) V12.13.0: `601278a8be603d6f8556cca5e946b8dec948f5e87098c7614481e6e1ab039804`
- Damit sind die ausführbare Python-Semantik von Controllerlogik und V4-Writer trotz aktualisierter Kommentare/Docstrings identisch.
- `command_lifecycle.py`, `mqtt_bridge.py`, `cross_charge.py` und `zendure_power_observation.py` sind byteidentisch.

## 4. Absichtlich geänderte Daten-/Kompatibilitätsschicht

- `csv_logger.py`: produktiven V3-Writer und V3-Fallback entfernt; Facade schreibt nur V4 und hält SQLite-Graphqueue unabhängig.
- `state.py`: interne Graph-/Zyklusdaten von V3-Schemaidentität entkoppelt; keine Regelentscheidung verändert.
- `config_manager.py`, `settings_registry.py`, `settings_runtime.py`: V4 fester Kompatibilitätsmarker; historische 3→4-Migration.
- Offline `tools/`: historische V3-Lesefähigkeit bleibt ausdrücklich read-only erhalten.
- `/graph-data.csv`: eigener `ZEC-GRAPH-EXPORT-V1`, kein Measurement-Label.

## 5. Hardware-/Lernwerkzeug

- Excel-Lernwerkzeug V12.12.2: `15f699008c82fe71367604fcb97e1900c023fe8929b40d3fc7210ee2117e79fe`
- Excel-Lernwerkzeug V12.13.0: `15f699008c82fe71367604fcb97e1900c023fe8929b40d3fc7210ee2117e79fe`
- Byteidentisch: **True**.

## 6. Ergebnis

**PASS.** Der Release entfernt ausschließlich produktive Legacy-V3-Schemawahl/-Schreibpfade und bereinigt deren Semantik. Live-Regelalgorithmen, Commandpfad, Cross-Charge, NIGHT, Harvest-Zielwertlogik, Single-Owner und der Measurement-V4-Writer bleiben fachlich unverändert; der V4-Feldvertrag bleibt exakt 246/249.
