# Research — sources for the drift-guard verification case

Sources consulted (all read from server bytes on 2026-11-28, not from reports):

- The runbook archive, fetched via `RUNBOOK_ARCHIVE` and verified against
  `RUNBOOK_SHA256` = `59b77697…`; its `SHA256SUMS` lists all five members and verifies rc 0.
  Confidence: high — this is the same fetch-and-verify chain the guard itself runs.
- The deployed copies at `6bc3114c…` on `pilot/spec-kit-baseline` (and `d58bd1e6…` on
  `main`): all four guarded paths byte-equal their archive members.
- The design note in PERS-387 (section "Acceptance checks") and the landing report on
  PERS-389: they agree on the post-landing values. Confidence: high — re-derived here.

Arguments for running the positive control as a real case PR on the pilot branch: it
exercises the exact path every future case takes, including case-mode staging of the
archive, the guard position after head checkout, and `check-case.py` over the five
IDEA ids. Arguments against: it costs one workflow run and one scratch PR that must be
closed unmerged — acceptable, since Quality may not merge and the case head carries no
workflow change, so the runbook's case-policy limit is not violated.

The evidence source of record for the run is the workflow artifact
(`spec-kit-<case>-<head>`), whose `check-result.json` records the gate exit code and the
check-run URL; `trusted-drift.jsonl` is the byte-equality record this case exists to
produce. Confidence in the method: high.
