# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import csv
import os
from typing import Any, Dict, Iterable, List

from version import CSV_SCHEMA

# ZEC-MEASUREMENT-V2: bewusst maschinenlesbare Spaltennamen.
# Trennzeichen: Semikolon. Dezimalzeichen: Punkt.
CSV_FIELDS: List[str] = [
    # Schema / Zeitbasis
    "schema",
    "controller_version",
    "date",
    "timestamp",
    "datetime_local",
    "epoch",
    "dt_s",

    # Messwerte / signierte Hauptwerte
    "raw_grid_power_w",
    "raw_grid_power_meaning",
    "grid_power_w",
    "grid_power_meaning",
    "zendure_target_power_w",
    "zendure_actual_power_w",
    "second_battery_power_w",
    "second_battery_power_meaning",

    # Zendure Rohwerte / Diagnose
    "zendure_raw_grid_input_power_w",
    "zendure_raw_pack_input_power_w",
    "zendure_raw_output_home_power_w",
    "zendure_raw_output_pack_power_w",
    "zendure_actual_charge_power_w",
    "zendure_actual_discharge_power_w",
    "zendure_telemetry_source",
    "zendure_api_fallback_active",
    "battery_temperature_c",

    # Zweitbatterie / Cross-Charge
    "second_battery_raw_power_w",
    "second_battery_discharge_power_w",
    "second_battery_soc_percent",
    "second_battery_capacity_kwh",
    "effective_export_power_w",

    # SOC / Reglerpfad
    "zendure_soc_percent",
    "mode",
    "mode_label",
    "target_before_smoothing_w",
    "target_after_smoothing_w",
    "target_after_ramp_w",
    "control_action",
    "limit_reason",
    "limit_label",
    "technical_limiters",
    "technical_path",
    "technical_path_label",
    "control_reason",

    # Tatsächlich gesendete MQTT-Kommandodynamik
    "mqtt_commands_sent_total",
    "mqtt_commands_sent_in_cycle",
    "mqtt_last_command",
    "mqtt_last_command_skipped",

    # Diagnose / Loop
    "charge_acceptance_state",
    "charge_acceptance_reason",
    "loop_duration_ms",
    "loop_counter",
    "last_error",
    "last_error_time",
]

CSV_HEADER_MAP = {field: field for field in CSV_FIELDS}


class CsvRotatingLogger:
    """CSV-Rotator für ZEC-MEASUREMENT-V2.

    Das Format unterstützt ausschließlich das aktuelle Schema. Alte CSV-Dateien
    werden nicht im Controller erkannt oder migriert; das V12.7-Update-Script
    verschiebt sie vor dem ersten Start in ein Backup-Verzeichnis.
    """

    def __init__(self) -> None:
        self._last_path = None

    def log(self, config: Dict[str, Any], row: Dict[str, Any]) -> None:
        if not config.get("CSV_LOG_ENABLED", False):
            return

        path = self.get_current_path(config)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._rotate_if_needed(config, path)
        write_header = not os.path.exists(path) or os.path.getsize(path) == 0

        out_row = dict(row)
        out_row["schema"] = out_row.get("schema") or CSV_SCHEMA

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore", delimiter=";")
            if write_header:
                writer.writerow(CSV_HEADER_MAP)
            writer.writerow({field: out_row.get(field, "") for field in CSV_FIELDS})

    def get_current_path(self, config: Dict[str, Any]) -> str:
        log_dir = str(config.get("CSV_LOG_DIR", "logs"))
        log_file = str(config.get("CSV_LOG_FILE", "zendure_measurements.csv"))
        return os.path.abspath(os.path.join(log_dir, log_file))

    def _rotate_if_needed(self, config: Dict[str, Any], path: str) -> None:
        max_bytes = int(config.get("CSV_LOG_MAX_BYTES", 5_000_000))
        backup_count = int(config.get("CSV_LOG_BACKUP_COUNT", 2))

        if not os.path.exists(path) or os.path.getsize(path) < max_bytes:
            return

        for index in range(backup_count, 0, -1):
            src = self._backup_path(path, index)
            dst = self._backup_path(path, index + 1)
            if index == backup_count and os.path.exists(src):
                os.remove(src)
            elif os.path.exists(src):
                os.replace(src, dst)

        os.replace(path, self._backup_path(path, 1))

    def _backup_path(self, path: str, index: int) -> str:
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        stem, ext = os.path.splitext(filename)
        return os.path.join(directory, f"{stem}_{index}{ext}")


def rows_to_csv(rows: Iterable[Dict[str, Any]]) -> str:
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, extrasaction="ignore", delimiter=";")
    writer.writerow(CSV_HEADER_MAP)
    for row in rows:
        out_row = dict(row)
        out_row["schema"] = out_row.get("schema") or CSV_SCHEMA
        writer.writerow({field: out_row.get(field, "") for field in CSV_FIELDS})
    return buffer.getvalue()
