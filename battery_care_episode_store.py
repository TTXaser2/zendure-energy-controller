# SPDX-License-Identifier: AGPL-3.0-or-later
"""Crash-resilient Battery Care grid-episode latch in the existing events DB.

Only the *operational* level and its immutable start-time recovery target are
persisted. Source freshness, command permission, effect and distinct SOC
confirmation MUST be reacquired after every restart.

This module is NOT a command publisher and never declares charging effective.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import closing
import time
from typing import Callable, Dict, Optional, Tuple

from battery_care_policy import CareEpisode
from operational_events import OperationalEventJournal


class CareEpisodePersistenceError(RuntimeError):
    """Persistence cannot be trusted; grid dispatch must fail closed."""


class CareEpisodeStore:
    def __init__(self, config_getter: Callable[[], Dict[str, object]]):
        self._journal = OperationalEventJournal(config_getter, None)

    @staticmethod
    def signature(episode: CareEpisode) -> Optional[Tuple[int, int]]:
        level, target = episode.active_level, episode.target_reserve_soc
        if level == 0:
            return None
        if (type(level) is not int or level not in (2, 3) or
                type(target) is not int or not (0 <= target <= 100)):
            raise CareEpisodePersistenceError("Ungültige Battery-Care-Episode")
        return level, target

    def _connect(self) -> sqlite3.Connection:
        # The journal already owns schema initialization and the configured
        # path/preflight semantics. Add a single latch table IN THE SAME DB.
        conn = None
        try:
            conn = self._journal._connect()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS battery_care_grid_episode (
                    slot INTEGER PRIMARY KEY CHECK(slot=1),
                    active_level INTEGER NOT NULL CHECK(active_level IN (2,3)),
                    reserve_soc INTEGER NOT NULL CHECK(reserve_soc BETWEEN 0 AND 100),
                    recorded_at REAL NOT NULL
                )
            """)
            conn.commit()
            return conn
        except (sqlite3.Error, OSError) as exc:
            if conn is not None:
                conn.close()
            raise CareEpisodePersistenceError("Battery-Care-Episoden-DB nicht verfügbar") from exc

    def exists(self) -> bool:
        """No SQLite side effect on a default-off fresh installation."""
        return os.path.isfile(self._journal.path())

    def load(self) -> CareEpisode:
        try:
            with closing(self._connect()) as conn:
                rows = conn.execute(
                    "SELECT active_level,reserve_soc FROM battery_care_grid_episode"
                ).fetchall()
            if not rows:
                return CareEpisode()
            if len(rows) != 1:
                raise CareEpisodePersistenceError("Mehrdeutige persistierte Battery-Care-Episode")
            level, target = rows[0]
            episode = CareEpisode(active_level=level, target_reserve_soc=target)
            self.signature(episode)
            # Deliberately NONE: old source IDs and elapsed timers from before
            # the restart never count as a fresh confirmation afterwards.
            return episode
        except (sqlite3.Error, OSError) as exc:
            raise CareEpisodePersistenceError("Battery-Care-Episode nicht lesbar") from exc

    def save(self, episode: CareEpisode) -> None:
        signature = self.signature(episode)
        try:
            with closing(self._connect()) as conn:
                with conn:
                    if signature is None:
                        conn.execute("DELETE FROM battery_care_grid_episode WHERE slot=1")
                    else:
                        conn.execute("""
                            INSERT INTO battery_care_grid_episode(slot,active_level,reserve_soc,recorded_at)
                            VALUES(1,?,?,?)
                            ON CONFLICT(slot) DO UPDATE SET
                               active_level=excluded.active_level,
                               reserve_soc=excluded.reserve_soc,
                               recorded_at=excluded.recorded_at
                        """, (signature[0], signature[1], time.time()))
        except (sqlite3.Error, OSError) as exc:
            raise CareEpisodePersistenceError("Battery-Care-Episode nicht dauerhaft speicherbar") from exc
