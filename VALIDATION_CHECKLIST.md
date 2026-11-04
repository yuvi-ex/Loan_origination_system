# Validation checklist

Run this before making the repository public, and again before each release or event. The bar: a stranger can clone
it, understand it, run it, and find nothing embarrassing, insecure or broken.

**Automated:** in Claude Code, from the repo root, run `/validate-repo` (whole repo) or `/validate-repo service`
(one folder). Add reviewer notes after ` -- `, for example names that must never appear publicly:
`/validate-repo -- <customer name>, <internal project name>`. Notes are passed to the reviewers but never written to
disk. Five read-only subagents (`.claude/agents/`) run in parallel and the report lands in
`validation-reports/report-<date>.md` (git-ignored). Nothing is fixed automatically.

**By hand:** work through the checks below. Every check ID matches the one the agents report.

## Safety rules for reviewers (human or agent)

- Review a **fresh clone** (`git clone <repo> /tmp/x`), not your working copy: it has only what strangers get.
- Never run `setup/*.sh`, `service/run.sh`, `dash/deploy.py` or `tests/click_test.py` during a review. They change
  the shared Exasol database, its VM containers, BucketFS and dash-server. Read them instead.
- Never paste a full secret into a report: first 4 characters + `****`.

## Severity and verdict

| Severity | Meaning |
|---|---|
| CRITICAL | Leaked secret, security hole, or the main demo cannot run. Blocks publishing. |
| HIGH | A typical user will get stuck or be misled. |
| MEDIUM | Friction, inconsistency, or a quality issue. |
| LOW | Polish. |

| Verdict | Rule |
|---|---|
| NOT READY | any CRITICAL, or more than 3 HIGH |
| READY WITH MINOR FIXES | no CRITICAL and 1–3 HIGH, or no HIGH but more than 10 MEDIUM |
| READY TO PUBLISH | no CRITICAL, no HIGH, at most 10 MEDIUM |

## 1. Security (`security-auditor`)

| ID | Check | How to check by hand |
|---|---|---|
| SEC-01 | No secrets in current files | `gitleaks detect --no-git`, or `uvx --from detect-secrets detect-secrets scan --all-files`, plus `git grep -nIiE '(password\|secret\|token\|api[_-]?key)\s*[:=]\|AKIA[0-9A-Z]{16}\|BEGIN [A-Z ]*PRIVATE KEY\|IDENTIFIED BY'` |
| SEC-02 | No secrets anywhere in git history, including deleted files | `gitleaks detect`, or `git log --all -p \| grep -nE '<same patterns>'` |
| SEC-03 | No credential files ever committed (`.env`, `config.local.env`, `secrets/`, keys, state files) | `git log --all --name-only --format= \| sort -u` |
| SEC-04 | No internal hostnames, private IPs (unless documented local addresses), home paths, employee emails, customer or internal project names | `git grep -nE '/Users/\|/home/\|@[a-z0-9-]+\.(com\|io\|net)'`; `git log --all --format='%ae'` |
| SEC-05 | No real personal data in sample data or PDFs; synthetic data is marked SYNTHETIC | read generators; `pdftotext` the PDFs; grep for PAN/phone/email patterns |
| SEC-06 | `.gitignore` covers env files, secrets, venvs, caches, build output, IDE folders, OS files, logs, every folder the code writes to | compare `.gitignore` with paths the code writes |
| SEC-07 | Placeholders are obviously fake; no working default passwords | grep for defaults |
| SEC-08 | Insecure demo shortcuts (TLS verification off, SQL string building, `eval`/`pickle`/`shell=True`, broad grants, `0.0.0.0`, wildcard CORS) carry a visible warning comment | `git grep -nE 'verify=False\|validate_certificate\|encryption=False\|shell=True\|pickle\.load\|eval\(\|GRANT .* TO PUBLIC\|0\.0\.0\.0'` |
| SEC-09 | No known vulnerable dependencies | `uvx pip-audit -r requirements.txt` |
| SEC-10 | Generated credentials stored safely (mode 600, git-ignored) and never printed or logged | read the login/secret creation steps |

**If a secret is found in history:** deleting the file is not enough, because every clone and fork keeps it. First
rotate or revoke the credential. Then rewrite history (`git filter-repo --invert-paths --path <file>` or BFG),
force-push every branch and tag, and ask GitHub support to purge cached views. Forks keep the old history, which is
why rotating comes first.

## 2. Reproducibility (`reproducibility-tester`)

| ID | Check | How to check by hand |
|---|---|---|
| REP-01 | A fresh clone contains everything the code needs | clone to a temp directory; compare with your working copy |
| REP-02 | The README, followed literally and in order, works; the `cd` folder matches what `git clone` creates | walk it step by step, record every failure or ambiguity |
| REP-03 | Every import and every CLI tool is declared (requirements, Prerequisites, or the environment it runs in: UDF, container, dash-server) | grep imports, map to `requirements.txt` |
| REP-04 | Versions pinned or bounded: Python packages, container image tags, downloads, language containers | read `requirements.txt` and scripts |
| REP-05 | Runtime versions documented and enforced (`.python-version`, installer check) | `uv venv --python 3.12` + install in a temp dir |
| REP-06 | Every setting the code reads is documented with an example (`config.env` acts as `.env.example`) | grep `CFG[`, `os.environ`, `$VAR` |
| REP-07 | No hardcoded absolute paths; OS/CPU assumptions stated (macOS-only commands, arm64 vs amd64, Windows support) | grep `/Users/`, `caffeinate`, `sed -i`, `stat -f` |
| REP-08 | Files that are not in the repo are created by a documented step before they are read | follow each read of an ignored/generated path |
| REP-09 | Entry points either run, or fail with a one-line message naming the fix (no traceback) when credentials/config are missing | run them from the temp clone without config |
| REP-10 | External downloads and image tags still exist | `curl -sIL <url>` |
| REP-11 | Install time, disk space and network needs are stated and accurate | compare README with scripts |

## 3. Documentation (`documentation-reviewer`)

| ID | Check | How to check by hand |
|---|---|---|
| DOC-01 | Root README has purpose, audience, prerequisites, quick start, structure, how to run, expected result, configuration, troubleshooting, uninstall, license, contribution and support | read it |
| DOC-02 | Each demo has its own README (or, for one demo with components, the root README covers each part) with expected output and paid-API cost | read it |
| DOC-03 | Every command is copy-pasteable and correct: folders, script names, flags, step names, env vars exist | check each against the script source |
| DOC-04 | Internal links, anchors and images resolve (case-sensitive) and images have alt text | open each |
| DOC-05 | External links answer | `curl -sIL` |
| DOC-06 | No unexplained jargon, TODOs, placeholders, stale dates, numbers or screenshots | read it against the code |
| DOC-07 | Spelling and grammar | `uvx codespell` |
| DOC-08 | `LICENSE` exists, matches README, has a complete copyright holder; third-party data and logos have their terms stated | read it |
| DOC-09 | CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md present | `ls` |
| DOC-10 | Paid APIs, large downloads and data licenses are disclosed | read it |

## 4. Code quality (`code-quality-reviewer`)

| ID | Check | How to check by hand |
|---|---|---|
| CQ-01 | Existing linters, formatters, type checkers and tests run clean (tests needing live services are skipped and say so) | run them |
| CQ-02 | With no config: `uvx ruff check --isolated`, `uvx --from shellcheck-py shellcheck -S warning setup/*.sh service/*.sh`, `python -m py_compile`, `uvx sqlfluff parse --dialect exasol sql/*.sql` | run them; don't add config to the repo |
| CQ-03 | No commented-out code, debug prints, leftover experiments, unused files | grep, and check each file is referenced |
| CQ-04 | No large or generated binaries committed (current files and history) | `git rev-list --objects --all \| git cat-file --batch-check` |
| CQ-05 | Consistent naming, layout, error handling, config reading across demos/components | read it |
| CQ-06 | Readable for learners: names, "why" comments on non-obvious parts, no dense one-liners | read it |
| CQ-07 | No swallowed errors; network calls have timeouts | grep `except`, `|| true`, `timeout` |
| CQ-08 | Dependency licenses are compatible with the repo license | `pip-licenses` in a throwaway venv |

## 5. Demo experience (`demo-experience-reviewer`)

| ID | Check | How to check by hand |
|---|---|---|
| DX-01 | Purpose obvious in 30 seconds from the README's first screen | show it to someone new |
| DX-02 | The demo shows something meaningful and the expected output is documented; screenshots are current | compare with the running UI |
| DX-03 | Error messages say what went wrong and what to do next | read `die`/`raise`/error UI paths |
| DX-04 | Paid APIs (e.g. Amazon Textract) have no uncapped loops, have timeouts, have a cost note and a free fallback | read the calls |
| DX-05 | Sample data is small, licensed, free of real personal data, and real company names are not used as fake ones | read generators and PDFs |
| DX-06 | Nothing unprofessional or internal: customer or prospect names, internal project names, jokes, frustrated comments, commit messages | grep, `git log --format=%s` |
| DX-07 | UI accessibility basics: alt text, contrast ≥ 4.5:1, status not by colour alone, keyboard use, visible focus | inspect theme and layout |
| DX-08 | Reset and uninstall are documented; background services are disclosed | read the README |
