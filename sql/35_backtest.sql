-- The back-test: score every historical loan with the SAME scorecard table, decide it under the LIVE and the DRAFT
-- policy, and add up what actually happened (defaults, and every rupee/dollar paid back). Nothing is precomputed:
-- each query scores all 1.34M loans again, so a policy edit is reflected the moment it is saved.
-- Limit (said on screen): only loans that WERE funded have outcomes, so the back-test can show which past loans a
-- policy would have turned away, not how the applicants who were rejected at the time would have behaved.
CREATE OR REPLACE VIEW LOS_BOOK.SCORED AS
SELECT l.LOAN_ID, YEAR(l.ISSUE_DATE) AS ISSUE_YEAR, l.FUNDED_AMOUNT, l.DEFAULTED, l.NET_CASH, l.FOIR_AFTER, l.BUREAU_SCORE,
       l.LOAN_TO_INCOME, l.TERM_MONTHS, l.EMP_YEARS, l.INQ_6M, l.PUB_REC, l.PURPOSE,
       ROUND(w.BASE_SCORE - w.FACTOR * (w.B0 + w.W_BUREAU * LEAST(GREATEST(l.BUREAU_SCORE, 300), 850)
             + w.W_FOIR * LEAST(GREATEST(l.FOIR_AFTER, 0), 60) + w.W_LTI * LEAST(GREATEST(l.LOAN_TO_INCOME, 0), 1)
             + w.W_INQ * LEAST(l.INQ_6M, 6) + w.W_EMP * LEAST(l.EMP_YEARS, 10)
             + w.W_TERM * CASE WHEN l.TERM_MONTHS = 60 THEN 1 ELSE 0 END + w.W_PUB * LEAST(l.PUB_REC, 3) + w.LN_ODDS), 0) AS SCORE
FROM LOS_BOOK.LOANS l CROSS JOIN LOS_POLICY.WEIGHTS w;

-- every loan decided twice, once per policy; grouped by the pair, so "what changes" is one GROUP BY
CREATE OR REPLACE VIEW LOS_BOOK.BACKTEST AS
WITH lp AS (SELECT * FROM LOS_POLICY.POLICY WHERE STATUS = 'LIVE'),
     dp AS (SELECT * FROM LOS_POLICY.POLICY WHERE STATUS = 'DRAFT'),
d AS (
  SELECT s.*,
         CASE WHEN s.SCORE < lp.DECLINE_BELOW OR s.FOIR_AFTER > lp.FOIR_CAP THEN 'DECLINE'
              WHEN s.SCORE < lp.APPROVE_FROM OR s.FOIR_AFTER > lp.FOIR_CAP - lp.FOIR_NEAR_BAND THEN 'REFER' ELSE 'APPROVE' END AS LIVE_DECISION,
         CASE WHEN s.SCORE < dp.DECLINE_BELOW OR s.FOIR_AFTER > dp.FOIR_CAP THEN 'DECLINE'
              WHEN s.SCORE < dp.APPROVE_FROM OR s.FOIR_AFTER > dp.FOIR_CAP - dp.FOIR_NEAR_BAND THEN 'REFER' ELSE 'APPROVE' END AS DRAFT_DECISION
  FROM LOS_BOOK.SCORED s CROSS JOIN lp CROSS JOIN dp)
SELECT LIVE_DECISION, DRAFT_DECISION, COUNT(*) AS LOANS, SUM(DEFAULTED) AS DEFAULTS, SUM(FUNDED_AMOUNT) AS LENT,
       SUM(NET_CASH) AS NET_CASH,
       SUM(CASE WHEN DEFAULTED = 1 THEN NET_CASH ELSE 0 END) AS CASH_FROM_DEFAULTS,      -- negative: money lost
       SUM(CASE WHEN DEFAULTED = 0 THEN NET_CASH ELSE 0 END) AS CASH_FROM_REPAID         -- positive: interest earned
FROM d GROUP BY LIVE_DECISION, DRAFT_DECISION;

-- the trade-off curve: outcomes by score band and FOIR band, for the chart (the console adds them up per cutoff)
CREATE OR REPLACE VIEW LOS_BOOK.FRONTIER AS
SELECT FLOOR(SCORE / 5) * 5 AS SCORE_BAND, LEAST(CEIL(FOIR_AFTER), 61) AS FOIR_BAND, COUNT(*) AS LOANS, SUM(DEFAULTED) AS DEFAULTS,
       SUM(NET_CASH) AS NET_CASH, SUM(FUNDED_AMOUNT) AS LENT
FROM LOS_BOOK.SCORED GROUP BY FLOOR(SCORE / 5) * 5, LEAST(CEIL(FOIR_AFTER), 61);
