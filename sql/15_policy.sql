-- LOS_POLICY: the credit policy is DATA. The risk team changes these rows; no code changes, no redeploy.
-- Re-running this file resets the policy to version 1 (the demo's starting point).
CREATE SCHEMA IF NOT EXISTS LOS_POLICY;

-- The knobs. Exactly one LIVE row; the risk officer edits the DRAFT row, simulates it, then publishes it.
CREATE OR REPLACE TABLE LOS_POLICY.POLICY (
  POLICY_VERSION      DECIMAL(5,0),
  STATUS              VARCHAR(8),          -- LIVE | DRAFT | RETIRED
  FOIR_CAP            DECIMAL(5,2),        -- max % of verified gross income going to repayments, incl. this loan
  FOIR_NEAR_BAND      DECIMAL(5,2),        -- within this many points of the cap: a person looks at it
  APPROVE_FROM        DECIMAL(5,0),        -- score at or above: approve automatically
  DECLINE_BELOW       DECIMAL(5,0),        -- score below: decline. In between: the grey zone, referred
  ASSESSMENT_RATE     DECIMAL(5,2),        -- affordability is tested at this rate, whatever the priced rate
  BASE_RATE           DECIMAL(5,2),        -- benchmark rate; the price is base + the band's risk premium
  AUTO_APPROVE_LIMIT  DECIMAL(12,0),       -- above this amount a person signs, whatever the score
  MAX_LOAN            DECIMAL(12,0),
  MIN_LOAN            DECIMAL(12,0),
  MIN_AGE             DECIMAL(3,0),        -- eligibility only: age never enters the score
  CHANGED_BY          VARCHAR(60),
  CHANGED_AT          TIMESTAMP,
  CHANGE_NOTE         VARCHAR(400));
INSERT INTO LOS_POLICY.POLICY VALUES
  (1, 'LIVE',  45, 3, 580, 560, 15.00, 9.25, 1000000, 4000000, 50000, 21, 'Credit Risk Committee', TIMESTAMP '2026-07-01 09:00:00', 'Personal loan policy FY27 Q2'),
  (2, 'DRAFT', 45, 3, 580, 560, 15.00, 9.25, 1000000, 4000000, 50000, 21, 'Credit Risk Committee', TIMESTAMP '2026-07-01 09:00:00', 'Draft: copy of version 1');

-- Risk-based pricing: the band's premium over the base rate.
CREATE OR REPLACE TABLE LOS_POLICY.RATE_BANDS (BAND VARCHAR(2), SCORE_FROM DECIMAL(5,0), SCORE_TO DECIMAL(5,0), RISK_PREMIUM DECIMAL(5,2));
INSERT INTO LOS_POLICY.RATE_BANDS VALUES
  ('A', 670, 999, 1.50), ('B', 640, 670, 3.25), ('C', 615, 640, 5.25), ('D', 590, 615, 7.50), ('E', 0, 590, 10.25);

-- When a case goes to a person. Thresholds are data; each rule names the metric it reads (LOS_CORE.RULE_METRICS).
CREATE OR REPLACE TABLE LOS_POLICY.REFERRAL_RULES (
  RULE_ID VARCHAR(4), TITLE VARCHAR(60), METRIC VARCHAR(30), OPERATOR VARCHAR(2), THRESHOLD DOUBLE,
  OUTCOME VARCHAR(8),                     -- REFER | DECLINE
  REVIEW_LEVEL VARCHAR(6),                -- UW1 underwriter | UW2 senior underwriter | FRAUD fraud desk
  WHY_A_PERSON VARCHAR(200), ENABLED BOOLEAN);
INSERT INTO LOS_POLICY.REFERRAL_RULES VALUES
  ('R01', 'Grey-zone score',              'POINTS_BELOW_APPROVE', '>',  0,    'REFER',   'UW1',   'The model is unsure: the score sits between the decline and approve cutoffs', TRUE),
  ('R02', 'Payslip does not match bank',  'INCOME_GAP_PCT',       '>',  15,   'REFER',   'UW1',   'Payslip net pay differs from the salary actually credited over six months', TRUE),
  ('R03', 'Unreadable document',          'MIN_KEY_CONFIDENCE',   '<',  0.85, 'REFER',   'UW1',   'A key field was read with low confidence: the extracted value may be wrong', TRUE),
  ('R04', 'Close to the FOIR cap',        'FOIR_NEAR_CAP',        '=',  1,    'REFER',   'UW1',   'Repayments would sit within the near-cap band: a small error flips the decision', TRUE),
  ('R05', 'No bureau record',             'BUREAU_MISSING',       '=',  1,    'REFER',   'UW1',   'Thin file: too little history for the model', TRUE),
  ('R06', 'New in the job',               'EMP_YEARS',            '<',  1,    'REFER',   'UW1',   'Less than a year with the current employer', TRUE),
  ('R07', 'Returned debits',              'RETURNED_DEBITS_6M',   '>=', 2,    'REFER',   'UW2',   'Two or more EMIs or mandates bounced in six months', TRUE),
  ('R08', 'Gaming spend',                 'GAMING_PCT',           '>',  5,    'REFER',   'UW2',   'Online gaming takes more than 5% of what comes into the account', TRUE),
  ('R09', 'Missing salary months',        'SALARY_GAPS_6M',       '>',  0,    'REFER',   'UW1',   'Salary did not arrive in every one of the last six months', TRUE),
  ('R10', 'Irregular salary',             'SALARY_CV_PCT',        '>',  25,   'REFER',   'UW1',   'Salary amounts swing by more than 25% month to month', TRUE),
  ('R11', 'Above auto-approval limit',    'AMOUNT_OVER_LIMIT',    '>',  0,    'REFER',   'UW2',   'Amount above what the system may approve on its own', TRUE),
  ('R12', 'ID does not match',            'ID_NAME_MISMATCH',     '=',  1,    'REFER',   'FRAUD', 'The name on the ID differs from the application', TRUE),
  ('D01', 'Score below decline cutoff',   'POINTS_BELOW_DECLINE', '>',  0,    'DECLINE', NULL,    'Predicted default risk is above appetite', TRUE),
  ('D02', 'Cannot afford the minimum',    'MAX_AMOUNT_SHORTFALL', '>',  0,    'DECLINE', NULL,    'Even the minimum loan would break the FOIR cap', TRUE),
  ('D03', 'Under minimum age',            'UNDER_MIN_AGE',        '=',  1,    'DECLINE', NULL,    'Eligibility: below the legal minimum age for this product', TRUE);

-- Who may sign what. Above their limit, or overriding the model, a second person must approve (four eyes).
CREATE OR REPLACE TABLE LOS_POLICY.REVIEWER_AUTHORITY (
  REVIEWER VARCHAR(40), ROLE_NAME VARCHAR(40), REVIEW_LEVEL VARCHAR(6), MAX_AMOUNT DECIMAL(12,0), MAY_OVERRIDE_DECLINE BOOLEAN);
INSERT INTO LOS_POLICY.REVIEWER_AUTHORITY VALUES
  ('Priya Natarajan',   'Underwriter',          'UW1',   1000000, FALSE),
  ('Arun Menon',        'Senior underwriter',   'UW2',   2500000, TRUE),
  ('Lakshmi Iyer',      'Head of credit',       'UW2',   4000000, TRUE),
  ('Farhan Sheikh',     'Fraud analyst',        'FRAUD', 0,       FALSE);

-- Every policy change, kept.
CREATE TABLE IF NOT EXISTS LOS_POLICY.POLICY_HISTORY (
  POLICY_VERSION DECIMAL(5,0), PUBLISHED_AT TIMESTAMP, PUBLISHED_BY VARCHAR(60), FOIR_CAP DECIMAL(5,2),
  APPROVE_FROM DECIMAL(5,0), DECLINE_BELOW DECIMAL(5,0), CHANGE_NOTE VARCHAR(400), BACKTEST_SUMMARY VARCHAR(2000));
DELETE FROM LOS_POLICY.POLICY_HISTORY;
INSERT INTO LOS_POLICY.POLICY_HISTORY VALUES (1, TIMESTAMP '2026-07-01 09:00:00', 'Credit Risk Committee', 45, 580, 560, 'Personal loan policy FY27 Q2', NULL);

-- ---------------------------------------------------------------- the decision log: append-only, enforced by privileges
CREATE SCHEMA IF NOT EXISTS LOS_OPS;
CREATE TABLE IF NOT EXISTS LOS_OPS.DECISION_LOG (
  LOG_ID            DECIMAL(18,0) IDENTITY,
  APP_ID            VARCHAR(20),
  DECIDED_AT        TIMESTAMP,
  DECIDED_BY        VARCHAR(40),
  ROLE_NAME         VARCHAR(40),
  STEP              VARCHAR(12),         -- DECISION | SECOND_SIGN | SYSTEM
  SYSTEM_DECISION   VARCHAR(16),         -- what the rules and the model said
  FINAL_DECISION    VARCHAR(24),         -- APPROVE | APPROVE_REDUCED | APPROVE_CONDITIONS | PENDING_INFO | DECLINE | REFER_FRAUD
  AMOUNT            DECIMAL(12,0),
  RATE              DECIMAL(5,2),
  TERM_MONTHS       DECIMAL(3,0),
  INCOME_BASIS      DECIMAL(12,0),       -- the monthly gross income the person decided on
  OVERRIDE_FLAG     BOOLEAN,             -- the person went against the system
  REASON_CODE       VARCHAR(40),
  CONDITIONS        VARCHAR(400),
  NOTES             VARCHAR(2000),
  RULES_FIRED       VARCHAR(400),
  SCORE             DECIMAL(5,0),
  POLICY_VERSION    DECIMAL(5,0),
  MODEL_VERSION     VARCHAR(40),
  NEEDS_SECOND_SIGN BOOLEAN,
  FEATURE_SNAPSHOT  VARCHAR(4000));
