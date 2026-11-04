#!/usr/bin/env bash
# The semantic layer made explicit + the data contracts: vocabulary and contract tables (sql/50_semantic.sql), the
# contract checks as a view over the live sources (the SQL lives in service/sqlq.py, one copy for the view and the
# per-upload check), rule R13, the decision views again (they read the results), a first full run, and grants.
source "$(dirname "$0")/common.sh"

say "1. Vocabulary, contracts, rule R13 (sql/50_semantic.sql)"
xfile "$ROOT/sql/50_semantic.sql"
ok "$(xsql 'SELECT COUNT(*) FROM LOS_SEM.TERMS' | tail -1) terms, $(xsql 'SELECT COUNT(*) FROM LOS_SEM.CONTRACTS' | tail -1) contracts"

say "2. The checks, as a view over the live sources"
V="$WORK/contract_view.sql"
(cd "$ROOT/service" && "$PY" -c 'import sqlq; print("CREATE OR REPLACE VIEW LOS_SEM.CONTRACT_CHECKS_LIVE AS\n" + sqlq.q_contract_checks() + ";")') > "$V"
xfile "$V"
ok "LOS_SEM.CONTRACT_CHECKS_LIVE"

say "3. Decision views (rule R13 reads the results)"
xfile "$ROOT/sql/30_decisions.sql"
ok "sql/30_decisions.sql"

say "4. Check every contract for every application"
T0=$("$PY" -c 'import time; print(time.time())')
xsql "DELETE FROM LOS_SEM.CONTRACT_RESULTS" >/dev/null
xsql "$(cd "$ROOT/service" && "$PY" -c 'import sqlq; print(sqlq.Q_CONTRACT_RUN)')" >/dev/null
SECS=$("$PY" -c "import time; print(round(time.time() - $T0, 1))")
read -r APPS CHECKS BREACHES <<<"$(xsql "SELECT COUNT(DISTINCT APP_ID), COUNT(*), SUM(CASE WHEN PASSED THEN 0 ELSE 1 END) FROM LOS_SEM.CONTRACT_RESULTS" | tail -1 | tr ',' ' ')"
xsql "INSERT INTO LOS_SEM.CONTRACT_RUNS VALUES (CURRENT_TIMESTAMP, $APPS, $CHECKS, $BREACHES, $SECS)" >/dev/null
ok "$CHECKS checks on $APPS applications in ${SECS} s: $BREACHES breaches"

say "5. App logins"
"$PY" "$ROOT/setup/05_governance.py"
