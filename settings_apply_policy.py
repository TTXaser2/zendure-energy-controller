# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

from settings_registry import ApplyClass, SETTINGS_BY_KEY


@dataclass(frozen=True)
class ApplyPlan:
    changed_keys: Tuple[str, ...]
    live_keys: Tuple[str, ...]
    restart_keys: Tuple[str, ...]
    protected_action_keys: Tuple[str, ...]
    read_only_keys: Tuple[str, ...]
    migration_only_keys: Tuple[str, ...]
    unknown_keys: Tuple[str, ...]

    @property
    def pending_restart(self) -> bool:
        return bool(self.restart_keys)

    @property
    def blocking_keys(self) -> Tuple[str, ...]:
        return self.protected_action_keys + self.read_only_keys + self.migration_only_keys

    @property
    def valid_for_normal_apply(self) -> bool:
        return not self.blocking_keys


def build_apply_plan(configured: Mapping[str, Any], effective: Mapping[str, Any], keys: Optional[Tuple[str, ...]] = None) -> ApplyPlan:
    """Pure classification only. This function writes and activates nothing."""
    universe = keys if keys is not None else tuple(dict.fromkeys(tuple(configured.keys()) + tuple(effective.keys())))
    changed = tuple(sorted(key for key in universe if configured.get(key) != effective.get(key)))
    buckets = {apply_class: [] for apply_class in ApplyClass}
    unknown = []
    for key in changed:
        spec = SETTINGS_BY_KEY.get(key)
        if spec is None:
            unknown.append(key)
        else:
            buckets[spec.apply_class].append(key)
    return ApplyPlan(
        changed_keys=changed,
        live_keys=tuple(sorted(buckets[ApplyClass.LIVE_NEXT_CYCLE])),
        restart_keys=tuple(sorted(buckets[ApplyClass.RESTART_REQUIRED])),
        protected_action_keys=tuple(sorted(buckets[ApplyClass.PROTECTED_ACTION])),
        read_only_keys=tuple(sorted(buckets[ApplyClass.READ_ONLY])),
        migration_only_keys=tuple(sorted(buckets[ApplyClass.MIGRATION_ONLY])),
        unknown_keys=tuple(sorted(unknown)),
    )
