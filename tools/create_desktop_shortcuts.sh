#!/usr/bin/env bash
set -euo pipefail

# Create desktop launchers for frequent Zendure Energy Controller support tasks.

INSTALL_DIR="/opt/zendure-controller"
DESKTOP_DIR="${HOME}/Desktop"

if [[ -f "${HOME}/.config/user-dirs.dirs" ]]; then
  # shellcheck disable=SC1090
  source "${HOME}/.config/user-dirs.dirs" || true
  if [[ -n "${XDG_DESKTOP_DIR:-}" ]]; then
    DESKTOP_DIR="${XDG_DESKTOP_DIR/#\$HOME/$HOME}"
  fi
fi

mkdir -p "$DESKTOP_DIR"

terminal_cmd="lxterminal"
if ! command -v lxterminal >/dev/null 2>&1; then
  if command -v x-terminal-emulator >/dev/null 2>&1; then
    terminal_cmd="x-terminal-emulator"
  elif command -v xterm >/dev/null 2>&1; then
    terminal_cmd="xterm"
  else
    terminal_cmd=""
  fi
fi

write_launcher() {
  local file="$1"
  local name="$2"
  local comment="$3"
  local exec_cmd="$4"
  local icon="$5"
  cat > "$file" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${name}
Comment=${comment}
Exec=${exec_cmd}
Icon=${icon}
Terminal=false
Categories=Utility;
DESKTOP
  chmod 755 "$file"
}

if [[ -n "$terminal_cmd" ]]; then
  write_launcher \
    "$DESKTOP_DIR/ZEC_Trace_sammeln.desktop" \
    "ZEC Trace sammeln" \
    "Sammelt ZEC-Service-Status, Journal und Runtime-Log in eine Datei" \
    "$terminal_cmd -e ${INSTALL_DIR}/tools/collect_zec_trace.sh --pause" \
    "utilities-terminal"

  write_launcher \
    "$DESKTOP_DIR/ZEC_Diagnosepaket_erstellen.desktop" \
    "ZEC Diagnosepaket erstellen" \
    "Erstellt ein ZEC-Analyse-/Diagnosepaket" \
    "$terminal_cmd -e ${INSTALL_DIR}/tools/run_zec_analysis_package_interactive.sh" \
    "utilities-system-monitor"

  write_launcher \
    "$DESKTOP_DIR/ZEC_Crashpaket_erstellen.desktop" \
    "ZEC Crashpaket erstellen" \
    "Sammelt Kernel-, Storage-, Service- und Vorboot-Logs für Crash-/Hängeranalyse" \
    "$terminal_cmd -e ${INSTALL_DIR}/tools/collect_zec_crash_package.sh --pause" \
    "drive-harddisk"
else
  write_launcher \
    "$DESKTOP_DIR/ZEC_Trace_sammeln.desktop" \
    "ZEC Trace sammeln" \
    "Sammelt ZEC-Service-Status, Journal und Runtime-Log in eine Datei" \
    "${INSTALL_DIR}/tools/collect_zec_trace.sh --pause" \
    "utilities-terminal"

  write_launcher \
    "$DESKTOP_DIR/ZEC_Diagnosepaket_erstellen.desktop" \
    "ZEC Diagnosepaket erstellen" \
    "Erstellt ein ZEC-Analyse-/Diagnosepaket" \
    "${INSTALL_DIR}/tools/run_zec_analysis_package_interactive.sh" \
    "utilities-system-monitor"

  write_launcher \
    "$DESKTOP_DIR/ZEC_Crashpaket_erstellen.desktop" \
    "ZEC Crashpaket erstellen" \
    "Sammelt Kernel-, Storage-, Service- und Vorboot-Logs für Crash-/Hängeranalyse" \
    "${INSTALL_DIR}/tools/collect_zec_crash_package.sh --pause" \
    "drive-harddisk"
fi

echo "Desktop-Verknüpfungen erstellt/aktualisiert:"
echo "- $DESKTOP_DIR/ZEC_Trace_sammeln.desktop"
echo "- $DESKTOP_DIR/ZEC_Diagnosepaket_erstellen.desktop"
echo "- $DESKTOP_DIR/ZEC_Crashpaket_erstellen.desktop"
echo
if [[ "$DESKTOP_DIR" != "$HOME/Desktop" ]]; then
  echo "Hinweis: Desktop-Verzeichnis laut XDG: $DESKTOP_DIR"
fi
echo "Falls Raspberry Pi OS nachfragt: 'Ausführen' bzw. 'Als vertrauenswürdig markieren' wählen."
