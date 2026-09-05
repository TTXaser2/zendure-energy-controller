import hashlib
import json
from pathlib import Path
import subprocess
import sys

from graph_core_v3 import connect_graph_core

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_verify_runtime_root_reproduces_and_fixes_field_preflight_cwd_bug(tmp_path):
    runtime_root = tmp_path / "opt" / "zendure-controller"
    runtime_root.mkdir(parents=True)
    db_path = runtime_root / "logs" / "zec_measurements.sqlite3"
    conn = connect_graph_core(db_path)
    conn.close()
    config = {
        "MEASUREMENT_DB_ENABLED": True,
        "MEASUREMENT_DB_PATH": "",
        "MEASUREMENT_DB_FILE": "zec_measurements.sqlite3",
        "MEASUREMENT_LOG_STORAGE_TARGET": "internal_sd",
        "MEASUREMENT_LOG_DIR": "logs",
        "MEASUREMENT_LOG_FILE": "zendure_measurements.csv",
    }
    config_path = runtime_root / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    staging_cwd = tmp_path / "Downloads" / "zendure_controller_v14_1_2"
    staging_cwd.mkdir(parents=True)

    # Old V14.1.0 behavior: relative logs resolve below the staging CWD.
    old = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "v14_cutover.py"), "verify", "--config", str(config_path), "--json"],
        cwd=staging_cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    assert old.returncode == 2
    old_payload = json.loads(old.stdout)
    assert old_payload["reason"] == "NOT_V3"
    assert Path(old_payload["db_path"]) == staging_cwd / "logs" / "zec_measurements.sqlite3"

    before_hash = _sha256(db_path)
    before_stat = db_path.stat()
    fixed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "v14_cutover.py"),
            "verify",
            "--config",
            str(config_path),
            "--runtime-root",
            str(runtime_root),
            "--json",
        ],
        cwd=staging_cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    assert fixed.returncode == 0, fixed.stderr or fixed.stdout
    payload = json.loads(fixed.stdout)
    assert payload["status"] == "ok"
    assert payload["reason"] == "V3_NATIVE_READY"
    assert payload["verification_mode"] == "READ_ONLY"
    assert Path(payload["db_path"]) == db_path
    assert Path(payload["runtime_root"]) == runtime_root
    assert _sha256(db_path) == before_hash
    after_stat = db_path.stat()
    assert after_stat.st_size == before_stat.st_size


def test_installer_and_diagnostics_pin_graph_verify_to_installed_runtime_root():
    installer = (ROOT / "tools" / "update_zendure_controller.sh").read_text(encoding="utf-8")
    diagnostics = (ROOT / "tools" / "collect_zec_install_diagnostics.sh").read_text(encoding="utf-8")
    assert installer.count('--runtime-root "$TARGET"') >= 3
    assert 'RUNTIME_ROOT="$(cd "$(dirname "$CONFIG")" && pwd)"' in diagnostics
    assert '--runtime-root "$RUNTIME_ROOT"' in diagnostics
