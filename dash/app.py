"""Loan Origination System, on dash-server (http://127.0.0.1:5100/apps/loan-origination by default, see config.env).

Six tabs, few words:
  1 Overview         the problem as one picture
  2 How it works     the journey of one application in six steps, and the three layers behind it, in plain words
  3 New application  upload the PDFs (or a sample), watch them read, verified and scored live, then review the edge case
                     on a checklist and sign (a second person signs above the first one's limit)
  4 LOS insights     every application received and its status, the rules that sent cases to a person, and what to
                     change in those rules (checked against 1.34M funded loans)
  5 Semantic layer   one vocabulary over every system; data contracts checked live on every application
  6 Audit trail      the append-only decision log, enforced by database privileges

The console holds no credentials and opens no database connection: everything goes through the LOS service
(service/, 127.0.0.1:LOS_PORT) as named operations. The service signs in as the login each job needs.
"""
import base64
import time
from datetime import datetime
from pathlib import Path

from flask import abort, send_file
from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update

import checklist as K
import how
import insights
import los
import los_settings
import story
from fmt import LABEL, esc, inr, pct
from page_css import PAGE_CSS
from theme import CSS as THEME_CSS

HERE = Path(__file__).resolve().parent
UPLOADS = Path(los_settings.UPLOADS)     # written by the LOS service; served read-only below
PACKS = {"karthik-raghunathan": ("Karthik Raghunathan", "₹12 L · salaried · Chennai"),
         "divya-ramesh": ("Divya Ramesh", "₹5 L · salaried · Bengaluru"),
         "ananya-krishnan": ("Ananya Krishnan", "₹6 L · not a bank customer · Pune")}
REVIEWERS = ["Priya Natarajan", "Arun Menon", "Lakshmi Iyer"]


def _css(s):
    return s.replace("<style>", "").replace("</style>", "")


APP_CSS = """
html, body { margin:0; }
body { font-family:"Figtree",sans-serif; color:var(--ink);
  background: radial-gradient(circle at top left, rgba(226,244,255,0.95), transparent 30%),
              radial-gradient(circle at top right, rgba(227,245,241,0.85), transparent 26%),
              linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 55%, #ffffff 100%); background-attachment:fixed; min-height:100vh; }
.page { padding:1.4rem 2.2rem 3rem; max-width:1700px; margin:0 auto; }
.md > p:empty { display:none; } .md p { margin:0; }
.tabbar { border-bottom:1px solid var(--line) !important; margin-bottom:.6rem; }
.tabbar .tab { background:transparent !important; border:0 !important; border-bottom:3px solid transparent !important; font-weight:600; font-size:.98rem;
  color:var(--muted) !important; padding:.55rem 0 !important; margin-right:1.8rem; width:auto !important; flex:0 0 auto !important; }
.tabbar .tab--selected { color:var(--bad) !important; border-bottom-color:var(--bad) !important; }
.btn { font-family:"Figtree",sans-serif; font-weight:700; font-size:.92rem; border-radius:12px; border:1px solid rgba(31,160,139,.35);
  background:linear-gradient(135deg,#081226 0%,#10203F 100%); color:#fff; padding:.6rem 1rem; cursor:pointer; text-align:left; }
.btn:hover { filter:brightness(1.18); } .btn.wide { width:100%; } .btn:disabled { opacity:.4; cursor:not-allowed; }
.btn.ghost { background:#fff; color:var(--ink2); border:1px solid var(--edge); }
.btn.go { background:linear-gradient(135deg,#0E6B5E 0%,#12796A 100%); border-color:#12796A; }
/* keyboard users must see where they are: never remove the focus ring without a replacement */
.btn:focus-visible, button:focus-visible, a:focus-visible, [role=tab]:focus-visible, .dash-input-container.inp:focus-within {
  outline:3px solid #0076AD; outline-offset:2px; }
.btn.sm { font-size:.82rem; padding:.42rem .8rem; border-radius:10px; }
.btn .s { display:block; font-weight:500; font-size:.76rem; opacity:.75; margin-top:.1rem; }
.cached { border-radius:10px; background:#FDF3F4; color:var(--no); font-size:.8rem; font-weight:700; padding:.35rem .6rem; margin-top:.5rem; }
.hint { font-size:.84rem; color:var(--muted); line-height:1.45; }
details.eng { border-radius:14px; border:1px solid var(--edge); background:#fff; margin:.8rem 0; padding:.2rem .9rem; }
details.eng > summary { cursor:pointer; font-weight:700; font-size:.88rem; color:var(--ink2); padding:.5rem 0; }
pre.sql { font-family:"JetBrains Mono",monospace; font-size:.72rem; line-height:1.5; background:#0B1730; color:#DCE6F5; border-radius:12px;
  padding:.7rem .9rem; white-space:pre-wrap; word-break:break-word; margin:.2rem 0 .6rem; max-height:24rem; overflow:auto; }

/* ---- tab 2: start + live steps */
.nt { display:grid; grid-template-columns:minmax(0,22rem) minmax(0,1fr); gap:1.6rem; align-items:start; margin-top:.4rem; }
.startc { border-radius:20px; border:1px solid var(--edge); background:#fff; padding:1rem 1.1rem; box-shadow:var(--shadow); display:grid; gap:.55rem; }
.drop { border:2px dashed #9ED9CE; border-radius:16px; background:#F2FBF9; padding:1.1rem .8rem; text-align:center; cursor:pointer; }
.drop:hover { background:#E3F5F1; } .drop .t { font-weight:900; color:#12796A; font-size:1rem; } .drop .d { font-size:.8rem; color:var(--muted); margin-top:.2rem; }
.or { font-size:.7rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:var(--faint); text-align:center; margin:.2rem 0 -.1rem; }
.stp { list-style:none; margin:0; padding:0; border-radius:20px; border:1px solid var(--edge); background:#fff; box-shadow:var(--shadow); }
.stp > li { display:grid; grid-template-columns:2.2rem minmax(0,1fr) 4.5rem; gap:.7rem; align-items:start; padding:.75rem 1rem; border-bottom:1px solid #EEF2F7; }
.stp > li:last-child { border-bottom:0; }
.stp .ic { width:1.9rem; height:1.9rem; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:900; font-size:.85rem;
  background:#EEF2F7; color:#5A6679; }
.stp li.done .ic { background:#1FA08B; color:#fff; } .stp li.fail .ic { background:#C8102E; color:#fff; }
.stp li.run .ic { background:#fff; border:3px solid #E3F5F1; border-top-color:#1FA08B; animation:spin .8s linear infinite; color:transparent; }
@keyframes spin { to { transform:rotate(360deg); } }
.stp .t { font-weight:800; color:var(--ink2); font-size:1rem; } .stp li.wait .t { color:#5A6679; }
.stp .d { font-size:.84rem; color:var(--muted); margin-top:.15rem; line-height:1.45; } .stp .d b { color:var(--ink2); }
.stp .s { text-align:right; font-variant-numeric:tabular-nums; font-weight:800; color:var(--teal-ink); font-size:.86rem; }
.thumbs { display:flex; gap:.6rem; flex-wrap:wrap; margin-top:.4rem; }
.thumbs figure { margin:0; text-align:center; } .thumbs img { width:84px; height:110px; object-fit:cover; object-position:top; border-radius:8px; border:1px solid var(--edge); background:#fff; }
.thumbs figcaption { font-size:.68rem; font-weight:800; color:var(--ink2); margin-top:.15rem; max-width:84px; }
.thumbs figcaption.x { color:#C8102E; }
/* step 3: three lanes, key -> system -> match */
.lanes { display:grid; gap:.45rem; margin-top:.5rem; }
.ln { display:grid; grid-template-columns:minmax(0,1.05fr) 2.2rem minmax(0,.9fr) 2.2rem minmax(0,1.5fr); align-items:center; }
.ln .lk { border-radius:12px; border:1px dashed #C9D3E0; background:#FAFBFD; padding:.35rem .6rem; }
.ln .lk small, .ln .ls small, .ln .lr small { display:block; font-size:.68rem; color:var(--faint); line-height:1.3; }
.ln .lk code { font-family:'JetBrains Mono',monospace; font-size:.8rem; color:var(--ink2); font-weight:700; background:none; padding:0; overflow-wrap:anywhere; }
.ln .ls { border-radius:12px; padding:.35rem .6rem; color:#fff; } .ln .ls b { font-size:.86rem; } .ln .ls small { color:rgba(255,255,255,.82); }
.ln.mg .ls { background:#0076AD; } .ln.pg .ls { background:#C56A00; } .ln.bu .ls { background:#7A4FD6; }
.ln .ar { position:relative; height:2px; margin:0 .25rem; background:#C9D3E0; overflow:visible; }
.ln .ar i { position:absolute; inset:0; background:linear-gradient(90deg,transparent 0,#1FA08B 50%,transparent 100%); background-size:200% 100%; animation:flow 1.6s linear 2; }
.ln .ar::after { content:""; position:absolute; right:-2px; top:-4px; border:5px solid transparent; border-left:7px solid #9FB0C4; border-right:0; }
@keyframes flow { from { background-position:100% 0; } to { background-position:-100% 0; } }
@media (prefers-reduced-motion: reduce) { .ln .ar i { animation:none; } }
.ln .lr { display:flex; gap:.5rem; align-items:center; border-radius:12px; border:1px solid #CDEBE4; background:#F2FBF8; padding:.35rem .6rem; }
.ln .lr b { font-size:.86rem; color:var(--ink2); } .ln .lr.no { border-color:#F3C2C8; background:#FFF7F8; }
.tick { flex:0 0 1.3rem; height:1.3rem; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:.72rem; font-weight:900; color:#fff; background:#1FA08B; }
.fz.no .tick, .lr.no .tick { background:#D98A00; }
/* step 4: semantic fusion */
.fus { margin-top:.7rem; border-radius:16px; border:1px solid var(--edge); background:linear-gradient(180deg,#F7FBFF 0%,#fff 60%); padding:.75rem .85rem; }
.fus .fk { font-size:.64rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; color:#12796A; }
.fus .ft { font-size:1.05rem; font-weight:900; color:var(--ink2); margin-top:.1rem; }
.fus .uid { font-family:'JetBrains Mono',monospace; background:#0B1B34; color:#fff; border-radius:8px; padding:.08rem .5rem; font-size:.9rem; }
.fus .fs { font-size:.8rem; color:var(--muted); margin-top:.25rem; max-width:75ch; } .fus .fs code { font-size:.76rem; }
.chain { display:flex; flex-wrap:wrap; align-items:center; gap:.3rem; margin:.6rem 0 .5rem; }
.kc { display:inline-flex; flex-direction:column; border-radius:10px; padding:.25rem .55rem; font-family:'JetBrains Mono',monospace; font-size:.76rem; font-weight:700; color:var(--ink2); border:1px solid; }
.kc small { font-family:inherit; font-size:.6rem; font-weight:500; color:var(--faint); }
.kc.mg { border-color:#9FD0EA; background:#EEF8FD; } .kc.pg { border-color:#F1C48D; background:#FFF6EC; } .kc.bu { border-color:#C9B7F2; background:#F5F1FE; }
.lk2 { font-style:normal; color:#9FB0C4; font-weight:900; }
.fwrap { overflow-x:auto; }
table.ftab { width:100%; border-collapse:collapse; font-size:.8rem; }
table.ftab th { text-align:left; font-size:.62rem; letter-spacing:.08em; text-transform:uppercase; color:var(--faint); padding:.35rem .4rem; white-space:nowrap; }
table.ftab tr + tr th { font-size:.8rem; letter-spacing:0; text-transform:none; color:var(--ink2); font-weight:800; white-space:normal; }
table.ftab td, table.ftab tr + tr th { border-top:1px solid #EEF2F7; padding:.35rem .4rem; vertical-align:top; }
.dot { display:inline-block; width:.55rem; height:.55rem; border-radius:50%; margin-right:.3rem; } .dot.mg { background:#0076AD; } .dot.pg { background:#C56A00; } .dot.bu { background:#7A4FD6; }
.fv { display:flex; flex-direction:column; border-left:3px solid; padding:.05rem .45rem; margin:.1rem 0; }
.fv code { font-family:'JetBrains Mono',monospace; font-size:.66rem; color:var(--faint); background:none; padding:0; } .fv b { color:var(--ink2); font-weight:700; }
.fv.mg { border-color:#0076AD; } .fv.pg { border-color:#C56A00; } .fv.bu { border-color:#7A4FD6; } .fv.none { border:0; color:var(--faint); }
.fz { display:flex; gap:.45rem; align-items:flex-start; } .fz b { color:var(--ink2); } .fz small { display:block; font-size:.68rem; color:var(--faint); }
/* step 4 summary: sources -> one query -> contracts -> policy -> result */
.fq { display:flex; align-items:center; gap:.45rem; flex-wrap:wrap; margin-top:.35rem; }
.fqs { display:grid; gap:.25rem; }
.fs1 { display:flex; align-items:center; gap:.35rem; border-radius:9px; padding:.18rem .5rem; color:#fff; font-size:.76rem; font-weight:800; }
.fs1 small { font-weight:500; opacity:.85; font-size:.64rem; margin-left:auto; padding-left:.4rem; }
.fs1 svg { width:14px; height:14px; } .fs1.mg { background:#0076AD; } .fs1.pg { background:#C56A00; } .fs1.bu { background:#7A4FD6; }
.fs1 .mb { display:inline-flex; align-items:flex-end; gap:1px; height:13px; } .fs1 .mb i { display:block; width:3px; background:#fff; border-radius:1px; }
svg.fqj { width:34px; height:72px; }
.fqq, .fqc, .fqo { display:flex; flex-direction:column; justify-content:center; border-radius:12px; padding:.35rem .65rem; font-size:.84rem; font-weight:900; line-height:1.15; }
.fqq small, .fqc small { font-size:.66rem; font-weight:600; opacity:.85; }
.fqq { background:#0B3B4A; color:#fff; } .fqc { background:#E3F5F1; color:#12796A; border:1px solid #9ED9CE; }
.fqc.bad { background:#FDE7EA; color:#B00D27; border-color:#F3C2C8; }
.fqa { color:#9FB0C4; font-size:1rem; }
.fqr { display:flex; gap:.25rem; } .fqr em { font-style:normal; font-size:.72rem; font-weight:800; color:var(--ink2); background:#F1F4F9; border:1px solid var(--edge); border-radius:999px; padding:.18rem .5rem; }
.fqo { flex-direction:row; align-items:baseline; gap:.25rem; background:#0B1B34; color:#fff; } .stp .d .fqo b, .fqo b { font-size:1rem; color:#fff; }
.fqh { display:flex; align-items:center; gap:.3rem; } .fqh svg { width:15px; height:15px; }
.fqo small { font-size:.62rem; font-weight:600; opacity:.75; margin-right:.35rem; }
/* step 4, compact: three systems -> one applicant card */
.fus2 { margin-top:.6rem; border-radius:16px; border:1px solid var(--edge); background:linear-gradient(180deg,#F7FBFF 0%,#fff 70%); padding:.7rem .85rem; }
.fus2 > .fk { font-size:.62rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; color:#12796A; margin-bottom:.4rem; }
.hub { display:grid; grid-template-columns:minmax(0,9.5rem) 3.2rem minmax(0,1fr); align-items:stretch; }
.hsrc { display:grid; gap:.35rem; align-content:center; }
.hs { border-radius:10px; padding:.3rem .6rem; color:#fff; } .hs b { font-size:.82rem; display:block; } .hs small { font-size:.68rem; opacity:.85; font-family:'JetBrains Mono',monospace; }
.hs.mg { background:#0076AD; } .hs.pg { background:#C56A00; } .hs.bu { background:#7A4FD6; }
svg.hin { width:100%; height:100%; min-height:7rem; }
.card360 { border-radius:14px; border:2px solid #0B1B34; background:#fff; padding:.55rem .7rem; }
.ch3 { display:flex; flex-wrap:wrap; align-items:center; gap:.45rem; margin-bottom:.45rem; }
.ch3 > span:first-child { font-size:.62rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:var(--faint); }
.ch3 .uid { font-family:'JetBrains Mono',monospace; background:#0B1B34; color:#fff; border-radius:8px; padding:.05rem .45rem; font-size:.84rem; }
.ch3 b { font-size:1rem; color:var(--ink2); } .ch3 em { font-style:normal; font-size:.78rem; color:#12796A; font-weight:700; margin-left:auto; }
.ftiles { display:grid; grid-template-columns:repeat(auto-fill,minmax(8.6rem,1fr)); gap:.35rem; }
.ftile { border-radius:10px; border:1px solid #CDEBE4; background:#F6FCFA; padding:.3rem .45rem; min-width:0; }
.ftile.no { border-color:#F5D08A; background:#FFF8EA; }
.ftop { display:flex; align-items:center; gap:.3rem; } .ftop b { font-size:.74rem; color:var(--ink2); }
.ftop .tick { flex:0 0 1rem; height:1rem; font-size:.6rem; } .ftile.no .tick { background:#D98A00; }
.sd { margin-left:auto; display:flex; gap:2px; } .sd i { width:.42rem; height:.42rem; border-radius:50%; display:block; }
.sd i.mg { background:#0076AD; } .sd i.pg { background:#C56A00; } .sd i.bu { background:#7A4FD6; }
.fval { font-family:'JetBrains Mono',monospace; font-size:.72rem; font-weight:700; color:var(--ink2); margin-top:.15rem; overflow-wrap:anywhere; line-height:1.3; }
.ftile.no .fval { color:#8A5300; }
.ln .lr.nocust { border-color:#D6DEE8; background:#F6F8FB; } .ln .lr.nocust .tick { background:#9FB0C4; }
.fs1.nocust { background:#E9EEF4; color:#5B6B80; } .hs.nocust { background:#B9C3CF; }
.fqr em.ml { background:#5B33C7; color:#fff; border-color:#5B33C7; box-shadow:0 0 0 3px rgba(91,51,199,.18); }
.cbar { display:flex; flex-wrap:wrap; align-items:center; gap:.5rem; margin-top:.55rem; font-size:.8rem; }
.cbar .cl { font-size:.62rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:#12796A; }
.cbar .sqs { display:inline-flex; gap:3px; } .cbar .sqs i { width:.8rem; height:.8rem; border-radius:3px; display:block; cursor:help; }
.cbar .sqs i.ok { background:#1FA08B; } .cbar .sqs i.warn { background:#F0B44E; } .cbar .sqs i.crit { background:#C8102E; }
.cbar b { color:var(--ink2); } .cbar .r { color:#B00D27; font-weight:800; } .cbar .a { color:#8A5300; font-weight:700; }
details.fmore { margin-top:.5rem; } details.fmore > summary { cursor:pointer; font-size:.8rem; font-weight:700; color:#12796A; }
details.fmore .fus { margin-top:.4rem; }
@media (max-width:1100px) { .hub { grid-template-columns:1fr; } svg.hin { display:none; } .hsrc { grid-auto-flow:column; } }
/* semantic labels + contracts */
code.sv { display:block; font-family:'JetBrains Mono',monospace; font-size:.6rem; font-weight:500; color:#12796A; background:none; padding:0; margin-top:.15rem; white-space:nowrap; }
.dot.xs { background:#0B1B34; }
.ctr { margin-top:.6rem; border-top:1px dashed #D6DEE8; padding-top:.55rem; }
.ctr .fk { font-size:.62rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; color:#12796A; }
.ctr .ch { font-size:.9rem; font-weight:800; color:var(--ink2); margin:.1rem 0 .35rem; } .ctr .ch .r { color:#B00D27; } .ctr .ch .a { color:#8A5300; }
.cgs { display:flex; flex-wrap:wrap; gap:.35rem 1rem; } .cg { display:flex; align-items:center; gap:.3rem; flex-wrap:wrap; font-size:.78rem; }
.cg > b { color:var(--ink2); margin-right:.1rem; }
.cc { font-family:'JetBrains Mono',monospace; font-size:.68rem; font-weight:700; border-radius:999px; padding:.08rem .45rem; cursor:help; }
.cc.ok { background:#E3F5F1; color:#12796A; } .cc.warn { background:#FEF3DC; color:#8A5300; } .cc.crit { background:#C8102E; color:#fff; }
.cn { font-size:.78rem; margin-top:.3rem; border-radius:8px; padding:.3rem .55rem; } .cn span { font-family:'JetBrains Mono',monospace; font-size:.72rem; }
.cn.warn { background:#FFF8EA; color:#6B4300; } .cn.crit { background:#FDECEF; color:#8E0A20; }
.lin { display:flex; flex-wrap:wrap; align-items:center; gap:.4rem; margin:.5rem 0 .9rem; }
.lin i { font-style:normal; color:#9FB0C4; font-weight:900; font-size:1.1rem; }
.ls2 { display:inline-flex; flex-direction:column; border-radius:12px; padding:.35rem .7rem; font-weight:800; font-size:.86rem; color:#fff; }
.ls2 small { font-weight:500; font-size:.66rem; opacity:.85; }
.ls2.mg { background:#0076AD; } .ls2.pg { background:#C56A00; } .ls2.bu { background:#7A4FD6; } .ls2.sem { background:#12796A; }
.ls2.con { background:#0B1B34; } .ls2.dec { background:#fff; color:var(--ink2); border:1px solid var(--edge); } .ls2.dec small { color:var(--muted); }
table.tbl.sem td small { display:block; font-size:.72rem; color:var(--muted); margin-top:.1rem; line-height:1.35; }
table.tbl.sem td.nil { color:#C3CCD8; } table.tbl.sem td.ub { font-size:.78rem; color:var(--muted); }
code.svb { font-family:'JetBrains Mono',monospace; font-size:.72rem; color:#0B5E52; background:#E3F5F1; border-radius:6px; padding:.1rem .35rem; white-space:nowrap; }
table.tbl.sem .fv { border-left:3px solid; padding:.05rem .45rem; display:block; } table.tbl.sem .fv b { font-family:'JetBrains Mono',monospace; font-size:.72rem; font-weight:600; }
.sev { font-size:.64rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; border-radius:999px; padding:.1rem .5rem; }
.sev.critical { background:#FDE7EA; color:#B00D27; } .sev.warning { background:#FEF3DC; color:#8A5300; }
ul.cl1 { list-style:none; margin:.3rem 0 0; padding:0; display:grid; gap:.2rem; }
ul.cl1 li { display:grid; grid-template-columns:1.2rem 3rem minmax(0,1fr) minmax(0,1fr); gap:.4rem; font-size:.8rem; align-items:baseline; }
ul.cl1 li i { font-style:normal; font-weight:900; } ul.cl1 li.ok i { color:#12796A; } ul.cl1 li.warn i { color:#8A5300; } ul.cl1 li.crit i { color:#B00D27; }
ul.cl1 li.crit span, ul.cl1 li.crit b { color:#B00D27; } ul.cl1 li code { font-size:.7rem; color:var(--muted); background:none; padding:0; }
.cst { font-weight:800; } .cst.ok { color:#12796A; } .cst.warn { color:#8A5300; } .cst.crit { color:#B00D27; }
@media (max-width:1100px) { .ln { grid-template-columns:1fr; } .ln .ar { height:.6rem; width:2px; margin:.1rem auto; } .ln .ar::after { display:none; } }
.rd { display:grid; grid-template-columns:minmax(0,10rem) minmax(0,1fr) 4rem; gap:.5rem; font-size:.82rem; padding:.15rem 0; }
.rd b { color:var(--ink2); } .rd span { color:var(--muted); } .rd i { font-style:normal; text-align:right; color:var(--faint); font-variant-numeric:tabular-nums; }
.src3 { display:flex; flex-wrap:wrap; gap:.35rem .5rem; margin-top:.3rem; font-size:.82rem; }
.src3 span { border-radius:8px; padding:.15rem .5rem; background:#F1F4F9; color:var(--ink2); }
.total { margin-top:.6rem; font-size:.84rem; color:var(--muted); text-align:right; } .total b { color:var(--teal-ink); font-size:1rem; }

/* ---- the case: banner, checklist, decision */
.banner { border-radius:20px; padding:1rem 1.2rem; margin:1.4rem 0 .8rem; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:1rem; align-items:center; }
.banner.refer { background:#FFFBF2; border:1px solid #F5D9A6; border-left:8px solid #F59E0B; }
.banner.approve { background:#F2FBF8; border:1px solid #CDEBE4; border-left:8px solid #1FA08B; }
.banner.decline { background:#FFF7F8; border:1px solid #F3C2C8; border-left:8px solid #C8102E; }
.banner .k { font-size:.66rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; color:var(--faint); }
.banner .t { font-size:1.45rem; font-weight:900; color:var(--ink2); margin:.1rem 0; line-height:1.2; }
.banner .m { font-size:.9rem; color:var(--muted); }
.kpis { display:flex; gap:.5rem; flex-wrap:wrap; }
.kp { border-radius:12px; background:#fff; border:1px solid var(--edge); padding:.4rem .7rem; text-align:center; min-width:5.2rem; }
.kp .v { font-size:1.15rem; font-weight:900; color:var(--ink2); font-variant-numeric:tabular-nums; } .kp .l { font-size:.68rem; color:var(--faint); font-weight:700; }
.kp.new { border-color:#8B5CF6; background:#FAF8FF; } .kp.new .v { color:#5B33C7; }
.ckh { display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:1rem; align-items:center; margin:.6rem 0 .5rem; }
.ckh .t { font-size:1.2rem; font-weight:900; color:var(--ink2); }
.ckh .bar { height:10px; border-radius:6px; background:#EEF2F7; overflow:hidden; display:flex; }
.ckh .bar i { display:block; height:100%; } .ckh .bar .a { background:#1FA08B; } .ckh .bar .r { background:#8B5CF6; } .ckh .bar .p { background:#F59E0B; }
.ckh .n { font-size:.84rem; color:var(--muted); white-space:nowrap; } .ckh .n b { color:var(--ink2); }
.ck { border-radius:18px; border:1px solid var(--edge); background:#fff; padding:.75rem 1rem .75rem .8rem; margin:.5rem 0; display:grid;
  grid-template-columns:2.2rem minmax(0,1fr); gap:.4rem .8rem; box-shadow:0 6px 18px rgba(8,18,38,.04); }
.ck .ic { width:1.9rem; height:1.9rem; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:900; color:#fff; font-size:.95rem; }
.ck.auto .ic { background:#1FA08B; } .ck.review .ic { background:#F59E0B; } .ck.decline .ic { background:#C8102E; }
.ck.sign .ic { background:#8B5CF6; } .ck.done .ic { background:#8B5CF6; }
.ck.review { border-color:#F5D9A6; background:#FFFDF8; } .ck.decline { border-color:#F3C2C8; } .ck.done { border-color:#D9CCFB; background:#FCFBFF; }
.ck .hd { display:flex; gap:.6rem; align-items:baseline; flex-wrap:wrap; }
.ck .ti { font-weight:900; font-size:1.05rem; color:var(--ink2); }
.ck .chip { font-size:.66rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; border-radius:999px; padding:.12rem .55rem; }
.ck.auto .chip { background:#E3F5F1; color:#12796A; } .ck.review .chip { background:#FEF3DC; color:#8A5300; } .ck.decline .chip { background:#FDE7EA; color:#B00D27; }
.ck.sign .chip, .ck.done .chip { background:#EFEAFE; color:#5B33C7; }
.ck .fi { font-size:.92rem; color:var(--ink2); margin-top:.15rem; line-height:1.45; }
.ck .rl { display:flex; flex-wrap:wrap; gap:.35rem; margin-top:.35rem; }
.ck .rl span { font-size:.76rem; border-radius:8px; padding:.15rem .5rem; background:#FEF3DC; color:#6B4300; } .ck .rl b { font-family:'JetBrains Mono',monospace; margin-right:.3rem; }
.ck details { margin-top:.35rem; } .ck details > summary { cursor:pointer; font-size:.78rem; font-weight:800; color:var(--teal-ink); letter-spacing:.02em; }
.tree { list-style:none; margin:.35rem 0 .2rem .35rem; padding:0 0 0 1.1rem; border-left:2px solid #DDE4EE; }
.tree > li { position:relative; padding:.35rem 0 .35rem .2rem; font-size:.86rem; color:var(--ink2); }
.tree > li::before { content:""; position:absolute; left:-1.1rem; top:.95rem; width:.9rem; border-top:2px solid #DDE4EE; }
.tree a { color:#0076AD; font-weight:800; text-decoration:none; } .tree a:hover { text-decoration:underline; }
.tree .mt { font-size:.76rem; color:var(--faint); }
.src { display:inline-block; font-size:.6rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; border-radius:6px; padding:.12rem .4rem; margin-right:.45rem; vertical-align:1px; }
.src.doc { background:#E2F4FF; color:#0076AD; } .src.db { background:#FFF4E5; color:#9A4A00; } .src.ext { background:#EFEAFE; color:#5B33C7; } .src.exa { background:#E3F5F1; color:#12796A; }
ul.kv { list-style:none; margin:.25rem 0 0 1.4rem; padding:0; display:grid; grid-template-columns:repeat(auto-fill,minmax(14rem,1fr)); gap:.1rem 1.2rem; }
ul.kv li { display:flex; justify-content:space-between; gap:.6rem; border-bottom:1px dashed #EEF2F7; padding:.12rem 0; font-size:.82rem; }
ul.kv li span { color:var(--muted); } ul.kv li b { color:var(--ink2); font-variant-numeric:tabular-nums; text-align:right; }
ul.kv li.bad span, ul.kv li.bad b { color:#B00D27; font-weight:800; }
.mono { font-family:'JetBrains Mono',monospace; font-size:.74rem; color:var(--muted); margin:.2rem 0 0 1.4rem; }
.sbars { display:flex; gap:.45rem; align-items:flex-end; height:5.4rem; margin:.4rem 0 .1rem 1.4rem; }
.sb { width:3.4rem; height:100%; display:flex; flex-direction:column; justify-content:flex-end; align-items:center; }
.sb i { display:block; width:100%; background:#E8A45A; border-radius:6px 6px 0 0; } .sb.hi i { background:#C8102E; }
.sb b { font-size:.68rem; color:var(--ink2); margin-top:.15rem; } .sb span { font-size:.66rem; color:var(--faint); }
.foir { display:grid; grid-template-columns:minmax(0,1fr) 3.6rem 4rem; gap:.6rem; align-items:center; margin:.4rem 0 .2rem 1.4rem; }
.foir .ft { position:relative; height:16px; border-radius:8px; background:#EEF2F7; } .foir .ft i { display:block; height:100%; border-radius:8px; background:#1FA08B; }
.foir .ft i.hi { background:#F59E0B; } .foir .ft s { position:absolute; top:-5px; bottom:-5px; border-left:2px dashed #081226; }
.foir b { font-weight:900; text-align:right; } .foir span { font-size:.76rem; color:var(--faint); }
.rv { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr) auto; gap:.6rem; align-items:end; margin-top:.5rem; border-radius:14px;
  background:#FFF8EA; border:1px solid #F5D9A6; padding:.6rem .7rem; }
.rv .lb { font-size:.7rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:#8A5300; margin-bottom:.25rem; }
.rv .radio label { display:block; font-size:.85rem; margin:.1rem 0; cursor:pointer; } .rv .radio input { margin-right:.4rem; }
.inp { font-family:"Figtree",sans-serif; font-size:.9rem; border-radius:10px; border:1px solid var(--edge); padding:.5rem .7rem; background:#fff; width:100%; box-sizing:border-box; }
.radio .dash-options-list-option { display:flex !important; flex-direction:row !important; align-items:center; gap:.45rem; font-size:.86rem; margin:.12rem 0; cursor:pointer; width:auto !important; }
.radio .dash-options-list-option-wrapper { display:inline-flex !important; width:auto !important; } .radio .dash-options-list-option-text { display:inline !important; width:auto !important; }
.radio input { margin:0; }
.dash-input-container.inp { padding:0; } .dash-input-container.inp input { border:0; outline:none; width:100%; box-sizing:border-box;
  font:inherit; background:transparent; padding:.5rem .7rem; }
.ann { margin-top:.45rem; border-radius:12px; background:#F6F3FF; border:1px solid #D9CCFB; padding:.45rem .7rem; font-size:.86rem; color:#3F2A8C; line-height:1.45; }
.ann .rs { margin-top:.3rem; font-size:.84rem; color:var(--ink2); } .ann .rs b { color:#5B33C7; }
.dp { border-radius:20px; border:2px solid #0B1B34; background:#fff; padding:1rem 1.1rem; margin-top:1rem; box-shadow:var(--shadow); }
.dp.lock { border:2px dashed #C9D3E0; color:var(--muted); box-shadow:none; }
.dp .t { font-size:1.15rem; font-weight:900; color:var(--ink2); margin-bottom:.5rem; }
.dpg { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,10rem) minmax(0,1.3fr) auto; gap:.8rem; align-items:end; }
.dpg .lb { font-size:.7rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:var(--faint); margin-bottom:.25rem; }
.dpg .radio label { display:block; font-size:.88rem; margin:.1rem 0; cursor:pointer; } .dpg .radio input { margin-right:.4rem; }
.signed { border-radius:16px; background:linear-gradient(135deg,#081226 0%,#12796A 100%); color:#fff; padding:1rem 1.2rem; margin-top:1rem; }
.signed .t { font-size:1.25rem; font-weight:900; } .signed .s { font-size:.9rem; opacity:.9; margin-top:.3rem; line-height:1.5; }
.signed.wait { background:linear-gradient(135deg,#3B2A7A 0%,#8B5CF6 100%); }
.refused { border-radius:12px; border:1px solid #F3C2C8; background:#FFF7F8; padding:.6rem .8rem; font-family:'JetBrains Mono',monospace; font-size:.8rem; color:#B00D27; margin-top:.5rem; }
.tb { display:flex; align-items:center; gap:.6rem; justify-content:flex-end; margin-top:1rem; font-size:.84rem; color:var(--muted); }
.tb .Select-control, .tb .dash-dropdown { min-width:15rem; }

/* ---- tab 3 / 4 */
.ringc { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; margin:.6rem 0; }
.ringc .c { border-radius:16px; border:1px solid #F3C2C8; background:#FFF7F8; padding:.7rem .9rem; }
.ringc .c .h { font-weight:900; color:#B00D27; font-size:1rem; } .ringc .c .d { font-size:.86rem; color:var(--ink2); margin-top:.25rem; line-height:1.45; }
.ringc .c .m { font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--muted); margin-top:.3rem; }
.big3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; margin:.6rem 0; }
.big3 .b { border-radius:16px; border:1px solid var(--edge); background:#fff; padding:.7rem .95rem; } .big3 .b .v { font-size:1.7rem; font-weight:900; color:var(--ink2); }
.big3 .b.bad .v { color:#C8102E; } .big3 .b .l { font-size:.84rem; color:var(--muted); }
table.tbl { width:100%; border-collapse:collapse; font-size:.84rem; background:#fff; border-radius:14px; overflow:hidden; }
table.tbl th { text-align:left; font-size:.64rem; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); padding:.45rem .6rem; background:#F6F9FC; }
table.tbl td { padding:.4rem .6rem; border-top:1px solid #EEF2F7; color:var(--ink2); vertical-align:top; } table.tbl td.n { text-align:right; font-variant-numeric:tabular-nums; }
.tblw { border-radius:14px; border:1px solid var(--edge); overflow:auto; max-height:26rem; }
.sim { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:1rem; align-items:center; border-radius:18px; border:1px solid var(--edge); background:#fff; padding:.9rem 1.1rem; }
.sim .lb { font-size:.9rem; font-weight:800; color:var(--ink2); margin-bottom:.3rem; }
.vbar { display:grid; grid-template-columns:12rem minmax(0,1fr) 6rem; gap:.7rem; align-items:center; margin:.4rem 0; font-size:.9rem; }
.vbar .vt { height:26px; border-radius:8px; background:#F1F4F9; } .vbar .vt i { display:block; height:100%; border-radius:8px; }
.vbar b { text-align:right; font-variant-numeric:tabular-nums; }
.verdict2 { border-radius:16px; padding:.9rem 1.1rem; margin:.7rem 0; color:#fff; background:linear-gradient(135deg,#081226 0%,#12796A 100%); }
.verdict2.warn { background:linear-gradient(135deg,#081226 0%,#8A5300 100%); }
.verdict2 .t { font-size:1.3rem; font-weight:900; } .verdict2 .s { font-size:.9rem; opacity:.92; margin-top:.3rem; line-height:1.45; }
.cmpt { width:100%; border-collapse:collapse; font-size:.92rem; margin:.4rem 0; background:#fff; }
.cmpt th { text-align:right; font-size:.64rem; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); padding:.35rem .5rem; }
.cmpt th:first-child, .cmpt td:first-child { text-align:left; } .cmpt td { text-align:right; padding:.4rem .5rem; border-top:1px solid #EEF2F7; font-variant-numeric:tabular-nums; }
.cmpt td.up { color:#12796A; font-weight:900; } .cmpt td.dn { color:#B00D27; font-weight:900; }
.ok4 { border-radius:12px; border:1px solid #CDEBE4; background:#F2FBF8; padding:.6rem .8rem; font-size:.9rem; color:#12796A; font-weight:700; margin-top:.5rem; }
.two { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:1.6rem; align-items:start; }
@media (max-width:1100px) { .nt, .two, .dpg, .rv { grid-template-columns:1fr; } .page { padding:1rem; } .ringc, .big3 { grid-template-columns:1fr; } }
"""

STYLE = _css(THEME_CSS) + _css(PAGE_CSS) + story.CSS + how.CSS + insights.CSS + APP_CSS
# All CSS inline: dash-server loads app.py under a synthetic module name, and an assets/ stylesheet is easy to lose.
INDEX = ("<!DOCTYPE html><html lang=\"en\"><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}<style>" + STYLE
         + "</style></head><body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>")


def H(fragment, **kw):
    """Raw HTML as one Markdown block: no blank lines and no indentation, so nothing becomes markdown."""
    text = "\n".join(l.strip() for l in str(fragment).splitlines() if l.strip())
    return dcc.Markdown(text, dangerously_allow_html=True, className="md", **kw)


def _memo(ttl):
    store = {}

    def deco(fn):
        def wrap(*a):
            hit = store.get(a)
            if hit and time.time() - hit[0] < ttl:
                return hit[1]
            val = fn(*a)
            store[a] = (time.time(), val)
            return val
        wrap.clear = store.clear
        return wrap
    return deco


@_memo(30)
def health():
    try:
        return dict(los.call("health", timeout=20), los=True)
    except los.Down:
        return {"exa": False, "pg": False, "mongo": False, "los": False}


def down(e):
    return H(f'<div class="cached">{esc(e)}</div>')


def _logo():
    b64 = base64.b64encode((HERE / "assets" / "exasol_logo_dark.svg").read_bytes()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" alt="Exasol" style="height:26px;width:auto;max-width:104px;display:block;"/>'


def hero(h):
    pill = lambda ok, t: f'<span class="hs-pill{"" if ok else " down"}">{t}</span>'  # noqa: E731
    return (f'<div class="hero-slim"><div class="hs-t">Loan Origination System'
            f'<span>Upload an application. Exasol reads, verifies and scores it live across every system, and sends only the edge cases to a human in the loop.</span></div>'
            f'<div class="hs-m">{pill(h.get("los", True), "LOS service")}{pill(h["exa"], "Exasol")}{pill(h["pg"], "Core banking")}{pill(h["mongo"], "Document store")}{pill(True, "Amazon Textract")}</div></div>')


# ------------------------------------------------------------------ tab 2: the live steps
def _norm(kind, v):
    """One vocabulary for comparing values that each system writes its own way."""
    if v in (None, ""):
        return None
    v = str(v).strip()
    if kind == "date":
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(v[:10], fmt).date()
            except ValueError:
                pass
        return v
    if kind == "mobile":
        return "".join(ch for ch in v if ch.isdigit())[-10:]
    return " ".join(v.upper().split())


def store_viz(job):
    """Step 3 as three lanes: the key each system is reached by, the system, what it matched."""
    f, cu, bu = job.get("form") or {}, job.get("customer") or {}, job.get("bureau") or {}
    n = len([g for g in job["docs"] if g.get("fields")])
    ids = ", ".join(esc(d[-1]) for d in job.get("doc_ids") or [])
    lanes = [
        ("mg", "from the uploads", f'{esc(job["app"])} + {n} PDFs', "User application", "MongoDB &middot; written",
         True, f'<b>{n} documents</b><small>applications &larr; {esc(job["app"])} &middot; documents &larr; {ids or "F, P, I, E"}</small>'),
        ("pg", "salary account, from the form", esc(f.get("account")), "Core banking", "Postgres &middot; looked up live",
         True if cu else None, f'<b>{esc(cu.get("CUST_ID"))}</b><small>{esc(cu.get("NAME_ON_RECORD"))} &middot; KYC {"done" if cu.get("KYC_DONE") == "Y" else "pending"} '
                   f'&middot; customer since {esc(str(cu.get("CUST_SINCE") or "")[:4])}</small>' if cu else '<b>not a bank customer</b><small>salary paid into another bank: income comes from the documents</small>'),
        ("bu", "PAN, from the PAN card", esc(job.get("pan") or f.get("pan")), "Credit report API", "called by a Python UDF in Exasol",
         bool(job.get("bureau_found")), f'<b>score {esc(bu.get("BUREAU_SCORE"))}</b><small>{esc(bu.get("ACTIVE_LOANS"))} active loans &middot; EMIs {inr(bu.get("EXISTING_EMI"))} a month'
         f'{" &middot; PDF report " + esc((job.get("bureau_api") or {}).get("REPORT_ID")) if job.get("bureau_pdf") else ""}</small>'
         if job.get("bureau_found") else '<b>no record</b><small>human in the loop decides</small>'),
    ]
    rows = "".join(f'<div class="ln {c}"><div class="lk"><small>{src}</small><code>{key}</code></div><div class="ar"><i></i></div>'
                   f'<div class="ls"><b>{sysn}</b><small>{how}</small></div><div class="ar"><i></i></div>'
                   f'<div class="lr {"ok" if ok else "nocust" if ok is None else "no"}"><span class="tick">{"&#10003;" if ok else "&ndash;" if ok is None else "!"}</span><div>{res}</div></div></div>'
                   for c, src, key, sysn, how, ok, res in lanes)
    return f'<div class="lanes">{rows}</div>'


SRC_CLASS = {"Document store": "mg", "Core banking": "pg", "Credit bureau": "bu", "Cross-system": "xs"}
SEMV = {"Applicant name": "SRC.APPLICATIONS.APPLICANT_NAME", "PAN": "SRC.ID_PROOFS.ID_NUMBER", "Date of birth": "SRC.APPLICATIONS.BIRTH_DATE",
        "Mobile": "SRC.APPLICATIONS.MOBILE", "Employer": "SRC.PAYSLIPS.EMPLOYER", "Monthly salary": "SRC.SALARY_MONTHLY.NET_CREDITED",
        "Existing EMIs": "SRC.BUREAU_PULLS.EXISTING_EMI"}       # the semantic-view column each fact lives in (LOS_SEM.TERMS)


def contracts_strip(rows):
    """One chip per data contract, grouped by the system that owes it: green kept, amber warning, red critical breach."""
    if not rows:
        return ""
    groups = {}
    for r in rows:
        groups.setdefault(r["SOURCE_SYSTEM"], []).append(r)
    ok = lambda r: str(r["PASSED"]).lower() in ("true", "1")  # noqa: E731
    crit = [r for r in rows if not ok(r) and r["SEVERITY"] == "CRITICAL"]
    warn = [r for r in rows if not ok(r) and r["SEVERITY"] != "CRITICAL"]
    chips = "".join(f'<div class="cg"><span class="dot {SRC_CLASS.get(g, "xs")}"></span><b>{esc(g)}</b>' + "".join(
        f'<span class="cc {"ok" if ok(r) else "crit" if r["SEVERITY"] == "CRITICAL" else "warn"}" title="{esc(r["EXPECTATION"])} | {esc(r["EVIDENCE"])}">'
        f'{"&#10003;" if ok(r) else "&times;" if r["SEVERITY"] == "CRITICAL" else "!"} {esc(r["CONTRACT_ID"])}</span>' for r in rs) + "</div>"
        for g, rs in groups.items())
    notes = "".join(f'<div class="cn {"crit" if r["SEVERITY"] == "CRITICAL" else "warn"}"><b>{esc(r["CONTRACT_ID"])}</b> {esc(r["EXPECTATION"])}: '
                    f'<span>{esc(r["EVIDENCE"])}</span></div>' for r in crit + warn)
    head = (f'{len(rows) - len(crit) - len(warn)} of {len(rows)} kept'
            + (f' &middot; <span class="r">{len(crit)} critical breach{"es" if len(crit) > 1 else ""}: human in the loop</span>' if crit else "")
            + (f' &middot; <span class="a">{len(warn)} warning{"s" if len(warn) > 1 else ""}</span>' if warn else ""))
    return f'<div class="ctr"><div class="fk">Data contracts, checked on this upload</div><div class="ch">{head}</div><div class="cgs">{chips}</div>{notes}</div>'


def fq_viz(job, dd):
    """Step 4 in one line of pictures: three sources -> one federated query -> contracts -> scorecard, policy, rules -> result."""
    crs = job.get("contracts") or []
    kept = sum(1 for r in crs if str(r["PASSED"]).lower() in ("true", "1"))
    crit = any(str(r["PASSED"]).lower() not in ("true", "1") and r["SEVERITY"] == "CRITICAL" for r in crs)
    bars = "".join(f'<i style="height:{h}%"></i>' for h in (70, 72, 70, 71, 70, 96 if float((job.get("facts") or {}).get("INCOME_GAP_PCT") or 0) > 15 else 70))
    ar = '<span class="fqa">&#10140;</span>'
    return (f'<div class="fq"><div class="fqs"><span class="fs1 mg">{_icon_doc()}User application<small>MongoDB</small></span>'
            + (f'<span class="fs1 pg"><b class="mb">{bars}</b>6 months salary<small>Postgres</small></span>' if (job.get("facts") or {}).get("BANK_CUSTOMER", 1)
               else '<span class="fs1 nocust">no bank record<small>not a customer</small></span>') +
            f'<span class="fs1 bu">{_icon_bur()}Credit report API<small>UDF</small></span></div>'
            f'<svg class="fqj" viewBox="0 0 40 90" preserveAspectRatio="none"><g fill="none" stroke-width="2.5">'
            f'<path d="M0 15 C20 15 20 45 40 45" stroke="#0076AD"/><path d="M0 45 L40 45" stroke="#C56A00"/><path d="M0 75 C20 75 20 45 40 45" stroke="#7A4FD6"/></g></svg>'
            f'<span class="fqq">1 federated query<small>SQL, nothing copied</small></span>{ar}'
            f'<span class="fqc {"bad" if crit else ""}"><span class="fqh"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/>'
            f'{"<path d=" + chr(34) + "M9 9l6 6M15 9l-6 6" + chr(34) + "/>" if crit else "<path d=" + chr(34) + "M9 12l2 2 4-4" + chr(34) + "/>"}</svg>Contracts</span>'
            f'<small>{kept} of {len(crs)} kept</small></span>{ar}'
            f'<span class="fqr"><em>Scorecard</em><em class="ml">&#9733; ML model</em><em>Policy</em><em>Rules</em></span>{ar}'
            f'<span class="fqo"><b>{int(dd.get("SCORE") or 0)}</b><small>score</small><b>{esc(dd.get("BAND"))}</b><small>band</small>'
            f'<b>{esc(dd.get("RATE"))}%</b><small>rate</small></span></div>')


def _icon_doc():
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M6 2h9l4 4v15a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z"/><path d="M14 2v5h5M8 12h8M8 16h8"/></svg>')


def _icon_bur():
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/></svg>')


def fusion_viz(job):
    """Semantic fusion: the same fact under different names, formats and systems, resolved to one applicant under one ID."""
    fx = job.get("facts") or {}
    if not fx:
        return ""
    f, cu, bu = job.get("form") or {}, job.get("customer") or {}, job.get("bureau") or {}
    docs = {g["kind"]: g.get("fields") or {} for g in job["docs"] if g.get("kind")}
    idp, pay, let = docs.get("ID_PROOF", {}), docs.get("PAYSLIP", {}), docs.get("EMPLOYMENT_LETTER", {})
    cid = fx.get("CUST_ID") or cu.get("CUST_ID")
    keys = [("mg", "application _id", job["app"]), ("mg", "salaryAccount", f.get("account")), ("pg", "acct_mst &rarr; cust_id", cid),
            ("mg", "PAN card idNumber", job.get("pan")), ("bu", "bureau key", job.get("pan"))]
    chain = '<i class="lk2">&harr;</i>'.join(f'<span class="kc {c}"><small>{lbl}</small>{esc(v)}</span>' for c, lbl, v in keys if v)

    def cell(sys_, field, val):
        return f'<div class="fv {sys_}"><code>{field}</code><b>{esc(val) if val not in (None, "") else "&mdash;"}</b></div>' if val not in (None, "") else '<div class="fv none">&mdash;</div>'

    def same(kind, *vals):
        vs = {_norm(kind, v) for v in vals if v not in (None, "")}
        return len(vs) <= 1 and bool(vs)

    gap = float(fx.get("INCOME_GAP_PCT") or 0)
    emps = [pay.get("employer"), let.get("employer"), f.get("employer")]
    short = {"Applicant name": f.get("name"), "PAN": job.get("pan") if idp.get("idNumber") else "no PAN card", "Date of birth": _norm("date", f.get("dob")),
             "Mobile": _norm("mobile", f.get("mobile")), "Employer": fx.get("EMPLOYER"),
             "Monthly salary": ("documents only" if fx.get("INCOME_GAP_PCT") is None else f"{gap:.0f}% apart" if gap > 15 else "matches the bank"), "Existing EMIs": inr(fx.get("EXISTING_EMI"))}
    rows = [
        ("Applicant name", [cell("mg", "form.name", f.get("name")), cell("mg", "panCard.name", idp.get("name"))],
         [cell("pg", "cust_mst.cust_nm", cu.get("NAME_ON_RECORD"))], [], same("text", f.get("name"), idp.get("name"), cu.get("NAME_ON_RECORD")),
         esc(f.get("name")), "upper/lower case ignored"),
        ("PAN", [cell("mg", "form.pan", f.get("pan")), cell("mg", "panCard.idNumber", idp.get("idNumber"))],
         [cell("pg", "cust_mst.pan_no", cu.get("PAN_ON_RECORD"))], [cell("bu", "pull key", job.get("pan"))],
         bool(idp.get("idNumber")) and same("text", f.get("pan"), idp.get("idNumber"), cu.get("PAN_ON_RECORD")), esc(job.get("pan")),
         "the bureau's key" if idp.get("idNumber") else "no PAN card: the form's PAN is unproven"),
        ("Date of birth", [cell("mg", "form.dob", f.get("dob")), cell("mg", "panCard.dob", idp.get("dob"))],
         [cell("pg", "cust_mst.dob_txt", cu.get("DOB_ON_RECORD"))], [], same("date", f.get("dob"), idp.get("dob"), cu.get("DOB_ON_RECORD")),
         esc(_norm("date", f.get("dob"))), "ISO date vs DD-MM-YYYY text"),
        ("Mobile", [cell("mg", "form.mobile", f.get("mobile"))], [cell("pg", "cust_mst.mob_no", cu.get("MOBILE_ON_RECORD"))], [],
         same("mobile", f.get("mobile"), cu.get("MOBILE_ON_RECORD")), esc(_norm("mobile", f.get("mobile"))), "last 10 digits"),
        ("Employer", [cell("mg", "payslip.employer", pay.get("employer")), cell("mg", "letter.employer", let.get("employer"))],
         [cell("pg", "salary payer acct", fx.get("PAYER_ACCT"))], [], same("text", *emps), esc(fx.get("EMPLOYER")), "payslip, letter, form"),
        ("Monthly salary", [cell("mg", "payslip.net", inr(pay.get("net")))],
         [cell("pg", f"avg SUM(txn_amt), {int(fx.get('SALARY_MONTHS') or 0)} months", inr(fx.get("BANK_SALARY_AVG")))], [],
         gap <= 15, inr(fx.get("VERIFIED_GROSS")) + " gross, verified", f"{gap:.0f}% apart" + (" (rule R02)" if gap > 15 else "")),
        ("Existing EMIs", [], [], [cell("bu", "bureau.existing_emi", inr(fx.get("EXISTING_EMI") if fx.get("EXISTING_EMI") is not None else bu.get("EXISTING_EMI")))],
         True, inr(fx.get("EXISTING_EMI")), "one source"),
    ]
    body = "".join(f'<tr><th>{c}<code class="sv">{SEMV.get(c, "")}</code></th><td>{"".join(m) or chr(8212)}</td><td>{"".join(pg) or chr(8212)}</td><td>{"".join(b) or chr(8212)}</td>'
                   f'<td><div class="fz {"ok" if ok else "no"}"><span class="tick">{"&#10003;" if ok else "!"}</span><div><b>{val}</b><small>{note}</small></div></div></td></tr>'
                   for c, m, pg, b, ok, val, note in rows)
    agree = sum(1 for r in rows if r[4])
    n_docs = len([g for g in job["docs"] if g.get("fields")])
    srcs = (f'<div class="hsrc"><div class="hs mg"><b>MongoDB</b><small>{n_docs} documents</small></div>'
            f'<div class="hs pg{"" if cid else " nocust"}"><b>Core banking</b><small>{esc(cid or "not a customer")}</small></div>'
            f'<div class="hs bu"><b>Credit report</b><small>{"score " + esc(bu.get("BUREAU_SCORE")) if bu else "no report"}</small></div></div>')
    arrows = ('<svg class="hin" viewBox="0 0 60 150" preserveAspectRatio="none"><g fill="none" stroke-width="3">'
              '<path d="M0 25 C30 25 30 75 60 75" stroke="#0076AD"/><path d="M0 75 L60 75" stroke="#C56A00"/>'
              '<path d="M0 125 C30 125 30 75 60 75" stroke="#7A4FD6"/></g></svg>')
    tiles = "".join(
        f'<div class="ftile {"ok" if ok else "no"}"><div class="ftop"><span class="tick">{"&#10003;" if ok else "!"}</span><b>{c}</b>'
        f'<span class="sd">{"".join(f"<i class={chr(34)}{k}{chr(34)}></i>" for k, cells in (("mg", m), ("pg", pg_), ("bu", b)) if cells)}</span></div>'
        f'<div class="fval">{esc(short.get(c)) if short.get(c) not in (None, "") else "&mdash;"}</div></div>'
        for c, m, pg_, b, ok, val, note in rows)
    crs = job.get("contracts") or []
    kept = lambda r: str(r["PASSED"]).lower() in ("true", "1")  # noqa: E731
    sq = "".join(f'<i class="{"ok" if kept(r) else "crit" if r["SEVERITY"] == "CRITICAL" else "warn"}" title="{esc(r["CONTRACT_ID"])} {esc(r["EXPECTATION"])}: {esc(r["EVIDENCE"])}"></i>' for r in crs)
    crit = [r for r in crs if not kept(r) and r["SEVERITY"] == "CRITICAL"]
    warn = [r for r in crs if not kept(r) and r["SEVERITY"] != "CRITICAL"]
    cbar = (f'<div class="cbar"><span class="cl">Data contracts</span><span class="sqs">{sq}</span><b>{len(crs) - len(crit) - len(warn)} of {len(crs)} kept</b>'
            + (f'<span class="r">{len(crit)} critical: human in the loop</span>' if crit else "")
            + (f'<span class="a">{len(warn)} warning{"s" if len(warn) > 1 else ""}</span>' if warn else "") + '</div>') if crs else ""
    alerts = "".join(f'<div class="cn crit"><b>{esc(r["CONTRACT_ID"])}</b> {esc(r["EXPECTATION"])}: <span>{esc(r["EVIDENCE"])}</span></div>' for r in crit)
    picture = (f'<div class="fus2"><div class="fk">Semantic fusion</div>'
               f'<div class="hub">{srcs}{arrows}<div class="card360"><div class="ch3"><span>One applicant</span><span class="uid">{esc(cid or job["app"])}</span>'
               f'<b>{esc(f.get("name"))}</b><em>{agree} of {len(rows)} facts agree across systems</em></div><div class="ftiles">{tiles}</div></div></div>'
               f'{cbar}{alerts}')
    return (picture + f'<details class="fmore"><summary>See every field, system by system</summary><div class="fus"><div class="fh"><div><div class="fk">Semantic fusion</div><div class="ft">One applicant, one ID: '
            f'<span class="uid">{esc(cid or job["app"])}</span></div><div class="fs">Each system names the same fact its own way. Exasol maps them to one '
            f'vocabulary (the semantic views) and joins them on the keys below: {agree} of {len(rows)} facts agree.</div></div></div>'
            f'<div class="chain">{chain}</div>'
            f'<div class="fwrap"><table class="ftab"><tr><th>Fact</th><th><span class="dot mg"></span>Document store &middot; MongoDB</th>'
            f'<th><span class="dot pg"></span>Core banking &middot; Postgres</th><th><span class="dot bu"></span>Bureau</th><th>Fused value</th></tr>{body}</table></div>'
            + contracts_strip(job.get("contracts")) + '</div></details></div>')


STEPS = [("received", "Application received"), ("read", "Read by Amazon Textract"), ("stored", "Stored and matched"),
         ("scored", "Verified and scored in Exasol"), ("decided", "Decision")]


def fallback_only(job):
    """True when no document was read by Textract, so the page must not claim it was."""
    read = [g for g in job.get("docs") or [] if g.get("kind") and g.get("fields") is not None]
    return bool(read) and all(g.get("error") for g in read)


def stepper(job=None, upto=-1, running=None, fail=None):
    """upto = index of the last finished step; running = index of the step in progress."""
    job = job or {}
    det = {}
    if job.get("docs"):
        figs = "".join(f'<figure>{"<img src=" + chr(34) + g["thumb"] + chr(34) + " alt=" + chr(34) + esc(LABEL.get(g["kind"], "document")) + " (first page)" + chr(34) + "/>" if g.get("thumb") else ""}'
                       f'<figcaption class="{"" if g["kind"] else "x"}">{esc(LABEL.get(g["kind"], "not recognised"))}</figcaption></figure>'
                       for g in job["docs"])
        det["received"] = (f'Application <b>{esc(job["app"])}</b>, {len(job["docs"])} PDFs: the document type is read from each file\'s own words.'
                           f'<div class="thumbs">{figs}</div>', None)
    if job.get("read_secs") is not None:
        rows = "".join(f'<div class="rd"><b>{esc(LABEL.get(g["kind"], g["kind"]))}</b>'
                       f'<span>{len([v for v in (g.get("fields") or {}).values() if v not in (None, "", [])])} fields, lowest confidence '
                       f'{pct(min((g.get("confidence") or {"x": 0}).values()))}{" &middot; <b>fallback: PDF text</b>" if g.get("error") else ""}</span>'
                       f'<i>{(g.get("ms") or 0) / 1000:.1f} s</i></div>' for g in job["docs"] if g.get("kind"))
        intro = ("Amazon Textract was not used (TEXTRACT=off, or no AWS credentials): each field was read from the PDF's own "
                 "text layer by rules." if fallback_only(job) else
                 f"All documents in parallel, region {los_settings.REGION}. One question per field, each answer with its own confidence.")
        det["read"] = (f'{intro}{rows}', job["read_secs"])
    if job.get("store_secs") is not None:
        cu = job.get("customer") or {}
        cust = (f'salary account {esc(job["form"].get("account"))} belongs to <b>{esc(cu.get("CUST_ID"))} {esc(cu.get("NAME_ON_RECORD"))}</b>'
                if cu else f'<b>no customer found</b> for account {esc(job.get("form", {}).get("account"))}')
        det["stored"] = ((store_viz(job) if "pan" in job else
                          f'<div class="src3"><span>Document store (MongoDB): the form + {len([g for g in job["docs"] if g.get("fields")]) - 1} documents</span>'
                          f'<span>Core banking (Postgres, live): {cust}</span>'
                          f'<span>Credit bureau: {"report pulled" if job.get("bureau_found") else "<b>no record</b>"}</span></div>'), job["store_secs"])
    if job.get("facts_secs") is not None and not job.get("error"):
        dd = job.get("decision") or {}
        det["scored"] = (fq_viz(job, dd) + fusion_viz(job),
                         job["facts_secs"] + (job.get("contracts_secs") or 0))
        dec = dd.get("SYSTEM_DECISION")
        txt = {"APPROVE": "Approved automatically: no person needed", "APPROVE_REDUCED": "Approved automatically, at a lower amount",
               "DECLINE": "Declined, with the reasons", "REFER": f"Human in the loop ({esc(dd.get('REVIEW_LEVEL'))}): rules {esc(dd.get('RULES_FIRED'))}"}.get(dec, esc(dec))
        warn = "".join(f'<br/><span style="color:#B00D27">{label}: {esc(job[k])}</span>'
                       for k, label in (("log_error", "Not written to the decision log"), ("contracts_error", "Data contracts not checked"))
                       if job.get(k))
        det["decided"] = (f'<b>{txt}</b>{warn}', None)
    lis = ""
    for i, (k, t) in enumerate(STEPS):
        if k == "read" and fallback_only(job):
            t = "Read from the PDFs' text layer"
        cls = "fail" if fail is not None and i == fail else "done" if i <= upto else "run" if i == running else "wait"
        d, s = det.get(k, ("", None))
        if cls == "fail":
            d = f'<span style="color:#B00D27">{esc(job.get("error"))}</span>'
        lis += (f'<li class="{cls}"><div class="ic">{"&#10003;" if cls == "done" else "!" if cls == "fail" else i + 1}</div>'
                f'<div><div class="t">{t}</div><div class="d">{d}</div></div><div class="s">{f"{s:.1f} s" if s is not None else ""}</div></li>')
    tot = f'<div class="total">Upload to decision: <b>{job["total_secs"]:.1f} s</b></div>' if job.get("total_secs") else ""
    return H(f'<ol class="stp">{lis}</ol>{tot}')


# ------------------------------------------------------------------ tab 2: the case
def banner(d, job_secs=None, rs=None):
    c = d["c"]
    dec = c["SYSTEM_DECISION"]
    cls = {"REFER": "refer", "DECLINE": "decline"}.get(dec, "approve")
    lvl = {"UW1": "an underwriter", "UW2": "a senior underwriter", "FRAUD": "the fraud desk"}.get(c.get("REVIEW_LEVEL"), "a person")
    title = {"APPROVE": "Approved automatically" + (f" in {job_secs:.0f} seconds" if job_secs else ""),
             "APPROVE_REDUCED": f"Approved automatically at {inr(c['OFFER_AMOUNT'], True)}",
             "DECLINE": "Declined by policy", "REFER": f"Human in the loop: {lvl} decides this one"}[dec]
    kp = [(int(c["SCORE"]), "score"), (c["BAND"], "band"), (f'{c["RATE"]}%', "rate"), (f'{float(c["FOIR_PCT"]):.1f}%', "FOIR"),
          (inr(c["OFFER_AMOUNT"] if dec != "REFER" else c["AMOUNT_REQUESTED"], True), "amount"), (inr(c["EMI_AT_OFFER"]), "EMI / month")]
    kps = "".join(f'<div class="kp"><div class="v">{esc(v)}</div><div class="l">{l}</div></div>' for v, l in kp)
    if rs:
        kps += f'<div class="kp new"><div class="v">{int(rs["SCORE"])} &middot; {esc(rs["BAND"])}</div><div class="l">after review</div></div>'
    return H(f'<div class="banner {cls}"><div><div class="k">{esc(c["APP_ID"])} &middot; {esc(c["APPLICANT_NAME"])} &middot; '
             f'{inr(c["AMOUNT_REQUESTED"], True)} over {int(c["TERM_MONTHS"])} months &middot; {esc(c["PURPOSE"])}</div>'
             f'<div class="t">{title}</div><div class="m">{esc(c.get("EMPLOYER"))} &middot; {esc(c.get("CITY"))} &middot; {esc(c.get("CHANNEL"))}</div></div>'
             f'<div class="kpis">{kps}</div></div>')


ICON = {"auto": "&#10003;", "review": "!", "decline": "&times;", "sign": "&#9998;", "done": "&#9998;"}
CHIP = {"auto": "Verified automatically", "review": "Needs review", "decline": "Fails policy", "sign": "Senior signature needed", "done": "Reviewed"}


def checklist(items, reviews, rs, signed_final):
    rows = []
    for it in items:
        rv = reviews.get(it["key"])
        st = "done" if rv else it["status"]
        if it["status"] == "sign" and signed_final:
            st, chip = "done", "Signed"
        else:
            chip = CHIP[st]
        rules = "".join(f'<span><b>{esc(r[0])}</b>{esc(r[1])}: {esc(r[2])}</span>' for r in it["rules"])
        head = (f'<div class="hd"><span class="ti">{esc(it["title"])}</span><span class="chip">{chip}</span></div>'
                f'<div class="fi">{it["finding"]}</div>' + (f'<div class="rl">{rules}</div>' if rules else ""))
        n = it["tree"].count("<li>{") + it["tree"].count('<li><span class="src')
        body = [H(head), html.Details(open=st != "auto", children=[
            html.Summary(f"Evidence: {n} source{'s' if n != 1 else ''}"), H(f'<ul class="tree">{it["tree"]}</ul>')])]
        if rv:
            extra = ""
            if it["key"] == "income" and rv["resolution"] == K.REGULAR and rs:
                extra = (f'<div class="rs">Re-scored live on regular salary ({inr(rs["INCOME"])} a month): score <b>{int(rs["SCORE"])}</b>, band <b>{esc(rs["BAND"])}</b>, '
                         f'rate <b>{rs["RATE"]}%</b>, FOIR <b>{float(rs["FOIR"]):.1f}%</b> against a {float(rs["FOIR_CAP"]):.0f}% cap, '
                         f'affordable up to <b>{inr(rs["MAX_AMOUNT"])}</b>.</div>')
            note = f' &middot; &ldquo;{esc(rv["note"])}&rdquo;' if rv.get("note") else ""
            body.append(H(f'<div class="ann">&#9998; Reviewed by <b>{esc(rv["by"])}</b> at {esc(rv["at"])}: <b>{esc(rv["resolution"])}</b>{note}{extra}</div>'))
        elif it["status"] in ("review", "decline"):
            body.append(html.Div(className="rv", children=[
                html.Div([html.Div("Your finding", className="lb"),
                          dcc.RadioItems(id={"type": "rv-opt", "k": it["key"]}, options=it["options"], value=it["options"][0], className="radio")]),
                html.Div([html.Div("Note for the file", className="lb"),
                          dcc.Input(id={"type": "rv-note", "k": it["key"]}, type="text", className="inp", placeholder="optional")]),
                html.Button("Mark as reviewed", id={"type": "rv-go", "k": it["key"]}, className="btn go", n_clicks=0)]))
        rows.append(html.Div(className=f"ck {st}", children=[H(f'<div class="ic">{ICON[st]}</div>'), html.Div(body)]))
    return rows


def _authority(d, name):
    return next((r for r in d["auth"] if r["REVIEWER"] == name), {})


WORDS = {"APPROVE": "approved", "APPROVE_CONDITIONS": "approved with conditions", "DECLINE": "declined", "REFER_FRAUD": "held for fraud"}


def decision_panel(d, items, reviews, rs, log, reviewer):
    c = d["c"]
    if c["SYSTEM_DECISION"] != "REFER":
        last = log[-1] if log else None
        who = f'Recorded in the decision log by the decision engine at {esc(str(last["DECIDED_AT"])[11:19])}.' if last else ""
        if c["SYSTEM_DECISION"] == "DECLINE":
            return H(f'<div class="signed" style="background:linear-gradient(135deg,#081226 0%,#8A1020 100%)"><div class="t">Declined: {esc(c.get("RULES_FIRED"))}</div>'
                     f'<div class="s">{esc(c.get("RULE_TITLES"))}. {who}</div></div>')
        return H(f'<div class="signed"><div class="t">Offer: {inr(c["OFFER_AMOUNT"])} at {c["RATE"]}% for {int(c["TERM_MONTHS"])} months, '
                 f'EMI {inr(c["EMI_AT_OFFER"])}</div><div class="s">Every check passed, so no person was needed. {who}</div></div>')
    pending = [it["title"] for it in items if it["status"] in ("review", "decline") and it["key"] not in reviews]
    decisions = [r for r in log if r["STEP"] == "DECISION"]
    if decisions:
        first = decisions[-1]
        second = [r for r in log if r["STEP"] == "SECOND_SIGN" and r["LOG_ID"] > first["LOG_ID"]]
        amt = f'{inr(first["AMOUNT"])} at {first["RATE"]}%' if first["AMOUNT"] else ""
        if str(first["NEEDS_SECOND_SIGN"]).lower() in ("true", "1") and not second:
            need = float(first["AMOUNT"] or 0)
            elig = [r for r in d["auth"] if r["REVIEW_LEVEL"] == "UW2" and float(r["MAX_AMOUNT"]) >= need and r["REVIEWER"] != first["DECIDED_BY"]]
            cs = elig[0]["REVIEWER"] if elig else None
            return html.Div([H(f'<div class="signed wait"><div class="t">Signed by {esc(first["DECIDED_BY"])}: {WORDS.get(first["FINAL_DECISION"], first["FINAL_DECISION"])} {amt}</div>'
                               f'<div class="s">Above {esc(first["DECIDED_BY"])}\'s authority or the case level: a second person must countersign before the offer goes out.</div></div>'),
                             html.Button(f"Countersign as {cs} ({elig[0]['ROLE_NAME']}, up to {inr(elig[0]['MAX_AMOUNT'], True)})" if cs else "No one may countersign this amount",
                                         id="cs-go", className="btn go", disabled=not cs, n_clicks=0, style={"marginTop": ".6rem"}),
                             dcc.Store(id="cs-who", data=cs)])
        trail = " &rarr; ".join(f'{esc(r["STEP"].replace("_", " ").lower())} by <b>{esc(r["DECIDED_BY"])}</b> at {esc(str(r["DECIDED_AT"])[11:19])}'
                                for r in [first] + second)
        return H(f'<div class="signed"><div class="t">Final: {WORDS.get(first["FINAL_DECISION"], first["FINAL_DECISION"])}, {amt}</div>'
                 f'<div class="s">{trail}. Both signatures, the checklist notes, the policy and the model version are in the decision log (tab 6).</div></div>')
    if pending:
        return H(f'<div class="dp lock"><div class="t">Decision</div>Review the open check{"s" if len(pending) > 1 else ""} first: '
                 f'<b>{esc(", ".join(pending))}</b>. Every review is kept with the decision.</div>')
    basis = rs or {}
    mx = float(basis.get("MAX_AMOUNT") or c["MAX_AMOUNT"] or 0)
    amount = min(float(c["AMOUNT_REQUESTED"]), mx) if mx else float(c["AMOUNT_REQUESTED"])
    rate = basis.get("RATE") or c["RATE"]
    a = _authority(d, reviewer)
    lim = float(a.get("MAX_AMOUNT") or 0)
    second = amount > lim or (c.get("REVIEW_LEVEL") == "UW2" and a.get("REVIEW_LEVEL") != "UW2")
    cond = "Income assessed on regular salary; one-time pay excluded" if (reviews.get("income") or {}).get("resolution") == K.REGULAR else ""
    return html.Div(className="dp", children=[
        H(f'<div class="t">Decision &middot; signing as {esc(reviewer)} ({esc(a.get("ROLE_NAME"))}, up to {inr(lim, True)})</div>'),
        html.Div(className="dpg", children=[
            html.Div([html.Div("Decision", className="lb"),
                      dcc.RadioItems(id="dp-dec", className="radio", value="APPROVE_CONDITIONS" if cond else "APPROVE",
                                     options=[{"label": "Approve", "value": "APPROVE"}, {"label": "Approve with conditions", "value": "APPROVE_CONDITIONS"},
                                              {"label": "Decline", "value": "DECLINE"}])]),
            html.Div([html.Div(f"Amount (₹) · rate {rate}%", className="lb"),
                      dcc.Input(id="dp-amt", type="number", value=int(amount), step=10000, className="inp")]),
            html.Div([html.Div("Conditions", className="lb"), dcc.Input(id="dp-cond", type="text", value=cond, className="inp")]),
            html.Button("Sign the decision", id="dp-go", className="btn go", n_clicks=0)]),
        H(f'<div class="hint" style="margin-top:.5rem">{"A second signature will be needed: " + ("the amount is above " + esc(reviewer) + "&rsquo;s limit." if amount > lim else "this case needs a senior underwriter.") if second else "Within your authority: your signature is final."}</div>'),
    ])



CONTRACT_SQL = """-- one statement, every contract, each source read once through the semantic views (excerpt)
WITH a AS (SELECT APP_ID, SUBMITTED_AT, AMOUNT_REQUESTED, TERM_MONTHS, SALARY_ACCOUNT FROM LOS_SRC.APPLICATIONS),
p AS (SELECT APP_ID, GROSS, DEDUCTIONS, NET, PAY_MONTH FROM LOS_SRC.PAYSLIPS),          -- MongoDB
c AS (SELECT ACCT_NO, CUST_ID, PAN_ON_RECORD, DOB_ON_RECORD FROM LOS_SRC.CUSTOMERS),     -- Postgres
t AS (SELECT ACCT_NO, SUM(CASE WHEN AMOUNT IS NULL OR AMOUNT <= 0 THEN 1 ELSE 0 END) AS BAD_AMT,
             MAX(TXN_DATE) AS LAST_TXN FROM LOS_SRC.TRANSACTIONS GROUP BY ACCT_NO),       -- Postgres
...
SELECT j.APP_ID, k.CONTRACT_ID,
  CASE k.CONTRACT_ID
    WHEN 'DS03' THEN ABS(GROSS - DEDUCTIONS - NET) <= 1
    WHEN 'DS05' THEN ID_NUMBER REGEXP_LIKE '[A-Z]{5}[0-9]{4}[A-Z]'
    WHEN 'CB02' THEN IS_DATE(DOB_ON_RECORD, 'DD-MM-YYYY')
    WHEN 'CB03' THEN COALESCE(BAD_AMT, 0) = 0
    WHEN 'XS01' THEN UPPER(TRIM(ID_NUMBER)) = UPPER(TRIM(PAN_ON_RECORD))
    ...
  END AS PASSED
FROM j CROSS JOIN LOS_SEM.CONTRACTS k;      -- the contracts are rows the owners maintain"""


def semantic_html(data):
    if data.get("error"):
        return "", f'<div class="refused">{esc(data["error"])}</div>'
    rows, run, zero = data["sum"]["rows"], data["run"], data["zero"]
    crit_c = [r for r in rows if r["SEVERITY"] == "CRITICAL" and int(r["BREACHES"] or 0)]
    warn_c = [r for r in rows if r["SEVERITY"] != "CRITICAL" and int(r["BREACHES"] or 0)]
    crit_apps = sum(int(r["BREACHES"] or 0) for r in crit_c)
    secs = data.get("secs") or run.get("SECONDS")
    checks = data.get("checks") or run.get("CHECKS")
    tiles = (f'<div class="big3"><div class="b"><div class="v">{float(secs or 0):.1f} s</div><div class="l">{int(checks or 0):,} checks on '
             f'{int(run.get("APPS") or 0):,} applications, against the live sources{" just now" if data.get("checks") else ""}</div></div>'
             f'<div class="b"><div class="v">{len(rows)} contracts</div><div class="l">owned by {len({r["OWNER"] for r in rows})} teams; rows in a table, not code</div></div>'
             f'<div class="b {"bad" if crit_c else ""}"><div class="v">{len(crit_c)} critical &middot; {len(warn_c)} warning</div><div class="l">contracts breached somewhere. '
             f'{"A critical breach puts a human in the loop" + (f": {crit_apps} now waiting" if crit_c else "")}; a warning is reported to the owner</div></div></div>')
    body = ""
    for r in rows:
        b, n = int(r["BREACHES"] or 0), int(r["APPS_CHECKED"] or 0)
        st = "ok" if not b else "crit" if r["SEVERITY"] == "CRITICAL" else "warn"
        body += (f'<tr><td><b>{esc(r["CONTRACT_ID"])}</b></td><td><span class="dot {SRC_CLASS.get(r["SOURCE_SYSTEM"], "xs")}"></span>{esc(r["SOURCE_SYSTEM"])}'
                 f'<small>{esc(r["OWNER"])}</small></td><td>{esc(r["EXPECTATION"])}<small><code>{esc(r["DATASET"])}</code></small></td>'
                 f'<td><span class="sev {r["SEVERITY"].lower()}">{esc(r["SEVERITY"].lower())}</span></td>'
                 f'<td class="n"><span class="cst {st}">{"kept" if not b else f"{b:,} breached"}</span><small>of {n:,}</small></td>'
                 f'<td><small>{esc(r.get("EXAMPLE") or "")}</small></td></tr>')
    callout = (f'<div class="verdict2 warn"><div class="t">Found in the core-banking feed: {int(zero.get("ROWS_BAD") or 0)} transactions with a &#8377;0 amount</div>'
               f'<div class="s">&ldquo;{esc(zero.get("NARRATION"))}&rdquo; postings in {int(zero.get("ACCOUNTS") or 0)} accounts break contract CB03. A warning, not a '
               f'block: they are debits, not salary, so no decision depends on them. The core-banking team owns the fix, and every affected application says so.</div></div>'
               if int(zero.get("ROWS_BAD") or 0) else "")
    vocab = (f'<div class="hw-pic">{how.semantic_picture()}</div>'
)
    return vocab, (f'{tiles}{callout}<details class="eng"><summary>All {len(rows)} contracts: who owes each one, and where it is broken</summary>'
            f'<div class="tblw" style="max-height:none"><table class="tbl sem"><tr><th>Contract</th><th>Owed by</th><th>Promise</th><th>Severity</th>'
            f'<th>Applications</th><th>Example</th></tr>{body}</table></div></details>'
            f'<details class="eng"><summary>How the checks run: one SQL statement, every contract, each source read once</summary><pre class="sql">{esc(CONTRACT_SQL)}</pre></details>')


def audit_html(data):
    lg = data["log"]
    if lg:
        cols = ["DECIDED_AT", "APP_ID", "STEP", "DECIDED_BY", "FINAL_DECISION", "AMOUNT", "RATE", "REASON_CODE", "NOTES", "POLICY_VERSION", "MODEL_VERSION"]
        body = "".join("<tr>" + "".join(f'<td class="{"n" if k in ("AMOUNT", "RATE") else ""}">{esc(str(r.get(k) or "")[:19] if k == "DECIDED_AT" else inr(r[k]) if k == "AMOUNT" and r.get(k) else r.get(k) if r.get(k) is not None else "")}</td>' for k in cols) + "</tr>" for r in lg)
        t = f'<div class="tblw"><table class="tbl"><tr>{"".join(f"<th>{k.replace(chr(95), chr(32)).lower()}</th>" for k in cols)}</tr>{body}</table></div>'
    else:
        t = '<div class="hint">No decisions recorded yet: upload an application in tab 3.</div>'
    rules = data["rules"]
    rt = "".join(f'<tr><td><b>{esc(r["RULE_ID"])}</b></td><td>{esc(r["TITLE"])}</td><td>{esc(r["METRIC"])} {esc(r["OPERATOR"])} {float(r["THRESHOLD"]):g}</td>'
                 f'<td>{esc(r["OUTCOME"])}</td><td>{esc(r["REVIEW_LEVEL"] or "")}</td></tr>' for r in rules)
    return t, f'<div class="tblw"><table class="tbl"><tr><th>Rule</th><th>When</th><th>Test</th><th>Outcome</th><th>Who</th></tr>{rt}</table></div>'


# ------------------------------------------------------------------ layout
TAB = {"style": {}, "selected_style": {}, "className": "tab", "selected_className": "tab--selected"}


def new_tab():
    return html.Div([
        html.Div(className="nt", children=[
            html.Div(className="startc", children=[
                H('<div class="qk" style="margin:0">Start an application</div>'),
                dcc.Upload(id="up", multiple=True, accept=".pdf,application/pdf", className="drop", children=H(
                    '<div class="t">Drop the PDFs here, or click to choose</div>'
                    '<div class="d">the application form, a payslip, the PAN card, an employment letter</div>')),
                H('<div class="or">or use a sample</div>'),
                *[html.Button([name, html.Span(sub, className="s")], id={"type": "pack", "p": k}, className="btn wide", n_clicks=0)
                  for k, (name, sub) in PACKS.items()],
                H('<div class="hint" style="font-size:.74rem">The sample PDFs are in <code>data/packs/</code>: drag a folder\'s four files onto the box to upload them yourself.</div>'),
                H('<div class="or" style="margin-top:.4rem">or open a case waiting for review</div>'),
                dcc.Dropdown(id="queue", placeholder="Review queue…", clearable=True, optionHeight=48),
            ]),
            html.Div(id="steps", children=stepper()),
        ]),
        html.Div(id="tb", className="tb", style={"display": "none"}, children=[
            html.Span("Reviewing as"),
            dcc.Dropdown(id="reviewer", options=REVIEWERS, value=REVIEWERS[0], clearable=False, style={"minWidth": "15rem"})]),
        dcc.Loading(html.Div(id="case-out"), type="dot"),
    ])


def insights_tab():
    return html.Div([
        H('<div class="ov-band"><div class="ov-k">LOS insights</div>'
          '<div class="ov-h">Every application received, where it went, and what to change in the rules.</div></div>'),
        dcc.Loading(html.Div(id="ins-out"), type="dot"),
    ])


def semantic_tab():
    return html.Div([
        H('<div class="ov-band"><div class="ov-k">Semantic layer</div>'
          '<div class="ov-h">The same fact has a different name in every system. Exasol gives it one.</div></div>'),
        dcc.Loading(html.Div(id="sem-out"), type="dot"),
    ])


def audit_tab():
    return html.Div([
        H('<div class="ov-band"><div class="ov-k">Controls the database enforces</div>'
          '<div class="ov-h">Every decision, by whom, on which policy and model. Kept, never edited.</div>'
          '<div class="ov-s">The underwriting desk signs in with its own login. That login may add rows to the decision log and nothing else.</div></div>'),
        html.Div(style={"display": "flex", "gap": ".6rem", "margin": ".4rem 0 .6rem"}, children=[
            html.Button("Refresh", id="aud-refresh", className="btn ghost sm", n_clicks=0),
            html.Button("Try to change a recorded decision", id="tamper", className="btn sm", n_clicks=0),
            html.Button("Try to delete the log", id="tamper2", className="btn sm", n_clicks=0)]),
        html.Div(id="tamper-out"),
        dcc.Loading(html.Div(id="aud-out"), type="dot"),
        H('<div class="ov-band"><div class="ov-k">When a case goes to a person</div><div class="ov-h">The rules, as rows the risk team owns</div></div>'),
        html.Div(id="rules-out"),
        H('<div class="footnote" style="margin-top:1rem">Honest limits: applicants, documents and transactions are synthetic (seeded); the PDFs are stamped SYNTHETIC. '
          'The loan book is real public Lending Club data (2007&ndash;2018, USD). The credit bureau is mocked. Documents are read by Amazon Textract (' + los_settings.REGION + '). '
          'No real bank systems are involved.</div>'),
    ])


def create_dash_app(server, url_base_pathname, metadata):
    base = url_base_pathname.rstrip("/") + "/"
    app = Dash(__name__, server=server, routes_pathname_prefix="/", requests_pathname_prefix=base,
               assets_folder=str(HERE / "assets"), title="Loan Origination System — Exasol",
               suppress_callback_exceptions=True, index_string=INDEX)

    def _pdf(app_id, name):
        f = UPLOADS / Path(app_id).name / Path(name).name
        if not f.exists():
            abort(404)
        return send_file(f, mimetype="application/pdf")
    try:
        server.add_url_rule("/doc/<app_id>/<name>", endpoint="los_pdf", view_func=_pdf)
    except AssertionError:
        pass  # already registered (hot reload)


    app.layout = html.Div(className="page", children=[
        H(f'<div class="pagehead">{_logo()}<span class="ph-t">Loan Origination System &middot; live demo</span></div>'),
        html.Div(id="hero", children=H(hero({"exa": True, "pg": True, "mongo": True}))),
        dcc.Interval(id="tick", interval=300_000, n_intervals=0),   # status pills; every 5 min, cheap checks only
        dcc.Store(id="job-r"), dcc.Store(id="job-x"), dcc.Store(id="job-s"), dcc.Store(id="cur"), dcc.Store(id="case"),
        dcc.Store(id="reviews", data={}), dcc.Store(id="rescore"), dcc.Store(id="signed", data=0), dcc.Store(id="sign-err"),
        dcc.Tabs(id="tabs", value="over", className="tabbar", children=[
            dcc.Tab(label="1 · Overview", value="over", children=dcc.Loading(html.Div(id="ov-body"), type="dot"), **TAB),
            dcc.Tab(label="2 · How it works", value="how", children=H(how.page()), **TAB),
            dcc.Tab(label="3 · New application", value="new", children=new_tab(), **TAB),
            dcc.Tab(label="4 · LOS insights", value="ins", children=insights_tab(), **TAB),
            dcc.Tab(label="5 · Semantic layer & contracts", value="sem", children=semantic_tab(), **TAB),
            dcc.Tab(label="6 · Audit trail", value="audit", children=audit_tab(), **TAB),
        ]),
    ])

    @app.callback(Output("hero", "children"), Input("tick", "n_intervals"))
    def _hero(_):
        return H(hero(health()))

    @app.callback(Output("ov-body", "children"), Input("tabs", "value"))
    def _overview(tab):
        if tab != "over":
            return no_update
        try:
            o = los.call("overview")
        except los.Down as e:
            return down(e)
        note = "" if o["pipe"]["live"] else '<div class="cached">A source was unavailable: the numbers are from the last good run.</div>'
        return H(story.problem(o["pipe"]) + note)

    # ---- tab 2: the live pipeline, one callback per step so the page shows each one finishing
    @app.callback(Output("job-r", "data"), Output("steps", "children", allow_duplicate=True), Output("case-out", "children", allow_duplicate=True),
                  Output("tb", "style", allow_duplicate=True),
                  Input("up", "contents"), Input({"type": "pack", "p": ALL}, "n_clicks"), State("up", "filename"), prevent_initial_call=True)
    def _start(contents, _packs, names):
        t = ctx.triggered_id
        try:
            if t == "up":
                if not contents:
                    return no_update, no_update, no_update, no_update
                job = los.call("receive", [(n, c.split(",", 1)[1]) for n, c in zip(names, contents)])
            elif isinstance(t, dict) and any(_packs):
                job = los.call("receive_pack", t["p"])
            else:
                return no_update, no_update, no_update, no_update
        except los.Down as e:
            return no_update, down(e), None, {"display": "none"}
        return job, stepper(job, upto=0, running=1), None, {"display": "none"}

    @app.callback(Output("job-x", "data"), Output("steps", "children", allow_duplicate=True), Input("job-r", "data"), prevent_initial_call=True)
    def _read(job):
        try:
            job = los.call("read", job["app"])
        except los.Down as e:
            return no_update, down(e)
        return job, stepper(job, upto=1, running=2)

    @app.callback(Output("job-s", "data"), Output("steps", "children", allow_duplicate=True), Input("job-x", "data"), prevent_initial_call=True)
    def _store(job):
        try:
            job = los.call("store", job["app"])
        except los.Down as e:
            return no_update, down(e)
        if job.get("error"):
            return no_update, stepper(job, upto=1, fail=2)
        return job, stepper(job, upto=2, running=3)

    @app.callback(Output("cur", "data", allow_duplicate=True), Output("steps", "children", allow_duplicate=True), Input("job-s", "data"),
                  prevent_initial_call=True)
    def _decide(job):
        try:
            job = los.call("decide", job["app"])
        except los.Down as e:
            return no_update, down(e)
        if job.get("error"):
            return no_update, stepper(job, upto=2, fail=3)
        return {"app": job["app"], "form": job.get("form"), "secs": job["total_secs"]}, stepper(job, upto=4)

    @app.callback(Output("queue", "options"), Input("tabs", "value"), Input("cur", "data"))
    def _queue(tab, _):
        if tab != "new":
            return no_update
        try:
            rows = los.call("queue")
        except los.Down:
            return []
        return [{"label": f'{r["APP_ID"]} · {r["APPLICANT_NAME"]} · {inr(r["AMOUNT_REQUESTED"], True)} · {r["RULES_FIRED"]}', "value": r["APP_ID"]}
                for r in rows]

    @app.callback(Output("cur", "data", allow_duplicate=True), Input("queue", "value"), prevent_initial_call=True)
    def _pick(app_id):
        return {"app": app_id} if app_id else no_update

    @app.callback(Output("case", "data"), Output("reviews", "data"), Output("rescore", "data"), Output("tb", "style"),
                  Input("cur", "data"), prevent_initial_call=True)
    def _load(cur):
        try:
            d = los.call("case_load", cur["app"])
        except los.Down:
            d = None
        if not d:
            return None, {}, None, {"display": "none"}
        d["form"], d["secs"] = cur.get("form"), cur.get("secs")
        return d, {}, None, {"display": "flex"}

    @app.callback(Output("case-out", "children"), Input("case", "data"), Input("reviews", "data"), Input("rescore", "data"),
                  Input("signed", "data"), Input("reviewer", "value"), State("sign-err", "data"))
    def _render(d, reviews, rs, _signed, reviewer, err):
        if not d:
            return None
        app_id = d["c"]["APP_ID"]
        items = K.build(d, href_base=f"{base}doc/{app_id}/", form=d.get("form"))
        try:
            log = los.call("log_rows", app_id)
        except los.Down as e:
            return down(e)
        final = any(r["STEP"] == "SECOND_SIGN" for r in log) or any(r["STEP"] == "DECISION" and str(r["NEEDS_SECOND_SIGN"]).lower() not in ("true", "1") for r in log)
        n_auto = sum(1 for it in items if it["status"] == "auto")
        n_rev = sum(1 for it in items if it["key"] in reviews)
        n_open = sum(1 for it in items if it["status"] in ("review", "decline") and it["key"] not in reviews)
        n_sign = sum(1 for it in items if it["status"] == "sign")
        tot = len(items)
        head = H(f'<div class="ckh"><div class="t">Review checklist</div><div class="bar"><i class="a" style="width:{100 * n_auto / tot:.0f}%"></i>'
                 f'<i class="r" style="width:{100 * (n_rev + (n_sign if final else 0)) / tot:.0f}%"></i><i class="p" style="width:{100 * (n_open + (0 if final else n_sign)) / tot:.0f}%"></i></div>'
                 f'<div class="n"><b>{n_auto}</b> verified automatically &middot; <b>{n_rev}</b> reviewed &middot; <b>{n_open}</b> open'
                 + (f' &middot; <b>{n_sign}</b> senior signature' if n_sign else "") + '</div></div>')
        out = [banner(d, d.get("secs") if d["c"]["SYSTEM_DECISION"] != "REFER" else None, rs), head, *checklist(items, reviews or {}, rs, final),
               decision_panel(d, items, reviews or {}, rs, log, reviewer)]
        if err:
            out.append(H(f'<div class="refused">{esc(err)}</div>'))
        if not d.get("live"):
            out.append(H('<div class="cached">Core banking was unavailable: the salary credits are from the last good read.</div>'))
        return out

    @app.callback(Output("reviews", "data", allow_duplicate=True), Output("rescore", "data", allow_duplicate=True),
                  Input({"type": "rv-go", "k": ALL}, "n_clicks"), State({"type": "rv-opt", "k": ALL}, "value"),
                  State({"type": "rv-note", "k": ALL}, "value"), State("reviewer", "value"), State("reviews", "data"), State("case", "data"),
                  State("rescore", "data"), prevent_initial_call=True)
    def _review(clicks, opts, notes, reviewer, reviews, d, rs):
        t = ctx.triggered_id
        if not t or not any(clicks):
            return no_update, no_update
        keys = [s["id"]["k"] for s in ctx.states_list[0]]
        i = keys.index(t["k"])
        reviews = dict(reviews or {})
        reviews[t["k"]] = {"resolution": opts[i], "note": (notes[i] or "").strip(), "by": reviewer, "at": datetime.now().strftime("%H:%M")}
        if t["k"] == "income" and opts[i] == K.REGULAR:
            try:
                rs = los.call("rescore_regular", d["c"]["APP_ID"])
            except los.Down:
                rs = None
        return reviews, rs

    @app.callback(Output("signed", "data"), Output("sign-err", "data"), Input("dp-go", "n_clicks"),
                  State("dp-dec", "value"), State("dp-amt", "value"), State("dp-cond", "value"), State("reviewer", "value"),
                  State("case", "data"), State("reviews", "data"), State("rescore", "data"), State("signed", "data"), prevent_initial_call=True)
    def _sign(n, dec, amt, cond, reviewer, d, reviews, rs, k):
        if not n:
            return no_update, no_update
        try:
            r = los.call("sign", d["c"]["APP_ID"], reviews or {}, dec, amt, cond, reviewer)
        except los.Down as e:
            return (k or 0) + 1, str(e)
        return (k or 0) + 1, None if r["ok"] else r["error"]

    @app.callback(Output("signed", "data", allow_duplicate=True), Output("sign-err", "data", allow_duplicate=True),
                  Input("cs-go", "n_clicks"), State("cs-who", "data"), State("case", "data"), State("signed", "data"), prevent_initial_call=True)
    def _countersign(n, who, d, k):
        if not n or not who:
            return no_update, no_update
        try:
            r = los.call("countersign", d["c"]["APP_ID"], who)
        except los.Down as e:
            return (k or 0) + 1, str(e)
        return (k or 0) + 1, None if r["ok"] else r["error"]

    # ---- tab 4
    @app.callback(Output("ins-out", "children"), Input("tabs", "value"))
    def _insights(tab):
        if tab != "ins":
            return no_update
        try:
            return H(insights.page(los.call("insights")))
        except los.Down as e:
            return down(e)

    @app.callback(Output("sem-out", "children"), Input("tabs", "value"))
    def _sem(tab):
        if tab != "sem":
            return no_update
        try:
            data = los.call("semantic")
        except los.Down as e:
            return down(e)
        return H(semantic_html(data)[0])

    # ---- tab 5
    @app.callback(Output("aud-out", "children"), Output("rules-out", "children"), Input("tabs", "value"), Input("aud-refresh", "n_clicks"))
    def _audit(tab, _):
        if tab != "audit":
            return no_update, no_update
        try:
            a, r = audit_html(los.call("audit"))
        except los.Down as e:
            return down(e), None
        return H(a), H(r)

    @app.callback(Output("tamper-out", "children"), Input("tamper", "n_clicks"), Input("tamper2", "n_clicks"), prevent_initial_call=True)
    def _tamper(_a, _b):
        try:
            r = los.call("tamper", "update" if ctx.triggered_id == "tamper" else "delete")
        except los.Down as e:
            return down(e)
        return H(f'<div class="refused"><b>Exasol refused it.</b> <code>{esc(r["sql"])}</code><br/>{esc(r["error"])}</div>' if not r["ok"] else
                 f'<div class="cached">It went through ({r["rows"]} rows): the privileges are wrong, run setup/05_governance.py</div>')

    return app
