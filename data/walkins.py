"""Get the lender's systems ready for LIVE uploads (the console's "New application" tab). Idempotent.

  * core banking (Postgres): Divya Ramesh, a second walk-in customer with seven months of steady salary (the clean case)
  * the credit bureau (mocked): LOS_SRC.BUREAU_FILE, what the bureau holds per PAN; an upload "pulls" from it
  * Karthik Raghunathan's pre-built application APP-26-104871 is removed from MongoDB, the facts copy and the bureau
    pulls: in the demo his application arrives live, from the PDFs in data/packs/karthik-raghunathan (his bank account stays)
  * MongoDB login docs_writer (readWrite on lending only), password in secrets/app_users.env

  .venv/bin/python data/walkins.py          (after data/generate.py, documents.py and setup/05_governance.py)
"""
import datetime as dt
import random
import sys
import tomllib
from pathlib import Path

import psycopg
import pyexasol
import pymongo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from los_config import CFG, port, source_secret, vm_ip  # noqa: E402
ENV = ROOT / "secrets" / "app_users.env"
VM_IP = vm_ip()
HERO = "APP-26-104871"
rng = random.Random(4417)

# ------------------------------------------------------------------ core banking: Divya Ramesh
CUST, ACCT, NET, EMI = "CIF20499001", "50100417730962", 88000, 6500
PAYER = ("WGRB0000240", "50200077115540")
rows, tid = [], [90_000_000]          # above every generated txn_id


def tx(d, amt, drcr, narr, chnl, cp=(None, None)):
    tid[0] += 1
    rows.append([tid[0], ACCT, d, round(amt, 2), drcr, narr[:120], chnl, cp[1], cp[0]])


tx(dt.date(2026, 3, 1), 142000, "C", "OPENING BALANCE B/F", "SYS")
for m in range(3, 11):
    last = (dt.date(2026, m + 1, 1) if m < 12 else dt.date(2027, 1, 1)) - dt.timedelta(days=1)
    while last.weekday() > 4:
        last -= dt.timedelta(days=1)
    if last <= dt.date(2026, 10, 24):
        tx(last, NET, "C", f"NEFT CR-{PAYER[0]}-NORTHWIND ANALYTICS PVT LTD-SALARY {dt.date(2026, m, 1):%b%y}".upper(), "NEFT", PAYER)
    if dt.date(2026, m, 5) <= dt.date(2026, 10, 24):
        tx(dt.date(2026, m, 5), EMI, "D", "NACH DR/NORTHWIND FIN/LOAN EMI", "NACH")
        tx(dt.date(2026, m, 3), 18500, "D", f"UPI/DR/{rng.randint(10**11, 10**12 - 1)}/RENT KAVITHA S", "UPI")
        for _ in range(rng.randint(12, 18)):
            tx(dt.date(2026, m, rng.randint(1, 24)), rng.uniform(150, 3200), "D",
               f"UPI/DR/{rng.randint(10**11, 10**12 - 1)}/{rng.choice(['SWIGGY', 'BIGBASKET', 'DMART', 'METRO RAIL', 'APOLLO PHARMACY', 'AMAZON PAY'])}", "UPI")
        tx(dt.date(2026, m, rng.randint(8, 20)), rng.uniform(9000, 16000), "D", "CC PAYMENT/AUTOPAY", "NEFT")
rows.sort(key=lambda r: (r[2], r[4] == "D", r[0]))
bal = 0.0
with psycopg.connect(host=VM_IP, port=port("PG_PORT"), user="cbs_admin", password=source_secret("PG_ADMIN_PASSWORD"), dbname="core_banking",
                     connect_timeout=10) as pg:
    pg.execute("DELETE FROM cbs.txn_hist WHERE acct_no = %s", (ACCT,))
    pg.execute("DELETE FROM cbs.acct_mst WHERE acct_no = %s", (ACCT,))
    pg.execute("DELETE FROM cbs.cust_mst WHERE cust_id = %s", (CUST,))
    pg.execute("INSERT INTO cbs.cust_mst VALUES (%s, 'DIVYA RAMESH', '19-08-1995', '0000012736', 'CDRPR8821M', 'BR121', '2021-07-09', 'Y')", (CUST,))
    pg.execute("INSERT INTO cbs.acct_mst VALUES (%s, %s, 'SBA', '2021-07-09', 'A')", (ACCT, CUST))
    with pg.cursor() as cur:
        for r in rows:
            bal += r[3] if r[4] == "C" else -r[3]
            cur.execute("INSERT INTO cbs.txn_hist VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", r + [round(bal, 2)])
print(f"core banking: {CUST} / {ACCT}, {len(rows)} transactions, closing balance {bal:,.0f}")

# ------------------------------------------------------------------ MongoDB: the writer login, and the hero arrives live
env = dict(l.strip().split("=", 1) for l in open(ENV) if "=" in l)
mc = pymongo.MongoClient(VM_IP, port("MONGO_PORT"), username="root", password=source_secret("MONGO_ROOT_PASSWORD"),
                         authSource="admin", directConnection=True, serverSelectionTimeoutMS=5000)
adm = mc["admin"]
if not adm.command("usersInfo", "docs_writer")["users"]:
    adm.command("createUser", "docs_writer", pwd=env["DOCS_WRITER"], roles=[{"role": "readWrite", "db": "lending"}])
else:
    adm.command("updateUser", "docs_writer", pwd=env["DOCS_WRITER"])
db = mc["lending"]
gone = db.applications.delete_many({"$or": [{"_id": HERO}, {"channelSource": "live upload"}]}).deleted_count
gone_d = db.documents.delete_many({"$or": [{"applicationId": HERO}, {"source": "live upload"}]}).deleted_count
print(f"mongodb: docs_writer ready; removed {gone} applications, {gone_d} documents (hero + earlier live uploads)")

# ------------------------------------------------------------------ Exasol: the bureau file, and the hero's rows
c = tomllib.load(open(Path.home() / ".exapump" / "config.toml", "rb"))[CFG["EXAPUMP_PROFILE"]]
# TLS is ON but the certificate is not verified: Exasol Personal serves a self-signed certificate on this machine's
# private VM. Against a real Exasol cluster, verify it (pyexasol: dsn="host/<FINGERPRINT>:8563", or a CA bundle).
x = pyexasol.connect(dsn=f"{c['host']}:{c['port']}", user=c["user"], password=c["password"], encryption=True,
                     websocket_sslopt={"cert_reqs": 0}, autocommit=True)
x.execute("""CREATE OR REPLACE TABLE LOS_SRC.BUREAU_FILE (
  PAN VARCHAR(10), NAME VARCHAR(80), BUREAU_SCORE DECIMAL(4,0), INQ_6M DECIMAL(3,0), PUB_REC DECIMAL(3,0),
  ACTIVE_LOANS DECIMAL(3,0), EXISTING_EMI DECIMAL(12,0), OLDEST_TRADE_YEARS DECIMAL(4,1))""")
x.execute("COMMENT ON TABLE LOS_SRC.BUREAU_FILE IS 'Mocked credit bureau: what the bureau holds per PAN. A live upload pulls from it into BUREAU_PULLS.'")
x.execute("""INSERT INTO LOS_SRC.BUREAU_FILE VALUES
  ('BKRPR4417K', 'KARTHIK RAGHUNATHAN', 742, 1, 0, 2, 31500, 13.2),
  ('CDRPR8821M', 'DIVYA RAMESH', 768, 0, 0, 1, 6500, 7.5)""")
for t in ("LOS_SRC.BUREAU_PULLS", "LOS_ACCEL.APPLICATION_FACTS"):
    x.execute(f"DELETE FROM {t} WHERE APP_ID = '{HERO}' OR APP_ID LIKE 'APP-26-2%'")
x.execute(f"DELETE FROM LOS_OPS.DECISION_LOG WHERE APP_ID = '{HERO}' OR APP_ID LIKE 'APP-26-2%'")
n = x.execute("SELECT COUNT(*) FROM LOS_ACCEL.APPLICATION_FACTS").fetchval()
print(f"exasol: BUREAU_FILE 2 rows; facts copy now {n} applications (live uploads are added one by one)")
