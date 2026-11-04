"""Train the CHALLENGER model: gradient boosting on the scorecard's seven inputs plus the loan purpose, scored inside
Exasol by a UDF.

Same book, same clipping, same split as data/train_scorecard.py (issued up to 2015 = train, 2016-2018 = out of time), so
the two models are compared like for like. Measured out of time: the same seven inputs alone gain almost nothing
(AUC 0.6742 vs the scorecard's 0.6722); the purpose is what adds signal (0.6796), FOIR before the loan adds none.
Monotonic constraints keep it defensible: a higher bureau score can never raise the risk, a higher FOIR can never
lower it, and so on. The scorecard still decides; this model is a second opinion.

Run with the pinned env (.work/mlenv: numpy 1.26.4, scikit-learn 1.7.2, joblib 1.5.3 = the versions in Exasol's
PYTHON3 container), or the pickle will not load inside the database. Writes .work/ml_model.pkl and .work/ml_quality.json.
"""
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
# the scorecard's features and clips, in the order the UDF passes them; +1 = risk may only rise with it, -1 = only fall
FEATURES = [("BUREAU_SCORE", 300, 850, -1), ("FOIR_AFTER", 0, 60, 1), ("LOAN_TO_INCOME", 0, 1.0, 1), ("INQ_6M", 0, 6, 1),
            ("EMP_YEARS", 0, 10, -1), ("TERM_60", 0, 1, 1), ("PUB_REC", 0, 3, 1)]
if sklearn.__version__ != "1.7.2" or np.__version__ != "1.26.4":
    sys.exit(f"use .work/mlenv: sklearn {sklearn.__version__}, numpy {np.__version__} will not load in Exasol")

b = pd.read_csv(ROOT / ".work" / "book.csv", parse_dates=["ISSUE_DATE"])
b["TERM_60"] = (b["TERM_MONTHS"] == 60).astype(int)
PURPOSES = list(b["PURPOSE"].value_counts().index)        # Lending Club categories; anything unknown scores as "other"
purpose_code = b["PURPOSE"].map({c: i for i, c in enumerate(PURPOSES)}).values
X = np.column_stack([b[f].clip(lo, hi) for f, lo, hi, _ in FEATURES] + [purpose_code]).astype(float)
y = b["DEFAULTED"].values
train = (b["ISSUE_DATE"].dt.year <= 2015).values

t = time.time()
m = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=200,
                                   l2_regularization=1.0, monotonic_cst=[c for *_, c in FEATURES] + [0],
                                   categorical_features=[False] * len(FEATURES) + [True],
                                   early_stopping=True, validation_fraction=0.1, random_state=7)
m.fit(X[train], y[train])
secs = time.time() - t
p = m.predict_proba(X)[:, 1]
q = dict(model="HistGradientBoostingClassifier", version="PL-GBM-2026.10", features=[f for f, *_ in FEATURES] + ["PURPOSE"],
         monotonic=True, iterations=int(m.n_iter_), train_loans=int(train.sum()), test_loans=int((~train).sum()),
         auc_train=round(roc_auc_score(y[train], p[train]), 4), auc_out_of_time=round(roc_auc_score(y[~train], p[~train]), 4),
         train_secs=round(secs, 1), sklearn=sklearn.__version__, numpy=np.__version__)
q["gini_out_of_time"] = round(2 * q["auc_out_of_time"] - 1, 4)
joblib.dump({"model": m, "purposes": PURPOSES, "clips": [(lo, hi) for _, lo, hi, _ in FEATURES], "version": q["version"]},
            ROOT / ".work" / "ml_model.pkl")
(ROOT / ".work" / "ml_quality.json").write_text(json.dumps(q, indent=1))
print(json.dumps(q, indent=1))
