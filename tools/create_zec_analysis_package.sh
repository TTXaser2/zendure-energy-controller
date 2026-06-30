#!/usr/bin/env bash
set -euo pipefail

# Create a Zendure Energy Controller analysis package.
# No config.json or secrets are included.
# RC8 default is non-invasive: services are NOT stopped unless --stop-services
# is requested explicitly.

MEASUREMENT_DIR=""
RUNTIME_DIR="/opt/zendure-controller/logs"
FALLBACK_DIR="/opt/zendure-controller/logs/fallback"
INSTALL_DIR="/opt/zendure-controller"
OUTPUT_DIR="/home/pi/Downloads"
NAME=""
STOP_SERVICES=0
LATEST_ONLY=0
WITH_REPLAY_REPORT=0
NO_FALLBACK_LOGS=0
WARNINGS=()

log() { printf '[zec-export] %s\n' "$*"; }
warn() { WARNINGS+=("$*"); printf '[zec-export][WARN] %s\n' "$*" >&2; }
err() { printf '[zec-export][ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'USAGE'
Usage: create_zec_analysis_package.sh [options]

Options:
  --measurement-dir DIR   Measurement log directory.
                          Default auto-detects config.json first, then known paths:
                          /media/pi/4CD6-6466/ZEC/logs
                          /media/pi/2.0 GB Volume/ZEC/logs
  --runtime-dir DIR       Runtime log directory. Default: /opt/zendure-controller/logs
  --fallback-dir DIR      Fallback log directory. Default: /opt/zendure-controller/logs/fallback
  --install-dir DIR       ZEC install directory. Default: /opt/zendure-controller
  --output-dir DIR        Output directory. Default: /home/pi/Downloads
  --name NAME             Package base name. Default: zec_analysis_<UTC timestamp>
  --no-stop-services      Do not stop services while copying files (default)
  --stop-services         Stop controller/replay briefly for a more consistent snapshot
  --latest-only           Include only the newest non-empty primary zendure_measurements_v4*.csv file
                          Default includes all non-empty primary zendure_measurements_v4*.csv files
  --with-replay-report    Optional: generate replay_report.txt with timeout and low priority
                          Default skips replay report to protect the Raspberry Pi
  --no-replay-report      Deprecated compatibility option; replay report is skipped by default
  --no-fallback-logs      Do not include fallback log directory
  -h, --help              Show help
USAGE
}

nonempty_v4_files() {
  local dir="$1"
  [[ -d "$dir" ]] || return 0
  find "$dir" -maxdepth 1 -type f -name 'zendure_measurements_v4*.csv' -size +0c -printf '%f\n' | sort
}

sidecar_files() {
  local dir="$1"
  [[ -d "$dir" ]] || return 0
  for f in zec_measurement_manifest.json zec_config_snapshots.json zec_runtime_events.jsonl; do
    [[ -f "$dir/$f" ]] && printf '%s\n' "$f"
  done
}

add_candidate_dir() {
  local candidate="$1"
  [[ -n "$candidate" ]] || return 0
  [[ -d "$candidate" ]] || return 0
  printf '%s\n' "$candidate"
}

configured_measurement_dir() {
  local config_file="$INSTALL_DIR/config.json"
  [[ -f "$config_file" ]] || return 0
  python3 - <<PY 2>/dev/null || true
import json, os
cfg=json.load(open(${config_file@Q}))
target=str(cfg.get('MEASUREMENT_LOG_STORAGE_TARGET',''))
mdir=str(cfg.get('MEASUREMENT_LOG_DIR','ZEC/logs') or 'ZEC/logs')
if os.path.isabs(mdir):
    print(mdir)
elif target == 'external_mount':
    mount=str(cfg.get('MEASUREMENT_LOG_MOUNTPOINT','') or '')
    if mount:
        print(os.path.join(mount, mdir))
else:
    print(os.path.join(${INSTALL_DIR@Q}, mdir))
PY
}

copy_manifest_referenced_warnings() {
  local dir="$1"
  local label="$2"
  local manifest="$dir/zec_measurement_manifest.json"
  [[ -f "$manifest" ]] || return 0
  python3 - <<PY 2>/dev/null || true
import json, os
manifest=${manifest@Q}
dir=${dir@Q}
label=${label@Q}
try:
    data=json.load(open(manifest, encoding='utf-8'))
except Exception as exc:
    print(f"MANIFEST_PARSE_ERROR|{label}|{exc}")
    raise SystemExit
for item in data.get('files', []):
    rel=item.get('relative_path') or item.get('file_name') or ''
    if not rel:
        continue
    path=os.path.join(dir, rel)
    if not os.path.exists(path):
        print(f"MISSING_MANIFEST_FILE|{label}|{rel}|row_count={item.get('row_count')}|first={item.get('first_measurement_epoch_ms')}|last={item.get('last_measurement_epoch_ms')}")
PY
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
    --stop-services) STOP_SERVICES=1; shift ;;
    --latest-only) LATEST_ONLY=1; shift ;;
    --with-replay-report) WITH_REPLAY_REPORT=1; shift ;;
    --no-replay-report) WITH_REPLAY_REPORT=0; shift ;;
    --no-fallback-logs) NO_FALLBACK_LOGS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) err "Unknown option: $1" ;;
  esac
done

if [[ -z "$MEASUREMENT_DIR" ]]; then
  mapfile -t candidates < <(
    configured_measurement_dir
    add_candidate_dir "/media/pi/4CD6-6466/ZEC/logs"
    add_candidate_dir "/media/pi/2.0 GB Volume/ZEC/logs"
  )
  # Prefer the first candidate with non-empty V4 data, otherwise keep the first existing one.
  first_existing=""
  for candidate in "${candidates[@]:-}"; do
    [[ -n "$first_existing" ]] || first_existing="$candidate"
    if [[ -n "$(nonempty_v4_files "$candidate" | head -n 1)" ]]; then
      MEASUREMENT_DIR="$candidate"
      break
    fi
  done
  [[ -n "$MEASUREMENT_DIR" ]] || MEASUREMENT_DIR="$first_existing"
fi

[[ -n "$MEASUREMENT_DIR" ]] || warn "Primary measurement directory not found; fallback-only package will be attempted"
[[ -z "$MEASUREMENT_DIR" || -d "$MEASUREMENT_DIR" ]] || warn "Primary measurement directory not found: $MEASUREMENT_DIR"
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
trap cleanup EXIT INT TERM

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
else
  log "Creating live snapshot without stopping services. Use --stop-services only when an exact closed-file snapshot is required."
fi

log "Creating package directory: $WORKDIR"
mkdir -p "$WORKDIR/primary_logs" "$WORKDIR/runtime_logs" "$WORKDIR/fallback_logs"

PRIMARY_COUNT=0
FALLBACK_COUNT=0

if [[ -n "$MEASUREMENT_DIR" && -d "$MEASUREMENT_DIR" ]]; then
  mapfile -t V4_FILES < <(nonempty_v4_files "$MEASUREMENT_DIR")
  if [[ ${#V4_FILES[@]} -eq 0 ]]; then
    warn "No non-empty zendure_measurements_v4*.csv files found in primary measurement directory: $MEASUREMENT_DIR"
  elif [[ $LATEST_ONLY -eq 1 ]]; then
    latest="$(ls -t "$MEASUREMENT_DIR"/zendure_measurements_v4*.csv 2>/dev/null | while read -r f; do [[ -s "$f" ]] && echo "$f" && break; done)"
    if [[ -n "$latest" ]]; then
      log "Including latest primary V4 measurement file only: $latest"
      cp -v -- "$latest" "$WORKDIR/primary_logs/"
      cp -v -- "$latest" "$WORKDIR/"
      PRIMARY_COUNT=1
    fi
  else
    log "Including all non-empty V4 measurement files from $MEASUREMENT_DIR"
    for f in "${V4_FILES[@]}"; do
      cp -v -- "$MEASUREMENT_DIR/$f" "$WORKDIR/primary_logs/"
      cp -v -- "$MEASUREMENT_DIR/$f" "$WORKDIR/"
      PRIMARY_COUNT=$((PRIMARY_COUNT+1))
    done
  fi

  for f in $(sidecar_files "$MEASUREMENT_DIR"); do
    cp -v -- "$MEASUREMENT_DIR/$f" "$WORKDIR/primary_logs/"
    cp -v -- "$MEASUREMENT_DIR/$f" "$WORKDIR/"
  done
  while IFS= read -r line; do
    [[ -n "$line" ]] && warn "$line"
  done < <(copy_manifest_referenced_warnings "$MEASUREMENT_DIR" "primary")
fi

if [[ $NO_FALLBACK_LOGS -eq 0 && -d "$FALLBACK_DIR" ]]; then
  mapfile -t FB_V4_FILES < <(nonempty_v4_files "$FALLBACK_DIR")
  if [[ ${#FB_V4_FILES[@]} -gt 0 ]]; then
    log "Including fallback V4 measurement files from $FALLBACK_DIR"
    for f in "${FB_V4_FILES[@]}"; do
      cp -v -- "$FALLBACK_DIR/$f" "$WORKDIR/fallback_logs/"
      FALLBACK_COUNT=$((FALLBACK_COUNT+1))
    done
  fi
  for f in $(sidecar_files "$FALLBACK_DIR"); do
    cp -v -- "$FALLBACK_DIR/$f" "$WORKDIR/fallback_logs/"
  done
  while IFS= read -r line; do
    [[ -n "$line" ]] && warn "$line"
  done < <(copy_manifest_referenced_warnings "$FALLBACK_DIR" "fallback")
fi

if [[ $PRIMARY_COUNT -eq 0 && $FALLBACK_COUNT -eq 0 ]]; then
  err "No non-empty V4 measurement CSV files found in primary or fallback directories"
fi
if [[ $PRIMARY_COUNT -eq 0 && $FALLBACK_COUNT -gt 0 ]]; then
  warn "Primary is empty/unavailable; creating fallback-only analysis package"
fi

if [[ -d "$RUNTIME_DIR" ]]; then
  for f in "$RUNTIME_DIR"/*.log "$RUNTIME_DIR"/*.log.*; do
    [[ -f "$f" ]] || continue
    cp -v -- "$f" "$WORKDIR/runtime_logs/"
  done
fi

WEB_PORT_FOR_STATUS="8080"
if [[ -f "$INSTALL_DIR/config.json" ]]; then
  WEB_PORT_FOR_STATUS="$(python3 - <<PY 2>/dev/null || echo 8080
import json
cfg=json.load(open(${INSTALL_DIR@Q} + '/config.json', encoding='utf-8'))
print(cfg.get('WEB_PORT', 8080))
PY
)"
fi
if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 2 "http://127.0.0.1:${WEB_PORT_FOR_STATUS}/status" -o "$WORKDIR/status_snapshot.json" 2>/dev/null; then
    log "Included live /status snapshot for diagnostics"
    python3 - <<PY > "$WORKDIR/SMA_DIAGNOSTICS_SUMMARY.txt" 2>/dev/null || true
import json
from pathlib import Path
path=Path(${WORKDIR@Q})/'status_snapshot.json'
data=json.load(open(path, encoding='utf-8'))
keys=[
 'grid_meter_source','raw_grid_source','grid_power','raw_grid_power',
 'sma_energy_meter_enabled','sma_energy_meter_running','sma_energy_meter_power_w',
 'sma_energy_meter_last_update_age_seconds','sma_energy_meter_socket_mode',
 'sma_energy_meter_effective_socket_mode','sma_energy_meter_bind_address',
 'sma_energy_meter_bind_mode','sma_energy_meter_reuseaddr_enabled',
 'sma_energy_meter_reuseport_requested','sma_energy_meter_reuseport_supported',
 'sma_energy_meter_reuseport_enabled','sma_energy_meter_reuseport_error',
 'sma_energy_meter_multicast_if_set','sma_energy_meter_packet_count',
 'sma_energy_meter_decode_count','sma_energy_meter_ignored_count',
 'sma_energy_meter_error_count','sma_energy_meter_packet_rate_per_min',
 'sma_energy_meter_last_packet_gap_s','sma_energy_meter_max_packet_gap_s',
 'sma_energy_meter_last_large_gap_s','sma_energy_meter_last_large_gap_age_seconds',
 'sma_energy_meter_group','sma_energy_meter_port','sma_energy_meter_interface',
 'sma_energy_meter_resolved_interface_ip','sma_energy_meter_configured_susy_id',
 'sma_energy_meter_configured_serial','sma_energy_meter_selected_device_key',
 'sma_energy_meter_detected_device_count','sma_energy_meter_last_error',
 'last_cycle_timing_json'
]
print('ZEC SMA diagnostics snapshot')
for k in keys:
    print(f'{k}={data.get(k)!r}')
PY
  else
    warn "Could not fetch live /status snapshot from localhost:${WEB_PORT_FOR_STATUS}"
  fi
fi

if compgen -G "$WORKDIR/runtime_logs/*.log*" > /dev/null; then
  grep -h -E 'SMA_DIAG|SMA Energy Meter|SMA_DIRECT|SMA_GRID|SMA packet|packet gap' "$WORKDIR"/runtime_logs/*.log* > "$WORKDIR/sma_runtime_events.txt" 2>/dev/null || true
fi

cat > "$WORKDIR/PACKAGE_INFO.txt" <<EOFINFO
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
primary_v4_file_count=$PRIMARY_COUNT
fallback_v4_file_count=$FALLBACK_COUNT

config.json is intentionally not included.
EOFINFO

if [[ ${#WARNINGS[@]} -gt 0 ]]; then
  {
    echo
    echo "Warnings:"
    for w in "${WARNINGS[@]}"; do
      echo "- $w"
    done
  } >> "$WORKDIR/PACKAGE_INFO.txt"
fi

if [[ $WITH_REPLAY_REPORT -eq 1 ]]; then
  REPLAY="$INSTALL_DIR/tools/replay_csv.py"
  if [[ -f "$REPLAY" ]]; then
    log "Generating optional replay report with timeout and low priority: $REPLAY"
    REPLAY_TIMEOUT_SECONDS="${ZEC_EXPORT_REPLAY_TIMEOUT_SECONDS:-180}"
    REPLAY_CMD=(python3 "$REPLAY" primary_logs/zendure_measurements_v4*.csv fallback_logs/zendure_measurements_v4*.csv)
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
  df -h ${MEASUREMENT_DIR:+"$MEASUREMENT_DIR"} "$OUTPUT_DIR" "$RUNTIME_DIR" 2>/dev/null || true
} >> "$WORKDIR/PACKAGE_INFO.txt"

log "Creating ZIP: $ZIP_PATH"
(
  cd "$OUTPUT_DIR"
  zip -qr "$(basename "$ZIP_PATH")" "$(basename "$WORKDIR")"
)

log "Package ready: $ZIP_PATH"
ls -lh "$ZIP_PATH"
