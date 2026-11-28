# Problem — what the positive control must prove

The PERS-383 incident class is a drifted trusted checker vouching for itself: in case
mode the checkers are staged from the pinned baseline, so a drifted baseline makes every
case run pass while the deployment is corrupt. The 1.0.6 guard closes that by comparing
each of the four guarded members against the SHA-verified runbook archive at the PR head,
in both modes.

Unproven until a green case run exists on the re-baselined pilot tip: that the guard's
case-mode path — archive fetch and verify into `$ROOT/archive`, then the four comparisons
against the head copies — executes cleanly on a real case PR and writes four PASS rows
with the correct digests. The design note's check 5 is exactly that run; this case is its
vehicle. A red run here would mean either a defect in the landed workflow or a real
drift between the archive and the deployed pilot state — both blockers, to be reported
with evidence, not fixed here.
