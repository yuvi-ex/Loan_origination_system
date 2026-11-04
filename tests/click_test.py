"""Headless click-through of the Loan Origination System console: every tab, three live applications, review, sign,
countersign, a drag-and-drop upload, the insights tab and the tamper test. Screenshots go to <outdir>; exits 1 on any
failure or browser console error. Needs playwright (requirements.txt) and: .venv/bin/python -m playwright install chromium
    .venv/bin/python tests/click_test.py <outdir> [steps]
steps: over how ananya karthik review sign divya upload risk sem nopan audit (default: all but nopan)
Run setup/reset_demo.sh afterwards: the test leaves its uploads and signatures behind."""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from los_config import CFG  # noqa: E402
URL = f"http://127.0.0.1:{CFG['DASH_SERVER_PORT']}/apps/{CFG['DASH_APP']}/"
PACKS = ROOT / "data" / "packs"
if len(sys.argv) < 2:
    sys.exit(__doc__)
out = sys.argv[1]
steps = sys.argv[2:] or ["over", "how", "karthik", "review", "sign", "divya", "upload", "risk", "sem", "audit"]
errs, T = [], {}


def snap(pg, name):
    h = pg.evaluate("() => Math.max(document.body.scrollHeight, document.querySelector('.page').scrollHeight)")
    pg.set_viewport_size({"width": 1600, "height": min(h + 40, 9000)}); time.sleep(0.8)
    pg.screenshot(path=f"{out}/{name}.png")
    pg.set_viewport_size({"width": 1600, "height": 1100})


def tab(pg, label):
    pg.get_by_text(label, exact=True).click(); time.sleep(1.2)


def run_pack(pg, label, name):
    tab(pg, "3 · New application")
    t = time.time()
    pg.locator("button", has_text=label).first.click()
    pg.wait_for_selector(".stp li.run", timeout=30000)
    pg.wait_for_selector("text=Upload to decision", timeout=120000)
    T[name + "_pipeline"] = round(time.time() - t, 1)
    pg.wait_for_selector(f".banner:has-text('{label}')", timeout=60000); time.sleep(1.5)
    T[name + "_case"] = round(time.time() - t, 1)
    snap(pg, name)


with sync_playwright() as p:
    try:
        b = p.chromium.launch(headless=True)                     # playwright's own Chromium
    except Exception:  # noqa: BLE001 - not downloaded: use an installed Google Chrome
        b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1600, "height": 1100})
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(URL); pg.wait_for_selector(".hw-pic", timeout=120000); time.sleep(1.5)
    for s in steps:
        if s == "over":
            snap(pg, "1_overview")
        elif s == "how":
            tab(pg, "2 · How it works"); pg.wait_for_selector(".hw-pic", timeout=30000); snap(pg, "1b_how")
        elif s == "karthik":
            run_pack(pg, "Karthik Raghunathan", "2_karthik_scored")
            T["karthik_ml"] = pg.locator(".ck", has_text="Credit history").first.inner_text().split("ML second opinion:")[-1][:60].strip()
        elif s == "review":
            t = time.time()
            inc = pg.locator(".ck.review").first
            inc.locator("input.dash-input-element").fill("Bonus is one-off; regular salary verified in bank")
            inc.get_by_role("button", name="Mark as reviewed").click()
            pg.wait_for_selector("text=Re-scored live on regular salary", timeout=60000); T["rescore"] = round(time.time() - t, 1)
            time.sleep(1)
            pg.locator(".ck.review").first.get_by_role("button", name="Mark as reviewed").click()
            pg.wait_for_selector("#dp-go", timeout=30000); time.sleep(1)
            snap(pg, "3_reviewed")
        elif s == "sign":
            pg.click("#dp-go"); pg.wait_for_selector("#cs-go", timeout=30000); time.sleep(1)
            snap(pg, "4_signed_first")
            pg.click("#cs-go"); pg.wait_for_selector("text=Final:", timeout=30000); time.sleep(1)
            snap(pg, "5_countersigned")
        elif s == "ananya":
            run_pack(pg, "Ananya Krishnan", "6b_ananya_noncustomer")
        elif s == "divya":
            run_pack(pg, "Divya Ramesh", "6_divya_auto")
        elif s == "upload":
            tab(pg, "3 · New application")
            files = sorted(str(f) for f in (PACKS / "karthik-raghunathan").glob("*.pdf"))
            t = time.time()
            pg.set_input_files("#up input[type=file]", files)
            pg.wait_for_selector(".stp li.run", timeout=30000)
            pg.wait_for_selector("text=Upload to decision", timeout=120000); T["upload_pipeline"] = round(time.time() - t, 1)
            pg.wait_for_selector(".banner", timeout=60000); time.sleep(1)
            snap(pg, "7_uploaded_files")
        elif s == "risk":
            tab(pg, "4 · LOS insights")
            pg.wait_for_selector("#ins-out .in-ls", timeout=60000); time.sleep(1)
            snap(pg, "8_insights")
        elif s == "sem":
            tab(pg, "5 · Semantic layer & contracts")
            pg.wait_for_selector("#sem-out .hw-pic", timeout=60000); time.sleep(1); snap(pg, "8c_semantic")
        elif s == "nopan":
            tab(pg, "3 · New application")
            files = sorted(str(f) for f in (PACKS / "karthik-raghunathan").glob("*.pdf") if "pan_card" not in f.name)
            t = time.time()
            pg.set_input_files("#up input[type=file]", files)
            pg.wait_for_selector(".stp li.run", timeout=30000)
            pg.wait_for_selector("text=Upload to decision", timeout=120000); T["nopan_pipeline"] = round(time.time() - t, 1)
            pg.wait_for_selector(".banner", timeout=60000); time.sleep(1)
            T["nopan_data"] = pg.locator(".ck", has_text="Data contracts").first.inner_text()[:160]
            snap(pg, "7b_no_pan")
        elif s == "audit":
            tab(pg, "6 · Audit trail")
            pg.wait_for_selector(".tbl", timeout=30000)
            pg.click("#tamper"); pg.wait_for_selector("text=Exasol refused it", timeout=30000); time.sleep(1)
            snap(pg, "9_audit")
    b.close()
print("timings", T)
print("console errors", errs[:10])
sys.exit(1 if errs else 0)
