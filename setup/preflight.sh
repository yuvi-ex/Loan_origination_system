#!/usr/bin/env bash
# Demo-day check: GO / NO-GO, and it fixes what it safely can. Run before every demo:
#   setup/preflight.sh            (add --reset to also empty the decision log and reset the policy)
# Self-heals: starts Exasol, starts the three source containers inside the VM (they do not survive a VM restart),
# starts the LOS service. Then proves every source answers with a real query, and that the console is up.
source "$(dirname "$0")/common.sh"
FAIL=0
bad() { printf '    \033[0;31mNO\033[0m  %s\n' "$*"; FAIL=1; }

say "1. Exasol"
xsql "SELECT 1;" | grep -q 1 || exasol start -d "$EXASOL_DEPLOYMENT" >/dev/null 2>&1 || exakit start >/dev/null 2>&1 || true
xsql "SELECT 1;" | grep -q 1 && ok "database answers" || bad "database not reachable: exakit start"

say "2. Core banking, document store and bureau API inside the VM"
"$ROOT/setup/vm.sh" 'podman start los-core-pg los-docs-mongo los-bureau-api >/dev/null 2>&1; podman ps --filter name=los- --format "{{.Names}} {{.Status}}"' | sed 's/^/    /'

say "3. Each source, through Exasol"
sleep 3
check() { local n; n=$(xsql "$2" | tail -1); [[ "$n" =~ ^[0-9]+$ && "$n" -gt 0 ]] && ok "$1: $n" || bad "$1: $(exasol connect -d "$EXASOL_DEPLOYMENT" -k --csv -c "$2" 2>&1 | grep -i error | cut -c1-160)"; }
check "core banking (Postgres), Karthik's salary months" "SELECT COUNT(*) FROM LOS_SRC.SALARY_MONTHLY WHERE ACCT_NO = '50100293844117';"
check "core banking (Postgres), Divya's salary months"   "SELECT COUNT(*) FROM LOS_SRC.SALARY_MONTHLY WHERE ACCT_NO = '50100417730962';"
check "document store (MongoDB), applications"         "SELECT COUNT(*) FROM LOS_SRC.APPLICATIONS;"
check "credit bureau file (both sample PANs)"          "SELECT COUNT(*) FROM LOS_SRC.BUREAU_FILE WHERE PAN IN ('BKRPR4417K', 'CDRPR8821M') HAVING COUNT(*) = 2;"
check "credit bureau API, called from Exasol (Python UDF)" "SELECT COUNT(*) FROM (SELECT LOS_SRC.BUREAU_API('BKRPR4417K')) WHERE HTTP_STATUS = 200;"
check "loan book (Exasol)"                             "SELECT COUNT(*) FROM LOS_BOOK.LOANS;"
check "referral queue"                                 "SELECT COUNT(*) FROM LOS_CORE.DECISIONS WHERE POLICY_STATUS = 'LIVE' AND SYSTEM_DECISION = 'REFER';"
check "fraud ring found"                             "SELECT COUNT(*) FROM LOS_CORE.FRAUD_RING;"
check "ML model: Python UDF scores inside Exasol"    "SELECT COUNT(*) FROM (SELECT LOS_ML.ML_PD(742, 42.2, 0.65, 1, 6, 0, 0, 'home_improvement') AS P FROM DUAL) WHERE P BETWEEN 0.01 AND 0.99;"
check "ML model: loan book scored"                   "SELECT COUNT(*) FROM LOS_BOOK.ML_SCORES HAVING COUNT(*) = (SELECT COUNT(*) FROM LOS_BOOK.LOANS);"
check "data contracts: checked, no critical breach"    "SELECT COUNT(*) FROM LOS_SEM.CONTRACT_RESULTS r JOIN LOS_SEM.CONTRACTS k ON k.CONTRACT_ID = r.CONTRACT_ID HAVING SUM(CASE WHEN NOT r.PASSED AND k.SEVERITY = 'CRITICAL' THEN 1 ELSE 0 END) = 0;"
check "free sessions (cap is 20)"                    "SELECT 20 - COUNT(*) FROM EXA_DBA_SESSIONS GROUP BY 'x';"
N=$(xsql "SELECT COUNT(*) FROM LOS_OPS.DECISION_LOG;" | tail -1)
[[ "$N" == "0" ]] && ok "decision log empty" || printf '    \033[0;33mnote\033[0m %s decisions already logged (run with --reset for a clean start)\n' "$N"
[[ "${1:-}" == "--reset" ]] && "$ROOT/setup/reset_demo.sh"

# Exasol Personal can run out of ETL channels after a burst of Postgres virtual-schema queries: every JDBC import then
# hangs 3 minutes ("Registry full" in the ETL logs, seen 2026-10-28). A database restart clears it.
EXALOGS="$DEPLOY_DIR/local/runtime/vm-shared/exa/logs"
RF=$( (find "$EXALOGS" -name '*EtlProcess*' -mmin -30 -exec grep -l 'Registry full' {} + 2>/dev/null || true) | wc -l | tr -d ' ')
LAST=$(ls -t "$EXALOGS"/*EtlProcess* 2>/dev/null | head -1 || true)
if [[ -n "$LAST" ]] && grep -q 'Registry full' "$LAST"; then
  bad "Exasol ETL channel registry is full now (Postgres queries hang 3 min): exasol stop && exasol start, then run this again"
elif [[ "$RF" != "0" ]]; then
  printf '    \033[0;33mnote\033[0m Exasol ETL registry was full earlier in the last 30 min (%s imports failed) and has recovered; restart the DB before the demo if in doubt\n' "$RF"
else
  ok "Exasol ETL channels healthy (no 'Registry full' in the last 30 min)"
fi

say "4. Amazon Textract (reads the uploads; without it the PDF text layer is used and the page says so)"
# Only checks that AWS credentials work (STS GetCallerIdentity is free); it never sends a page to Textract.
if [[ "$(printf '%s' "${TEXTRACT:-on}" | tr '[:upper:]' '[:lower:]')" == "off" ]]; then
  printf '    \033[0;33mnote\033[0m TEXTRACT=off: uploads use the PDF text-layer fallback, nothing is sent to AWS\n'
elif "$PY" -c "import boto3;boto3.Session(profile_name='$TEXTRACT_PROFILE' or None).client('sts',region_name='$TEXTRACT_REGION').get_caller_identity()" >/dev/null 2>&1; then
  ok "AWS credentials found: uploads are read by Amazon Textract ($TEXTRACT_REGION), billed by AWS per page"
else
  printf '    \033[0;33mnote\033[0m no AWS credentials: uploads use the PDF text-layer fallback\n'
fi

say "5. LOS service + console"
"$ROOT/service/run.sh" >/dev/null && curl -s -m 30 -X POST "http://127.0.0.1:$LOS_PORT/rpc" -H 'Content-Type: application/json' -d '{"fn":"health"}' | grep -q '"exa": true' \
  && ok "LOS service http://127.0.0.1:$LOS_PORT (Exasol, core banking, document store)" || bad "LOS service not healthy (see .work/los_api.log)"
curl -s -m 30 -o /dev/null -w '%{http_code}' "$CONSOLE" | grep -q 200 && ok "console $CONSOLE" \
  || bad "console not answering: is dash-server running? (exakit status); deploy: .venv/bin/python dash/deploy.py"

echo
(( FAIL == 0 )) && printf '\033[1;32mGO\033[0m\n' || { printf '\033[1;31mNO-GO\033[0m (fix the NO lines above)\n'; exit 1; }
