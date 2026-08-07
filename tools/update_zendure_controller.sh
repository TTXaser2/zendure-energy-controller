#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=root_artifact_transaction.sh
source "$SCRIPT_DIR/root_artifact_transaction.sh"

VERSION="${1:-}"
EXPECTED_VERSION="v12_11_4"
EXPECTED_SOURCE_RC19="12.11.2-rc19"
EXPECTED_SOURCE_FIX5_VERSION="12.11.2-rc20"
EXPECTED_SOURCE_FIX5_BUILD_ID="rc20-audit-fix5-20260806"
EXPECTED_SOURCE_FIX6_VERSION="12.11.2-rc20"
EXPECTED_SOURCE_FIX6_BUILD_ID="rc20-audit-fix6-20260806"
EXPECTED_SOURCE_V12113_VERSION="12.11.3"
EXPECTED_SOURCE_V12113_BUILD_ID="v12.11.3-20260806"
EXPECTED_TARGET_BUILD_ID="v12.11.4-20260807"

if [ "$VERSION" != "$EXPECTED_VERSION" ]; then
    echo "FEHLER: Dieses Update-Skript unterstützt V12.11.3 sowie die dokumentierten Fix-6-/Recovery-Ausgangsstände als Quelle für V12.11.4."
    echo "Aufruf: $0 ${EXPECTED_VERSION}"
    exit 1
fi

ZIP="/home/pi/Downloads/zendure_controller_${VERSION}.zip"
DIR="/home/pi/Downloads/zendure_controller_${VERSION}"
TARGET="/opt/zendure-controller"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="/home/pi/zendure-controller-backup-${STAMP}.tar.gz"
CONFIG_BACKUP="/home/pi/config.pre-v12.11.4.${STAMP}.json"
ROOT_ARTIFACT_BACKUP="/var/backups/zec-v12.11.4-root-artifacts-${STAMP}"
RESTART_HELPER_DEST="/usr/local/sbin/zendure-controller-restart"
SUDOERS_DEST="/etc/sudoers.d/zendure-controller"
ROLLBACK_STARTED=0
BACKUP_CREATED=0
ROOT_ARTIFACTS_BACKED_UP=0
INSTALLATION_STARTED=0

CONTROLLER_WAS_ACTIVE=0
REPLAY_WAS_ACTIVE=0
PREVIEW_WAS_ACTIVE=0

read_installed_identity() {
    python3 - "$TARGET/version.py" <<'PY'
import re
import sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.is_file():
    raise SystemExit(2)
text = path.read_text(encoding="utf-8")
def value(name):
    match = re.search(rf'^{name}\s*=\s*["\']([^"\']*)["\']', text, flags=re.M)
    return match.group(1) if match else ""
version = value("APP_VERSION")
if not version:
    raise SystemExit(3)
print(version)
print(value("APP_BUILD_ID"))
PY
}


restore_services() {
    if [ "$CONTROLLER_WAS_ACTIVE" -eq 1 ]; then sudo systemctl start zendure-controller.service || true; fi
    if [ "$REPLAY_WAS_ACTIVE" -eq 1 ]; then sudo systemctl start zendure-replay.service || true; fi
    if [ "$PREVIEW_WAS_ACTIVE" -eq 1 ]; then sudo systemctl start zendure-status-preview.service || true; fi
}

backup_root_artifacts() {
    zec_backup_root_artifacts "$ROOT_ARTIFACT_BACKUP" "$RESTART_HELPER_DEST" "$SUDOERS_DEST"
    ROOT_ARTIFACTS_BACKED_UP=1
}

restore_root_artifacts() {
    [ "$ROOT_ARTIFACTS_BACKED_UP" -eq 1 ] || return 0
    zec_restore_root_artifacts "$ROOT_ARTIFACT_BACKUP" "$RESTART_HELPER_DEST" "$SUDOERS_DEST"
    if sudo test -e "$SUDOERS_DEST"; then
        sudo visudo -cf "$SUDOERS_DEST" >/dev/null
    fi
}

recover_on_error() {
    local exit_code="${1:-$?}"
    if [ "${BASH_SUBSHELL:-0}" -gt 0 ]; then
        return "$exit_code"
    fi
    trap - ERR EXIT
    set +e
    if [ "$ROLLBACK_STARTED" -eq 1 ]; then
        exit "$exit_code"
    fi
    ROLLBACK_STARTED=1
    echo
    if [ "$INSTALLATION_STARTED" -eq 0 ]; then
        echo "FEHLER: V12.11.4-Paketvorprüfung wurde abgebrochen."
        echo "Die Produktivinstallation wurde noch nicht begonnen; Dienste und /opt/zendure-controller blieben unverändert."
        exit "$exit_code"
    fi
    echo "FEHLER: V12.11.4-Update wurde während der Produktivinstallation abgebrochen. Starte automatischen Rollback."
    sudo systemctl stop zendure-controller.service zendure-replay.service zendure-status-preview.service >/dev/null 2>&1 || true
    if [ "$BACKUP_CREATED" -eq 1 ] && [ -f "$BACKUP" ]; then
        sudo rm -rf "$TARGET"
        sudo tar -xzf "$BACKUP" -C /opt
        if [ -f "$TARGET/systemd/zendure-controller.service" ]; then
            sudo install -o root -g root -m 0644 "$TARGET/systemd/zendure-controller.service" /etc/systemd/system/zendure-controller.service
        fi
        if [ -f "$TARGET/systemd/zendure-replay.service" ]; then
            sudo install -o root -g root -m 0644 "$TARGET/systemd/zendure-replay.service" /etc/systemd/system/zendure-replay.service
        fi
        if [ -f "$TARGET/systemd/zendure-status-preview.service" ]; then
            sudo install -o root -g root -m 0644 "$TARGET/systemd/zendure-status-preview.service" /etc/systemd/system/zendure-status-preview.service
        fi
        sudo systemctl daemon-reload || true
        echo "Installationsverzeichnis aus Backup wiederhergestellt: $BACKUP"
    else
        echo "Die Dienste wurden gestoppt, aber Produktivdateien noch nicht ersetzt; kein Datei-Rollback erforderlich."
    fi
    restore_root_artifacts || true
    restore_services
    sudo systemctl status zendure-controller.service --no-pager -l || true
    exit "$exit_code"
}
trap 'recover_on_error $?' ERR

verify_source_manifest() {
    [ -f "$DIR/V12_11_4_SOURCE_MANIFEST.sha256" ] || {
        echo "FEHLER: V12_11_4_SOURCE_MANIFEST.sha256 fehlt im Paket."
        return 1
    }
    (
        trap - ERR
        cd "$DIR"
        sha256sum -c V12_11_4_SOURCE_MANIFEST.sha256 >/dev/null
    )
}

verify_javascript_syntax_if_available() {
    if command -v node >/dev/null 2>&1; then
        node --check static/status_v2.js
        node --check static/settings_v2.js
        echo "JavaScript-Syntax lokal mit Node.js geprüft."
    else
        echo "INFO: Node.js ist nicht installiert; keine Produktivabhängigkeit."
        echo "Die JavaScript-Dateien werden über das Source-Manifest gegen den buildseitig geprüften Inhalt verifiziert."
    fi
}


verify_runtime_readiness_smoke() {
    local root="$1"
    (
        trap - ERR
        cd "$root"
        PYTHONDONTWRITEBYTECODE=1 python3 - <<'PYSMOKE'
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

[ -f "$ZIP" ] || { echo "FEHLER: ZIP nicht gefunden: $ZIP"; exit 1; }
[ -d "$TARGET" ] || { echo "FEHLER: Zielverzeichnis nicht gefunden: $TARGET"; exit 1; }
[ -f "$TARGET/config.json" ] || { echo "FEHLER: Produktive config.json fehlt: $TARGET/config.json"; exit 1; }

mapfile -t INSTALLED_IDENTITY < <(read_installed_identity)
INSTALLED_VERSION="${INSTALLED_IDENTITY[0]:-}"
INSTALLED_BUILD_ID="${INSTALLED_IDENTITY[1]:-}"
SOURCE_MODE=""
if [ "$INSTALLED_VERSION" = "$EXPECTED_SOURCE_RC19" ]; then
    SOURCE_MODE="RC19"
elif [ "$INSTALLED_VERSION" = "$EXPECTED_SOURCE_FIX5_VERSION" ] && [ "$INSTALLED_BUILD_ID" = "$EXPECTED_SOURCE_FIX5_BUILD_ID" ]; then
    SOURCE_MODE="RC20_FIX5"
elif [ "$INSTALLED_VERSION" = "$EXPECTED_SOURCE_FIX6_VERSION" ] && [ "$INSTALLED_BUILD_ID" = "$EXPECTED_SOURCE_FIX6_BUILD_ID" ]; then
    SOURCE_MODE="RC20_FIX6"
elif [ "$INSTALLED_VERSION" = "$EXPECTED_SOURCE_V12113_VERSION" ] && [ "$INSTALLED_BUILD_ID" = "$EXPECTED_SOURCE_V12113_BUILD_ID" ]; then
    SOURCE_MODE="V12_11_3"
else
    echo "FEHLER: Nicht unterstützter Ausgangsstand: Version=${INSTALLED_VERSION}, Build-ID=${INSTALLED_BUILD_ID:-nicht gesetzt}"
    echo "Erlaubt sind exakt V12.11.3, RC20 Fix 6, RC20 Fix 5 oder RC19."
    exit 1
fi
echo "Ausgangsstand erkannt: ${SOURCE_MODE} (${INSTALLED_VERSION}${INSTALLED_BUILD_ID:+ / ${INSTALLED_BUILD_ID}})"

if systemctl is-active --quiet zendure-controller.service; then CONTROLLER_WAS_ACTIVE=1; fi
if systemctl is-active --quiet zendure-replay.service; then REPLAY_WAS_ACTIVE=1; fi
if systemctl is-active --quiet zendure-status-preview.service; then PREVIEW_WAS_ACTIVE=1; fi

echo "V12.11.4-Paket vor dem Stoppen des Produktivdienstes entpacken und prüfen..."
rm -rf "$DIR"
unzip -q "$ZIP" -d /home/pi/Downloads
[ -d "$DIR" ] || { echo "FEHLER: erwarteter ZIP-Root fehlt: $DIR"; exit 1; }
[ -f "$DIR/version.py" ] || { echo "FEHLER: version.py fehlt im Paket"; exit 1; }
read_package_identity() {
    python3 - "$DIR/version.py" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding='utf-8')
def value(name):
    match = re.search(rf'^{name}\s*=\s*["\']([^"\']+)["\']', text, re.M)
    return match.group(1) if match else ''
print(value('APP_VERSION'))
print(value('APP_BUILD_ID'))
PY
}
mapfile -t PACKAGE_IDENTITY < <(read_package_identity)
TARGET_PACKAGE_VERSION="${PACKAGE_IDENTITY[0]:-}"
TARGET_PACKAGE_BUILD_ID="${PACKAGE_IDENTITY[1]:-}"
[ "$TARGET_PACKAGE_VERSION" = "12.11.4" ] || { echo "FEHLER: Paket meldet Version ${TARGET_PACKAGE_VERSION}"; exit 1; }
[ "$TARGET_PACKAGE_BUILD_ID" = "$EXPECTED_TARGET_BUILD_ID" ] || { echo "FEHLER: Paket meldet Build-ID ${TARGET_PACKAGE_BUILD_ID}"; exit 1; }

verify_source_manifest
(
    trap - ERR
    cd "$DIR"
    python3 -m py_compile *.py tools/*.py
    verify_javascript_syntax_if_available
    bash -n tools/update_zendure_controller.sh
    verify_runtime_readiness_smoke "$DIR"
    python3 tools/migrate_rc19_to_rc20.py --config "$TARGET/config.json" --check-only --json >/tmp/zec_rc20_migration_preflight.json
    ZEC_INSTALLER_PREFLIGHT=1 PYTHONWARNINGS="error::ResourceWarning" python3 -m unittest discover -s tests -q
)

echo "Paketpreflight und Config-Migrationspreflight bestanden."
INSTALLATION_STARTED=1
INSTALL_START_EPOCH="$(date +%s)"
echo "Stoppe Dienste..."
sudo systemctl stop zendure-controller.service || true
sudo systemctl stop zendure-replay.service || true
sudo systemctl stop zendure-status-preview.service || true

echo "Erstelle vollständiges Rollback-Backup..."
cd /opt
sudo tar -czf "$BACKUP" zendure-controller
sudo chown pi:pi "$BACKUP"
chmod 600 "$BACKUP"
BACKUP_CREATED=1
cp "$TARGET/config.json" "$CONFIG_BACKUP"
chmod 600 "$CONFIG_BACKUP"
backup_root_artifacts

echo "Kopiere V12.11.4-Dateien; config.json, Last-Good und Laufzeitdaten bleiben erhalten..."
rsync -a \
  --exclude 'config.json' \
  --exclude 'config.json.last-good*' \
  --exclude 'logs/' \
  --exclude '*.sqlite3' \
  --exclude 'zec_config_snapshots.json' \
  --exclude 'zec_runtime_events.jsonl*' \
  --exclude 'zendure_controller.lock' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  "$DIR/" "$TARGET/"

if [ -d "$DIR/tests" ]; then
    mkdir -p "$TARGET/tests"
    rsync -a --delete "$DIR/tests/" "$TARGET/tests/"
fi

cd "$TARGET"
echo "Führe idempotente bestehende Configmigration aus..."
python3 tools/migrate_rc19_to_rc20.py --config config.json --json | tee /tmp/zec_rc20_migration_result.json

rm -rf "$TARGET/Tools"
rm -f "$TARGET/zendureController.py"

sudo chown -R pi:pi "$TARGET"
find "$TARGET" -type d -exec chmod 750 {} \;
find "$TARGET" -type f -exec chmod 640 {} \;
find "$TARGET" -type f -name "*.sh" -exec chmod 750 {} \;
find "$TARGET" -type f -path '*/tools/*.py' -exec chmod 750 {} \;
chmod 600 "$TARGET/config.json"
chmod 600 "$TARGET"/config.json.last-good* 2>/dev/null || true

# Fixed, root-owned restart contract. The configured free-form command no longer exists.
sudo install -o root -g root -m 0755 "$TARGET/systemd/zendure-controller-restart" "$RESTART_HELPER_DEST"
sudo install -o root -g root -m 0440 "$TARGET/systemd/zendure-controller-sudoers" "$SUDOERS_DEST"
sudo visudo -cf "$SUDOERS_DEST" >/dev/null

for unit in zendure-controller.service zendure-replay.service zendure-status-preview.service; do
    if [ -f "$TARGET/systemd/$unit" ]; then
        sudo install -o root -g root -m 0644 "$TARGET/systemd/$unit" "/etc/systemd/system/$unit"
    fi
done
sudo systemctl daemon-reload

echo "Finale lokale Prüfung im Installationsverzeichnis..."
python3 -m py_compile *.py tools/*.py
verify_javascript_syntax_if_available
bash -n tools/update_zendure_controller.sh
verify_runtime_readiness_smoke "$TARGET"
ZEC_INSTALLER_PREFLIGHT=1 PYTHONWARNINGS="error::ResourceWarning" python3 -m unittest discover -s tests -q

echo "Starte Controller..."
sudo systemctl start zendure-controller.service
if [ "$REPLAY_WAS_ACTIVE" -eq 1 ]; then sudo systemctl start zendure-replay.service; fi
if [ "$PREVIEW_WAS_ACTIVE" -eq 1 ]; then sudo systemctl start zendure-status-preview.service; fi

READY_BODY="$(mktemp)"
READY_JSON="$(mktemp)"
cleanup_tmp() { rm -f "$READY_BODY" "$READY_JSON"; }
trap cleanup_tmp EXIT
echo "Installations-Abnahme (maximal 90 Sekunden):"
echo "Bevorzugt wird ready=true; ein ausschließlich transienter Limit-Readback-Versatz darf die Installation nicht zurückrollen."
READY_DEADLINE=$((SECONDS + 90))
READY_OK=0
TRANSITIONAL_STREAK=0
TRANSITIONAL_ACCEPTED=0
while [ "$SECONDS" -lt "$READY_DEADLINE" ]; do
    if curl -fsS --connect-timeout 1 --max-time 2 http://127.0.0.1:8080/ready >"$READY_BODY" 2>/dev/null \
       && python3 -m json.tool <"$READY_BODY" >"$READY_JSON" 2>/dev/null; then
        RESULT="$(python3 tools/evaluate_installation_readiness.py "$READY_BODY")"
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
    echo "Ausschließlich ein transienter INPUT_LIMIT/OUTPUT_LIMIT-Readback beziehungsweise ein ungefährlicher Beobachtungszustand ist noch offen."
    echo "Kein Rollback: Controller, Datenquellen, Command-State, statische Invarianten und Telemetrie sind gesund."
    [ -s "$READY_JSON" ] && cat "$READY_JSON"
else
    echo "FEHLER: V12.11.4 erreichte weder ready=true noch einen stabilen sicheren Übergangszustand."
    [ -s "$READY_JSON" ] && cat "$READY_JSON"
    journalctl -u zendure-controller.service --since "@$INSTALL_START_EPOCH" --no-pager || true
    false
fi

trap - ERR
cleanup_tmp
trap - EXIT

echo "Update abgeschlossen und Installations-Abnahme erfolgreich."
echo "V12.11.4 erfolgreich installiert."
echo "Backup: $BACKUP"
echo "Config-Backup: $CONFIG_BACKUP"
echo "Root-Artefakt-Backup: $ROOT_ARTIFACT_BACKUP"
echo "Settings: http://<PI-IP>:8080/settings"
