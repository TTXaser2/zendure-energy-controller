#!/bin/bash
# Exact backup/restore transaction for privileged installer artifacts.
set -Eeuo pipefail

zec_root_run() {
    if [ "${ZEC_ROOT_DIRECT:-0}" = "1" ]; then
        "$@"
    else
        sudo "$@"
    fi
}

zec_root_key() {
    printf '%s' "$1" | sed 's#^/##; s#/#__#g'
}

zec_backup_root_artifacts() {
    local backup_dir="$1"; shift
    zec_root_run rm -rf "$backup_dir"
    zec_root_run mkdir -p "$backup_dir/files" "$backup_dir/state"
    local path key
    for path in "$@"; do
        key="$(zec_root_key "$path")"
        if zec_root_run test -e "$path"; then
            printf 'present\n' | zec_root_run tee "$backup_dir/state/$key" >/dev/null
            zec_root_run cp -a --parents "$path" "$backup_dir/files"
        else
            printf 'absent\n' | zec_root_run tee "$backup_dir/state/$key" >/dev/null
        fi
    done
}

zec_restore_root_artifacts() {
    local backup_dir="$1"; shift
    local path key state saved
    for path in "$@"; do
        key="$(zec_root_key "$path")"
        state="$(zec_root_run cat "$backup_dir/state/$key" 2>/dev/null || true)"
        zec_root_run rm -f "$path"
        if [ "$state" = "present" ]; then
            saved="$backup_dir/files$path"
            zec_root_run mkdir -p "$(dirname "$path")"
            zec_root_run cp -a "$saved" "$path"
        elif [ "$state" != "absent" ]; then
            echo "FEHLER: Root-Artefakt-Backupzustand fehlt für $path" >&2
            return 1
        fi
    done
}
