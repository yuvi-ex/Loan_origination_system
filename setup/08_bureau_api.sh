#!/usr/bin/env bash
# The credit bureau as a live API: the mock bureau's files (data/bureau_api.py), its container (setup/00_sources_vm.sh),
# the CONNECTION holding its address and key, the calling UDF and the response log (sql/55_bureau_api.sql), and the
# grants: only LOS_INTAKE may run the UDF, and the connection may be used only by that script.
source "$(dirname "$0")/common.sh"
ENVF="$ROOT/secrets/app_users.env"
[[ -f "$ENVF" ]] || die "run setup/05_governance.py first (it creates secrets/app_users.env)"
if ! grep -q '^BUREAU_API_KEY=' "$ENVF"; then      # generated once, never printed
  (umask 077; echo "BUREAU_API_KEY=bk_$(python3 -c 'import secrets; print(secrets.token_hex(24))')" >> "$ENVF")
fi
KEY=$(grep '^BUREAU_API_KEY=' "$ENVF" | cut -d= -f2)

say "1. Bureau API files + container"
"$PY" "$ROOT/data/bureau_api.py" | sed 's/^/    /'
"$ROOT/setup/00_sources_vm.sh" >/dev/null
"$ROOT/setup/vm.sh" "podman restart los-bureau-api >/dev/null"; sleep 2
ok "los-bureau-api in the VM, port $BUREAU_PORT"

say "2. Connection, UDF, response log"
xsql "CREATE OR REPLACE CONNECTION LOS_BUREAU_API TO 'http://$SRC_HOST:$BUREAU_PORT' USER 'los' IDENTIFIED BY '$KEY'" >/dev/null
xfile "$ROOT/sql/55_bureau_api.sql"
xsql "GRANT EXECUTE ON LOS_SRC.BUREAU_API TO LOS_INTAKE" >/dev/null
xsql "GRANT ACCESS ON CONNECTION LOS_BUREAU_API FOR SCRIPT LOS_SRC.BUREAU_API TO LOS_INTAKE" >/dev/null
xsql "GRANT INSERT ON LOS_SRC.BUREAU_REPORTS TO LOS_INTAKE" >/dev/null
ok "$(xsql "SELECT HTTP_STATUS || ' ' || REPORT_ID || ' score ' || BUREAU_SCORE || ' in ' || MS || ' ms' FROM (SELECT LOS_SRC.BUREAU_API('BKRPR4417K'))" | tail -1)"
