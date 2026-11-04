"""The LOS service's Exasol connections, one login per job so the database enforces the controls:
  uw      LOS_UW      reads everything; may only ADD rows to the decision log
  risk    LOS_RISK    reads everything; may only change the policy tables
  intake  LOS_INTAKE  reads everything; may only ADD a bureau pull and an application's facts row
No admin login: resets are done by the setup scripts. Passwords live in secrets/app_users.env (mode 600).
Every successful read is cached to disk; if a source fails on stage the page shows the last good result and says so.
"""
import json
import re
import threading
import time
import tomllib
from pathlib import Path

import sys

import pyexasol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from los_config import CFG, ROOT  # noqa: E402

CACHE = ROOT / "dash" / "cache"
USERS = ROOT / "secrets" / "app_users.env"
LOGIN = {"uw": "LOS_UW", "risk": "LOS_RISK", "intake": "LOS_INTAKE"}


def env():
    return dict(l.strip().split("=", 1) for l in open(USERS) if "=" in l)


def _connect(who):
    c = tomllib.load(open(Path.home() / ".exapump" / "config.toml", "rb"))[CFG["EXAPUMP_PROFILE"]]     # host and port only
    user, pw = LOGIN[who], env()[LOGIN[who]]
    # TLS is ON but the certificate is not verified: Exasol Personal serves a self-signed certificate on this machine's
    # private VM. Against a real Exasol cluster, verify it (pyexasol: dsn="host/<FINGERPRINT>:8563", or a CA bundle).
    con = pyexasol.connect(dsn=f"{c['host']}:{c['port']}", user=user, password=pw, encryption=True,
                           websocket_sslopt={"cert_reqs": 0}, fetch_dict=True, autocommit=True)
    con.execute("ALTER SESSION SET QUERY_TIMEOUT = 120")
    con.execute(f"ALTER SESSION SET TIME_ZONE = '{CFG['TIME_ZONE']}'")     # decision-log times in the lender's own time
    return con


_CONN, _LOCKS = {}, {w: threading.RLock() for w in LOGIN}
_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def _num(v):
    """pyexasol returns DECIMAL as str: numeric strings become numbers."""
    if isinstance(v, str) and _NUM.match(v):
        return float(v) if "." in v else int(v)
    return v


def _exec(sql, who):
    with _LOCKS[who]:
        for attempt in (1, 2):
            try:
                if who not in _CONN or _CONN[who].is_closed:
                    _CONN[who] = _connect(who)
                return _CONN[who].execute(sql)
            except (pyexasol.ExaCommunicationError, pyexasol.ExaConnectionError):
                _CONN.pop(who, None)
                if attempt == 2:
                    raise


def run(sql, key=None, who="uw"):
    """A read. Returns {rows, secs, live, error}; on failure the last good result for `key`, labelled."""
    t = time.time()
    try:
        with _LOCKS[who]:
            st = _exec(sql, who)
            rows = [{k: _num(v) for k, v in r.items()} for r in st.fetchall()] if st.result_type == "resultSet" else []
        res = {"rows": rows, "secs": time.time() - t, "live": True, "error": None}
        if key:
            CACHE.mkdir(parents=True, exist_ok=True)
            (CACHE / f"{key}.json").write_text(json.dumps(res, default=str))
        return res
    except Exception as e:  # noqa: BLE001
        msg = getattr(e, "message", str(e))[:300]
        f = CACHE / f"{key}.json" if key else None
        if f and f.exists():
            res = json.loads(f.read_text())
            res.update(live=False, error=msg)
            return res
        return {"rows": [], "secs": time.time() - t, "live": False, "error": msg}


def write(sql, who):
    """A change, as a named login. Never cached; the database's own error comes back verbatim."""
    t = time.time()
    try:
        with _LOCKS[who]:
            st = _exec(sql, who)
            return {"ok": True, "rows": st.rowcount(), "secs": time.time() - t, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "rows": 0, "secs": time.time() - t, "error": getattr(e, "message", str(e))[:400]}


def q(v):
    """SQL string literal."""
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"
