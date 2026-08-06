#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Isolated analysis worker for Zendure Energy Controller replay service.

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
for item in (PROJECT_ROOT, TOOLS_DIR):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from replay_core import AnalysisLimits, analyze_files  # noqa: E402


def _set_memory_limit(limit_mb: int) -> None:
    if limit_mb <= 0:
        return
    try:
        import resource  # type: ignore
        limit = int(limit_mb) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except Exception:
        # Parent process still monitors RSS via /proc on Linux. If rlimit is not
        # available, analysis remains protected by parent timeout/RSS kill.
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    cfg: Dict[str, Any] = request.get("cfg") or {}
    limits = AnalysisLimits(**(request.get("limits") or {}))
    memory_mb = int(request.get("memory_mb") or 0)
    address_space_mb = int(request.get("address_space_mb") or memory_mb or 0)
    _set_memory_limit(address_space_mb)

    result = analyze_files(
        [str(p) for p in request.get("paths") or []],
        min_soc_percent=int(cfg.get("MIN_SOC_PERCENT", 15)),
        max_soc_percent=int(cfg.get("MAX_SOC_PERCENT", 99)),
        limits=limits,
        target_band_w=float(cfg.get("DEADBAND_W", 100) or 100),
        significant_grid_w=200.0,
        cross_discharge_threshold_w=float(cfg.get("CROSS_CHARGE_SIGNIFICANT_W", 80) or 80),
        zendure_charge_threshold_w=float(cfg.get("MIN_EFFECTIVE_SURPLUS_FOR_CHARGE_W", 150) or 100),
        max_charge_power_w=float(cfg.get("MAX_CHARGE_POWER_W", 2100) or 2100),
        max_discharge_power_w=float(cfg.get("MAX_DISCHARGE_POWER_W", 2100) or 2100),
    )
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
