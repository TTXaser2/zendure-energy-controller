#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Deprecated compatibility entry point. V16 canonical name is install_zendure_controller.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "HINWEIS: update_zendure_controller.sh ist ab V16 veraltet; verwende install_zendure_controller.sh." >&2
exec "$SCRIPT_DIR/install_zendure_controller.sh" "$@"
