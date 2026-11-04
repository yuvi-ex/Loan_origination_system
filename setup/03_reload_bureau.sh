#!/usr/bin/env bash
# After data/generate.py: reload the bureau responses into Exasol and rebuild the accelerated facts.
source "$(dirname "$0")/common.sh"
xsql "TRUNCATE TABLE LOS_SRC.BUREAU_PULLS;" >/dev/null
xload "$WORK/bureau.csv" LOS_SRC.BUREAU_PULLS
xsql "ALTER VIRTUAL SCHEMA LOS_DOCS REFRESH;" >/dev/null
xfile "$ROOT/sql/20_facts.sql"
ok "facts rebuilt: $(xsql "SELECT COUNT(*) FROM LOS_ACCEL.APPLICATION_FACTS;" | tail -1) applications"
