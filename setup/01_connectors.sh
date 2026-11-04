#!/usr/bin/env bash
# Everything Exasol needs to read the two source databases in place, installed under this project's own names so it
# never disturbs other projects on the same database. Downloads once into .work/dl. Idempotent.
#   Postgres  official PostgreSQL virtual schema (Java adapter) + JDBC driver        -> BucketFS default/los/jars
#   MongoDB   exasol-labs MongoDB virtual schema (Rust adapter) + Rust language container
#             -> BucketFS default/los/libmongodb_vs.so, default/slc/los-rustslc, language alias LOSRUST,
#                scripts LOS_MONGODB_VS.MONGODB_ADAPTER and MONGODB_SCAN
# Also makes sure the JAVA and PYTHON3 script languages exist (installing one restarts the database).
source "$(dirname "$0")/common.sh"
DL="$WORK/dl"; mkdir -p "$DL"
PGVS_VER=4.0.1; PGVS_JAR=virtual-schema-dist-14.0.4-postgresql-$PGVS_VER.jar; JDBC_JAR=postgresql-42.7.4.jar
MVS_VER=0.1.3; RSLC_VER=0.33.0          # the MongoDB adapter release is built for exactly this Rust SLC (see its README)

# Every file that ends up running inside the database is checked against its SHA-256, taken from the publisher's
# release page (GitHub release digests; Maven's checksum for the JDBC driver), not from the same download.
fetch() {  # url file sha256
  if [[ ! -s "$DL/$2" ]]; then
    curl -fsSL --retry 3 -o "$DL/$2.part" "$1" || die "download failed: $1"
    mv -f "$DL/$2.part" "$DL/$2"
  fi
  echo "$3  $DL/$2" | shasum -a 256 -c --status || { rm -f "$DL/$2"; die "checksum mismatch for $2 (deleted it; run again to re-download)"; }
}

say "1. Script languages JAVA and PYTHON3"
LANGS=$(xsql "SELECT SYSTEM_VALUE FROM EXA_PARAMETERS WHERE PARAMETER_NAME='SCRIPT_LANGUAGES';" | tail -1)
for L in JAVA PYTHON3; do
  if [[ " $LANGS " == *" $L="* ]]; then ok "$L present"; else
    say "   installing $L (the database restarts)"; exasol slc install "$L" -d "$EXASOL_DEPLOYMENT" --auto-approve
  fi
done

say "2. Postgres: virtual schema adapter + JDBC driver"
fetch "https://github.com/exasol/postgresql-virtual-schema/releases/download/$PGVS_VER/$PGVS_JAR" "$PGVS_JAR" \
  aeb82011f71bdd4b79567dd648193f88fe664a167fad2ed5c3ac22606f229461
fetch "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/$JDBC_JAR" "$JDBC_JAR" \
  188976721ead8e8627eb6d8389d500dccc0c9bebd885268a3047180274a6031e
mkdir -p "$BFS/default/los/jars"
cp "$DL/$PGVS_JAR" "$DL/$JDBC_JAR" "$BFS/default/los/jars/"
# The pushed-down fetch runs as IMPORT FROM JDBC in Exasol's own loader, which on Exasol Personal reads drivers from
# vm-shared/exa/jdbc (not BucketFS drivers/jdbc). Shared by every project: added only when missing.
JDBC_DIR="$RUNTIME/vm-shared/exa/jdbc/postgresql"
if [[ -f "$JDBC_DIR/settings.cfg" ]]; then ok "Postgres driver already registered for the loader ($(grep '^JAR=' "$JDBC_DIR/settings.cfg"))"; else
  mkdir -p "$JDBC_DIR"; cp "$DL/$JDBC_JAR" "$JDBC_DIR/"
  # NOSECURITY=YES lets the loader's Java sandbox run this driver, which the PostgreSQL JDBC driver needs on Exasol.
  printf 'DRIVERNAME=POSTGRESQL\nJAR=%s\nDRIVERMAIN=org.postgresql.Driver\nPREFIX=jdbc:postgresql:\nFETCHSIZE=100000\nINSERTSIZE=-1\nNOSECURITY=YES\n\n' "$JDBC_JAR" > "$JDBC_DIR/settings.cfg"
  ok "Postgres driver registered for the loader"
fi
ok "BucketFS default/los/jars: $PGVS_JAR, $JDBC_JAR"

say "3. MongoDB: Rust language container $RSLC_VER + adapter $MVS_VER"
ARCH=$("$ROOT/setup/vm.sh" 'uname -m')
case "$ARCH" in aarch64|arm64) SLC_TGZ=lc-rust-$RSLC_VER-aarch64.tar.gz; SO=exasol-mongodb-vs-$MVS_VER-linux-aarch64.so
                               SLC_SHA=de311ae8acadd30579373820d00b92364866880c15bf2edf8284567a8aaa5f8e
                               SO_SHA=fc42e8f6ea490429409b09d8b203db9a7446b0c7a69b03c03c85ef30dcc1da37 ;;
                x86_64)        SLC_TGZ=lc-rust-$RSLC_VER.tar.gz;         SO=exasol-mongodb-vs-$MVS_VER-linux-x86_64.so
                               SLC_SHA=eeedf5f2f8f7a4ad3a329065e516f93106412f270280bf47dede8e5023985245
                               SO_SHA=d619dcc5b4b35fc1520af8922eea07ba2ec504c70d5c4ee7142ce22289420827 ;;
                *) die "unsupported VM architecture: $ARCH" ;; esac
fetch "https://github.com/exasol-labs/language-container-rs/releases/download/v$RSLC_VER/$SLC_TGZ" "$SLC_TGZ" "$SLC_SHA"
fetch "https://github.com/exasol-labs/exasol-mongodb-vs/releases/download/v$MVS_VER/$SO" "$SO" "$SO_SHA"
fetch "https://raw.githubusercontent.com/exasol-labs/exasol-mongodb-vs/v$MVS_VER/sql/install.sql" "mongodb-vs-$MVS_VER-install.sql" \
  ca8e43850689ec870d6d37d6f8be633253ef509768b87e4965f097e489e1049c
ok "$SLC_TGZ, $SO, install.sql: checksums verified"
SLC="$BFS/default/slc/los-rustslc"
if [[ ! -x "$SLC/exaudf/exaudfclient" || "$(cat "$SLC/.los-version" 2>/dev/null)" != "$RSLC_VER" ]]; then
  rm -rf "$SLC"; mkdir -p "$SLC"; tar xzf "$DL/$SLC_TGZ" -C "$SLC"; echo "$RSLC_VER" > "$SLC/.los-version"
fi
cp "$DL/$SO" "$BFS/default/los/libmongodb_vs.so"
sleep 3
ok "BucketFS default/slc/los-rustslc, default/los/libmongodb_vs.so"

say "4. Language alias LOSRUST (other aliases are kept exactly as they are)"
DEF="LOSRUST=localzmq+protobuf:///bfsdefault/default/slc/los-rustslc?lang=rust#buckets/bfsdefault/default/slc/los-rustslc/exaudf/exaudfclient"
CUR=$(xsql "SELECT SYSTEM_VALUE FROM EXA_PARAMETERS WHERE PARAMETER_NAME='SCRIPT_LANGUAGES';" | tail -1)
if [[ " $CUR " == *" $DEF "* ]]; then ok "already registered"; else
  NEW=$(printf '%s\n' $CUR | grep -v '^LOSRUST=' | tr '\n' ' '; echo "$DEF")
  echo "$CUR" > "$WORK/script_languages.before"
  xsql "ALTER SYSTEM SET SCRIPT_LANGUAGES = '$NEW';" >/dev/null
  ok "$(xsql "SELECT SYSTEM_VALUE FROM EXA_PARAMETERS WHERE PARAMETER_NAME='SCRIPT_LANGUAGES';" | tail -1 | tr ' ' '\n' | cut -d= -f1 | tr '\n' ' ')"
fi

say "5. Adapter scripts (the release's sql/install.sql, under this project's schema and alias)"
sed -e 's/MONGODB_VS\./LOS_MONGODB_VS./g' -e 's/SCHEMA IF NOT EXISTS MONGODB_VS/SCHEMA IF NOT EXISTS LOS_MONGODB_VS/' \
    -e 's/CREATE OR REPLACE RUST /CREATE OR REPLACE LOSRUST /' \
    -e 's#/buckets/bfsdefault/rust/libmongodb_vs.so#/buckets/bfsdefault/default/los/libmongodb_vs.so#' \
    "$DL/mongodb-vs-$MVS_VER-install.sql" > "$WORK/mongodb_vs_install.sql"
xfile "$WORK/mongodb_vs_install.sql"
ok "$(xsql "SELECT GROUP_CONCAT(SCRIPT_NAME || ' (' || SCRIPT_LANGUAGE || ')') FROM EXA_ALL_SCRIPTS WHERE SCRIPT_SCHEMA = 'LOS_MONGODB_VS';" | tail -1)"
