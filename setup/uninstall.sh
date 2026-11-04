#!/usr/bin/env bash
# Remove everything this project created, and nothing else: the LOS_* schemas, logins and connections, the LOSRUST
# language alias, its BucketFS folders, the three containers and their volumes, the console app, the LOS service.
# Leaves the shared Postgres JDBC registration (vm-shared/exa/jdbc) and your downloads in .work/dl.
#   setup/uninstall.sh --yes
source "$(dirname "$0")/common.sh"
[[ "${1:-}" == "--yes" ]] || die "this deletes the project's data in Exasol, Postgres and MongoDB: run with --yes"

say "1. LOS service and console"
pkill -f "$ROOT/service/los_api.py" 2>/dev/null && ok "LOS service stopped" || ok "LOS service not running"
"$PY" - <<PY 2>/dev/null | sed 's/^/    /' || printf '    \033[0;33mnote\033[0m console app not deleted (dash-server not answering)\n'
import sys; sys.path.insert(0, "$ROOT/dash")
import deploy
_, inv = deploy.call("apps_list", {})
if deploy.APP in {a.get("name") for a in inv.get("apps", [])}:
    deploy.call("app_delete", {"name": deploy.APP, "confirmation": deploy.APP})
    print(f"ok  console app {deploy.APP} deleted")
else:
    print(f"ok  no console app {deploy.APP}")
PY

say "2. Exasol objects"
for s in LOS_CBS LOS_APPS LOS_DOCS; do xsql "DROP VIRTUAL SCHEMA IF EXISTS $s CASCADE;" >/dev/null || true; done
for s in LOS_ACCEL LOS_ADAPTERS LOS_BOOK LOS_CORE LOS_ML LOS_MONGODB_VS LOS_OPS LOS_POLICY LOS_SEM LOS_SRC; do
  xsql "DROP SCHEMA IF EXISTS $s CASCADE;" >/dev/null || true; done
for u in LOS_UW LOS_RISK LOS_INTAKE; do xsql "DROP USER IF EXISTS $u CASCADE;" >/dev/null || true; done
for c in LOS_CBS_PG LOS_DOCS_MONGO LOS_BUREAU_API; do xsql "DROP CONNECTION IF EXISTS $c;" >/dev/null || true; done
CUR=$(xsql "SELECT SYSTEM_VALUE FROM EXA_PARAMETERS WHERE PARAMETER_NAME='SCRIPT_LANGUAGES';" | tail -1)
if [[ " $CUR " == *" LOSRUST="* ]]; then
  NEW=$(printf '%s\n' $CUR | grep -v '^LOSRUST=' | tr '\n' ' ' | sed 's/ $//')
  xsql "ALTER SYSTEM SET SCRIPT_LANGUAGES = '$NEW';" >/dev/null
fi
LEFT=$(xsql "SELECT COUNT(*) FROM EXA_SCHEMAS WHERE SCHEMA_NAME IN ('LOS_CBS','LOS_APPS','LOS_DOCS','LOS_ACCEL','LOS_ADAPTERS','LOS_BOOK','LOS_CORE','LOS_ML','LOS_MONGODB_VS','LOS_OPS','LOS_POLICY','LOS_SEM','LOS_SRC');" | tail -1)
[[ "$LEFT" == "0" ]] && ok "schemas, logins, connections, LOSRUST alias removed" || die "$LEFT LOS schemas still there"

say "3. BucketFS and the bureau API files"
rm -rf "$BFS/default/los" "$BFS/default/slc/los-rustslc" "$BUREAU_DIR"
ok "default/los, default/slc/los-rustslc, vm-shared/los-bureau-api"

say "4. Containers and volumes in the VM"
"$ROOT/setup/vm.sh" 'podman rm -f los-core-pg los-docs-mongo los-bureau-api >/dev/null 2>&1; podman volume rm -f los-core los-docs >/dev/null 2>&1; true'
ok "los-core-pg, los-docs-mongo, los-bureau-api"

rm -rf "$WORK/uploads" "$ROOT/dash/cache" "$ROOT/secrets"
ok "local state removed (kept .venv and .work/dl)"
