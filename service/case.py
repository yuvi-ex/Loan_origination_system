"""One application's facts from every system, for the console's review checklist (built in ../dash/checklist.py).
The salary credits, the customer record and the application are read LIVE; the rest from the facts copy and views.
"""

import sqlq as S
import xdb


def _one(r):
    return (r["rows"] or [{}])[0]


def load(app):
    """Every fact the checklist needs. The salary credits, the customer record and the application are read LIVE."""
    c = _one(xdb.run(S.q_case(app), key=f"case_{app}"))
    if not c:
        return None
    res = {
        "c": c,
        "app": _one(xdb.run(f"SELECT * FROM LOS_SRC.APPLICATIONS WHERE APP_ID = {xdb.q(app)}", key=f"appl_{app}")),
        "hits": xdb.run(S.q_hits(app), key=f"hits_{app}")["rows"],
        "contrib": xdb.run(S.q_contrib(app), key=f"contrib_{app}")["rows"],
        "salary": xdb.run(S.q_salary(app), key=f"sal_{app}"),
        "pay": _one(xdb.run(S.q_payslip(app), key=f"pay_{app}")),
        "lines": xdb.run(S.q_lines(app), key=f"lines_{app}")["rows"],
        "idp": _one(xdb.run(S.q_idp(app), key=f"idp_{app}")),
        "letter": _one(xdb.run(S.q_letter(app), key=f"letter_{app}")),
        "bureau": _one(xdb.run(S.q_bureau(app), key=f"bur_{app}")),
        "bureau_report": _one(xdb.run(S.q_bureau_report(app), key=f"burrep_{app}")),      # the API call: report id, status, ms
        "cust": _one(xdb.run(S.q_customer(c.get("SALARY_ACCOUNT")), key=f"cust_{app}")),
        "docs": xdb.run(S.q_docs(app), key=f"docs_{app}")["rows"],
        "auth": xdb.run(S.Q_AUTH, key="auth")["rows"],
        "policy": _one(xdb.run("SELECT * FROM LOS_POLICY.POLICY WHERE STATUS = 'LIVE'", key="policy_live")),
        "model": _one(xdb.run(S.Q_MODEL, key="model")),
        "ml": _one(xdb.run(S.q_ml_case(app), key=f"ml_{app}")),          # the challenger's second opinion (Python UDF)
        "ml_model": _one(xdb.run(S.Q_ML_MODEL, key="ml_model")),
        "contracts": xdb.run(S.q_contracts_app(app), key=f"contracts_{app}")["rows"],     # data contracts (LOS_SEM)
    }
    res["live"] = res["salary"]["live"]
    res["uploaded"] = sorted(f.name for f in (xdb.ROOT / ".work" / "uploads" / app).glob("*.pdf"))
    return res


def log_rows(app):
    return xdb.run(f"SELECT LOG_ID, DECIDED_AT, STEP, DECIDED_BY, ROLE_NAME, FINAL_DECISION, AMOUNT, RATE, NEEDS_SECOND_SIGN "
                   f"FROM LOS_OPS.DECISION_LOG WHERE APP_ID = {xdb.q(app)} ORDER BY LOG_ID")["rows"]


def rescore(app, income, amount, term):
    """The same scorecard, policy and rate bands with the underwriter's income: only the inputs change."""
    r = _one(xdb.run(S.q_whatif(app, float(income), float(amount), int(term))))
    r["INCOME"] = float(income)
    return r


