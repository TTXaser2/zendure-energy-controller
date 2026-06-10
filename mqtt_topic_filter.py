# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""MQTT topic filter helpers.

MQTT topic matching is case-sensitive. Supported wildcards:
- + matches exactly one topic level
- # matches all remaining levels and is only valid as the final level
"""

from typing import Any, Dict


def mqtt_topic_matches_filter(topic_filter: str, topic: str) -> bool:
    flt = str(topic_filter or "").strip()
    top = str(topic or "")
    if not flt or not top:
        return False

    filter_levels = flt.split("/")
    topic_levels = top.split("/")

    for index, filter_level in enumerate(filter_levels):
        if filter_level == "#":
            return index == len(filter_levels) - 1
        if index >= len(topic_levels):
            return False
        if filter_level == "+":
            continue
        if filter_level != topic_levels[index]:
            return False

    return len(topic_levels) == len(filter_levels)


def mqtt_diagnostic_should_capture(cfg: Dict[str, Any], topic: str) -> bool:
    if not cfg.get("MQTT_TOPIC_DIAGNOSTIC_ENABLED", False):
        return False

    view_mode = str(cfg.get("MQTT_TOPIC_DIAGNOSTIC_VIEW_MODE", "filtered")).strip().lower()
    if view_mode == "all":
        return True

    diagnostic_filter = str(cfg.get("MQTT_TOPIC_DIAGNOSTIC_FILTER", "Zendure/#")).strip()
    return mqtt_topic_matches_filter(diagnostic_filter, topic)
