"""Tab 1 · the problem statement as one picture: four documents, evidence in four systems, one engine, two outcomes.
Counts are read live (fallback: last good run). Few words on purpose; the talk track carries the rest.
"""
import how
from fmt import esc, inr  # noqa: F401

CSS = """
.ps-h { font-size:2rem; font-weight:900; letter-spacing:-.03em; color:var(--ink2); margin:.3rem 0 .2rem; line-height:1.15; }
.ps-h em { font-style:normal; color:#12796A; }
.ps-s { font-size:1.02rem; color:var(--muted); margin-bottom:1.1rem; }
.pf { display:grid; grid-template-columns:minmax(0,.85fr) 3.2rem minmax(0,1fr) 3.2rem minmax(0,.8fr) 3.2rem minmax(0,1fr); align-items:center; }
.pf-col { display:grid; gap:.55rem; }
.pf-k { font-size:.64rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; color:var(--faint); margin-bottom:.1rem; }
.pf-doc { display:flex; gap:.6rem; align-items:center; border-radius:14px; border:1px solid var(--edge); background:#fff; padding:.5rem .7rem; box-shadow:var(--shadow); }
.pf-doc svg { flex:0 0 26px; } .pf-doc b { font-size:.92rem; color:var(--ink2); }
.pf-sys { border-radius:14px; border:1px solid var(--edge); background:#fff; padding:.55rem .8rem; border-left:6px solid #9FB0C4; box-shadow:var(--shadow); }
.pf-sys.mg { border-left-color:#0076AD; } .pf-sys.pg { border-left-color:#C56A00; } .pf-sys.bu { border-left-color:#8B5CF6; } .pf-sys.ex { border-left-color:#12796A; }
.pf-sys .t { font-weight:900; color:var(--ink2); font-size:.98rem; } .pf-sys .d { font-size:.8rem; color:var(--muted); }
.pf-arr svg { width:100%; height:16rem; }
.pf-exa { border-radius:22px; background:linear-gradient(160deg,#081226 0%,#12796A 100%); color:#fff; padding:1.3rem 1rem; text-align:center; box-shadow:var(--shadow); }
.pf-exa .t { font-size:1.55rem; font-weight:900; } .pf-exa .d { font-size:.84rem; opacity:.9; margin-top:.4rem; line-height:1.45; }
.pf-exa .c { display:inline-block; margin-top:.7rem; font-size:.7rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase;
  background:rgba(255,255,255,.14); border-radius:999px; padding:.25rem .7rem; }
.pf-out { border-radius:16px; padding:.8rem 1rem; border:1px solid var(--edge); background:#fff; box-shadow:var(--shadow); }
.pf-out .v { font-size:1.9rem; font-weight:900; line-height:1.05; font-variant-numeric:tabular-nums; }
.pf-out .l { font-size:.86rem; color:var(--ink2); font-weight:700; margin-top:.15rem; } .pf-out .s { font-size:.78rem; color:var(--muted); }
.pf-out.auto { border-left:6px solid #1FA08B; } .pf-out.auto .v { color:#12796A; }
.pf-out.hitl { border-left:6px solid #F59E0B; background:#FFFBF2; } .pf-out.hitl .v { color:#9A6206; }
.pf-out.dec { border-left:6px solid #C8102E; } .pf-out.dec .v { color:#C8102E; font-size:1.3rem; }
.today { display:flex; align-items:center; gap:.8rem; margin:1rem 0 .2rem; border-radius:14px; background:#FFF7F8; border:1px solid #F3C2C8; padding:.55rem .9rem; color:#912018; font-size:.92rem; }
.today b { font-weight:900; } .today .x { font-size:1.4rem; font-weight:900; }
.nums4 { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.7rem; margin:1rem 0 .3rem; }
.n4 { border-radius:16px; border:1px solid var(--edge); background:#fff; padding:.75rem .95rem; }
.n4 .v { font-size:1.6rem; font-weight:900; color:var(--ink2); line-height:1.1; } .n4 .l { font-size:.84rem; color:var(--muted); margin-top:.2rem; line-height:1.35; }
.n4.bad .v { color:#C8102E; } .n4.good .v { color:#12796A; }
.n4 .go { display:inline-block; margin-top:.35rem; font-size:.66rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:var(--teal-ink); }
.k4s { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.7rem; margin-top:.8rem; }
.k4 { display:flex; gap:.7rem; align-items:center; border-radius:16px; border:1px solid var(--edge); background:#fff; padding:.6rem .85rem; }
.k4 svg { flex:0 0 32px; width:32px; height:32px; } .k4 .v { font-size:1.35rem; font-weight:900; color:var(--ink2); line-height:1.1; }
.k4.good .v { color:#12796A; } .k4.bad .v { color:#C8102E; } .k4 .l { font-size:.8rem; color:var(--muted); }
.k4 .go { font-size:.62rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:var(--teal-ink); margin-top:.15rem; }
@media (max-width:1000px) { .k4s { grid-template-columns:1fr 1fr; } }
@media (max-width:1250px) { .pf { grid-template-columns:1fr; gap:.6rem; } .pf-arr svg { height:2.4rem; transform:rotate(90deg); } .nums4 { grid-template-columns:1fr 1fr; } }
"""

_DOC = ('<svg width="26" height="30" viewBox="0 0 26 30"><path d="M3 1h14l7 7v20a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1z" fill="#F1F4F9" stroke="#9FB0C4" stroke-width="1.5"/>'
        '<path d="M17 1v7h7" fill="none" stroke="#9FB0C4" stroke-width="1.5"/><path d="M6 14h13M6 18h13M6 22h9" stroke="{c}" stroke-width="2" stroke-linecap="round"/></svg>')
_IN = ('<svg viewBox="0 0 50 240" preserveAspectRatio="none"><g fill="none" stroke="#1FA08B" stroke-width="3" stroke-dasharray="7 5">'
       '<path d="M0 30 C25 30 25 120 50 120"/><path d="M0 90 C25 90 25 120 50 120"/><path d="M0 150 C25 150 25 120 50 120"/>'
       '<path d="M0 210 C25 210 25 120 50 120"/></g></svg>')
_FAN = ('<svg viewBox="0 0 50 240" preserveAspectRatio="none"><g fill="none" stroke="#1FA08B" stroke-width="3">'
        '<path d="M0 120 C25 120 25 45 50 45"/><path d="M0 120 C25 120 25 140 50 140"/><path d="M0 120 C25 120 25 215 50 215"/></g></svg>')
_SAME = ('<svg viewBox="0 0 50 240" preserveAspectRatio="none"><g fill="none" stroke="#9FB0C4" stroke-width="3" stroke-dasharray="4 6">'
         '<path d="M0 30 L50 30"/><path d="M0 90 L50 90"/><path d="M0 150 L50 150"/><path d="M0 210 L50 210"/></g></svg>')


def _t(x, y, txt, size=12, weight=600, color="#0B1B34", anchor="middle", opacity=None):
    o = f' opacity="{opacity}"' if opacity else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{color}"{o}>{txt}</text>'


def _picture(auto_pct, refer_pct, decl_pct, auto, refer, decl):
    """Today (one officer, four systems, by hand) vs with Exasol (four PDFs -> one engine over the four systems -> three ways out)."""
    I = how._i
    out = ['<svg viewBox="0 0 1240 400" role="img" aria-label="Today versus with Exasol">',
           '<defs><marker id="ov-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto">'
           '<path d="M0 0 L10 5 L0 10 z" fill="#9FB0C4"/></marker></defs>']
    # ---- today
    out.append('<rect x="10" y="10" width="430" height="380" rx="24" fill="#FFF7F8" stroke="#F3C2C8"/>')
    out.append(_t(30, 42, "TODAY", 13, 900, "#B00D27", "start"))
    tiles = [(40, 70, "#0076AD", how.I_DB, "Documents"), (290, 70, "#C56A00", how.I_BANK, "Core banking"),
             (40, 290, "#7A4FD6", how.I_CHART, "Credit report"), (290, 290, "#12796A", how.I_GAUGE, "LOS system")]
    curves = ["M194 198 C170 190 190 110 165 95", "M266 198 C290 190 270 110 290 95",
              "M194 214 C170 222 190 300 165 315", "M266 214 C290 222 270 300 290 315"]
    for (x, y, c, ic, t), d in zip(tiles, curves):
        out.append(f'<path d="{d}" fill="none" stroke="#C8102E" stroke-width="2" stroke-dasharray="5 5" opacity=".7"/>')
        out.append(f'<rect x="{x}" y="{y}" width="125" height="50" rx="12" fill="{c}"/>' + I(ic, x + 10, y + 13, 1.0, "#fff", 2.2)
                   + _t(x + 40, y + 30, t, 12.5, 800, "#fff", "start"))
    out.append('<circle cx="230" cy="206" r="36" fill="#fff" stroke="#C8102E" stroke-width="2.5"/>' + I(how.I_USER, 212, 188, 1.5, "#B00D27", 1.8))
    out.append(_t(230, 262, "2&ndash;5 days", 17, 900, "#B00D27") + _t(230, 280, "per application", 12, 600, "#8E0A20"))
    out.append(_t(225, 376, "a credit officer opens each system by hand, one file at a time", 12, 600, "#8E0A20"))
    # ---- the turn: the customer's documents arrive, then Exasol
    out.append('<line x1="450" y1="206" x2="478" y2="206" stroke="#9FB0C4" stroke-width="4" marker-end="url(#ov-ah)"/>')
    for k, c in enumerate(["#0E2A47", "#C56A00", "#7A4FD6", "#0076AD"]):
        dx, dy = k * 10, k * 8
        out.append(f'<rect x="{492 + dx}" y="{168 + dy}" width="48" height="62" rx="7" fill="#fff" stroke="{c}" stroke-width="2.3"/>'
                   f'<path d="M{500 + dx} {186 + dy}h31M{500 + dx} {196 + dy}h31M{500 + dx} {206 + dy}h18" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>')
    out.append(_t(538, 280, "Customer", 13, 900) + _t(538, 296, "documents", 13, 900))
    out.append('<line x1="588" y1="210" x2="642" y2="210" stroke="#9FB0C4" stroke-width="3" marker-end="url(#ov-ah)"/>')
    # ---- with Exasol
    out.append('<rect x="650" y="10" width="580" height="380" rx="24" fill="#F2FBF8" stroke="#CDEBE4"/>')
    out.append(_t(670, 42, "WITH EXASOL", 13, 900, "#12796A", "start"))
    for k, (c, ic, t) in enumerate([("#0076AD", how.I_DB, "Application"), ("#C56A00", how.I_BANK, "Banking"),
                                    ("#7A4FD6", how.I_CHART, "Credit API"), ("#12796A", how.I_GAUGE, "LOS system")]):
        x = 680 + k * 65
        out.append(f'<rect x="{x}" y="58" width="60" height="44" rx="11" fill="{c}"/>' + I(ic, x + 18, 64, 1.0, "#fff", 2.2)
                   + _t(x + 30, 97, t, 9.5, 800, "#fff"))
        out.append(f'<line x1="{x + 30}" y1="104" x2="{x + 30}" y2="136" stroke="{c}" stroke-width="2.5" stroke-dasharray="4 4"/>')
    out.append(_t(942, 76, "read in place,", 11.5, 700, "#12796A", "start") + _t(942, 91, "nothing copied", 11.5, 700, "#12796A", "start")
               + _t(942, 109, "account holders: transactions", 10.5, 700, "#C56A00", "start") + _t(942, 123, "others: credit report", 10.5, 700, "#7A4FD6", "start"))
    out.append('<rect x="672" y="138" width="270" height="150" rx="24" fill="#0B3B4A"/><rect x="672" y="138" width="270" height="150" rx="24" fill="#12796A" opacity=".55"/>')
    out.append(_t(807, 172, "Exasol", 26, 900, "#fff") + _t(807, 196, "federates each system where it is,", 12, 500, "#fff")
               + _t(807, 213, "verifies and scores through semantic views:", 12, 500, "#fff") + _t(807, 230, "one certified policy for every decision", 12, 500, "#fff"))
    out.append('<rect x="709" y="248" width="196" height="24" rx="12" fill="rgba(255,255,255,.16)"/>'
               + _t(807, 264, "FEDERATED &middot; SEMANTIC VIEWS", 10.5, 800, "#fff"))
    rows = [(160, "#1FA08B", how.I_OK, f"{auto_pct}%", f"automatic &middot; {auto:,}"),
            (225, "#D98A00", how.I_USER, f"{refer_pct}%", f"human in the loop &middot; {refer:,}"),
            (290, "#C8102E", how.I_NO, f"{decl_pct}%", f"declined &middot; {decl:,}")]
    for y, c, ic, v, l in rows:
        out.append(f'<path d="M944 213 C970 213 970 {y} 995 {y}" fill="none" stroke="{c}" stroke-width="2.5"/>')
        out.append(I(ic, 1000, y - 15, 1.25, c, 2.2) + _t(1036, y + 4, v, 22, 900, c, "start") + _t(1036, y + 20, l, 10.5, 600, "#5B6B80", "start"))
    out.append(_t(940, 340, "about 15 seconds from upload to a priced decision", 14, 800, "#12796A")
               + _t(940, 360, "people see only the cases that need judgement", 12, 500, "#5B6B80"))
    out.append('</svg>')
    return "".join(out)


def problem(pipe):
    """pipe: Q_PIPELINE result (applications per system decision)."""
    by = {r["SYSTEM_DECISION"]: int(r["APPS"]) for r in pipe["rows"]}
    total = sum(by.values()) or 1
    auto = by.get("APPROVE", 0) + by.get("APPROVE_REDUCED", 0)
    refer, decl = by.get("REFER", 0), by.get("DECLINE", 0)
    pct = lambda n: round(100 * n / total)  # noqa: E731
    return f'''<div class="ov-band" style="margin-top:.4rem"><div class="ov-k">The problem</div>
<div class="ps-h">The proof for a loan sits in four systems. <em>Exasol checks them all, live.</em></div></div>
<div class="hw-pic">{_picture(pct(auto), pct(refer), pct(decl), auto, refer, decl)}</div>'''
