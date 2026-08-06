#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from settings_registry import registry_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the generated, secret-safe SettingsRegistry snapshot")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(registry_snapshot(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
