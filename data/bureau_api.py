"""The credit bureau, as an API (mocked, but called the way a real one is): writes the server, one JSON record and one PDF
credit report per PAN into the VM-shared folder; setup/00_sources_vm.sh runs it in a container inside the Exasol VM.

  GET /v1/credit-report?pan=<PAN>          X-API-Key: <key>  ->  the report as JSON (404 if the bureau has no file)
  GET /v1/credit-report/<reportId>.pdf     X-API-Key: <key>  ->  the same report as a PDF

Exasol calls it from a Python UDF (LOS_SRC.BUREAU_API, sql/55_bureau_api.sql); the address and key live in the
CONNECTION object LOS_BUREAU_API, so no SQL and no app ever holds the key. The LOS service fetches the PDF for
the checklist. Every PDF is stamped SYNTHETIC: no real person, no real bureau.
    .venv/bin/python data/bureau_api.py
"""
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from los_config import RUNTIME  # noqa: E402
OUT = RUNTIME / "vm-shared" / "los-bureau-api"   # /mnt/host/los-bureau-api inside the VM

FILES = {
    "BKRPR4417K": dict(name="Karthik Raghunathan", dob="1992-03-11", score=742, enquiries6m=1, publicRecords=0, oldestTradeYears=13.2,
                       accounts=[("Woodgrove Bank", "Car loan", 18500, "current"), ("Contoso Bank", "Personal loan", 13000, "current"),
                                 ("Tailspin Card", "Credit card", 0, "current")]),
    "CDRPR8821M": dict(name="Divya Ramesh", dob="1995-08-19", score=768, enquiries6m=0, publicRecords=0, oldestTradeYears=7.5,
                       accounts=[("Fabrikam Bank", "Two-wheeler loan", 6500, "current"), ("Woodgrove Card", "Credit card", 0, "current")]),
    "ANKPK6634R": dict(name="Ananya Krishnan", dob="1993-12-04", score=731, enquiries6m=1, publicRecords=0, oldestTradeYears=6.1,
                       accounts=[("Litware Bank", "Consumer durable loan", 9800, "current"), ("Northwind Card", "Credit card", 0, "current")]),
}

SERVER = r'''"""Mock credit-bureau API (stdlib only). Serves /srv/data/<PAN>.json and /srv/reports/<id>.pdf; logs every call."""
import json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
KEY = open("/srv/api_key").read().strip()

class H(BaseHTTPRequestHandler):
    def _out(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/health":
            return self._out(200, {"ok": True})
        if self.headers.get("X-API-Key") != KEY:
            return self._out(401, {"error": "invalid API key"})
        if u.path == "/v1/credit-report":
            pan = (parse_qs(u.query).get("pan") or [""])[0].upper()
            f = f"/srv/data/{pan}.json"
            return self._out(200, json.load(open(f))) if pan.isalnum() and os.path.exists(f) else self._out(404, {"error": "no file for this PAN"})
        if u.path.startswith("/v1/credit-report/") and u.path.endswith(".pdf"):
            rid = u.path.rsplit("/", 1)[1][:-4]
            f = f"/srv/reports/{rid}.pdf"
            return self._out(200, open(f, "rb").read(), "application/pdf") if rid.replace("-", "").isalnum() and os.path.exists(f) else self._out(404, {"error": "no such report"})
        self._out(404, {"error": "unknown endpoint"})
    def log_message(self, fmt, *a):
        sys.stdout.write(time.strftime("%H:%M:%S ") + (fmt % a) + "\n"); sys.stdout.flush()

# 0.0.0.0 is the container's own interface: podman publishes the port on the VM's host-only network only
ThreadingHTTPServer(("0.0.0.0", 8000), H).serve_forever()
'''


def report_pdf(path, pan, f, rid):
    c = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4
    c.setFillColor(colors.HexColor("#3B2A7A")); c.rect(0, H - 90, W, 90, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 20); c.drawString(40, H - 50, "Credit Information Report")
    c.setFont("Helvetica", 10); c.drawString(40, H - 70, f"Report {rid}  ·  issued 28-10-2026  ·  consumer bureau (mock)")
    c.setFillColor(colors.HexColor("#C8102E")); c.setFont("Helvetica-Bold", 9)
    c.drawString(40, H - 105, "SYNTHETIC DOCUMENT - DEMO ONLY - NOT A REAL PERSON OR BUREAU")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 12); c.drawString(40, H - 140, "Consumer")
    c.setFont("Helvetica", 11)
    for i, (k, v) in enumerate([("Name", f["name"]), ("PAN", pan), ("Date of birth", f["dob"])]):
        c.drawString(40, H - 162 - i * 18, f"{k}:"); c.drawString(160, H - 162 - i * 18, v)
    c.setFillColor(colors.HexColor("#F1ECFD")); c.roundRect(370, H - 220, 185, 90, 10, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#3B2A7A")); c.setFont("Helvetica", 10); c.drawString(385, H - 150, "Credit score")
    c.setFont("Helvetica-Bold", 34); c.drawString(385, H - 190, str(f["score"])); c.setFont("Helvetica", 9); c.drawString(385, H - 208, "range 300 - 900")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 12); c.drawString(40, H - 260, "Summary")
    emi = sum(a[2] for a in f["accounts"])
    c.setFont("Helvetica", 11)
    for i, (k, v) in enumerate([("Enquiries, last 6 months", f["enquiries6m"]), ("Public records", f["publicRecords"]),
                                ("Active loans", sum(1 for a in f["accounts"] if a[2] > 0)), ("Total EMI (Rs / month)", f"{emi:,}"),
                                ("Oldest account (years)", f["oldestTradeYears"])]):
        c.drawString(40, H - 282 - i * 18, k); c.drawRightString(330, H - 282 - i * 18, str(v))
    c.setFont("Helvetica-Bold", 12); c.drawString(40, H - 390, "Accounts")
    c.setFont("Helvetica-Bold", 10)
    for x, t in [(40, "Lender"), (190, "Type"), (360, "EMI (Rs)"), (450, "Status")]:
        c.drawString(x, H - 410, t)
    c.setFont("Helvetica", 10)
    for i, (lender, typ, e, st) in enumerate(f["accounts"]):
        y = H - 430 - i * 18
        c.drawString(40, y, lender); c.drawString(190, y, typ); c.drawRightString(410, y, f"{e:,}"); c.drawString(450, y, st)
    c.setFillColor(colors.HexColor("#C8102E")); c.setFont("Helvetica-Bold", 9)
    c.drawString(40, 40, "SYNTHETIC DOCUMENT - DEMO ONLY")
    c.save()


def main():
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    (OUT / "api.py").write_text(SERVER)
    env = dict(l.strip().split("=", 1) for l in open(ROOT / "secrets" / "app_users.env") if "=" in l)
    (OUT / "api_key").write_text(env["BUREAU_API_KEY"])
    for pan, f in FILES.items():
        rid = f"CIR-{pan[-5:-1]}-2610"
        emi = sum(a[2] for a in f["accounts"])
        rec = dict(reportId=rid, pan=pan, name=f["name"], dob=f["dob"], score=f["score"], enquiries6m=f["enquiries6m"],
                   publicRecords=f["publicRecords"], activeLoans=sum(1 for a in f["accounts"] if a[2] > 0), existingEmi=emi,
                   oldestTradeYears=f["oldestTradeYears"], accounts=[dict(lender=a[0], type=a[1], emi=a[2], status=a[3]) for a in f["accounts"]],
                   reportUrl=f"/v1/credit-report/{rid}.pdf")
        (OUT / "data" / f"{pan}.json").write_text(json.dumps(rec, indent=1))
        report_pdf(OUT / "reports" / f"{rid}.pdf", pan, f, rid)
        print(pan, rid, f["score"], emi)


if __name__ == "__main__":
    main()
