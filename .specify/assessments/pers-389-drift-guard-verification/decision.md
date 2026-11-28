# Decision — positive control vehicle

Proceed with this idea case (`pers-389-drift-guard-verification`) as the check-5
positive control: branch from `6bc3114c…`, add exactly the six allowed files, open the PR
against `pilot/spec-kit-baseline`, and require a green gate run with four PASS rows in
`trusted-drift.jsonl`. If the run is red, report the failure with the bundle evidence and
stop — fixes belong to Build.

The PR is closed unmerged: Quality may not merge, and merging any case would advance the
pilot tip and invalidate the freshly re-baselined `PILOT_BASELINE_SHA` for the rest of the
chain. The run record, not the merge, is the deliverable.

Verdict: go
