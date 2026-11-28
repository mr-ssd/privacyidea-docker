# Intake — drift-guard verification case (PERS-389, check 5)

Quality squad is asked to independently verify the runbook 1.0.6 landing on
`pilot/spec-kit-baseline` (pinned `PILOT_BASELINE_SHA` = `6bc3114c…`) against the six
acceptance checks in the PERS-387 design note.

This case is the positive control for the new trusted-checker byte-equality guard
(PERS-385): a case PR opened on the re-baselined pilot tip must run green end to end, and
its evidence bundle must carry `trusted-drift.jsonl` with four PASS rows — archive member
digest equal to deployed digest for `check.py`, `check-case.py`, `managed-files.json` and
`trace-workflow.yml`.

Scope: this case adds only its own assessment reports and trace manifest, exactly the
allowed paths for an `idea` case. No trusted checker, workflow, or managed file is touched.
