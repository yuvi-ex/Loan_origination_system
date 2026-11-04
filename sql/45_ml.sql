-- The challenger model: gradient boosting trained in Python (data/train_ml.py), scored INSIDE Exasol by a Python UDF.
-- The pickle lives in BucketFS (/buckets/bfsdefault/default/los/ml/ml_model.pkl); the UDF loads it once per
-- UDF process and scores whole batches. The scorecard still decides; this model's PD is a second opinion beside it.
-- Needs the PYTHON3 script language container (exasol slc install PYTHON3; restarts the database).
CREATE SCHEMA IF NOT EXISTS LOS_ML;

-- what the model is, for the screen (numbers from .work/ml_quality.json; setup/06_ml.sh rewrites the row)
CREATE TABLE IF NOT EXISTS LOS_ML.MODEL (
  MODEL_VERSION VARCHAR(40), ALGORITHM VARCHAR(80), INPUTS VARCHAR(400), TRAIN_LOANS DECIMAL(9,0), TEST_LOANS DECIMAL(9,0),
  AUC_OUT_OF_TIME DOUBLE, GINI_OUT_OF_TIME DOUBLE, TRAINED_AT TIMESTAMP);

-- the application's purpose in the Lending Club categories the model was trained on; anything unmapped scores as 'other'
CREATE OR REPLACE TABLE LOS_ML.PURPOSE_MAP (APP_PURPOSE VARCHAR(60), BOOK_PURPOSE VARCHAR(40));
INSERT INTO LOS_ML.PURPOSE_MAP VALUES
  ('Home renovation', 'home_improvement'), ('Wedding', 'wedding'), ('Medical', 'medical'), ('Education', 'educational'),
  ('Higher education', 'educational'), ('Debt consolidation', 'debt_consolidation'), ('Travel', 'vacation'),
  ('Vehicle', 'car'), ('Business', 'small_business');

-- batched: one call scores any number of rows (the whole book, or every application)
CREATE OR REPLACE PYTHON3 SET SCRIPT LOS_ML.PREDICT_PD(
  ROW_KEY VARCHAR(40), BUREAU_SCORE DOUBLE, FOIR_AFTER DOUBLE, LOAN_TO_INCOME DOUBLE, INQ_6M DOUBLE, EMP_YEARS DOUBLE,
  TERM_60 DOUBLE, PUB_REC DOUBLE, PURPOSE VARCHAR(40))
EMITS (ROW_KEY VARCHAR(40), ML_PD DOUBLE) AS
import joblib
import numpy as np
import pandas as pd

# A pickle can run code when loaded: load only a model you trained yourself (setup/06_ml.sh). Anyone who can
# write this BucketFS path could run code inside the UDF.
BUNDLE = joblib.load("/buckets/bfsdefault/default/los/ml/ml_model.pkl")      # once per UDF process
MODEL, CODES = BUNDLE["model"], {p: i for i, p in enumerate(BUNDLE["purposes"])}
CLIPS, OTHER = np.array(BUNDLE["clips"], dtype=float), CODES["other"]

def run(ctx):
    while True:
        df = ctx.get_dataframe(num_rows=100000)
        if df is None or len(df) == 0:
            break
        x = df.iloc[:, 1:8].astype(float).fillna(0).to_numpy()
        x = np.clip(x, CLIPS[:, 0], CLIPS[:, 1])
        purpose = df.iloc[:, 8].map(CODES).fillna(OTHER).to_numpy(dtype=float)
        pd_ = MODEL.predict_proba(np.column_stack([x, purpose]))[:, 1]
        ctx.emit(pd.DataFrame({"ROW_KEY": df.iloc[:, 0].astype(str), "ML_PD": pd_}))
        if len(df) < 100000:
            break
/

-- one row at a time, for a SELECT list (one application; per-row overhead makes it the wrong tool for the book)
CREATE OR REPLACE PYTHON3 SCALAR SCRIPT LOS_ML.ML_PD(
  BUREAU_SCORE DOUBLE, FOIR_AFTER DOUBLE, LOAN_TO_INCOME DOUBLE, INQ_6M DOUBLE, EMP_YEARS DOUBLE, TERM_60 DOUBLE,
  PUB_REC DOUBLE, PURPOSE VARCHAR(40))
RETURNS DOUBLE AS
import joblib
import numpy as np

BUNDLE = joblib.load("/buckets/bfsdefault/default/los/ml/ml_model.pkl")
MODEL, CODES = BUNDLE["model"], {p: i for i, p in enumerate(BUNDLE["purposes"])}
CLIPS = np.array(BUNDLE["clips"], dtype=float)

def run(ctx):
    x = np.array([[ctx.BUREAU_SCORE, ctx.FOIR_AFTER, ctx.LOAN_TO_INCOME, ctx.INQ_6M, ctx.EMP_YEARS, ctx.TERM_60, ctx.PUB_REC]], dtype=float)
    x = np.clip(np.nan_to_num(x), CLIPS[:, 0], CLIPS[:, 1])
    code = CODES.get(ctx.PURPOSE, CODES["other"])
    return float(MODEL.predict_proba(np.column_stack([x, [[code]]]))[0, 1])
/

-- the model's inputs for every application, from the same features the scorecard uses (LIVE policy)
CREATE OR REPLACE VIEW LOS_ML.APPLICATION_INPUTS AS
SELECT a.APP_ID, a.X_BUREAU, a.X_FOIR, a.X_LTI, a.X_INQ, a.X_EMP, a.X_TERM, a.X_PUB,
       COALESCE(m.BOOK_PURPOSE, 'other') AS BOOK_PURPOSE
FROM LOS_CORE.APPLICATION_FEATURES a
JOIN LOS_CORE.APPLICATION_FACTS f ON f.APP_ID = a.APP_ID
LEFT JOIN LOS_ML.PURPOSE_MAP m ON m.APP_PURPOSE = f.PURPOSE
WHERE a.POLICY_STATUS = 'LIVE';

-- every historical loan's ML PD, written by one INSERT ... SELECT PREDICT_PD(...) (the LOS service op ml_score_book)
CREATE TABLE IF NOT EXISTS LOS_BOOK.ML_SCORES (LOAN_ID DECIMAL(12,0), ML_PD DOUBLE);
CREATE TABLE IF NOT EXISTS LOS_ML.RUNS (RUN_AT TIMESTAMP, ROWS_SCORED DECIMAL(12,0), SECONDS DOUBLE, MODEL_VERSION VARCHAR(40));

-- champion vs challenger on the loans neither model was trained on (issued 2016-2018), the way a credit committee
-- compares models: both obey the LIVE policy's FOIR cap, both approve the SAME number of loans (as many as the
-- scorecard's cut-off approves), then look at the loans where they disagree (the swap sets)
CREATE OR REPLACE VIEW LOS_ML.CHALLENGER AS
WITH lp AS (SELECT * FROM LOS_POLICY.POLICY WHERE STATUS = 'LIVE'),
t AS (
  SELECT s.LOAN_ID, s.SCORE, m.ML_PD, s.DEFAULTED, s.NET_CASH, s.FUNDED_AMOUNT,
         CASE WHEN s.SCORE >= lp.DECLINE_BELOW THEN 1 ELSE 0 END AS SC_APPROVE
  FROM LOS_BOOK.SCORED s JOIN LOS_BOOK.ML_SCORES m ON m.LOAN_ID = s.LOAN_ID CROSS JOIN lp
  WHERE s.ISSUE_YEAR >= 2016 AND s.FOIR_AFTER <= lp.FOIR_CAP),
r AS (
  SELECT t.*, CASE WHEN ROW_NUMBER() OVER (ORDER BY ML_PD, LOAN_ID) <= SUM(SC_APPROVE) OVER () THEN 1 ELSE 0 END AS ML_APPROVE
  FROM t)
SELECT SC_APPROVE, ML_APPROVE, COUNT(*) AS LOANS, SUM(DEFAULTED) AS DEFAULTS, SUM(FUNDED_AMOUNT) AS LENT, SUM(NET_CASH) AS NET_CASH
FROM r GROUP BY SC_APPROVE, ML_APPROVE;
