"""Tab 'How it works': the whole system as ONE picture, few words (user: "too clumsy, too much info, need pictorial").
Left to right: four PDFs are uploaded (1), a reader turns them into data (2), Exasol checks every claim against the
systems where the data already lives, without copying them (3), the bank's policy decides (4), the answer goes one of
three ways, and every step lands in a log nobody can change (5). Static on purpose: the next tab does it live.
"""

CSS = """
.hw-h { font-size:1.9rem; font-weight:900; letter-spacing:-.03em; color:var(--ink2); margin:.3rem 0 .1rem; line-height:1.15; }
.hw-h em { font-style:normal; color:#12796A; }
.hw-pic { margin-top:.6rem; border-radius:24px; border:1px solid var(--edge); background:#fff; box-shadow:var(--shadow); padding:.6rem .8rem; overflow-x:auto; }
.hw-pic svg { display:block; width:100%; min-width:900px; height:auto; }
.hw-pic text { font-family:inherit; }
.hw3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; margin-top:.8rem; }
.hw3 > div { display:flex; align-items:center; gap:.7rem; border-radius:16px; background:#F2FBF8; border:1px solid #CDEBE4; padding:.6rem .9rem; }
.hw3 svg { flex:0 0 34px; width:34px; height:34px; } .hw3 b { font-size:1.05rem; color:var(--ink2); display:block; } .hw3 span { font-size:.82rem; color:var(--muted); }
@media (max-width:900px) { .hw3 { grid-template-columns:1fr; } }
"""

# 24x24 line icons, drawn into the picture with a translate + scale
I_DOC = '<path d="M6 2h9l4 4v15a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"/><path d="M14 2v5h5M8 12h8M8 16h8M8 8h3"/>'
I_EYE = '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'
I_DB = '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>'
I_BANK = '<path d="M3 10l9-6 9 6"/><path d="M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 21h18"/>'
I_CHART = '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>'
I_GAUGE = '<path d="M4 18a8 8 0 1 1 16 0"/><path d="M12 18l4-6"/><circle cx="12" cy="18" r="1.2"/>'
I_OK = '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>'
I_USER = '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>'
I_NO = '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>'
I_LOCK = '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>'
I_COPY = '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M4 16V5a1 1 0 0 1 1-1h11"/><path d="M3 3l18 18"/>'
I_CLOCK = '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'
I_BOT = '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4M9 13h.01M15 13h.01M8 20v2M16 20v2"/>'
I_WHY = '<path d="M9 11l3 3 8-8"/><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"/>'


def _i(path, x, y, s=2.0, color="#0B1B34", sw=1.7):
    return (f'<g transform="translate({x},{y}) scale({s})" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round">{path}</g>')


def _num(n, x, y):
    return f'<circle cx="{x}" cy="{y}" r="15" fill="#0B1B34"/><text x="{x}" y="{y + 5}" text-anchor="middle" font-size="15" font-weight="900" fill="#fff">{n}</text>'


def _label(x, y, big, small, color="#0B1B34", anchor="middle"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="17" font-weight="800" fill="{color}">{big}</text>'
            f'<text x="{x}" y="{y + 20}" text-anchor="{anchor}" font-size="13" fill="#5B6B80">{small}</text>')


def _svg_icon(path, color="#12796A"):
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round">{path}</svg>')


def picture():
    W, H = 1240, 470
    arrow = '<path d="M0 0 L10 5 L0 10 z" fill="#9FB0C4"/>'
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="How a loan application flows through the system">',
           f'<defs><marker id="hw-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto">{arrow}</marker></defs>']
    # 1 the four PDFs, fanned
    for k, (dx, dy, c) in enumerate([(0, 0, "#0E2A47"), (14, 10, "#C56A00"), (28, 20, "#7A4FD6"), (42, 30, "#0076AD")]):
        out.append(f'<rect x="{40 + dx}" y="{205 + dy}" width="62" height="80" rx="8" fill="#fff" stroke="{c}" stroke-width="2.5"/>'
                   f'<path d="M{50 + dx} {228 + dy}h40M{50 + dx} {240 + dy}h40M{50 + dx} {252 + dy}h26" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>')
    out.append(_num(1, 45, 190) + _label(97, 362, "Customer documents", "form · payslip · PAN · letter"))
    # 2 the reader
    out.append('<line x1="160" y1="250" x2="228" y2="250" stroke="#9FB0C4" stroke-width="3" marker-end="url(#hw-ah)"/>')
    out.append('<circle cx="285" cy="250" r="52" fill="#FFF3E3" stroke="#B8641A" stroke-width="2.5"/>' + _i(I_EYE, 261, 226, 2.0, "#B8641A"))
    out.append(_num(2, 245, 192) + _label(285, 335, "Data extraction", "Amazon Textract"))
    # where the data lives: three cabinets on top, read in place by the hub
    srcs = [(470, "#0076AD", I_DB, "User application", "MongoDB"), (620, "#C56A00", I_BANK, "Core banking", "Postgres"),
            (770, "#7A4FD6", I_CHART, "Credit report", "API call · PDF")]
    for x, c, ic, t, s in srcs:
        out.append(f'<rect x="{x - 62}" y="18" width="124" height="96" rx="18" fill="{c}"/>' + _i(ic, x - 18, 30, 1.5, "#fff", 2))
        out.append(f'<text x="{x}" y="88" text-anchor="middle" font-size="15" font-weight="800" fill="#fff">{t}</text>'
                   f'<text x="{x}" y="104" text-anchor="middle" font-size="11.5" fill="#fff" opacity=".85">{s}</text>')
        out.append(f'<line x1="{x}" y1="116" x2="{620 + (x - 620) * .35}" y2="150" stroke="{c}" stroke-width="3" stroke-dasharray="6 6"/>')
    out.append('<text x="900" y="72" font-size="13" font-weight="700" fill="#12796A">stays where it is,</text>'
               '<text x="900" y="90" font-size="13" font-weight="700" fill="#12796A">read in place</text>'
               '<text x="900" y="122" font-size="11.5" font-weight="700" fill="#C56A00">account holders: their bank transactions</text>'
               '<text x="900" y="139" font-size="11.5" font-weight="700" fill="#7A4FD6">others: documents + credit report</text>')
    # 3 the hub: what happens inside Exasol, top to bottom
    out.append('<line x1="340" y1="250" x2="448" y2="250" stroke="#9FB0C4" stroke-width="3" marker-end="url(#hw-ah)"/>')
    out.append('<rect x="455" y="150" width="330" height="232" rx="28" fill="#0B3B4A"/>'
               '<rect x="455" y="150" width="330" height="232" rx="28" fill="#12796A" opacity=".55"/>')
    out.append('<text x="620" y="186" text-anchor="middle" font-size="26" font-weight="900" fill="#fff">Exasol</text>')
    inner = [("Federated query", "in place"), ("Semantic views", "one name per fact"),
             ("Data contracts", "13 checks, live"), ("Score · rules · ML", "bank policy")]
    for k, (t, d) in enumerate(inner):
        y = 200 + k * 44
        out.append(f'<rect x="475" y="{y}" width="290" height="36" rx="12" fill="rgba(255,255,255,.14)"/>'
                   f'<circle cx="494" cy="{y + 18}" r="10" fill="#fff"/><text x="494" y="{y + 22}" text-anchor="middle" font-size="11" font-weight="900" fill="#0B3B4A">{chr(97 + k)}</text>'
                   f'<text x="514" y="{y + 23}" font-size="14" font-weight="800" fill="#fff">{t}</text>'
                   f'<text x="755" y="{y + 23}" text-anchor="end" font-size="11.5" fill="#fff" opacity=".85">{d}</text>')
    out.append(_num(3, 470, 152))
    # 4 decide
    out.append('<line x1="790" y1="250" x2="838" y2="250" stroke="#9FB0C4" stroke-width="3" marker-end="url(#hw-ah)"/>')
    out.append('<circle cx="890" cy="250" r="48" fill="#E3F5F1" stroke="#12796A" stroke-width="2.5"/>' + _i(I_GAUGE, 866, 224, 2.0, "#12796A"))
    out.append('<rect x="878" y="170" width="64" height="22" rx="11" fill="#5B33C7"/>'
               '<text x="910" y="185" text-anchor="middle" font-size="11" font-weight="900" fill="#fff">ML model</text>')
    out.append(_num(4, 852, 196) + _label(890, 330, "Decide", "scorecard + ML model"))
    # three ways out
    outs = [(165, "#1FA08B", I_OK, "Approved", "~15 seconds"), (250, "#D98A00", I_USER, "Human in the loop", "with a checklist"),
            (335, "#C8102E", I_NO, "Declined", "with the reasons")]
    for y, c, ic, t, s in outs:
        out.append(f'<path d="M940 250 C975 250 975 {y} 1010 {y}" fill="none" stroke="{c}" stroke-width="3" marker-end="url(#hw-ah)"/>')
        out.append(_i(ic, 1018, y - 18, 1.5, c, 2.2) + _label(1060, y - 2, t, s, c, "start"))
    # 5 the log
    out.append('<line x1="40" y1="410" x2="1200" y2="410" stroke="#E6EBF2" stroke-width="2"/>')
    out.append(_num(5, 470, 438) + _i(I_LOCK, 500, 422, 1.3, "#0B1B34"))
    out.append('<text x="540" y="443" font-size="15" font-weight="800" fill="#0B1B34">Every step is logged</text>'
               '<text x="712" y="443" font-size="13" fill="#5B6B80">and no one can change it, not even the underwriter</text>')
    out.append('</svg>')
    return "".join(out)


def page():
    take = [(I_COPY, "No copies", "the data stays in its systems"), (I_CLOCK, "Seconds, not days", "people only see the edge cases"),
            (I_WHY, "Every decision explained", "each rule, score point and signature")]
    return (f'<div class="ov-band" style="margin-top:.4rem"><div class="ov-k">How it works</div>'
            f'<div class="hw-h">Four PDFs in, a decision out. <em>Nothing is copied.</em></div></div>'
            f'<div class="hw-pic">{picture()}</div>'
            f'<div class="hw3">{"".join(f"<div>{_svg_icon(i)}<div><b>{t}</b><span>{s}</span></div></div>" for i, t, s in take)}</div>')


def semantic_picture():
    """Three systems, each with its own names for the same facts -> the semantic views (one name each) -> the contracts
    gate -> trusted facts go on to the decision; a broken promise goes to a person."""
    W, H = 1240, 420
    arrow = '<path d="M0 0 L10 5 L0 10 z" fill="#9FB0C4"/>'
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="How the semantic layer and data contracts work">',
           f'<defs><marker id="sm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto">{arrow}</marker></defs>']
    srcs = [(20, "#0076AD", I_DB, "User application", "MongoDB", ["applicant.dob", "fields.net", "fields.idNumber"]),
            (150, "#C56A00", I_BANK, "Core banking", "Postgres", ["cust_mst.dob_txt", "txn_hist.txn_amt", "cust_mst.pan_no"]),
            (280, "#7A4FD6", I_CHART, "Credit report API", "", ["score", "existingEmi", "reportId"])]
    for y, c, ic, t, sub, names in srcs:
        out.append(f'<rect x="30" y="{y}" width="290" height="116" rx="18" fill="{c}"/>' + _i(ic, 44, y + 12, 1.2, "#fff", 2))
        out.append(f'<text x="80" y="{y + 30}" font-size="16" font-weight="800" fill="#fff">{t}</text>'
                   f'<text x="306" y="{y + 30}" text-anchor="end" font-size="11.5" fill="#fff" opacity=".85">{sub}</text>')
        for k, n in enumerate(names):
            out.append(f'<rect x="44" y="{y + 44 + k * 22}" width="262" height="19" rx="6" fill="rgba(255,255,255,.16)"/>'
                       f'<text x="54" y="{y + 58 + k * 22}" font-size="12" font-family="JetBrains Mono, monospace" fill="#fff">{n}</text>')
        out.append(f'<path d="M322 {y + 58} C380 {y + 58} 380 210 432 210" fill="none" stroke="{c}" stroke-width="3" stroke-dasharray="6 6"/>')
    out.append(_num(1, 32, 20))
    out.append('<text x="175" y="412" text-anchor="middle" font-size="13" font-weight="700" fill="#5B6B80">every system has its own names and formats</text>')
    # the semantic views
    out.append('<rect x="440" y="40" width="270" height="340" rx="22" fill="#E3F5F1" stroke="#12796A" stroke-width="2.5"/>')
    out.append('<text x="575" y="72" text-anchor="middle" font-size="20" font-weight="900" fill="#0B3B4A">Semantic views</text>'
               '<text x="575" y="90" text-anchor="middle" font-size="12.5" fill="#12796A">one name, one type for every fact</text>')
    # who makes them: an agent drafts each view, a person approves it
    out.append('<rect x="458" y="100" width="100" height="26" rx="13" fill="#0B1B34"/>' + _i(I_BOT, 465, 104, 0.75, "#5EE0C2", 2.2)
               + '<text x="485" y="117" font-size="10.5" font-weight="800" fill="#fff">Agent creates</text>'
               + '<path d="M561 113 h10" stroke="#12796A" stroke-width="2" marker-end="url(#sm-ah)"/>'
               + '<rect x="574" y="100" width="118" height="26" rx="13" fill="#12796A"/>' + _i(I_USER, 581, 104, 0.75, "#fff", 2.2)
               + '<text x="601" y="117" font-size="10.5" font-weight="800" fill="#fff">Human approves</text>')
    terms = [("Date of birth", "DATE"), ("Monthly salary", "Rs / month"), ("PAN", "the join key"), ("Existing EMIs", "Rs / month"),
             ("Bureau score", "300-900"), ("Customer ID", "the one ID")]
    for k, (t, ty) in enumerate(terms):
        y = 136 + k * 39
        out.append(f'<rect x="458" y="{y}" width="234" height="32" rx="10" fill="#fff" stroke="#9ED9CE"/>'
                   f'<text x="472" y="{y + 21}" font-size="14" font-weight="800" fill="#0B1B34">{t}</text>'
                   f'<text x="680" y="{y + 21}" text-anchor="end" font-size="11.5" fill="#12796A">{ty}</text>')
    out.append(_num(2, 448, 42))
    # the contracts gate
    out.append('<line x1="712" y1="210" x2="772" y2="210" stroke="#9FB0C4" stroke-width="3" marker-end="url(#sm-ah)"/>')
    out.append('<path d="M840 130 l70 28 v52 c0 48 -32 80 -70 96 c-38 -16 -70 -48 -70 -96 v-52 z" fill="#0B1B34"/>'
               + _i('<path d="M7 12l3.5 3.5 7-7"/>', 804, 174, 3.0, "#5EE0C2", 2.2))
    out.append('<text x="840" y="336" text-anchor="middle" font-size="17" font-weight="800" fill="#0B1B34">Data contracts</text>'
               '<text x="840" y="356" text-anchor="middle" font-size="13" fill="#5B6B80">13 promises, 4 owners</text>'
               '<text x="840" y="374" text-anchor="middle" font-size="13" fill="#5B6B80">checked on every upload</text>')
    out.append(_num(3, 790, 132))
    # two ways out
    out.append('<path d="M912 190 C950 190 950 120 990 120" fill="none" stroke="#1FA08B" stroke-width="3" marker-end="url(#sm-ah)"/>')
    out.append('<rect x="1000" y="78" width="220" height="86" rx="18" fill="#F2FBF8" stroke="#1FA08B" stroke-width="2"/>'
               + _i(I_OK, 1014, 92, 1.3, "#1FA08B", 2.2) +
               '<text x="1052" y="112" font-size="16" font-weight="800" fill="#12796A">Kept: trusted facts</text>'
               '<text x="1014" y="140" font-size="12.5" fill="#5B6B80">on to the scorecard, the rules</text>'
               '<text x="1014" y="156" font-size="12.5" fill="#5B6B80">and the ML model</text>')
    out.append('<path d="M912 240 C950 240 950 300 990 300" fill="none" stroke="#C8102E" stroke-width="3" marker-end="url(#sm-ah)"/>')
    out.append('<rect x="1000" y="258" width="220" height="86" rx="18" fill="#FFF5F6" stroke="#C8102E" stroke-width="2"/>'
               + _i(I_USER, 1014, 272, 1.3, "#C8102E", 2.2) +
               '<text x="1052" y="292" font-size="16" font-weight="800" fill="#B00D27">Human in the loop</text>'
               '<text x="1014" y="320" font-size="12.5" fill="#5B6B80">critical breach: a person decides</text>'
               '<text x="1014" y="336" font-size="12.5" fill="#5B6B80">warning: the owner is told</text>')
    out.append('</svg>')
    return "".join(out)
