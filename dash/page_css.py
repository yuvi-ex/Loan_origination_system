"""Page-level CSS of the console: the shared look of the Exasol demo consoles."""
PAGE_CSS = """<style>
.block-container { padding-top:1rem !important; }
.dgm { border-radius:22px; border:1px solid var(--edge); background:#fff; box-shadow:var(--shadow); padding:.5rem .6rem .2rem; }
.dgm svg { display:block; width:100%; height:auto; font-family:Figtree,sans-serif; }
.dgm .zone { fill:#F6F9FC; stroke:#DFE5EE; stroke-dasharray:6 5; }
.dgm .zlabel { font-size:12px; font-weight:800; letter-spacing:.14em; fill:#66748A; }
.dgm .node { transition:opacity .3s; }
.dgm .node rect { fill:#fff; stroke:#DFE5EE; stroke-width:1.5; }
.dgm .node .nt { font-size:19px; font-weight:800; fill:#0B1B34; }
.dgm .node .ns { font-size:13px; fill:#66748A; }
.dgm .node.exa rect { fill:#F2FBF9; stroke:#9ED9CE; stroke-width:2; }
.dgm .node.on rect { stroke:#1FA08B; stroke-width:3.5; }
.dgm .edge { stroke:#B9C5D3; stroke-width:3; fill:none; transition:opacity .3s; }
.dgm .edge.on { stroke:#1FA08B; stroke-width:5; stroke-dasharray:12 8; animation:flow .8s linear infinite; }
@keyframes flow { to { stroke-dashoffset:-40; } }
.dgm .dim { opacity:.28; }
.dgm .node.via rect { stroke:#1FA08B; stroke-width:2; stroke-dasharray:7 5; }
.dgm .node.via { opacity:.75; }
.dgm .edge.via { stroke:#1FA08B; stroke-width:3; stroke-dasharray:4 6; opacity:.7; }
.dgm .pill.via rect { fill:#7FB8AE; }
.dgm .node.user rect { fill:#081226; stroke:#081226; } .dgm .node.user .nt { fill:#fff; } .dgm .node.user .ns { fill:#B8C6DA; }
.dgm .node.vsband rect { fill:#E3F5F1; stroke:#9ED9CE; stroke-width:2; }
.dgm .node.vsband.on rect { stroke:#1FA08B; stroke-width:3; }
.dgm .vt { font-size:16px; font-weight:800; fill:#12796A; } .dgm .vs2 { font-size:12px; fill:#4A5464; }
.dgm .udf rect { fill:#fff; stroke:#9ED9CE; stroke-width:1.5; stroke-dasharray:5 4; }
.dgm .udf.on rect { stroke:#1FA08B; stroke-width:3; stroke-dasharray:none; } .dgm .udf.dim { opacity:.35; }
.dgm .ut { font-size:14px; font-weight:800; fill:#0B1B34; } .dgm .us { font-size:11.5px; fill:#66748A; }
.ov-band { margin:1.6rem 0 .5rem; } .ov-k { text-transform:uppercase; letter-spacing:.14em; font-size:.7rem; font-weight:800; color:var(--teal-ink); }
.ov-h { font-size:1.45rem; font-weight:800; letter-spacing:-.02em; color:var(--ink2); margin:.15rem 0 .2rem; }
.ov-s { font-size:.98rem; color:var(--muted); line-height:1.55; max-width:62rem; }
.cmp2 { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin:.7rem 0 .4rem; }
.cc { border-radius:18px; border:1px solid var(--edge); background:#fff; padding:1rem 1.2rem; }
.cc.bad { border-left:5px solid var(--no); } .cc.good { border-left:5px solid var(--teal); }
.cc .k { text-transform:uppercase; letter-spacing:.12em; font-size:.66rem; font-weight:800; }
.cc.bad .k { color:var(--no); } .cc.good .k { color:var(--teal-ink); }
.cc .t { font-weight:800; font-size:1.15rem; margin:.2rem 0 .5rem; }
.cc ul { margin:0 0 0 1.1rem; padding:0; } .cc li { margin:.28rem 0; line-height:1.5; color:var(--muted); }
.steps4 { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.6rem; margin:.7rem 0 .5rem; }
.st4 { border-radius:16px; border:1px solid var(--edge); background:#fff; padding:.8rem .9rem; position:relative; }
.st4 .n { font-size:.66rem; font-weight:800; letter-spacing:.12em; color:var(--teal-ink); text-transform:uppercase; }
.st4 .t { font-weight:800; font-size:1rem; margin:.15rem 0 .3rem; } .st4 .d { font-size:.85rem; color:var(--muted); line-height:1.45; }
.st4.exa { background:#F2FBF9; border-color:#CDEBE4; }
.live { border-radius:14px; background:#F6F9FC; border:1px solid var(--edge); padding:.6rem .9rem; font-size:.88rem; color:var(--ink2); margin:.3rem 0; }
.live b { color:var(--teal-ink); }
.tok { display:grid; grid-template-columns:1fr auto 1fr auto 1fr; gap:.7rem; align-items:center; margin:.7rem 0 .4rem; }
.tk2 { border-radius:18px; border:1px solid var(--edge); background:#fff; padding:.9rem 1.1rem; }
.tk2 .v { font-size:2rem; font-weight:900; color:var(--ink2); font-variant-numeric:tabular-nums; line-height:1.1; }
.tk2 .k { font-size:.85rem; color:var(--muted); margin-top:.2rem; line-height:1.4; }
.tk2.bad .v { color:var(--no); } .tk2.good { background:#E3F5F1; border-color:#CDEBE4; } .tk2.good .v { color:var(--teal-ink); }
.tk2.navy { background:linear-gradient(135deg,#081226 0%,#12796A 100%); border:0; } .tk2.navy .v, .tk2.navy .k { color:#fff; }
.tka { font-size:1.6rem; color:var(--faint); }
.trace { border-radius:16px; border:1px solid var(--edge); background:#fff; padding:.4rem .2rem; margin:.5rem 0; }
.tr { display:grid; grid-template-columns:2.2rem minmax(0,1.5fr) minmax(0,2fr) 6rem 7rem; gap:.6rem; align-items:center;
  padding:.5rem .8rem; border-bottom:1px solid #EEF2F7; font-size:.88rem; }
.tr:last-child { border-bottom:0; } .tr.h { font-size:.62rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); }
.tr .ic { width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:.7rem; font-weight:800; }
.tr .ic.llm { background:#EEF0FF; color:#4B4FD8; } .tr .ic.sql { background:#E3F5F1; color:var(--teal-ink); }
.tr .nm { font-weight:800; } .tr .ds { color:var(--muted); font-size:.82rem; } .tr .num { text-align:right; font-variant-numeric:tabular-nums; font-weight:700; }
.tr.tot { background:#F6F9FC; font-weight:800; }
@media (max-width:1000px) { .cmp2, .steps4 { grid-template-columns:1fr; } .tok { grid-template-columns:1fr; } .tka { display:none; } }
.ov-s:empty { display:none; }
.pipe { display:flex; align-items:stretch; gap:.4rem; margin:.8rem 0 .4rem; }
.pp { flex:1; border-radius:18px; border:1px solid var(--edge); background:#fff; padding:1rem .8rem; text-align:center; box-shadow:0 8px 22px rgba(8,18,38,.05); }
.pp.exa { background:linear-gradient(180deg,#E3F5F1 0%,#fff 100%); border-color:#9ED9CE; }
.pp-ic { width:54px; height:54px; border-radius:50%; margin:0 auto .5rem; display:flex; align-items:center; justify-content:center;
  background:#EEF2F7; color:var(--ink2); } .pp.exa .pp-ic { background:#12796A; color:#fff; }
.pp-t { font-weight:900; font-size:1.05rem; color:var(--ink2); } .pp-d { font-size:.8rem; color:var(--muted); margin-top:.1rem; }
.pp-tg { display:inline-block; margin-top:.45rem; font-family:'JetBrains Mono',monospace; font-size:.66rem; color:#0076AD; background:#E2F4FF; border-radius:999px; padding:.1rem .5rem; }
.pp-ar { display:flex; align-items:center; color:#9FB0C4; font-size:1.4rem; font-weight:800; }
.pp-loop { display:flex; align-items:center; gap:1rem; flex-wrap:wrap; font-size:.88rem; font-weight:700; color:var(--teal-ink); margin:.3rem 0 .2rem .3rem; }
.pp-chip { font-size:.76rem; font-weight:800; color:#fff; background:var(--navy); border-radius:999px; padding:.25rem .8rem; }
.big-x { color:var(--teal-ink); }
.tbars { border-radius:20px; border:1px solid var(--edge); background:#fff; padding:1.1rem 1.2rem .9rem; margin:.7rem 0 .3rem; }
.tb-row { display:grid; grid-template-columns:15rem 1fr 7rem; gap:1rem; align-items:center; margin:.55rem 0 1.1rem; }
.tb-l { font-weight:800; font-size:.95rem; color:var(--ink2); line-height:1.25; } .tb-l span { display:block; font-weight:600; font-size:.76rem; color:var(--faint); }
.tb-tr { position:relative; height:34px; border-radius:10px; background:#F1F4F9; }
.tb-f { height:100%; border-radius:10px; } .tb-f.bad { background:linear-gradient(90deg,#FF7A85,#C8102E); } .tb-f.good { background:#1FA08B; min-width:4px; }
.tb-ctx { position:absolute; top:-10px; bottom:-10px; border-left:3px dashed #081226; }
.tb-ctx span { position:absolute; top:-1.35rem; left:-.2rem; white-space:nowrap; font-size:.7rem; font-weight:800; color:#081226; }
.tb-pin { position:absolute; top:50%; transform:translateY(-50%); margin-left:.6rem; font-size:.8rem; font-weight:800; color:var(--teal-ink); white-space:nowrap; }
.tb-v { font-size:1.5rem; font-weight:900; text-align:right; font-variant-numeric:tabular-nums; } .tb-v.bad { color:#C8102E; } .tb-v.good { color:var(--teal-ink); }
.lf { border-radius:20px; border:1px solid var(--edge); background:#fff; padding:.9rem 1.2rem .7rem; margin:.7rem 0 .2rem; }
.lf-hd { display:flex; align-items:center; gap:.6rem; font-size:.85rem; font-weight:800; color:var(--ink2); margin-bottom:.7rem; }
.lf-dot { width:10px; height:10px; border-radius:50%; background:#1FA08B; }
.lf-tot { margin-left:auto; font-size:.8rem; color:#fff; background:var(--navy); border-radius:999px; padding:.2rem .75rem; }
.lf-row { display:grid; grid-template-columns:13rem 1fr; gap:1rem; align-items:center; margin:.45rem 0; }
.lf-n { font-weight:800; font-size:.92rem; color:var(--ink2); display:flex; align-items:center; gap:.5rem; }
.lf-b { font-size:.62rem; font-weight:900; letter-spacing:.06em; border-radius:6px; padding:.12rem .4rem; }
.lf-b.llm { background:#EEF0FF; color:#4B4FD8; } .lf-b.sql { background:#E3F5F1; color:var(--teal-ink); }
.lf-tr { position:relative; height:30px; background:repeating-linear-gradient(90deg,#F6F9FC 0 24.9%,#EEF2F7 25% 25.2%); border-radius:8px; }
.lf-bar { position:absolute; top:3px; bottom:3px; border-radius:7px; display:flex; align-items:center; padding:0 .6rem; overflow:visible; }
.lf-bar.llm { background:#6B6FE8; } .lf-bar.sql { background:#1FA08B; }
.lf-bar span { color:#fff; font-size:.74rem; font-weight:800; white-space:nowrap; }
.lf-ax { display:flex; justify-content:space-between; margin-left:14rem; font-size:.68rem; color:var(--faint); margin-top:.2rem; }
.tiles { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:.7rem; margin:.6rem 0 .4rem; }
.tl { border-radius:18px; border:1px solid var(--edge); background:#fff; padding:1.1rem .8rem; text-align:center; box-shadow:0 8px 22px rgba(8,18,38,.05); }
.tl-ic { width:58px; height:58px; border-radius:18px; margin:0 auto .6rem; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(135deg,#081226 0%,#12796A 100%); color:#fff; }
.tl-t { font-weight:900; font-size:1rem; color:var(--ink2); line-height:1.25; } .tl-f { font-size:.74rem; font-weight:800; color:var(--teal-ink); margin-top:.35rem; }
@media (max-width:1100px) { .tiles { grid-template-columns:repeat(3,minmax(0,1fr)); } .pipe { flex-wrap:wrap; } .pp-ar { display:none; }
  .tb-row { grid-template-columns:1fr; } .lf-row { grid-template-columns:1fr; } .lf-ax { margin-left:0; } }
.dgm .sem rect { fill:#081226; stroke:#081226; } .dgm .sem .st1 { font-size:15px; font-weight:800; fill:#fff; }
.dgm .sem .st2 { font-size:12px; fill:#B8E6DC; }
.fail3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)) auto minmax(0,1.15fr); gap:.6rem; align-items:stretch; margin:.7rem 0 .4rem; }
.f3 { border-radius:16px; border:1px solid #F3C2C8; border-top:4px solid #C8102E; background:#fff; padding:.8rem .9rem; }
.f3.good { border:0; background:linear-gradient(135deg,#081226 0%,#12796A 100%); }
.f3-k { font-size:.62rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:#C8102E; }
.f3-t { font-weight:900; font-size:1.05rem; color:var(--ink2); margin:.15rem 0 .2rem; } .f3-d { font-size:.84rem; color:var(--muted); }
.f3.good .f3-k { color:#7FE3D0; } .f3.good .f3-t { color:#fff; font-size:1.2rem; } .f3.good .f3-d { color:#D6F3EC; }
.f3-ar { display:flex; align-items:center; font-size:1.6rem; color:var(--faint); font-weight:800; }
.layers { display:grid; gap:.45rem; margin-top:.4rem; }
.ly { display:grid; grid-template-columns:9.5rem 1fr; gap:.8rem; align-items:center; border-radius:14px; border:1px solid var(--edge); background:#fff; padding:.75rem 1rem; }
.ly.exa { background:#F2FBF9; border-color:#CDEBE4; } .ly.dark { background:#081226; border-color:#081226; }
.ly-n { font-weight:900; font-size:.95rem; color:var(--ink2); } .ly-t { font-size:.9rem; color:var(--muted); }
.ly.dark .ly-n { color:#fff; } .ly.dark .ly-t { color:#B8E6DC; }
.fan { border-radius:20px; border:1px solid var(--edge); background:#fff; padding:1rem 1.2rem .8rem; margin:.7rem 0 .3rem; }
.fn-row { display:grid; grid-template-columns:12rem 1fr; gap:1rem; align-items:center; margin:.5rem 0; }
.fn-l { font-weight:800; font-size:.95rem; color:var(--ink2); line-height:1.25; } .fn-l span { display:block; font-weight:600; font-size:.76rem; color:var(--faint); }
.fn-tr { height:38px; border-radius:10px; background:#F1F4F9; }
.fn-f { height:100%; border-radius:10px; display:flex; align-items:center; justify-content:flex-end; padding-right:.8rem; }
.fn-f span { color:#fff; font-weight:900; font-size:1.05rem; font-variant-numeric:tabular-nums; }
.fn-f.bad { background:linear-gradient(90deg,#FF7A85,#C8102E); } .fn-f.good { background:#1FA08B; }
.fn-foot { display:flex; align-items:center; gap:.8rem; flex-wrap:wrap; font-size:.88rem; color:var(--muted); margin-top:.6rem; }
.fn-foot b { color:var(--ink2); }
.fn-x { font-size:1.05rem; font-weight:900; color:#fff; background:#C8102E; border-radius:999px; padding:.2rem .8rem; }
.path5 { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.6rem; margin:.7rem 0 .4rem; position:relative; }
.p5 { border-radius:18px; border:1px solid var(--edge); background:#fff; padding:.9rem .8rem; text-align:center; }
.p5-n { width:34px; height:34px; border-radius:50%; margin:0 auto .4rem; display:flex; align-items:center; justify-content:center;
  font-weight:900; background:#EEF2F7; color:var(--ink2); }
.p5-t { font-weight:900; font-size:1.05rem; color:var(--ink2); } .p5-d { font-size:.8rem; color:var(--muted); margin-top:.1rem; }
.p5-s { display:inline-block; margin-top:.45rem; font-size:.66rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase;
  border-radius:999px; padding:.12rem .55rem; background:#F1F4F9; color:var(--faint); }
.p5.done { background:#F2FBF9; border-color:#9ED9CE; } .p5.done .p5-n { background:#1FA08B; color:#fff; } .p5.done .p5-s { background:#1FA08B; color:#fff; }
.p5.sv .p5-n { background:#081226; color:#fff; } .p5.sv .p5-s { background:#081226; color:#fff; }
@media (max-width:1100px) { .fail3 { grid-template-columns:1fr; } .f3-ar { display:none; } .path5 { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .fn-row, .ly { grid-template-columns:1fr; } }

/* ---- lighter palette: no heavy black blocks; Semantic Views gets its own soft indigo ---- */
.dgm .node.user rect { fill:#E2F4FF !important; stroke:#7CC8F0 !important; stroke-width:2 !important; }
.dgm .node.user .nt { fill:#0B1B34 !important; } .dgm .node.user .ns { fill:#0076AD !important; }
.dgm .node.user.on rect { stroke:#0076AD !important; stroke-width:3 !important; }
.dgm .sem rect { fill:#EEF0FF !important; stroke:#9EA3F0 !important; stroke-width:2 !important; }
.dgm .sem .st1 { fill:#3B3FB8 !important; } .dgm .sem .st2 { fill:#5B5F88 !important; }
.ly.dark { background:#EEF0FF !important; border-color:#C9CCF7 !important; }
.ly.dark .ly-n { color:#3B3FB8 !important; } .ly.dark .ly-t { color:#5B5F88 !important; }
.f3.good { background:linear-gradient(135deg,#E3F5F1 0%,#F2FBF9 100%) !important; border:2px solid #1FA08B !important; }
.f3.good .f3-k { color:#12796A !important; } .f3.good .f3-t { color:#0B1B34 !important; } .f3.good .f3-d { color:#12796A !important; }
.p5.sv { background:#F5F6FF; border-color:#C9CCF7; }
.p5.sv .p5-n { background:#6B6FE8 !important; } .p5.sv .p5-s { background:#6B6FE8 !important; }
.pp-chip, .lf-tot { background:#12796A !important; }
.dgm .pill rect { fill:#3A4A63; }
/* ---- a bigger header banner ---- */
.hero-slim { padding:1.35rem 1.8rem !important; border-radius:22px !important; margin-bottom:1.1rem !important; gap:1.2rem !important; }
.hs-t { font-size:1.75rem !important; line-height:1.25 !important; letter-spacing:-.02em; }
.hs-t span { display:block; font-size:1.05rem !important; margin:.35rem 0 0 !important; color:rgba(247,251,255,.78) !important; letter-spacing:0; }
.hs-m { gap:.6rem !important; }
.hs-pill { font-size:.78rem !important; padding:.4rem .95rem !important; letter-spacing:.08em !important; }
.dgm .vialbl { font-size:12px; font-weight:800; fill:#12796A; font-style:italic; }
.dgm .pill rect { fill:#081226; } .dgm .pill text { font-size:13px; font-weight:800; fill:#fff; }
.dgm .pill.on rect { fill:#1FA08B; }
.dgm .flowlbl { font-size:12.5px; font-weight:800; fill:#12796A; }
.dgm .flowlbl.back { fill:#0076AD; }
.qk { text-transform:uppercase; letter-spacing:.14em; font-size:.7rem; font-weight:800; color:var(--teal-ink); margin:.1rem 0 .4rem; }
.ans { border-radius:20px; border:1px solid var(--edge); background:#fff; box-shadow:var(--shadow); padding:1rem 1.15rem; margin-top:.6rem; }
.ans .q { font-size:1.25rem; font-weight:800; line-height:1.3; color:var(--ink2); margin-bottom:.1rem; }
.ans .src { font-size:.85rem; color:var(--muted); }
.big3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.55rem; margin:.8rem 0 .7rem; }
.b3 { border-radius:14px; background:#F6F9FC; padding:.6rem .8rem; }
.b3 .v { font-size:1.6rem; font-weight:800; color:var(--ink2); line-height:1.1; font-variant-numeric:tabular-nums; }
.b3 .k { font-size:.78rem; color:var(--muted); margin-top:.15rem; line-height:1.3; }
.b3.hl { background:#E3F5F1; } .b3.hl .v { color:var(--teal-ink); }
.did { margin:.2rem 0 0; }
.did .k { text-transform:uppercase; letter-spacing:.12em; font-size:.64rem; font-weight:800; color:var(--teal-ink); margin-bottom:.3rem; }
.did ul { margin:0 0 0 1.1rem; padding:0; } .did li { margin:.25rem 0; font-size:.95rem; line-height:1.45; color:var(--ink); }
.cached { border-radius:10px; background:#FDF3F4; color:var(--no); font-size:.8rem; font-weight:700; padding:.35rem .6rem; margin-top:.5rem; }
.tk { border-radius:12px; border:1px solid var(--edge); padding:.45rem .7rem; margin-bottom:.35rem; font-size:.88rem; line-height:1.4; }
.tk.churn { border-left:4px solid var(--no); }
.tk .tag { font-size:.6rem; font-weight:800; text-transform:uppercase; letter-spacing:.08em; border-radius:999px;
  padding:.05rem .45rem; background:#F1F4F9; color:var(--muted); margin-right:.35rem; }
.tk.churn .tag { background:var(--no); color:#fff; }
.cu { display:grid; grid-template-columns:minmax(0,1fr) 5.5rem; gap:.6rem; align-items:center; border-bottom:1px solid #EEF2F7; padding:.4rem 0; }
.cu:last-child { border-bottom:0; }
.cu .nm { font-weight:800; font-size:.92rem; } .cu .mt { font-size:.78rem; color:var(--muted); font-style:italic; line-height:1.35; }
.cu .v { text-align:right; font-weight:800; font-variant-numeric:tabular-nums; }
.hint { font-size:.95rem; color:var(--muted); line-height:1.55; }
.punch { border-radius:18px; margin:1rem 0 .4rem; padding:1.1rem 1.3rem;
  background:linear-gradient(135deg,#081226 0%,#10203F 55%,#12796A 100%); box-shadow:0 14px 34px rgba(8,18,38,.22); }
.punch .pt { color:#fff; font-size:1.75rem; font-weight:900; letter-spacing:-.02em; line-height:1.15; }
.punch .pv { color:#fff; font-size:1.15rem; font-weight:700; margin-top:.35rem; opacity:.92; }
.punch .pv::first-line { }
.punch .ps { color:#7FE3D0; font-size:.82rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; margin-top:.45rem; }
.why6 { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:.6rem; margin:1.4rem 0 .4rem; }
.w6 { border-radius:14px; background:#fff; border:1px solid var(--edge); padding:.7rem .8rem; }
.w6 .t { font-weight:800; font-size:.9rem; line-height:1.3; } .w6 .d { font-size:.8rem; color:var(--muted); margin-top:.25rem; line-height:1.4; }
.w6 .f { font-size:.72rem; font-weight:800; color:var(--teal-ink); margin-top:.35rem; }
div[data-testid="stVerticalBlock"] .stButton > button { justify-content:flex-start !important; text-align:left !important; }
.st-key-qbtns .stButton > button { min-height:2.8rem !important; font-size:.95rem !important; }
.st-key-qbtns .stButton > button { justify-content:flex-start !important; padding-left:1rem !important; }
.st-key-qbtns .stButton > button > div, .st-key-qbtns .stButton > button [data-testid="stMarkdownContainer"] {
  justify-content:flex-start !important; text-align:left !important; width:100%; }
.st-key-qbtns .stButton > button p { text-align:left !important; width:100%; margin:0; }
.dmap { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.6rem; margin:0 0 1rem; }
.dm { border-radius:16px; border:1px solid var(--edge); background:#fff; padding:.7rem .9rem; }
.dm.exa { background:#F2FBF9; border-color:#CDEBE4; }
.dm .dk { text-transform:uppercase; letter-spacing:.12em; font-size:.64rem; font-weight:800; color:var(--teal-ink); }
.dm .ds { font-weight:800; font-size:1.1rem; margin:.1rem 0 .15rem; } .dm .ds span { font-weight:600; font-size:.82rem; color:var(--faint); }
.dm .dt { font-family:'JetBrains Mono',monospace; font-size:.74rem; color:#0076AD; }
.dm .dd { font-size:.8rem; color:var(--muted); margin-top:.2rem; line-height:1.35; }
.cmpk { margin:1.6rem 0 .4rem; }
@media (max-width:1300px) { .why6 { grid-template-columns:repeat(3,minmax(0,1fr)); } .dmap { grid-template-columns:repeat(2,minmax(0,1fr)); } }
</style>"""
