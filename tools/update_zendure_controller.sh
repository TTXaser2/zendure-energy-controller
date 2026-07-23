#!/bin/bash
set -euo pipefail

VERSION="${1:-}"

if [ -z "$VERSION" ]; then
    echo "Bitte Version angeben, z. B.:"
    echo "$0 v12_10_0_rc6"
    exit 1
fi

ZIP="/home/pi/Downloads/zendure_controller_${VERSION}.zip"
DIR="/home/pi/Downloads/zendure_controller_${VERSION}"
TARGET="/opt/zendure-controller"
BACKUP="/home/pi/zendure-controller-backup-$(date +%Y%m%d_%H%M%S).tar.gz"
CONFIG_BACKUP="/home/pi/config.backup.$(date +%Y%m%d_%H%M%S).json"

if [ ! -f "$ZIP" ]; then
    echo "FEHLER: ZIP-Datei nicht gefunden: ${ZIP}"
    exit 1
fi

if [ ! -d "$TARGET" ]; then
    echo "FEHLER: Zielverzeichnis nicht gefunden: ${TARGET}"
    echo "Bitte Erstinstallation gemäß Benutzerhandbuch durchführen."
    exit 1
fi

CONTROLLER_WAS_ACTIVE=0
REPLAY_WAS_ACTIVE=0
if systemctl is-active --quiet zendure-controller.service; then
    CONTROLLER_WAS_ACTIVE=1
fi
if systemctl is-active --quiet zendure-replay.service; then
    REPLAY_WAS_ACTIVE=1
fi

recover_on_error() {
    echo "FEHLER: Update wurde abgebrochen."
    echo "Versuche, zuvor laufende Dienste wieder zu starten..."
    if [ "$CONTROLLER_WAS_ACTIVE" -eq 1 ]; then
        sudo systemctl start zendure-controller.service || true
    fi
    if [ "$REPLAY_WAS_ACTIVE" -eq 1 ]; then
        sudo systemctl start zendure-replay.service || true
    fi
    echo "Recovery-Hinweis: Falls ein Dienst nicht startet, Backup liegt unter: ${BACKUP}"
    sudo systemctl status zendure-controller.service --no-pager -l || true
    if [ "$REPLAY_WAS_ACTIVE" -eq 1 ]; then
        sudo systemctl status zendure-replay.service --no-pager -l || true
    fi
}
trap recover_on_error ERR

echo "Update Zendure Energy Controller auf ${VERSION}"
echo "ZIP:    ${ZIP}"
echo "Ziel:   ${TARGET}"
echo "Backup: ${BACKUP}"

echo "Stoppe Dienste..."
sudo systemctl stop zendure-controller.service || true
sudo systemctl stop zendure-replay.service || true

echo "Erstelle Backup des aktuellen Installationsverzeichnisses..."
cd /opt
tar -czf "$BACKUP" zendure-controller

if [ -f "${TARGET}/config.json" ]; then
    echo "Sichere config.json separat..."
    cp "${TARGET}/config.json" "$CONFIG_BACKUP"
fi

if [ "$VERSION" = "v12_7" ]; then
    echo "V12.7 CSV-Schemawechsel: verschiebe vorhandene CSV-Dateien aus dem aktiven Logverzeichnis..."
    CSV_DIR=$(TARGET="$TARGET" python3 - <<'PY'
import json
import os
from pathlib import Path

target = Path(os.environ["TARGET"]).resolve()
cfg_path = target / "config.json"
log_dir = "logs"
if cfg_path.exists():
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        log_dir = str(cfg.get("CSV_LOG_DIR") or "logs")
    except Exception:
        pass
p = Path(log_dir)
if not p.is_absolute():
    p = target / p
print(str(p.resolve()))
PY
)
    if [ -d "$CSV_DIR" ]; then
        mapfile -t CSV_FILES < <(find "$CSV_DIR" -maxdepth 1 -type f -name "*.csv" -print)
        if [ "${#CSV_FILES[@]}" -gt 0 ]; then
            mkdir -p "$CSV_BACKUP_DIR"
            printf '%s\n' "${CSV_FILES[@]}" | while IFS= read -r file; do
                mv "$file" "$CSV_BACKUP_DIR/"
            done
            echo "CSV-Backup: ${CSV_BACKUP_DIR}"
        else
            echo "Keine vorhandenen CSV-Dateien gefunden."
        fi
    else
        echo "CSV-Logverzeichnis existiert noch nicht: ${CSV_DIR}"
    fi
fi


echo "Entpacke Update..."
cd /home/pi/Downloads
rm -rf "$DIR"
unzip -q "$ZIP"

if [ ! -d "$DIR" ]; then
    echo "FEHLER: Entpackter Ordner nicht gefunden: ${DIR}"
    exit 1
fi

echo "Kopiere neue Dateien..."
rsync -av \
  --exclude "config.json" \
  --exclude "config.json.last-good" \
  --exclude "logs/" \
  --exclude "__pycache__/" \
  "$DIR/" \
  "$TARGET/"

echo "Bereinige obsolete Tests im Zielverzeichnis..."
if [ -d "$DIR/tests" ]; then
    mkdir -p "$TARGET/tests"
    rsync -a --delete "$DIR/tests/" "$TARGET/tests/"
fi

echo "Migriere Logging-Config auf MEASUREMENT_LOG_MODE, falls alte CSV_LOG_*-Keys vorhanden sind..."
cd "$TARGET"
python3 - <<'PY'
from config_manager import ConfigManager
cm = ConfigManager("config.json")
cm.load()
print("Config geprüft/migriert.")
PY

echo "Bereinige alte V12.6-Kompatibilitätsreste..."
rm -rf "${TARGET}/Tools"
rm -f "${TARGET}/zendureController.py"

echo "Setze Rechte..."
sudo chown -R pi:pi "$TARGET"
find "$TARGET" -type d -exec chmod 750 {} \;
find "$TARGET" -type f -exec chmod 640 {} \;
find "$TARGET" -type f -name "*.sh" -exec chmod 750 {} \;
find "$TARGET" -type f -path "*/tools/*.py" -exec chmod 750 {} \;

echo "Syntaxcheck..."
cd "$TARGET"
python3 -m py_compile *.py
python3 -m py_compile tools/*.py

echo "Automatisierte Tests..."
python3 -m unittest discover -s tests

echo "Aktualisiere systemd-Dateien, falls vorhanden..."
if [ -f "${TARGET}/systemd/zendure-controller.service" ]; then
    sudo cp "${TARGET}/systemd/zendure-controller.service" /etc/systemd/system/zendure-controller.service
fi
if [ -f "${TARGET}/systemd/zendure-replay.service" ]; then
    sudo cp "${TARGET}/systemd/zendure-replay.service" /etc/systemd/system/zendure-replay.service
fi
sudo systemctl daemon-reload

echo "Starte Live-Dienst..."
sudo systemctl start zendure-controller.service

if [ "$REPLAY_WAS_ACTIVE" -eq 1 ]; then
    echo "Starte zuvor aktiven Analyse-Dienst..."
    sudo systemctl start zendure-replay.service
fi

trap - ERR

echo "Dienststatus:"
systemctl status zendure-controller.service --no-pager -l
if [ "$REPLAY_WAS_ACTIVE" -eq 1 ]; then
    systemctl status zendure-replay.service --no-pager -l
fi

echo "Ready-Check (maximal 20 Sekunden):"
READY_OK=0
READY_BODY="$(mktemp)"
READY_JSON="$(mktemp)"
READY_DEADLINE=$((SECONDS + 20))
READY_ATTEMPT=0
while [ "$SECONDS" -lt "$READY_DEADLINE" ]; do
    READY_ATTEMPT=$((READY_ATTEMPT + 1))
    if curl -fsS --connect-timeout 1 --max-time 1 "http://127.0.0.1:8080/ready" > "$READY_BODY" 2>/dev/null \
       && python3 -m json.tool < "$READY_BODY" > "$READY_JSON" 2>/dev/null; then
        echo "Ready nach Versuch ${READY_ATTEMPT}:"
        cat "$READY_JSON"
        READY_OK=1
        break
    fi
    sleep 0.5
done
rm -f "$READY_BODY" "$READY_JSON"

if [ "$READY_OK" -ne 1 ]; then
    echo "FEHLER: Der Controller-Dienst läuft, aber /ready lieferte innerhalb von 20 Sekunden kein gültiges JSON."
    echo "Bitte unmittelbar prüfen:"
    echo "  systemctl status zendure-controller.service --no-pager -l"
    echo "  journalctl -u zendure-controller.service -n 100 --no-pager"
    exit 1
fi

echo "Update abgeschlossen und Ready-Check erfolgreich."
if [ "$REPLAY_WAS_ACTIVE" -eq 1 ]; then
    echo "Der Analyse-Dienst war vor dem Update aktiv und wurde wieder gestartet."
else
    echo "Der optionale Analyse-Dienst wurde installiert, aber nicht aktiviert."
    echo "Start bei Bedarf: sudo systemctl start zendure-replay.service"
    echo "Optional dauerhaft aktivieren: sudo systemctl enable zendure-replay.service"
fi
