#!/bin/bash
set -euo pipefail

VERSION="${1:-}"

if [ -z "$VERSION" ]; then
    echo "Bitte Version angeben, z. B.:"
    echo "$0 v12_8_12"
    exit 1
fi

ZIP="/home/pi/Downloads/zendure_controller_${VERSION}.zip"
DIR="/home/pi/Downloads/zendure_controller_${VERSION}"
TARGET="/opt/zendure-controller"
BACKUP="/home/pi/zendure-controller-backup-$(date +%Y%m%d_%H%M%S).tar.gz"
CONFIG_BACKUP="/home/pi/config.backup.$(date +%Y%m%d_%H%M%S).json"
CSV_BACKUP_DIR="/home/pi/zendure-log-backup-pre-${VERSION}-$(date +%Y%m%d_%H%M%S)"

if [ ! -f "$ZIP" ]; then
    echo "FEHLER: ZIP-Datei nicht gefunden: ${ZIP}"
    exit 1
fi

if [ ! -d "$TARGET" ]; then
    echo "FEHLER: Zielverzeichnis nicht gefunden: ${TARGET}"
    echo "Bitte Erstinstallation gemäß Benutzerhandbuch durchführen."
    exit 1
fi

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

echo "Dienststatus:"
systemctl status zendure-controller.service --no-pager -l

echo "Ready-Check:"
curl -s "http://127.0.0.1:8080/ready" | python3 -m json.tool || true

echo "Update abgeschlossen."
echo "Der optionale Analyse-Dienst wurde installiert, aber nicht aktiviert."
echo "Start bei Bedarf: sudo systemctl start zendure-replay.service"
echo "Optional dauerhaft aktivieren: sudo systemctl enable zendure-replay.service"
