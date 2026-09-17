#!/usr/bin/env bash
# Secretsafe manual crash/support bundle. Raw config.json is never copied.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAUSE=0; OUT_DIR="${HOME}/Downloads"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pause) PAUSE=1; shift;;
    --output-dir) OUT_DIR="$2"; shift 2;;
    -h|--help) echo "Usage: collect_zec_crash_package.sh [--pause] [--output-dir DIR]"; exit 0;;
    *) echo "Unbekannte Option: $1" >&2; exit 2;;
  esac
done
ZIP="$(python3 "$SCRIPT_DIR/zec_support_bundle.py" collect --label crash --output-dir "$OUT_DIR" --stage manual_crash | tail -n1)"
echo "Crash-/Supportpaket erstellt:"
echo "$ZIP"
[[ $PAUSE -eq 1 ]] && read -r -p "Enter drücken zum Schließen..."
