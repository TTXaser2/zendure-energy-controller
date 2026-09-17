#!/usr/bin/env bash
# Compatibility wrapper. V16 diagnostics are produced by the shared secretsafe core.
# Contract markers retained for audit: config.redacted.json / SETTINGS_BY_KEY / is_secret.
# Raw config.json is intentionally NOT included. /ready and /api/graph/v1/runtime are collected dynamically.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${HOME}/Downloads"; LABEL="install"; SINCE_EPOCH=""; CONFIG="/opt/zendure-controller/config.json"; INSTALL_LOG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUT_DIR="$2"; shift 2;;
    --label) LABEL="$2"; shift 2;;
    --since-epoch) SINCE_EPOCH="$2"; shift 2;;
    --config) CONFIG="$2"; shift 2;;
    --install-log) INSTALL_LOG="$2"; shift 2;;
    --cutover-report) shift 2;;
    *) echo "Unbekannte Option: $1" >&2; exit 2;;
  esac
done
args=(collect --label "$LABEL" --output-dir "$OUT_DIR" --config "$CONFIG" --target /opt/zendure-controller --stage install_diagnostics)
[[ -n "$SINCE_EPOCH" ]] && args+=(--since-epoch "$SINCE_EPOCH")
[[ -n "$INSTALL_LOG" ]] && args+=(--install-log "$INSTALL_LOG")
exec python3 "$SCRIPT_DIR/zec_support_bundle.py" "${args[@]}"
