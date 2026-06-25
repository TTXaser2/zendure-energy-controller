#!/usr/bin/env bash
set -euo pipefail

# Create a Zendure Energy Controller analysis package.
# No config.json or secrets are included.

MEASUREMENT_DIR=""
RUNTIME_DIR="/opt/zendure-controller/logs"
FALLBACK_DIR="/opt/zendure-controller/logs/fallback"
INSTALL_DIR="/opt/zendure-controller"
OUTPUT_DIR="/home/pi/Downloads"
NAME=""
STOP_SERVICES=1
LATEST_ONLY=0
WITH_REPLAY_REPORT=0
NO_FALLBACK_LOGS=0

log() { printf '[zec-export] %s\n' "$*"; }
err() { printf '[zec-export][ERROR] %s\n' "$*" >&2; exit 1; }
warn() { printf '[zec-export][WARN] %s\n' "$*" >&2; }

usage() {
  cat <<'EOF'
Usage: create_zec_analysis_package.sh [options]

Options:
  --measurement-dir DIR   Measurement log directory.
                          Default auto-detects:
                          /media/pi/4CD6-6466/ZEC/logs
                          /media/pi/2.0 GB Volume/ZEC/logs
  --runtime-dir DIR       Runtime log directory. Default: /opt/zendure-controller/logs
  --fallback-dir DIR      Fallback log directory. Default: /opt/zendure-controller/logs/fallback
  --install-dir DIR       ZEC install directory. Default: /opt/zendure-controller
  --output-dir DIR        Output directory. Default: /home/pi/Downloads
  --name NAME             Package base name. Default: zec_analysis_<UTC timestamp>
  --no-stop-services      Do not stop controller/replay services while copying files
  --latest-only           Include only the newest zendure_measurements_v4*.csv file
                          Default includes all zendure_measurements_v4*.csv files
  --with-replay-report    Optional: generate replay_report.txt with timeout and low priority
                          Default skips replay report to protect the Raspberry Pi
  --no-replay-report      Deprecated compatibility option; replay report is skipped by default
  --no-fallback-logs      Do not include fallback log directory
  -h, --help              Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --measurement-dir) MEASUREMENT_DIR="${2:-}"; shift 2 ;;
    --runtime-dir) RUNTIME_DIR="${2:-}"; shift 2 ;;
    --fallback-dir) FALLBACK_DIR="${2:-}"; shift 2 ;;
    --install-dir) INSTALL_DIR="${2:-}"; shift 2 ;;
    --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    --name) NAME="${2:-}"; shift 2 ;;
    --no-stop-services) STOP_SERVICES=0; shift ;;
    --latest-only) LATEST_ONLY=1; shift ;;
    --with-replay-report) WITH_REPLAY_REPORT=1; shift ;;
    --no-replay-report) WITH_REPLAY_REPORT=0; shift ;;
    --no-fallback-logs) NO_FALLBACK_LOGS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) err "Unknown option: $1" ;;
  esac
done

if [[ -z "$MEASUREMENT_DIR" ]]; then
  for candidate in \
    "/media/pi/4CD6-6466/ZEC/logs" \
    "/media/pi/2.0 GB Volume/ZEC/logs"; do
    if [[ -d "$candidate" ]]; then
      MEASUREMENT_DIR="$candidate"
      break
    fi
  done
fi

[[ -n "$MEASUREMENT_DIR" ]] || err "Measurement directory not found. Use --measurement-dir DIR."
[[ -d "$MEASUREMENT_DIR" ]] || err "Measurement directory not found: $MEASUREMENT_DIR"
[[ -d "$RUNTIME_DIR" ]] || warn "Runtime directory not found: $RUNTIME_DIR"
[[ -d "$INSTALL_DIR" ]] || warn "Install directory not found: $INSTALL_DIR"
mkdir -p "$OUTPUT_DIR" || err "Cannot create output directory: $OUTPUT_DIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
[[ -n "$NAME" ]] || NAME="zec_analysis_$STAMP"
WORKDIR="$OUTPUT_DIR/$NAME"
ZIP_PATH="$OUTPUT_DIR/$NAME.zip"

if [[ -e "$WORKDIR" || -e "$ZIP_PATH" ]]; then
  err "Output already exists: $WORKDIR or $ZIP_PATH"
fi

SERVICES=(zendure-controller.service zendure-replay.service)
ACTIVE_SERVICES=()

cleanup() {
  local status=$?
  if [[ $STOP_SERVICES -eq 1 ]]; then
    if [[ ${#ACTIVE_SERVICES[@]} -gt 0 ]]; then
      log "Restarting previously active services: ${ACTIVE_SERVICES[*]}"
      sudo systemctl start "${ACTIVE_SERVICES[@]}" || warn "Could not restart one or more services"
    fi
  fi
  if [[ $status -eq 0 ]]; then
    rm -rf "$WORKDIR"
  else
    warn "Keeping temporary directory for inspection: $WORKDIR"
  fi
}
trap cleanup EXIT

if [[ $STOP_SERVICES -eq 1 ]]; then
  for svc in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$svc"; then
      ACTIVE_SERVICES+=("$svc")
    fi
  done
  for svc in "${ACTIVE_SERVICES[@]}"; do
    log "Stopping $svc for consistent snapshot"
    sudo systemctl stop "$svc"
  done
fi

log "Creating package directory: $WORKDIR"
mkdir -p "$WORKDIR/runtime_logs" "$WORKDIR/fallback_logs"

shopt -s nullglob
cd "$MEASUREMENT_DIR"
V4_FILES=(zendure_measurements_v4*.csv)
if [[ ${#V4_FILES[@]} -eq 0 ]]; then
  err "No zendure_measurements_v4*.csv files found in $MEASUREMENT_DIR"
fi

if [[ $LATEST_ONLY -eq 1 ]]; then
  latest="$(ls -t zendure_measurements_v4*.csv 2>/dev/null | head -n 1)"
  [[ -n "$latest" ]] || err "No V4 measurement file found"
  log "Including latest V4 measurement file only: $MEASUREMENT_DIR/$latest"
  cp -v -- "$latest" "$WORKDIR/"
else
  log "Including all V4 measurement files from $MEASUREMENT_DIR"
  for f in "${V4_FILES[@]}"; do
    cp -v -- "$f" "$WORKDIR/"
  done
fi

for f in zec_measurement_manifest.json zec_config_snapshots.json zec_runtime_events.jsonl; do
  if [[ -f "$MEASUREMENT_DIR/$f" ]]; then
    cp -v -- "$MEASUREMENT_DIR/$f" "$WORKDIR/"
  else
    warn "Optional/required V4 companion file missing: $MEASUREMENT_DIR/$f"
  fi
done

if [[ -d "$RUNTIME_DIR" ]]; then
  for f in "$RUNTIME_DIR"/*.log "$RUNTIME_DIR"/*.log.*; do
    [[ -f "$f" ]] || continue
    cp -v -- "$f" "$WORKDIR/runtime_logs/"
  done
fi

if [[ $NO_FALLBACK_LOGS -eq 0 && -d "$FALLBACK_DIR" ]]; then
  for f in "$FALLBACK_DIR"/*; do
    [[ -f "$f" ]] || continue
    cp -v -- "$f" "$WORKDIR/fallback_logs/"
  done
fi

cat > "$WORKDIR/PACKAGE_INFO.txt" <<EOF
ZEC analysis package
created_utc=$STAMP
hostname=$(hostname)
user=$(id -un)
measurement_dir=$MEASUREMENT_DIR
runtime_dir=$RUNTIME_DIR
fallback_dir=$FALLBACK_DIR
install_dir=$INSTALL_DIR
output_dir=$OUTPUT_DIR
stop_services=$STOP_SERVICES
latest_only=$LATEST_ONLY
with_replay_report=$WITH_REPLAY_REPORT

config.json is intentionally not included.
EOF

if [[ $WITH_REPLAY_REPORT -eq 1 ]]; then
  REPLAY="$INSTALL_DIR/tools/replay_csv.py"
  if [[ -f "$REPLAY" ]]; then
    log "Generating optional replay report with timeout and low priority: $REPLAY"
    REPLAY_TIMEOUT_SECONDS="${ZEC_EXPORT_REPLAY_TIMEOUT_SECONDS:-180}"
    REPLAY_CMD=(python3 "$REPLAY" zendure_measurements_v4*.csv)
    if command -v ionice >/dev/null 2>&1; then
      REPLAY_CMD=(ionice -c3 "${REPLAY_CMD[@]}")
    fi
    if command -v nice >/dev/null 2>&1; then
      REPLAY_CMD=(nice -n 15 "${REPLAY_CMD[@]}")
    fi
    (
      cd "$WORKDIR"
      if command -v timeout >/dev/null 2>&1; then
        timeout --kill-after=5s "${REPLAY_TIMEOUT_SECONDS}s" "${REPLAY_CMD[@]}" > replay_report.txt 2>&1 || warn "Replay report failed or timed out; package remains usable without it"
      else
        warn "timeout command not found; skipping replay report to protect the Pi"
      fi
    )
  else
    warn "Replay tool not found: $REPLAY"
  fi
else
  log "Skipping replay report by default; raw CSV/manifest/config/runtime files are included for offline analysis"
fi

{
  echo
  echo "Included package files:"
  (cd "$WORKDIR" && find . -type f -printf '%P\t%s bytes\n' | sort)
  echo
  echo "Disk usage:"
  df -h "$MEASUREMENT_DIR" "$OUTPUT_DIR" "$RUNTIME_DIR" 2>/dev/null || true
} >> "$WORKDIR/PACKAGE_INFO.txt"

log "Creating ZIP: $ZIP_PATH"
(
  cd "$OUTPUT_DIR"
  zip -qr "$(basename "$ZIP_PATH")" "$(basename "$WORKDIR")"
)

log "Package ready: $ZIP_PATH"
ls -lh "$ZIP_PATH"
