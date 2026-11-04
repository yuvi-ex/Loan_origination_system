"""Train the application scorecard on the historical book and write it as a TABLE, not a pickle.

A logistic regression on seven currency-free features (ratios, counts, a bureau score), trained on loans issued up to
2015 and checked on 2016-2018 (out of time). Excluded on purpose: age, gender, marital status, postcode, state and
job title (protected attributes or proxies for them), and Lending Club's own grade and rate (that would be copying
someone else's risk decision). Card utilisation and past delinquencies were tried and DROPPED: both took
the wrong sign (more risk -> better score) because the bureau score already carries them, and a scorecard a credit
committee cannot defend is not one it will sign. Because the model is linear, each feature's contribution to the score is exact:
points = -FACTOR x weight x (value - book average). Those contributions ARE the reason codes (for a linear model they
equal the SHAP values). Writes .work/scorecard.csv and .work/scorecard_quality.json.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
# feature, clip low, clip high, reason code shown to the applicant / underwriter when it pulls the score DOWN
FEATURES = [
    ("BUREAU_SCORE",   300, 850, "Credit bureau score below the book average"),
    ("FOIR_AFTER",       0,  60, "High share of income already committed to repayments (FOIR)"),
    ("LOAN_TO_INCOME",   0, 1.0, "Loan amount is large relative to income"),
    ("INQ_6M",           0,   6, "Several recent credit applications"),
    ("EMP_YEARS",        0,  10, "Short time with the current employer"),
    ("TERM_60",          0,   1, "Longer repayment term (60 months)"),
    ("PUB_REC",          0,   3, "Public record (judgement or insolvency)"),
]
PDO, BASE_SCORE, BASE_ODDS = 40, 600, 4.0          # 600 points at 4:1 good:bad, 40 points to double the odds
FACTOR = PDO / math.log(2)

b = pd.read_csv(ROOT / ".work" / "book.csv", parse_dates=["ISSUE_DATE"])
b["TERM_60"] = (b["TERM_MONTHS"] == 60).astype(int)
X = np.column_stack([b[f].clip(lo, hi) for f, lo, hi, _ in FEATURES])
y = b["DEFAULTED"].values
train = (b["ISSUE_DATE"].dt.year <= 2015).values
m = LogisticRegression(max_iter=2000, C=1.0)
mu, sd = X[train].mean(0), X[train].std(0)
m.fit((X[train] - mu) / sd, y[train])
w = m.coef_[0] / sd                                   # weights on the raw (clipped) scale
b0 = m.intercept_[0] - (m.coef_[0] * mu / sd).sum()
p = 1 / (1 + np.exp(-(b0 + X @ w)))
auc_in, auc_oot = roc_auc_score(y[train], p[train]), roc_auc_score(y[~train], p[~train])
gini = 2 * auc_oot - 1
book_mean = X.mean(0)

rows = [dict(FEATURE=f, CLIP_LOW=lo, CLIP_HIGH=hi, WEIGHT=round(float(wi), 8), BOOK_MEAN=round(float(mi), 6),
             REASON=r, ORDINAL=i + 1) for i, ((f, lo, hi, r), wi, mi) in enumerate(zip(FEATURES, w, book_mean))]
rows.append(dict(FEATURE="_INTERCEPT", CLIP_LOW=0, CLIP_HIGH=0, WEIGHT=round(float(b0), 8), BOOK_MEAN=0, REASON="", ORDINAL=0))
pd.DataFrame(rows).to_csv(ROOT / ".work" / "scorecard.csv", index=False, lineterminator="\n")
q = dict(train_loans=int(train.sum()), test_loans=int((~train).sum()), auc_train=round(auc_in, 4), auc_out_of_time=round(auc_oot, 4),
         gini_out_of_time=round(gini, 4), pdo=PDO, base_score=BASE_SCORE, base_odds=BASE_ODDS, factor=round(FACTOR, 6))
(ROOT / ".work" / "scorecard_quality.json").write_text(json.dumps(q, indent=1))
print(json.dumps(q, indent=1))
for r in rows:
    print(f'{r["FEATURE"]:15s} w={r["WEIGHT"]:+.5f} mean={r["BOOK_MEAN"]:.3f}')
score = BASE_SCORE + FACTOR * (np.log((1 - p) / p) - math.log(BASE_ODDS))
s = pd.Series(score)
print(s.describe(percentiles=[.05, .1, .25, .5, .75, .9, .95]).round(1))
band = pd.cut(s, [0, 540, 560, 580, 600, 620, 640, 660, 999])
print(pd.DataFrame({"band": band, "d": y}).groupby("band", observed=True)["d"].agg(["count", "mean"]).round(3))
