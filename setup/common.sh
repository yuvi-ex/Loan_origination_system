# shellcheck shell=bash disable=SC2034  # sourced: the variables below are used by the scripts that source it
# Shared settings for the setup scripts. Source it, do not run it. Values come from config.env (+ config.local.env).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; source "$ROOT/config.env"; [[ -f "$ROOT/config.local.env" ]] && source "$ROOT/config.local.env"; set +a
WORK="$ROOT/.work"; mkdir -p "$WORK"
# Passwords of the demo source containers (Postgres admin + read-only login, MongoDB root + read-only login). Generated
# on first use into secrets/sources.env (git-ignored, mode 600) and read from there by every script, never written in
# code. setup/uninstall.sh deletes them together with the container volumes they belong to, so the two stay in step.
SOURCES_ENV="$ROOT/secrets/sources.env"
if [[ ! -f "$SOURCES_ENV" ]]; then
  (umask 077; mkdir -p "$ROOT/secrets"; python3 -c 'import secrets
for k in ("PG_ADMIN_PASSWORD", "PG_READER_PASSWORD", "MONGO_ROOT_PASSWORD", "MONGO_READER_PASSWORD"):
    print(f"{k}={secrets.token_hex(16)}")' >"$SOURCES_ENV")
fi
set -a
# shellcheck source=/dev/null
source "$SOURCES_ENV"
set +a
DEPLOY_DIR="$HOME/.exasol/personal/deployments/$EXASOL_DEPLOYMENT"
RUNTIME="$DEPLOY_DIR/local/runtime"
# BucketFS on Exasol Personal is a directory shared with the host: an upload is a copy.
BFS="$RUNTIME/vm-shared/exa/bucketfs/bfsdefault"
# The VM folder the bureau API container serves its files from (/mnt/host/los-bureau-api inside the VM).
BUREAU_DIR="$RUNTIME/vm-shared/los-bureau-api"
PY="$ROOT/.venv/bin/python"
CONSOLE="http://127.0.0.1:$DASH_SERVER_PORT/apps/$DASH_APP/"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
ok()  { printf '    \033[0;32mok\033[0m  %s\n' "$*"; }
die() { printf '\n\033[0;31merror: %s\033[0m\n' "$*" >&2; exit 1; }

# -k: accept the self-signed certificate of Exasol Personal on this machine's private VM. Do not copy -k into
# scripts that talk to a real Exasol cluster: let the CLI verify the certificate there.
# exasol connect prints CSV (a header row per statement) on stdout and exits 1 on a SQL error.
xsql()  { exasol connect -d "$EXASOL_DEPLOYMENT" -k --csv -c "$1" 2>/dev/null; }
# xfile runs a SQL file and fails (stopping the calling script) if any statement failed.
xfile() {
  local out; out=$(exasol connect -d "$EXASOL_DEPLOYMENT" -k --csv -f "$1" 2>&1 >/dev/null | grep -v '^Using .*deployment' || true)
  [[ -z "$out" ]] && return 0
  echo "$out" | sed 's/^/    /' >&2
  [[ "$out" != *rror* ]] || { printf '\033[0;31merror in %s\033[0m\n' "$1" >&2; return 1; }
}
xload() { exapump upload --profile "$EXAPUMP_PROFILE" "$1" --table "$2" 2>&1 | tail -1; }
