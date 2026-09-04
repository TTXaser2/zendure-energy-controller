#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="${HOME}/Downloads"
LABEL="install"
SINCE_EPOCH=""
CONFIG="/opt/zendure-controller/config.json"
CUTOVER_REPORT=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output-dir) OUT_DIR="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --since-epoch) SINCE_EPOCH="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    --cutover-report) CUTOVER_REPORT="$2"; shift 2 ;;
    *) echo "Unbekannte Option: $1" >&2; exit 2 ;;
  esac
done

TS="$(date +%Y%m%d_%H%M%S)"
SAFE_LABEL="$(printf '%s' "$LABEL" | tr -c 'A-Za-z0-9._-' '_')"
WORK="${OUT_DIR}/zec_${SAFE_LABEL}_diagnostics_${TS}"
ARCHIVE="${OUT_DIR}/zec_${SAFE_LABEL}_diagnostics_${TS}.tar.gz"
mkdir -p "$WORK" "$OUT_DIR"

run_shell() {
  local name="$1"; shift
  {
    echo "===== ${name} ====="
    echo "Command: $*"
    echo
    bash -lc "$*" 2>&1
  } >"${WORK}/${name}.txt"
}

safe_copy() {
  local src="$1" dst="$2"
  if [ -f "$src" ]; then cp -a "$src" "${WORK}/${dst}" 2>/dev/null || true; fi
}

run_shell date 'date -Is'
run_shell uname 'uname -a'
run_shell uptime 'uptime'
run_shell free 'free -h'
run_shell df 'df -hT'
run_shell lsblk 'lsblk -f'
run_shell findmnt 'findmnt'
run_shell controller_status 'systemctl status zendure-controller.service --no-pager -l || true'
run_shell replay_status 'systemctl status zendure-replay.service --no-pager -l || true'
run_shell mosquitto_status 'systemctl status mosquitto.service --no-pager -l || true'
run_shell evcc_status 'systemctl status evcc.service --no-pager -l || true'

if [ -n "$SINCE_EPOCH" ]; then
  run_shell controller_journal "journalctl -u zendure-controller.service --since '@${SINCE_EPOCH}' --no-pager -l || true"
else
  run_shell controller_journal 'journalctl -u zendure-controller.service -b -n 800 --no-pager -l || true'
fi
run_shell kernel_recent 'journalctl -k -b -n 600 --no-pager -l || true'
run_shell system_warnings 'journalctl -p warning..alert -b -n 600 --no-pager -l || true'
run_shell zec_health 'curl -sS --connect-timeout 1 --max-time 5 http://127.0.0.1:8080/health | python3 -m json.tool || true'
run_shell zec_ready 'curl -sS --connect-timeout 1 --max-time 5 http://127.0.0.1:8080/ready | python3 -m json.tool || true'
run_shell graph_runtime 'curl -sS --connect-timeout 1 --max-time 5 http://127.0.0.1:8080/api/graph/v1/runtime | python3 -m json.tool || true'
run_shell graph_workspace 'curl -sS --connect-timeout 1 --max-time 5 http://127.0.0.1:8080/api/graph/v1/workspace | python3 -m json.tool || true'
run_shell installed_identity "grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' /opt/zendure-controller/version.py 2>/dev/null || true"
run_shell package_identity "grep -E 'APP_VERSION|APP_VERSION_LABEL|APP_BUILD_ID' '$PACKAGE_ROOT/version.py' 2>/dev/null || true"

if [ -f "$CONFIG" ]; then
  python3 - "$PACKAGE_ROOT" "$CONFIG" >"${WORK}/config.redacted.json" 2>"${WORK}/config_redaction_error.txt" <<'PY' || true
import json, sys
from pathlib import Path
root=Path(sys.argv[1])
sys.path.insert(0,str(root))
from settings_registry import SETTINGS_BY_KEY
cfg=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
out={}
for key,value in cfg.items():
    spec=SETTINGS_BY_KEY.get(key)
    if spec is not None and getattr(spec,'is_secret',False):
        out[key]={"secret_set": bool(value)}
    else:
        out[key]=value
print(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True))
PY
  python3 "$PACKAGE_ROOT/tools/v14_cutover.py" preflight --config "$CONFIG" --json >"${WORK}/v14_cutover_preflight.json" 2>"${WORK}/v14_cutover_preflight.err" || true
  python3 "$PACKAGE_ROOT/tools/v14_cutover.py" verify --config "$CONFIG" --json >"${WORK}/v14_cutover_verify.json" 2>"${WORK}/v14_cutover_verify.err" || true
fi

for f in /tmp/zec_v14_*.json /tmp/zec_v14_*.err /tmp/zec_v14_*.txt; do
  [ -f "$f" ] && cp -a "$f" "$WORK/" 2>/dev/null || true
done
if [ -n "$CUTOVER_REPORT" ]; then safe_copy "$CUTOVER_REPORT" cutover_report.json; fi
safe_copy /opt/zendure-controller/version.py installed_version.py

cat >"${WORK}/README.txt" <<EOF
ZEC V14 Install/Update Diagnostics
Created: $(date -Is)
Host: $(hostname)
Label: ${LABEL}
Archive: ${ARCHIVE}

This package is created automatically for install/update diagnostics.
Raw config.json is intentionally NOT included. Secret settings are redacted.
Controller readiness and Graph-History readiness are collected separately.
EOF

(
  cd "$OUT_DIR" || exit 1
  tar -czf "$ARCHIVE" "$(basename "$WORK")"
)
chmod 600 "$ARCHIVE" 2>/dev/null || true
printf '%s\n' "$ARCHIVE"
