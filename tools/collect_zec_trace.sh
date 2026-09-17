#!/usr/bin/env bash
set -u

# Collect a compact Zendure Energy Controller trace bundle as a single text file.
# Designed for quick support/debug runs on the Raspberry Pi. No config.json is dumped.

INSTALL_DIR="/opt/zendure-controller"
LOG_DIR="/opt/zendure-controller/logs"
OUTPUT_DIR="/home/pi/Downloads"
LINES_JOURNAL_CONTROLLER=300
LINES_JOURNAL_REPLAY=160
LINES_RUNTIME=240
PAUSE=0
INCLUDE_SENSITIVE=0

usage() {
  cat <<'USAGE'
Usage: collect_zec_trace.sh [options]

Options:
  --output-dir DIR         Output directory. Default: /home/pi/Downloads
  --install-dir DIR        ZEC install directory. Default: /opt/zendure-controller
  --log-dir DIR            Runtime log directory. Default: /opt/zendure-controller/logs
  --journal-lines N        Controller journal lines. Default: 300
  --runtime-lines N        Runtime log lines. Default: 240
  --include-sensitive      Do not redact status JSON fields such as serial/user/token keys
  --pause                  Wait for Enter before exit, useful for desktop launchers
  -h, --help               Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    --install-dir) INSTALL_DIR="${2:-}"; shift 2 ;;
    --log-dir) LOG_DIR="${2:-}"; shift 2 ;;
    --journal-lines) LINES_JOURNAL_CONTROLLER="${2:-300}"; shift 2 ;;
    --runtime-lines) LINES_RUNTIME="${2:-240}"; shift 2 ;;
    --include-sensitive) INCLUDE_SENSITIVE=1; shift ;;
    --pause) PAUSE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

mkdir -p "$OUTPUT_DIR" 2>/dev/null || OUTPUT_DIR="$HOME"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="$OUTPUT_DIR/zec_trace_$TS.txt"
LATEST="$OUTPUT_DIR/zec_trace_latest.txt"
DEFAULT_WEB_PORT=8080
BASE_URL="http://127.0.0.1:${DEFAULT_WEB_PORT}"
if [[ -f "$INSTALL_DIR/tools/deployment_contract.py" ]]; then
  resolved="$(python3 "$INSTALL_DIR/tools/deployment_contract.py" endpoint --target "$INSTALL_DIR" --json 2>/dev/null || true)"
  if [[ -n "$resolved" ]]; then
    BASE_URL="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("base_url",f"http://127.0.0.1:{sys.argv[2]}"))' "$resolved" "$DEFAULT_WEB_PORT" 2>/dev/null || echo "http://127.0.0.1:${DEFAULT_WEB_PORT}")"
  fi
fi

section() {
  echo
  echo "===== $* ====="
}

run_cmd() {
  local label="$1"; shift
  section "$label"
  "$@" 2>&1 || true
}


http_timing() {
  local url="$1"
  local tmp="/tmp/zec_trace_http_$$.out"
  echo "--- $url ---"
  curl -o "$tmp" -sS \
    -w "http=%{http_code} time_total=%{time_total}s time_connect=%{time_connect}s time_starttransfer=%{time_starttransfer}s size=%{size_download} bytes\n" \
    "$url" 2>&1 || true
  echo "first_bytes:"
  if [[ -f "$tmp" ]]; then
    head -c 500 "$tmp" || true
    echo
    rm -f "$tmp"
  else
    echo "(keine Ausgabedatei)"
  fi
}

redacted_status_json() {
  local url="$1"
  local include_sensitive="$2"
  python3 - "$url" "$include_sensitive" <<'PY' 2>&1 || true
import json
import sys
import urllib.request

url = sys.argv[1]
include_sensitive = sys.argv[2] == "1"
try:
    with urllib.request.urlopen(url, timeout=4) as r:
        payload = r.read().decode("utf-8", errors="replace")
except Exception as exc:
    print(f"REQUEST_FAILED: {exc}")
    raise SystemExit(0)
try:
    data = json.loads(payload)
except Exception:
    print(payload[:8000])
    raise SystemExit(0)

sensitive_fragments = ("password", "passwd", "secret", "token", "username", "user_name", "serial")

def scrub(obj):
    if include_sensitive:
        return obj
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(frag in lk for frag in sensitive_fragments):
                out[k] = "<redacted>"
            else:
                out[k] = scrub(v)
        return out
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj

print(json.dumps(scrub(data), ensure_ascii=False, indent=2, sort_keys=True)[:20000])
PY
}

{
  echo "ZEC Trace"
  echo "Created: $(date -Is)"
  echo "Host: $(hostname 2>/dev/null || true)"
  echo "Output: $OUT"
  echo "Sensitive redaction: $([[ $INCLUDE_SENSITIVE -eq 1 ]] && echo disabled || echo enabled)"

  run_cmd "SYSTEM / UNAME" uname -a
  run_cmd "SYSTEM / UPTIME" uptime
  run_cmd "SYSTEM / DATE" date -Is
  run_cmd "PYTHON" python3 --version

  if command -v vcgencmd >/dev/null 2>&1; then
    run_cmd "PI / THROTTLED" vcgencmd get_throttled
    run_cmd "PI / TEMPERATURE" vcgencmd measure_temp
  else
    section "PI / VCGENCMD"
    echo "vcgencmd not available"
  fi

  run_cmd "VERSION FILE" cat "$INSTALL_DIR/version.py"
  run_cmd "SERVICE / CONTROLLER STATUS" systemctl status zendure-controller.service --no-pager -l
  run_cmd "SERVICE / REPLAY STATUS" systemctl status zendure-replay.service --no-pager -l
  run_cmd "SERVICE / CONTROLLER IS-ACTIVE" systemctl is-active zendure-controller.service
  run_cmd "SERVICE / REPLAY IS-ACTIVE" systemctl is-active zendure-replay.service

  run_cmd "JOURNAL / CONTROLLER LAST $LINES_JOURNAL_CONTROLLER" journalctl -u zendure-controller -n "$LINES_JOURNAL_CONTROLLER" --no-pager -l
  run_cmd "JOURNAL / REPLAY LAST $LINES_JOURNAL_REPLAY" journalctl -u zendure-replay -n "$LINES_JOURNAL_REPLAY" --no-pager -l

  run_cmd "RUNTIME LOG LAST $LINES_RUNTIME" tail -n "$LINES_RUNTIME" "$LOG_DIR/zendure_runtime.log"
  run_cmd "RUNTIME LOG DIRECTORY" ls -lah "$LOG_DIR"

  run_cmd "DISK / DF" df -h
  run_cmd "MOUNTS / ZEC USB" findmnt /mnt/zec-usb
  run_cmd "MOUNTS / ALL RELEVANT" sh -c 'findmnt | grep -E "zec|media/pi|/mnt/zec|/opt|/home" || true'

  run_cmd "NETWORK / IP ADDR BRIEF" sh -c 'ip -brief addr 2>/dev/null || ip addr'

  section "HTTP / READY"
  redacted_status_json "${BASE_URL}/ready" "$INCLUDE_SENSITIVE"

  section "HTTP / STATUS REDACTED"
  redacted_status_json "${BASE_URL}/status" "$INCLUDE_SENSITIVE"

  section "HTTP / ENDPOINT TIMINGS"
  http_timing "${BASE_URL}/"
  http_timing "${BASE_URL}/status"
  http_timing "${BASE_URL}/soc-day-data"
  http_timing "${BASE_URL}/graph"
  http_timing "${BASE_URL}/api/graph/v1/runtime"
  http_timing "${BASE_URL}/api/graph/v1/workspace"
  http_timing "${BASE_URL}/grid-mini-sparkline"
  http_timing "${BASE_URL}/measurement-db-status"

  section "HTTP / MEASUREMENT DB STATUS"
  redacted_status_json "${BASE_URL}/measurement-db-status" "$INCLUDE_SENSITIVE"

  section "RECENT DOWNLOAD ZIPS"
  ls -lah "$HOME/Downloads"/zendure_controller_*.zip 2>/dev/null | tail -n 20 || true
} > "$OUT" 2>&1

cp "$OUT" "$LATEST" 2>/dev/null || true

echo
echo "ZEC Trace erstellt:"
echo "$OUT"
if [[ -f "$LATEST" ]]; then
  echo "Kopie/Alias: $LATEST"
fi
echo

if [[ $PAUSE -eq 1 ]]; then
  read -r -p "Enter drücken zum Schließen..."
fi
