#!/bin/bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=../tools/root_artifact_transaction.sh
source "$ROOT/tools/root_artifact_transaction.sh"
ZEC_ROOT_DIRECT=1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
HELPER="$TMP/usr/local/sbin/zendure-controller-restart"
SUDOERS="$TMP/etc/sudoers.d/zendure-controller"
BACKUP="$TMP/backup"
mkdir -p "$(dirname "$HELPER")" "$(dirname "$SUDOERS")"
printf 'old-helper\n' >"$HELPER"
chmod 0751 "$HELPER"
# Sudoers intentionally absent before the transaction.
zec_backup_root_artifacts "$BACKUP" "$HELPER" "$SUDOERS"
printf 'new-helper\n' >"$HELPER"
chmod 0755 "$HELPER"
printf 'new-sudoers\n' >"$SUDOERS"
chmod 0440 "$SUDOERS"
zec_restore_root_artifacts "$BACKUP" "$HELPER" "$SUDOERS"
[ "$(cat "$HELPER")" = "old-helper" ]
[ "$(stat -c '%a' "$HELPER")" = "751" ]
[ ! -e "$SUDOERS" ]
echo "root artifact rollback fixture: PASS"
