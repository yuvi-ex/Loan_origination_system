#!/usr/bin/env bash
# Build the whole Loan Origination System from nothing, in order. Every step is re-runnable; a failed run can simply be
# started again. About 20-30 minutes on a laptop, most of it the Lending Club download (1.6 GB) and loading 1.34M loans.
#   setup/install.sh                    everything
#   LC_CSV=/path/accepted.csv setup/install.sh    reuse a Lending Club file you already have
#   setup/install.sh --from <step>      resume at a step (names below)
# Steps: check venv sources connectors book generate attach documents model facts decisions logins walkins ml bureau
#        semantic service console preflight
source "$(dirname "$0")/common.sh"
STEPS=(check venv sources connectors book generate attach documents model facts decisions logins walkins ml bureau semantic service console preflight)
FROM=check
case "${1:-}" in
  "") ;;
  --from) [[ -n "${2:-}" ]] || die "--from needs a step name (one of: ${STEPS[*]})"; FROM="$2" ;;
  *) die "unknown argument '$1'. Usage: setup/install.sh [--from <step>]   steps: ${STEPS[*]}" ;;
esac
[[ " ${STEPS[*]} " == *" $FROM "* ]] || die "unknown step '$FROM' (one of: ${STEPS[*]})"
go=0
CUR=""
step() { [[ "$1" == "$FROM" ]] && go=1; (( go )) && CUR="$1"; (( go )); }
# If any step fails, say which one and how to carry on from there instead of starting again.
trap 'rc=$?; if (( rc )) && [[ -n "$CUR" ]]; then printf "\n    \033[1mfailed at step %s.\033[0m Fix the error above, then resume: setup/install.sh --from %s\n" "$CUR" "$CUR" >&2; fi' EXIT
sqlf() { for f in "$@"; do xfile "$ROOT/sql/$f.sql" || die "sql/$f.sql failed"; ok "sql/$f.sql"; done; }

if step check; then
  say "Prerequisites"
  for c in exasol exapump uv curl python3; do command -v "$c" >/dev/null || die "'$c' is not installed (see README: Prerequisites)"; done
  command -v docker >/dev/null || command -v podman >/dev/null || die "Docker or podman is needed to fetch the container images"
  [[ -f "$HOME/.exapump/config.toml" ]] && grep -q "^\[$EXAPUMP_PROFILE\]" "$HOME/.exapump/config.toml" \
    || die "no [$EXAPUMP_PROFILE] profile in ~/.exapump/config.toml (the Exasol starter kit writes it)"
  [[ -f "$RUNTIME/vm-runtime.json" ]] || die "no Exasol Personal VM found under $RUNTIME (deployment '$EXASOL_DEPLOYMENT')"
  xsql "SELECT 1;" | grep -q 1 || { exasol start -d "$EXASOL_DEPLOYMENT" >/dev/null 2>&1 || true; xsql "SELECT 1;" | grep -q 1 || die "Exasol does not answer: exasol start"; }
  "$ROOT/setup/vm.sh" true || die "cannot reach the Exasol VM over SSH"
  curl -sf -m 5 -o /dev/null "http://127.0.0.1:$DASH_SERVER_PORT/" || printf '    \033[0;33mnote\033[0m dash-server is not answering on :%s; the console step needs it (exakit marketplace)\n' "$DASH_SERVER_PORT"
  ok "exasol, exapump, uv, container engine, Exasol answering, VM reachable"
fi

if step venv; then
  say "Python environment (.venv, Python 3.12)"
  # an existing .venv of another Python version (an IDE may have made one) is replaced, not reused
  [[ -x "$PY" ]] && ! "$PY" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' && rm -rf "$ROOT/.venv"
  [[ -x "$PY" ]] || uv venv "$ROOT/.venv" --python 3.12 >/dev/null
  uv pip install --quiet --python "$PY" -r "$ROOT/requirements.txt"
  ok "$("$PY" -V)"
fi

step sources    && "$ROOT/setup/00_sources_vm.sh"
step connectors && "$ROOT/setup/01_connectors.sh"

if step book; then
  say "The loan book: 1.34M real Lending Club loans, and the scorecard trained on them"
  LC_SHA256=3eae03c28fd9d2e8a076ebeb73507e8d4d0f44d90500decdb0936e0933d1f36a
  if [[ -n "${LC_CSV:-}" ]]; then        # your own copy: it must exist and be exactly the published file
    [[ -s "$LC_CSV" ]] || die "LC_CSV=$LC_CSV: file not found"
    echo "$LC_SHA256  $LC_CSV" | shasum -a 256 -c --status \
      || die "LC_CSV=$LC_CSV is not the pinned Lending Club file (SHA-256 differs): unset LC_CSV to download it"
  fi
  LC="${LC_CSV:-$WORK/dl/accepted.csv}"
  if [[ ! -s "$LC" ]]; then
    mkdir -p "$WORK/dl"
    # Pinned to one revision of the dataset and checked against its SHA-256: every number the console shows comes from
    # exactly this file. -C - resumes an interrupted download instead of starting the 1.6 GB again.
    LC_REV=c435da047e81f2875a23827c1548f5083a33d178
    curl -fL --retry 5 -C - -o "$LC.part" "https://huggingface.co/datasets/codesignal/lending-club-loan-accepted/resolve/$LC_REV/accepted_2007_to_2018Q4.csv"
    echo "$LC_SHA256  $LC.part" | shasum -a 256 -c --status \
      || die "the downloaded loan history does not match its published SHA-256: delete $LC.part and run setup/install.sh --from book"
    mv "$LC.part" "$LC"
  fi
  "$PY" "$ROOT/data/prepare_book.py" "$LC"
  "$PY" "$ROOT/data/train_scorecard.py"
fi

if step generate; then
  say "Synthetic lender: 2,400 applications into core banking (Postgres) and the document store (MongoDB)"
  "$PY" "$ROOT/data/generate.py"
fi

step attach && "$ROOT/setup/02_sources.sh"
if step documents; then say "PDFs: sample packs and the ring's payslips"; "$PY" "$ROOT/data/documents.py"; fi
if step model;     then say "Semantic views, policy"; sqlf 12_model 10_src 15_policy; fi
step facts && "$ROOT/setup/03_reload_bureau.sh"
if step decisions; then say "Contract tables, decision engine, back-test, fraud"; sqlf 50_semantic 30_decisions 35_backtest 40_fraud; fi
if step logins;    then say "Database logins for the service"; "$PY" "$ROOT/setup/05_governance.py"; fi
if step walkins;   then say "Walk-in customers, bureau file, document-store writer"; "$PY" "$ROOT/data/walkins.py"; fi
step ml       && "$ROOT/setup/06_ml.sh"
step bureau   && "$ROOT/setup/08_bureau_api.sh"
step semantic && "$ROOT/setup/07_semantic.sh"
if step service; then say "LOS service"; "$ROOT/service/run.sh"; fi
if step console; then say "Console on dash-server"; "$PY" "$ROOT/dash/deploy.py"; fi
if step preflight; then "$ROOT/setup/preflight.sh" --reset; echo; echo "Open $CONSOLE"; fi
