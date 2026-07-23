# SPDX-License-Identifier: AGPL-3.0-or-later
"""Small cached Raspberry Pi/Linux health snapshot for the web UI.

All reads are performed from the web/status path, never from the controller loop.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from typing import Any, Dict, Optional

_lock = threading.Lock()
_cache: Dict[str, Any] = {"built": 0.0, "payload": None}
_prev_cpu: Optional[tuple[int, int]] = None
_prev_swap: Optional[tuple[float, int, int]] = None
_start_epoch = time.time()


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _cpu_percent() -> Optional[float]:
    global _prev_cpu
    text = _read("/proc/stat")
    if not text:
        return None
    parts = text.splitlines()[0].split()
    if not parts or parts[0] != "cpu":
        return None
    vals = [int(x) for x in parts[1:]]
    total = sum(vals)
    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
    current = (total, idle)
    if _prev_cpu is None:
        _prev_cpu = current
        return None
    dt = total - _prev_cpu[0]
    di = idle - _prev_cpu[1]
    _prev_cpu = current
    if dt <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (dt - di) / dt))


def _mem() -> Dict[str, Optional[float]]:
    vals: Dict[str, int] = {}
    for line in _read("/proc/meminfo").splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        try:
            vals[k] = int(v.strip().split()[0]) * 1024
        except Exception:
            pass
    total = vals.get("MemTotal", 0)
    avail = vals.get("MemAvailable", 0)
    swap_total = vals.get("SwapTotal", 0)
    swap_free = vals.get("SwapFree", 0)
    return {
        "ram_total_bytes": total or None,
        "ram_available_bytes": avail or None,
        "ram_used_percent": (100.0 * (total - avail) / total) if total else None,
        "swap_total_bytes": swap_total,
        "swap_used_bytes": max(0, swap_total - swap_free),
    }



def _swap_activity() -> Dict[str, Optional[float]]:
    """Return swap-in/out throughput derived from /proc/vmstat deltas.

    Linux exposes pswpin/pswpout as page counters.  The calculation is cached
    with the other web metrics and never runs in the controller loop.
    """
    global _prev_swap
    values: Dict[str, int] = {}
    for line in _read("/proc/vmstat").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in {"pswpin", "pswpout"}:
            try:
                values[parts[0]] = int(parts[1])
            except Exception:
                pass
    if "pswpin" not in values or "pswpout" not in values:
        return {"swap_in_bytes_per_s": None, "swap_out_bytes_per_s": None}
    now = time.monotonic()
    current = (now, values["pswpin"], values["pswpout"])
    if _prev_swap is None:
        _prev_swap = current
        return {"swap_in_bytes_per_s": None, "swap_out_bytes_per_s": None}
    elapsed = now - _prev_swap[0]
    page_size = int(os.sysconf("SC_PAGE_SIZE")) if hasattr(os, "sysconf") else 4096
    if elapsed <= 0:
        _prev_swap = current
        return {"swap_in_bytes_per_s": None, "swap_out_bytes_per_s": None}
    result = {
        "swap_in_bytes_per_s": max(0.0, (current[1] - _prev_swap[1]) * page_size / elapsed),
        "swap_out_bytes_per_s": max(0.0, (current[2] - _prev_swap[2]) * page_size / elapsed),
    }
    _prev_swap = current
    return result

def _temperature() -> Optional[float]:
    raw = _read("/sys/class/thermal/thermal_zone0/temp")
    try:
        value = float(raw)
        return value / 1000.0 if value > 200 else value
    except Exception:
        return None


def _load() -> list[Optional[float]]:
    parts = _read("/proc/loadavg").split()
    try:
        return [float(parts[0]), float(parts[1]), float(parts[2])]
    except Exception:
        return [None, None, None]


def _uptime() -> Optional[float]:
    try:
        return float(_read("/proc/uptime").split()[0])
    except Exception:
        return None


def _throttled() -> Dict[str, Any]:
    result: Dict[str, Any] = {"available": False, "raw": None, "current": [], "historic": []}
    if not shutil.which("vcgencmd"):
        return result
    try:
        proc = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=0.8, check=False)
        text = (proc.stdout or "").strip()
        raw = int(text.split("=", 1)[1], 16)
        result.update({"available": True, "raw": f"0x{raw:x}"})
        current_map = {0: "Unterspannung", 1: "Frequenz begrenzt", 2: "Drosselung aktiv", 3: "Temperaturlimit aktiv"}
        hist_map = {16: "Unterspannung", 17: "Frequenz begrenzt", 18: "Drosselung", 19: "Temperaturlimit"}
        result["current"] = [label for bit, label in current_map.items() if raw & (1 << bit)]
        result["historic"] = [label for bit, label in hist_map.items() if raw & (1 << bit)]
    except Exception:
        pass
    return result


def _disk(path: str) -> Dict[str, Optional[int]]:
    try:
        usage = shutil.disk_usage(path if os.path.exists(path) else os.path.dirname(path) or "/")
        return {"disk_total_bytes": usage.total, "disk_free_bytes": usage.free, "disk_used_bytes": usage.used}
    except Exception:
        return {"disk_total_bytes": None, "disk_free_bytes": None, "disk_used_bytes": None}


def get_system_metrics(storage_path: str = "/", ttl_s: float = 5.0) -> Dict[str, Any]:
    now = time.time()
    with _lock:
        if _cache.get("payload") is not None and now - float(_cache.get("built") or 0) < ttl_s:
            return dict(_cache["payload"])
        payload: Dict[str, Any] = {
            "captured_epoch": now,
            "cpu_percent": _cpu_percent(),
            "cpu_count": os.cpu_count() or 1,
            "temperature_c": _temperature(),
            "load": _load(),
            "system_uptime_s": _uptime(),
            "web_uptime_s": max(0.0, now - _start_epoch),
            "throttling": _throttled(),
        }
        payload.update(_mem())
        payload.update(_swap_activity())
        payload.update(_disk(storage_path))
        _cache.update({"built": now, "payload": payload})
        return dict(payload)
