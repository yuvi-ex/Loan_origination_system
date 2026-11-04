"""A loan application arriving live: PDFs in, a decision out. Each step is its own call, so the console shows progress.

  receive   the PDFs are saved under a new application number; which document each one is comes from its own words
  read      Amazon Textract reads every PDF in parallel
  store     the form and the extracted fields go to MongoDB (the document store), the customer is found in core
            banking by the salary account on the form, and the bureau is pulled by PAN
  decide    one federated INSERT ... SELECT builds the application's facts row from MongoDB + Postgres + the bureau;
            score, rules, price and decision are views over it, so the decision exists the moment the row does

The job's state stays here (UPLOADS/<app>/job.json): the console passes only the application number.
"""
import base64
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pdfplumber
import pymongo

import los_config
import sqlq as S
import xdb
from extract import classify, extract

UPLOADS = xdb.ROOT / ".work" / "uploads"
PACKS = xdb.ROOT / "data" / "packs"
ORDER = ["APPLICATION", "PAYSLIP", "ID_PROOF", "EMPLOYMENT_LETTER"]
SUFFIX = {"APPLICATION": "F", "PAYSLIP": "P", "ID_PROOF": "I", "EMPLOYMENT_LETTER": "E"}
APP_RX = re.compile(r"^APP-26-\d{6}$")
MAX_FILES, MAX_BYTES = 8, 10_000_000
APP_DAY = los_config.CFG.get("APP_DATE", "2026-10-27")   # live uploads are dated inside the synthetic data's calendar


def vm_ip():
    return los_config.vm_ip()


_CLIENT = None


def _mongo():
    """The document store as docs_writer. One client for the whole service: pymongo pools connections inside it."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = pymongo.MongoClient(vm_ip(), los_config.port("MONGO_PORT"), username="docs_writer", password=xdb.env()["DOCS_WRITER"],
                                      authSource="admin", directConnection=True, serverSelectionTimeoutMS=4000)
    return _CLIENT["lending"]


def _dir(app):
    if not APP_RX.match(str(app)):
        raise ValueError("not an application number")
    return UPLOADS / app


def _load(app):
    return json.loads((_dir(app) / "job.json").read_text())


def _save(job):
    (_dir(job["app"]) / "job.json").write_text(json.dumps(job, default=str))
    return job


def next_id():
    """Never reuse a number: take the highest one seen in MongoDB, in the facts copy and in the upload folders. (MongoDB
    alone is not enough: an upload stalled past a reset can still write its facts row afterwards, and a reused number
    then shows two applicants' facts under one ID.)"""
    seen = [a["_id"] for a in _mongo().applications.find({"_id": {"$regex": "^APP-26-2"}}, {"_id": 1})]
    seen += [r["APP_ID"] for r in xdb.run("SELECT DISTINCT APP_ID FROM LOS_ACCEL.APPLICATION_FACTS WHERE APP_ID LIKE 'APP-26-2%'",
                                          who="intake")["rows"]]
    seen += [d.name for d in UPLOADS.glob("APP-26-2*")] if UPLOADS.exists() else []
    return f"APP-26-{max([int(a[7:]) for a in seen if APP_RX.match(str(a))] + [200000]) + 1}"


def thumb(pdf, width=150):
    """First page as a small PNG data URL, for the 'documents received' strip."""
    try:
        with pdfplumber.open(pdf) as p:
            img = p.pages[0].to_image(width=width).original
        b = BytesIO()
        img.save(b, format="PNG")
        return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ receive
def receive(files):
    """files: [(name, base64 data)], PDFs only. Saves them under a new application number; returns the job."""
    if not files or len(files) > MAX_FILES:
        raise ValueError(f"upload 1 to {MAX_FILES} PDFs")
    blobs = []
    for name, data in files:
        raw = base64.b64decode(data)
        if len(raw) > MAX_BYTES or not raw.startswith(b"%PDF"):
            raise ValueError(f"{Path(str(name)).name}: not a PDF, or larger than 10 MB")
        blobs.append((re.sub(r"[^A-Za-z0-9._-]", "_", Path(str(name)).name) or "document.pdf", raw))
    app = next_id()
    d = _dir(app)
    d.mkdir(parents=True, exist_ok=True)
    got = []
    for name, raw in blobs:
        (d / name).write_bytes(raw)
        got.append({"file": name, "kind": classify(d / name), "thumb": thumb(d / name)})
    got.sort(key=lambda g: ORDER.index(g["kind"]) if g["kind"] in ORDER else 9)
    return _save({"app": app, "docs": got, "t0": time.time(), "at": APP_DAY + datetime.now().strftime("T%H:%M")})


def receive_pack(name):
    packs = {p.name: p for p in PACKS.iterdir() if p.is_dir()}
    if name not in packs:
        raise ValueError("no such sample")
    return receive([(f.name, base64.b64encode(f.read_bytes()).decode()) for f in sorted(packs[name].glob("*.pdf"))])


# ------------------------------------------------------------------ read
def read(app):
    job, t = _load(app), time.time()
    d = _dir(app)
    docs = [g for g in job["docs"] if g["kind"]]
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda g: extract(d / g["file"], g["kind"]), docs))
    for g, r in zip(docs, res):
        g.update(fields=r["fields"], confidence=r["confidence"], engine=r["engine"], ms=r["ms"], error=r["error"])
    job["read_secs"] = time.time() - t
    return _save(job)


# ------------------------------------------------------------------ store
def store(app):
    job, t = _load(app), time.time()
    at = job["at"]
    by = {g["kind"]: g for g in job["docs"] if g.get("fields")}
    form = by.get("APPLICATION", {}).get("fields", {})
    job["form"] = form
    if not form.get("account"):
        job["error"] = "No loan application form was found among the uploads, so there is no applicant, amount or salary account to check."
        return _save(job)
    cust = xdb.run(S.q_customer(form["account"]), who="intake")
    c = (cust["rows"] or [{}])[0]
    job["customer"] = c
    db = _mongo()
    db.applications.replace_one({"_id": app}, {
        "_id": app, "custId": c.get("CUST_ID"), "submittedAt": at, "channel": form.get("channel") or "Live upload",
        "channelSource": "live upload", "product": "Personal loan", "amountRequested": int(form.get("amount") or 0),
        "termMonths": int(form.get("term") or 0), "purpose": form.get("purpose"),
        "applicant": {"name": form.get("name"), "dob": form.get("dob"), "mobile": form.get("mobile"), "email": form.get("email"),
                      "city": form.get("city"), "pin": form.get("pin")},
        "salaryAccount": form.get("account"), "deviceId": hashlib.sha1((app + "dev").encode()).hexdigest()[:8]}, upsert=True)
    for kind, g in by.items():
        f = {k: v for k, v in g["fields"].items() if k not in ("lineItems", "notes")}
        for k in ("gross", "bonus", "deductions", "net"):     # the MongoDB virtual schema is strict: these are doubles, always
            if f.get(k) is not None:
                f[k] = float(f[k])
        try:
            with pdfplumber.open(_dir(app) / g["file"]) as p:
                producer = (p.metadata or {}).get("Producer", "")
        except Exception:  # noqa: BLE001
            producer = ""
        doc = {"_id": f"DOC-{app[4:]}-{SUFFIX[kind]}", "applicationId": app, "docType": "APPLICATION_FORM" if kind == "APPLICATION" else kind,
               "fileName": g["file"], "pages": 1, "uploadedAt": at, "source": "live upload",
               "extraction": {"engine": g["engine"], "ms": g["ms"], "minConfidence": min(g["confidence"].values() or [0])},
               "fields": f, "confidence": g["confidence"],
               "fingerprint": {"producer": producer, "templateHash": hashlib.sha1((f.get("employer") or "scanner").encode()).hexdigest()[:8]
                               if kind == "PAYSLIP" else {"ID_PROOF": "pan-v2"}.get(kind, kind.lower())}}
        if g["fields"].get("lineItems"):
            doc["lineItems"] = [dict(li, amount=float(li["amount"])) for li in g["fields"]["lineItems"]]
        db.documents.replace_one({"_id": doc["_id"]}, doc, upsert=True)
    pan = (by.get("ID_PROOF", {}).get("fields", {}).get("idNumber") or form.get("pan") or "").upper()
    a = xdb.write(S.q_bureau_call(app, pan), "intake")             # the bureau API, called from a Python UDF in Exasol
    b = xdb.write(S.q_bureau_pull(app, c.get("CUST_ID")), "intake") if a["ok"] else a
    job["bureau_found"] = bool(b["ok"] and b["rows"])
    job["bureau_error"] = None if b["ok"] else b["error"]
    rep = (xdb.run(S.q_bureau_report(app), who="intake")["rows"] or [{}])[0]
    job["bureau_api"] = {k: rep.get(k) for k in ("HTTP_STATUS", "REPORT_ID", "MS")}
    job["bureau_pdf"] = _bureau_pdf(app, rep.get("REPORT_ID")) if rep.get("REPORT_ID") else None
    job["pan"] = pan                                          # what each match was keyed on, for the console's picture
    job["doc_ids"] = [f"DOC-{app[4:]}-{SUFFIX[k]}" for k in by]
    job["bureau"] = (xdb.run(S.q_bureau(app), who="intake")["rows"] or [{}])[0] if job["bureau_found"] else {}
    job["store_secs"] = time.time() - t
    return _save(job)


def _bureau_pdf(app, rid):
    """The bureau's PDF report, fetched from its API into the application's folder (evidence on the checklist)."""
    import urllib.request
    try:
        req = urllib.request.Request(f"http://{vm_ip()}:{los_config.port('BUREAU_PORT')}/v1/credit-report/{rid}.pdf", headers={"X-API-Key": xdb.env()["BUREAU_API_KEY"]})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
        if not raw.startswith(b"%PDF"):
            return None
        name = f"5_credit_bureau_report_{re.sub(r'[^A-Za-z0-9-]', '', rid)}.pdf"
        (_dir(app) / name).write_bytes(raw)
        return name
    except Exception as e:  # noqa: BLE001 - the case still opens without the PDF; the log says why
        print(f"bureau PDF {rid} not fetched: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return None


# ------------------------------------------------------------------ decide
def decide(app):
    job, t = _load(app), time.time()
    r = xdb.write(S.q_facts_insert(app), "intake")
    job["facts_secs"] = time.time() - t
    if not r["ok"]:
        job["error"] = r["error"]
        return _save(job)
    # data contracts for this upload, through the semantic views, BEFORE the decision is read: a critical breach is rule R13
    t2 = time.time()
    c = xdb.write(f"DELETE FROM LOS_SEM.CONTRACT_RESULTS WHERE APP_ID = {xdb.q(app)}", "intake")
    c = c if not c["ok"] else xdb.write("INSERT INTO LOS_SEM.CONTRACT_RESULTS SELECT APP_ID, CONTRACT_ID, COALESCE(PASSED, FALSE), EVIDENCE, CURRENT_TIMESTAMP FROM ("
                  + S.q_contract_checks(app, (job.get("form") or {}).get("account")) + ")", "intake")
    job["contracts"] = xdb.run(S.q_contracts_app(app), who="intake")["rows"] if c["ok"] else []
    job["contracts_error"] = None if c["ok"] else c["error"]
    job["contracts_secs"] = time.time() - t2
    d = xdb.run(f"SELECT SYSTEM_DECISION, SCORE, BAND, RATE, REVIEW_LEVEL, RULES_FIRED FROM LOS_CORE.DECISIONS "
                f"WHERE POLICY_STATUS = 'LIVE' AND APP_ID = {xdb.q(app)}", who="intake")
    job["decision"] = (d["rows"] or [{}])[0]
    # the fused row as Exasol built it (one vocabulary over MongoDB, Postgres and the bureau), for the semantic-fusion view
    f = xdb.run(f"SELECT CUST_ID, APPLICANT_NAME, NAME_ON_ID, EMPLOYER, PAYSLIP_NET, BANK_SALARY_AVG, INCOME_GAP_PCT, SALARY_MONTHS, "
                f"PAYER_ACCT, PAYER_IFSC, BUREAU_SCORE, EXISTING_EMI, VERIFIED_GROSS, BANK_CUSTOMER FROM LOS_CORE.APPLICATION_FACTS "
                f"WHERE APP_ID = {xdb.q(app)}", who="intake")
    job["facts"] = (f["rows"] or [{}])[0]
    if job["decision"].get("SYSTEM_DECISION") not in (None, "REFER"):
        w = xdb.write(S.q_log_auto(app), "uw")     # a decision the system made alone is logged too
        job["log_error"] = None if w["ok"] else w["error"]      # the console shows it: an unlogged decision must not look final
    job["total_secs"] = time.time() - job["t0"]
    return _save(job)
