"""Client for the LOS service (service/los_api.py; its address comes from los_settings.py, written by deploy.py).

The console never connects to a database: every read, write, upload and extraction is a named operation on the
service, which signs in as the login the job needs. If the service is down, call() raises Down with a message the
page shows as is.
"""
import json
import urllib.error
import urllib.request

import los_settings

URL = los_settings.LOS_URL


class Down(Exception):
    pass


def call(fn, *args, timeout=180):
    body = json.dumps({"fn": fn, "args": args}, default=str).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        out = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        out = json.loads(e.read() or b"{}")
    except Exception as e:  # noqa: BLE001 - refused, timed out
        raise Down(f"The LOS service is not answering ({type(e).__name__}). Start it: service/run.sh") from e
    if not out.get("ok"):
        raise Down(out.get("error") or "The LOS service gave no answer. Restart it (service/run.sh); its log is .work/los_api.log")
    return out["result"]
