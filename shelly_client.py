# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Eduard Fuchs <info@eduardfuchs.de>
#
# This file is part of Zendure Energy Controller.
# See LICENSE, NOTICE and DISCLAIMER.md for license, attribution and warranty information.

import requests
from typing import Dict, Any


class ShellyClient:
    def __init__(self) -> None:
        self.session = requests.Session()

    def read_grid_power(self, config: Dict[str, Any]) -> float:
        url = f"http://{config['SHELLY_IP']}/rpc/Shelly.GetStatus"
        response = self.session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if config.get("LOG_RAW_RESPONSE", False):
            print(f"[RAW] {data}")

        return float(data["em:0"]["total_act_power"])
