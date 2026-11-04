"""The LOS service: the loan-origination back end the console (on dash-server) calls. Loopback only, 127.0.0.1:LOS_PORT (config.env).

It holds every connection the console must not: Exasol as separate logins (underwriting, risk, intake; each with only
the privileges its job needs), MongoDB as docs_writer, Amazon Textract as the TEXTRACT_PROFILE AWS profile. The hosted
Dash app holds no credentials and opens no database connection (dash-server's credential checks forbid it).

Only the named operations in OPS can be called; none takes SQL. Start: service/run.sh
POST /rpc {"fn": "...", "args": [...]}  ->  {"ok": true, "result": ...}
GET /health -> {"ok": true}, or 503 {"ok": false, "missing": [...]} naming what to install or run first.
Only JSON requests addressed to 127.0.0.1/localhost are accepted: a web page in the same browser cannot call it
(a cross-site form post is not JSON, and a DNS-rebinding page sends its own host name).
"""
import json
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import intake  # noqa: E402
import los_config  # noqa: E402
import ops  # noqa: E402

PORT = los_config.port("LOS_PORT")
HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
MAX_BODY = 120_000_000     # 8 PDFs of up to 10 MB each, base64-encoded, with room to spare
OPS = {"health": ops.health, "overview": ops.overview, "queue": ops.queue, "case_load": ops.case_load, "log_rows": ops.log_rows,
       "rescore_regular": ops.rescore_regular, "sign": ops.sign, "countersign": ops.countersign, "insights": ops.insights,
       "semantic": ops.semantic, "audit": ops.audit, "tamper": ops.tamper,
       "receive": intake.receive, "receive_pack": intake.receive_pack, "read": intake.read, "store": intake.store, "decide": intake.decide}


def missing():
    """What a full install creates. Without it no operation can work, so /health says what to do instead of 'ok'."""
    need = {Path.home() / ".exapump" / "config.toml": "install the Exasol starter kit (README: Prerequisites)",
            los_config.RUNTIME / "vm-runtime.json": "start Exasol Personal (exasol start)",
            HERE.parent / "secrets" / "app_users.env": "run setup/install.sh (step 'logins' creates it)"}
    return [f"{p} not found: {fix}" for p, fix in need.items() if not p.exists()]


def plain(e):
    """An exception as a sentence for the page, with the next step where we know it."""
    msg = str(e)
    if "Registry full" in msg:
        return "Exasol ran out of ETL channels. Restart the database (exasol stop && exasol start), then run setup/preflight.sh."
    if isinstance(e, ConnectionError) or "Connection refused" in msg or "timed out" in msg.lower():
        return f"A source system did not answer ({type(e).__name__}). Run setup/preflight.sh: it restarts what is stopped."
    return f"{type(e).__name__}: {msg[:300]} (details in .work/los_api.log)"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path != "/health":
            return self._send(404, {"ok": False})
        m = missing()
        self._send(503 if m else 200, {"ok": not m, "missing": m})

    def do_POST(self):  # noqa: N802
        t = time.time()
        if self.path != "/rpc":
            return self._send(404, {"ok": False})
        if self.headers.get("Host") not in HOSTS or not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._send(403, {"ok": False, "error": "only JSON requests to 127.0.0.1 are accepted"})
        size = int(self.headers.get("Content-Length") or 0)
        if size > MAX_BODY:
            return self._send(413, {"ok": False, "error": f"request larger than {MAX_BODY // 1_000_000} MB"})
        try:
            req = json.loads(self.rfile.read(size))
        except ValueError:
            return self._send(400, {"ok": False, "error": "the request body is not JSON"})
        fn = OPS.get(req.get("fn"))      # look the operation up first, so a KeyError inside one is not "unknown"
        if fn is None:
            return self._send(404, {"ok": False, "error": f"unknown operation {req.get('fn')!r}"})
        try:
            res = fn(*req.get("args", []))
            self._send(200, {"ok": True, "result": res})
            print(f"{time.strftime('%H:%M:%S')} {req['fn']:16} {time.time() - t:6.2f}s", flush=True)
        except Exception as e:  # noqa: BLE001 - logged in full, shown to the page as one sentence
            traceback.print_exc()
            self._send(500, {"ok": False, "error": plain(e)})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if missing():
        sys.exit("LOS service not started:\n  " + "\n  ".join(missing()))
    print(f"LOS service on http://127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
