# Rollout plan — R-DEMO (r3)

Protocol: convergence/1 · Parent: PERS-DEMO · Lead: Build
## Objective & scope
Adopt the convergence protocol on a fixture repository. Out of scope: cohort
application, provider metering, new agents.
## Inventory
- Runbook: `docs/release-runbook.md` · trace gate: `.github/workflows/spec-kit-trace.yml`
- Tooling: `.github/scripts/pins.py`, `.github/scripts/plan_lint.py`
## Rules & constraints
R1–R8 of the convergence protocol, referenced by ID. The trace gate and the
runbook evidence contract are unchanged.
## Stage plan
| Stage | Squad | Deliverable | Gate |
|---|---|---|---|
| 1 | D&K | protocol, template | G1–G8 |
| 2 | Build | pins.py, linter, CI job | G1–G8 + controls |
| 3 | Quality | dry-run metrics | per-target PASS/FAIL |
## Sub-issue budget
Declared: 20 · Consumed: 3 · Remaining: 17 (crossing needs member approval)
## Pins (generated — do not edit by hand)
<!-- pin:runbook_version -->runbook_version: 1.0.6<!-- /pin:runbook_version -->
<!-- pin:archive_sha256 -->archive_sha256: pinned at ledger r6 (plan-pins.json)<!-- /pin:archive_sha256 -->
<!-- pin:gist_url -->gist_url: https://gist.github.com/example/runbook-evidence<!-- /pin:gist_url -->
## Evidence pointers
- Gate r3: PERS-DEMO-2 · Sweep r6: PERS-DEMO-3
- Operator pasted the tarball digest here: 9a8b7c6d9a8b7c6d9a8b7c6d9a8b7c6d9a8b7c6d9a8b7c6d9a8b7c6d9a8b7c6d
## Revision log
- r1: initial plan (PERS-DEMO-1)
- r2: stage plan corrected (PERS-DEMO-2)
- r3: pin sweep (PERS-DEMO-3)
