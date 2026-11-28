# Decision — pers-375-silent-key-regeneration

- **Slug**: pers-375-silent-key-regeneration
- **Decided**: 2026-11-27
- **Artifacts reviewed**: intake.md, research.md, problem.md, concept.md

## Scorecard

| Criterion | Rating | Justification |
|-----------|--------|---------------|
| Problem validity | adequate | The original reproduction is already fixed at the base, but audit-key regeneration with existing data still silently invalidates old signatures, which is the second harm named in issue #2. |
| Evidence strength | strong | Every claim is read from the pinned base SHA or from upstream `pi_setup.py`; the commit that shipped the partial fix is identified and dated. No container run was performed, and that limit is stated. |
| Value vs. inaction | adequate | A one-script change closes the remaining silent path and aligns code with `README.md:113`; doing nothing leaves a documented promise unmet. |
| Feasibility / appetite | strong | Small: one shell script plus tests; no schema, API, workflow or variable change. |
| Strategic fit | strong | Constitution principle 4 requires docs to match source; the current guard contradicts the README. |
| Risk posture | adequate | The main risk — a stricter guard causing a boot failure — is the intended fail-closed behaviour and is recoverable by restoring the key volume; the `PI_AUDIT_NO_SIGN` exemption and probe-error message are open design points. |

Verdict: go

The idea is worth specifying, but not as "fix issue #2": the total-loss reproduction is already refused by `bf2c26e`. It is worth specifying as a scoped hardening of the existing guard — audit keys, the marker-present path, the fail-open probe, and the empty-key branch — because those paths still produce the harm the issue describes and the README already claims they do not. A `go` hands this to `specify`; it does not authorise implementation, a branch, or a merge, and the maintainers still decide whether a missing audit key should be fatal.

## If go — Handoff to `specify`

- **Problem**: the shipped key-loss refusal covers only the encryption key, only when the bootstrap marker is absent, and only when the database probe succeeds; audit keys and the other paths still regenerate silently.
- **Chosen approach**: Option A — extend the existing refusal in `configure_privacyidea.sh`, keep it non-SQLite-scoped, honour `PI_AUDIT_NO_SIGN=true` as an exemption, and distinguish probe failure from "data present".
- **In scope**: audit-key guard, marker-present handling, fail-closed probe, empty-key handling, and a stub-based test for each path.
- **Out of scope**: SQLite, key rotation, HSM backends, backup/restore tooling, workflows, `.specify` onboarding files.
- **Success metrics**: each residual path exits non-zero with a message naming the missing key and the restore action; no path writes a key file when privacyIDEA tables exist; a shell test fails if any path regresses.
- **Carried-forward open questions**: whether `PI_AUDIT_NO_SIGN=true` exempts the audit guard; what privacyIDEA does at startup when the marker is present and `PI_ENCFILE` is absent; whether any deployment separates the key path from `PI_DATA_DIR`.
