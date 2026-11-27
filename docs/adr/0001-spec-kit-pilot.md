# ADR 0001 — Isolated Spec Kit pilot on privacyidea-docker

- Status: accepted (pilot execution approved 2026-11-27T07:37:59Z)
- Issue: PERS-327 (child of PERS-311)
- Authorization: `Approve isolated pilot execution after PERS-317 PASS; zero workspace agent changes`

## Context

PERS-311 approved planning a Spec Kit software-factory rollout. The plan (V12
revision 3 on PERS-312, comment `01a21b87-f322-7d36-9e5b-811d4768046b`,
124,943 bytes, SHA-256 `6c80f89a70d45de7019c839146a642d2768046fadf7599f9c35590814a04105a`)
passed all gates (PERS-317, PERS-320/PERS-322, PERS-324, PERS-326). The member
approved the isolated pilot on `mr-ssd/privacyidea-docker` at
`f3c01c28cefd6f3df6ea2fe95c4653088ee4024e` with zero workspace agent changes.

## Decision

Run the pilot exactly as the plan's §6 specifies:

1. One branch `pilot/spec-kit-baseline` with exactly three commits:
   reviewed profile + constitution; pinned scaffold (installer-owned files,
   policy, retention, ADR, checker, manifest, bootstrap receipt); trace
   workflow + case dispatcher. One unmerged baseline PR against `main`.
2. Three case PRs against the baseline branch: feature (`test-release-input`
   make target), bug (README:114 `PI_AUTO_UPDATE` wording), idea
   (container-readiness assessment, no implementation), each with a Multica
   case issue, spec artifacts, trace manifest and CI evidence.
3. `specify` pinned at 1.4.5 (`6ba8beefff8d6408cadd62038e92d459093e33a8`),
   codex/opencode/omp integrations, bug + assess extensions, trusted checker and
   receipt, exact-path staging gate, fail-closed case dispatcher.

## Consequences

- Positive: end-to-end proof of the trace workflow (issue ↔ artifacts ↔ PR ↔ CI)
  on a real repository with existing CI preserved.
- Constraints honoured: no merge, no deployment, no release; `main` untouched;
  no skill binding, instruction edit, runtime rebinding or new agent.

## Rollback

Unmerged rollback per plan §6: verify reviewed base/head, close case PRs then
the baseline PR, delete case branches then the baseline branch; retain closed
PR and issue evidence. If later merged, reviewed revert PRs in reverse
dependency order, baseline revert last.
