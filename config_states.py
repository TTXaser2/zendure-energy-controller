# SPDX-License-Identifier: AGPL-3.0-or-later
"""Local named configuration-state store for ZEC V13."""
from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

from config_bundle import BundleError, build_bundle, encode_bundle, parse_bundle

MAX_NAMED_STATES = 100
_NAME_MAX = 80
_DESCRIPTION_MAX = 500
_STATE_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class ConfigStateError(RuntimeError):
    pass


def _clean_text(value: Any, *, minimum: int, maximum: int, code: str) -> str:
    text = str(value or "").strip()
    if len(text) < minimum or len(text) > maximum or any(ord(ch) < 32 and ch not in "\t" for ch in text):
        raise ConfigStateError(code)
    return " ".join(text.split())


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class StateRead:
    state_id: str
    path: str
    data: bytes
    revision: str
    bundle: Any


class ConfigStateStore:
    def __init__(self, config_path: str) -> None:
        self.config_path = os.path.abspath(config_path)
        self.root = os.path.join(os.path.dirname(self.config_path), "config-states")
        self._lock = threading.RLock()

    def ensure_root(self) -> None:
        parent = os.path.dirname(self.root)
        os.makedirs(parent, exist_ok=True)
        if os.path.lexists(self.root):
            st = os.lstat(self.root)
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                raise ConfigStateError("CONFIG_STATE_STORE_UNSAFE")
        else:
            os.mkdir(self.root, 0o700)
        os.chmod(self.root, 0o700)

    @staticmethod
    def _validate_id(state_id: str) -> str:
        value = str(state_id or "")
        if not _STATE_ID_RE.fullmatch(value):
            raise ConfigStateError("CONFIG_STATE_ID_INVALID")
        return value

    def _path(self, state_id: str) -> str:
        state_id = self._validate_id(state_id)
        return os.path.join(self.root, state_id + ".zec-config.json")

    def _read(self, state_id: str) -> StateRead:
        self.ensure_root()
        path = self._path(state_id)
        try:
            st = os.lstat(path)
        except FileNotFoundError as exc:
            raise ConfigStateError("CONFIG_STATE_NOT_FOUND") from exc
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise ConfigStateError("CONFIG_STATE_FILE_UNSAFE")
        if stat.S_IMODE(st.st_mode) & 0o077:
            raise ConfigStateError("CONFIG_STATE_FILE_PERMISSIONS_UNSAFE")
        if st.st_size > 1024 * 1024:
            raise ConfigStateError("CONFIG_STATE_FILE_TOO_LARGE")
        with open(path, "rb") as handle:
            data = handle.read(1024 * 1024 + 1)
        try:
            bundle = parse_bundle(data)
        except Exception as exc:
            raise ConfigStateError("CONFIG_STATE_CORRUPT") from exc
        if bundle.payload.get("artifact_kind") != "named_state":
            raise ConfigStateError("CONFIG_STATE_KIND_INVALID")
        return StateRead(state_id, path, data, _sha(data), bundle)

    def get(self, state_id: str) -> StateRead:
        with self._lock:
            return self._read(state_id)

    def _atomic_write(self, path: str, data: bytes) -> None:
        self.ensure_root()
        fd, tmp = tempfile.mkstemp(prefix=".zec-config-state-", suffix=".tmp", dir=self.root)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb", closefd=True) as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
            os.chmod(path, 0o600)
            dirfd = os.open(self.root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
        finally:
            try:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            except Exception:
                pass

    def _count_files(self) -> int:
        self.ensure_root()
        return sum(1 for name in os.listdir(self.root) if name.endswith(".zec-config.json"))

    def create(
        self,
        manager: Any,
        *,
        name: str,
        description: str = "",
        scope_mode: str = "full_managed",
        categories: Optional[Iterable[str]] = None,
        keys: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        name = _clean_text(name, minimum=1, maximum=_NAME_MAX, code="CONFIG_STATE_NAME_INVALID")
        description = _clean_text(description, minimum=0, maximum=_DESCRIPTION_MAX, code="CONFIG_STATE_DESCRIPTION_INVALID")
        status = manager.status()
        if not status.get("primary_config_valid") or status.get("config_health") != "valid":
            raise ConfigStateError("CONFIG_STATE_CREATE_PRIMARY_CONFIG_INVALID")
        with self._lock:
            if self._count_files() >= MAX_NAMED_STATES:
                raise ConfigStateError("CONFIG_STATE_LIMIT_REACHED")
            state_id = uuid.uuid4().hex
            data = build_bundle(
                manager,
                artifact_kind="named_state",
                scope_mode=scope_mode,
                categories=categories,
                keys=keys,
                name=name,
                description=description,
                include_secrets=False,
            )
            path = self._path(state_id)
            self._atomic_write(path, data)
            item = self._read(state_id)
            return self._summary(item)

    @staticmethod
    def _summary(item: StateRead) -> Dict[str, Any]:
        p = item.bundle.payload
        src = item.bundle.source_metadata
        scope = item.bundle.scope
        return {
            "state_id": item.state_id,
            "state_revision": item.revision,
            "status": "valid",
            "name": str(p.get("name") or ""),
            "description": str(p.get("description") or ""),
            "created_at": p.get("created_at"),
            "source_app_version": src.get("app_version"),
            "source_app_build_id": src.get("app_build_id"),
            "registry_schema_version": src.get("settings_registry_schema_version"),
            "scope_mode": scope.get("mode"),
            "scope_key_count": len(scope.get("keys") or []),
            "secrets_included": False,
        }

    def list(self) -> Dict[str, Any]:
        self.ensure_root()
        items = []
        with self._lock:
            for name in sorted(os.listdir(self.root)):
                if not name.endswith(".zec-config.json"):
                    continue
                state_id = name[:-len(".zec-config.json")]
                if not _STATE_ID_RE.fullmatch(state_id):
                    continue
                try:
                    items.append(self._summary(self._read(state_id)))
                except Exception:
                    path = self._path(state_id)
                    try:
                        with open(path, "rb") as handle:
                            revision = _sha(handle.read(1024 * 1024 + 1))
                    except Exception:
                        revision = ""
                    items.append({
                        "state_id": state_id,
                        "state_revision": revision,
                        "status": "corrupt",
                        "name": "Beschädigter Konfigurationsstand",
                        "description": "",
                    })
        return {"status": "ok", "count": len(items), "limit": MAX_NAMED_STATES, "items": items}

    def patch(self, state_id: str, *, expected_revision: str, name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            item = self._read(state_id)
            if item.revision != str(expected_revision or ""):
                raise ConfigStateError("CONFIG_STATE_REVISION_CONFLICT")
            payload = dict(item.bundle.payload)
            if name is not None:
                payload["name"] = _clean_text(name, minimum=1, maximum=_NAME_MAX, code="CONFIG_STATE_NAME_INVALID")
            if description is not None:
                payload["description"] = _clean_text(description, minimum=0, maximum=_DESCRIPTION_MAX, code="CONFIG_STATE_DESCRIPTION_INVALID")
            data = encode_bundle(payload)
            self._atomic_write(item.path, data)
            return self._summary(self._read(state_id))

    def delete(self, state_id: str, *, expected_revision: str) -> Dict[str, Any]:
        with self._lock:
            item = self._read(state_id)
            if item.revision != str(expected_revision or ""):
                raise ConfigStateError("CONFIG_STATE_REVISION_CONFLICT")
            os.unlink(item.path)
            dirfd = os.open(self.root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
            return {"status": "deleted", "state_id": state_id}

    def export_bytes(self, state_id: str, *, expected_revision: Optional[str] = None) -> bytes:
        with self._lock:
            item = self._read(state_id)
            if expected_revision is not None and item.revision != str(expected_revision):
                raise ConfigStateError("CONFIG_STATE_REVISION_CONFLICT")
            return bytes(item.data)
