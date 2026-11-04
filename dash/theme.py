"""The console's look: Exasol brand tokens (colours, fonts, spacing) shared by the demo consoles.

A dark gradient hero, translucent signal cards on it,
teal section kickers, and a dark "what to notice" card. What is different is the
job -- this screen argues a CASE rather than driving a pipeline, so it adds an
act structure (challenge / solution / notice) and a red accent for the places
the demo admits it fails.
"""

FONTS = ("https://fonts.googleapis.com/css2?"
         "family=Figtree:wght@400;500;600;700;800;900&"
         "family=JetBrains+Mono:wght@400;500;700&display=swap")

# The font link is an @import INSIDE <style>, never a <link> before it. A <link>
# opens a CommonMark type-6 HTML block, which ends at the first blank line -- so
# everything after the first blank line in this stylesheet renders on the page as
# literal text. `<style>` opens a type-1 block instead, which runs to </style>.
# Ported verbatim from the clinical-trials demo so the two presentations share
# one visual language. Tokens, hero, act rail, challenge/solution cards, KPI grid
# and the dark note card are unchanged. Everything under "kafka demo additions"
# is new and is written in the same idiom.
_SHEET = f"""
<style>
@import url('{FONTS}');
:root {{
  /* Exasol brand, taken from exasol.com's own stylesheet.
     One rule governs everything below: #00B2FF is a FILL, never text -- it
     measures 2.38:1 on white. The -ink variants are its accessible
     counterparts and every coloured word on the page uses one of those. */
  --navy:#081226; --navy-8:#10203F;
  --bg-top:#F4F7FB; --bg-bottom:#FFFFFF;
  --ink:#081226; --muted:#4A5464; --faint:#5A6679;
  --blue:#00B2FF;  --blue-ink:#0076AD;  --blue-soft:#E2F4FF;
  --teal:#1FA08B;  --teal-ink:#12796A;  --teal-soft:#E3F5F1;
  --green:#5FC33B; --green-ink:#3E8722; --green-soft:#EDF8E6;
  --amber:#F59E0B; --amber-ink:#9A6206; --amber-soft:#FEF3DC;
  --bad:#C4121F;   --bad-ink:#C4121F;   --bad-soft:#FCEBEC;
  --line:rgba(8,18,38,0.10);
  --card:rgba(255,255,255,0.86);
  --shadow:0 18px 45px rgba(8,18,38,0.09);
}}
html, body, [class*="css"] {{ font-family:"Figtree",sans-serif; color:var(--ink); }}
.stApp {{
  background:
    radial-gradient(circle at top left, rgba(226,244,255,0.95), transparent 30%),
    radial-gradient(circle at top right, rgba(227,245,241,0.85), transparent 26%),
    linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 55%, #ffffff 100%);
}}
.block-container {{ padding:1.4rem 2.2rem 3rem !important; max-width:100% !important; }}
@media (min-width:1700px) {{ .block-container {{ padding-left:3.5rem !important;
  padding-right:3.5rem !important; }} }}
h1,h2,h3 {{ font-family:"Figtree",sans-serif; letter-spacing:-0.03em; color:var(--ink); }}
code, pre, .mono {{ font-family:"JetBrains Mono",monospace !important; }}
[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stToolbar"],
[data-testid="stHeaderActionElements"], #MainMenu, header[data-testid="stHeader"],
footer {{ display:none; }}

/* ---------- hero ---------- */
.hero-shell {{ position:relative;
  background:linear-gradient(135deg, #081226 0%, #10203F 58%, #12796A 100%);
  border-radius:28px; padding:1.8rem 1.9rem; box-shadow:var(--shadow);
  color:#f7fbff; margin-bottom:1.35rem; overflow:hidden; position:relative;
}}
.hero-shell::after {{
  content:""; position:absolute; inset:auto -40px -40px auto; width:220px; height:220px;
  background:radial-gradient(circle, rgba(255,255,255,0.17), transparent 65%);
}}
.hero-eyebrow {{ text-transform:uppercase; letter-spacing:.16em; font-size:.72rem;
  font-weight:600; color:rgba(255,255,255,.70); margin-bottom:.8rem; }}
.hero-title {{ font-family:"Figtree",sans-serif; font-size:2.2rem; line-height:1.02;
  font-weight:700; max-width:20ch; margin-bottom:.7rem; }}
.hero-copy {{ max-width:58rem; font-size:1rem; line-height:1.6; color:rgba(247,251,255,.82); }}
.signal-grid {{ display:grid; gap:.85rem; margin-top:1.15rem; grid-template-columns:repeat(4,minmax(0,1fr)); }}
.signal-card {{ border-radius:22px; border:1px solid rgba(255,255,255,.10);
  background:rgba(255,255,255,.10); padding:1rem; backdrop-filter:blur(8px); }}
.signal-label {{ text-transform:uppercase; letter-spacing:.12em; font-size:.68rem; font-weight:700;
  margin-bottom:.35rem; color:rgba(255,255,255,.62); }}
.signal-value {{ font-family:"Figtree",sans-serif; font-size:1.2rem; font-weight:700; }}
.signal-meta {{ color:rgba(255,255,255,.70); font-size:.88rem; margin-top:.2rem; }}
.signal-card.down {{ border-color:rgba(255,160,150,.45); background:rgba(196,18,31,.22); }}

/* ---------- section + act ---------- */
.section-kicker {{ text-transform:uppercase; letter-spacing:.16em; font-size:.7rem;
  font-weight:700; color:var(--teal); margin-bottom:.25rem; }}
.section-title {{ font-family:"Figtree",sans-serif; font-size:1.5rem; margin:0; }}
.section-copy {{ color:var(--muted); max-width:64rem; margin-top:.3rem; line-height:1.6; }}

.act-rail {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.6rem; margin:.2rem 0 1.4rem; }}
.act-chip {{ border-radius:14px; border:1px solid var(--line); background:rgba(255,255,255,.62);
  padding:.6rem .75rem; }}
.act-chip .n {{ font-family:"JetBrains Mono",monospace; font-size:.66rem; font-weight:700;
  letter-spacing:.14em; color:var(--faint); }}
.act-chip .t {{ font-size:.86rem; font-weight:600; line-height:1.3; margin-top:.1rem; }}
.act-chip.on {{ border-color:rgba(31,160,139,.35); background:linear-gradient(180deg,
  rgba(228,250,247,.96) 0%, rgba(255,255,255,.98) 100%); }}
.act-chip.on .n {{ color:var(--teal); }}

.chal {{ border-radius:22px; border:1px solid var(--line); box-shadow:var(--shadow);
  background:linear-gradient(180deg, rgba(255,246,244,.95) 0%, rgba(255,252,251,.98) 100%);
  border-left:5px solid var(--bad); padding:1.1rem 1.2rem; margin-bottom:.9rem; }}
.sol {{ border-radius:22px; border:1px solid var(--line); box-shadow:var(--shadow);
  background:linear-gradient(180deg, rgba(228,250,247,.92) 0%, rgba(255,255,255,.98) 100%);
  border-left:5px solid var(--teal); padding:1.1rem 1.2rem; margin-bottom:.9rem; }}
.chal .lbl, .sol .lbl {{ text-transform:uppercase; letter-spacing:.14em; font-size:.66rem;
  font-weight:700; margin-bottom:.4rem; }}
.chal .lbl {{ color:var(--bad); }}
.sol  .lbl {{ color:var(--teal); }}
.chal p, .sol p {{ margin:.35rem 0 0; line-height:1.6; }}
.chal .big {{ font-family:"Figtree",sans-serif; font-size:1.25rem; font-weight:700;
  line-height:1.25; }}
.sol .big {{ font-family:"Figtree",sans-serif; font-size:1.25rem; font-weight:700;
  line-height:1.25; }}

.note-card {{ border-radius:22px; border:1px solid rgba(255,255,255,.08); box-shadow:var(--shadow);
  background:linear-gradient(180deg, rgba(11,34,53,.96) 0%, rgba(19,45,69,.95) 100%);
  color:#f6fbff; padding:1.15rem; }}
.note-card .mini-kicker {{ text-transform:uppercase; letter-spacing:.12em; font-size:.68rem;
  font-weight:700; margin-bottom:.35rem; color:rgba(255,255,255,.66); }}
.note-card p, .note-card ul {{ margin:.45rem 0 0; line-height:1.55; color:inherit; }}
.note-card li {{ margin-bottom:.25rem; }}

/* ---------- numbers ---------- */
.kpi-grid {{ display:grid; gap:.85rem; margin:.2rem 0 .4rem;
  grid-template-columns:repeat(6,minmax(0,1fr)); }}
@media (max-width:1500px) {{ .kpi-grid {{ grid-template-columns:repeat(3,minmax(0,1fr)); }} }}
@media (max-width:900px) {{ .kpi-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
.kpi {{ border-radius:18px; border:1px solid var(--line); background:var(--card);
  box-shadow:var(--shadow); padding:.9rem 1rem; }}
.kpi .k {{ text-transform:uppercase; letter-spacing:.12em; font-size:.66rem; font-weight:700;
  color:var(--muted); }}
.kpi .v {{ font-family:"Figtree",sans-serif; font-size:1.65rem; font-weight:700;
  font-variant-numeric:tabular-nums; margin-top:.15rem; }}
.kpi .x {{ font-size:.82rem; color:var(--muted); margin-top:.1rem; line-height:1.4; }}
.kpi.hot {{ border-color:rgba(196,18,31,.28); background:linear-gradient(180deg,
  rgba(251,234,233,.95) 0%, rgba(255,252,252,.98) 100%); }}
.kpi.hot .v {{ color:var(--bad); }}
.kpi.good .v {{ color:var(--teal); }}

/* single-series bars: the row label names the bar, so no legend */
.bars {{ margin-top:.5rem; }}
.barrow {{ display:grid; grid-template-columns:190px 1fr 92px; gap:.7rem; align-items:center;
  padding:.28rem 0; }}
.barrow .lb {{ font-size:.86rem; color:var(--ink); }}
.barrow .tr {{ height:20px; background:rgba(8,18,38,.06); border-radius:6px; overflow:hidden; }}
.barrow .fl {{ height:100%; background:var(--teal); border-radius:6px; }}
.barrow .fl.warn {{ background:var(--amber); }}
.barrow .fl.bad {{ background:var(--bad); }}
.barrow .vv {{ font-family:"JetBrains Mono",monospace; font-size:.82rem; text-align:right;
  color:var(--muted); font-variant-numeric:tabular-nums; }}

/* result rows */
.res {{ border-radius:14px; border:1px solid var(--line); background:rgba(255,255,255,.80);
  padding:.6rem .8rem; margin-bottom:.4rem; }}
.res.bad {{ border-color:rgba(196,18,31,.35); background:rgba(251,234,233,.85); }}
.res .top {{ display:flex; gap:.6rem; align-items:baseline; flex-wrap:wrap; }}
.res .nct {{ font-family:"JetBrains Mono",monospace; font-size:.8rem; color:var(--muted); }}
.res .tag {{ font-size:.63rem; text-transform:uppercase; letter-spacing:.1em; font-weight:700;
  border-radius:999px; padding:.1rem .5rem; background:var(--teal-soft); color:var(--teal); }}
.res.bad .tag {{ background:var(--bad); color:#fff; }}
.res .sim {{ margin-left:auto; font-family:"JetBrains Mono",monospace; font-size:.76rem; color:var(--faint); }}
.res .tx {{ font-size:.88rem; color:var(--ink); margin-top:.22rem; line-height:1.45; }}

.tiers {{ display:grid; grid-template-columns:1fr auto 1fr; gap:.9rem; align-items:stretch; margin:.3rem 0 .2rem; }}
.tier {{ border-radius:18px; border:1px solid var(--line); background:var(--card);
  box-shadow:var(--shadow); padding:.9rem 1rem; }}
.tier .k {{ text-transform:uppercase; letter-spacing:.12em; font-size:.64rem; font-weight:700;
  color:var(--muted); }}
.tier .n {{ font-family:"Figtree",sans-serif; font-size:1.05rem; font-weight:700; margin-top:.15rem; }}
.tier .d {{ font-size:.82rem; color:var(--muted); margin-top:.2rem; line-height:1.45; }}
.tier.lake {{ border-color:rgba(245,158,11,.30); background:linear-gradient(180deg,
  rgba(255,247,234,.95) 0%, rgba(255,253,250,.98) 100%); }}
.joiner {{ display:flex; align-items:center; justify-content:center; font-family:"JetBrains Mono",monospace;
  font-size:.7rem; font-weight:700; letter-spacing:.12em; color:var(--teal); text-align:center;
  writing-mode:horizontal-tb; padding:0 .3rem; }}

.stTabs [data-baseweb="tab-list"] {{ gap:1.4rem; border-bottom:1px solid var(--line); }}
.stTabs [data-baseweb="tab"] {{ font-size:.92rem; font-weight:600; color:var(--muted); padding:.4rem 0; }}
.stTabs [aria-selected="true"] {{ color:var(--bad) !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background:var(--bad); }}

.stButton > button {{ font-family:"Figtree",sans-serif !important; font-weight:600 !important;
  border-radius:12px !important; border:1px solid rgba(31,160,139,.35) !important;
  background:linear-gradient(135deg,#081226 0%,#10203F 100%) !important; color:#fff !important; }}
@media (max-width:1000px) {{
  .signal-grid, .kpi-grid, .act-rail {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .tiers {{ grid-template-columns:1fr; }}
}}

/* ================= kafka demo additions ================= */
/* The five-hop rail. Same card language as .kpi, one per pipeline stage. */
.rail {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.7rem; margin:.7rem 0 .2rem; }}
.stg {{ border-radius:18px; border:1px solid var(--line); background:var(--card);
  box-shadow:var(--shadow); padding:.8rem .95rem; transition:all .22s ease; }}
.stg .sys {{ font-family:"JetBrains Mono",monospace; font-size:.62rem; font-weight:700;
  letter-spacing:.13em; text-transform:uppercase; color:var(--faint); }}
.stg .what {{ font-size:.9rem; font-weight:600; margin-top:.12rem; }}
.stg .ms {{ font-family:"Figtree",sans-serif; font-size:1.6rem; font-weight:700;
  font-variant-numeric:tabular-nums; margin-top:.25rem; color:var(--faint); }}
.stg .ms small {{ font-size:.72rem; font-weight:600; margin-left:.1rem; }}
.stg.run {{ border-color:rgba(245,158,11,.38);
  background:linear-gradient(180deg, rgba(255,247,234,.96) 0%, rgba(255,253,250,.98) 100%); }}
.stg.run .ms {{ color:var(--amber); }}
.stg.done {{ border-color:rgba(31,160,139,.32); }}
.stg.done .ms {{ color:var(--ink); }}

/* The verdict. One number, allowed to be enormous. */
.verdict {{ border-radius:22px; border:1px solid var(--line); box-shadow:var(--shadow);
  padding:1.15rem 1.35rem; margin:.8rem 0 .7rem; display:flex; align-items:center;
  gap:1.9rem; flex-wrap:wrap; }}
.verdict .word {{ font-family:"Figtree",sans-serif; font-size:clamp(2.6rem,5.4vw,4.2rem);
  font-weight:700; letter-spacing:-.04em; line-height:1; }}
.verdict .m {{ text-transform:uppercase; letter-spacing:.12em; font-size:.66rem;
  font-weight:700; color:var(--muted); }}
.verdict .m b {{ display:block; font-family:"Figtree",sans-serif; font-size:1.75rem;
  font-weight:700; color:var(--ink); letter-spacing:-.02em; text-transform:none;
  font-variant-numeric:tabular-nums; margin-top:.1rem; }}
.v-approve {{ background:linear-gradient(180deg, rgba(228,250,247,.92) 0%, rgba(255,255,255,.98) 100%);
  border-left:5px solid var(--teal); }}
.v-approve .word {{ color:var(--teal); }}
.v-review {{ background:linear-gradient(180deg, rgba(255,247,234,.95) 0%, rgba(255,253,250,.98) 100%);
  border-left:5px solid var(--amber); }}
.v-review .word {{ color:var(--amber); }}
.v-block {{ background:linear-gradient(180deg, rgba(251,234,233,.95) 0%, rgba(255,252,252,.98) 100%);
  border-left:5px solid var(--bad); }}
.v-block .word {{ color:var(--bad); }}

/* Architecture strip: reuses .tier, six across with joiners. */
.archrow {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:.55rem;
  align-items:stretch; margin:.4rem 0 .2rem; }}
.tier.exa {{ border-color:rgba(31,160,139,.32); background:linear-gradient(180deg,
  rgba(228,250,247,.92) 0%, rgba(255,255,255,.98) 100%); }}
.tier.exa .k {{ color:var(--teal); }}

/* The act rail here has seven steps, not four. */
.act-rail.seven {{ grid-template-columns:repeat(7,minmax(0,1fr)); }}
.act-chip.done {{ opacity:.55; }}

/* Receipt bars reuse .barrow; only the negative direction is new. */
.barrow .fl.neg {{ background:var(--blue-ink); }}


/* slim hero, shown once the story is running */
.hero-slim {{ display:flex; align-items:center; justify-content:space-between; gap:1rem;
  flex-wrap:wrap; border-radius:18px; padding:.7rem 1.1rem; margin-bottom:.8rem;
  background:linear-gradient(135deg, rgba(9,33,48,0.96) 0%, rgba(17,42,73,0.94) 60%,
  rgba(147,76,31,0.88) 100%); box-shadow:var(--shadow); color:#f7fbff; }}
.hs-t {{ font-family:"Figtree",sans-serif; font-size:1.05rem; font-weight:700; }}
.hs-t em {{ font-style:normal; color:#7fd6ff; }}
.hs-t span {{ font-family:"Figtree",sans-serif; font-weight:500; font-size:.85rem;
  color:rgba(247,251,255,.62); margin-left:.5rem; }}
.hs-m {{ display:flex; align-items:center; gap:.7rem; flex-wrap:wrap;
  font-size:.82rem; color:rgba(247,251,255,.75); }}
.hs-pill {{ text-transform:uppercase; letter-spacing:.1em; font-size:.6rem; font-weight:700;
  border-radius:999px; padding:.18rem .6rem; background:rgba(31,160,139,.45); color:#c9f5ec; }}
.hs-pill.down {{ background:rgba(196,18,31,.5); color:#ffd7d4; }}
.hs-num {{ font-family:"Figtree",sans-serif; font-weight:700; color:#fff; }}

/* the rail sits directly above the controls; keep the gap small */
div[data-testid="stHorizontalBlock"]:has(button[data-testid="stBaseButton-tertiary"]) {{
  margin-bottom:.35rem; }}
/* nav rail buttons: streamlit's own kinds carry the state */
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"],
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-tertiary"] {{
  font-family:"JetBrains Mono",monospace !important; font-size:.6rem !important;
  font-weight:700 !important; letter-spacing:.08em !important;
  padding:.24rem .1rem !important; border-radius:7px !important;
  min-height:0 !important; }}
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"] {{
  background:rgba(215,243,239,.7) !important; color:var(--teal) !important;
  border:1px solid rgba(31,160,139,.25) !important; }}
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-tertiary"] {{
  background:rgba(255,255,255,.5) !important; color:var(--faint) !important;
  border:1px solid var(--line) !important; }}
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-primary"] {{
  font-family:"JetBrains Mono",monospace !important; font-size:.6rem !important;
  font-weight:700 !important; letter-spacing:.08em !important;
  padding:.24rem .1rem !important; border-radius:7px !important; min-height:0 !important; }}

/* three-up row for the page-1 summary points */
.archrow.three {{ grid-template-columns:repeat(3,minmax(0,1fr)); }}
/* result grid on page 2 */
.restab {{ width:100%; border-collapse:collapse; font-size:.85rem; margin-top:.2rem; }}
.restab th {{ text-align:right; font-family:"JetBrains Mono",monospace; font-size:.58rem;
  letter-spacing:.09em; text-transform:uppercase; color:var(--faint); font-weight:700;
  padding:.3rem .55rem .4rem; border-bottom:1px solid var(--rule-firm,var(--line));
  line-height:1.25; vertical-align:bottom; }}
.restab th:first-child, .restab th:last-child {{ text-align:left; }}
.restab td {{ padding:.45rem .55rem; border-bottom:1px solid var(--line); color:var(--ink); }}
.restab td.merch {{ font-weight:600; }}
.restab td.num {{ text-align:right; font-variant-numeric:tabular-nums;
  font-family:"JetBrains Mono",monospace; font-size:.82rem; }}
.restab td.score {{ font-weight:700; }}
.restab td.empty {{ text-align:center; color:var(--muted); padding:1.2rem; }}
.restab tr.hot td {{ background:rgba(251,234,233,.75); }}
.restab tr.hot td.score {{ color:var(--bad); }}
.restab tr.warn td {{ background:rgba(251,238,218,.7); }}
.restab tr.warn td.score {{ color:var(--amber); }}
.restab tr:last-child td {{ border-bottom:0; }}
.pill-d {{ font-family:"JetBrains Mono",monospace; font-size:.6rem; font-weight:700;
  letter-spacing:.09em; border-radius:999px; padding:.18rem .55rem; }}
.d-approve {{ background:var(--teal-soft); color:var(--teal); }}
.d-review {{ background:var(--amber-soft); color:var(--amber); }}
.d-block {{ background:var(--bad); color:#fff; }}

/* the drawn architecture */
.archbox {{ border-radius:22px; border:1px solid var(--line); background:rgba(255,255,255,.72);
  box-shadow:var(--shadow); padding:.6rem .6rem .3rem; margin:.3rem 0 .5rem; overflow-x:auto; }}
.archbox svg {{ display:block; width:100%; height:auto; }}
.doclinks {{ font-size:.84rem; color:var(--muted); margin:0 0 .9rem; line-height:1.9; }}
.doclinks .dl-k {{ font-family:"JetBrains Mono",monospace; font-size:.62rem; font-weight:700;
  letter-spacing:.12em; text-transform:uppercase; color:var(--faint); margin-right:.7rem; }}
.doclinks a {{ color:var(--teal); text-decoration:none; border-bottom:1px solid rgba(31,160,139,.3); }}
.doclinks a:hover {{ border-bottom-color:var(--teal); }}

.runlabel {{ font-family:"JetBrains Mono",monospace; font-size:.68rem; font-weight:700;
  letter-spacing:.06em; color:var(--muted); margin:.6rem 0 -.2rem; }}
.howto {{ border-radius:14px; border:1px solid var(--line); border-left:4px solid var(--teal);
  background:rgba(215,243,239,.45); padding:.6rem .9rem; margin:.2rem 0 .7rem;
  font-size:.92rem; color:var(--muted); }}
.howto b {{ color:var(--ink); }}
.footnote {{ font-size:.78rem; color:var(--faint); line-height:1.55; margin-top:.5rem;
  max-width:70ch; }}
.footnote b {{ color:var(--muted); font-family:"JetBrains Mono",monospace; }}

/* agentic investigation steps */
.agstep {{ max-width:100%; overflow:hidden; border-radius:18px; border:1px solid var(--line); background:var(--card);
  box-shadow:var(--shadow); padding:.8rem 1rem; margin-bottom:.6rem;
  border-left:4px solid var(--teal); }}
.ag-why {{ font-size:1rem; font-weight:600; color:var(--ink); margin-bottom:.45rem; }}
.ag-sql {{ font-family:"JetBrains Mono",monospace; font-size:.74rem; line-height:1.5;
  color:var(--blue-ink); background:rgba(8,18,38,.04); border-radius:8px; padding:.5rem .65rem;
  white-space:pre-wrap; word-break:break-word; margin-bottom:.45rem; }}
.agtabwrap {{ max-width:100%; overflow-x:auto; }}
.agtab {{ width:100%; border-collapse:collapse; font-size:.76rem;
  font-family:"JetBrains Mono",monospace; table-layout:auto; }}
.agtab th, .agtab td {{ white-space:nowrap; }}
.agtab th {{ text-align:left; font-size:.6rem; letter-spacing:.08em; text-transform:uppercase;
  color:var(--faint); font-weight:700; padding:.25rem .5rem .3rem 0;
  border-bottom:1px solid var(--line); }}
.agtab td {{ padding:.28rem .5rem .28rem 0; border-bottom:1px solid var(--line);
  color:var(--muted); }}
.ag-more {{ font-size:.7rem; color:var(--faint); margin-top:.4rem; }}
.ag-err {{ font-size:.8rem; color:var(--bad); background:var(--bad-soft);
  border-radius:8px; padding:.4rem .6rem; }}
.note-card ul {{ margin:.5rem 0 .3rem 1.1rem; padding:0; }}
.note-card li {{ margin-bottom:.3rem; font-size:.95rem; }}

.ag-tool {{ font-family:"JetBrains Mono",monospace; font-size:.72rem; font-weight:700;
  letter-spacing:.06em; color:var(--teal); background:var(--teal-soft);
  border-radius:6px; padding:.15rem .5rem; }}
.idcard {{ border-radius:16px; border:1px solid var(--line); background:var(--card);
  box-shadow:var(--shadow); padding:.7rem 1rem; margin:.5rem 0 .8rem;
  border-left:4px solid var(--teal); }}
.id-k {{ text-transform:uppercase; letter-spacing:.12em; font-size:.6rem; font-weight:700;
  color:var(--muted); }}
.id-u {{ font-family:"JetBrains Mono",monospace; font-size:1.05rem; font-weight:700;
  color:var(--ink); margin-top:.1rem; }}
.id-b {{ font-size:.85rem; color:var(--muted); margin-top:.15rem; }}

.qpreview {{ font-size:.92rem; line-height:1.55; color:var(--muted);
  background:rgba(255,255,255,.65); border:1px solid var(--line);
  border-left:3px solid var(--faint); border-radius:10px;
  padding:.6rem .85rem; margin:-.2rem 0 .7rem; }}

/* the answer */
.ans-head {{ font-family:"Figtree",sans-serif; font-size:1.3rem; font-weight:700;
  line-height:1.35; color:var(--ink); margin:.9rem 0 .5rem; max-width:80ch; }}
.ans-ev {{ margin:.2rem 0 .9rem 1.15rem; padding:0; }}
.ans-ev li {{ margin-bottom:.35rem; font-size:1rem; line-height:1.5; color:var(--fg2,var(--muted)); }}
.ans-ev li::marker {{ color:var(--teal); }}
/* the rows the agent nominated as its evidence */
.prooftbl {{ border:1px solid var(--line); border-radius:14px; overflow:hidden;
  background:var(--card); box-shadow:var(--shadow); margin:.2rem 0 .35rem; }}
.prooftbl table {{ width:100%; border-collapse:collapse; font-size:.86rem; }}
.prooftbl th {{ text-align:left; font-family:"JetBrains Mono",monospace; font-size:.6rem;
  letter-spacing:.1em; text-transform:uppercase; color:var(--muted); font-weight:700;
  padding:.5rem .8rem; background:rgba(8,18,38,.035);
  border-bottom:1px solid var(--line); white-space:nowrap; }}
.prooftbl td {{ padding:.45rem .8rem; border-bottom:1px solid var(--line);
  color:var(--ink); white-space:nowrap; }}
.prooftbl tbody tr:last-child td {{ border-bottom:0; }}
.prooftbl td:not(:first-child) {{ font-variant-numeric:tabular-nums; }}
.proof-note {{ font-size:.78rem; color:var(--faint); margin:0 0 1rem .1rem; }}
/* recommended action */
.actbox {{ border-radius:16px; border:1px solid var(--line); background:var(--card);
  box-shadow:var(--shadow); border-left:4px solid var(--teal);
  padding:.8rem 1.1rem .9rem; margin:.2rem 0 1rem; }}
.act-k {{ text-transform:uppercase; letter-spacing:.12em; font-size:.6rem; font-weight:700;
  color:var(--teal); margin-bottom:.4rem; }}
.act-list {{ margin:0 0 0 1.1rem; padding:0; }}
.act-list li {{ margin-bottom:.3rem; font-size:.95rem; line-height:1.5; color:var(--ink); }}
.cites-k {{ text-transform:uppercase; letter-spacing:.12em; font-size:.6rem; font-weight:700;
  color:var(--teal); margin:.4rem 0 .3rem; }}
.working {{ border-radius:14px; border:1px dashed var(--line); background:rgba(255,255,255,.55);
  padding:1rem 1.2rem; font-size:.95rem; color:var(--muted); text-align:center; }}

.auditbox {{ border-radius:16px; border:1px solid var(--line); background:rgba(255,255,255,.6);
  padding:.75rem 1rem .6rem; margin:.9rem 0 .4rem; }}
.audittbl {{ width:100%; border-collapse:collapse; font-size:.76rem;
  font-family:"JetBrains Mono",monospace; }}
.audittbl th {{ text-align:left; font-size:.58rem; letter-spacing:.1em; text-transform:uppercase;
  color:var(--faint); font-weight:700; padding:.25rem .6rem .3rem 0;
  border-bottom:1px solid var(--line); }}
.audittbl td {{ padding:.28rem .6rem .28rem 0; border-bottom:1px solid var(--line);
  color:var(--muted); white-space:nowrap; }}
.audittbl tbody tr:last-child td {{ border-bottom:0; }}
.audittbl .au-u {{ color:var(--teal); font-weight:700; }}
.audittbl .au-n {{ text-align:right; font-variant-numeric:tabular-nums; }}
.audittbl .au-q {{ white-space:normal; word-break:break-word; color:var(--blue-ink); }}
/* "where it ran" ledger */
.ran {{ width:100%; border-collapse:collapse; font-size:.95rem; margin-top:.3rem; }}
.ran td {{ padding:.6rem 0; border-bottom:1px solid var(--line); }}
.ran td:last-child {{ text-align:right; font-weight:600; }}
.ran tr:last-child td {{ border-bottom:0; }}
.ran .no {{ color:var(--faint); text-decoration:line-through; }}
.ran tr.hit td:last-child {{ color:var(--teal); font-weight:700; }}
@media (max-width:1200px) {{
  .rail {{ grid-template-columns:repeat(3,minmax(0,1fr)); }}
  .archrow {{ grid-template-columns:repeat(3,minmax(0,1fr)); }}
  .act-rail.seven {{ grid-template-columns:repeat(4,minmax(0,1fr)); }}
}}
.pagehead {{ display:flex; align-items:center; gap:.9rem; margin:0 0 .9rem .1rem; }}
.pagehead img {{ height:26px !important; width:auto !important;
  max-width:104px !important; }}
.pagehead .ph-t {{ font-size:.72rem; font-weight:700; letter-spacing:.14em;
  text-transform:uppercase; color:var(--faint); }}

/* ===== visual-first pages: one type family, one grid ===== */
/* Figtree everywhere; monospace is reserved for real SQL (st.code). */
.restab th, .restab td.num, .res .nct, .res .sim, .chip, .pill-d, .id-u,
.stg .sys, .mono-soft {{ font-family:"Figtree",sans-serif !important;
  font-variant-numeric:tabular-nums; }}
.restab th {{ font-size:.66rem; letter-spacing:.08em; }}
.restab td.num {{ font-size:.86rem; }}
.section-title {{ font-weight:800; letter-spacing:-.02em; }}
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"],
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-tertiary"],
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-primary"],
.stButton > button {{ font-family:"Figtree",sans-serif !important; font-size:.88rem !important;
  font-weight:700 !important; letter-spacing:0 !important; padding:.55rem .8rem !important;
  border-radius:12px !important; min-height:2.6rem !important; }}

.flow {{ display:grid; grid-template-columns:1fr auto 1fr auto 1fr auto 1fr;
  align-items:center; gap:.55rem; margin:.7rem 0 1rem; }}
.flow.five {{ grid-template-columns:1fr auto 1fr auto 1fr auto 1fr auto 1fr; }}
.fnode {{ display:flex; align-items:center; gap:.65rem; border-radius:14px;
  border:1px solid var(--line); background:var(--card); padding:.6rem .8rem; min-width:0; }}
.fnode .ic {{ width:34px; height:34px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; background:var(--blue-soft); color:var(--blue-ink); flex:none; }}
.fnode.hl {{ border-color:rgba(8,18,38,.25); }}
.fnode.hl .ic {{ background:var(--navy); color:#fff; }}
.fnode .t {{ font-weight:700; font-size:.95rem; line-height:1.15; }}
.fnode .s {{ font-size:.76rem; color:var(--faint); line-height:1.2; }}
.farrow {{ color:var(--faint); font-size:1.1rem; }}
@media (max-width:900px) {{ .flow, .flow.five {{ grid-template-columns:1fr; }}
  .farrow {{ display:none; }} }}

.colhead {{ display:flex; align-items:center; gap:.5rem; margin:.2rem 0 .6rem; flex-wrap:wrap;
  min-height:2.6rem; }}
.colhead .ttl {{ font-weight:800; font-size:1.1rem; margin-right:.3rem; }}
.colhead .ic {{ width:30px; height:30px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; background:var(--blue-soft); color:var(--blue-ink); }}
.chip {{ font-size:.72rem; font-weight:700; border-radius:999px; padding:.18rem .6rem;
  background:rgba(8,18,38,.06); color:var(--muted); }}
.chip.warn {{ background:var(--amber-soft); color:var(--amber-ink); }}
.chip.add {{ background:var(--teal-soft); color:var(--teal-ink); }}
.chip.no {{ background:transparent; border:1px dashed rgba(8,18,38,.2); color:var(--faint);
  text-decoration:line-through; }}
.res {{ padding:.62rem .9rem; }}
.res .risk {{ display:inline-block; width:8px; height:8px; border-radius:50%;
  margin-right:.45rem; background:var(--teal); vertical-align:middle; }}
.res .risk.mid {{ background:var(--amber); }}
.res .risk.hi {{ background:var(--bad); }}
.res .sim {{ font-size:.8rem; }}
.bar {{ display:flex; align-items:center; gap:.45rem; justify-content:flex-end; }}
.bar .trk {{ width:64px; height:7px; border-radius:999px; background:rgba(8,18,38,.08);
  overflow:hidden; flex:none; }}
.bar .fil {{ height:100%; border-radius:999px; background:var(--teal); }}
.bar .fil.mid {{ background:var(--amber); }}
.bar .fil.hi {{ background:var(--bad); }}

/* page 4: persona cards and access chips */
.pcard {{ border-radius:16px; border:2px solid var(--line); background:var(--card);
  padding:.85rem 1rem; margin-bottom:.5rem; display:flex; gap:.75rem; align-items:center; }}
.pcard.on {{ border-color:var(--navy); box-shadow:var(--shadow); }}
.pcard .ic {{ width:40px; height:40px; border-radius:50%; flex:none; display:flex;
  align-items:center; justify-content:center; background:var(--blue-soft); color:var(--blue-ink); }}
.pcard.on .ic {{ background:var(--navy); color:#fff; }}
.pcard .t {{ font-weight:800; font-size:1rem; line-height:1.15; }}
.pcard .u {{ font-size:.74rem; color:var(--faint); margin:.1rem 0 .35rem; }}
.pcard .books {{ display:flex; gap:.35rem; flex-wrap:wrap; }}
.qlabel {{ font-weight:800; font-size:1rem; margin:.9rem 0 .1rem; }}
/* page 3: claim line, stat panels, limits */
.claim {{ display:flex; gap:.8rem; align-items:center; border-radius:16px;
  background:var(--navy); color:#fff; padding:.8rem 1.1rem; margin:.9rem 0 .9rem;
  font-size:.95rem; }}
.claim .ic {{ width:34px; height:34px; border-radius:50%; flex:none; display:flex;
  align-items:center; justify-content:center; background:rgba(255,255,255,.12); }}
.claim b {{ color:#fff; }}
.panel {{ border-radius:16px; border:1px solid var(--line); background:var(--card);
  padding:.9rem 1.1rem; height:100%; }}
.panel-k {{ text-transform:uppercase; letter-spacing:.12em; font-size:.66rem;
  font-weight:700; color:var(--teal-ink); }}
.panel-t {{ font-weight:800; font-size:1.25rem; margin:.1rem 0 .55rem; }}
.panel-x {{ font-size:.8rem; color:var(--faint); margin-top:.45rem; }}
.hbars {{ display:grid; gap:.45rem; }}
.hb {{ display:grid; grid-template-columns:minmax(0,11rem) 1fr 4.5rem; gap:.6rem;
  align-items:center; font-size:.85rem; }}
.hb-l {{ color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.hb-t {{ height:10px; border-radius:999px; background:rgba(8,18,38,.07); overflow:hidden; }}
.hb-f {{ height:100%; border-radius:999px; background:var(--teal); }}
.hb-f.mid {{ background:var(--amber); }}
.hb-f.hi {{ background:var(--bad); }}
.hb-v {{ text-align:right; font-weight:700; font-variant-numeric:tabular-nums; }}
.limits {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.7rem; margin:.4rem 0 .9rem; }}
@media (max-width:1000px) {{ .limits {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
.lim {{ display:flex; gap:.65rem; align-items:center; border-radius:14px;
  border:1px solid rgba(196,18,31,.18); background:rgba(252,235,236,.5); padding:.7rem .85rem; }}
.lim .ic {{ width:32px; height:32px; border-radius:50%; flex:none; display:flex;
  align-items:center; justify-content:center; background:var(--bad-soft); color:var(--bad-ink); }}
.lim .t {{ font-weight:800; font-size:.92rem; }}
.lim .s {{ font-size:.76rem; color:var(--muted); line-height:1.3; }}
.doclinks {{ display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; }}
.doclinks a.chip {{ text-decoration:none; border-bottom:0; color:var(--teal-ink); }}

/* human review */
.an {{ font-size:.68rem; font-weight:700; margin-top:.2rem; white-space:nowrap; }}
.an-ok {{ color:var(--teal-ink); }}
.an-bad {{ color:var(--bad-ink); }}
.an-wait {{ color:var(--amber-ink); }}
.rv {{ display:grid; grid-template-columns:minmax(0,1.4fr) minmax(0,1fr) auto; gap:.8rem;
  align-items:center; border-radius:14px; border:1px solid var(--line); background:var(--card);
  padding:.6rem .9rem; margin-bottom:.4rem; }}
.rv-m {{ font-size:.92rem; }}
.rv-s .bar {{ justify-content:flex-start; font-size:.8rem; color:var(--muted); }}
.rv-p {{ font-size:.72rem; font-weight:800; border-radius:999px; padding:.2rem .65rem; white-space:nowrap; }}
.rv-wait {{ border-color:rgba(245,158,11,.4); }}
.rv-wait .rv-p {{ background:var(--amber-soft); color:var(--amber-ink); }}
.rv-ok .rv-p {{ background:var(--teal-soft); color:var(--teal-ink); }}
.rv-bad .rv-p {{ background:var(--bad-soft); color:var(--bad-ink); }}

/* ===== compact result + one font for Streamlit widgets ===== */
.rail {{ gap:.5rem; margin:.6rem 0 .1rem; }}
.stg {{ border-radius:14px; box-shadow:none; padding:.5rem .8rem; }}
.stg .sys {{ font-family:"Figtree",sans-serif !important; font-size:.6rem; letter-spacing:.1em; }}
.stg .what {{ font-size:.8rem; font-weight:600; margin-top:0; color:var(--muted); }}
.stg .ms {{ font-size:1.15rem; margin-top:.1rem; }}
.runlabel {{ font-family:"Figtree",sans-serif !important; font-size:.8rem; font-weight:600;
  letter-spacing:0; color:var(--muted); margin:.7rem 0 -.3rem; }}
.verdict {{ border-radius:16px; box-shadow:none; padding:.75rem 1.1rem; margin:.6rem 0 .5rem;
  gap:1.6rem; }}
.verdict .word {{ font-size:clamp(1.7rem,2.8vw,2.4rem); font-weight:800; letter-spacing:-.03em; }}
.verdict .m {{ font-size:.6rem; }}
.verdict .m b {{ font-size:1.2rem; }}
.kpi-grid {{ gap:.5rem; margin:.1rem 0 .3rem; }}
.kpi {{ border-radius:12px; box-shadow:none; padding:.55rem .8rem; }}
.kpi .k {{ font-size:.58rem; }}
.kpi .v {{ font-size:1.15rem; margin-top:.05rem; }}
.kpi .x {{ font-size:.72rem; margin-top:0; line-height:1.3; }}
div[data-testid="stWidgetLabel"] p, div[data-testid="stWidgetLabel"] label,
.stTextInput input, .stNumberInput input, div[data-baseweb="select"] div,
.stCheckbox label p, div[data-testid="stPopoverBody"] p,
div[data-testid="stExpander"] summary p, div[data-testid="stPopover"] button p {{
  font-family:"Figtree",sans-serif !important; }}
div[data-testid="stWidgetLabel"] p {{ font-size:.8rem !important; font-weight:600 !important;
  color:var(--muted) !important; }}

@media (min-width:1000px) {{ .kpi-grid {{ grid-template-columns:repeat(6,minmax(0,1fr)); }} }}
div[data-testid="stPopover"] button {{ background:rgba(215,243,239,.7) !important;
  color:var(--teal) !important; border:1px solid rgba(31,160,139,.25) !important; }}
button[data-testid="stBaseButton-primaryFormSubmit"] {{
  background:linear-gradient(135deg,#081226 0%,#10203F 100%) !important; color:#fff !important;
  border:1px solid rgba(31,160,139,.35) !important; }}

/* ================= colour system v2 =================
   White surfaces, navy ink, and colour only where it means something:
   green approve, amber review, red block. Exasol blue stays the brand accent. */
:root {{ --ok:#0B6E4C; --ok-soft:#E6F4EE; --warn:#9A5800; --warn-soft:#FDF1E1;
  --no:#C8102E; --no-soft:#FBE9EC; --edge:#DFE5EE; --ink2:#0B1B34; }}

/* buttons: white with a navy hover; the one primary action stays navy */
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"],
div[data-testid="stPopover"] button, .stButton > button[kind="secondary"] {{
  background:#fff !important; color:var(--ink2) !important;
  border:1px solid var(--edge) !important; box-shadow:0 1px 2px rgba(11,27,52,.06) !important; }}
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-secondary"]:hover,
div[data-testid="stPopover"] button:hover {{ border-color:var(--ink2) !important; }}
div[data-testid="stHorizontalBlock"] button[data-testid="stBaseButton-primary"],
.stButton > button[kind="primary"] {{ background:var(--ink2) !important; color:#fff !important;
  border:1px solid var(--ink2) !important; }}
/* each preset carries the colour of the outcome it produces */
.st-key-fn button p::before, .st-key-fv button p::before, .st-key-ff button p::before {{
  content:""; display:inline-block; width:9px; height:9px; border-radius:50%;
  margin-right:.5rem; vertical-align:middle; }}
.st-key-fn button p::before {{ background:var(--ok); }}
.st-key-fv button p::before {{ background:#F59E0B; }}
.st-key-ff button p::before {{ background:#FF4D5E; }}

/* the verdict: a solid decision block, then the numbers */
.verdict.vbar {{ background:#fff !important; border:1px solid var(--edge) !important;
  border-left:0 !important; padding:0 !important; overflow:hidden; gap:1.8rem !important; }}
.verdict.vbar .vw {{ display:flex; align-items:center; gap:.7rem; align-self:stretch;
  padding:.85rem 1.4rem; color:#fff; }}
.verdict.vbar .vi {{ width:34px; height:34px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; background:rgba(255,255,255,.18); color:#fff; }}
.verdict.vbar .word {{ color:#fff !important; }}
.vbar.v-approve .vw {{ background:var(--ok); }}
.vbar.v-review .vw {{ background:#D97706; }}
.vbar.v-block .vw {{ background:var(--no); }}
.verdict.vbar .vp {{ margin-left:auto; margin-right:1.2rem; font-size:.72rem; color:var(--faint); }}

/* metric cards: white; a risky one gets a red rule, not a pink wash */
.kpi {{ background:#fff !important; border:1px solid var(--edge) !important; }}
.kpi.hot {{ background:#fff !important; border-left:3px solid var(--no) !important; }}
.kpi.hot .v {{ color:var(--no) !important; }}

/* pipeline rail: neutral, a green dot on each finished hop */
.stg, .stg.done {{ background:#fff !important; border-color:var(--edge) !important; }}
.stg.done .sys::before {{ content:""; display:inline-block; width:7px; height:7px;
  border-radius:50%; background:var(--ok); margin-right:.4rem; vertical-align:middle; }}
.stg.run {{ border-color:#F59E0B !important; background:#FFFBF3 !important; }}

/* insight and next best action */
.card {{ background:#fff; border:1px solid var(--edge); border-radius:16px;
  padding:.9rem 1.1rem; margin:.2rem 0 .6rem; height:100%; }}
.card-k {{ text-transform:uppercase; letter-spacing:.12em; font-size:.62rem; font-weight:800;
  color:#0072C6; }}
.card-k.bad {{ color:var(--no); }}
.card-t {{ font-weight:800; font-size:1.05rem; margin:.15rem 0 .6rem; color:var(--ink2); }}
.card-x {{ font-size:.72rem; color:var(--faint); margin-top:.5rem; }}
.dr {{ display:grid; grid-template-columns:minmax(0,1.3fr) minmax(0,1fr) 2.6rem; gap:.6rem;
  align-items:center; font-size:.86rem; margin:.28rem 0; }}
.dr-l {{ color:var(--ink2); }}
.dr-t {{ height:8px; border-radius:999px; background:#EEF2F7; overflow:hidden; }}
.dr-f {{ height:100%; border-radius:999px; background:linear-gradient(90deg,#FF7A85,var(--no)); }}
.dr-v {{ text-align:right; font-weight:800; color:var(--ink2); font-variant-numeric:tabular-nums; }}
.na {{ display:grid; grid-template-columns:1.4rem 2.1rem 1fr; gap:.6rem; align-items:center;
  padding:.45rem 0; border-top:1px solid #EEF2F7; }}
.na:first-of-type {{ border-top:0; }}
.na-n {{ font-weight:800; color:var(--no); font-size:.95rem; }}
.na-i {{ width:32px; height:32px; border-radius:50%; background:var(--no-soft); color:var(--no);
  display:flex; align-items:center; justify-content:center; }}
.na-t {{ font-weight:800; font-size:.9rem; color:var(--ink2); }}
.na-s {{ font-size:.78rem; color:var(--muted); line-height:1.35; }}

/* decision pills in the results table, same three colours */
.d-approve {{ background:var(--ok-soft) !important; color:var(--ok) !important; }}
.d-review {{ background:var(--warn-soft) !important; color:var(--warn) !important; }}
.d-block {{ background:var(--no) !important; color:#fff !important; }}
.restab tr.hot td {{ background:#FDF3F4 !important; }}
.restab tr.warn td {{ background:#FFF8EE !important; }}

.card.rev .dr-f {{ background:linear-gradient(90deg,#FBBF24,#D97706); }}
.card-k.warn {{ color:var(--warn); }}
.mflow {{ display:flex; flex-wrap:wrap; align-items:center; gap:.3rem; margin:-.2rem 0 .6rem; }}
.mf {{ font-size:.7rem; font-weight:700; color:var(--muted); background:#F1F4F9;
  border-radius:999px; padding:.12rem .55rem; }}
.mfa {{ color:var(--faint); font-size:.8rem; }}
.card .rv {{ grid-template-columns:1fr auto; margin:0; }}
</style>
"""

# Belt and braces: with no blank lines there is no boundary for a markdown parser
# to end the HTML block on, whatever rule it implements. The source above stays
# readable; only what is injected is collapsed.
CSS = "\n".join(line for line in _SHEET.splitlines() if line.strip())
