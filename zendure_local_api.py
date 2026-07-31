# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace
from typing import Any, Dict, Optional, Tuple

import requests


WORKER_DISABLED = "DISABLED"
WORKER_IDLE = "IDLE"
WORKER_REQUESTING = "REQUESTING"
WORKER_BACKOFF = "BACKOFF"
WORKER_STOPPING = "STOPPING"
WORKER_STOPPED = "STOPPED"


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


@dataclass(frozen=True)
class ZendureLocalApiConfigSnapshot:
    generation: int
    use_for_telemetry: bool
    local_ip: str
    poll_interval_s: float
    configured_timeout_s: float
    effective_timeout_s: float
    error_backoff_s: float
    soc_priority: str
    fallback_only: bool
    device_id: str

    @property
    def enabled(self) -> bool:
        return bool(self.use_for_telemetry and self.local_ip)

    @classmethod
    def from_config(cls, config: Dict[str, Any], generation: int) -> "ZendureLocalApiConfigSnapshot":
        configured_timeout = max(0.2, float(config.get("ZENDURE_LOCAL_API_TIMEOUT_SECONDS", 5) or 5))
        timeout_cap = max(0.2, float(config.get("ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS", 1.5) or 1.5))
        return cls(
            generation=int(generation),
            use_for_telemetry=bool(config.get("ZENDURE_LOCAL_API_USE_FOR_TELEMETRY", False)),
            local_ip=str(config.get("ZENDURE_LOCAL_IP", "") or "").strip(),
            poll_interval_s=max(1.0, float(config.get("ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS", 5) or 5)),
            configured_timeout_s=configured_timeout,
            effective_timeout_s=max(0.2, min(configured_timeout, timeout_cap)),
            error_backoff_s=max(0.0, float(config.get("ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS", 30) or 0)),
            soc_priority=str(config.get("ZENDURE_LOCAL_API_SOC_PRIORITY", "properties_first") or "properties_first"),
            fallback_only=bool(config.get("ZENDURE_LOCAL_API_TELEMETRY_FALLBACK_ONLY", True)),
            device_id=str(config.get("DEVICE_ID", "") or ""),
        )

    def as_request_config(self) -> Dict[str, Any]:
        return {
            "ZENDURE_LOCAL_IP": self.local_ip,
            "ZENDURE_LOCAL_API_TIMEOUT_SECONDS": self.configured_timeout_s,
            "ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS": self.effective_timeout_s,
        }


@dataclass(frozen=True)
class ZendurePackSnapshot:
    pack_sn: str
    temperature_c: Optional[float] = None
    temperature_raw: Any = None
    power_w: Optional[int] = None
    soc_percent: Optional[int] = None
    state: Any = None


@dataclass(frozen=True)
class ZendureLocalApiSuccessfulData:
    device_sn: str
    electric_level: Optional[int]
    pack_soc_level: Optional[int]
    selected_api_soc: Optional[int]
    pack_input_power_w: Optional[int]
    output_home_power_w: Optional[int]
    grid_input_power_w: Optional[int]
    output_pack_power_w: Optional[int]
    grid_off_power_w: Optional[int]
    solar_input_power_w: Optional[int]
    smart_mode: Optional[int]
    ac_mode: Any
    input_limit_w: Optional[int]
    output_limit_w: Optional[int]
    inverse_max_power_w: Optional[int]
    charge_max_limit_w: Optional[int]
    grid_off_mode: Any
    headunit_temperature_c: Optional[float]
    headunit_temperature_raw: Any
    packs: Tuple[ZendurePackSnapshot, ...]
    parse_warnings: Tuple[str, ...]


@dataclass(frozen=True)
class ZendureLocalApiSnapshot:
    snapshot_sequence: int = 0
    data_success_sequence: int = 0
    config_generation: int = 0
    worker_state: str = WORKER_DISABLED
    latest_attempt_ok: Optional[bool] = None
    last_attempt_wall_epoch: Optional[float] = None
    last_attempt_monotonic: Optional[float] = None
    last_success_wall_epoch: Optional[float] = None
    last_success_monotonic: Optional[float] = None
    request_duration_ms: Optional[float] = None
    consecutive_error_count: int = 0
    backoff_until_monotonic: Optional[float] = None
    latest_error_code: str = "NONE"
    latest_error_text: str = ""
    latest_parse_warning_count: int = 0
    successful_data: Optional[ZendureLocalApiSuccessfulData] = None
    successful_data_config_generation: int = 0

    def backoff_remaining_s(self, now_monotonic: Optional[float] = None) -> float:
        if self.backoff_until_monotonic is None:
            return 0.0
        now = time.monotonic() if now_monotonic is None else float(now_monotonic)
        return max(0.0, float(self.backoff_until_monotonic) - now)

    @property
    def parse_warning_count(self) -> int:
        return max(0, int(self.latest_parse_warning_count or 0))


class ZendureLocalApiClient:
    """Read-only HTTP transport for the local Zendure API.

    RC18 keeps the historical synchronous methods for the manual diagnostic
    endpoint and regression tests. The live controller uses ``fetch_report_once``
    exclusively from ``ZendureLocalApiWorker``; therefore the transport session
    is never shared between controller and worker threads.
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        # Legacy synchronous scheduling state. The RC18 worker does not use it.
        self.last_poll_epoch: Optional[float] = None
        self.backoff_until_epoch: Optional[float] = None
        self.consecutive_error_count: int = 0

    @staticmethod
    def effective_timeout(config: Dict[str, Any]) -> float:
        configured_timeout = float(config.get("ZENDURE_LOCAL_API_TIMEOUT_SECONDS", 5) or 5)
        timeout_cap = float(config.get("ZENDURE_LOCAL_API_CONTROL_TIMEOUT_CAP_SECONDS", 1.5) or 1.5)
        return max(0.2, min(configured_timeout, timeout_cap))

    def should_poll(self, config: Dict[str, Any]) -> bool:
        if not config.get("ZENDURE_LOCAL_API_USE_FOR_TELEMETRY", False):
            return False
        if not str(config.get("ZENDURE_LOCAL_IP", "")).strip():
            return False
        now = time.time()
        if self.backoff_until_epoch is not None and now < self.backoff_until_epoch:
            return False
        interval = max(1, int(config.get("ZENDURE_LOCAL_API_POLL_INTERVAL_SECONDS", 5)))
        if self.last_poll_epoch is None:
            return True
        return (now - self.last_poll_epoch) >= interval

    def fetch_report_once(self, config: Dict[str, Any]) -> Dict[str, Any]:
        ip = str(config.get("ZENDURE_LOCAL_IP", "") or "").strip()
        if not ip:
            raise RuntimeError("ZENDURE_LOCAL_IP ist leer")
        url = f"http://{ip}/properties/report"
        response = self.session.get(url, timeout=self.effective_timeout(config))
        response.raise_for_status()
        try:
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"Ungültige JSON-Antwort von {url}: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"Ungültige JSON-Struktur von {url}: Objekt erwartet")
        return payload

    def fetch_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        self.last_poll_epoch = time.time()
        try:
            payload = self.fetch_report_once(config)
        except Exception:
            self._register_failure(config)
            raise
        self.consecutive_error_count = 0
        self.backoff_until_epoch = None
        return payload

    def _register_failure(self, config: Dict[str, Any]) -> None:
        self.consecutive_error_count += 1
        backoff = max(0, int(config.get("ZENDURE_LOCAL_API_ERROR_BACKOFF_SECONDS", 30) or 0))
        if backoff > 0:
            self.backoff_until_epoch = time.time() + backoff

    def recreate_session(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass
        self.session = requests.Session()

    def close_session(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass


class ZendureLocalApiWorker:
    """Single-threaded, latest-only worker for ``/properties/report``.

    The worker performs HTTP and parsing only. It never writes ControllerState,
    publishes MQTT commands or performs controller decisions.
    """

    def __init__(self, client: ZendureLocalApiClient, config: Dict[str, Any]) -> None:
        self._client = client
        self._config_lock = threading.Lock()
        self._snapshot_lock = threading.Lock()
        self._config = ZendureLocalApiConfigSnapshot.from_config(config, generation=1)
        initial_state = WORKER_IDLE if self._config.enabled else WORKER_DISABLED
        self._snapshot = ZendureLocalApiSnapshot(
            config_generation=self._config.generation,
            worker_state=initial_state,
        )
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def config_generation(self) -> int:
        with self._config_lock:
            return self._config.generation

    def current_config(self) -> ZendureLocalApiConfigSnapshot:
        with self._config_lock:
            return self._config

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._wake.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="zec-zendure-local-api",
            daemon=True,
        )
        self._thread.start()

    def is_alive(self) -> bool:
        return bool(self._thread is not None and self._thread.is_alive())

    def request_stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def join_timeout_s(self) -> float:
        cfg = self.current_config()
        return max(1.0, min(3.0, float(cfg.effective_timeout_s) + 0.75))

    def update_config(self, config: Dict[str, Any]) -> int:
        with self._config_lock:
            current = self._config
            candidate = ZendureLocalApiConfigSnapshot.from_config(config, generation=current.generation)
            if replace(candidate, generation=0) == replace(current, generation=0):
                return current.generation
            self._config = replace(candidate, generation=current.generation + 1)
            generation = self._config.generation
        self._wake.set()
        return generation

    def latest_snapshot(self) -> ZendureLocalApiSnapshot:
        with self._snapshot_lock:
            return self._snapshot

    def _publish(self, **changes: Any) -> ZendureLocalApiSnapshot:
        with self._snapshot_lock:
            current = self._snapshot
            changes["snapshot_sequence"] = current.snapshot_sequence + 1
            self._snapshot = replace(current, **changes)
            return self._snapshot

    def _get_config(self) -> ZendureLocalApiConfigSnapshot:
        with self._config_lock:
            return self._config

    def _wait(self, timeout_s: float) -> None:
        if timeout_s <= 0:
            return
        self._wake.wait(timeout=max(0.01, float(timeout_s)))
        self._wake.clear()

    def _run(self) -> None:
        cfg = self._get_config()
        active_generation = cfg.generation
        active_ip = cfg.local_ip
        next_poll_monotonic = time.monotonic()
        self._publish(
            config_generation=cfg.generation,
            worker_state=WORKER_IDLE if cfg.enabled else WORKER_DISABLED,
            latest_error_code="NONE",
            latest_error_text="",
        )
        try:
            while not self._stop.is_set():
                cfg = self._get_config()
                if cfg.generation != active_generation:
                    if cfg.local_ip != active_ip:
                        self._client.recreate_session()
                    active_generation = cfg.generation
                    active_ip = cfg.local_ip
                    next_poll_monotonic = time.monotonic()

                if not cfg.enabled:
                    snap = self.latest_snapshot()
                    if snap.worker_state != WORKER_DISABLED or snap.config_generation != cfg.generation:
                        self._publish(
                            config_generation=cfg.generation,
                            worker_state=WORKER_DISABLED,
                            latest_error_code="NONE",
                            latest_error_text="",
                            backoff_until_monotonic=None,
                        )
                    self._wait(1.0)
                    continue

                now_monotonic = time.monotonic()
                snap = self.latest_snapshot()
                backoff_until = snap.backoff_until_monotonic
                if backoff_until is not None and now_monotonic < backoff_until:
                    if snap.worker_state != WORKER_BACKOFF:
                        self._publish(worker_state=WORKER_BACKOFF, config_generation=cfg.generation)
                    self._wait(min(1.0, backoff_until - now_monotonic))
                    continue

                if now_monotonic < next_poll_monotonic:
                    if snap.worker_state not in {WORKER_IDLE, WORKER_BACKOFF}:
                        self._publish(worker_state=WORKER_IDLE, config_generation=cfg.generation)
                    self._wait(min(1.0, next_poll_monotonic - now_monotonic))
                    continue

                request_cfg = cfg
                request_generation = cfg.generation
                self._publish(worker_state=WORKER_REQUESTING, config_generation=request_generation)
                started_wall = time.time()
                started_monotonic = time.monotonic()
                try:
                    payload = self._client.fetch_report_once(request_cfg.as_request_config())
                    parsed = parse_local_api_report(payload, request_cfg)
                    finished_wall = time.time()
                    finished_monotonic = time.monotonic()
                    duration_ms = (finished_monotonic - started_monotonic) * 1000.0
                    current_cfg = self._get_config()
                    if current_cfg.generation != request_generation:
                        self._publish(
                            config_generation=current_cfg.generation,
                            worker_state=WORKER_IDLE if current_cfg.enabled else WORKER_DISABLED,
                            latest_attempt_ok=False,
                            last_attempt_wall_epoch=finished_wall,
                            last_attempt_monotonic=finished_monotonic,
                            request_duration_ms=duration_ms,
                            latest_error_code="SUPERSEDED_CONFIG",
                            latest_error_text="Ergebnis wegen neuer Configgeneration verworfen.",
                            latest_parse_warning_count=0,
                            backoff_until_monotonic=None,
                        )
                        next_poll_monotonic = finished_monotonic
                        continue
                    prior = self.latest_snapshot()
                    self._publish(
                        config_generation=request_generation,
                        worker_state=WORKER_IDLE,
                        latest_attempt_ok=True,
                        last_attempt_wall_epoch=finished_wall,
                        last_attempt_monotonic=finished_monotonic,
                        last_success_wall_epoch=finished_wall,
                        last_success_monotonic=finished_monotonic,
                        request_duration_ms=duration_ms,
                        consecutive_error_count=0,
                        backoff_until_monotonic=None,
                        latest_error_code="NONE",
                        latest_error_text="",
                        latest_parse_warning_count=len(parsed.parse_warnings),
                        successful_data=parsed,
                        successful_data_config_generation=request_generation,
                        data_success_sequence=prior.data_success_sequence + 1,
                    )
                    next_poll_monotonic = finished_monotonic + request_cfg.poll_interval_s
                except Exception as exc:
                    finished_wall = time.time()
                    finished_monotonic = time.monotonic()
                    duration_ms = (finished_monotonic - started_monotonic) * 1000.0
                    current_cfg = self._get_config()
                    if current_cfg.generation != request_generation:
                        self._publish(
                            config_generation=current_cfg.generation,
                            worker_state=WORKER_IDLE if current_cfg.enabled else WORKER_DISABLED,
                            latest_attempt_ok=False,
                            last_attempt_wall_epoch=finished_wall,
                            last_attempt_monotonic=finished_monotonic,
                            request_duration_ms=duration_ms,
                            latest_error_code="SUPERSEDED_CONFIG",
                            latest_error_text="Fehler eines veralteten Requests verworfen.",
                            latest_parse_warning_count=0,
                            backoff_until_monotonic=None,
                        )
                        next_poll_monotonic = finished_monotonic
                        continue
                    prior = self.latest_snapshot()
                    errors = prior.consecutive_error_count + 1
                    backoff_until = (
                        finished_monotonic + request_cfg.error_backoff_s
                        if request_cfg.error_backoff_s > 0
                        else None
                    )
                    self._publish(
                        config_generation=request_generation,
                        worker_state=WORKER_BACKOFF if backoff_until is not None else WORKER_IDLE,
                        latest_attempt_ok=False,
                        last_attempt_wall_epoch=finished_wall,
                        last_attempt_monotonic=finished_monotonic,
                        request_duration_ms=duration_ms,
                        consecutive_error_count=errors,
                        backoff_until_monotonic=backoff_until,
                        latest_error_code=classify_local_api_error(exc),
                        latest_error_text=str(exc)[:500],
                        latest_parse_warning_count=0,
                    )
                    next_poll_monotonic = finished_monotonic + request_cfg.poll_interval_s
        finally:
            self._publish(worker_state=WORKER_STOPPING)
            self._client.close_session()
            self._publish(worker_state=WORKER_STOPPED)


def classify_local_api_error(exc: Exception) -> str:
    if isinstance(exc, requests.Timeout):
        return "TIMEOUT"
    if isinstance(exc, requests.ConnectionError):
        return "CONNECTION_ERROR"
    if isinstance(exc, requests.HTTPError):
        return "HTTP_ERROR"
    text = str(exc).lower()
    if "json" in text:
        return "JSON_ERROR"
    return "REQUEST_ERROR"


def parse_local_api_report(
    report: Dict[str, Any],
    config: ZendureLocalApiConfigSnapshot,
) -> ZendureLocalApiSuccessfulData:
    warnings = []
    props = report.get("properties", {}) if isinstance(report, dict) else {}
    if not isinstance(props, dict):
        warnings.append("properties_not_object")
        props = {}
    pack_data = report.get("packData", []) if isinstance(report, dict) else []
    if not isinstance(pack_data, list):
        warnings.append("packData_not_list")
        pack_data = []
    first_pack = pack_data[0] if pack_data and isinstance(pack_data[0], dict) else {}

    electric_level = _safe_int(props.get("electricLevel"))
    pack_soc = _safe_int(first_pack.get("socLevel"))
    if config.soc_priority == "pack_first":
        api_soc = pack_soc if pack_soc is not None else electric_level
    else:
        api_soc = electric_level if electric_level is not None else pack_soc

    parsed_packs = []
    for idx, pack in enumerate(pack_data[:8]):
        if not isinstance(pack, dict):
            warnings.append(f"pack_{idx+1}_not_object")
            continue
        parsed_packs.append(ZendurePackSnapshot(
            pack_sn=str(pack.get("sn", f"pack-{idx+1}")),
            temperature_c=zendure_temp_to_celsius(pack.get("maxTemp")),
            temperature_raw=pack.get("maxTemp"),
            power_w=_safe_int(pack.get("power")),
            soc_percent=_safe_int(pack.get("socLevel")),
            state=pack.get("state"),
        ))
    if len(pack_data) > 8:
        warnings.append("pack_limit_8_applied")

    warnings = tuple(str(item)[:160] for item in warnings[:16])
    return ZendureLocalApiSuccessfulData(
        device_sn=str(report.get("sn", config.device_id) or config.device_id or "headunit"),
        electric_level=electric_level,
        pack_soc_level=pack_soc,
        selected_api_soc=api_soc,
        pack_input_power_w=_safe_int(props.get("packInputPower")),
        output_home_power_w=_safe_int(props.get("outputHomePower")),
        grid_input_power_w=_safe_int(props.get("gridInputPower")),
        output_pack_power_w=_safe_int(props.get("outputPackPower")),
        grid_off_power_w=_safe_int(props.get("gridOffPower")),
        solar_input_power_w=_safe_int(props.get("solarInputPower")),
        smart_mode=_safe_int(props.get("smartMode")),
        ac_mode=props.get("acMode"),
        input_limit_w=_safe_int(props.get("inputLimit")),
        output_limit_w=_safe_int(props.get("outputLimit")),
        inverse_max_power_w=_safe_int(props.get("inverseMaxPower")),
        charge_max_limit_w=_safe_int(props.get("chargeMaxLimit")),
        grid_off_mode=props.get("gridOffMode"),
        headunit_temperature_c=zendure_temp_to_celsius(props.get("hyperTmp")),
        headunit_temperature_raw=props.get("hyperTmp"),
        packs=tuple(parsed_packs),
        parse_warnings=warnings,
    )


def zendure_temp_to_celsius(value: Any) -> Optional[float]:
    """Normalize Zendure temperature values to Celsius."""
    if value is None:
        return None
    try:
        raw = float(value)
    except Exception:
        return None
    if -40.0 <= raw <= 120.0:
        return round(raw, 1)
    if 250.0 <= raw <= 400.0:
        return round(raw - 273.15, 1)
    if 2500.0 <= raw <= 4000.0:
        return round((raw / 10.0) - 273.15, 1)
    return None
