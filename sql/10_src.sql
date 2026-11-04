-- LOS_SRC: every source read LIVE, translated into one vocabulary. Views only: nothing is stored.
-- LIKE, not REGEXP_LIKE, over LOS_CBS: the Postgres dialect pushes expressions down.
CREATE SCHEMA IF NOT EXISTS LOS_SRC;

-- ---------------------------------------------------------------- loan applications (MongoDB): what the applicant typed
CREATE OR REPLACE VIEW LOS_SRC.APPLICATIONS AS
SELECT a."mongo_id" AS APP_ID, a."custId" AS CUST_ID,
       TO_TIMESTAMP(REPLACE(a."submittedAt", 'T', ' '), 'YYYY-MM-DD HH24:MI') AS SUBMITTED_AT,
       a."channel" AS CHANNEL, a."product" AS PRODUCT, a."amountRequested" AS AMOUNT_REQUESTED,
       a."termMonths" AS TERM_MONTHS, a."purpose" AS PURPOSE, a."salaryAccount" AS SALARY_ACCOUNT, a."deviceId" AS DEVICE_ID,
       p."name" AS APPLICANT_NAME, TO_DATE(p."dob", 'YYYY-MM-DD') AS BIRTH_DATE, p."city" AS CITY, p."mobile" AS MOBILE
FROM LOS_APPS.APPLICATIONS a
JOIN LOS_APPS."APPLICATIONS_applicant" p ON p."_id" = a."applicant|object";

-- ---------------------------------------------------------------- extracted documents (MongoDB): one shape per document type
CREATE OR REPLACE VIEW LOS_SRC.PAYSLIPS AS
SELECT d."applicationId" AS APP_ID, d."mongo_id" AS DOC_ID, d."fileName" AS FILE_NAME,
       f."employeeName" AS EMPLOYEE_NAME, f."employer" AS EMPLOYER, f."employerAddress" AS EMPLOYER_ADDRESS,
       f."payMonth" AS PAY_MONTH, TO_DATE(f."dateOfJoining", 'YYYY-MM-DD') AS DATE_OF_JOINING,
       f."gross" AS GROSS, f."bonus" AS BONUS, f."deductions" AS DEDUCTIONS, f."net" AS NET,
       c."net" AS CONF_NET, c."gross" AS CONF_GROSS, c."employer" AS CONF_EMPLOYER, c."employeeName" AS CONF_NAME,
       x."minConfidence" AS MIN_CONFIDENCE, x."engine" AS EXTRACT_ENGINE, x."ms" AS EXTRACT_MS,
       g."producer" AS PDF_PRODUCER, g."templateHash" AS TEMPLATE_HASH
FROM LOS_DOCS.DOCUMENTS d
JOIN LOS_DOCS."DOCUMENTS_fields" f ON f."_id" = d."fields|object"
LEFT JOIN LOS_DOCS."DOCUMENTS_confidence" c ON c."_id" = d."confidence|object"
LEFT JOIN LOS_DOCS."DOCUMENTS_extraction" x ON x."_id" = d."extraction|object"
LEFT JOIN LOS_DOCS."DOCUMENTS_fingerprint" g ON g."_id" = d."fingerprint|object"
WHERE d."docType" = 'PAYSLIP';

CREATE OR REPLACE VIEW LOS_SRC.ID_PROOFS AS
SELECT d."applicationId" AS APP_ID, d."mongo_id" AS DOC_ID, f."idType" AS ID_TYPE, f."name" AS NAME_ON_ID,
       TO_DATE(f."dob", 'YYYY-MM-DD') AS DOB_ON_ID, f."idNumber" AS ID_NUMBER,
       c."idNumber" AS CONF_ID_NUMBER, c."name" AS CONF_NAME, x."minConfidence" AS MIN_CONFIDENCE
FROM LOS_DOCS.DOCUMENTS d
JOIN LOS_DOCS."DOCUMENTS_fields" f ON f."_id" = d."fields|object"
LEFT JOIN LOS_DOCS."DOCUMENTS_confidence" c ON c."_id" = d."confidence|object"
LEFT JOIN LOS_DOCS."DOCUMENTS_extraction" x ON x."_id" = d."extraction|object"
WHERE d."docType" = 'ID_PROOF';

CREATE OR REPLACE VIEW LOS_SRC.EMPLOYMENT_LETTERS AS
SELECT d."applicationId" AS APP_ID, f."employer" AS EMPLOYER, f."designation" AS DESIGNATION,
       TO_DATE(f."joiningDate", 'YYYY-MM-DD') AS JOINING_DATE, f."employmentType" AS EMPLOYMENT_TYPE
FROM LOS_DOCS.DOCUMENTS d
JOIN LOS_DOCS."DOCUMENTS_fields" f ON f."_id" = d."fields|object"
WHERE d."docType" = 'EMPLOYMENT_LETTER';

-- ---------------------------------------------------------------- core banking (Postgres): legacy column names, read live
CREATE OR REPLACE VIEW LOS_SRC.TRANSACTIONS AS
SELECT t.TXN_ID, t.ACCT_NO, t.TXN_DT AS TXN_DATE, t.TXN_AMT AS AMOUNT, t.DR_CR, t.NARR AS NARRATION, t.CHNL AS CHANNEL,
       t.CP_ACCT AS COUNTERPARTY_ACCT, t.CP_IFSC AS COUNTERPARTY_IFSC, t.BAL_AMT AS BALANCE_AFTER,
       CASE WHEN t.DR_CR = 'C' AND t.NARR LIKE '%-SALARY %' THEN 'SALARY'
            WHEN t.DR_CR = 'D' AND t.NARR LIKE 'NACH DR/%LOAN EMI' THEN 'LOAN_EMI'
            WHEN t.NARR LIKE 'NACH RTN%' THEN 'RETURNED_DEBIT'
            WHEN t.NARR LIKE '%ONLINE GAMING%' THEN 'GAMING'
            WHEN t.NARR LIKE '%RENT%' THEN 'RENT'
            WHEN t.CHNL IN ('ATM', 'CASH') THEN 'CASH'
            WHEN t.DR_CR = 'C' THEN 'OTHER_CREDIT' ELSE 'SPEND' END AS CATEGORY
FROM LOS_CBS.TXN_HIST t;

-- salary credits per account and month: the aggregate runs IN Postgres (pushed down by the virtual schema)
CREATE OR REPLACE VIEW LOS_SRC.SALARY_MONTHLY AS
SELECT ACCT_NO, TO_DATE(TO_CHAR(TXN_DT, 'YYYY-MM') || '-01', 'YYYY-MM-DD') AS MON, SUM(TXN_AMT) AS NET_CREDITED,
       MAX(CP_ACCT) AS PAYER_ACCT, MAX(CP_IFSC) AS PAYER_IFSC, MAX(NARR) AS NARRATION
FROM LOS_CBS.TXN_HIST
WHERE DR_CR = 'C' AND NARR LIKE '%-SALARY %'
GROUP BY ACCT_NO, TO_CHAR(TXN_DT, 'YYYY-MM');

-- behaviour signals per account over the six months before the application (window applied in LOS_CORE)
CREATE OR REPLACE VIEW LOS_SRC.TXN_MONTHLY AS
SELECT ACCT_NO, TO_DATE(TO_CHAR(TXN_DT, 'YYYY-MM') || '-01', 'YYYY-MM-DD') AS MON,
       SUM(CASE WHEN DR_CR = 'C' THEN TXN_AMT ELSE 0 END) AS CREDITS,
       SUM(CASE WHEN DR_CR = 'D' THEN TXN_AMT ELSE 0 END) AS DEBITS,
       SUM(CASE WHEN NARR LIKE 'NACH RTN%' THEN 1 ELSE 0 END) AS RETURNED_DEBITS,
       SUM(CASE WHEN NARR LIKE '%ONLINE GAMING%' THEN TXN_AMT ELSE 0 END) AS GAMING_SPEND,
       SUM(CASE WHEN DR_CR = 'D' AND NARR LIKE 'NACH DR/%LOAN EMI' THEN TXN_AMT ELSE 0 END) AS EMI_DEBITS,
       MIN(BAL_AMT) AS MIN_BALANCE
FROM LOS_CBS.TXN_HIST
GROUP BY ACCT_NO, TO_CHAR(TXN_DT, 'YYYY-MM');

-- line items the extractor read off the payslip (only documents that carry them), and an index of every upload
CREATE OR REPLACE VIEW LOS_SRC.PAYSLIP_LINES AS
SELECT d."applicationId" AS APP_ID, li."_pos" AS POS, li."label" AS LINE_ITEM, li."amount" AS AMOUNT, li."kind" AS KIND,
       li."recurring" AS RECURRING
FROM LOS_DOCS."DOCUMENTS_lineItems_arr" li JOIN LOS_DOCS.DOCUMENTS d ON d."_id" = li."_parent";

CREATE OR REPLACE VIEW LOS_SRC.DOCUMENT_INDEX AS
SELECT d."applicationId" AS APP_ID, d."mongo_id" AS DOC_ID, d."docType" AS DOC_TYPE, d."fileName" AS FILE_NAME,
       x."engine" AS ENGINE, x."ms" AS MS, x."minConfidence" AS MIN_CONF
FROM LOS_DOCS.DOCUMENTS d LEFT JOIN LOS_DOCS."DOCUMENTS_extraction" x ON x."_id" = d."extraction|object";

-- ---------------------------------------------------------------- customers (Postgres): who owns an account (used to match a live upload)
CREATE OR REPLACE VIEW LOS_SRC.CUSTOMERS AS
SELECT a.ACCT_NO, a.CUST_ID, c.CUST_NM AS NAME_ON_RECORD, c.PAN_NO AS PAN_ON_RECORD, c.DOB_TXT AS DOB_ON_RECORD, c.MOB_NO AS MOBILE_ON_RECORD,
       c.KYC_FLG AS KYC_DONE, c.CUST_SINCE, a.OPEN_DT AS ACCOUNT_OPENED, a.ACCT_STAT AS ACCOUNT_STATUS
FROM LOS_CBS.ACCT_MST a JOIN LOS_CBS.CUST_MST c ON c.CUST_ID = a.CUST_ID;
