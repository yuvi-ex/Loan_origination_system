"""Document extraction: an uploaded PDF -> typed fields with a confidence per field.

Primary: Amazon Textract (AnalyzeDocument, Mumbai region ap-south-1) with QUERIES (one question per field, each answer
with Textract's own confidence) and TABLES (the payslip's earnings/deductions lines). Two rules sit on top of what Textract
reads, and both are visible here, not hidden in a model:
  * a line item is one-time if its label says bonus / one-time / arrears / incentive / reimbursement
  * gross - deductions must equal net; if it does not, the net-pay confidence is cut to 0.5, so the case goes to a person
Fallback: the PDF's own text layer, parsed with rules (works offline, digital PDFs only).
Credentials: AWS profile TEXTRACT_PROFILE (empty = the default AWS credential chain); region TEXTRACT_REGION (config.env).
Cost: Textract is billed per page by AWS. TEXTRACT=off in config.local.env never calls AWS (text layer only).
"""
import os
import re
import time
from datetime import datetime
from pathlib import Path

try:
    from los_config import CFG
except ImportError:      # used outside the repository
    CFG = {}
REGION = os.environ.get("TEXTRACT_REGION") or CFG.get("TEXTRACT_REGION") or "ap-south-1"
PROFILE = os.environ.get("TEXTRACT_PROFILE") or CFG.get("TEXTRACT_PROFILE") or None
ENGINE = f"Amazon Textract ({REGION})"
ENABLED = (os.environ.get("TEXTRACT") or CFG.get("TEXTRACT") or "on").strip().lower() != "off"

QUERIES = {
    "PAYSLIP": [("employeeName", "What is the employee name?"), ("employer", "What is the company name at the top?"),
                ("employerAddress", "What is the company address?"), ("payMonth", "Which month and year is this payslip for?"),
                ("dateOfJoining", "What is the date of joining?"), ("gross", "What is the gross earnings amount?"),
                ("deductions", "What is the total deductions amount?"), ("net", "What is the NET PAY amount?")],
    "ID_PROOF": [("name", "What is the name?"), ("dob", "What is the date of birth?"), ("idNumber", "What is the ID number (PAN)?")],
    "APPLICATION": [("name", "What is the applicant's full name?"), ("dob", "What is the date of birth?"), ("pan", "What is the PAN?"),
                    ("mobile", "What is the mobile number?"), ("email", "What is the email?"), ("cityPin", "What is the city and PIN code?"),
                    ("employer", "Who is the employer?"), ("account", "What is the salary account number?"),
                    ("declaredNet", "What is the monthly take-home pay declared?"), ("amount", "What is the loan amount requested?"),
                    ("term", "What is the tenure in months?"), ("purpose", "What is the purpose of the loan?"),
                    ("channel", "What is the channel?")],
    "EMPLOYMENT_LETTER": [("employer", "Which company issued this letter?"), ("designation", "What is the employee's designation?"),
                          ("joiningDate", "Since which date is the employee employed?"),
                          ("employmentType", "Is the employment permanent or temporary?")],
}
CONF_KEYS = {"PAYSLIP": ("employeeName", "employer", "gross", "net", "payMonth", "dateOfJoining"),
             "ID_PROOF": ("name", "dob", "idNumber"), "EMPLOYMENT_LETTER": ("employer", "designation", "joiningDate"),
             "APPLICATION": ("name", "pan", "account", "amount", "term")}
LABEL = {"APPLICATION": "Loan application form", "PAYSLIP": "Payslip", "ID_PROOF": "PAN card", "EMPLOYMENT_LETTER": "Employment letter"}


def classify(pdf: Path) -> str | None:
    """Which document is this? Read from the PDF's own words (local, instant); the file name only as a last resort."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf) as p:
            t = " ".join((pg.extract_text() or "") for pg in p.pages[:2]).upper()
    except Exception:  # noqa: BLE001 - a scan without a text layer
        t = ""
    t += " " + pdf.name.upper()
    for kind, words in (("APPLICATION", ("LOAN APPLICATION FORM",)), ("PAYSLIP", ("NET PAY", "PAYSLIP", "SALARY SLIP")),
                        ("ID_PROOF", ("IDENTITY DOCUMENT", "PAN CARD", "PERMANENT ACCOUNT NUMBER")),
                        ("EMPLOYMENT_LETTER", ("TO WHOMSOEVER", "EMPLOYMENT LETTER", "HAS BEEN EMPLOYED"))):
        if any(w in t for w in words):
            return kind
    return None
ONE_TIME = re.compile(r"bonus|one[- ]time|arrear|incentive|reimburs", re.I)


def _amount(s):
    m = re.search(r"-?[\d,]+(?:\.\d+)?", (s or "").replace("INR", ""))
    return float(m.group(0).replace(",", "")) if m else None


def _date(s):
    s = (s or "").strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return s or None


def _month(s):
    for fmt in ("%B %Y", "%b %Y", "%m/%Y", "%Y-%m"):
        try:
            return datetime.strptime((s or "").strip(), fmt).strftime("%Y-%m")
        except ValueError:
            pass
    return s or None


def extract(pdf: Path, kind: str) -> dict:
    """Returns {fields, confidence, engine, ms, error}."""
    t = time.time()
    try:
        if not ENABLED:
            raise RuntimeError("Textract is off (TEXTRACT=off in config)")
        out = _textract(pdf, kind)
        out.update(engine=ENGINE, ms=int((time.time() - t) * 1000), error=None)
        return out
    except Exception as e:  # noqa: BLE001 - no network / no credentials: fall back to the text layer
        err = f"{type(e).__name__}: {str(e)[:160]}"
    out = _text_layer(pdf, kind)
    out.update(engine="pdf-text rules (fallback)", ms=int((time.time() - t) * 1000), error=err)
    return out


def _textract(pdf: Path, kind: str) -> dict:
    import boto3
    from botocore.config import Config
    tx = boto3.Session(profile_name=PROFILE).client("textract", region_name=REGION,
                                                     config=Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 4, "mode": "adaptive"}))
    feats = ["QUERIES"] + (["TABLES"] if kind == "PAYSLIP" else [])
    r = tx.analyze_document(Document={"Bytes": pdf.read_bytes()}, FeatureTypes=feats,
                            QueriesConfig={"Queries": [{"Text": q, "Alias": a} for a, q in QUERIES[kind]]})
    by = {b["Id"]: b for b in r["Blocks"]}
    raw, conf = {}, {}
    for b in r["Blocks"]:
        if b["BlockType"] == "QUERY":
            ans = [by[i] for rel in b.get("Relationships", []) for i in rel["Ids"] if by[i]["BlockType"] == "QUERY_RESULT"]
            best = max(ans, key=lambda a: a.get("Confidence", 0), default=None)
            raw[b["Query"]["Alias"]] = best.get("Text") if best else None
            conf[b["Query"]["Alias"]] = round((best.get("Confidence", 0) if best else 0) / 100, 3)
    f = dict(raw)
    if kind == "PAYSLIP":
        for k in ("gross", "deductions", "net"):
            f[k] = _amount(raw.get(k))
        f["dateOfJoining"], f["payMonth"] = _date(raw.get("dateOfJoining")), _month(raw.get("payMonth"))
        f["lineItems"] = _payslip_lines(r["Blocks"], by)
        f["bonus"] = sum(li["amount"] for li in f["lineItems"] if li["kind"] == "earning" and not li["recurring"])
        if None not in (f["gross"], f["deductions"], f["net"]) and abs(f["gross"] - f["deductions"] - f["net"]) > 1:
            conf["net"] = min(conf.get("net", 0), 0.5)          # the numbers do not add up: a person must look
            f["notes"] = f"Arithmetic check failed: gross {f['gross']:,.0f} - deductions {f['deductions']:,.0f} != net {f['net']:,.0f}."
        else:
            f["notes"] = "Payslip includes a one-time payment." if f["bonus"] else ""
    elif kind == "ID_PROOF":
        f["dob"], f["idType"] = _date(raw.get("dob")), "PAN"
    elif kind == "APPLICATION":
        _application(f)
    else:
        f["joiningDate"] = _date(raw.get("joiningDate"))
    return {"fields": f, "confidence": {k: conf.get(k, 0.0) for k in CONF_KEYS[kind]}}


def _application(f):
    """Typed values from the form's answers: amounts and tenure as numbers, the account as digits, city and PIN apart."""
    f["dob"] = _date(f.get("dob"))
    f["amount"], f["declaredNet"] = _amount(f.get("amount")), _amount(f.get("declaredNet"))
    t = _amount(f.get("term"))
    f["term"] = int(t) if t else None
    f["account"] = re.sub(r"\D", "", f.get("account") or "") or None
    f["pan"] = re.sub(r"\s", "", (f.get("pan") or "").upper()) or None
    m = re.match(r"(.*?)[\s,]*(\d{6})$", (f.pop("cityPin", None) or "").strip())
    f["city"], f["pin"] = (m.group(1).strip(), m.group(2)) if m else (None, None)


def _payslip_lines(blocks, by):
    """Line items from the table(s) whose header says Earnings / Deductions. Each label column is read with the amount
    column to its right; the header above the label says which kind it is. Totals rows are skipped."""
    items = []
    for t in (b for b in blocks if b["BlockType"] == "TABLE"):
        cells = {}
        for i in (i for rel in t.get("Relationships", []) if rel["Type"] == "CHILD" for i in rel["Ids"]):
            c = by[i]
            if c["BlockType"] != "CELL":
                continue
            words = [by[w]["Text"] for rel in c.get("Relationships", []) if rel["Type"] == "CHILD" for w in rel["Ids"]
                     if by[w]["BlockType"] == "WORD"]
            cells[(c["RowIndex"], c["ColumnIndex"])] = " ".join(words)
        header = {col: txt for (row, col), txt in cells.items() if row == 1}
        if not any(re.search(r"earning|deduction", h, re.I) for h in header.values()):
            continue                                   # not the pay table (e.g. the employee details block)
        ncol = max(col for _, col in cells)
        for row in sorted({r for r, _ in cells if r > 1}):
            for lc in range(1, ncol, 2):
                label, amt = cells.get((row, lc), "").strip(), _amount(cells.get((row, lc + 1)))
                if not label or amt is None or re.search(r"total|gross|net pay|amount", label, re.I):
                    continue
                kind = "deduction" if re.search(r"deduct", header.get(lc, ""), re.I) else "earning"
                items.append({"label": label, "amount": amt, "kind": kind, "recurring": not ONE_TIME.search(label)})
    return items


def _num(s):
    return float(s.replace(",", ""))


def _text_layer(pdf: Path, kind: str) -> dict:
    import pdfplumber
    with pdfplumber.open(pdf) as p:
        text = "\n".join(page.extract_text() or "" for page in p.pages)
    lines = [l.strip() for l in text.splitlines() if l.strip() and "SYNTHETIC" not in l]
    f, conf = {}, {}
    if kind == "PAYSLIP":
        def grab(rx, cast=str):
            m = re.search(rx, text)
            return cast(m.group(1).strip()) if m else None
        f["employer"] = re.split(r"\s+(?:Payslip for|SALARY SLIP)", lines[0])[0] if lines else None
        f["employerAddress"] = next((l for l in lines[:4] if re.search(r"\b\d{6}\b", l)), None)
        f["employeeName"] = grab(r"Employee name\s+(.+?)\s+Employee ID")
        f["dateOfJoining"] = _date(grab(r"Date of joining\s+(\d\d-\d\d-\d{4})"))
        f["gross"] = grab(r"Gross earnings\s+([\d,]+)", _num)
        f["deductions"] = grab(r"Total deductions\s+([\d,]+)", _num)
        f["net"] = grab(r"NET PAY\s+INR\s+([\d,]+)", _num)
        f["bonus"] = sum(_num(x) for x in re.findall(r"[Bb]onus[^\d\n]*([\d,]{4,})", text))
        mm = re.search(r"(?:Payslip for|SALARY SLIP -)\s+(\w+\s+\d{4})", text, re.I)
        f["payMonth"] = _month(mm.group(1).title()) if mm else None
        f["notes"] = "Payslip includes a one-time payment." if f["bonus"] else ""
    elif kind == "APPLICATION":
        def box(label):
            m = re.search(re.escape(label) + r"[^\n]*\n(.+)", text)
            return m.group(1).strip() if m else None
        # two boxes per line: the label line holds both labels, the next line both values
        pairs = [("Full name", "Date of birth", "name", "dob"), ("PAN", "Mobile number", "pan", "mobile"),
                 ("Email", "City and PIN code", "email", "cityPin"), ("Employer", "Employment type", "employer", None),
                 ("Salary account number", "Monthly take-home pay", "account", "declaredNet"),
                 ("Loan amount requested", "Tenure (months)", "amount", "term")]
        for la, lb, ka, kb in pairs:
            v = box(la)
            if not v:
                continue
            if kb == "dob" or kb == "mobile":
                a_, _, b_ = v.rpartition(" ")
                f[ka], f[kb] = a_, b_
            elif kb == "cityPin":
                parts = v.split(" ")
                f[ka], f[kb] = parts[0], " ".join(parts[1:])
            elif kb == "declaredNet":
                f[ka], f[kb] = v.split(" ")[0], v.split(" ", 1)[1] if " " in v else None
            elif kb == "term":
                f[ka], f[kb] = v.split(" ")[0], v.split(" ")[-1]
            else:
                f[ka] = v.split(" Salaried")[0] if la == "Employer" else v
        f["purpose"] = box("Purpose of the loan")
        _application(f)
    elif kind == "ID_PROOF":
        for k, rx in (("name", r"Name\s*\n(.+)"), ("dob", r"Date of birth\s*\n(.+)"), ("idNumber", r"ID number \(PAN\)\s*\n(.+)")):
            m = re.search(rx, text)
            f[k] = m.group(1).strip() if m else None
        f["dob"], f["idType"] = _date(f.get("dob")), "PAN"
    else:
        f["employer"] = lines[0] if lines else None
        m = re.search(r" as ((?:\w+ ){0,4}\w+) since (\d{1,2} \w+ \d{4})", text.replace("\n", " "))
        f["designation"], f["joiningDate"] = (m.group(1), _date(m.group(2))) if m else (None, None)
        f["employmentType"] = "Permanent" if "permanent" in text.lower() else None
    conf = {k: (0.9 if f.get(k) not in (None, "") else 0.0) for k in CONF_KEYS[kind]}
    return {"fields": f, "confidence": conf}
