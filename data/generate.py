"""Synthetic loan pipeline for the Demo Finance demo -> core banking (Postgres) + document store (MongoDB) + bureau.

Deterministic (seeded). What it writes:
  Postgres  core_banking.cbs   CUST_MST, ACCT_MST, TXN_HIST   salary accounts and ~7 months of transactions
  MongoDB   lending            applications, documents        what the applicant typed + what was extracted from each PDF
  CSV       .work/bureau.csv                                  the credit bureau response per application (mocked)
  JSON      .work/truth.json                                  what was planted, so the checks can be measured

The applicants' risk profiles are SAMPLED FROM REAL LENDING CLUB LOANS (bureau score, inquiries, public records,
existing debt ratio, loan-to-income, tenure), then given Indian names, INR incomes and transactions. So the scorecard
sees the joint distribution it was trained on, not invented numbers. Planted on top:
  * the hero, Karthik Raghunathan: the latest payslip carries a one-off bonus, the bank shows the regular salary
  * a ring of 14 applications: 4 "employers", one payslip template, salaries paid from 3 personal accounts,
    amounts just under the auto-approval limit. Every check on each application passes on its own.
  * the usual edge cases at realistic rates: inflated payslips, unreadable scans, bounced debits, gaming spend,
    irregular income, thin bureau files, an ID that does not match the application, under-age applicants.
"""
import csv
import datetime as dt
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from los_config import port, source_secret, vm_ip  # noqa: E402
WORK = ROOT / ".work"
N_APPS = 2400
AS_OF = dt.date(2026, 10, 24)              # the pipeline covers the 30 days to this date
HIST_FROM = dt.date(2026, 3, 1)            # transactions from here (7+ months)
AUTO_LIMIT = 1_000_000                     # the auto-approval limit the ring structures under
rng = random.Random(20261103)
np.random.seed(20261103)

FIRST = ["Aarav", "Aditi", "Akash", "Ananya", "Anil", "Anjali", "Arjun", "Arun", "Bhavana", "Deepa", "Deepak", "Divya",
         "Ganesh", "Gayathri", "Gokul", "Harini", "Hari", "Ishaan", "Janani", "Karthik", "Kavya", "Keerthana", "Kiran",
         "Lakshmi", "Madhavan", "Mahesh", "Meera", "Mohan", "Nandini", "Naveen", "Nikhil", "Nisha", "Pooja", "Pradeep",
         "Priya", "Rahul", "Rajesh", "Ramya", "Ravi", "Rekha", "Rohan", "Sanjay", "Saranya", "Shalini", "Shreya",
         "Siddharth", "Sneha", "Sriram", "Suresh", "Swathi", "Tarun", "Uma", "Varun", "Vidya", "Vignesh", "Vijay",
         "Vinod", "Yamini", "Farhan", "Ayesha", "Imran", "Sana", "Joseph", "Mary", "Thomas", "Anita", "Gurpreet", "Harpreet"]
LAST = ["Iyer", "Iyengar", "Krishnan", "Raghunathan", "Subramanian", "Venkatesh", "Natarajan", "Ramasamy", "Pillai",
        "Nair", "Menon", "Reddy", "Rao", "Naidu", "Sharma", "Verma", "Gupta", "Agarwal", "Patel", "Shah", "Desai",
        "Kulkarni", "Joshi", "Deshpande", "Banerjee", "Chatterjee", "Das", "Bose", "Singh", "Kaur", "Khan", "Sheikh",
        "D'Souza", "Fernandes", "Thomas", "George", "Mathew", "Chandran", "Sundaram", "Balasubramanian"]
CITIES = [("Chennai", "600"), ("Bengaluru", "560"), ("Hyderabad", "500"), ("Coimbatore", "641"), ("Pune", "411"),
          ("Mumbai", "400"), ("Kochi", "682"), ("Madurai", "625"), ("Mysuru", "570"), ("Visakhapatnam", "530")]
PURPOSES = ["Home renovation", "Wedding", "Medical", "Education", "Debt consolidation", "Travel", "Vehicle", "Business"]
# Fictional bank codes in the IFSC shape (4 letters + 0 + branch): no real bank is a party to any transaction.
BANKS = ["WGRB", "CNTB", "FBKB", "NWDB", "TLSB", "LTWB", "ADVB", "PRSB"]
SUFFIX = ["Technologies Pvt Ltd", "Systems Pvt Ltd", "Infotech Ltd", "Solutions Pvt Ltd", "Engineering Ltd",
          "Logistics Pvt Ltd", "Pharma Ltd", "Textiles Ltd", "Auto Components Ltd", "Retail Pvt Ltd", "Finserv Ltd",
          "Healthcare Pvt Ltd", "Constructions Ltd", "Foods Pvt Ltd", "Analytics Pvt Ltd"]
STEMS = ["Brightline", "Kaveri", "Sahyadri", "Coromandel", "Vindhya", "Indus", "Meridian", "Lotus", "Tranquebar",
         "Nilgiri", "Godavari", "Deccan", "Malabar", "Konark", "Hampi", "Aravalli", "Saffron", "Peacock", "Banyan",
         "Monsoon", "Cauvery", "Narmada", "Ashoka", "Chola", "Pallava", "Vijaya", "Sindhu", "Ganga", "Thar", "Sundar"]
PAYROLL_TOOLS = ["PayrollOne 4.2", "HRMSuite 11.3", "PayDesk 2025.3", "SalaryCloud 7.1", "PeopleLedger 5.0"]


def ifsc(bank):
    return f"{bank}000{rng.randint(1000, 9999)}"


def acct_no(prefix="5010"):
    return prefix + "".join(str(rng.randint(0, 9)) for _ in range(10))


def last_working_day(y, m):
    d = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def months_between(a, b):
    out, y, m = [], a.year, a.month
    while dt.date(y, m, 1) <= b:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def pan():
    L = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(rng.choice(L) for _ in range(3)) + "P" + rng.choice(L) + f"{rng.randint(1000, 9999)}" + rng.choice(L)


def h8(s):
    return hashlib.sha1(s.encode()).hexdigest()[:8]


# ------------------------------------------------------------------ employers
employers = []
used = set()
while len(employers) < 46:
    n = f"{rng.choice(STEMS)} {rng.choice(SUFFIX)}"
    if n in used:
        continue
    used.add(n)
    city = rng.choice(CITIES)
    employers.append(dict(name=n, address=f"{rng.randint(2, 480)}, {rng.choice(['IT Expressway', 'MG Road', 'Mount Road', 'Outer Ring Road', 'Hitech City Road', 'Industrial Estate', 'Anna Salai', 'Residency Road'])}, {city[0]} {city[1]}{rng.randint(1, 99):03d}",
                          bank=rng.choice(BANKS), acct=acct_no("9120"), tool=rng.choice(PAYROLL_TOOLS), template=h8(n)))
employers[0].update(name="Brightline Systems Pvt Ltd", address="114, IT Expressway, Sholinganallur, Chennai 600119")
employers[0]["template"] = h8(employers[0]["name"])
RING_EMPLOYERS = [dict(name=n, address=a, template="a91f3c07", tool="Online Payslip Maker 3.2") for n, a in [
    ("Apex Novatech Solutions", "Unit 7, 3rd Floor, Velachery Main Road, Chennai 600042"),
    ("Zenlore Infotech Pvt Ltd", "Plot 22, Phase 2, Electronic City, Bengaluru 560100"),
    ("Bluefinch Digital Services", "Shop 4, Madhapur Main Road, Hyderabad 500081"),
    ("Orbiq Analytics LLP", "No. 9, Avinashi Road, Coimbatore 641018")]]
RING_PAYERS = [("WGRB0004417", "20114587320"), ("CNTB0006632", "663201009874"), ("NWDB0001190", "919010044215")]

# ------------------------------------------------------------------ risk profiles sampled from the real book
book = pd.read_csv(WORK / "book.csv", usecols=["ISSUE_DATE", "TERM_MONTHS", "EMP_YEARS", "DTI_BEFORE", "LOAN_TO_INCOME",
                                                "INQ_6M", "PUB_REC", "BUREAU_SCORE"])
book = book[book["ISSUE_DATE"] >= "2016-01-01"].sample(N_APPS, random_state=7).reset_index(drop=True)

apps, docs, bureau, custs, accts, truth = [], [], [], [], [], {"ring": [], "planted": {}}
txns = []
txn_id = [9_000_000]


def tx(acct, d, amt, drcr, narr, chnl, cp_acct=None, cp_ifsc=None):
    txn_id[0] += rng.randint(1, 9)
    txns.append([txn_id[0], acct, d, round(amt, 2), drcr, narr[:120], chnl, cp_acct, cp_ifsc])


def spend_month(acct, y, m, net, end, frac, flags):
    """Ordinary month of spending for a salaried person; returns nothing, appends txns."""
    days = (min(last_working_day(y, m) + dt.timedelta(days=3), end) - dt.date(y, m, 1)).days
    if days <= 0:
        return
    pick = lambda: dt.date(y, m, 1) + dt.timedelta(days=rng.randint(0, days))  # noqa: E731
    budget = net * frac
    if flags.get("rent"):
        d = dt.date(y, m, min(3, days + 1))
        if d <= end:
            tx(acct, d, flags["rent"], "D", f"UPI/DR/{rng.randint(10**11, 10**12 - 1)}/RENT {flags['landlord']}", "UPI")
            budget -= flags["rent"]
    for _ in range(rng.randint(1, 3)):
        a = rng.choice([2000, 3000, 5000, 10000])
        tx(acct, pick(), a, "D", f"ATM WDL/{rng.choice(CITIES)[0].upper()}/{rng.randint(100000, 999999)}", "ATM")
        budget -= a
    for nm in ("TNEB ELECTRICITY", "AIRTEL POSTPAID", "ACT FIBERNET", "INDANE GAS"):
        if rng.random() < .7:
            a = rng.uniform(300, 2800)
            tx(acct, pick(), a, "D", f"BBPS/DR/{nm}", "BBPS")
            budget -= a
    if rng.random() < .8:
        a = max(0, budget * rng.uniform(.2, .4))
        tx(acct, pick(), a, "D", "CC PAYMENT/AUTOPAY", "NEFT")
        budget -= a
    if flags.get("gaming"):
        for _ in range(rng.randint(4, 12)):
            a = net * rng.uniform(.008, .025)
            tx(acct, pick(), a, "D", f"UPI/DR/{rng.randint(10**11, 10**12 - 1)}/ONLINE GAMING WALLET", "UPI")
            budget -= a
    k = rng.randint(10, 22)
    for _ in range(k):
        a = max(50, budget / k * rng.uniform(.4, 1.6))
        tx(acct, pick(), a, "D", f"UPI/DR/{rng.randint(10**11, 10**12 - 1)}/{rng.choice(['SWIGGY', 'ZEPTO', 'BIGBASKET', 'DMART', 'AMAZON PAY', 'IRCTC', 'APOLLO PHARMACY', 'MERCHANT', 'PETROL BUNK', 'KIRANA STORE'])}", "UPI")


def payslip_lines(regular, bonus, deductions):
    """The payslip's lines, as the extractor reads them off a real one: earnings add up to the gross, deductions to the
    gross minus the net. Money is always a double (the MongoDB virtual schema is strict on types). No randomness, so the
    rest of the generated data is unchanged."""
    deductions = max(0, deductions)
    basic, hra = round(regular * .5), round(regular * .2)
    pf = min(round(basic * .12), deductions)
    pt = min(200, deductions - pf)
    lines = [("Basic salary", basic, "earning", True), ("House rent allowance", hra, "earning", True),
             ("Special allowance", regular - basic - hra, "earning", True)]
    if bonus:
        lines.append(("Performance bonus (one-time)", bonus, "earning", False))
    lines += [("Provident fund", pf, "deduction", True), ("Professional tax", pt, "deduction", True),
              ("Income tax (TDS)", deductions - pf - pt, "deduction", True)]
    return [{"label": l, "amount": float(a), "kind": k, "recurring": r} for l, a, k, r in lines]


def make_app(i, prof, forced=None):
    f = forced or {}
    first, last = f.get("name", (rng.choice(FIRST), rng.choice(LAST)))
    name = f"{first} {last}"
    city, pin3 = f.get("city", rng.choice(CITIES))
    cust_id = f"CIF{20431000 + i * 7:08d}"
    app_id = f.get("app_id", f"APP-26-{104000 + i * 3}")
    age = f.get("age", int(np.clip(np.random.normal(34, 8), 21, 58)))
    if not forced and rng.random() < .004:
        age = rng.choice([19, 20])
    dob = f.get("dob", AS_OF.replace(year=AS_OF.year - age) - dt.timedelta(days=rng.randint(40, 330)))
    sub = f.get("submitted", AS_OF - dt.timedelta(days=rng.randint(0, 29), minutes=0))
    sub_ts = dt.datetime.combine(sub, dt.time(rng.randint(8, 21), rng.randint(0, 59)))
    gross = f.get("gross", float(np.clip(np.random.lognormal(np.log(90000), .45), 28000, 600000)))
    gross = round(gross / 500) * 500
    net_reg = f.get("net", round(gross * rng.uniform(.74, .82) / 100) * 100)
    emp = f.get("employer", rng.choice(employers))
    emp_years = f.get("emp_years", int(prof["EMP_YEARS"]) or rng.choice([0, 1, 1, 2, 2, 3, 4]))   # Lending Club 0 = "<1 year" OR unknown
    doj = AS_OF - dt.timedelta(days=int(emp_years * 365.25 + rng.randint(30, 300)))
    term = f.get("term", 60 if prof["TERM_MONTHS"] == 60 else rng.choice([12, 24, 36, 36, 48]))
    amount = f.get("amount", int(np.clip(round(prof["LOAN_TO_INCOME"] * gross * 12 / 10000) * 10000, 50000, 4000000)))
    exist_emi = f.get("existing_emi", round(prof["DTI_BEFORE"] / 100 * gross / 100) * 100)
    acct = f.get("acct", acct_no())
    acct_open = f.get("acct_open", min(HIST_FROM - dt.timedelta(days=rng.randint(30, 3000)), doj + dt.timedelta(days=20)))
    flags = dict(f.get("flags", {}))
    if not forced:
        r = rng.random()
        if r < .025:
            flags["inflated"] = rng.uniform(1.2, 1.45)        # payslip edited upwards
        elif r < .04:
            flags["bonus"] = round(gross * rng.uniform(.2, .4) / 1000) * 1000
        if rng.random() < .02:
            flags["gaming"] = True
        if rng.random() < .015 + .04 * (prof["BUREAU_SCORE"] < 680):
            flags["bounces"] = rng.randint(2, 5)
        if rng.random() < .02:
            flags["irregular"] = True
        if rng.random() < .025:
            flags["low_conf"] = rng.choice(["net", "employer", "idNumber"])
        if rng.random() < .005:
            flags["id_mismatch"] = True
        if rng.random() < .012:
            flags["thin_file"] = True
    if rng.random() < .35 and "rent" not in flags:
        flags["rent"] = round(net_reg * rng.uniform(.12, .28) / 500) * 500
        flags["landlord"] = f"{rng.choice(FIRST).upper()} {rng.choice(LAST).upper()[:1]}"

    # ---- core banking
    custs.append([cust_id, name.upper(), dob.strftime("%d-%m-%Y"), f"00000{rng.randint(100000000, 999999999) % 100000:05d}", f.get("pan") or pan(),
                  f"BR{rng.randint(101, 188)}", acct_open, "Y"])
    accts.append([acct, cust_id, "SBA", acct_open, "A"])
    bal0 = net_reg * rng.uniform(.3, 1.5)
    tx(acct, max(HIST_FROM, acct_open), bal0, "C", "OPENING BALANCE B/F", "SYS")
    payer = f.get("payer", (emp.get("bank", "WGRB") + "0000001", emp.get("acct")))
    for (y, m) in months_between(max(HIST_FROM, acct_open), AS_OF):
        pay_d = last_working_day(y, m)
        net_m = net_reg
        if flags.get("irregular"):
            if (y, m) == (2026, 7):
                net_m = 0
            else:
                net_m = round(net_reg * rng.uniform(.65, 1.3) / 100) * 100
        if flags.get("bonus") and (y, m) == (2026, 9):
            net_m += round(flags["bonus"] * .7 / 100) * 100
        if f.get("bonus_net") and (y, m) == (2026, 9):
            net_m = f["bonus_net"]
        if pay_d <= AS_OF and net_m > 0 and pay_d >= max(HIST_FROM, acct_open):
            tx(acct, pay_d, net_m, "C", f"NEFT CR-{payer[0]}-{emp['name'].upper()[:28]}-SALARY {dt.date(y, m, 1):%b%y}".upper(),
               "NEFT", payer[1], payer[0])
            if f.get("mule"):
                tx(acct, pay_d + dt.timedelta(days=1), round(net_m * rng.uniform(.8, .9), -3), "D",
                   "CASH WDL/BRANCH/SELF", "CASH")
        if exist_emi > 0 and dt.date(y, m, 5) <= AS_OF:
            parts = [exist_emi] if exist_emi < 15000 or rng.random() < .5 else [round(exist_emi * .6), exist_emi - round(exist_emi * .6)]
            for k, p in enumerate(parts):
                lender = random.Random(cust_id + str(k)).choice(["NORTHWIND FIN", "WOODGROVE BANK", "FABRIKAM CAPITAL", "CONTOSO CARDS", "TAILSPIN CREDIT", "LITWARE BANK"])
                tx(acct, dt.date(y, m, 5 + k), p, "D", f"NACH DR/{lender}/LOAN EMI", "NACH")
        if not f.get("mule"):
            spend_month(acct, y, m, net_m or net_reg * .5, AS_OF, rng.uniform(.72, .97), flags)
    if flags.get("bounces"):
        for k in range(flags["bounces"]):
            d = AS_OF - dt.timedelta(days=rng.randint(5, 170))
            tx(acct, d, 590, "D", "NACH RTN CHG/INSUFFICIENT BALANCE", "SYS")

    # ---- what the applicant typed
    apps.append({"_id": app_id, "custId": cust_id, "submittedAt": sub_ts.isoformat(timespec="minutes"),
                 "channel": f.get("channel", rng.choice(["Mobile app", "Mobile app", "Web", "Branch"])),
                 "product": "Personal loan", "amountRequested": amount, "termMonths": term,
                 "purpose": f.get("purpose", rng.choice(PURPOSES)),
                 "applicant": {"name": name, "dob": dob.isoformat(), "mobile": custs[-1][3],
                               "email": f"{first.lower()}.{last.lower().replace(chr(39), '')}{rng.randint(1, 99)}@example.com",
                               "city": city, "pin": f"{pin3}{rng.randint(1, 99):03d}"},
                 "salaryAccount": acct, "deviceId": f.get("device", h8(app_id + "dev"))})

    # ---- what was extracted from each uploaded PDF
    bonus_g = f.get("bonus_gross", flags.get("bonus", 0))
    pay_gross = gross + bonus_g
    pay_net = f.get("payslip_net", round(net_reg * flags.get("inflated", 1)) + (round(bonus_g * .7 / 100) * 100 if bonus_g and not forced else 0))
    conf = {k: round(rng.uniform(.93, .995), 3) for k in ("employeeName", "employer", "gross", "net", "payMonth", "dateOfJoining")}
    if flags.get("low_conf") in conf:
        conf[flags["low_conf"]] = round(rng.uniform(.58, .83), 3)
    ext_ms = rng.randint(2100, 6800)
    docs.append({"_id": f"DOC-{app_id[4:]}-P", "applicationId": app_id, "docType": "PAYSLIP",
                 "fileName": f"payslip_sep2026_{last.lower().replace(chr(39), '')}.pdf", "pages": 1,
                 "uploadedAt": sub_ts.isoformat(timespec="minutes"),
                 "extraction": {"engine": "synthetic (not extracted)", "ms": ext_ms, "minConfidence": min(conf.values())},
                 "fields": {"employeeName": name, "employer": emp["name"], "employerAddress": emp["address"],
                            "payMonth": "2026-09", "dateOfJoining": doj.isoformat(), "gross": float(pay_gross),
                            "bonus": float(bonus_g), "deductions": float(pay_gross - pay_net), "net": float(pay_net)},
                 "confidence": conf, "fingerprint": {"producer": emp["tool"], "templateHash": emp["template"]},
                 "lineItems": payslip_lines(pay_gross - bonus_g, bonus_g, pay_gross - pay_net)})
    id_conf = {"name": round(rng.uniform(.95, .995), 3), "dob": round(rng.uniform(.94, .995), 3),
               "idNumber": round(rng.uniform(.93, .995), 3)}
    if flags.get("low_conf") == "idNumber":
        id_conf["idNumber"] = round(rng.uniform(.55, .8), 3)
    id_name = name if not flags.get("id_mismatch") else f"{rng.choice(FIRST)} {last}"
    docs.append({"_id": f"DOC-{app_id[4:]}-I", "applicationId": app_id, "docType": "ID_PROOF",
                 "fileName": "pan_card.pdf", "pages": 1, "uploadedAt": sub_ts.isoformat(timespec="minutes"),
                 "extraction": {"engine": "synthetic (not extracted)", "ms": rng.randint(1500, 3500), "minConfidence": min(id_conf.values())},
                 "fields": {"idType": "PAN", "name": id_name, "dob": dob.isoformat(), "idNumber": custs[-1][4]},
                 "confidence": id_conf, "fingerprint": {"producer": "scanner", "templateHash": "pan-v2"}})
    if rng.random() < .55 or forced:
        docs.append({"_id": f"DOC-{app_id[4:]}-E", "applicationId": app_id, "docType": "EMPLOYMENT_LETTER",
                     "fileName": "employment_letter.pdf", "pages": 1, "uploadedAt": sub_ts.isoformat(timespec="minutes"),
                     "extraction": {"engine": "synthetic (not extracted)", "ms": rng.randint(1800, 4200), "minConfidence": .95},
                     "fields": {"employer": emp["name"], "designation": f.get("designation", rng.choice(["Software Engineer", "Senior Analyst", "Manager", "Associate", "Team Lead", "Executive", "Consultant"])),
                                "joiningDate": doj.isoformat(), "employmentType": "Permanent"},
                     "confidence": {"employer": .97, "designation": .96, "joiningDate": .95},
                     "fingerprint": {"producer": "word-processor", "templateHash": h8(emp["name"] + "letter")}})

    # ---- bureau (mocked)
    thin = flags.get("thin_file")
    bureau.append([app_id, cust_id, sub_ts, None if thin else int(f.get("bureau", prof["BUREAU_SCORE"])),
                   0 if thin else int(f.get("inq", prof["INQ_6M"])), 0 if thin else int(f.get("pub", prof["PUB_REC"])),
                   0 if thin else (1 if exist_emi < 15000 else 2) if exist_emi > 0 else 0, int(exist_emi),
                   0 if thin else round(rng.uniform(1, 15), 1)])
    truth["planted"][app_id] = {k: v for k, v in flags.items() if k not in ("rent", "landlord")}
    return app_id


# ------------------------------------------------------------------ the hero
HERO = make_app(0, book.iloc[0], dict(
    app_id="APP-26-104871", name=("Karthik", "Raghunathan"), city=("Chennai", "600"), age=34,
    submitted=dt.date(2026, 10, 23), gross=147000, net=113000, employer=employers[0], emp_years=6,
    term=48, amount=1_200_000, existing_emi=31500, bureau=742, inq=1, purpose="Home renovation",
    bonus_gross=45000, payslip_net=148600, bonus_net=148600, dob=dt.date(1992, 3, 11), pan="BKRPR4417K", pub=0, designation="Senior Software Engineer", channel="Mobile app",
    acct="50100293844117"))
truth["hero"] = HERO

# ------------------------------------------------------------------ the ring
ring_names = [("Vikram", "Sethi"), ("Rohit", "Malhotra"), ("Sameer", "Kapoor"), ("Ajay", "Bhatia"), ("Nitin", "Arora"),
              ("Manish", "Chopra"), ("Deepak", "Khanna"), ("Sunil", "Mehra"), ("Rakesh", "Oberoi"), ("Pankaj", "Grover"),
              ("Alok", "Saxena"), ("Vivek", "Tandon"), ("Gaurav", "Ahuja"), ("Karan", "Bajaj")]
for j, nm in enumerate(ring_names):
    e = RING_EMPLOYERS[j % 4]
    net = rng.choice([140000, 145000, 150000, 160000])
    rid = make_app(1 + j, book.iloc[1 + j], dict(
        name=nm, city=rng.choice(CITIES[:4]), age=rng.randint(27, 38), submitted=dt.date(2026, 10, 8) + dt.timedelta(days=rng.randint(0, 12)),
        gross=round(net / .78 / 1000) * 1000, net=net, payslip_net=net, employer=e, emp_years=rng.choice([3, 4, 5]),
        term=rng.choice([48, 60]), amount=rng.choice([950000, 975000, 980000, 990000]), existing_emi=0,
        bureau=rng.randint(722, 781), inq=rng.choice([0, 1]), pub=0, payer=RING_PAYERS[j % 3], mule=True,
        acct_open=dt.date(2026, 2, rng.randint(2, 26)), purpose=rng.choice(["Home renovation", "Travel", "Wedding"]),
        device=["d7c1a2f0", "d7c1a2f0", "e41b9930"][j % 3], channel="Mobile app"))
    truth["ring"].append(rid)

for i in range(15, N_APPS):
    make_app(i, book.iloc[i])

# ------------------------------------------------------------------ write
(WORK / "truth.json").write_text(json.dumps(truth, indent=1, default=str))
with open(WORK / "bureau.csv", "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["APP_ID", "CUST_ID", "PULLED_AT", "BUREAU_SCORE", "INQ_6M", "PUB_REC", "ACTIVE_LOANS", "EXISTING_EMI", "OLDEST_TRADE_YEARS"])
    w.writerows(bureau)
(WORK / "applications.json").write_text(json.dumps(apps))
(WORK / "documents.json").write_text(json.dumps(docs))
print(f"applications {len(apps)}  documents {len(docs)}  customers {len(custs)}  transactions {len(txns)}")

if "--dry" in sys.argv:
    sys.exit(0)

import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402
import pymongo  # noqa: E402

VM_IP = vm_ip()
DDL = """
DROP SCHEMA IF EXISTS cbs CASCADE;
CREATE SCHEMA cbs;
CREATE TABLE cbs.cust_mst (cust_id varchar(12) PRIMARY KEY, cust_nm varchar(80), dob_txt varchar(10), mob_no varchar(10),
  pan_no varchar(10), brn_cd varchar(6), cust_since date, kyc_flg char(1));
CREATE TABLE cbs.acct_mst (acct_no varchar(16) PRIMARY KEY, cust_id varchar(12) REFERENCES cbs.cust_mst, acct_typ varchar(3),
  open_dt date, acct_stat char(1));
CREATE TABLE cbs.txn_hist (txn_id bigint PRIMARY KEY, acct_no varchar(16), txn_dt date, txn_amt numeric(14,2), dr_cr char(1),
  narr varchar(120), chnl varchar(6), cp_acct varchar(20), cp_ifsc varchar(11), bal_amt numeric(14,2));
"""
with psycopg.connect(host=VM_IP, port=port("PG_PORT"), user="cbs_admin", password=source_secret("PG_ADMIN_PASSWORD"), dbname="core_banking",
                     connect_timeout=10) as pg:
    pg.execute(DDL)
    with pg.cursor() as cur:
        with cur.copy("COPY cbs.cust_mst FROM STDIN") as cp:
            for r in custs:
                cp.write_row(r)
        with cur.copy("COPY cbs.acct_mst FROM STDIN") as cp:
            for r in accts:
                cp.write_row(r)
        txns.sort(key=lambda r: (r[1], r[2], r[4] == "D", r[0]))
        bal, last = 0.0, None
        with cur.copy("COPY cbs.txn_hist FROM STDIN") as cp:
            for r in txns:
                if r[1] != last:
                    bal, last = 0.0, r[1]
                bal += r[3] if r[4] == "C" else -r[3]
                cp.write_row(r + [round(bal, 2)])
    pg.execute("CREATE INDEX ON cbs.txn_hist (acct_no, txn_dt)")
    pg.execute("""DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cbs_reader') THEN
                  CREATE ROLE cbs_reader LOGIN; END IF; END $$""")
    # set (or reset) the read-only login's password; sql.Literal quotes it, so no value is ever pasted into SQL text
    pg.execute(sql.SQL("ALTER ROLE cbs_reader PASSWORD {}").format(sql.Literal(source_secret("PG_READER_PASSWORD"))))
    pg.execute("GRANT USAGE ON SCHEMA cbs TO cbs_reader; GRANT SELECT ON ALL TABLES IN SCHEMA cbs TO cbs_reader")
    pg.execute("ANALYZE")
print("postgres: core_banking.cbs loaded")

mc = pymongo.MongoClient(VM_IP, port("MONGO_PORT"), username="root", password=source_secret("MONGO_ROOT_PASSWORD"),
                         authSource="admin", directConnection=True, serverSelectionTimeoutMS=5000)
db = mc["lending"]
db.applications.drop(); db.documents.drop()
db.applications.insert_many(apps); db.documents.insert_many(docs)
db.documents.create_index("applicationId")
adm = mc["admin"]
if not adm.command("usersInfo", "docs_reader")["users"]:
    adm.command("createUser", "docs_reader", pwd=source_secret("MONGO_READER_PASSWORD"), roles=[{"role": "read", "db": "lending"}])
else:
    adm.command("updateUser", "docs_reader", pwd=source_secret("MONGO_READER_PASSWORD"))
print("mongodb: lending.applications + lending.documents loaded")
