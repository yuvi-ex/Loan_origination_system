#!/usr/bin/env python3
"""Deploy the Loan Origination System to dash-server (http://127.0.0.1:<DASH_SERVER_PORT>/apps/<DASH_APP>/, see config.env).

    .venv/bin/python dash/deploy.py

Idempotent: creates the app on the first run, replaces its files after that, deploys live (rolling back on a failed
health check) and prints the probes. The console holds no credentials: it calls the LOS service (../service), which
must be running (service/run.sh) for the page to show data.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from los_config import CFG, ROOT  # noqa: E402

APP, TITLE, PROFILE = CFG["DASH_APP"], "Loan Origination System", "starter-kit"      # PROFILE: dash-server's own Exasol profile
BASE = f"http://127.0.0.1:{CFG['DASH_SERVER_PORT']}"
MCP = f"{BASE}/mcp"
MODULES = ["app.py", "checklist.py", "fmt.py", "how.py", "insights.py", "los.py", "los_settings.py", "story.py", "theme.py", "page_css.py"]
REQUIREMENTS = f"# none: the console calls the LOS service (127.0.0.1:{CFG['LOS_PORT']}) for every read, write and extraction\n"
# one read-only smoke query for dash-server's own probes (its profile, not the app's logins)
QUERIES = {"pipeline": "SELECT SYSTEM_DECISION, COUNT(*) AS APPS FROM LOS_CORE.DECISIONS WHERE POLICY_STATUS = 'LIVE' GROUP BY SYSTEM_DECISION"}


def call(name, args):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(MCP, data=body, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    try:
        raw = urllib.request.urlopen(req, timeout=900).read().decode()
    except urllib.error.URLError as e:
        raise SystemExit(f"dash-server is not answering at {MCP} ({e.reason}). Install or start it (exakit marketplace dash-server; "
                         f"exakit status), then deploy again: setup/install.sh --from console") from None
    for line in raw.splitlines():
        if line.startswith("data: "):
            raw = line[6:]
    payload = json.loads(raw)
    if "error" in payload:
        raise SystemExit(f"{name} failed: {payload['error']}")
    res = payload["result"]
    text = "\n".join(c.get("text", "") for c in res.get("content", []))
    data = res.get("structuredContent") or {}
    if not data and "Result:" in text:
        data = json.loads(text[text.find("Result:") + 7:])
    if res.get("isError"):
        raise SystemExit(f"{name} failed:\n{text[:3000]}\n" + json.dumps(data.get("error", data), indent=1)[-6000:])
    return text.split("\n", 1)[0], data


def settings():
    """The hosted app cannot read config.env: its settings travel as a small module, also kept locally (git-ignored)."""
    (HERE / "los_settings.py").write_text(
        '"""Written by dash/deploy.py from config.env. Do not edit."""\n'
        f'LOS_URL = "http://127.0.0.1:{CFG["LOS_PORT"]}/rpc"\n'
        f'UPLOADS = {str(ROOT / ".work" / "uploads")!r}\n'
        f'REGION = {CFG["TEXTRACT_REGION"]!r}\n')


def files():
    settings()
    out = [{"path": m, "content": (HERE / m).read_text()} for m in MODULES]
    out.append({"path": "assets/exasol_logo_dark.svg", "content": (HERE / "assets" / "exasol_logo_dark.svg").read_text()})
    out += [{"path": f"queries/business/{k}.sql", "content": v.strip() + "\n"} for k, v in QUERIES.items()]
    out.append({"path": "requirements.txt", "content": REQUIREMENTS})
    manifest = {"name": APP, "title": TITLE, "route": f"/apps/{APP}",
                "description": "Loan origination: upload an application, Amazon Textract reads it, Exasol verifies it live against core banking (Postgres), the document store (MongoDB) and the bureau, scores it, and sends edge cases to a person with a review checklist.",
                "template": "exasol-analytics",
                "data_sources": {"primary": {"kind": "exasol", "profile": PROFILE, "auth_mode": "local_direct"}}}
    out.append({"path": "dash-app.json", "content": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"})
    return out


def main():
    fs = files()
    _, inv = call("apps_list", {})
    if APP not in {a.get("name") for a in inv.get("apps", [])}:
        head, _ = call("app_create_from_files", {"name": APP, "title": TITLE, "template": "exasol-analytics", "files": fs,
                                                 "start_immediately": False})
        print(f"create   : {head}")
    else:
        head, _ = call("app_put_files", {"name": APP, "files": fs})
        print(f"files    : {head} ({len(fs)} files)")
    head, v = call("app_validate", {"name": APP})
    print(f"validate : {head}")
    head, _ = call("app_deploy_draft", {"name": APP, "deployment_target": "live", "auto_rollback_on_health_failure": True})
    print(f"deploy   : {head}")
    _, h = call("app_run_healthcheck", {"name": APP, "target": "live"})
    for p in h.get("health", {}).get("probes", []):
        print(f"  {p.get('status'):10} {p.get('name')}")
    print(f"\n{BASE}/apps/{APP}/")


if __name__ == "__main__":
    main()
