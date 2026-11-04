-- The credit bureau, called live: a Python UDF calls the bureau's REST API (data/bureau_api.py, container
-- los-bureau-api in the VM) for one PAN and emits the report. The API address and key are in the CONNECTION
-- LOS_BUREAU_API (created by setup/08_bureau_api.sh from secrets/app_users.env): only this script may use it.
-- Every response is kept as received in BUREAU_REPORTS; the bureau pull (BUREAU_PULLS) is taken from it, so the API
-- is called once per application. The pre-loaded 2,400 applications keep their stored pulls.

CREATE TABLE IF NOT EXISTS LOS_SRC.BUREAU_REPORTS (
  APP_ID VARCHAR(20), PAN VARCHAR(10), CALLED_AT TIMESTAMP, HTTP_STATUS DECIMAL(3,0), REPORT_ID VARCHAR(40),
  BUREAU_SCORE DECIMAL(4,0), INQ_6M DECIMAL(3,0), PUB_REC DECIMAL(3,0), ACTIVE_LOANS DECIMAL(3,0), EXISTING_EMI DECIMAL(12,0),
  OLDEST_TRADE_YEARS DECIMAL(4,1), MS DECIMAL(9,0));

CREATE OR REPLACE PYTHON3 SCALAR SCRIPT LOS_SRC.BUREAU_API(PAN VARCHAR(10))
EMITS (PAN VARCHAR(10), HTTP_STATUS DECIMAL(3,0), REPORT_ID VARCHAR(40), BUREAU_SCORE DECIMAL(4,0), INQ_6M DECIMAL(3,0),
       PUB_REC DECIMAL(3,0), ACTIVE_LOANS DECIMAL(3,0), EXISTING_EMI DECIMAL(12,0), OLDEST_TRADE_YEARS DECIMAL(4,1), MS DECIMAL(9,0)) AS
import decimal
import json
import time
import urllib.error
import urllib.parse
import urllib.request


def run(ctx):
    c = exa.get_connection("LOS_BUREAU_API")           # address + API key, never in SQL
    url = c.address.rstrip("/") + "/v1/credit-report?pan=" + urllib.parse.quote((ctx.PAN or "").upper())
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"X-API-Key": c.password}), timeout=10) as r:
            d, code = json.load(r), r.status
    except urllib.error.HTTPError as e:
        d, code = {}, e.code
    except Exception:                                           # bureau unreachable: 503, the rules refer it (no record)
        d, code = {}, 503
    old = d.get("oldestTradeYears")
    ctx.emit(ctx.PAN, code, d.get("reportId"), d.get("score"), d.get("enquiries6m"), d.get("publicRecords"), d.get("activeLoans"),
             d.get("existingEmi"), None if old is None else decimal.Decimal(str(old)), round((time.time() - t) * 1000))
/
