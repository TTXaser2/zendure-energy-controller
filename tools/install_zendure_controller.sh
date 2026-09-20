#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Canonical ZEC V16 installer: supported update + clean fresh install.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=root_artifact_transaction.sh
source "$SCRIPT_DIR/root_artifact_transaction.sh"

EXPECTED_VERSION_ARG="v16_1_0"
EXPECTED_SOURCE_VERSION="16.0.2"
EXPECTED_SOURCE_BUILD_ID="v16.0.2-20260917"
EXPECTED_TARGET_VERSION="16.1.0"
EXPECTED_TARGET_BUILD_ID="v16.1.0-20260919"
SOURCE_MANIFEST="V16_1_0_SOURCE_MANIFEST.sha256"
TARGET="/opt/zendure-controller"
BOOTSTRAP="$TARGET/.zec_first_install_bootstrap.json"
DOWNLOAD_DIR="/home/pi/Downloads"
DEFAULT_WEB_PORT=8080

VERSION="${1:-}"
[ "$VERSION" = "$EXPECTED_VERSION_ARG" ] || {
  echo "FEHLER: Aufruf: $0 ${EXPECTED_VERSION_ARG} [--preflight-only] [--fresh-install] [--web-port PORT]" >&2
  exit 2
}
shift || true

PREFLIGHT_ONLY=0
FRESH_ASSERT=0
WEB_PORT="$DEFAULT_WEB_PORT"
WEB_PORT_EXPLICIT=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --preflight-only) PREFLIGHT_ONLY=1; shift ;;
    --fresh-install) FRESH_ASSERT=1; shift ;;
    --web-port) WEB_PORT="${2:-}"; WEB_PORT_EXPLICIT=1; shift 2 ;;
    -h|--help)
      cat <<EOF
Usage: $0 ${EXPECTED_VERSION_ARG} [options]
  --preflight-only       vollständige Vorprüfung, keine Produktivmutation
  --fresh-install        CLEAN_FRESH_INSTALL explizit bestätigen
  --web-port PORT        nur Fresh Install; 1024..65535, Default 8080
EOF
      exit 0 ;;
    *) echo "FEHLER: Unbekannte Option: $1" >&2; exit 2 ;;
  esac
done

STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DOWNLOAD_DIR" 2>/dev/null || true
INSTALL_LOG="$DOWNLOAD_DIR/zec_v16_1_0_installer_${STAMP}.log"
if ! touch "$INSTALL_LOG" 2>/dev/null; then
  INSTALL_LOG="/tmp/zec_v16_1_0_installer_${STAMP}.log"
  touch "$INSTALL_LOG"
fi
exec > >(tee -a "$INSTALL_LOG") 2>&1
INSTALL_START_EPOCH="$(date +%s)"

ZIP="$DOWNLOAD_DIR/zendure_controller_${VERSION}.zip"
STAGE_BASE="/tmp/zec_${VERSION}_stage_$$"
STAGED_ROOT="$STAGE_BASE/zendure_controller_${VERSION}"
INSTALL_MODE="UNCLASSIFIED"
EFFECTIVE_WEB_PORT=""
PACKAGE_SHA256=""
INSTALLATION_STARTED=0
BACKUP_CREATED=0
ROOT_ARTIFACTS_BACKED_UP=0
ROLLBACK_STARTED=0
SUPPORT_WORK=""
SUPPORT_ZIP=""
BACKUP="$DOWNLOAD_DIR/zendure-controller-backup-${STAMP}.tar.gz"
CONFIG_BACKUP="$DOWNLOAD_DIR/config.pre-v16.1.0.${STAMP}.json"
ROOT_ARTIFACT_BACKUP="/var/backups/zec-v16.1.0-root-artifacts-${STAMP}"
INSTALL_REPORT="/tmp/zec_v16_1_0_install_report.json"
BACKUP_SHA256=""
BACKUP_SIZE="0"
CONTROLLER_WAS_ACTIVE=0
REPLAY_WAS_ACTIVE=0
PREVIEW_WAS_ACTIVE=0

ROOT_ARTIFACTS=(
  "/usr/local/sbin/zendure-controller-restart"
  "/etc/sudoers.d/zendure-controller"
  "/etc/systemd/system/zendure-controller.service"
  "/etc/systemd/system/zendure-replay.service"
  "/etc/systemd/system/zendure-status-preview.service"
)

cleanup_stage() { rm -rf "$STAGE_BASE" 2>/dev/null || true; }

start_support_capture() {
  local stage="$1" code="$2"
  [ -n "$SUPPORT_WORK" ] && return 0
  local tool="$SCRIPT_DIR/zec_support_bundle.py"
  [ -f "$tool" ] || return 0
  SUPPORT_WORK="$(python3 "$tool" collect \
    --label "v16.1.0-installer-failure" --output-dir "$DOWNLOAD_DIR" \
    --target "$TARGET" --config "$TARGET/config.json" --install-log "$INSTALL_LOG" \
    --since-epoch "$INSTALL_START_EPOCH" --stage "$stage" --error-code "$code" \
    --package-sha256 "$PACKAGE_SHA256" --source-version "$EXPECTED_SOURCE_VERSION" \
    --source-build-id "$EXPECTED_SOURCE_BUILD_ID" --target-version "$EXPECTED_TARGET_VERSION" \
    --target-build-id "$EXPECTED_TARGET_BUILD_ID" --defer-finalize 2>/dev/null | tail -n 1 || true)"
}

finalize_support_capture() {
  local result="$1" code="$2"
  [ -n "$SUPPORT_WORK" ] || return 0
  SUPPORT_ZIP="$(python3 "$SCRIPT_DIR/zec_support_bundle.py" finalize \
    --work-dir "$SUPPORT_WORK" --output-dir "$DOWNLOAD_DIR" \
    --rollback-result "$result" --rollback-exit-code "$code" 2>/dev/null | tail -n 1 || true)"
  [ -n "$SUPPORT_ZIP" ] && echo "Automatisches Diagnosepaket: $SUPPORT_ZIP"
}

restore_previous_services() {
  [ "$CONTROLLER_WAS_ACTIVE" -eq 1 ] && sudo systemctl start zendure-controller.service || true
  [ "$REPLAY_WAS_ACTIVE" -eq 1 ] && sudo systemctl start zendure-replay.service || true
  [ "$PREVIEW_WAS_ACTIVE" -eq 1 ] && sudo systemctl start zendure-status-preview.service || true
}

rollback_update() {
  sudo systemctl stop zendure-controller.service zendure-replay.service zendure-status-preview.service >/dev/null 2>&1 || true
  if [ "$BACKUP_CREATED" -eq 1 ] && [ -f "$BACKUP" ]; then
    sudo rm -rf "$TARGET"
    sudo tar -xzf "$BACKUP" -C /opt
  fi
  if [ "$ROOT_ARTIFACTS_BACKED_UP" -eq 1 ]; then
    zec_restore_root_artifacts "$ROOT_ARTIFACT_BACKUP" "${ROOT_ARTIFACTS[@]}" || true
  fi
  sudo systemctl daemon-reload || true
  restore_previous_services
}

rollback_fresh() {
  sudo systemctl disable --now zendure-controller.service >/dev/null 2>&1 || true
  sudo systemctl disable --now zendure-replay.service zendure-status-preview.service >/dev/null 2>&1 || true
  sudo rm -rf "$TARGET"
  if [ "$ROOT_ARTIFACTS_BACKED_UP" -eq 1 ]; then
    zec_restore_root_artifacts "$ROOT_ARTIFACT_BACKUP" "${ROOT_ARTIFACTS[@]}" || true
  else
    for p in "${ROOT_ARTIFACTS[@]}"; do sudo rm -f "$p" || true; done
  fi
  sudo systemctl daemon-reload || true
}

on_error() {
  local code="${1:-1}" line="${2:-0}"
  [ "$code" -eq 0 ] && return 0
  [ "$ROLLBACK_STARTED" -eq 1 ] && exit "$code"
  ROLLBACK_STARTED=1
  trap - ERR EXIT
  set +e
  echo
  echo "FEHLER: V16.1.0 Installer abgebrochen (rc=$code, line=$line, mode=$INSTALL_MODE)."
  start_support_capture "pre_rollback" "RC_${code}_LINE_${line}"
  local rollback_result="not_required_preflight"
  if [ "$INSTALLATION_STARTED" -eq 1 ]; then
    if [ "$INSTALL_MODE" = "SUPPORTED_UPDATE" ]; then
      rollback_update
      rollback_result="update_rollback_completed"
    elif [ "$INSTALL_MODE" = "CLEAN_FRESH_INSTALL" ]; then
      rollback_fresh
      rollback_result="fresh_install_rollback_completed"
    fi
  fi
  finalize_support_capture "$rollback_result" "$code"
  echo "Persistentes Installerlog: $INSTALL_LOG"
  cleanup_stage
  exit "$code"
}
trap 'on_error $? $LINENO' ERR
trap 'on_error $? $LINENO' EXIT

require_basic_contract() {
  [ "$(id -un)" = "pi" ] || { echo "FEHLER: Installer muss als Benutzer pi gestartet werden (sudo wird gezielt intern verwendet)."; return 1; }
  getent group pi >/dev/null || { echo "FEHLER: Gruppe pi fehlt."; return 1; }
  [ -d /home/pi ] || { echo "FEHLER: /home/pi fehlt."; return 1; }
  [ -d "$DOWNLOAD_DIR" ] || { echo "FEHLER: $DOWNLOAD_DIR fehlt."; return 1; }
}

verify_manifest_at() {
  local root="$1"
  [ -f "$root/$SOURCE_MANIFEST" ] || { echo "FEHLER: $SOURCE_MANIFEST fehlt."; return 1; }
  (cd "$root" && sha256sum -c "$SOURCE_MANIFEST" >/dev/null)
}

verify_build_evidence_at() {
  local root="$1"
  python3 - "$root/validation/V16_1_0_FULL_TEST.txt" "$root/validation/V16_1_0_RESOURCEWARNING_TEST.txt" <<'PY'
from pathlib import Path
import sys
for path, markers in [
    (Path(sys.argv[1]), ("RELEASE: V16.1.0", "STATUS: PASS")),
    (Path(sys.argv[2]), ("RELEASE: V16.1.0", "STATUS: PASS", "RESOURCEWARNING: ERROR")),
]:
    if not path.is_file(): raise SystemExit(f"FEHLER: Build-Testevidenz fehlt: {path}")
    text=path.read_text(encoding='utf-8')
    if any(m not in text for m in markers): raise SystemExit(f"FEHLER: Build-Testevidenz unvollständig: {path.name}")
print("Build-Testevidenz für V16.1.0 verifiziert.")
PY
}

verify_js_at() {
  local root="$1"
  if command -v node >/dev/null 2>&1; then
    node --check "$root/static/status_v2.js"
    node --check "$root/static/settings_v2.js"
    node --check "$root/static/graph_v14_1.js"
  else
    echo "INFO: Node.js ist nicht installiert; Manifestnachweis bleibt maßgeblich."
  fi
}

verify_runtime_readiness_smoke() {
  local root="$1"
  (
    trap - ERR
    cd "$root"
    ZEC_INSTALLER_PREFLIGHT=1 PYTHONWARNINGS="error::ResourceWarning" PYTHONDONTWRITEBYTECODE=1 python3 - <<'PYSMOKE'
from config_manager import DEFAULT_CONFIG
from state import ControllerState
from web_ui import build_health_payload, build_ready_payload

state = ControllerState()
max_age = int(DEFAULT_CONFIG.get("ZENDURE_COMMAND_STATE_FRESH_SECONDS", 30))
snapshot = state.readiness_snapshot(max_age)
assert snapshot["second_battery_valid"] is False
assert snapshot["second_battery_validity_reason"] == "SECOND_BATTERY_MISSING"
health = build_health_payload(snapshot)
assert health["alive"] is True
ready = build_ready_payload(DEFAULT_CONFIG, snapshot)
assert isinstance(ready, dict)
assert ready["ready"] is False
assert isinstance(ready.get("failed_checks"), list)
print("Runtime-Readiness-Smoke-Test bestanden.")
PYSMOKE
  )
}

package_preflight() {
  [ -f "$ZIP" ] || { echo "FEHLER: ZIP nicht gefunden: $ZIP"; return 1; }
  PACKAGE_SHA256="$(sha256sum "$ZIP" | awk '{print $1}')"
  unzip -tq "$ZIP" >/dev/null
  rm -rf "$STAGE_BASE"; mkdir -p "$STAGE_BASE"
  unzip -q "$ZIP" -d "$STAGE_BASE"
  [ -d "$STAGED_ROOT" ] || { echo "FEHLER: erwarteter ZIP-Root fehlt: $STAGED_ROOT"; return 1; }
  python3 "$STAGED_ROOT/tools/deployment_contract.py" identity \
    --version-file "$STAGED_ROOT/version.py" \
    --expected-version "$EXPECTED_TARGET_VERSION" \
    --expected-build "$EXPECTED_TARGET_BUILD_ID" --json \
    >"$STAGE_BASE/package_identity.json"
  echo "Package-Identität: PASS"
  verify_manifest_at "$STAGED_ROOT"
  PYTHONDONTWRITEBYTECODE=1 python3 "$STAGED_ROOT/tools/validate_release_datasheet.py" --root "$STAGED_ROOT"
  PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$STAGED_ROOT"/*.py "$STAGED_ROOT"/tools/*.py
  verify_js_at "$STAGED_ROOT"
  bash -n "$STAGED_ROOT/tools/install_zendure_controller.sh"
  verify_runtime_readiness_smoke "$STAGED_ROOT"
  bash -n "$STAGED_ROOT/tools/uninstall_zendure_controller.sh"
  bash -n "$STAGED_ROOT/tools/update_zendure_controller.sh"
  verify_build_evidence_at "$STAGED_ROOT"
}

system_dependency_preflight() {
  require_basic_contract
  local dep_json="$STAGE_BASE/dependencies.json"
  python3 "$STAGED_ROOT/tools/deployment_contract.py" dependencies --json >"$dep_json" || true
  python3 - "$dep_json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1],encoding='utf-8'))
if not p.get('ok'):
    print('FEHLER: Runtime-/Installerabhängigkeiten fehlen.')
    if p.get('missing_tools'): print('Fehlende Systemwerkzeuge:', ', '.join(p['missing_tools']))
    if p.get('missing_python'): print('Fehlende Python-Abhängigkeiten:', ', '.join(p['missing_python']))
    if p.get('install_hint'): print('Copy-Paste-Installationsbefehl:\n' + p['install_hint'])
    raise SystemExit(1)
print('Dependency-Preflight: PASS')
PY
}

classify_mode() {
  local state_json="$STAGE_BASE/state.json"
  python3 "$STAGED_ROOT/tools/deployment_contract.py" classify \
    --expected-version "$EXPECTED_SOURCE_VERSION" --expected-build "$EXPECTED_SOURCE_BUILD_ID" --json >"$state_json"
  INSTALL_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["state"])' "$state_json")"
  echo "INSTALL_MODE=$INSTALL_MODE"
  if [ "$INSTALL_MODE" = "AMBIGUOUS_OR_PARTIAL_INSTALL" ]; then
    echo "FEHLER: Unvollständige oder nicht unterstützte ZEC-Installation erkannt. Es wurden keine Änderungen vorgenommen."
    python3 - "$state_json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1])); print('Gefundene aktive Artefakte:'); [print(' - '+x) for x in p.get('found',[])]
print('Identität:',p.get('identity'))
PY
    return 1
  fi
  if [ "$FRESH_ASSERT" -eq 1 ] && [ "$INSTALL_MODE" != "CLEAN_FRESH_INSTALL" ]; then
    echo "FEHLER: --fresh-install darf ausschließlich bei CLEAN_FRESH_INSTALL verwendet werden."
    return 1
  fi
  if [ "$WEB_PORT_EXPLICIT" -eq 1 ] && [ "$INSTALL_MODE" != "CLEAN_FRESH_INSTALL" ]; then
    echo "FEHLER: --web-port ist ausschließlich für CLEAN_FRESH_INSTALL zulässig."
    return 1
  fi
}

mode_specific_preflight() {
  if [ "$INSTALL_MODE" = "CLEAN_FRESH_INSTALL" ]; then
    EFFECTIVE_WEB_PORT="$WEB_PORT"
    python3 "$STAGED_ROOT/tools/deployment_contract.py" port-check "$EFFECTIVE_WEB_PORT" --json >"$STAGE_BASE/port.json" || {
      echo "FEHLER: WEB_PORT $EFFECTIVE_WEB_PORT ist bereits belegt oder nicht bindbar."; return 1;
    }
  else
    EFFECTIVE_WEB_PORT="$(python3 "$STAGED_ROOT/tools/deployment_contract.py" endpoint --target "$TARGET" --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["port"])')"
    [ -f "$TARGET/config.json" ] || { echo "FEHLER: config.json fehlt im unterstützten Updatezustand."; return 1; }
    (cd "$STAGED_ROOT" && python3 tools/migrate_config_to_current.py --config "$TARGET/config.json" --check-only --json >"$STAGE_BASE/migration_preflight.json")
    (cd "$STAGED_ROOT" && python3 tools/v14_cutover.py verify --config "$TARGET/config.json" --runtime-root "$TARGET" --json >"$STAGE_BASE/graph_preflight.json")
  fi
}

package_preflight
system_dependency_preflight
classify_mode
mode_specific_preflight

echo "PREFLIGHT_RESULT=PASS"
echo "INSTALL_MODE=$INSTALL_MODE"
echo "WEB_PORT=$EFFECTIVE_WEB_PORT"
echo "PRODUCTIVE_CHANGES=NONE"
echo "SAFE_TO_INSTALL=yes"
echo "Persistentes Installerlog: $INSTALL_LOG"
if [ "$PREFLIGHT_ONLY" -eq 1 ]; then
  trap - ERR EXIT
  cleanup_stage
  exit 0
fi

INSTALLATION_STARTED=1
if systemctl is-active --quiet zendure-controller.service; then CONTROLLER_WAS_ACTIVE=1; fi
if systemctl is-active --quiet zendure-replay.service; then REPLAY_WAS_ACTIVE=1; fi
if systemctl is-active --quiet zendure-status-preview.service; then PREVIEW_WAS_ACTIVE=1; fi

# Root artifacts are backed up for update and fresh install; clean fresh state
# therefore records every path as absent and gives rollback an exact contract.
zec_backup_root_artifacts "$ROOT_ARTIFACT_BACKUP" "${ROOT_ARTIFACTS[@]}"
ROOT_ARTIFACTS_BACKED_UP=1

if [ "$INSTALL_MODE" = "SUPPORTED_UPDATE" ]; then
  echo "Stoppe bestehende ZEC-Dienste..."
  sudo systemctl stop zendure-controller.service || true
  sudo systemctl stop zendure-replay.service || true
  sudo systemctl stop zendure-status-preview.service || true
  echo "Erstelle vollständiges Rollback-Backup..."
  (cd /opt && sudo tar -czf "$BACKUP" zendure-controller)
  sudo chown pi:pi "$BACKUP"; chmod 600 "$BACKUP"
  BACKUP_CREATED=1
  BACKUP_SHA256="$(sha256sum "$BACKUP" | awk '{print $1}')"; BACKUP_SIZE="$(stat -c %s "$BACKUP")"
  cp "$TARGET/config.json" "$CONFIG_BACKUP"; chmod 600 "$CONFIG_BACKUP"
  echo "Bereinige obsolete, sicher regenerierbare Python-Caches..."
  python3 "$STAGED_ROOT/tools/deployment_contract.py" cleanup-obsolete-caches \
    --target "$TARGET" --staged-root "$STAGED_ROOT" --apply --json \
    >"$STAGE_BASE/obsolete_cache_cleanup.json"
  echo "Kopiere V16.1.0-Dateien; Benutzerdaten bleiben erhalten..."
  rsync -a --delete \
    --exclude 'config.json' --exclude 'config.json.last-good*' --exclude 'logs/' \
    --exclude 'config-states/' --exclude '*.sqlite3' --exclude 'zec_config_snapshots.json' \
    --exclude 'zec_runtime_events.jsonl*' --exclude '.zec_first_install_bootstrap.json' \
    --exclude 'zendure_controller.lock' --exclude 'zendure_controller.instance.lock' \
    --exclude '__pycache__/' --exclude '.pytest_cache/' \
    "$STAGED_ROOT/" "$TARGET/"
  (cd "$TARGET" && python3 tools/migrate_config_to_current.py --config config.json --json >"$STAGE_BASE/migration_result.json")
  (cd "$TARGET" && python3 tools/v14_cutover.py verify --config "$TARGET/config.json" --runtime-root "$TARGET" --json >"$STAGE_BASE/graph_verify_prestart.json")
else
  echo "Erzeuge saubere V16.1.0-Fresh-Installation ohne config.json..."
  sudo install -d -o pi -g pi -m 0750 "$TARGET"
  rsync -a --exclude '__pycache__/' --exclude '.pytest_cache/' "$STAGED_ROOT/" "$TARGET/"
  sudo chown -R pi:pi "$TARGET"
  rm -f "$TARGET/config.json" "$TARGET"/config.json.last-good* 2>/dev/null || true
  rm -rf "$TARGET/config-states"; mkdir -p "$TARGET/config-states"; chmod 700 "$TARGET/config-states"
  python3 "$TARGET/tools/deployment_contract.py" bootstrap-write --path "$BOOTSTRAP" --web-port "$EFFECTIVE_WEB_PORT" --json >/dev/null
fi

rm -rf "$TARGET/Tools"; rm -f "$TARGET/zendureController.py"
sudo chown -R pi:pi "$TARGET"
find "$TARGET" -type d -exec chmod 750 {} \;
find "$TARGET" -type f -exec chmod 640 {} \;
find "$TARGET" -type f -name '*.sh' -exec chmod 750 {} \;
find "$TARGET" -type f -path '*/tools/*.py' -exec chmod 750 {} \;
[ -f "$TARGET/config.json" ] && chmod 600 "$TARGET/config.json" || true
[ -f "$BOOTSTRAP" ] && chmod 600 "$BOOTSTRAP" || true
find "$TARGET/config-states" -maxdepth 1 -type f -name '*.zec-config.json' -exec chmod 600 {} \; 2>/dev/null || true

sudo install -o root -g root -m 0755 "$TARGET/systemd/zendure-controller-restart" /usr/local/sbin/zendure-controller-restart
sudo install -o root -g root -m 0440 "$TARGET/systemd/zendure-controller-sudoers" /etc/sudoers.d/zendure-controller
sudo visudo -cf /etc/sudoers.d/zendure-controller >/dev/null
for unit in zendure-controller.service zendure-replay.service zendure-status-preview.service; do
  sudo install -o root -g root -m 0644 "$TARGET/systemd/$unit" "/etc/systemd/system/$unit"
done
sudo systemctl daemon-reload

# Canonical service ownership: controller is enabled; replay/preview are installed
# but a fresh install must not activate them.
if [ "$INSTALL_MODE" = "CLEAN_FRESH_INSTALL" ]; then
  sudo systemctl disable zendure-replay.service zendure-status-preview.service >/dev/null 2>&1 || true
  sudo systemctl enable zendure-controller.service >/dev/null
fi

# Local post-copy verification before service start.
verify_manifest_at "$TARGET"
PYTHONDONTWRITEBYTECODE=1 python3 "$TARGET/tools/validate_release_datasheet.py" --root "$TARGET"
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile "$TARGET"/*.py "$TARGET"/tools/*.py
verify_js_at "$TARGET"
bash -n "$TARGET/tools/install_zendure_controller.sh"
bash -n "$TARGET/tools/uninstall_zendure_controller.sh"
verify_runtime_readiness_smoke "$TARGET"
if [ "$INSTALL_MODE" = "SUPPORTED_UPDATE" ]; then
  (cd "$TARGET" && python3 tools/v14_cutover.py verify --config "$TARGET/config.json" --runtime-root "$TARGET" --json >"$STAGE_BASE/graph_verify_local.json")
fi

sudo systemctl start zendure-controller.service
if [ "$INSTALL_MODE" = "SUPPORTED_UPDATE" ]; then
  [ "$REPLAY_WAS_ACTIVE" -eq 1 ] && sudo systemctl start zendure-replay.service || true
  [ "$PREVIEW_WAS_ACTIVE" -eq 1 ] && sudo systemctl start zendure-status-preview.service || true
fi

BASE_URL="http://127.0.0.1:${EFFECTIVE_WEB_PORT}"
if [ "$INSTALL_MODE" = "CLEAN_FRESH_INSTALL" ]; then
  echo "Fresh-Install-Abnahme (maximal 30 Sekunden)..."
  deadline=$((SECONDS+30)); ok=0
  while [ "$SECONDS" -lt "$deadline" ]; do
    h="$STAGE_BASE/health.json"; r="$STAGE_BASE/ready.json"
    if systemctl is-active --quiet zendure-controller.service \
      && curl -fsS --connect-timeout 1 --max-time 2 "$BASE_URL/health" >"$h" 2>/dev/null \
      && curl -fsS --connect-timeout 1 --max-time 2 "$BASE_URL/ready" >"$r" 2>/dev/null \
      && curl -fsS --connect-timeout 1 --max-time 2 "$BASE_URL/settings" >/dev/null 2>&1 \
      && python3 - "$h" "$r" <<PY
import json,sys
h=json.load(open(sys.argv[1])); r=json.load(open(sys.argv[2]))
assert h.get('alive') is True
assert h.get('version') == '$EXPECTED_TARGET_VERSION'
assert h.get('build_id') == '$EXPECTED_TARGET_BUILD_ID'
s=r.get('settings_runtime') or {}
assert s.get('startup_mode') == 'FIRST_INSTALL_SETUP', s
assert s.get('config_health') == 'missing', s
assert s.get('control_allowed') is False, s
assert r.get('ready') is False, r
PY
    then ok=1; break; fi
    sleep 1
  done
  [ "$ok" -eq 1 ] || { echo "FEHLER: Fresh-Install-Erfolgszustand innerhalb 30 s nicht erreicht."; false; }
  echo "Fresh-Install-Erfolgszustand bestätigt: FIRST_INSTALL_SETUP / ready=false / control_allowed=false."
else
  echo "Update-Abnahme am tatsächlich wirksamen Webendpoint $BASE_URL (maximal 90 Sekunden)..."
  echo "Bevorzugt wird ready=true; ein ausschließlich transienter Limit-Readback-Versatz darf die Installation nicht zurückrollen."
  READY_BODY="$STAGE_BASE/ready_body.json"
  READY_JSON="$STAGE_BASE/ready_validated.json"
  READY_DEADLINE=$((SECONDS + 90))
  READY_OK=0
  TRANSITIONAL_STREAK=0
  TRANSITIONAL_ACCEPTED=0
  while [ "$SECONDS" -lt "$READY_DEADLINE" ]; do
    if curl -fsS --connect-timeout 1 --max-time 2 "$BASE_URL/ready" >"$READY_BODY" 2>/dev/null \
       && python3 -m json.tool <"$READY_BODY" >"$READY_JSON" 2>/dev/null; then
      RESULT="$(cd "$TARGET" && python3 tools/evaluate_installation_readiness.py "$READY_BODY" 2>/dev/null || true)"
      case "$RESULT" in
        READY:*) READY_OK=1; break ;;
        TRANSITIONAL:*)
          TRANSITIONAL_STREAK=$((TRANSITIONAL_STREAK + 1))
          if [ "$TRANSITIONAL_STREAK" -ge 15 ] && [ "$SECONDS" -ge 30 ]; then
            TRANSITIONAL_ACCEPTED=1
            break
          fi
          ;;
        *) TRANSITIONAL_STREAK=0 ;;
      esac
    else
      TRANSITIONAL_STREAK=0
    fi
    sleep 1
  done
  if [ "$READY_OK" -eq 1 ]; then
    echo "Controller vollständig ready=true."
  elif [ "$TRANSITIONAL_ACCEPTED" -eq 1 ]; then
    echo "WARNUNG: Controller ist noch nicht global ready=true, aber der Produktivstart ist sicher bestätigt."
    [ -s "$READY_JSON" ] && cat "$READY_JSON"
  else
    echo "FEHLER: V16.1.0 erreichte weder ready=true noch einen stabilen sicheren Übergangszustand."
    [ -s "$READY_JSON" ] && cat "$READY_JSON"
    false
  fi
  curl -fsS --connect-timeout 1 --max-time 10 "$BASE_URL/api/graph/v1/runtime" >"$STAGE_BASE/graph_runtime.json"
  curl -fsS --connect-timeout 1 --max-time 10 "$BASE_URL/api/graph/v1/workspace" >"$STAGE_BASE/graph_workspace.json"
  python3 - "$STAGE_BASE/graph_runtime.json" "$STAGE_BASE/graph_workspace.json" <<'PY'
import json,sys
runtime=json.load(open(sys.argv[1])); workspace=json.load(open(sys.argv[2])); wr=workspace.get('runtime') or {}
assert runtime.get('control_readiness_impact') == 'NONE'
assert runtime.get('read_mode') == 'V3_NATIVE' and runtime.get('workspace_ready') is True
assert wr.get('read_mode') == 'V3_NATIVE' and wr.get('workspace_ready') is True
PY
fi

python3 - "$INSTALL_REPORT" <<PY
import json,time
from pathlib import Path
payload={
 'format':'ZEC_V16_1_0_INSTALL_REPORT_V1','status':'ok','completed_epoch_s':time.time(),
 'install_mode':'$INSTALL_MODE','source':{'version':'$EXPECTED_SOURCE_VERSION','build_id':'$EXPECTED_SOURCE_BUILD_ID'} if '$INSTALL_MODE'=='SUPPORTED_UPDATE' else None,
 'target':{'version':'$EXPECTED_TARGET_VERSION','build_id':'$EXPECTED_TARGET_BUILD_ID'},
 'web_endpoint':{'host':'127.0.0.1','port':int('$EFFECTIVE_WEB_PORT')},
 'release_backup':{'path':'$BACKUP','sha256':'$BACKUP_SHA256','size':int('$BACKUP_SIZE')} if '$INSTALL_MODE'=='SUPPORTED_UPDATE' else None,
 'config_backup':'$CONFIG_BACKUP' if '$INSTALL_MODE'=='SUPPORTED_UPDATE' else None,
 'root_artifact_backup':'$ROOT_ARTIFACT_BACKUP',
 'first_install_bootstrap':'$BOOTSTRAP' if '$INSTALL_MODE'=='CLEAN_FRESH_INSTALL' else None,
 'graph_core_v3_rebuilt': False if '$INSTALL_MODE'=='SUPPORTED_UPDATE' else None,
 'graph_core_v3_preserved': True if '$INSTALL_MODE'=='SUPPORTED_UPDATE' else None,
 'graph_control_state_backfill': ({'status':'not_run','reason':'COMPLETED_IN_SOURCE_RELEASE_V14_1_3','inserted_intervals':{}} if '$INSTALL_MODE'=='SUPPORTED_UPDATE' else None),
}
Path('$INSTALL_REPORT').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY

trap - ERR EXIT
cleanup_stage
echo "V16.1.0 erfolgreich installiert."
echo "Installationsmodus: $INSTALL_MODE"
[ "$INSTALL_MODE" = "SUPPORTED_UPDATE" ] && echo "Backup: $BACKUP" || true
[ "$INSTALL_MODE" = "SUPPORTED_UPDATE" ] && echo "Backup-SHA256: $BACKUP_SHA256" || true
echo "Installationsreport: $INSTALL_REPORT"
echo "Persistentes Installerlog: $INSTALL_LOG"
echo "Settings: http://<PI-IP>:${EFFECTIVE_WEB_PORT}/settings"
