"""Lending Club accepted loans 2007-2018Q4 -> the historical loan book (loans with a FINAL outcome only).

Source: the public Lending Club loan tape (mirrored at huggingface.co/datasets/codesignal/lending-club-loan-accepted).
Keeps only what underwriting can see at application time plus the realised cash flows, so the back-test uses
real money: NET_CASH = everything the borrower paid back minus what was lent. No zip code, no state, no
employment title: postcode and free-text job titles are proxies for protected attributes and never reach the model.
Writes .work/book.csv (LF line endings, no index) for exapump.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".work" / "dl" / "accepted.csv"
COLS = ["id", "issue_d", "term", "loan_amnt", "funded_amnt", "int_rate", "installment", "grade", "emp_length",
        "annual_inc", "verification_status", "dti", "revol_util", "delinq_2yrs", "inq_last_6mths", "pub_rec",
        "open_acc", "fico_range_low", "purpose", "loan_status", "total_pymnt", "total_rec_int", "recoveries"]

df = pd.read_csv(SRC, usecols=COLS, low_memory=False)
print("rows in tape", len(df))
df = df[df["loan_status"].isin(["Fully Paid", "Charged Off", "Default"])].copy()
df = df[(df["annual_inc"] > 0) & df["dti"].between(0, 100) & df["fico_range_low"].notna()]
df["ISSUE_DATE"] = pd.to_datetime(df["issue_d"], format="%b-%Y").dt.date
df["TERM_MONTHS"] = df["term"].str.extract(r"(\d+)").astype(int)
df["EMP_YEARS"] = (df["emp_length"].str.replace("< 1 year", "0").str.extract(r"(\d+)").astype(float).fillna(0))
df["DEFAULTED"] = (df["loan_status"] != "Fully Paid").astype(int)
# FOIR after the loan: existing debt service (Lending Club dti) + this loan's instalment, as % of gross monthly income
df["FOIR_AFTER"] = (df["dti"] + df["installment"] * 1200 / df["annual_inc"]).round(2)
df["LOAN_TO_INCOME"] = (df["loan_amnt"] / df["annual_inc"]).round(4)
df["NET_CASH"] = (df["total_pymnt"] - df["funded_amnt"]).round(2)
df["revol_util"] = df["revol_util"].fillna(df["revol_util"].median()).clip(0, 150)
for c in ("delinq_2yrs", "inq_last_6mths", "pub_rec", "open_acc"):
    df[c] = df[c].fillna(0).astype(int)
out = pd.DataFrame({
    "LOAN_ID": df["id"].astype(np.int64), "ISSUE_DATE": df["ISSUE_DATE"], "TERM_MONTHS": df["TERM_MONTHS"],
    "LOAN_AMOUNT": df["loan_amnt"], "FUNDED_AMOUNT": df["funded_amnt"], "INT_RATE": df["int_rate"],
    "INSTALMENT": df["installment"], "LC_GRADE": df["grade"], "EMP_YEARS": df["EMP_YEARS"].astype(int),
    "ANNUAL_INCOME": df["annual_inc"], "INCOME_VERIFIED": df["verification_status"].ne("Not Verified").astype(int),
    "DTI_BEFORE": df["dti"], "FOIR_AFTER": df["FOIR_AFTER"], "LOAN_TO_INCOME": df["LOAN_TO_INCOME"],
    "REVOL_UTIL": df["revol_util"], "DELINQ_2Y": df["delinq_2yrs"], "INQ_6M": df["inq_last_6mths"],
    "PUB_REC": df["pub_rec"], "OPEN_ACCOUNTS": df["open_acc"], "BUREAU_SCORE": df["fico_range_low"].astype(int),
    "PURPOSE": df["purpose"], "OUTCOME": df["loan_status"], "DEFAULTED": df["DEFAULTED"],
    "TOTAL_PAID": df["total_pymnt"].round(2), "INTEREST_PAID": df["total_rec_int"].round(2),
    "RECOVERIES": df["recoveries"].round(2), "NET_CASH": df["NET_CASH"]})
out.to_csv(ROOT / ".work" / "book.csv", index=False, lineterminator="\n")
print("final-outcome loans", len(out), "default rate", round(out["DEFAULTED"].mean() * 100, 2), "%")
print(out[["FOIR_AFTER", "BUREAU_SCORE", "LOAN_TO_INCOME", "REVOL_UTIL"]].describe(percentiles=[.05, .25, .5, .75, .9, .95]).round(2))
print(out.groupby(out["ISSUE_DATE"].map(lambda d: d.year))["DEFAULTED"].agg(["count", "mean"]).round(3))
