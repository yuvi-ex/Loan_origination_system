#!/usr/bin/env python3
"""The two people the console acts as, with database privileges that ENFORCE the controls (not just the UI):
  LOS_UW    underwriting desk  reads everything; may INSERT into the decision log, never UPDATE or DELETE it
  LOS_RISK  risk team          reads everything; may change the DRAFT policy and publish it (policy tables only),
                                      and re-score the book with the challenger model (its score table only)
  LOS_INTAKE  live uploads     reads everything; may only ADD a bureau pull and an application's facts row,
                                      and record data-contract results
Also a password for the MongoDB login docs_writer (created by data/walkins.py).
Passwords are generated once into secrets/app_users.env (mode 600) and never printed.
  .venv/bin/python setup/05_governance.py
"""
import os
import secrets
import tomllib
from pathlib import Path

import pyexasol

ROOT = Path(__file__).resolve().parents[1]
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))
from los_config import CFG  # noqa: E402
ENV = ROOT / "secrets" / "app_users.env"
READ = ["LOS_CORE", "LOS_SRC", "LOS_POLICY", "LOS_BOOK", "LOS_ACCEL", "LOS_OPS", "LOS_ML", "LOS_SEM"]
GRANTS = {
    "LOS_UW": ["GRANT INSERT ON LOS_OPS.DECISION_LOG TO {u}"],
    "LOS_RISK": ["GRANT UPDATE ON LOS_POLICY.POLICY TO {u}", "GRANT INSERT ON LOS_POLICY.POLICY TO {u}",
                        "GRANT INSERT ON LOS_POLICY.POLICY_HISTORY TO {u}",
                        "GRANT INSERT ON LOS_BOOK.ML_SCORES TO {u}", "GRANT DELETE ON LOS_BOOK.ML_SCORES TO {u}",
                        "GRANT INSERT ON LOS_ML.RUNS TO {u}"],
    "LOS_INTAKE": ["GRANT INSERT ON LOS_SRC.BUREAU_PULLS TO {u}", "GRANT INSERT ON LOS_ACCEL.APPLICATION_FACTS TO {u}",
                          "GRANT INSERT ON LOS_SEM.CONTRACT_RESULTS TO {u}", "GRANT DELETE ON LOS_SEM.CONTRACT_RESULTS TO {u}",
                          "GRANT INSERT ON LOS_SEM.CONTRACT_RUNS TO {u}"],
}

c = tomllib.load(open(Path.home() / ".exapump" / "config.toml", "rb"))[CFG["EXAPUMP_PROFILE"]]
# TLS is ON but the certificate is not verified: Exasol Personal serves a self-signed certificate on this machine's
# private VM. Against a real Exasol cluster, verify it (pyexasol: dsn="host/<FINGERPRINT>:8563", or a CA bundle).
con = pyexasol.connect(dsn=f"{c['host']}:{c['port']}", user=c["user"], password=c["password"], encryption=True,
                       websocket_sslopt={"cert_reqs": 0})
pw = dict(l.strip().split("=", 1) for l in open(ENV) if "=" in l) if ENV.exists() else {}
existing = {r[0] for r in con.execute("SELECT USER_NAME FROM EXA_DBA_USERS").fetchall()}
# On a first install the ML and semantic-layer schemas do not exist yet: their own setup steps (06, 07) run this again.
schemas = {r[0] for r in con.execute("SELECT SCHEMA_NAME FROM EXA_SCHEMAS").fetchall()}
tables = {f"{r[0]}.{r[1]}" for r in con.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM EXA_ALL_TABLES").fetchall()}
skipped = set()
for u, extra in GRANTS.items():
    pw.setdefault(u, "Wl" + secrets.token_urlsafe(18).replace("-", "x").replace("_", "y"))
    con.execute(f'{"ALTER" if u in existing else "CREATE"} USER {u} IDENTIFIED BY "{pw[u]}"')
    con.execute(f"GRANT CREATE SESSION TO {u}")
    for s in READ:
        if s in schemas:
            con.execute(f"GRANT SELECT ON SCHEMA {s} TO {u}")
        else:
            skipped.add(s)
    if "LOS_ML" in schemas:
        con.execute(f"GRANT EXECUTE ON SCHEMA LOS_ML TO {u}")      # the ML model's UDFs
    for g in extra:
        obj = g.split(" ON ", 1)[1].split(" TO ", 1)[0]
        if obj in tables:
            con.execute(g.format(u=u))
        else:
            skipped.add(obj)
pw.setdefault("DOCS_WRITER", "Dw" + secrets.token_urlsafe(18).replace("-", "x").replace("_", "y"))
ENV.parent.mkdir(exist_ok=True)
old = os.umask(0o077)
ENV.write_text("".join(f"{u}={p}\n" for u, p in pw.items()))
os.umask(old)
print(f"users {', '.join(GRANTS)} ready, DOCS_WRITER password set (passwords in {ENV})"
      + (f"; not there yet, granted by a later step: {', '.join(sorted(skipped))}" if skipped else ""))
