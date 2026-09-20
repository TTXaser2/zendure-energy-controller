#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Transactional ZEC V16 uninstaller / clean-fresh-reset tool.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/root_artifact_transaction.sh"
TARGET="/opt/zendure-controller"
DOWNLOAD_DIR="/home/pi/Downloads"
MODE=""
PREFLIGHT_ONLY=0
BACKUP_USER_DATA=1
INCLUDE_MEASUREMENT=0
BACKUP_DIR="$DOWNLOAD_DIR"
ASSUME_YES=0
CONFIRM_NO_BACKUP=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --preflight-only) PREFLIGHT_ONLY=1; shift ;;
    --uninstall) MODE="UNINSTALL"; shift ;;
    --fresh-install-reset) MODE="FRESH_INSTALL_RESET"; shift ;;
    --no-user-data-backup) BACKUP_USER_DATA=0; shift ;;
    --backup-dir) BACKUP_DIR="${2:-}"; shift 2 ;;
    --include-measurement-data) INCLUDE_MEASUREMENT=1; shift ;;
    --yes) ASSUME_YES=1; shift ;;
    --confirm-no-user-data-backup) CONFIRM_NO_BACKUP=1; shift ;;
    -h|--help)
      cat <<EOF
Usage: $0 (--uninstall|--fresh-install-reset) [options]
  --preflight-only              nur anzeigen/pruefen, keine Produktivmutation
  --no-user-data-backup         lokalen Restore-Backup-Export bewusst abschalten
  --backup-dir DIR              Backupziel (Default /home/pi/Downloads)
  --include-measurement-data    zusätzlich große Measurement-/Deep-Trace-Daten sichern
  --yes                         normale Sicherheitsabfrage nicht interaktiv beantworten
  --confirm-no-user-data-backup  Datenverlust bei --no-user-data-backup explizit bestätigen
EOF
      exit 0 ;;
    *) echo "FEHLER: Unbekannte Option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$MODE" ] || { echo "FEHLER: --uninstall oder --fresh-install-reset erforderlich." >&2; exit 2; }

STAMP="$(date +%Y%m%d_%H%M%S)"; mkdir -p "$DOWNLOAD_DIR" 2>/dev/null || true
LOG="$DOWNLOAD_DIR/zec_uninstall_${STAMP}.log"; touch "$LOG" 2>/dev/null || LOG="/tmp/zec_uninstall_${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1
START_EPOCH="$(date +%s)"
SUPPORT_WORK=""; USER_BACKUP_ARCHIVE=""; USER_BACKUP_MANIFEST=""; MUTATION_STARTED=0
ROOT_ARTIFACTS=(
  "/usr/local/sbin/zendure-controller-restart"
  "/etc/sudoers.d/zendure-controller"
  "/etc/systemd/system/zendure-controller.service"
  "/etc/systemd/system/zendure-replay.service"
  "/etc/systemd/system/zendure-status-preview.service"
)

support_begin() {
  [ -n "$SUPPORT_WORK" ] && return 0
  SUPPORT_WORK="$(python3 "$SCRIPT_DIR/zec_support_bundle.py" collect --label "uninstall-failure" \
    --output-dir "$DOWNLOAD_DIR" --target "$TARGET" --config "$TARGET/config.json" \
    --install-log "$LOG" --since-epoch "$START_EPOCH" --stage pre_failure_cleanup \
    --error-code "$1" --defer-finalize 2>/dev/null | tail -n1 || true)"
}
support_finalize() {
  [ -n "$SUPPORT_WORK" ] || return 0
  python3 "$SCRIPT_DIR/zec_support_bundle.py" finalize --work-dir "$SUPPORT_WORK" \
    --output-dir "$DOWNLOAD_DIR" --rollback-result "$1" --rollback-exit-code "$2" 2>/dev/null | tail -n1 || true
}
on_error() {
  local rc="${1:-1}" line="${2:-0}"
  [ "$rc" -eq 0 ] && return
  trap - ERR EXIT; set +e
  echo "FEHLER: Uninstaller abgebrochen (rc=$rc, line=$line)."
  support_begin "RC_${rc}_LINE_${line}"
  bundle="$(support_finalize "uninstall_failed_no_automatic_restore" "$rc")"
  [ -n "$bundle" ] && echo "Diagnosepaket: $bundle"
  echo "Persistentes Uninstallerlog: $LOG"
  exit "$rc"
}
trap 'on_error $? $LINENO' ERR
trap 'on_error $? $LINENO' EXIT

[ "$(id -un)" = "pi" ] || { echo "FEHLER: als Benutzer pi ausführen; sudo wird intern verwendet."; false; }
[ -d /home/pi ] || { echo "FEHLER: /home/pi fehlt."; false; }

# The uninstaller accepts the current release or its directly supported predecessor.
IDENTITY_JSON="$(python3 - "$TARGET/version.py" <<'PY'
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent) if '__file__' in globals() else '.')
p=Path(sys.argv[1]); text=p.read_text(encoding='utf-8') if p.is_file() else ''
import re
def v(n):
 m=re.search(rf'^{n}\s*=\s*["\']([^"\']+)["\']',text,re.M); return m.group(1) if m else ''
print(json.dumps({'version':v('APP_VERSION'),'build_id':v('APP_BUILD_ID')}))
PY
)"
INSTALLED_VERSION="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("version",""))' "$IDENTITY_JSON")"
INSTALLED_BUILD="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("build_id",""))' "$IDENTITY_JSON")"
if [ ! -e "$TARGET" ]; then
  STATE="$(python3 "$SCRIPT_DIR/deployment_contract.py" classify --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])')"
  if [ "$STATE" = "CLEAN_FRESH_INSTALL" ]; then
    echo "ZEC ist bereits vollständig entfernt; CLEAN_FRESH_INSTALL_STATE=yes"
    trap - ERR EXIT; exit 0
  fi
fi
case "$INSTALLED_VERSION/$INSTALLED_BUILD" in
  "15.0.3/v15.0.3-20260911"|"16.0.0/v16.0.0-20260913"|"16.0.1/v16.0.1-20260915"|"16.0.2/v16.0.2-20260917"|"16.1.0/v16.1.0-20260919") ;;
  *) echo "FEHLER: Uninstaller verweigert unbekannte/partielle Installation: $INSTALLED_VERSION / $INSTALLED_BUILD"; false ;;
esac
STATE="$(python3 "$SCRIPT_DIR/deployment_contract.py" classify --expected-version "$INSTALLED_VERSION" --expected-build "$INSTALLED_BUILD" --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["state"])')"
[ "$STATE" = "SUPPORTED_UPDATE" ] || { echo "FEHLER: aktiver ZEC-Zustand ist nicht vollständig/konsistent: $STATE"; false; }

echo "UNINSTALL_MODE=$MODE"
echo "INSTALLED_VERSION=$INSTALLED_VERSION"
echo "USER_DATA_BACKUP=$([ "$BACKUP_USER_DATA" -eq 1 ] && echo yes || echo no)"
echo "INCLUDE_MEASUREMENT_DATA=$([ "$INCLUDE_MEASUREMENT" -eq 1 ] && echo yes || echo no)"
echo "Folgende aktive Artefakte werden entfernt:"
printf ' - %s\n' "$TARGET" "${ROOT_ARTIFACTS[@]}"
echo "Systempakete, MQTT-Broker, EVCC, Netzwerk und Benutzer pi bleiben unangetastet."
if [ "$PREFLIGHT_ONLY" -eq 1 ]; then
  echo "PREFLIGHT_RESULT=PASS"
  echo "PRODUCTIVE_CHANGES=NONE"
  echo "Persistentes Uninstallerlog: $LOG"
  trap - ERR EXIT; exit 0
fi

if [ "$ASSUME_YES" -ne 1 ]; then
  if [ -t 0 ]; then
    echo
    read -r -p "Zum Fortfahren exakt 'REMOVE ZEC' eingeben: " answer
    [ "$answer" = "REMOVE ZEC" ] || { echo "Abgebrochen."; trap - ERR EXIT; exit 1; }
  else
    echo "FEHLER: Nicht-interaktiver Lauf benötigt --yes."; false
  fi
fi
if [ "$BACKUP_USER_DATA" -eq 0 ] && [ "$CONFIRM_NO_BACKUP" -ne 1 ]; then
  if [ -t 0 ] && [ "$ASSUME_YES" -ne 1 ]; then
    read -r -p "WARNUNG: Ohne Benutzerdatensicherung fortfahren? Exakt 'DELETE WITHOUT BACKUP' eingeben: " no_backup_answer
    [ "$no_backup_answer" = "DELETE WITHOUT BACKUP" ] || { echo "Abgebrochen."; trap - ERR EXIT; exit 1; }
  else
    echo "FEHLER: --no-user-data-backup benötigt zusätzlich --confirm-no-user-data-backup."; false
  fi
fi

if [ "$BACKUP_USER_DATA" -eq 1 ]; then
  mkdir -p "$BACKUP_DIR"
  args=(--target "$TARGET" --output-dir "$BACKUP_DIR" --label "${MODE,,}")
  [ "$INCLUDE_MEASUREMENT" -eq 1 ] && args+=(--include-measurement-data)
  BACKUP_JSON="$(python3 "$SCRIPT_DIR/backup_zec_user_data.py" "${args[@]}")"
  USER_BACKUP_ARCHIVE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["archive"])' "$BACKUP_JSON")"
  USER_BACKUP_MANIFEST="${USER_BACKUP_ARCHIVE%.tar.gz}.manifest.json"
  echo "Benutzerdatenbackup: $USER_BACKUP_ARCHIVE"
else
  echo "WARNUNG: Benutzerdatenbackup wurde explizit deaktiviert."
fi

MUTATION_STARTED=1
sudo systemctl disable --now zendure-controller.service zendure-replay.service zendure-status-preview.service >/dev/null 2>&1 || true
sudo rm -rf "$TARGET"
for path in "${ROOT_ARTIFACTS[@]}"; do sudo rm -f "$path"; done
sudo systemctl daemon-reload
sudo systemctl reset-failed zendure-controller.service zendure-replay.service zendure-status-preview.service >/dev/null 2>&1 || true

STATE_JSON="$(python3 "$SCRIPT_DIR/deployment_contract.py" classify --json)"
STATE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["state"])' "$STATE_JSON")"
[ "$STATE" = "CLEAN_FRESH_INSTALL" ] || { echo "FEHLER: Entfernung unvollständig; Zustand=$STATE"; false; }

trap - ERR EXIT
echo "ACTIVE_ZEC_RUNTIME_REMOVED=yes"
echo "ACTIVE_CONFIG_REMOVED=yes"
echo "SYSTEMD_ARTIFACTS_REMOVED=yes"
echo "ZEC_DEPENDENCIES_REMOVED=no"
echo "CLEAN_FRESH_INSTALL_STATE=yes"
[ -n "$USER_BACKUP_ARCHIVE" ] && echo "USER_DATA_BACKUP=$USER_BACKUP_ARCHIVE"
echo "Persistentes Uninstallerlog: $LOG"
