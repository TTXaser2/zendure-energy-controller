#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
set -euo pipefail

DURATION_MINUTES=20
INTERVAL_SECONDS=2
OUTPUT_DIR="/home/pi/Downloads"

usage() {
  cat <<'TXT'
Usage: collect_resync_diagnostics.sh [--minutes N] [--interval-seconds N] [--output-dir DIR]

Collects a bounded ZEC command-resync/MQTT freshness trace without stopping or
restarting services. The controller and MQTT command path are read-only from
this tool's perspective.
TXT
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) DURATION_MINUTES="$2"; shift 2 ;;
    --interval-seconds) INTERVAL_SECONDS="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$DURATION_MINUTES" =~ ^[0-9]+$ ]] || { echo "--minutes must be an integer" >&2; exit 2; }
[[ "$INTERVAL_SECONDS" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo "--interval-seconds must be numeric" >&2; exit 2; }

mkdir -p "$OUTPUT_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
WORK="$OUTPUT_DIR/zec_resync_diag_${TS}"
ARCHIVE="${WORK}.tar.gz"
START_JOURNAL="$(date '+%Y-%m-%d %H:%M:%S')"
mkdir -p "$WORK"

curl -fsS --max-time 5 'http://127.0.0.1:8080/operational-events?days=2&limit=1000' \
  > "$WORK/operational_events_before.json" 2> "$WORK/operational_events_before.err" || true

python3 - "$WORK/status_samples.jsonl" "$DURATION_MINUTES" "$INTERVAL_SECONDS" <<'PY'
import datetime as dt
import json
import sys
import time
import urllib.request

out_path = sys.argv[1]
duration_s = max(1.0, float(sys.argv[2]) * 60.0)
interval_s = max(0.5, float(sys.argv[3]))
end_at = time.monotonic() + duration_s
keys = (
    "operating_mode", "control_reason", "zendure_target_signed_power",
    "actual_zendure_power_w", "actual_zendure_power_valid",
    "zendure_mqtt_overall_status", "zendure_mqtt_status_reason",
    "zendure_mqtt_connected", "zendure_mqtt_live_confirmed",
    "zendure_mqtt_critical_data_age_s", "zendure_mqtt_missing_critical_groups",
    "zendure_mqtt_stale_critical_groups", "zendure_mqtt_topic_groups_json",
    "command_uncertain_mqtt_active", "command_uncertain_mqtt_status",
    "command_resync_count", "command_resync_last_time", "command_resync_reason",
    "command_resync_suppressed_count", "command_resync_suppressed_last_time",
    "command_resync_suppressed_reason", "command_effect_state_category",
    "command_effect_state_reason", "mqtt_commands_sent_total", "loop_counter",
)

def iso_now():
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")

sample = 0
with open(out_path, "w", encoding="utf-8", buffering=1) as out:
    while time.monotonic() < end_at:
        started = time.monotonic()
        sample += 1
        row = {"captured_at": iso_now(), "sample": sample}
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/status", timeout=3) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            for key in keys:
                row[key] = data.get(key)
            row["request_ok"] = True
        except Exception as exc:
            row.update({"request_ok": False, "request_error": repr(exc)})
        out.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        remaining = interval_s - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)
PY

curl -fsS --max-time 5 'http://127.0.0.1:8080/operational-events?days=2&limit=1000' \
  > "$WORK/operational_events_after.json" 2> "$WORK/operational_events_after.err" || true

# Use journalctl's unambiguous local-time format. ISO strings containing T and
# a numeric UTC offset were rejected on the target Pi in the earlier helper.
journalctl -u zendure-controller.service --since "$START_JOURNAL" \
  --no-pager -o short-iso-precise > "$WORK/controller_journal.txt" 2>&1 || true

{
  echo "captured_from=$START_JOURNAL"
  echo "captured_to=$(date '+%Y-%m-%d %H:%M:%S')"
  echo
  free -h
  echo
  swapon --show --bytes
  echo
  vmstat 1 10
} > "$WORK/system_snapshot.txt" 2>&1 || true

tar -C "$(dirname "$WORK")" -czf "$ARCHIVE" "$(basename "$WORK")"
rm -rf "$WORK"
echo "Fertig: $ARCHIVE"
ls -lh "$ARCHIVE"
