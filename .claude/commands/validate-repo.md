---
description: Validate this repo for public release - runs 5 read-only specialist subagents in parallel and writes a consolidated report with a READY / NOT READY verdict
argument-hint: "[scope: folder, default whole repo] [-- notes for reviewers, e.g. names that must not appear]"
---

# /validate-repo

Arguments: `$ARGUMENTS`

You orchestrate a release-readiness review of this repository for a wide public audience: a stranger must be able to
clone it, understand it, run it, and find nothing embarrassing, insecure or broken. You do **not** fix anything. The
only file you write is the report.

## 1. Resolve scope and context

- Split the arguments on the first ` -- `. Before it: the scope. After it: free-text notes for the reviewers (for
  example names of customers, prospects or internal projects that must not appear publicly). Never write the notes
  into any file in the repository, including the report: in the report, refer to them as "the names given at run time".
- Empty scope → the whole repository. Otherwise the scope must be an existing directory inside the repo (relative to
  the repo root); if not, stop and tell the user which folders exist.
- Collect run facts with one Bash call: repo root (`git rev-parse --show-toplevel`), HEAD (`git rev-parse --short HEAD`),
  branch, `git status --porcelain | wc -l` (uncommitted changes are NOT what strangers will get; say so in the report),
  today's date, and which tools are on PATH: `gitleaks trufflehog uv uvx node npx docker shellcheck ruff pip-audit`.
- Determine the repo's shape: several demo folders, or one demo with component folders. The scorecard (step 4) is per
  demo in the first case, per top-level component in the second.

## 2. Launch the five specialists in parallel

In ONE message, launch these five subagents with the Agent tool, concurrently:
`security-auditor`, `reproducibility-tester`, `documentation-reviewer`, `code-quality-reviewer`,
`demo-experience-reviewer`.

Give each the same brief: repo root (absolute path), scope, HEAD SHA, the run date, tools available, the repo shape,
and the notes. Remind each: read-only, follow the hard rules in your agent file, return exactly the output format in your
agent file, evidence for every finding.

If a subagent type is not available in this session (new agent files are only picked up when a session starts), launch a
`general-purpose` agent instead whose prompt is: "Read `.claude/agents/<name>.md` in <repo root>. Those are your
instructions; follow every hard rule in it (you are read-only: never use Write, Edit or any command that changes the
repository or shared state). <brief>". Record in the report which agents ran this way.

Wait for all five. If one fails or times out, do not invent its results: its checks go in "Checks skipped" with the
reason.

## 3. Consolidate

1. **Validate.** Drop nothing silently. A finding without a location or evidence becomes `needs human review` and drops one
   severity level. Spot-check every CRITICAL and HIGH yourself with a Read or Grep of the cited line before you accept
   it; if it does not hold up, downgrade it or mark it `needs human review`, and say so.
2. **De-duplicate.** Same root cause at the same location (or the same pattern across files) = one finding. Keep the
   highest severity, list every reporting agent and every location, merge the fixes.
3. **Calibrate severity** with these definitions, whatever the agent said:
   - CRITICAL: leaked secret, security hole, or the main demo cannot run. Blocks publishing.
   - HIGH: a typical user will get stuck or be misled.
   - MEDIUM: friction, inconsistency, or quality issue.
   - LOW: polish.
4. **Number** final findings `F-01 …` in severity order (CRITICAL first; within a level, the ones a stranger hits first).
5. **Verdict:**
   - NOT READY: any CRITICAL, or more than 3 HIGH.
   - READY WITH MINOR FIXES: no CRITICAL and 1–3 HIGH, or no HIGH but more than 10 MEDIUM.
   - READY TO PUBLISH: no CRITICAL, no HIGH, at most 10 MEDIUM.

## 4. Write the report

Path: `validation-reports/report-<YYYY-MM-DD>.md` (create the folder if needed). If that file exists, use
`report-<YYYY-MM-DD>-2.md`, `-3`, and so on: never overwrite an earlier report. Secrets stay redacted (first 4
characters + `****`).

```
# Repository validation report: <repo name>
Date · scope · commit <sha> on <branch> · uncommitted changes: <n> (not included in what strangers get)

## Executive summary
**Verdict: <READY TO PUBLISH | READY WITH MINOR FIXES | NOT READY>**, one sentence on why.
| CRITICAL | HIGH | MEDIUM | LOW | needs human review |
Top 5 issues: one line each, with F-number.
(If any secret is in git history: a boxed warning that deleting the file is not enough: rotate the credential first,
then rewrite history with git filter-repo or BFG, force-push, and ask GitHub to purge cached views; forks keep it.)

## Findings
### CRITICAL
#### F-01 <title>
- **Category:** … · **Reported by:** … · **Check:** SEC-02, …
- **Location:** `path:line` (all locations)
- **What is wrong:** …
- **Why it matters for a public audience:** …
- **Suggested fix:** …
- **Evidence:** …
- **Confidence:** confirmed | needs human review
### HIGH … ### MEDIUM … ### LOW …
(MEDIUM and LOW may use a compact table if there are many: F-no, check, location, issue, fix.)

## Scorecard
Per demo (or per component): rows; columns Security · Runs · Docs · Code · Experience.
✅ no issue above LOW · ⚠️ MEDIUM present · ❌ HIGH or CRITICAL present · — not checked. Then a one-line note per row.

## README walk-through (from reproducibility-tester)

## Checks run and skipped
Table of every check ID from VALIDATION_CHECKLIST.md: RAN / PARTIAL / SKIPPED, the tool or method, and the reason
for anything not fully run. A check is "passed" only if it RAN and found nothing. Never mark a skipped check as passed.

## Run notes
Agents and how they ran (named subagent or general-purpose fallback), tools used, temp directories cleaned up.
```

## 5. Reply to the user

Show: the verdict, the severity counts, the top 5, the report path, and (if applicable) the git-history secret
remediation in plain words. Then ask whether they want you to fix the issues, starting with the CRITICAL ones. Do not
change any repository file until they say yes.
