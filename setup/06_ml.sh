#!/usr/bin/env bash
# The challenger model: train it (pinned to the library versions inside Exasol), put it in BucketFS, create the UDFs and
# views (sql/45_ml.sql), record what it is, score the whole book once, and give the app logins access.
# Needs the PYTHON3 script language container: exasol slc install PYTHON3 --auto-approve (restarts the database).
#   setup/06_ml.sh            reuse .work/ml_model.pkl if it exists
#   setup/06_ml.sh --retrain  train again
source "$(dirname "$0")/common.sh"
ENV="$WORK/mlenv"

say "1. Training environment (numpy 1.26.4, scikit-learn 1.7.2: the versions in Exasol's PYTHON3 container)"
# install every time (fast when nothing changed), so a half-built environment from an interrupted run is repaired
[ -x "$ENV/bin/python" ] || uv venv --python 3.12 "$ENV" >/dev/null
uv pip install --quiet --python "$ENV/bin/python" numpy==1.26.4 scikit-learn==1.7.2 pandas==2.3.2 joblib==1.5.3 scipy==1.16.2
ok "$("$ENV/bin/python" -c 'import sklearn, numpy; print("sklearn", sklearn.__version__, "numpy", numpy.__version__)')"

say "2. Train"
if [ "${1:-}" = "--retrain" ] || [ ! -f "$WORK/ml_model.pkl" ]; then
  "$ENV/bin/python" "$ROOT/data/train_ml.py" | grep -E 'auc|iterations'
fi
ok "$(python3 -c "import json; q = json.load(open('$WORK/ml_quality.json')); print('out-of-time AUC', q['auc_out_of_time'])")"

say "3. Model into BucketFS"
mkdir -p "$BFS/default/los/ml"
cp "$WORK/ml_model.pkl" "$BFS/default/los/ml/"
sleep 3; ok "/buckets/bfsdefault/default/los/ml/ml_model.pkl"

say "4. UDFs, views, tables (sql/45_ml.sql)"
xfile "$ROOT/sql/45_ml.sql"
Q=$(python3 -c "import json; print(json.dumps(json.load(open('$WORK/ml_quality.json'))))")
read -r VER AUC GINI TRN TST <<<"$(python3 -c "import json; q = json.loads('''$Q'''); print(q['version'], q['auc_out_of_time'], q['gini_out_of_time'], q['train_loans'], q['test_loans'])")"
xsql "DELETE FROM LOS_ML.MODEL" >/dev/null
xsql "INSERT INTO LOS_ML.MODEL VALUES ('$VER', 'Gradient boosting (scikit-learn HistGradientBoosting), monotonic', 'the scorecard''s seven inputs + loan purpose', $TRN, $TST, $AUC, $GINI, CURRENT_TIMESTAMP)" >/dev/null
ok "$VER, AUC $AUC"

say "5. Score the book inside Exasol"
T0=$(python3 -c 'import time; print(time.time())')
xsql "DELETE FROM LOS_BOOK.ML_SCORES" >/dev/null
xsql "$(cd "$ROOT/service" && python3 -c 'import sqlq; print(sqlq.Q_SCORE_BOOK)')" >/dev/null
SECS=$(python3 -c "import time; print(round(time.time() - $T0, 1))")
N=$(xsql "SELECT COUNT(*) FROM LOS_BOOK.ML_SCORES" | tail -1)
xsql "INSERT INTO LOS_ML.RUNS VALUES (CURRENT_TIMESTAMP, $N, $SECS, '$VER')" >/dev/null
ok "$N loans scored in ${SECS} s"

say "6. App logins"
"$PY" "$ROOT/setup/05_governance.py"
