#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

"""
Zendure SolarFlow 2400 AC+ Controller - Version 12.8.4

Start:
    python3 ZendureController.py

Webinterface:
    http://<raspberry-ip>:8080
"""
import os
import sys
import threading
import signal

from version import APP_BUILD_ID, APP_VERSION_LABEL
from instance_owner import INSTANCE_LOCK_EXIT_CODE, InstanceLockHeldError, acquire_instance_lock



def main() -> None:
    try:
        instance_lock = acquire_instance_lock(build_id=APP_BUILD_ID)
    except InstanceLockHeldError as exc:
        print("[STARTUP] Zweite Zendure-Controllerinstanz abgewiesen; produktive Ownership ist bereits belegt.")
        print(f"[STARTUP] Globaler Instance-Lock: {exc.path}")
        if exc.owner:
            print(f"[STARTUP] Aktiver Owner: {exc.owner}")
        raise SystemExit(INSTANCE_LOCK_EXIT_CODE)

    # Runtime-/I/O-Komponenten werden absichtlich erst nach erfolgreicher
    # produktiver Ownership geladen. Damit kann eine abgewiesene Zweitinstanz
    # weder durch Import-Nebenwirkungen noch durch Initialisierung einen
    # produktiven Pfad eröffnen.
    import uvicorn
    from app_logger import RotatingAppLogger
    from config_manager import ConfigManager
    from controller_logic import ZendureController
    from csv_logger import CsvRotatingLogger
    from mqtt_bridge import MqttBridge
    from shelly_client import ShellyClient
    from sma_energy_meter import SmaEnergyMeterClient
    from state import ControllerState
    from web_ui import create_app
    from zendure_local_api import ZendureLocalApiClient

    config_manager = ConfigManager("config.json")
    config = config_manager.load()

    app_logger = RotatingAppLogger()
    app_logger.log(config, f"[STARTUP] Zendure Energy Controller {APP_VERSION_LABEL} startet")
    app_logger.log(config, f"[INSTANCE] produktiver Owner pid={instance_lock.pid} build={instance_lock.build_id} lock={instance_lock.path}")

    state = ControllerState()
    with state.lock:
        state.instance_owner_active = True
        state.instance_owner_pid = instance_lock.pid
        state.instance_owner_build_id = instance_lock.build_id
        state.instance_owner_since_utc = instance_lock.started_time_utc
        state.instance_owner_lock_path = instance_lock.path
    state.ensure_graph_limit(int(config.get("GRAPH_HISTORY_LIMIT", 300)))

    mqtt_bridge = MqttBridge(state, config_manager.get, app_logger=app_logger)
    mqtt_bridge.start()

    controller = ZendureController(
        config_manager=config_manager,
        state=state,
        mqtt_bridge=mqtt_bridge,
        shelly_client=ShellyClient(),
        csv_logger=CsvRotatingLogger(),
        zendure_api_client=ZendureLocalApiClient(),
        app_logger=app_logger,
        sma_energy_meter_client=SmaEnergyMeterClient(),
    )

    app = create_app(
        config_manager=config_manager,
        state=state,
    )

    def request_shutdown(signum, frame) -> None:  # type: ignore[no-untyped-def]
        app_logger.log(config_manager.get(), f"[SHUTDOWN] Signal {signum} empfangen, Controller wird sauber beendet")
        controller.request_stop()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    def run_webserver() -> None:
        cfg = config_manager.get()
        uvicorn.run(
            app,
            host=str(cfg.get("WEB_HOST", "0.0.0.0")),
            port=int(cfg.get("WEB_PORT", 8080)),
            log_level="warning",
        )

    web_thread = threading.Thread(target=run_webserver, daemon=True)
    web_thread.start()

    print("")
    print("===================================================")
    print(f" Zendure Energy Controller {APP_VERSION_LABEL} gestartet")
    print(f" Webinterface:  http://0.0.0.0:{config.get('WEB_PORT', 8080)}")
    print(" API Docs:      /docs")
    print("===================================================")
    print("")

    try:
        controller.run_forever()
    finally:
        try:
            controller.close()
        except Exception:
            pass
        try:
            instance_lock.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
