#!/usr/bin/env bash
# Put the demo back to its starting state: no live uploads, empty decision log, policy version 1 (live + identical draft).
# Uses the admin login: the console's own logins cannot delete from the log, which is the point.
source "$(dirname "$0")/common.sh"
xsql "DELETE FROM LOS_OPS.DECISION_LOG;" >/dev/null || die "reset failed. Check the database (setup/preflight.sh), then run setup/reset_demo.sh again"
xsql "DELETE FROM LOS_POLICY.POLICY;" >/dev/null || die "reset failed. Check the database (setup/preflight.sh), then run setup/reset_demo.sh again"
xsql "INSERT INTO LOS_POLICY.POLICY VALUES (1, 'LIVE', 45, 3, 580, 560, 15.00, 9.25, 1000000, 4000000, 50000, 21, 'Credit Risk Committee', TIMESTAMP '2026-07-01 09:00:00', 'Personal loan policy FY27 Q2');" >/dev/null || die "reset failed. Check the database (setup/preflight.sh), then run setup/reset_demo.sh again"
xsql "INSERT INTO LOS_POLICY.POLICY VALUES (2, 'DRAFT', 45, 3, 580, 560, 15.00, 9.25, 1000000, 4000000, 50000, 21, 'Credit Risk Committee', TIMESTAMP '2026-07-01 09:00:00', 'Draft: copy of version 1');" >/dev/null || die "reset failed. Check the database (setup/preflight.sh), then run setup/reset_demo.sh again"
xsql "DELETE FROM LOS_POLICY.POLICY_HISTORY WHERE POLICY_VERSION > 1;" >/dev/null || die "reset failed. Check the database (setup/preflight.sh), then run setup/reset_demo.sh again"
xsql "DELETE FROM LOS_SEM.CONTRACT_RESULTS WHERE APP_ID LIKE 'APP-26-2%';" >/dev/null || die "reset failed. Check the database (setup/preflight.sh), then run setup/reset_demo.sh again"   # live uploads' contract checks
xsql "DELETE FROM LOS_SRC.BUREAU_REPORTS WHERE APP_ID LIKE 'APP-26-2%';" >/dev/null || die "reset failed. Check the database (setup/preflight.sh), then run setup/reset_demo.sh again"     # live uploads' bureau API calls
ok "decision log empty, policy v1 live, draft = live"
"$PY" "$ROOT/data/walkins.py" | sed 's/^/    /'      # removes every live upload from MongoDB, the bureau pulls and the facts copy
rm -rf "$WORK/uploads"
ok "live uploads removed: upload Karthik and Divya again on stage"
