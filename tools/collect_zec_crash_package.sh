#!/usr/bin/env bash
set -u

# Collect a compact but useful system/crash package for Raspberry Pi hangs,
# reboots, storage/MMC/USB issues and ZEC service failures.

TS=$(date +%Y%m%d_%H%M%S)
OUT_DIR="${HOME}/Downloads"
WORK="${OUT_DIR}/zec_crash_${TS}"
ZIP="${OUT_DIR}/zec_crash_${TS}.zip"
LATEST="${OUT_DIR}/zec_crash_latest.zip"

mkdir -p "$WORK" "$OUT_DIR"

run_cmd() {
  local name="$1"
  shift
  {
    echo "===== ${name} ====="
    echo "Command: $*"
    echo
    "$@" 2>&1
  } > "${WORK}/${name}.txt"
}

run_shell() {
  local name="$1"
  shift
  {
    echo "===== ${name} ====="
    echo "Command: $*"
    echo
    bash -lc "$*" 2>&1
  } > "${WORK}/${name}.txt"
}

safe_copy() {
  local src="$1"
  local dst="$2"
  if [[ -e "$src" ]]; then
    cp -a "$src" "${WORK}/${dst}" 2>/dev/null || true
  fi
}

echo "Sammle ZEC-Crashpaket nach: ${WORK}"
echo

run_cmd date date -Is
run_cmd uname uname -a
run_cmd uptime uptime
run_cmd free free -h
run_cmd df df -h
run_cmd lsblk lsblk -f
run_cmd findmnt findmnt
run_shell vcgencmd_throttled 'vcgencmd get_throttled || true'
run_shell vcgencmd_temp 'vcgencmd measure_temp || true'

run_shell systemctl_controller 'systemctl status zendure-controller.service --no-pager -l || true'
run_shell systemctl_replay 'systemctl status zendure-replay.service --no-pager -l || true'
run_shell systemctl_evcc 'systemctl status evcc.service --no-pager -l || true'
run_shell systemctl_mosquitto 'systemctl status mosquitto.service --no-pager -l || true'

run_shell journal_controller_current 'journalctl -u zendure-controller -b -n 500 --no-pager -l || true'
run_shell journal_replay_current 'journalctl -u zendure-replay -b -n 300 --no-pager -l || true'
run_shell journal_evcc_current 'journalctl -u evcc -b -n 300 --no-pager -l || true'
run_shell journal_mosquitto_current 'journalctl -u mosquitto -b -n 300 --no-pager -l || true'

run_shell journal_kernel_current 'journalctl -k -b -n 900 --no-pager -l || true'
run_shell journal_warnings_current 'journalctl -p warning..alert -b -n 900 --no-pager -l || true'
run_shell journal_kernel_previous 'journalctl -k -b -1 -n 900 --no-pager -l || true'
run_shell journal_warnings_previous 'journalctl -p warning..alert -b -1 -n 900 --no-pager -l || true'
run_shell journal_controller_previous 'journalctl -u zendure-controller -b -1 -n 500 --no-pager -l || true'
run_shell journal_evcc_previous 'journalctl -u evcc -b -1 -n 300 --no-pager -l || true'

FILTER='mmc|blk|sda|usb|ext4|vfat|fat|i/o|timeout|blocked|hung|reset|under-voltage|voltage|error|fail|throttled'
run_shell dmesg_storage_filtered "dmesg -T | egrep -i '${FILTER}' || true"
run_shell journal_storage_filtered "journalctl -b --no-pager -l | egrep -i '${FILTER}' | tail -n 1200 || true"
run_shell journal_storage_previous_filtered "journalctl -b -1 --no-pager -l | egrep -i '${FILTER}' | tail -n 1200 || true"

run_shell zec_runtime_log_tail 'tail -n 600 /opt/zendure-controller/logs/zendure_runtime.log || true'
run_shell zec_ready 'curl -s --max-time 5 http://127.0.0.1:8080/ready | python3 -m json.tool || true'
run_shell zec_status_head 'curl -s --max-time 5 http://127.0.0.1:8080/status | python3 -m json.tool | head -n 260 || true'

run_shell fstab 'cat /etc/fstab || true'
run_shell boot_cmdline 'cat /boot/cmdline.txt || cat /boot/firmware/cmdline.txt || true'
run_shell boot_config 'cat /boot/config.txt || cat /boot/firmware/config.txt || true'

safe_copy /opt/zendure-controller/version.py version.py
safe_copy /opt/zendure-controller/config.json config.json.snapshot
safe_copy /etc/fstab fstab.snapshot

cat > "${WORK}/README.txt" <<README
ZEC Crash Package
Created: $(date -Is)
Host: $(hostname)
Output: ${ZIP}

Use this package for:
- Raspberry Pi hangs/freezes/reboots
- mmc_rescan, blocked task, ext4/vfat/FAT, USB/storage diagnostics
- EVCC/MQTT/ZEC service failures around a crash window

Notes:
- previous-boot sections are only populated when persistent journald data exists.
- config.json is copied as a snapshot for diagnostics. Review before sharing externally.
README

(
  cd "$OUT_DIR" || exit 1
  zip -qr "$ZIP" "$(basename "$WORK")"
)
cp -f "$ZIP" "$LATEST" 2>/dev/null || true

echo
echo "Crashpaket erstellt:"
echo "$ZIP"
echo
ls -lh "$ZIP" 2>/dev/null || true
echo
if [[ "${1:-}" == "--pause" ]]; then
  read -r -p "Enter drücken zum Schließen..."
fi
