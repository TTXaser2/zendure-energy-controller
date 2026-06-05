# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# Optional CSV analysis for Zendure Energy Controller. The live controller does
# not import this module.

import csv
import os
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

CSV_SCHEMA = "ZEC-MEASUREMENT-V2"

DEFAULT_MAX_FILES = 20
DEFAULT_MAX_TOTAL_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_ROWS = 500_000
DEFAULT_TARGET_BAND_W = 100.0
DEFAULT_SIGNIFICANT_GRID_W = 200.0
DEFAULT_CROSS_DISCHARGE_W = 80.0
DEFAULT_ZENDURE_CHARGE_W = 100.0


@dataclass
class CsvMeasurementFile:
    path: str
    rows: List[Dict[str, Any]]
    size_bytes: int = 0


@dataclass
class AnalysisLimits:
    max_files: int = DEFAULT_MAX_FILES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    max_rows: int = DEFAULT_MAX_ROWS


def _float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _float_or_none(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _percent(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * part / total, 1)


def _round(value: float, digits: int = 3) -> float:
    return round(float(value or 0.0), digits)


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = int(round(0.95 * (len(values) - 1)))
    return values[idx]


def _row_epoch(row: Dict[str, Any]) -> Optional[float]:
    epoch = _float_or_none(row.get("epoch"))
    if epoch and epoch > 0:
        return epoch
    return None


def _row_time_label(row: Dict[str, Any]) -> str:
    return _text(row.get("datetime_local") or (str(row.get("date", "")) + " " + str(row.get("timestamp", ""))).strip() or row.get("timestamp") or "-")


def _row_sort_key(row: Dict[str, Any]) -> Tuple[float, str, int]:
    epoch = _row_epoch(row)
    if epoch is not None:
        return (epoch, _row_time_label(row), _int(row.get("loop_counter"), 0))
    return (0.0, _row_time_label(row), _int(row.get("loop_counter"), 0))


def _row_dt_s(row: Dict[str, Any], previous_epoch: Optional[float]) -> float:
    dt = _float(row.get("dt_s"), -1.0)
    if dt >= 0.0:
        return dt
    epoch = _row_epoch(row)
    if previous_epoch is not None and epoch is not None and epoch > previous_epoch:
        return epoch - previous_epoch
    return 0.0


def _mode(row: Dict[str, Any]) -> str:
    return _text(row.get("mode") or "-")


def _grid(row: Dict[str, Any]) -> float:
    return _float(row.get("grid_power_w"), _float(row.get("grid_power"), 0.0))


def _target(row: Dict[str, Any]) -> float:
    return _float(row.get("zendure_target_power_w"), _float(row.get("zendure_target_signed_power"), 0.0))


def _actual(row: Dict[str, Any]) -> float:
    return _float(row.get("zendure_actual_power_w"), _float(row.get("zendure_system_signed_power"), 0.0))


def _second_display_power(row: Dict[str, Any]) -> float:
    return _float(row.get("second_battery_power_w"), _float(row.get("sma_battery_display_power"), _float(row.get("sma_battery_power"), 0.0)))


def _second_discharge_power(row: Dict[str, Any]) -> float:
    value = _float_or_none(row.get("second_battery_discharge_power_w"))
    if value is not None:
        return max(0.0, value)
    # Signed display convention: positive = charging, negative = discharging.
    return max(0.0, -_second_display_power(row))


def _limiter_text(row: Dict[str, Any]) -> str:
    return _text(row.get("technical_limiters") or row.get("limit_reason") or row.get("limit_label") or "")


def _is_cross_blocked(row: Dict[str, Any]) -> bool:
    limiters = _limiter_text(row)
    return any(token in limiters for token in ("SMA_DISCHARGE", "LOW_EFFECTIVE_SURPLUS", "CROSS_CHARGE"))


def _is_safe_state(row: Dict[str, Any]) -> bool:
    return _mode(row) == "SAFE_STATE" or "SAFE_STATE" in _text(row.get("control_action"))


def _event(events: List[Dict[str, Any]], row: Dict[str, Any], severity: str, kind: str, text: str, details: Optional[Dict[str, Any]] = None) -> None:
    events.append({
        "time": _row_time_label(row),
        "severity": severity,
        "type": kind,
        "text": text,
        "details": details or {},
    })


def read_measurement_csv(path: str) -> CsvMeasurementFile:
    """Read a ZEC-MEASUREMENT-V2 CSV file.

    Legacy CSV formats are intentionally unsupported. The schema column must be
    present and every non-empty row must declare ZEC-MEASUREMENT-V2.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    size_bytes = os.path.getsize(path)
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        if ";" not in first_line:
            raise ValueError("Nicht unterstütztes CSV-Format: ZEC-MEASUREMENT-V2 erwartet Semikolon-Trennzeichen.")
        reader = csv.DictReader(f, delimiter=";")
        if not reader.fieldnames or "schema" not in reader.fieldnames:
            raise ValueError("Nicht unterstütztes CSV-Format: Spalte 'schema' fehlt.")
        for row in reader:
            if not any((v or "").strip() for v in row.values()):
                continue
            schema = (row.get("schema") or "").strip()
            if schema != CSV_SCHEMA:
                raise ValueError(f"Nicht unterstütztes CSV-Schema: {schema or 'leer'}")
            rows.append(dict(row))
    return CsvMeasurementFile(path=path, rows=rows, size_bytes=size_bytes)


def read_measurement_csv_files(paths: Sequence[str], limits: Optional[AnalysisLimits] = None) -> Tuple[List[CsvMeasurementFile], List[str]]:
    limits = limits or AnalysisLimits()
    unique_paths: List[str] = []
    seen = set()
    for raw in paths:
        if not raw:
            continue
        path = str(Path(raw).resolve())
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    if not unique_paths:
        raise ValueError("Keine CSV-Datei ausgewählt.")
    if len(unique_paths) > limits.max_files:
        raise ValueError(f"Zu viele Dateien ausgewählt: maximal {limits.max_files} CSV-Dateien pro Analyselauf.")

    total_size = 0
    files: List[CsvMeasurementFile] = []
    warnings: List[str] = []
    total_rows = 0
    for path in unique_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        total_size += os.path.getsize(path)
        if total_size > limits.max_total_bytes:
            raise ValueError(
                f"Die ausgewählten Dateien sind zu groß ({total_size / 1024 / 1024:.1f} MB). "
                f"Limit: {limits.max_total_bytes / 1024 / 1024:.0f} MB."
            )
        mf = read_measurement_csv(path)
        files.append(mf)
        total_rows += len(mf.rows)
        if total_rows > limits.max_rows:
            raise ValueError(f"Zu viele Messpunkte: maximal {limits.max_rows:,} Zeilen pro Analyselauf.".replace(",", "."))
        if not mf.rows:
            warnings.append(f"{os.path.basename(path)} enthält keine Messdaten.")
    return files, warnings


def _merge_rows(files: Sequence[CsvMeasurementFile]) -> Tuple[List[Dict[str, Any]], int]:
    merged: List[Dict[str, Any]] = []
    for file_index, mf in enumerate(files):
        for row in mf.rows:
            r = dict(row)
            r["_source_file"] = os.path.basename(mf.path)
            r["_source_index"] = file_index
            merged.append(r)
    merged.sort(key=_row_sort_key)

    deduped: List[Dict[str, Any]] = []
    seen = set()
    duplicates = 0
    for row in merged:
        epoch = _row_epoch(row)
        key = (round(epoch, 3), _text(row.get("loop_counter"))) if epoch is not None else (_row_time_label(row), _text(row.get("loop_counter")), _text(row.get("_source_file")))
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, duplicates



def _has_grid(row: Dict[str, Any]) -> bool:
    return row.get("grid_power_w", row.get("grid_power")) not in (None, "")


def _has_actual(row: Dict[str, Any]) -> bool:
    return row.get("zendure_actual_power_w", row.get("zendure_system_signed_power")) not in (None, "")


def _soc_value(row: Dict[str, Any]) -> Optional[float]:
    return _float_or_none(row.get("zendure_soc_percent", row.get("soc")))


def _sign(value: float, threshold: float) -> int:
    if value > threshold:
        return 1
    if value < -threshold:
        return -1
    return 0


def _classify_state(
    row: Dict[str, Any],
    grid_value: float,
    target: float,
    actual: float,
    soc: Optional[float],
    min_soc_percent: int,
    max_soc_percent: int,
    target_band_w: float,
) -> str:
    mode = _mode(row)
    if _is_safe_state(row):
        return "SAFE_STATE"
    if soc is not None and soc >= max_soc_percent and grid_value < -target_band_w:
        return "MAX_SOC"
    if soc is not None and soc <= min_soc_percent and grid_value > target_band_w:
        return "MIN_SOC"
    if _is_cross_blocked(row):
        return "CROSS_CHARGE_LIMIT"
    if mode == "NIGHT_DISCHARGE":
        return "NIGHT_DISCHARGE"
    if abs(grid_value) <= target_band_w and abs(target) < 50 and abs(actual) < 80:
        return "HOLD_DEADBAND"
    if target > 50 or actual > 80 or mode == "CHARGE":
        return "AUTO_CHARGE"
    if target < -50 or actual < -80 or mode == "DISCHARGE":
        return "AUTO_DISCHARGE"
    if abs(grid_value) > target_band_w and abs(target) < 50:
        return "HOLD_OUTSIDE_DEADBAND"
    return mode or "OTHER"


def _state_is_controllable(state: str) -> bool:
    return state in {"AUTO_CHARGE", "AUTO_DISCHARGE", "HOLD_DEADBAND", "HOLD_OUTSIDE_DEADBAND", "NIGHT_DISCHARGE"}


def _rating_green_yellow_red(value: float, green: float, yellow: float, lower_is_better: bool = True) -> str:
    if lower_is_better:
        if value <= green:
            return "green"
        if value <= yellow:
            return "yellow"
        return "red"
    if value >= green:
        return "green"
    if value >= yellow:
        return "yellow"
    return "red"


def _make_recommendations(result: Dict[str, Any]) -> List[Dict[str, str]]:
    recs: List[Dict[str, str]] = []
    fair = result.get("fair_regulator_quality") or {}
    sat = result.get("actuator_reserve") or {}
    dead = result.get("deadband") or {}
    tracking = result.get("tracking") or {}
    osc = result.get("oscillation") or {}
    cmd = result.get("command_efficiency") or {}
    cross = result.get("cross_charge") or {}
    dq = result.get("data_quality") or {}

    if dq.get("status") != "ok":
        recs.append({"severity": "warning", "topic": "Datenbasis", "text": "Die Analyse enthält Datenlücken oder fehlende Messwerte. Parameteränderungen sollten erst nach Prüfung der Datenqualität bewertet werden."})
    if fair.get("controllable_avg_abs_grid_w", 0) > 300:
        recs.append({"severity": "warning", "topic": "Reglerqualität", "text": "Die beeinflussbare Restabweichung ist erhöht. Prüfe CONTROL_GAIN, SMOOTHING_FACTOR und MAX_POWER_STEP_W; bei träger Reaktion kann eine vorsichtig aggressivere Regelung sinnvoll sein."})
    if fair.get("non_controllable_percent", 0) > 50:
        recs.append({"severity": "info", "topic": "Randbedingungen", "text": "Ein großer Anteil der Netzabweichung ist nicht durch den Regler beeinflussbar. Ursache sind eher SOC-/Leistungsgrenzen oder Safe-State-Zeiten als falsche Regelparameter."})
    if sat.get("charge_saturated_percent", 0) > 20:
        recs.append({"severity": "info", "topic": "Ladegrenze", "text": "Zendure arbeitet häufig am Ladelimit oder bei MAX_SOC. Mehr Ladeleistung bzw. Speicherkapazität würde Einspeisung eher reduzieren als eine Reglerparameteränderung."})
    if sat.get("discharge_saturated_percent", 0) > 10:
        recs.append({"severity": "info", "topic": "Entladegrenze", "text": "Zendure arbeitet häufig am Entladelimit oder bei MIN_SOC. Mehr Entladeleistung/Kapazität würde Netzbezug eher reduzieren als eine Reglerparameteränderung."})
    if tracking.get("bad_tracking_percent", 0) > 20:
        recs.append({"severity": "warning", "topic": "Zendure Soll/Ist", "text": "Zendure folgt dem Sollwert häufig nicht ausreichend. Vor Parameteränderungen MQTT-Telemetrie, SOC-Grenzen und Zendure-interne Leistungsbegrenzung prüfen."})
    if dead.get("outside_deadband_with_reserve_percent", 0) > 15:
        recs.append({"severity": "warning", "topic": "Deadband", "text": "Das Netz liegt oft außerhalb des Deadbands, obwohl Stellreserve vorhanden ist. Prüfe, ob Deadband, Glättung oder Regelverstärkung zu konservativ eingestellt sind."})
    if dead.get("commands_inside_deadband", 0) > 10:
        recs.append({"severity": "info", "topic": "Deadband", "text": "Es wurden mehrere Kommandos innerhalb des Deadbands gesendet. MIN_COMMAND_CHANGE_W oder Deadband können ggf. erhöht werden, falls die Regelung unnötig unruhig wirkt."})
    if osc.get("oscillation_rating") == "red":
        recs.append({"severity": "warning", "topic": "Oszillation", "text": "Viele schnelle Richtungswechsel deuten auf Schwingen hin. Prüfe CONTROL_GAIN, SMOOTHING_FACTOR, MODE_CHANGE_LOCK_SECONDS und MIN_COMMAND_CHANGE_W."})
    if cmd.get("no_effect_percent", 0) > 25:
        recs.append({"severity": "info", "topic": "MQTT-Kommandowirkung", "text": "Ein relevanter Anteil der MQTT-Kommandos zeigt keine erkennbare Wirkung. Prüfe MIN_COMMAND_CHANGE_W, Zendure-Reaktionszeit und Telemetrieaktualität."})
    if cross.get("rating") in {"yellow", "red"}:
        recs.append({"severity": "warning", "topic": "Cross-Charge", "text": "Cross-Charge zeigt kritische Überschneidungen. Prüfe SMA_DISCHARGE_BLOCK_W, CROSS_CHARGE_RESERVE_W und MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W."})
    if not recs:
        recs.append({"severity": "ok", "topic": "Gesamtbewertung", "text": "Keine eindeutige Handlungsempfehlung erkannt. Die Regelung wirkt in den ausgewählten Daten unauffällig oder die Abweichungen sind überwiegend systembedingt."})
    return recs[:10]


def analyze_rows(
    rows: Iterable[Dict[str, Any]],
    min_soc_percent: int = 15,
    max_soc_percent: int = 99,
    *,
    file_count: int = 1,
    filenames: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    duplicate_rows_removed: int = 0,
    target_band_w: float = DEFAULT_TARGET_BAND_W,
    significant_grid_w: float = DEFAULT_SIGNIFICANT_GRID_W,
    cross_discharge_threshold_w: float = DEFAULT_CROSS_DISCHARGE_W,
    zendure_charge_threshold_w: float = DEFAULT_ZENDURE_CHARGE_W,
    max_charge_power_w: float = 2100.0,
    max_discharge_power_w: float = 2100.0,
) -> Dict[str, Any]:
    rows_list = list(rows)
    total_dt = 0.0
    grid_import_wh = grid_export_wh = 0.0
    zendure_charge_wh = zendure_discharge_wh = 0.0
    second_charge_wh = second_discharge_wh = 0.0
    min_soc_s = max_soc_s = night_s = safe_state_s = 0.0
    missing_grid = missing_soc = missing_zendure_actual = 0
    high_soc_states = Counter()
    mqtt_commands = mqtt_changed_rows = mqtt_target_change_rows = 0
    target_step_abs_sum = target_step_abs_max = 0.0
    target_sign_changes = mode_switches = target_zero_crossings = 0
    import_over_s = export_over_s = target_band_s = 0.0
    abs_grid_values: List[float] = []
    dt_values: List[float] = []
    gap_events = 0
    events: List[Dict[str, Any]] = []

    cross_blocked_s = cross_block_events = 0
    cross_critical_s = cross_critical_events = 0
    cross_sma_discharge_wh = cross_zendure_charge_wh = 0.0
    cross_sma_discharge_samples: List[float] = []
    cross_zendure_charge_samples: List[float] = []
    cross_prevented_charge_wh = 0.0
    cross_rating = "green"
    cross_rating_reason = "Keine kritischen Überschneidungen erkannt."

    # New V12.8.4 diagnostics.
    controllable_s = uncontrollable_s = 0.0
    controllable_error_ws = non_controllable_error_ws = total_error_ws = 0.0
    controllable_values: List[float] = []
    non_controllable_values: List[float] = []
    charge_saturated_s = discharge_saturated_s = 0.0
    charge_free_s = discharge_free_s = 0.0
    charge_reserve_ws = discharge_reserve_ws = 0.0
    tracking_active_s = tracking_good_s = tracking_bad_s = 0.0
    tracking_errors: List[float] = []
    target_no_actual_s = 0.0
    deadband_inside_s = deadband_extended_s = 0.0
    hold_inside_deadband_s = 0.0
    outside_deadband_with_reserve_s = 0.0
    commands_inside_deadband = 0
    large_target_steps = 0
    short_reverse_commands = 0
    command_effect_improved = command_effect_neutral = command_effect_worse = command_effect_unknown = 0

    mode_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {
        "samples": 0, "seconds": 0.0, "abs_grid_w_sum": 0.0, "grid_wh_abs": 0.0,
        "grid_import_wh": 0.0, "grid_export_wh": 0.0, "time_in_target_band_s": 0.0,
        "mqtt_commands": 0.0, "controllable_error_ws": 0.0, "non_controllable_error_ws": 0.0,
    })

    previous_epoch: Optional[float] = None
    previous_mode: Optional[str] = None
    previous_target: Optional[float] = None
    previous_target_sign = 0
    previous_direction_epoch: Optional[float] = None
    was_cross_blocked = was_cross_critical = was_safe_state = False
    first_time = _row_time_label(rows_list[0]) if rows_list else "-"
    last_time = _row_time_label(rows_list[-1]) if rows_list else "-"
    per_row: List[Dict[str, Any]] = []

    for row in rows_list:
        dt = _row_dt_s(row, previous_epoch)
        epoch = _row_epoch(row)
        if epoch is not None:
            previous_epoch = epoch
        if dt > 0:
            dt_values.append(dt)
        total_dt += dt

        has_grid = _has_grid(row)
        grid_value = _grid(row)
        if not has_grid:
            missing_grid += 1
        wh = grid_value * dt / 3600.0
        if wh > 0:
            grid_import_wh += wh
        else:
            grid_export_wh += abs(wh)
        abs_grid = abs(grid_value)
        abs_grid_values.append(abs_grid)
        total_error_ws += abs_grid * dt
        if abs_grid <= target_band_w:
            target_band_s += dt
            deadband_inside_s += dt
        if abs_grid <= max(target_band_w * 2.5, 200.0):
            deadband_extended_s += dt
        if grid_value >= significant_grid_w:
            import_over_s += dt
        if grid_value <= -significant_grid_w:
            export_over_s += dt

        actual = _actual(row)
        has_actual = _has_actual(row)
        if not has_actual:
            missing_zendure_actual += 1
        if actual >= 0:
            zendure_charge_wh += actual * dt / 3600.0
        else:
            zendure_discharge_wh += abs(actual) * dt / 3600.0

        second_power = _second_display_power(row)
        if second_power >= 0:
            second_charge_wh += second_power * dt / 3600.0
        else:
            second_discharge_wh += abs(second_power) * dt / 3600.0

        soc = _soc_value(row)
        if soc is None:
            missing_soc += 1
        else:
            if 0 <= soc <= min_soc_percent:
                min_soc_s += dt
            if soc >= max_soc_percent:
                max_soc_s += dt

        mode = _mode(row)
        target = _target(row)
        state = _classify_state(row, grid_value, target, actual, soc, min_soc_percent, max_soc_percent, target_band_w)
        if mode == "NIGHT_DISCHARGE":
            night_s += dt
        if previous_mode is not None and mode != previous_mode:
            mode_switches += 1
            _event(events, row, "info", "mode_switch", f"Moduswechsel: {previous_mode} -> {mode}")
        previous_mode = mode

        safe_state = _is_safe_state(row)
        if safe_state:
            safe_state_s += dt
            if not was_safe_state:
                _event(events, row, "error", "safe_state", "SAFE_STATE aktiv oder Safe-State-Aktion erkannt")
        was_safe_state = safe_state

        charge_state = _text(row.get("charge_acceptance_state") or "ok")
        high_soc_states[charge_state] += 1

        commands_in_cycle = _int(row.get("mqtt_commands_sent_in_cycle"), 0)
        if commands_in_cycle > 0:
            mqtt_changed_rows += 1
            mqtt_commands += commands_in_cycle
            if abs_grid <= target_band_w:
                commands_inside_deadband += commands_in_cycle

        if previous_target is not None:
            step = target - previous_target
            abs_step = abs(step)
            if abs_step > 0:
                mqtt_target_change_rows += 1
                target_step_abs_sum += abs_step
                target_step_abs_max = max(target_step_abs_max, abs_step)
                if abs_step >= 500:
                    large_target_steps += 1
        target_sign = _sign(target, zendure_charge_threshold_w)
        if previous_target_sign and target_sign and target_sign != previous_target_sign:
            target_sign_changes += 1
            if previous_direction_epoch is not None and epoch is not None and (epoch - previous_direction_epoch) <= 60:
                short_reverse_commands += 1
            previous_direction_epoch = epoch
            _event(events, row, "warning", "target_direction_change", f"Sollleistung wechselt Vorzeichen: {previous_target:+.0f} W -> {target:+.0f} W")
        elif target_sign:
            previous_direction_epoch = epoch if previous_direction_epoch is None else previous_direction_epoch
        if previous_target_sign and target_sign == 0:
            target_zero_crossings += 1
        if target_sign:
            previous_target_sign = target_sign
        previous_target = target

        blocked = _is_cross_blocked(row)
        if blocked:
            cross_blocked_s += dt
            if not was_cross_blocked:
                cross_block_events += 1
                _event(events, row, "info", "cross_charge_block", "Cross-Charge-Schutz begrenzt oder blockiert Zendure-Ladung", {"limiters": _limiter_text(row)})
        was_cross_blocked = blocked

        sma_discharge = _second_discharge_power(row)
        zendure_charge = max(0.0, actual)
        zendure_target_charge = max(0.0, target)
        critical = sma_discharge >= cross_discharge_threshold_w and zendure_charge >= zendure_charge_threshold_w
        if critical:
            cross_critical_s += dt
            cross_sma_discharge_wh += sma_discharge * dt / 3600.0
            cross_zendure_charge_wh += zendure_charge * dt / 3600.0
            cross_sma_discharge_samples.append(sma_discharge)
            cross_zendure_charge_samples.append(zendure_charge)
            if not was_cross_critical:
                cross_critical_events += 1
                _event(events, row, "warning", "cross_charge_overlap", f"Kritische Überschneidung: Zusatzbatterie entlädt ({sma_discharge:.0f} W), Zendure lädt ({zendure_charge:.0f} W)")
        was_cross_critical = critical
        if blocked and zendure_target_charge > zendure_charge:
            cross_prevented_charge_wh += (zendure_target_charge - zendure_charge) * dt / 3600.0

        charge_reserve = max(0.0, max_charge_power_w - max(0.0, actual))
        discharge_reserve = max(0.0, max_discharge_power_w - max(0.0, -actual))
        if soc is not None and soc >= max_soc_percent:
            charge_reserve = 0.0
        if soc is not None and soc <= min_soc_percent:
            discharge_reserve = 0.0
        if safe_state:
            charge_reserve = discharge_reserve = 0.0
        if blocked:
            charge_reserve = min(charge_reserve, max(0.0, abs(grid_value) - sma_discharge))

        if grid_value < -target_band_w:
            controllable_part = min(abs_grid, charge_reserve)
            non_controllable_part = max(0.0, abs_grid - controllable_part)
            if charge_reserve <= 50:
                charge_saturated_s += dt
            else:
                charge_free_s += dt
                charge_reserve_ws += charge_reserve * dt
        elif grid_value > target_band_w:
            controllable_part = min(abs_grid, discharge_reserve)
            non_controllable_part = max(0.0, abs_grid - controllable_part)
            if discharge_reserve <= 50:
                discharge_saturated_s += dt
            else:
                discharge_free_s += dt
                discharge_reserve_ws += discharge_reserve * dt
        else:
            controllable_part = 0.0
            non_controllable_part = 0.0
        if _state_is_controllable(state) or controllable_part > 0 or abs_grid <= target_band_w:
            controllable_s += dt
            controllable_values.append(controllable_part)
        else:
            uncontrollable_s += dt
        controllable_error_ws += controllable_part * dt
        non_controllable_error_ws += non_controllable_part * dt
        if non_controllable_part > 0:
            non_controllable_values.append(non_controllable_part)
        if abs_grid > target_band_w and controllable_part > 50:
            outside_deadband_with_reserve_s += dt
        if state == "HOLD_DEADBAND":
            hold_inside_deadband_s += dt

        if abs(target) >= zendure_charge_threshold_w:
            tracking_active_s += dt
            terr = abs(target - actual)
            tracking_errors.append(terr)
            good_threshold = max(120.0, abs(target) * 0.25)
            if terr <= good_threshold:
                tracking_good_s += dt
            else:
                tracking_bad_s += dt
                if (target > 0 and actual < max(80.0, target * 0.2)) or (target < 0 and actual > min(-80.0, target * 0.2)):
                    target_no_actual_s += dt

        stat = mode_stats[state]
        stat["samples"] += 1
        stat["seconds"] += dt
        stat["abs_grid_w_sum"] += abs_grid
        stat["grid_wh_abs"] += abs(wh)
        stat["grid_import_wh"] += wh if wh > 0 else 0.0
        stat["grid_export_wh"] += abs(wh) if wh < 0 else 0.0
        stat["time_in_target_band_s"] += dt if abs_grid <= target_band_w else 0.0
        stat["mqtt_commands"] += commands_in_cycle
        stat["controllable_error_ws"] += controllable_part * dt
        stat["non_controllable_error_ws"] += non_controllable_part * dt

        per_row.append({"row": row, "dt": dt, "grid_abs": abs_grid, "epoch": epoch, "state": state, "controllable_part": controllable_part, "safe": safe_state, "charge_reserve": charge_reserve, "discharge_reserve": discharge_reserve, "commands": commands_in_cycle})

    # Command effect: compare absolute grid error with the value two samples later.
    for i, item in enumerate(per_row):
        if item["commands"] <= 0:
            continue
        if item["safe"] or i + 2 >= len(per_row):
            command_effect_unknown += 1
            continue
        future = per_row[i + 2]
        if future["safe"] or future["dt"] <= 0:
            command_effect_unknown += 1
            continue
        delta = item["grid_abs"] - future["grid_abs"]
        if delta > max(80.0, item["grid_abs"] * 0.15):
            command_effect_improved += 1
        elif delta < -max(80.0, item["grid_abs"] * 0.15):
            command_effect_worse += 1
        else:
            command_effect_neutral += 1

    if dt_values:
        median_dt = statistics.median(dt_values)
        avg_dt = sum(dt_values) / len(dt_values)
        min_dt = min(dt_values)
        max_dt = max(dt_values)
        gap_threshold = max(median_dt * 2.5, median_dt + 5.0)
        previous_epoch = None
        for row in rows_list:
            dt = _row_dt_s(row, previous_epoch)
            epoch = _row_epoch(row)
            if epoch is not None:
                previous_epoch = epoch
            if dt > gap_threshold:
                gap_events += 1
                if gap_events <= 20:
                    _event(events, row, "warning", "data_gap", f"Datenlücke erkannt: dt_s={dt:.1f} s")
    else:
        median_dt = avg_dt = min_dt = max_dt = 0.0

    mqtt_commands_per_hour = mqtt_commands / (total_dt / 3600.0) if total_dt > 0 else 0.0
    active_hours = controllable_s / 3600.0 if controllable_s > 0 else 0.0
    mqtt_commands_per_active_hour = mqtt_commands / active_hours if active_hours > 0 else 0.0
    mode_switches_per_hour = mode_switches / (total_dt / 3600.0) if total_dt > 0 else 0.0
    avg_abs_grid = sum(abs_grid_values) / len(abs_grid_values) if abs_grid_values else 0.0
    median_abs_grid = statistics.median(abs_grid_values) if abs_grid_values else 0.0
    p95_abs_grid = _p95(abs_grid_values)
    controllable_avg = controllable_error_ws / total_dt if total_dt > 0 else 0.0
    controllable_active_avg = controllable_error_ws / controllable_s if controllable_s > 0 else 0.0
    non_controllable_avg = non_controllable_error_ws / total_dt if total_dt > 0 else 0.0
    tracking_avg = sum(tracking_errors) / len(tracking_errors) if tracking_errors else 0.0
    tracking_p95 = _p95(tracking_errors)

    if mqtt_commands_per_hour > 300:
        _event(events, rows_list[-1] if rows_list else {}, "warning", "mqtt_rate", f"Sehr hohe MQTT-Kommandorate: {mqtt_commands_per_hour:.1f} Kommandos/h")
    if target_sign_changes > 5 and total_dt <= 3600:
        _event(events, rows_list[-1] if rows_list else {}, "warning", "oscillation_hint", f"Auffällige Sollwert-Richtungswechsel: {target_sign_changes} Wechsel")

    if cross_critical_s >= 300 or (cross_sma_discharge_samples and max(cross_sma_discharge_samples) >= 500 and cross_critical_s >= 60):
        cross_rating = "red"
        cross_rating_reason = "Längere oder leistungsstarke gleichzeitige Zusatzbatterie-Entladung und Zendure-Ladung erkannt."
    elif cross_critical_s > 0:
        cross_rating = "yellow"
        cross_rating_reason = "Kurze oder geringe kritische Überschneidung erkannt."

    osc_score = target_sign_changes + short_reverse_commands * 2 + large_target_steps * 0.5
    osc_rating = "green" if osc_score <= 5 else ("yellow" if osc_score <= 15 else "red")
    deadband_rating = _rating_green_yellow_red(100.0 - _percent(outside_deadband_with_reserve_s, total_dt), 85.0, 70.0, lower_is_better=False)
    tracking_rating = _rating_green_yellow_red(_percent(tracking_bad_s, tracking_active_s), 10.0, 25.0, lower_is_better=True)
    fair_rating = _rating_green_yellow_red(controllable_active_avg, 180.0, 350.0, lower_is_better=True)
    command_total_eval = command_effect_improved + command_effect_neutral + command_effect_worse
    no_effect_percent = _percent(command_effect_neutral, command_total_eval)
    command_rating = _rating_green_yellow_red(no_effect_percent, 20.0, 40.0, lower_is_better=True)
    saturation_percent = _percent(charge_saturated_s + discharge_saturated_s, total_dt)
    saturation_rating = _rating_green_yellow_red(saturation_percent, 20.0, 45.0, lower_is_better=True)

    mode_quality = []
    for mode_name, stat in sorted(mode_stats.items(), key=lambda kv: (-kv[1]["seconds"], kv[0])):
        samples = max(1, int(stat["samples"]))
        mode_seconds = float(stat["seconds"])
        mode_quality.append({
            "mode": mode_name,
            "samples": int(stat["samples"]),
            "seconds": _round(mode_seconds, 1),
            "percent": _percent(mode_seconds, total_dt),
            "grid_import_kwh": _round(stat["grid_import_wh"] / 1000.0, 4),
            "grid_export_kwh": _round(stat["grid_export_wh"] / 1000.0, 4),
            "avg_abs_grid_w": _round(stat["abs_grid_w_sum"] / samples, 1),
            "abs_grid_kwh": _round(stat["grid_wh_abs"] / 1000.0, 4),
            "time_in_target_band_percent": _percent(stat["time_in_target_band_s"], mode_seconds),
            "controllable_avg_abs_grid_w": _round(stat["controllable_error_ws"] / mode_seconds if mode_seconds else 0.0, 1),
            "non_controllable_avg_abs_grid_w": _round(stat["non_controllable_error_ws"] / mode_seconds if mode_seconds else 0.0, 1),
            "mqtt_commands": int(stat["mqtt_commands"]),
        })

    data_quality_status = "ok"
    data_quality_warnings: List[str] = list(warnings or [])
    if rows_list and missing_grid:
        data_quality_warnings.append(f"{missing_grid} Zeilen ohne Netzleistung.")
    if rows_list and missing_soc:
        data_quality_warnings.append(f"{missing_soc} Zeilen ohne Zendure-SOC.")
    if rows_list and missing_zendure_actual:
        data_quality_warnings.append(f"{missing_zendure_actual} Zeilen ohne Zendure-Istleistung.")
    if gap_events:
        data_quality_warnings.append(f"{gap_events} größere Datenlücken erkannt.")
    if duplicate_rows_removed:
        data_quality_warnings.append(f"{duplicate_rows_removed} doppelte Messpunkte entfernt.")
    if safe_state_s > 0:
        data_quality_warnings.append(f"SAFE_STATE-Zeit erkannt: {safe_state_s:.1f} s.")
    if data_quality_warnings:
        data_quality_status = "warning"
    if not rows_list:
        data_quality_status = "error"
        data_quality_warnings.append("Keine Messdaten vorhanden.")

    summary = {
        "fair_regulator_quality": fair_rating,
        "actuator_reserve": saturation_rating,
        "zendure_tracking": tracking_rating,
        "cross_charge": cross_rating,
        "deadband": deadband_rating,
        "mqtt_command_effect": command_rating,
        "oscillation": osc_rating,
        "data_quality": "green" if data_quality_status == "ok" else ("red" if data_quality_status == "error" else "yellow"),
    }

    result = {
        "schema": CSV_SCHEMA,
        "analysis_version": "12.8.4",
        "file_count": int(file_count),
        "filenames": filenames or [],
        "rows": len(rows_list),
        "duplicate_rows_removed": int(duplicate_rows_removed),
        "period_start": first_time,
        "period_end": last_time,
        "duration_seconds": _round(total_dt, 1),
        "data_quality": {
            "status": data_quality_status,
            "warnings": data_quality_warnings,
            "avg_dt_s": _round(avg_dt, 3),
            "median_dt_s": _round(median_dt, 3),
            "min_dt_s": _round(min_dt, 3),
            "max_dt_s": _round(max_dt, 3),
            "gap_events": int(gap_events),
            "missing_grid_rows": int(missing_grid),
            "missing_soc_rows": int(missing_soc),
            "missing_zendure_actual_rows": int(missing_zendure_actual),
            "safe_state_seconds": _round(safe_state_s, 1),
        },
        "energy": {
            "grid_import_kwh": _round(grid_import_wh / 1000.0, 4),
            "grid_export_kwh": _round(grid_export_wh / 1000.0, 4),
            "zendure_charge_kwh": _round(zendure_charge_wh / 1000.0, 4),
            "zendure_discharge_kwh": _round(zendure_discharge_wh / 1000.0, 4),
            "second_battery_charge_kwh": _round(second_charge_wh / 1000.0, 4),
            "second_battery_discharge_kwh": _round(second_discharge_wh / 1000.0, 4),
        },
        "grid_import_kwh": _round(grid_import_wh / 1000.0, 4),
        "grid_export_kwh": _round(grid_export_wh / 1000.0, 4),
        "time_at_min_soc_seconds": _round(min_soc_s, 1),
        "time_at_max_soc_seconds": _round(max_soc_s, 1),
        "night_mode_seconds": _round(night_s, 1),
        "charge_acceptance_states": dict(sorted(high_soc_states.items())),
        "regulator_quality": {
            "target_band_w": _round(target_band_w, 1),
            "significant_grid_w": _round(significant_grid_w, 1),
            "avg_abs_grid_w": _round(avg_abs_grid, 1),
            "median_abs_grid_w": _round(median_abs_grid, 1),
            "p95_abs_grid_w": _round(p95_abs_grid, 1),
            "time_in_target_band_seconds": _round(target_band_s, 1),
            "time_in_target_band_percent": _percent(target_band_s, total_dt),
            "time_import_over_threshold_seconds": _round(import_over_s, 1),
            "time_export_over_threshold_seconds": _round(export_over_s, 1),
            "mqtt_commands_sent": int(mqtt_commands),
            "mqtt_command_rows": int(mqtt_changed_rows),
            "mqtt_commands_per_hour": _round(mqtt_commands_per_hour, 1),
            "mode_switches": int(mode_switches),
            "mode_switches_per_hour": _round(mode_switches_per_hour, 1),
            "target_change_rows": int(mqtt_target_change_rows),
            "avg_target_step_w": _round(target_step_abs_sum / max(1, mqtt_target_change_rows), 1),
            "max_target_step_w": _round(target_step_abs_max, 1),
            "target_sign_changes": int(target_sign_changes),
            "target_zero_crossings": int(target_zero_crossings),
        },
        "fair_regulator_quality": {
            "rating": fair_rating,
            "total_avg_abs_grid_w": _round(avg_abs_grid, 1),
            "active_window_seconds": _round(controllable_s, 1),
            "active_window_percent": _percent(controllable_s, total_dt),
            "non_active_window_seconds": _round(uncontrollable_s, 1),
            "controllable_avg_abs_grid_w": _round(controllable_avg, 1),
            "controllable_active_avg_abs_grid_w": _round(controllable_active_avg, 1),
            "controllable_p95_w": _round(_p95(controllable_values), 1),
            "non_controllable_avg_abs_grid_w": _round(non_controllable_avg, 1),
            "non_controllable_p95_w": _round(_p95(non_controllable_values), 1),
            "controllable_percent": _percent(controllable_error_ws, total_error_ws),
            "non_controllable_percent": _percent(non_controllable_error_ws, total_error_ws),
        },
        "actuator_reserve": {
            "rating": saturation_rating,
            "max_charge_power_w": _round(max_charge_power_w, 1),
            "max_discharge_power_w": _round(max_discharge_power_w, 1),
            "charge_saturated_seconds": _round(charge_saturated_s, 1),
            "charge_saturated_percent": _percent(charge_saturated_s, total_dt),
            "discharge_saturated_seconds": _round(discharge_saturated_s, 1),
            "discharge_saturated_percent": _percent(discharge_saturated_s, total_dt),
            "avg_free_charge_reserve_w": _round(charge_reserve_ws / charge_free_s if charge_free_s else 0.0, 1),
            "avg_free_discharge_reserve_w": _round(discharge_reserve_ws / discharge_free_s if discharge_free_s else 0.0, 1),
            "charge_free_seconds": _round(charge_free_s, 1),
            "discharge_free_seconds": _round(discharge_free_s, 1),
        },
        "tracking": {
            "rating": tracking_rating,
            "active_seconds": _round(tracking_active_s, 1),
            "good_seconds": _round(tracking_good_s, 1),
            "bad_seconds": _round(tracking_bad_s, 1),
            "good_tracking_percent": _percent(tracking_good_s, tracking_active_s),
            "bad_tracking_percent": _percent(tracking_bad_s, tracking_active_s),
            "avg_error_w": _round(tracking_avg, 1),
            "p95_error_w": _round(tracking_p95, 1),
            "target_without_actual_seconds": _round(target_no_actual_s, 1),
        },
        "deadband": {
            "rating": deadband_rating,
            "target_band_w": _round(target_band_w, 1),
            "inside_deadband_seconds": _round(deadband_inside_s, 1),
            "inside_deadband_percent": _percent(deadband_inside_s, total_dt),
            "inside_extended_band_percent": _percent(deadband_extended_s, total_dt),
            "hold_inside_deadband_seconds": _round(hold_inside_deadband_s, 1),
            "hold_inside_deadband_percent": _percent(hold_inside_deadband_s, deadband_inside_s),
            "outside_deadband_with_reserve_seconds": _round(outside_deadband_with_reserve_s, 1),
            "outside_deadband_with_reserve_percent": _percent(outside_deadband_with_reserve_s, total_dt),
            "commands_inside_deadband": int(commands_inside_deadband),
        },
        "oscillation": {
            "rating": osc_rating,
            "target_sign_changes": int(target_sign_changes),
            "target_zero_crossings": int(target_zero_crossings),
            "large_target_steps": int(large_target_steps),
            "short_reverse_commands": int(short_reverse_commands),
            "mode_switches": int(mode_switches),
            "mode_switches_per_hour": _round(mode_switches_per_hour, 1),
            "oscillation_score": _round(osc_score, 1),
        },
        "command_efficiency": {
            "rating": command_rating,
            "commands_total": int(mqtt_commands),
            "command_rows": int(mqtt_changed_rows),
            "commands_per_hour_total": _round(mqtt_commands_per_hour, 1),
            "commands_per_active_hour": _round(mqtt_commands_per_active_hour, 1),
            "avg_target_step_w": _round(target_step_abs_sum / max(1, mqtt_target_change_rows), 1),
            "max_target_step_w": _round(target_step_abs_max, 1),
            "improved_count": int(command_effect_improved),
            "neutral_count": int(command_effect_neutral),
            "worse_count": int(command_effect_worse),
            "unknown_count": int(command_effect_unknown),
            "improved_percent": _percent(command_effect_improved, command_total_eval),
            "no_effect_percent": _percent(command_effect_neutral, command_total_eval),
        },
        "cross_charge": {
            "rating": cross_rating,
            "rating_reason": cross_rating_reason,
            "block_events": int(cross_block_events),
            "blocked_seconds": _round(cross_blocked_s, 1),
            "critical_overlap_events": int(cross_critical_events),
            "critical_overlap_seconds": _round(cross_critical_s, 1),
            "critical_overlap_percent": _percent(cross_critical_s, total_dt),
            "max_sma_discharge_w_during_overlap": _round(max(cross_sma_discharge_samples) if cross_sma_discharge_samples else 0.0, 1),
            "avg_sma_discharge_w_during_overlap": _round(sum(cross_sma_discharge_samples) / len(cross_sma_discharge_samples) if cross_sma_discharge_samples else 0.0, 1),
            "max_zendure_charge_w_during_overlap": _round(max(cross_zendure_charge_samples) if cross_zendure_charge_samples else 0.0, 1),
            "avg_zendure_charge_w_during_overlap": _round(sum(cross_zendure_charge_samples) / len(cross_zendure_charge_samples) if cross_zendure_charge_samples else 0.0, 1),
            "sma_discharge_kwh_during_overlap": _round(cross_sma_discharge_wh / 1000.0, 4),
            "zendure_charge_kwh_during_overlap": _round(cross_zendure_charge_wh / 1000.0, 4),
            "reduced_or_prevented_charge_kwh": _round(cross_prevented_charge_wh / 1000.0, 4),
        },
        "night_discharge": {"seconds": _round(night_s, 1), "percent": _percent(night_s, total_dt)},
        "high_soc": {"states": dict(sorted(high_soc_states.items())), "note": "V12.8.4 wertet High-SOC bewusst nur leichtgewichtig aus; Schwerpunkt sind Reglerqualität und Cross-Charge."},
        "cross_charge_events": int(cross_block_events),
        "mqtt_commands_sent": int(mqtt_commands),
        "mqtt_command_rows": int(mqtt_changed_rows),
        "mode_quality": mode_quality,
        "operating_state_matrix": mode_quality,
        "summary_ratings": summary,
        "events": events[-250:],
        "thresholds": {
            "target_band_w": _round(target_band_w, 1),
            "significant_grid_w": _round(significant_grid_w, 1),
            "cross_discharge_threshold_w": _round(cross_discharge_threshold_w, 1),
            "zendure_charge_threshold_w": _round(zendure_charge_threshold_w, 1),
        },
    }
    result["recommendations"] = _make_recommendations(result)
    return result


def analyze_files(
    paths: Sequence[str],
    min_soc_percent: int = 15,
    max_soc_percent: int = 99,
    *,
    limits: Optional[AnalysisLimits] = None,
    target_band_w: float = DEFAULT_TARGET_BAND_W,
    significant_grid_w: float = DEFAULT_SIGNIFICANT_GRID_W,
    cross_discharge_threshold_w: float = DEFAULT_CROSS_DISCHARGE_W,
    zendure_charge_threshold_w: float = DEFAULT_ZENDURE_CHARGE_W,
    max_charge_power_w: float = 2100.0,
    max_discharge_power_w: float = 2100.0,
) -> Dict[str, Any]:
    files, warnings = read_measurement_csv_files(paths, limits=limits)
    merged, duplicates = _merge_rows(files)
    result = analyze_rows(
        merged,
        min_soc_percent=min_soc_percent,
        max_soc_percent=max_soc_percent,
        file_count=len(files),
        filenames=[os.path.basename(f.path) for f in files],
        warnings=warnings,
        duplicate_rows_removed=duplicates,
        target_band_w=target_band_w,
        significant_grid_w=significant_grid_w,
        cross_discharge_threshold_w=cross_discharge_threshold_w,
        zendure_charge_threshold_w=zendure_charge_threshold_w,
        max_charge_power_w=max_charge_power_w,
        max_discharge_power_w=max_discharge_power_w,
    )
    result["paths"] = [f.path for f in files]
    result["total_size_bytes"] = sum(f.size_bytes for f in files)
    return result


def analyze_file(path: str, min_soc_percent: int = 15, max_soc_percent: int = 99) -> Dict[str, Any]:
    result = analyze_files([path], min_soc_percent=min_soc_percent, max_soc_percent=max_soc_percent)
    result["path"] = path
    result["filename"] = os.path.basename(path)
    return result


def summary_csv(result: Dict[str, Any]) -> str:
    rows = [
        ("files", ", ".join(result.get("filenames") or [result.get("filename", "-")])),
        ("rows", result.get("rows", 0)),
        ("period_start", result.get("period_start", "-")),
        ("period_end", result.get("period_end", "-")),
        ("duration_seconds", result.get("duration_seconds", 0)),
        ("data_quality_status", (result.get("data_quality") or {}).get("status", "-")),
        ("avg_abs_grid_w", (result.get("regulator_quality") or {}).get("avg_abs_grid_w", 0)),
        ("median_abs_grid_w", (result.get("regulator_quality") or {}).get("median_abs_grid_w", 0)),
        ("p95_abs_grid_w", (result.get("regulator_quality") or {}).get("p95_abs_grid_w", 0)),
        ("time_in_target_band_percent", (result.get("regulator_quality") or {}).get("time_in_target_band_percent", 0)),
        ("controllable_active_avg_abs_grid_w", (result.get("fair_regulator_quality") or {}).get("controllable_active_avg_abs_grid_w", 0)),
        ("non_controllable_percent", (result.get("fair_regulator_quality") or {}).get("non_controllable_percent", 0)),
        ("deadband_rating", (result.get("deadband") or {}).get("rating", "-")),
        ("mqtt_command_effect_rating", (result.get("command_efficiency") or {}).get("rating", "-")),
        ("mqtt_commands_per_hour", (result.get("regulator_quality") or {}).get("mqtt_commands_per_hour", 0)),
        ("mode_switches_per_hour", (result.get("regulator_quality") or {}).get("mode_switches_per_hour", 0)),
        ("cross_charge_rating", (result.get("cross_charge") or {}).get("rating", "-")),
        ("cross_critical_overlap_seconds", (result.get("cross_charge") or {}).get("critical_overlap_seconds", 0)),
        ("cross_blocked_seconds", (result.get("cross_charge") or {}).get("blocked_seconds", 0)),
        ("night_mode_seconds", result.get("night_mode_seconds", 0)),
    ]
    out = ["metric;value"]
    for key, value in rows:
        escaped = str(value).replace("\n", " ").replace(";", ",")
        out.append(f"{key};{escaped}")
    return "\n".join(out) + "\n"
