-- The model's metadata (written by data/train_scorecard.py's numbers; regenerate with setup/03_model.sh).
CREATE SCHEMA IF NOT EXISTS LOS_POLICY;
CREATE OR REPLACE TABLE LOS_POLICY.MODEL (
  MODEL_VERSION VARCHAR(40), TRAINED_ON VARCHAR(200), TRAIN_LOANS DECIMAL(9,0), TEST_LOANS DECIMAL(9,0),
  AUC_OUT_OF_TIME DOUBLE, GINI_OUT_OF_TIME DOUBLE, PDO DOUBLE, BASE_SCORE DOUBLE, BASE_ODDS DOUBLE, FACTOR DOUBLE,
  EXCLUDED VARCHAR(400));
INSERT INTO LOS_POLICY.MODEL VALUES ('PL-SCORECARD-2026.10', 'Lending Club loans issued 2007-2015',
  826596, 517845, 0.6722, 0.3443, 40, 600, 4.0, 57.707802,
  'age, gender, marital status, postcode, state, job title (protected or proxies); lender grade and rate (someone else''s decision); card utilisation and past delinquencies (wrong sign once the bureau score is in)');
