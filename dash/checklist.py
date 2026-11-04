"""The review checklist: one line per thing a credit officer must be satisfied about (identity, income, ...), with the
evidence underneath it, indented: which document or system it came from, what was read, how sure the reader was.

A line is green when the system verified it, amber when a referral rule fired on it (a person reviews and annotates it),
red when a decline rule fired, purple when it needs a senior signature. Nothing here decides: the rules in
LOS_POLICY.REFERRAL_RULES do, in the database. This module only lays out what the LOS service returned.
"""
from datetime import date

from fmt import esc, inr, pct

# ------------------------------------------------------------------ the checklist
# which rules belong to which line; R03 (unreadable document) goes to the line whose document was hard to read
ITEMS = [
    ("data", "Data contracts", ["R13"]),
    ("identity", "Identity and KYC", ["R12", "D03"]),
    ("income", "Income", ["R02", "R09", "R10"]),
    ("employment", "Employment", ["R06"]),
    ("credit", "Credit history and score", ["R05", "R01", "D01"]),
    ("afford", "Affordability", ["R04", "D02"]),
    ("conduct", "Account conduct", ["R07", "R08"]),
    ("authority", "Approval authority", ["R11"]),
]
OPTIONS = {
    "data": ["Missing data obtained from the applicant", "Proceed: the gap is explained", "Not acceptable"],
    "identity": ["Identity confirmed (video KYC)", "Send to the fraud desk"],
    "income": ["Use regular salary only (exclude one-time pay)", "Accept the payslip as stated", "Ask for three more payslips"],
    "employment": ["Confirmed with the employer", "Ask for the offer letter"],
    "credit": ["Bureau report checked, acceptable", "Not acceptable"],
    "afford": ["Within the cap: accept", "Reduce to the affordable maximum"],
    "conduct": ["Explained by the applicant", "Not acceptable"],
}
REGULAR = OPTIONS["income"][0]


def _src(kind, label):
    return f'<span class="src {kind}">{label}</span>'


def _doc(file, kind, engine, conf, body="", href=None):
    name = f'<a href="{href}" target="_blank">{esc(file)}</a>' if href else f"<b>{esc(file)}</b>"
    how = "typed into the record (synthetic, no PDF)" if "synthetic" in str(engine) else f"read by {esc(engine)}"
    c = f' &middot; confidence {pct(conf)}' if conf not in (None, "") else ""
    return f'<li>{_src("doc", "PDF")}{name} <span class="mt">{esc(kind)} &middot; {how}{c}</span>{body}</li>'


def _sys(kind, label, title, meta, body=""):
    return f'<li>{_src(kind, label)}<b>{esc(title)}</b> <span class="mt">{esc(meta)}</span>{body}</li>'


def _kv(pairs, bad=()):
    return '<ul class="kv">' + "".join(f'<li class="{"bad" if k in bad else ""}"><span>{esc(k)}</span><b>{v}</b></li>' for k, v in pairs) + "</ul>"


def build(d, href_base=None, form=None):
    """d = the LOS service's case.load. href_base: URL prefix the console serves uploaded PDFs under. form = the form's fields."""
    c, a, p, idp, let, bu, cu = d["c"], d["app"], d["pay"], d["idp"], d["letter"], d["bureau"], d["cust"]
    pol = d["policy"]
    fired = {h["RULE_ID"]: h for h in d["hits"]}
    docs = {x["DOC_TYPE"]: x for x in d["docs"]}
    up = set(d.get("uploaded") or [])
    href = (lambda f: f"{href_base}{f}" if href_base and f in up else None)
    form = form or {}
    fd = docs.get("APPLICATION_FORM")
    low_id = (idp.get("MIN_CONFIDENCE") or 1) < (p.get("MIN_CONFIDENCE") or 1)
    lines = d["lines"]
    one_time = [l for l in lines if l["KIND"] == "earning" and str(l["RECURRING"]).lower() in ("false", "0")]
    sal = d["salary"]["rows"]
    out = []

    def item(key, title, rules, finding, tree):
        rules = list(rules) + (["R03"] if "R03" in fired and key == ("identity" if low_id else "income") else [])
        hit = [fired[r] for r in rules if r in fired]
        status = "decline" if any(h["OUTCOME"] == "DECLINE" for h in hit) else "sign" if key == "authority" and hit \
            else "review" if hit else "auto"
        out.append({"key": key, "title": title, "status": status, "finding": finding, "tree": tree,
                    "rules": [(h["RULE_ID"], h["TITLE"], h["EVIDENCE"], h["WHY_A_PERSON"]) for h in hit],
                    "options": OPTIONS.get(key, ["Checked: acceptable", "Not acceptable"])})

    # ---- data contracts: what each source promised, kept or not (LOS_SEM, checked on the upload)
    crs = d.get("contracts") or []
    kept = lambda r: str(r["PASSED"]).lower() in ("true", "1")  # noqa: E731
    kind = {"Document store": ("doc", "MongoDB"), "Core banking": ("db", "Core banking"), "Credit bureau": ("ext", "Bureau"), "Cross-system": ("exa", "Exasol")}
    tree, groups = "", {}
    for r in crs:
        groups.setdefault(r["SOURCE_SYSTEM"], []).append(r)
    for g, rs in groups.items():
        k, lbl = kind.get(g, ("exa", g))
        tree += _sys(k, lbl, f"{g}: {sum(kept(r) for r in rs)} of {len(rs)} contracts kept", f"owed by {rs[0]['OWNER']}",
                     '<ul class="cl1">' + "".join(
                         f'<li class="{"ok" if kept(r) else "crit" if r["SEVERITY"] == "CRITICAL" else "warn"}"><i>{"&#10003;" if kept(r) else "&times;" if r["SEVERITY"] == "CRITICAL" else "!"}</i>'
                         f'<b>{esc(r["CONTRACT_ID"])}</b><span>{esc(r["EXPECTATION"])}</span><code>{esc(r["EVIDENCE"])}</code></li>' for r in rs) + "</ul>")
    broken = [r for r in crs if not kept(r)]
    crit = [r for r in broken if r["SEVERITY"] == "CRITICAL"]
    if crs:
        item("data", "Data contracts", ["R13"],
             ("Every source delivered what it promised." if not broken else
              f"{len(crs) - len(broken)} of {len(crs)} contracts kept. " + "; ".join(f"{r['CONTRACT_ID']}: {esc(r['EVIDENCE'])}" for r in (crit or broken)[:3])
              + ("." if crit else " (warning only: reported to the source's owner)")), tree)

    # ---- identity
    pan_doc = idp.get("ID_NUMBER")
    same = lambda x, y: str(x or "").strip().upper() == str(y or "").strip().upper()  # noqa: E731
    customer = bool(cu.get("CUST_ID"))
    ok_name = same(idp.get("NAME_ON_ID"), c.get("APPLICANT_NAME"))
    ok_pan = same(pan_doc, cu.get("PAN_ON_RECORD")) if customer else True
    tree = ""
    if "ID_PROOF" in docs:
        x = docs["ID_PROOF"]
        tree += _doc(x["FILE_NAME"], "PAN card", x["ENGINE"], x["MIN_CONF"], _kv(
            [("Name", esc(idp.get("NAME_ON_ID"))), ("PAN", esc(pan_doc)), ("Date of birth", esc(idp.get("DOB_ON_ID")))],
            bad=() if ok_name else ("Name",)), href(x["FILE_NAME"]))
    if fd:
        tree += _doc(fd["FILE_NAME"], "Application form", fd["ENGINE"], fd["MIN_CONF"], _kv(
            [("Name", esc(c.get("APPLICANT_NAME"))), ("Date of birth", esc(a.get("BIRTH_DATE"))), ("Mobile", esc(a.get("MOBILE")))]), href(fd["FILE_NAME"]))
    if customer:
        tree += _sys("db", "Core banking", f"Customer {cu.get('CUST_ID')}", "Postgres, read live",
                     _kv([("Name on record", esc(cu.get("NAME_ON_RECORD"))), ("PAN on record", esc(cu.get("PAN_ON_RECORD"))),
                          ("KYC done", "yes" if cu.get("KYC_DONE") == "Y" else "no"), ("Customer since", esc(cu.get("CUST_SINCE")))],
                         bad=() if ok_pan else ("PAN on record",)))
    else:
        tree += _sys("db", "Core banking", "Not a bank customer", "nothing to compare: the documents and the bureau carry identity", "")
    item("identity", "Identity and KYC", ["R12", "D03"],
         ("Name and PAN agree across the PAN card, the application and the bank's own records." if customer
          else "Name and PAN agree across the PAN card and the application; not a bank customer, so there is no bank record.")
         if ok_name and ok_pan else "The name or PAN on the documents does not match.", tree)

    # ---- income
    gap = c.get("INCOME_GAP_PCT")
    avg = c.get("BANK_SALARY_AVG")
    if sal:
        mx = max(float(r["NET_CREDITED"]) for r in sal) or 1
        net = float(p.get("NET") or 0)
        bars = '<div class="sbars">' + "".join(
            f'<div class="sb{" hi" if net and abs(float(r["NET_CREDITED"]) - net) < 1 and abs(net - float(avg or 0)) > 1 else ""}">'
            f'<i style="height:{100 * float(r["NET_CREDITED"]) / mx:.0f}%"></i><b>{float(r["NET_CREDITED"]) / 1e5:.2f} L</b>'
            f'<span>{date.fromisoformat(str(r["MON"])[:10]).strftime("%b")}</span></div>' for r in sal) + "</div>"
    else:
        bars = '<div class="mt">No salary credits found in the six months before the application.</div>'
    tree = ""
    if "PAYSLIP" in docs:
        x = docs["PAYSLIP"]
        li = [(esc(l["LINE_ITEM"]), inr(l["AMOUNT"])) for l in lines if l["KIND"] == "earning"]
        tree += _doc(x["FILE_NAME"], f"Payslip {p.get('PAY_MONTH') or ''}", x["ENGINE"], p.get("MIN_CONFIDENCE"),
                     _kv([("Gross", inr(p.get("GROSS"))), ("Deductions", inr(p.get("DEDUCTIONS"))), ("Net pay", inr(p.get("NET")))])
                     + ('<div class="mt" style="margin:.35rem 0 0 1.4rem">Earnings, line by line</div>'
                        + _kv(li, bad=tuple(esc(l["LINE_ITEM"]) for l in one_time)) if li else ""), href(x["FILE_NAME"]))
    if customer:
        tree += _sys("db", "Core banking", "Salary credited, six months before the application", "Postgres, read live",
                     bars + (f'<div class="mt">Average {inr(avg)} a month, paid from {esc(c.get("PAYER_ACCT"))}</div>' if avg else ""))
    else:
        tree += _sys("db", "Core banking", "Not a bank customer", "the salary is paid into another bank: income is taken from the documents", "")
    if form.get("declaredNet") and fd:
        tree += _doc(fd["FILE_NAME"], "Application form", fd["ENGINE"], None, _kv([("Take-home pay declared", inr(form["declaredNet"]))]), href(fd["FILE_NAME"]))
    if one_time:
        ot = " The payslip itself lists " + ", ".join(f'{esc(l["LINE_ITEM"])} {inr(l["AMOUNT"])}' for l in one_time) + "."
    else:
        ot = ""
    if gap is not None and float(gap) > 15:
        finding = f"Payslip net {inr(p.get('NET'))} is {float(gap):.0f}% away from what the bank actually received ({inr(avg)} a month).{ot}"
    elif sal:
        finding = f"Payslip and bank agree: {inr(p.get('NET'))} on the payslip, {inr(avg)} a month received.{ot}"
    elif not customer:
        finding = f"Not a bank customer: income taken from the payslip ({inr(p.get('GROSS'))} gross, {inr(p.get('NET'))} net); no bank record to check it against.{ot}"
    else:
        finding = "No salary credits to check the payslip against."
    item("income", "Income", ["R02", "R09", "R10"], finding, tree)

    # ---- employment
    tree = ""
    if "EMPLOYMENT_LETTER" in docs:
        x = docs["EMPLOYMENT_LETTER"]
        tree += _doc(x["FILE_NAME"], "Employment letter", x["ENGINE"], x["MIN_CONF"], _kv(
            [("Employer", esc(let.get("EMPLOYER"))), ("Designation", esc(let.get("DESIGNATION"))), ("Employed since", esc(let.get("JOINING_DATE"))),
             ("Type", esc(let.get("EMPLOYMENT_TYPE")))]), href(x["FILE_NAME"]))
    if "PAYSLIP" in docs:
        tree += _doc(docs["PAYSLIP"]["FILE_NAME"], "Payslip", docs["PAYSLIP"]["ENGINE"], None,
                     _kv([("Employer", esc(p.get("EMPLOYER"))), ("Date of joining", esc(c.get("DATE_OF_JOINING")))]), href(docs["PAYSLIP"]["FILE_NAME"]))
    if sal:
        tree += _sys("db", "Core banking", "Who pays the salary", "Postgres, read live", f'<div class="mono">{esc(sal[-1].get("NARRATION"))}</div>')
    yrs = c.get("EMP_YEARS")
    item("employment", "Employment", ["R06"],
         f"{esc(c.get('EMPLOYER') or p.get('EMPLOYER'))}, {int(yrs or 0)} years" + (", permanent" if str(let.get("EMPLOYMENT_TYPE", "")).lower() == "permanent" else "")
         + (". The salary credits name the same employer." if sal else "."), tree)

    # ---- credit
    neg = sorted([r for r in d["contrib"] if float(r["POINTS"]) < 0], key=lambda r: float(r["POINTS"]))[:3]
    br = d.get("bureau_report") or {}
    pdf = next((f for f in up if f.startswith("5_credit_bureau_report")), None)
    tree = ""
    if pdf:
        tree += _doc(pdf, "Credit report (PDF)", "the credit report API", None,
                     _kv([("Report", esc(br.get("REPORT_ID"))), ("API answered", f"HTTP {esc(br.get('HTTP_STATUS'))} in {esc(br.get('MS'))} ms")]), href(pdf))
    tree += _sys("ext", "Credit report", "Credit report API",
                 (f"API call from Exasol (Python UDF), {str(bu.get('PULLED_AT') or '')[:16]}" if br else f"pulled {str(bu.get('PULLED_AT') or '')[:16]}") if bu else "no record",
                _kv([("Bureau score", esc(bu.get("BUREAU_SCORE"))), ("Enquiries, last 6 months", esc(bu.get("INQ_6M"))),
                     ("Active loans", esc(bu.get("ACTIVE_LOANS"))), ("Existing EMIs", inr(bu.get("EXISTING_EMI")))]) if bu else "")
    tree += _sys("exa", "Exasol", f"Scorecard {esc(d['model'].get('MODEL_VERSION'))}", "a table, scored in SQL",
                 _kv([("Score", f"{int(c['SCORE'])} (approve from {int(pol.get('APPROVE_FROM') or 0)})"), ("Band and rate", f"{esc(c['BAND'])} &middot; {c['RATE']}%"),
                      ("Probability of default", f"{c.get('PD_PCT')}%")]
                     + [(f"— {r['REASON']}", f"{float(r['POINTS']):+.0f} pts") for r in neg]))
    ml, ml_say = (d.get("ml") or {}).get("ML_PD_PCT"), ""
    if ml is not None:
        sc, ml = float(c.get("PD_PCT") or 0), float(ml)
        verdict = ("sees more risk than the scorecard: worth a closer look" if ml >= max(1.5 * sc, sc + 3)
                   else "sees less risk than the scorecard" if sc >= max(1.5 * ml, ml + 3) else "agrees with the scorecard")
        mm = d.get("ml_model") or {}
        tree += _sys("exa", "Exasol", f"Second opinion: ML model {esc(mm.get('MODEL_VERSION'))}",
                     "Python (gradient boosting) running inside Exasol as a UDF; it does not decide",
                     _kv([("Probability of default", f"{ml:.1f}% (scorecard {sc:.1f}%)"), ("Verdict", verdict),
                          ("Trained on", f"{int(mm.get('TRAIN_LOANS') or 0):,} loans, AUC {mm.get('AUC_OUT_OF_TIME')} out of time")]))
        ml_say = f" ML second opinion: PD {ml:.1f}%, {verdict.split(':')[0]}."
    item("credit", "Credit history and score", ["R05", "R01", "D01"],
         (f"Bureau {esc(bu.get('BUREAU_SCORE'))}, scorecard {int(c['SCORE'])}: band {esc(c['BAND'])} at {c['RATE']}%." if bu
          else f"No bureau record; scorecard {int(c['SCORE'])} uses the book average.") + ml_say, tree)

    # ---- affordability
    cap = float(pol.get("FOIR_CAP") or 45)
    foir = float(c.get("FOIR_PCT") or 0)
    tree = _sys("exa", "Exasol", "Repayments as a share of verified income (FOIR)", f"tested at the {pol.get('ASSESSMENT_RATE')}% assessment rate",
                f'<div class="foir"><div class="ft"><i style="width:{min(foir, 70) / 70 * 100:.0f}%" class="{"hi" if foir > cap - float(pol.get("FOIR_NEAR_BAND") or 3) else ""}"></i>'
                f'<s style="left:{cap / 70 * 100:.0f}%"></s></div><b>{foir:.1f}%</b><span>cap {cap:.0f}%</span></div>'
                + _kv([("Verified monthly income", inr(c.get("VERIFIED_GROSS"))), ("Existing EMIs", inr(c.get("EXISTING_EMI"))),
                       ("Requested", f"{inr(c['AMOUNT_REQUESTED'])} over {int(c['TERM_MONTHS'])} months"),
                       ("Most it can afford", inr(c.get("MAX_AMOUNT")))]))
    item("afford", "Affordability", ["R04", "D02"],
         f"FOIR {foir:.1f}% against a {cap:.0f}% cap; affordable up to {inr(c.get('MAX_AMOUNT'), True)}.", tree)

    # ---- conduct
    if customer:
        tree = _sys("db", "Core banking", "The salary account, six months", "Postgres, read live",
                    _kv([("Returned debits (bounces)", esc(c.get("RETURNED_DEBITS_6M"))), ("Spent on online gaming", f"{float(c.get('GAMING_PCT') or 0):.1f}% of credits")]))
        conduct = "No bounced payments, no gaming spend." if not fired.keys() & {"R07", "R08"} else "The account shows bounced payments or gaming spend."
    else:
        tree = _sys("db", "Core banking", "Not a bank customer", "no account history with us to check", "")
        conduct = "Not a bank customer: no account history with us to check."
    item("conduct", "Account conduct", ["R07", "R08"], conduct, tree)

    # ---- authority
    lim = float(pol.get("AUTO_APPROVE_LIMIT") or 1e6)
    who = [f'{esc(r["REVIEWER"])} ({esc(r["REVIEW_LEVEL"])}, up to {inr(r["MAX_AMOUNT"], True)})' for r in d["auth"] if float(r["MAX_AMOUNT"]) > 0]
    item("authority", "Approval authority", ["R11"],
         f"{inr(c['AMOUNT_REQUESTED'], True)} is above the {inr(lim, True)} the system may approve alone: a senior underwriter signs."
         if float(c["AMOUNT_REQUESTED"]) > lim else f"{inr(c['AMOUNT_REQUESTED'], True)} is within the {inr(lim, True)} the system may approve alone.",
         _sys("exa", "Policy", f"Version {int(pol.get('POLICY_VERSION') or 1)}", "who may sign what", "<ul class='kv'>" + "".join(f"<li><span>{w}</span></li>" for w in who) + "</ul>"))
    return out
