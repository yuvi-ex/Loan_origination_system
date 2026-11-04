"""Render the PDFs the demo shows: the hero's three uploads and two payslips from the ring (same template, two "employers").

Every page is stamped SYNTHETIC: no real person, employer or identity document is depicted.
Writes data/docs/<APP_ID>/*.pdf and the upload packs data/packs/<name>/*.pdf (application form + 3 documents)
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "docs"
W, H = A4


def inr(v):
    s = f"{int(round(v)):d}"
    head, tail = s[:-3], s[-3:]
    while len(head) > 2:
        tail = head[-2:] + "," + tail
        head = head[:-2]
    return (head + "," + tail if head else tail)


def stamp(c):
    """SYNTHETIC marking in a band at the top and bottom edge, never across figures (a diagonal watermark over the
    totals line made Textract read total deductions as net pay)."""
    w, h = c._pagesize
    c.saveState()
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.HexColor("#C8102E"))
    c.drawCentredString(w / 2, h - 12, "SYNTHETIC DOCUMENT · DEMO ONLY · NOT A REAL PERSON OR EMPLOYER")
    c.drawCentredString(w / 2, 6, "SYNTHETIC DOCUMENT · DEMO ONLY")
    c.restoreState()


def payslip(path, emp, person, month, earnings, deductions, style="corporate", producer="PayrollOne 4.2"):
    c = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    c.setTitle(f"Payslip {month}")
    c.setAuthor(emp["name"])
    c.setProducer(producer)
    if style == "corporate":
        c.setFillColor(colors.HexColor("#0B3D6B"))
        c.rect(0, H - 90, W, 90, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(40, H - 45, emp["name"])
        c.setFont("Helvetica", 9)
        c.drawString(40, H - 62, emp["address"])
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(W - 40, H - 45, f"Payslip for {month}")
        y = H - 125
        ink = colors.HexColor("#0B3D6B")
    else:   # the ring's template: a generic online payslip maker
        c.setStrokeColor(colors.HexColor("#999999"))
        c.rect(30, H - 110, W - 60, 80, fill=0)
        c.setFont("Times-Bold", 16)
        c.drawCentredString(W / 2, H - 58, emp["name"].upper())
        c.setFont("Times-Roman", 9)
        c.drawCentredString(W / 2, H - 74, emp["address"])
        c.setFont("Times-Bold", 11)
        c.drawCentredString(W / 2, H - 96, f"SALARY SLIP - {month.upper()}")
        y = H - 140
        ink = colors.black
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9.5)
    rows = [("Employee name", person["name"]), ("Employee ID", person["emp_id"]), ("Designation", person["designation"]),
            ("Date of joining", person["doj"]), ("PAN", person["pan"]), ("Bank account", person["acct_masked"])]
    for i, (k, v) in enumerate(rows):
        x = 40 if i % 2 == 0 else W / 2 + 10
        if i % 2 == 0 and i:
            y -= 18
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(x, y, k)
        c.setFillColor(colors.black)
        c.drawString(x + 105, y, str(v))
    y -= 36
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(40, y, "Earnings")
    c.drawRightString(W / 2 - 20, y, "Amount (INR)")
    c.drawString(W / 2 + 10, y, "Deductions")
    c.drawRightString(W - 40, y, "Amount (INR)")
    c.line(40, y - 5, W - 40, y - 5)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    yy = y - 22
    for i in range(max(len(earnings), len(deductions))):
        if i < len(earnings):
            c.drawString(40, yy, earnings[i][0])
            c.drawRightString(W / 2 - 20, yy, inr(earnings[i][1]))
        if i < len(deductions):
            c.drawString(W / 2 + 10, yy, deductions[i][0])
            c.drawRightString(W - 40, yy, inr(deductions[i][1]))
        yy -= 18
    g, d = sum(v for _, v in earnings), sum(v for _, v in deductions)
    c.line(40, yy + 8, W - 40, yy + 8)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(40, yy - 8, "Gross earnings")
    c.drawRightString(W / 2 - 20, yy - 8, inr(g))
    c.drawString(W / 2 + 10, yy - 8, "Total deductions")
    c.drawRightString(W - 40, yy - 8, inr(d))
    c.setFillColor(colors.HexColor("#EEF4FA") if style == "corporate" else colors.HexColor("#F2F2F2"))
    c.rect(40, yy - 52, W - 80, 30, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(52, yy - 42, "NET PAY")
    c.drawRightString(W - 52, yy - 42, f"INR {inr(g - d)}")
    c.setFont("Helvetica-Oblique", 8.5)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(40, 60, "This is a computer-generated payslip and does not require a signature.")
    stamp(c)
    c.save()


def id_doc(path, person):
    c = canvas.Canvas(str(path), pagesize=(340, 215), invariant=1)
    c.setProducer("scanner")
    c.setFillColor(colors.HexColor("#F3F6F9"))
    c.roundRect(5, 5, 330, 205, 12, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#1F3A5F"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20, 185, "IDENTITY DOCUMENT (SAMPLE)")
    c.setFont("Helvetica", 7)
    c.drawString(20, 174, "Synthetic card for a software demo - not a government document")
    c.setFillColor(colors.HexColor("#CCD6E0"))
    c.rect(20, 60, 70, 90, fill=1, stroke=0)
    c.setFillColor(colors.black)
    for i, (k, v) in enumerate([("Name", person["name"]), ("Date of birth", person["dob"]), ("ID number (PAN)", person["pan"])]):
        c.setFont("Helvetica", 7)
        c.drawString(105, 140 - i * 32, k)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(105, 127 - i * 32, v)
    stamp(c)
    c.save()


def letter(path, emp, person):
    c = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    c.setProducer("word-processor")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, H - 70, emp["name"])
    c.setFont("Helvetica", 9)
    c.drawString(50, H - 86, emp["address"])
    c.setFont("Helvetica", 11)
    y = H - 140
    for line in ["Date: 20 October 2026", "", "TO WHOMSOEVER IT MAY CONCERN", "",
                 f"This is to certify that {person['name']} (Employee ID {person['emp_id']}) has been employed with",
                 f"{emp['name']} as {person['designation']} since {person['doj_long']}, on a permanent basis.",
                 "", "This letter is issued at the request of the employee for the purpose of a loan application.",
                 "", "", "For " + emp["name"], "", "Authorised signatory, Human Resources"]:
        c.drawString(50, y, line)
        y -= 18
    stamp(c)
    c.save()


def application_form(path, a):
    """The loan application itself, as the branch or the app would print it: labelled boxes, one value each."""
    c = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    c.setTitle("Personal loan application")
    c.setProducer("Demo Finance onboarding 2.3")
    c.setFillColor(colors.HexColor("#0E2A47"))
    c.rect(0, H - 80, W, 80, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(40, H - 42, "Demo Finance")
    c.setFont("Helvetica", 11)
    c.drawString(40, H - 60, "PERSONAL LOAN APPLICATION FORM")
    c.setFont("Helvetica", 9)
    c.drawRightString(W - 40, H - 42, f"Submitted {a['date']}")
    c.drawRightString(W - 40, H - 58, f"Channel: {a['channel']}")
    y = H - 115

    def section(title):
        nonlocal y
        c.setFillColor(colors.HexColor("#0E2A47"))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, title)
        c.setStrokeColor(colors.HexColor("#0E2A47"))
        c.line(40, y - 4, W - 40, y - 4)
        y -= 26

    def box(label, value, x, w):
        c.setFillColor(colors.HexColor("#555555"))
        c.setFont("Helvetica", 8.5)
        c.drawString(x, y + 12, label)
        c.setStrokeColor(colors.HexColor("#9AA8B8"))
        c.rect(x, y - 8, w, 18, fill=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10.5)
        c.drawString(x + 5, y - 3, str(value))

    half = (W - 80 - 16) / 2
    section("1. Applicant")
    for row in [(("Full name", a["name"]), ("Date of birth", a["dob"])), (("PAN", a["pan"]), ("Mobile number", a["mobile"])),
                (("Email", a["email"]), ("City and PIN code", f"{a['city']} {a['pin']}"))]:
        box(row[0][0], row[0][1], 40, half)
        box(row[1][0], row[1][1], 40 + half + 16, half)
        y -= 40
    y -= 6
    section("2. Employment and bank")
    for row in [(("Employer", a["employer"]), ("Employment type", "Salaried, permanent")),
                (("Salary account number", a["account"]), ("Monthly take-home pay (declared)", f"INR {inr(a['declared_net'])}"))]:
        box(row[0][0], row[0][1], 40, half)
        box(row[1][0], row[1][1], 40 + half + 16, half)
        y -= 40
    y -= 6
    section("3. Loan requested")
    box("Loan amount requested (INR)", inr(a["amount"]), 40, half)
    box("Tenure (months)", a["term"], 40 + half + 16, half)
    y -= 40
    box("Purpose of the loan", a["purpose"], 40, W - 80)
    y -= 46
    section("4. Documents enclosed")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    for d in ("Latest payslip", "PAN card", "Employment letter"):
        c.drawString(48, y, f"[x]  {d}")
        y -= 16
    y -= 14
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.HexColor("#444444"))
    c.drawString(40, y, "I authorise Demo Finance to obtain my credit report and to verify my salary credits with my bank.")
    c.drawString(40, y - 14, f"Signed electronically by {a['name']} (OTP verified)")
    stamp(c)
    c.save()


PACKS = {
    "karthik-raghunathan": dict(
        form=dict(name="Karthik Raghunathan", dob="11-03-1992", pan="BKRPR4417K", mobile="0000017517",
                  email="karthik.raghunathan@example.com", city="Chennai", pin="600097", employer="Brightline Systems Pvt Ltd",
                  account="50100293844117", declared_net=148600, amount=1200000, term=48, purpose="Home renovation",
                  date="27-10-2026", channel="Mobile app"),
        emp={"name": "Brightline Systems Pvt Ltd", "address": "114, IT Expressway, Sholinganallur, Chennai 600119"},
        person={"name": "Karthik Raghunathan", "emp_id": "BLS-20417", "designation": "Senior Software Engineer",
                "doj": "15-06-2020", "doj_long": "15 June 2020", "pan": "BKRPR4417K", "acct_masked": "XXXXXXXX4117", "dob": "11-03-1992"},
        earnings=[("Basic salary", 75000), ("House rent allowance", 30000), ("Special allowance", 42000),
                  ("Performance bonus (one-time)", 45000)],
        deductions=[("Provident fund", 9000), ("Professional tax", 200), ("Income tax (TDS)", 34200)]),
    "divya-ramesh": dict(
        form=dict(name="Divya Ramesh", dob="19-08-1995", pan="CDRPR8821M", mobile="0000012736",
                  email="divya.ramesh@example.com", city="Bengaluru", pin="560034", employer="Northwind Analytics Pvt Ltd",
                  account="50100417730962", declared_net=88000, amount=500000, term=36, purpose="Higher education",
                  date="27-10-2026", channel="Branch"),
        emp={"name": "Northwind Analytics Pvt Ltd", "address": "Block C, Northwind Tech Park, Outer Ring Road, Bengaluru 560103"},
        person={"name": "Divya Ramesh", "emp_id": "NWA-08812", "designation": "Data Analyst",
                "doj": "01-07-2021", "doj_long": "1 July 2021", "pan": "CDRPR8821M", "acct_masked": "XXXXXXXX0962", "dob": "19-08-1995"},
        earnings=[("Basic salary", 55000), ("House rent allowance", 22000), ("Special allowance", 33000)],
        deductions=[("Provident fund", 6600), ("Professional tax", 200), ("Income tax (TDS)", 15200)]),
    # NOT a customer of the bank: her salary account is with another bank, so core banking has nothing on her
    "ananya-krishnan": dict(
        form=dict(name="Ananya Krishnan", dob="04-12-1993", pan="ANKPK6634R", mobile="0000043175",
                  email="ananya.krishnan@example.com", city="Pune", pin="411057", employer="Lakeview Pharma Pvt Ltd",
                  account="50200718843301", declared_net=100000, amount=600000, term=36, purpose="Wedding",
                  date="27-10-2026", channel="Website"),
        emp={"name": "Lakeview Pharma Pvt Ltd", "address": "Plot 9, Lakeview Business Park, Hinjewadi, Pune 411057"},
        person={"name": "Ananya Krishnan", "emp_id": "LVP-11307", "designation": "Regulatory Affairs Manager",
                "doj": "02-01-2020", "doj_long": "2 January 2020", "pan": "ANKPK6634R", "acct_masked": "XXXXXXXX3301", "dob": "04-12-1993"},
        earnings=[("Basic salary", 60000), ("House rent allowance", 24000), ("Special allowance", 36000)],
        deductions=[("Provident fund", 7200), ("Professional tax", 200), ("Income tax (TDS)", 12600)]),
}


def packs():
    """What an applicant uploads: the application form and three supporting documents (data/packs/<name>/)."""
    for name, p in PACKS.items():
        d = ROOT / "data" / "packs" / name
        d.mkdir(parents=True, exist_ok=True)
        last = p["person"]["name"].split()[-1].lower()
        application_form(d / "1_loan_application_form.pdf", p["form"])
        payslip(d / f"2_payslip_sep2026_{last}.pdf", p["emp"], p["person"], "September 2026", p["earnings"], p["deductions"])
        id_doc(d / "3_pan_card.pdf", p["person"])
        letter(d / "4_employment_letter.pdf", p["emp"], p["person"])
        print("pack", d.relative_to(ROOT), sorted(f.name for f in d.glob("*.pdf")))


def main():
    hero_dir = OUT / "APP-26-104871"
    hero_dir.mkdir(parents=True, exist_ok=True)
    emp = {"name": "Brightline Systems Pvt Ltd", "address": "114, IT Expressway, Sholinganallur, Chennai 600119"}
    karthik = {"name": "Karthik Raghunathan", "emp_id": "BLS-20417", "designation": "Senior Software Engineer",
               "doj": "15-06-2020", "doj_long": "15 June 2020", "pan": "BKRPR4417K", "acct_masked": "XXXXXXXX4117",
               "dob": "11-03-1992"}
    payslip(hero_dir / "payslip_sep2026_raghunathan.pdf", emp, karthik, "September 2026",
            [("Basic salary", 75000), ("House rent allowance", 30000), ("Special allowance", 42000),
             ("Performance bonus (one-time)", 45000)],
            [("Provident fund", 9000), ("Professional tax", 200), ("Income tax (TDS)", 34200)])
    id_doc(hero_dir / "pan_card.pdf", karthik)
    letter(hero_dir / "employment_letter.pdf", emp, karthik)

    # two ring payslips: different employers, same template and producer
    for app, e, p, net in [
        ("APP-26-104003", {"name": "Apex Novatech Solutions", "address": "Unit 7, 3rd Floor, Velachery Main Road, Chennai 600042"},
         {"name": "Vikram Sethi", "emp_id": "E1043", "designation": "Analyst", "doj": "01-04-2022", "pan": "AVSPS5521Q", "acct_masked": "XXXXXXXX2208"}, 145000),
        ("APP-26-104018", {"name": "Zenlore Infotech Pvt Ltd", "address": "Plot 22, Phase 2, Electronic City, Bengaluru 560100"},
         {"name": "Manish Chopra", "emp_id": "E1043", "designation": "Analyst", "doj": "01-04-2022", "pan": "BMCPC7710L", "acct_masked": "XXXXXXXX9031"}, 150000)]:
        d = OUT / app
        d.mkdir(parents=True, exist_ok=True)
        gross = round(net / .78 / 1000) * 1000
        payslip(d / "payslip_sep2026.pdf", e, p, "September 2026",
                [("Basic", round(gross * .5)), ("HRA", round(gross * .2)), ("Other allowances", gross - round(gross * .5) - round(gross * .2))],
                [("PF", 1800), ("PT", 200), ("TDS", gross - net - 2000)], style="maker", producer="Online Payslip Maker 3.2")
    print("rendered", sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*.pdf")))
    packs()


if __name__ == "__main__":
    main()
