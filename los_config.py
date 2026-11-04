"""Settings for every Python part of the Loan Origination System: config.env, then config.local.env (git-ignored).

    from los_config import CFG, ROOT, vm_ip
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _read(p):
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


CFG = {**_read(ROOT / "config.env"), **_read(ROOT / "config.local.env")}
# Generated passwords of the demo source containers (setup/common.sh writes them on the first setup step).
SOURCES_ENV = ROOT / "secrets" / "sources.env"
RUNTIME = Path.home() / ".exasol" / "personal" / "deployments" / CFG["EXASOL_DEPLOYMENT"] / "local" / "runtime"


def vm_ip():
    """The Exasol Personal VM's address: the source containers' ports are published on it."""
    return json.loads((RUNTIME / "vm-runtime.json").read_text())["vm_ip"]


def port(name):
    return int(CFG[name])


def source_secret(name):
    """A source container password from secrets/sources.env, with a message that says how to create it."""
    sec = _read(SOURCES_ENV)
    if name not in sec:
        raise SystemExit(f"{name} missing from {SOURCES_ENV}: run setup/install.sh (its first steps create it)")
    return sec[name]
