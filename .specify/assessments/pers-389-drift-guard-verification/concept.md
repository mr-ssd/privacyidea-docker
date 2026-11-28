# Concept — shape of the verification case

An `idea` case is the lightest case type the policy allows: five assessment reports plus
the trace manifest, nothing else. The tradeoff taken: an idea case exercises the full
case-mode gate (guard, `check.py verify`, five `check-case.py` ids) without touching any
file the manifest policy would complicate — no Makefile, no README, no spec directory.

The manifest pins `reviewed_baseline_sha` to the new pilot tip `6bc3114c…`, so the PR must
branch from exactly that commit; a branch cut from the pre-landing tip `18949394…` would
fail the `base == PILOT_BASELINE_SHA` check for a reason unrelated to the guard. The
expected outcome is a green run whose bundle shows four PASS rows in
`trusted-drift.jsonl`, each archive digest equal to the deployed digest and equal to the
values verified from the fetched archive in this issue's checks 1–2.
