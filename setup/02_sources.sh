#!/usr/bin/env bash
# Attach the lender's systems to Exasol as virtual schemas (nothing copied), and load what lives IN Exasol.
#   LOS_CBS    core banking on Postgres          official PostgreSQL virtual schema (JDBC), read-only login
#   LOS_APPS   loan applications on MongoDB      MongoDB virtual schema (exasol-labs), read-only login
#   LOS_DOCS   extracted documents on MongoDB    MongoDB virtual schema
#   LOS_BOOK.LOANS        1.34M historical loans with outcomes (Lending Club), the risk team's store
#   LOS_SRC.BUREAU_PULLS  the bureau response per application (mocked), stored as received
# Needs setup/01_connectors.sh (adapters, drivers) and setup/00_sources_vm.sh (the containers). Idempotent.
source "$(dirname "$0")/common.sh"

# holds the read-only logins' passwords: written mode 600 and removed once run
(umask 077; cat > "$WORK/02_sources.sql") <<SQL
CREATE SCHEMA IF NOT EXISTS LOS_ADAPTERS;
CREATE OR REPLACE JAVA ADAPTER SCRIPT LOS_ADAPTERS.POSTGRES_ADAPTER AS
  %scriptclass com.exasol.adapter.RequestDispatcher;
  %jvmoption -Duser.timezone=UTC;
  %jar /buckets/bfsdefault/default/los/jars/virtual-schema-dist-14.0.4-postgresql-4.0.1.jar;
  %jar /buckets/bfsdefault/default/los/jars/postgresql-42.7.4.jar;
/
CREATE OR REPLACE CONNECTION LOS_CBS_PG TO 'jdbc:postgresql://$SRC_HOST:$PG_PORT/core_banking'
  USER 'cbs_reader' IDENTIFIED BY '$PG_READER_PASSWORD';
CREATE OR REPLACE CONNECTION LOS_DOCS_MONGO TO 'mongodb://$SRC_HOST:$MONGO_PORT/?authSource=admin&directConnection=true'
  USER 'docs_reader' IDENTIFIED BY '$MONGO_READER_PASSWORD';
DROP VIRTUAL SCHEMA IF EXISTS LOS_CBS CASCADE;
CREATE VIRTUAL SCHEMA LOS_CBS USING LOS_ADAPTERS.POSTGRES_ADAPTER WITH
  CONNECTION_NAME = 'LOS_CBS_PG' CATALOG_NAME = 'core_banking' SCHEMA_NAME = 'cbs'
  POSTGRESQL_IDENTIFIER_MAPPING = 'CONVERT_TO_UPPER';
DROP VIRTUAL SCHEMA IF EXISTS LOS_APPS CASCADE;
CREATE VIRTUAL SCHEMA LOS_APPS USING LOS_MONGODB_VS.MONGODB_ADAPTER WITH
  MONGODB_CONNECTION = 'LOS_DOCS_MONGO' DATABASE = 'lending' COLLECTION = 'applications' INFERENCE_SAMPLE_SIZE = '3000';
DROP VIRTUAL SCHEMA IF EXISTS LOS_DOCS CASCADE;
CREATE VIRTUAL SCHEMA LOS_DOCS USING LOS_MONGODB_VS.MONGODB_ADAPTER WITH
  MONGODB_CONNECTION = 'LOS_DOCS_MONGO' DATABASE = 'lending' COLLECTION = 'documents' INFERENCE_SAMPLE_SIZE = '7000';
SQL

say "1. Connections + virtual schemas"
xfile "$WORK/02_sources.sql" || { rm -f "$WORK/02_sources.sql"; die "sql for the connections and virtual schemas failed"; }
rm -f "$WORK/02_sources.sql"
xsql "SELECT COLUMN_SCHEMA, COLUMN_TABLE, COUNT(*) AS COLS FROM EXA_ALL_COLUMNS
      WHERE COLUMN_SCHEMA IN ('LOS_CBS','LOS_APPS','LOS_DOCS') GROUP BY 1,2 ORDER BY 1,2;"
xsql "SELECT COUNT(*) AS CBS_TXNS FROM LOS_CBS.TXN_HIST;"

say "2. The historical book, the bureau responses and the scorecard (stored in Exasol)"
xfile "$ROOT/sql/05_tables.sql"
xload "$WORK/book.csv" LOS_BOOK.LOANS
xload "$WORK/bureau.csv" LOS_SRC.BUREAU_PULLS
xload "$WORK/scorecard.csv" LOS_POLICY.SCORECARD
xsql "SELECT (SELECT COUNT(*) FROM LOS_BOOK.LOANS) AS BOOK, (SELECT COUNT(*) FROM LOS_SRC.BUREAU_PULLS) AS BUREAU,
             (SELECT COUNT(*) FROM LOS_POLICY.SCORECARD) AS SCORECARD;"
