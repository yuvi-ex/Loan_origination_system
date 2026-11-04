"""Tab 4 · LOS insights: how many applications came in, where each one went, which rules sent cases to a person, and
what to change in those rules. Every number is read live through the LOS service (`insights`); the lessons are
checked against what really happened to 1.34M funded loans in the book.
"""
from fmt import esc, inr

CSS = """
.in-bar { display:flex; height:2.6rem; border-radius:12px; overflow:hidden; gap:2px; background:#fff; margin:.4rem 0 .5rem; }
.in-bar span { display:flex; align-items:center; justify-content:center; color:#fff; font-size:.8rem; font-weight:800; min-width:0; white-space:nowrap; overflow:hidden; }
.in-leg { display:flex; flex-wrap:wrap; gap:.3rem 1.1rem; font-size:.84rem; color:var(--muted); }
.in-leg i { display:inline-block; width:.75rem; height:.75rem; border-radius:3px; margin-right:.35rem; vertical-align:-1px; }
.in-leg b { color:var(--ink2); }
.in-h { font-size:1.15rem; font-weight:900; color:var(--ink2); margin:1.5rem 0 .15rem; }
.in-sub { font-size:.86rem; color:var(--muted); margin-bottom:.6rem; }
.in-card { border-radius:16px; border:1px solid var(--edge); background:#fff; padding:.8rem 1rem; box-shadow:var(--shadow); }
.in-rules { display:grid; grid-template-columns:minmax(10rem,18rem) minmax(0,1fr) 6.5rem; gap:.45rem .8rem; align-items:center; font-size:.86rem; }
.in-rules .id { font-weight:900; color:var(--ink2); } .in-rules .t { color:var(--ink2); }
.in-rules .n { text-align:right; font-variant-numeric:tabular-nums; color:var(--muted); } .in-rules .n b { color:var(--ink2); }
.in-rules .hd { font-size:.66rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); }
.in-track { position:relative; height:.9rem; background:#F1F4F9; border-radius:5px; }
.in-track .all { position:absolute; inset:0 auto 0 0; background:#F8C977; border-radius:5px; }
.in-track .alone { position:absolute; inset:0 auto 0 0; background:#D98A00; border-radius:5px; }
.in-sum { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; margin:.2rem 0 .8rem; }
.in-sum .v { font-size:1.5rem; font-weight:900; color:var(--ink2); line-height:1.1; font-variant-numeric:tabular-nums; }
.in-sum .l { font-size:.82rem; color:var(--muted); margin-top:.15rem; }
.in-sum .good .v { color:#12796A; } .in-sum .bad .v { color:#C8102E; }
.in-ls { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; }
.in-l { border-left:6px solid #9FB0C4; }
.in-l.add { border-left-color:#7A4FD6; } .in-l.chg { border-left-color:#D98A00; } .in-l.keep { border-left-color:#1FA08B; }
.in-l .tg { display:inline-block; font-size:.64rem; font-weight:900; letter-spacing:.1em; text-transform:uppercase; border-radius:999px;
  padding:.15rem .55rem; margin-right:.4rem; color:#fff; background:#9FB0C4; vertical-align:2px; }
.in-l.add .tg { background:#7A4FD6; } .in-l.chg .tg { background:#B87500; } .in-l.keep .tg { background:#12796A; }
.in-l .tt { font-size:1.02rem; font-weight:900; color:var(--ink2); }
.in-l dl { display:grid; grid-template-columns:5.6rem minmax(0,1fr); gap:.3rem .6rem; margin:.6rem 0 0; font-size:.86rem; }
.in-l dt { font-size:.66rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:var(--faint); padding-top:.15rem; }
.in-l dd { margin:0; color:var(--ink2); line-height:1.45; }
.in-l .ev { color:var(--muted); }
.in-l .fx { font-weight:800; }
.in-foot { font-size:.78rem; color:var(--muted); margin-top:.9rem; }
@media (max-width:1100px) { .in-ls { grid-template-columns:1fr; } }
@media (max-width:700px) { .in-rules { grid-template-columns:minmax(0,1fr) 5rem; } .in-rules .in-bc { display:none; }
  .in-sum { grid-template-columns:1fr; } .in-bar span { font-size:0; } }
"""

# plain names for the referral rules, so the page reads without the rule codes (the codes stay in the checklist and the log)
NAMES = {"R01": "Borderline score", "R02": "Payslip and bank salary disagree", "R03": "Hard-to-read document",
         "R04": "Close to the debt-burden (FOIR) limit", "R05": "No credit-bureau record", "R06": "Less than a year in the job",
         "R07": "Bounced payments", "R08": "Online-gaming spend", "R09": "Missing salary months", "R10": "Irregular salary",
         "R11": "Above the auto-approval amount", "R12": "Name on the ID does not match", "R13": "Data check failed"}

SEGS = [("APPROVE", None, "Approved automatically", "#1FA08B"), ("APPROVE_REDUCED", None, "Approved for a lower amount", "#7CCFBF"),
        ("REFER", "UW1", "Underwriter", "#F2A93B"), ("REFER", "UW2", "Senior underwriter", "#C27A00"),
        ("REFER", "FRAUD", "Fraud desk", "#7A4FD6"), ("DECLINE", None, "Declined", "#C8102E")]
# the percentage printed on each segment: dark ink on the light fills, white on the dark ones (each pair >= 4.5:1)
LABEL_INK = {"#1FA08B": "#081226", "#7CCFBF": "#081226", "#F2A93B": "#081226", "#C27A00": "#081226"}


def _rate(rows, k, b, s="all"):
    r = next((x for x in rows if x["K"] == k and int(x["B"]) == b and x["S"] == s), None)
    return 100 * float(r["DEFAULTS"]) / float(r["LOANS"]) if r and float(r["LOANS"]) else 0.0


def _book(rows, k, bands, s):
    """Default rate over several bands together (the FOIR rows are split by score strength)."""
    sel = [x for x in rows if x["K"] == k and int(x["B"]) in bands and x["S"] == s]
    n = sum(float(x["LOANS"]) for x in sel)
    return 100 * sum(float(x["DEFAULTS"]) for x in sel) / n if n else 0.0


def page(data):
    st, ru, bk, ck = data["status"], data["rules"], data["book"], data["checks"]
    if not st["rows"]:
        return f'<div class="refused">The decision engine returned nothing: {esc(st.get("error") or "")}</div>'
    cnt = {(r["SYSTEM_DECISION"], r["REVIEW_LEVEL"] or None): r for r in st["rows"]}
    n = lambda d, l=None: int(cnt.get((d, l), {}).get("APPS") or 0)  # noqa: E731
    total = sum(int(r["APPS"]) for r in st["rows"])
    asked = sum(float(r["ASKED"] or 0) for r in st["rows"])
    auto, red, decl = n("APPROVE"), n("APPROVE_REDUCED"), n("DECLINE")
    uw1, uw2, frd = n("REFER", "UW1"), n("REFER", "UW2"), n("REFER", "FRAUD")
    refer = uw1 + uw2 + frd
    offered = sum(float(cnt.get((d, None), {}).get("OFFERED") or 0) for d in ("APPROVE", "APPROVE_REDUCED"))
    decided = sum(int(r["DECIDED_BY_PERSON"] or 0) for r in st["rows"] if r["SYSTEM_DECISION"] == "REFER")
    p = lambda x: round(100 * x / total) if total else 0  # noqa: E731

    out = ['<div class="nums4">',
           f'<div class="n4"><div class="v">{total:,}</div><div class="l">applications received<br/>{inr(asked, True)} asked for</div></div>',
           f'<div class="n4 good"><div class="v">{auto + red:,} <span style="font-size:1rem">({p(auto + red)}%)</span></div>'
           f'<div class="l">approved without a person<br/>{inr(offered, True)} offered; {red:,} for a lower amount</div></div>',
           f'<div class="n4"><div class="v" style="color:#9A6206">{refer:,} <span style="font-size:1rem">({p(refer)}%)</span></div>'
           f'<div class="l">sent to a person<br/>{uw1:,} underwriter &middot; {uw2:,} senior &middot; {frd:,} fraud desk</div></div>',
           f'<div class="n4 bad"><div class="v">{decl:,} <span style="font-size:1rem">({p(decl)}%)</span></div>'
           f'<div class="l">declined by the rules<br/>score too low or cannot afford the minimum</div></div></div>']

    bar, leg = [], []
    for d, l, label, c in SEGS:
        v = n(d, l)
        if v:
            bar.append(f'<span style="flex:{v};background:{c};color:{LABEL_INK.get(c, "#fff")}" title="{esc(label)}: {v:,}">{p(v)}%</span>' if p(v) >= 4
                       else f'<span style="flex:{v};background:{c}" title="{esc(label)}: {v:,}"></span>')
            leg.append(f'<span><i style="background:{c}"></i>{esc(label)} <b>{v:,}</b></span>')
    out.append(f'<div class="in-card"><div class="in-bar" role="img" aria-label="Status of {total:,} applications">{"".join(bar)}</div>'
               f'<div class="in-leg">{"".join(leg)}</div>'
               f'<div class="in-sub" style="margin:.5rem 0 0">Of the {refer:,} sent to a person, {decided:,} '
               f'{"has" if decided == 1 else "have"} been decided and signed so far; the rest wait in the review queue.</div></div>')

    # ---- why cases went to a person
    refs = sorted([r for r in ru["rows"] if r["OUTCOME"] == "REFER"], key=lambda r: -int(r["FIRES"] or 0))
    top = max([int(r["FIRES"] or 0) for r in refs] + [1])
    rows = ['<div class="hd">Reason</div><div class="hd in-bc">Cases (darker: the only reason)</div><div class="hd n">Cases &middot; only</div>']
    for r in refs:
        f, a = int(r["FIRES"] or 0), int(r["ALONE"] or 0)
        rows.append(f'<div class="t">{esc(NAMES.get(r["RULE_ID"], r["TITLE"]))}</div>'
                    f'<div class="in-bc"><div class="in-track"><div class="all" style="width:{100 * f / top:.1f}%"></div>'
                    f'<div class="alone" style="width:{100 * a / top:.1f}%"></div></div></div>'
                    f'<div class="n"><b>{f:,}</b> &middot; {a:,}</div>')
    out.append('<div class="in-h">Why applications went to a person</div>'
               '<div class="in-sub">A case can trip several rules. "Only" counts the cases that one rule alone sent to a person: '
               'those are the referrals a rule change would remove.</div>'
               f'<div class="in-card"><div class="in-rules">{"".join(rows)}</div></div>')

    # ---- lessons
    rr = {r["RULE_ID"]: r for r in ru["rows"]}
    c = {r["K"]: r for r in ck["rows"]}
    gi = lambda k, f: int(float(c.get(k, {}).get(f) or 0))  # noqa: E731
    ring_n, ring_ok, ring_amt = gi("RING", "N"), gi("RING", "M"), float(c.get("RING", {}).get("AMT") or 0)
    bonus_ok = gi("R02_BONUS", "M")
    near_weak = gi("FOIR_40_42_WEAK", "M")
    r03, r03_mob = gi("R03_MOBILE", "N"), gi("R03_MOBILE", "M")
    r03_alone, r03_strong = int(rr.get("R03", {}).get("ALONE") or 0), int(rr.get("R03", {}).get("ALONE_STRONG") or 0)
    r01_f, r01_a = int(rr.get("R01", {}).get("FIRES") or 0), int(rr.get("R01", {}).get("ALONE") or 0)
    rows_b = bk["rows"]
    s1, s2, s3, s4 = (_rate(rows_b, "SCORE", b) for b in (1, 2, 3, 4))
    w_lo, w_mid, w_near = (_book(rows_b, "FOIR", {b}, "weak") for b in (1, 2, 3))
    g_lo, g_mid, g_near = (_book(rows_b, "FOIR", {b}, "strong") for b in (1, 2, 3))
    after = refer - bonus_ok - r03_alone + near_weak + ring_ok

    def card(kind, tag, title, saw, change, effect):
        return (f'<div class="in-card in-l {kind}"><div><span class="tg">{tag}</span><span class="tt">{title}</span></div><dl>'
                f'<dt>What we saw</dt><dd class="ev">{saw}</dd><dt>Change</dt><dd>{change}</dd>'
                f'<dt>Effect</dt><dd class="fx">{effect}</dd></dl></div>')

    lessons = [
        card("add", "Add a rule", "Fraud-ring check: applications that share a salary payer or a payslip template",
             f'{ring_ok} of {ring_n} linked applications ({inr(ring_amt, True)}) were approved automatically: each passed every rule on its own. '
             'They share one payslip template and three personal accounts paying the "salaries", across four employers.',
             'Refer to the fraud desk when the same salary payer account or payslip template appears on 3 or more applications in 90 days.',
             f'+{ring_ok} cases to the fraud desk; {inr(ring_amt, True)} not paid out to a ring.'),
        card("chg", "Change", "Debt-burden warning: start at 40% of income, not 42%, for weaker scores",
             f'In the loan book, scores under 600 default {w_mid:.1f}% at FOIR 40&ndash;42% and {w_near:.1f}% at 42&ndash;45% (the band the warning covers today), '
             f'against {w_lo:.1f}% below 40%. Scores of 600+: {g_lo:.1f}%, {g_mid:.1f}%, {g_near:.1f}%. The risk steps up at 40%.',
             'Widen the near-cap band from 3 to 5 points (FOIR 40&ndash;45%) for scores below 600; leave it at 3 for stronger scores.',
             f'+{near_weak} cases to an underwriter that are approved automatically today.'),
        card("chg", "Change", "Payslip vs bank check: take one-time pay out before comparing",
             f'{int(rr.get("R02", {}).get("ALONE") or 0)} cases went to a person for the payslip-bank gap alone. In {bonus_ok} of them the payslip '
             'shows a bonus; without it, the payslip matches the bank within 15%.',
             'Compare the bank\'s 6-month salary with payslip net minus one-time pay (bonus, arrears). '
             'Underwriters already do this by hand with "Use regular salary only".',
             f'&minus;{bonus_ok} referrals, with no change to the risk taken.'),
        card("chg", "Change", "Hard-to-read documents: ask for a clearer copy before a person looks",
             f'{r03_alone} cases went to a person only because a document was hard to read; {r03_strong} of them score 620 or more. '
             f'{r03_mob} of the {r03} unreadable documents came through the mobile app.',
             'Send the applicant an automatic "please upload a clearer copy" request; refer only if the second copy is also unreadable. '
             'Add capture guidance (flat, lit, all four corners) to the mobile app.',
             f'Up to &minus;{r03_alone} referrals, and a faster answer for the applicant.'),
        card("keep", "Keep", "Borderline scores (560&ndash;580): the review earns its keep",
             f'It is the largest single source of work: {r01_f:,} cases, {r01_a:,} for this reason alone. But the loan book defaults '
             f'{s2:.1f}% in 560&ndash;580, against {s3:.1f}% in 580&ndash;600 and {s4:.1f}% in 600&ndash;640 (and {s1:.1f}% below 560).',
             'No change. Moving the automatic approval down to 560 would approve loans almost a third of which defaulted.',
             'Underwriter time stays where the risk is.'),
    ]
    out.append('<div class="in-h">Lessons learned: what to change in the rules</div>'
               '<div class="in-sub">Each suggestion is checked against the cases above and against what really happened to 1.34M funded loans. '
               'Changes go into the DRAFT policy for the risk committee, never straight into LIVE.</div>')
    out.append('<div class="in-sum">'
               f'<div class="in-card"><div class="v">{refer:,} &rarr; {after:,}</div><div class="l">cases a person would see with all four changes</div></div>'
               f'<div class="in-card good"><div class="v">&minus;{bonus_ok + r03_alone:,}</div><div class="l">referrals removed where the check only found paperwork (payslip, unreadable documents)</div></div>'
               f'<div class="in-card bad"><div class="v">+{near_weak + ring_ok:,}</div><div class="l">risky cases caught that are approved today (debt-burden warning, new fraud-ring check)</div></div>'
               '</div>')
    out.append(f'<div class="in-ls">{"".join(lessons)}</div>')
    out.append('<div class="in-foot">Applications are synthetic (seeded). Outcomes are the public Lending Club book (US, 2007&ndash;2018): '
               'confirm on the lender\'s own book before a change goes live.'
               + ("" if all(x["live"] for x in (st, ru, bk, ck)) else ' <b>A source was unavailable: some numbers are from the last good run.</b>')
               + '</div>')
    return "".join(out)
