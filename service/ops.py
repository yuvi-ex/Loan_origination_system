"""The operations the console may ask for, and nothing else: no SQL comes from the caller, every statement is built
here, and each runs as the login whose privileges fit the job (uw, risk, intake). Application numbers, reviewers,
decisions and amounts are validated before they reach a statement.
"""
import json
import re

import case
import intake
import los_config
import sqlq as S
import xdb

APP_RX = re.compile(r"^APP-26-\d{6}$")
DECISIONS = {"APPROVE", "APPROVE_CONDITIONS", "DECLINE"}
REGULAR = "Use regular salary only (exclude one-time pay)"


def _app(a):
    if not APP_RX.match(str(a)):
        raise ValueError("not an application number")
    return a


def _authority():
    return {r["REVIEWER"]: r for r in xdb.run(S.Q_AUTH, key="auth")["rows"]}


def health():
    """The header's status pills. Core banking is checked with a plain TCP connect, NOT a query through the virtual
    schema: every Postgres virtual-schema query starts a JDBC import process in Exasol, and a probe every minute from
    each open page helped fill Exasol Personal's ETL channel registry ("Registry full", 2026-10-28), which stalled every
    Postgres import for 3 minutes per try."""
    out = {"exa": xdb.run("SELECT 1 AS X")["live"], "pg": _tcp(intake.vm_ip(), los_config.port('PG_PORT'))}
    try:
        intake._mongo().command("ping")
        out["mongo"] = True
    except Exception:  # noqa: BLE001
        out["mongo"] = False
    return out


def _tcp(host, port):
    import socket
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False


def overview():
    return {"pipe": xdb.run(S.Q_PIPELINE, key="pipeline")}


def queue():
    return xdb.run(S.Q_QUEUE_LOS, key="queue")["rows"]


def case_load(app):
    return case.load(_app(app))


def log_rows(app):
    return case.log_rows(_app(app))


def rescore_regular(app):
    """The income review's 'regular salary only': the payslip's gross minus its one-time lines, re-scored live."""
    d = case.load(_app(app))
    c = d["c"]
    one_time = sum(float(l["AMOUNT"]) for l in d["lines"] if l["KIND"] == "earning" and str(l["RECURRING"]).lower() in ("false", "0"))
    income = float(d["pay"].get("GROSS") or c["VERIFIED_GROSS"]) - one_time
    return case.rescore(app, income, c["AMOUNT_REQUESTED"], c["TERM_MONTHS"])


def sign(app, reviews, decision, amount, cond, reviewer):
    """The underwriter's decision, with every checklist review in NOTES. Needs a second signature above the signer's limit.

    DEMO SIMPLIFICATION: who signs is the name picked in the console ("Reviewing as"), not a login. The database does
    enforce that the log can only grow, but a real system must bind each signature to an authenticated user (for
    example one database login per underwriter), or anyone could sign as a senior underwriter."""
    _app(app)
    auth = _authority()
    if reviewer not in auth or decision not in DECISIONS:
        raise ValueError("unknown reviewer or decision")
    c = (xdb.run(S.q_case(app))["rows"] or [{}])[0]
    pol = (xdb.run("SELECT POLICY_VERSION FROM LOS_POLICY.POLICY WHERE STATUS = 'LIVE'", key="policy_live")["rows"] or [{}])[0]
    model = (xdb.run(S.Q_MODEL, key="model")["rows"] or [{}])[0]
    a = auth[reviewer]
    approve = decision != "DECLINE"
    amount = float(amount or 0)
    second = approve and (amount > float(a["MAX_AMOUNT"]) or (c.get("REVIEW_LEVEL") == "UW2" and a["REVIEW_LEVEL"] != "UW2"))
    regular = (reviews.get("income") or {}).get("resolution") == REGULAR
    basis = rescore_regular(app) if regular else {}
    notes = " | ".join(f'{k}: {v.get("resolution")}' + (f' ({v["note"]})' if v.get("note") else "") + f' [{v.get("by")} {v.get("at")}]'
                       for k, v in (reviews or {}).items())
    ml = (xdb.run(S.q_ml_case(app))["rows"] or [{}])[0]
    snap = json.dumps({"score": c["SCORE"], "band": c["BAND"], "foir": c["FOIR_PCT"], "pd_pct": c.get("PD_PCT"),
                       "ml_pd_pct": ml.get("ML_PD_PCT"), "rescored": basis or None}, default=str)
    return xdb.write(f"""INSERT INTO LOS_OPS.DECISION_LOG (APP_ID, DECIDED_AT, DECIDED_BY, ROLE_NAME, STEP, SYSTEM_DECISION, FINAL_DECISION,
        AMOUNT, RATE, TERM_MONTHS, INCOME_BASIS, OVERRIDE_FLAG, REASON_CODE, CONDITIONS, NOTES, RULES_FIRED, SCORE, POLICY_VERSION, MODEL_VERSION,
        NEEDS_SECOND_SIGN, FEATURE_SNAPSHOT) VALUES ({xdb.q(app)}, CURRENT_TIMESTAMP, {xdb.q(reviewer)}, {xdb.q(a["ROLE_NAME"])}, 'DECISION',
        {xdb.q(c["SYSTEM_DECISION"])}, {xdb.q(decision)}, {int(amount) if approve else 'NULL'}, {float(basis.get("RATE") or c["RATE"])},
        {int(c["TERM_MONTHS"])}, {int(basis.get("INCOME") or c.get("VERIFIED_GROSS") or 0)}, FALSE,
        {xdb.q("ONE_TIME_INCOME_EXCLUDED" if regular else "CHECKLIST_REVIEWED")}, {xdb.q(str(cond or "")[:400])}, {xdb.q(notes[:1990])},
        {xdb.q(c["RULES_FIRED"])}, {int(c["SCORE"])}, {int(pol.get("POLICY_VERSION") or 1)}, {xdb.q(model.get("MODEL_VERSION"))},
        {str(second).upper()}, {xdb.q(snap)})""", "uw")


def countersign(app, who):
    _app(app)
    auth = _authority()
    if who not in auth or auth[who]["REVIEW_LEVEL"] != "UW2":
        raise ValueError("not a senior underwriter")
    return xdb.write(f"""INSERT INTO LOS_OPS.DECISION_LOG (APP_ID, DECIDED_AT, DECIDED_BY, ROLE_NAME, STEP, SYSTEM_DECISION, FINAL_DECISION,
        AMOUNT, RATE, TERM_MONTHS, INCOME_BASIS, OVERRIDE_FLAG, REASON_CODE, CONDITIONS, RULES_FIRED, SCORE, POLICY_VERSION, MODEL_VERSION, NEEDS_SECOND_SIGN)
        SELECT APP_ID, CURRENT_TIMESTAMP, {xdb.q(who)}, {xdb.q(auth[who]["ROLE_NAME"])}, 'SECOND_SIGN', SYSTEM_DECISION, FINAL_DECISION, AMOUNT, RATE,
               TERM_MONTHS, INCOME_BASIS, OVERRIDE_FLAG, REASON_CODE, CONDITIONS, RULES_FIRED, SCORE, POLICY_VERSION, MODEL_VERSION, FALSE
        FROM LOS_OPS.DECISION_LOG WHERE APP_ID = {xdb.q(app)} AND STEP = 'DECISION'
        QUALIFY ROW_NUMBER() OVER (ORDER BY LOG_ID DESC) = 1""", "uw")



def insights():
    """Tab 4: what came in, where it went, which rules sent it to a person, and what the loan book says about those rules."""
    return {"status": xdb.run(S.Q_INS_STATUS, key="ins_status"), "rules": xdb.run(S.Q_INS_RULES, key="ins_rules"),
            "book": xdb.run(S.Q_INS_BOOK, key="ins_book"), "checks": xdb.run(S.Q_INS_CHECKS, key="ins_checks")}



def semantic():
    """The semantic layer and the data contracts: vocabulary, every contract with its breaches, the last full run."""
    return {"terms": xdb.run(S.Q_TERMS, key="terms")["rows"], "sum": xdb.run(S.Q_CONTRACT_SUMMARY, key="contract_sum"),
            "run": (xdb.run(S.Q_CONTRACT_LAST_RUN, key="contract_run")["rows"] or [{}])[0],
            "zero": (xdb.run(S.Q_ZERO_TXN_SCAN, key="zero_txn")["rows"] or [{}])[0]}



def audit():
    return {"log": xdb.run(S.Q_LOG)["rows"][:40], "rules": xdb.run(S.Q_RULES, key="rules")["rows"]}


TAMPER = {"update": "UPDATE LOS_OPS.DECISION_LOG SET FINAL_DECISION = 'DECLINE' WHERE LOG_ID IS NOT NULL",
          "delete": "DELETE FROM LOS_OPS.DECISION_LOG"}


def tamper(kind):
    """The demonstration: the underwriting login tries to change history. The database refuses (INSERT is all it has)."""
    return dict(xdb.write(TAMPER[kind], "uw"), sql=TAMPER[kind])
