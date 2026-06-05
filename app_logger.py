# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import os
from datetime import datetime
from typing import Any, Dict


class RotatingAppLogger:
    """Optional rotating text log for operational messages.

    This is intentionally separate from the CSV data logger. The CSV logger
    stores measurement and control rows; this logger stores human-readable
    operational messages such as startup, MQTT reconnects and errors.
    """

    def log(self, config: Dict[str, Any], message: str) -> None:
        if not config.get("FILE_LOG_ENABLED", False):
            return

        try:
            path = self.get_current_path(config)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self._rotate_if_needed(config, path)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} {message}\n")
        except Exception:
            # File logging must never break the controller.
            pass

    def get_current_path(self, config: Dict[str, Any]) -> str:
        log_dir = str(config.get("FILE_LOG_DIR", "logs"))
        log_file = str(config.get("FILE_LOG_FILE", "zendure_runtime.log"))
        return os.path.abspath(os.path.join(log_dir, log_file))

    def _rotate_if_needed(self, config: Dict[str, Any], path: str) -> None:
        max_bytes = int(config.get("FILE_LOG_MAX_BYTES", 2_000_000))
        backup_count = int(config.get("FILE_LOG_BACKUP_COUNT", 3))

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
