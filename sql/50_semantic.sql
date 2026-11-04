-- The semantic layer made explicit, and the data contracts every source must keep.
--   TERMS      the business vocabulary: each term, what it means, the semantic-view column that carries it, and the
--              field each system stores it in (the LOS_SRC views ARE the mapping; this table documents it)
--   CONTRACTS  what each source promises to deliver, owned by a named team, CRITICAL or WARNING
--   CONTRACT_RESULTS  the checks, per application, written by the LOS service (one upload, or the whole portfolio)
-- The checks themselves are one SQL statement (service/sqlq.py q_contract_checks), installed as the view
-- LOS_SEM.CONTRACT_CHECKS_LIVE by setup/07_semantic.sh. A CRITICAL breach refers the case (rule R13).
CREATE SCHEMA IF NOT EXISTS LOS_SEM;

CREATE OR REPLACE TABLE LOS_SEM.TERMS (
  ORDINAL DECIMAL(3,0), TERM VARCHAR(40), DEFINITION VARCHAR(300), SEMANTIC_VIEW VARCHAR(80),
  MONGODB_FIELD VARCHAR(120), POSTGRES_FIELD VARCHAR(160), BUREAU_FIELD VARCHAR(60), USED_BY VARCHAR(120));
INSERT INTO LOS_SEM.TERMS VALUES
 (1,  'Application ID', 'One loan application, from upload to decision', 'SRC.APPLICATIONS.APP_ID',
      'applications._id, documents.applicationId', NULL, 'BUREAU_PULLS.APP_ID', 'every join'),
 (2,  'Customer ID (CIF)', 'The bank''s own identifier for the applicant: the unique ID the records fuse on', 'SRC.CUSTOMERS.CUST_ID',
      'applications.custId', 'acct_mst.cust_id = cust_mst.cust_id', 'BUREAU_PULLS.CUST_ID', 'identity, fraud links'),
 (3,  'Applicant name', 'The person applying, as written on the form', 'SRC.APPLICATIONS.APPLICANT_NAME',
      'applications.applicant.name; documents.fields.name (PAN card)', 'cust_mst.cust_nm (upper case)', NULL, 'R12 identity'),
 (4,  'PAN', 'Permanent Account Number: the tax ID and the bureau''s key', 'SRC.ID_PROOFS.ID_NUMBER',
      'documents.fields.idNumber (PAN card); documents.fields.pan (form)', 'cust_mst.pan_no', 'the pull key', 'bureau pull, XS01'),
 (5,  'Date of birth', 'A DATE, whatever each system stores', 'SRC.APPLICATIONS.BIRTH_DATE',
      'applications.applicant.dob (ISO text)', 'cust_mst.dob_txt (DD-MM-YYYY text)', NULL, 'D03 minimum age'),
 (6,  'Salary account', 'The account the salary is paid into, named on the form', 'SRC.APPLICATIONS.SALARY_ACCOUNT',
      'applications.salaryAccount', 'acct_mst.acct_no, txn_hist.acct_no', NULL, 'the match to core banking'),
 (7,  'Payslip net pay', 'Take-home pay as the payslip states it', 'SRC.PAYSLIPS.NET',
      'documents.fields.net (PAYSLIP)', NULL, NULL, 'R02'),
 (8,  'Salary credited', 'Salary that actually arrived: credits whose narration says SALARY, per month', 'SRC.SALARY_MONTHLY.NET_CREDITED',
      NULL, 'txn_hist.txn_amt where dr_cr = ''C'' and narr like ''%-SALARY %''', NULL, 'R02, R09, R10'),
 (9,  'Verified income', 'Payslip gross scaled down to what the bank received, never up', 'CORE.APPLICATION_FACTS.VERIFIED_GROSS',
      'documents.fields.gross', 'salary credited (6-month average)', NULL, 'FOIR, scorecard'),
 (10, 'Existing EMIs', 'Monthly repayments on loans the applicant already has', 'SRC.BUREAU_PULLS.EXISTING_EMI',
      NULL, NULL, 'existing_emi', 'FOIR'),
 (11, 'Bureau score', 'The credit bureau''s score, 300 to 900', 'SRC.BUREAU_PULLS.BUREAU_SCORE',
      NULL, NULL, 'score', 'scorecard, R05'),
 (12, 'Returned debit', 'A payment that bounced for lack of funds', 'SRC.TRANSACTIONS.CATEGORY = ''RETURNED_DEBIT''',
      NULL, 'txn_hist.narr like ''NACH RTN%''', NULL, 'R07'),
 (13, 'Loan purpose', 'What the loan is for, mapped to the categories the ML model learned', 'SRC.APPLICATIONS.PURPOSE',
      'applications.purpose', NULL, NULL, 'ML model (via ML.PURPOSE_MAP)');

-- who made each definition: an AI agent drafted the semantic views from the source schemas; a data steward approved them
ALTER TABLE LOS_SEM.TERMS ADD COLUMN PROPOSED_BY VARCHAR(60);
ALTER TABLE LOS_SEM.TERMS ADD COLUMN APPROVED_BY VARCHAR(60);
ALTER TABLE LOS_SEM.TERMS ADD COLUMN APPROVED_AT TIMESTAMP;
ALTER TABLE LOS_SEM.TERMS ADD COLUMN STATUS VARCHAR(12);
UPDATE LOS_SEM.TERMS SET PROPOSED_BY = 'AI agent (from the source schemas)', APPROVED_BY = 'Data steward',
  APPROVED_AT = TIMESTAMP '2026-10-28 11:30:00', STATUS = 'APPROVED';

CREATE OR REPLACE TABLE LOS_SEM.CONTRACTS (
  ORDINAL DECIMAL(3,0), CONTRACT_ID VARCHAR(4), SOURCE_SYSTEM VARCHAR(30), DATASET VARCHAR(40), EXPECTATION VARCHAR(200),
  SEVERITY VARCHAR(8), OWNER VARCHAR(40));
INSERT INTO LOS_SEM.CONTRACTS VALUES
 (1,  'DS01', 'Document store', 'SRC.DOCUMENT_INDEX', 'The proof of income and identity is present: a payslip and a PAN card', 'CRITICAL', 'Digital onboarding'),
 (7,  'DS07', 'Document store', 'SRC.DOCUMENT_INDEX', 'An employment letter is on file', 'WARNING', 'Digital onboarding'),
 (2,  'DS02', 'Document store', 'SRC.PAYSLIPS', 'A payslip states gross pay, deductions and net pay', 'CRITICAL', 'Digital onboarding'),
 (3,  'DS03', 'Document store', 'SRC.PAYSLIPS', 'A payslip adds up: gross minus deductions equals net, within Rs 1', 'WARNING', 'Digital onboarding'),
 (4,  'DS04', 'Document store', 'SRC.PAYSLIPS', 'The payslip is recent: its month is within two months of the application', 'WARNING', 'Digital onboarding'),
 (5,  'DS05', 'Document store', 'SRC.ID_PROOFS', 'The PAN is well formed: five letters, four digits, one letter', 'CRITICAL', 'Digital onboarding'),
 (6,  'DS06', 'Document store', 'SRC.APPLICATIONS', 'Amount Rs 50,000 to Rs 40 L, term 12 to 60 months, salary account given', 'CRITICAL', 'Digital onboarding'),
 (8,  'CB01', 'Core banking', 'SRC.CUSTOMERS', 'For a bank customer: the salary account exists and belongs to the applicant (not applicable otherwise)', 'CRITICAL', 'Core banking operations'),
 (9,  'CB02', 'Core banking', 'SRC.CUSTOMERS', 'Date of birth is a valid DD-MM-YYYY date', 'WARNING', 'Core banking operations'),
 (10, 'CB03', 'Core banking', 'SRC.TRANSACTIONS', 'Every transaction on the account has a positive amount', 'WARNING', 'Core banking operations'),
 (11, 'CB04', 'Core banking', 'SRC.TRANSACTIONS', 'The account is current: transactions up to the month before the application', 'WARNING', 'Core banking operations'),
 (12, 'BU01', 'Credit bureau', 'SRC.BUREAU_PULLS', 'A returned report has a score of 300 to 900 and is at most 30 days old (no report at all is rule R05)', 'CRITICAL', 'Credit risk'),
 (13, 'XS01', 'Cross-system', 'SRC.ID_PROOFS x SRC.CUSTOMERS', 'For a bank customer: PAN on the card equals PAN in core banking (not applicable otherwise)', 'CRITICAL', 'Data governance');

CREATE TABLE IF NOT EXISTS LOS_SEM.CONTRACT_RESULTS (
  APP_ID VARCHAR(20), CONTRACT_ID VARCHAR(4), PASSED BOOLEAN, EVIDENCE VARCHAR(300), CHECKED_AT TIMESTAMP);
CREATE TABLE IF NOT EXISTS LOS_SEM.CONTRACT_RUNS (
  RUN_AT TIMESTAMP, APPS DECIMAL(9,0), CHECKS DECIMAL(9,0), BREACHES DECIMAL(9,0), SECONDS DOUBLE);

-- a CRITICAL breach means the data cannot be trusted as delivered: a person looks (the decision views pick it up)
DELETE FROM LOS_POLICY.REFERRAL_RULES WHERE RULE_ID = 'R13';
INSERT INTO LOS_POLICY.REFERRAL_RULES VALUES ('R13', 'Data contract breached', 'CRITICAL_CONTRACT_BREACHES', '>', 0, 'REFER', 'UW1',
  'A critical data contract failed: a source did not deliver what it promised', TRUE);
