# Concept — pers-375-silent-key-regeneration

- **Slug**: pers-375-silent-key-regeneration
- **Created**: 2026-11-27
- **Recommended option**: Option A — extend the existing refusal to the residual paths

## Options

### Option A — Extend the existing guard (recommended)

- **Sketch**: keep the shipped refusal and close the paths it misses. Apply the same database probe before creating audit keys; run the key-presence check before the marker short-circuit (or make the marker conditional on the keys being present); make a probe error a refusal rather than a pass; and handle an existing-but-empty key file with the refusal message instead of a "create" attempt that upstream rejects. The user-visible result is one consistent failure: the container stops and names the missing key path and the restore action.
- **Appetite**: small (days).
- **Trade-offs**: wins consistency with `README.md:113` and closes the audit-signature half of the report; sacrifices the ability to boot with a deliberately discarded audit key unless `PI_AUDIT_NO_SIGN=true` is honoured as an exemption, and makes a transient database outage at first boot look like a key problem unless the message distinguishes probe failure from data present.
- **Rabbit holes**: deciding whether the guard is about "data exists" or "keys absent"; making failure messages distinguish three causes (probe error, data present, empty key) without turning the shell script into a state machine; and testing without a live non-SQLite database in CI.

### Option B — Close issue #2 as already fixed, document the residual paths

- **Sketch**: no code change. Amend `README.md:113` to say the refusal covers the encryption key only when the marker is absent, and open separate issues for audit keys and the marker path.
- **Appetite**: small (hours).
- **Trade-offs**: wins zero risk on the start path; sacrifices the audit-signature half of the reported harm, leaves the code/docs mismatch in place, and spreads one coherent guard across several issues.
- **Rabbit holes**: the separate issues are likely to be deprioritised, so the gap persists indefinitely.

### Option C — Do nothing

- **Sketch**: leave the code as it is; operators are expected to restore key volumes.
- **Appetite**: none.
- **Trade-offs**: wins nothing beyond avoiding change; sacrifices the documented contract and leaves the audit-key regeneration silent.
- **Rabbit holes**: none; this is the status quo.

## Recommendation

Option A. The reported total-loss reproduction is already refused, so the work is not "implement issue #2" but "finish the guard the README already promises". The change stays in one shell script plus tests, needs no schema or workflow change, and removes the last silent regeneration path this repository can reach. Option B is the fallback if maintainers decide audit-key loss should not block a boot; it should then be recorded as an explicit exception, not left implicit.

## Tradeoff

The core tradeoff is failing closed on missing keys versus a container that cannot boot. A strict guard stops a privacyIDEA instance from starting whenever key material and data disagree — the safe outcome for token and audit integrity, but it also turns a recoverable operational mistake into an outage and removes any legitimate "start without audit signing" choice unless `PI_AUDIT_NO_SIGN=true` is exempted. A permissive guard keeps containers bootable but reintroduces exactly the silent regeneration issue #2 reports. The recommendation leans to failing closed because the failure is loud, actionable and recoverable by restoring a volume, whereas silent regeneration is unrecoverable.

## Out of Scope (for the recommended option)

- SQLite deployments and any change to the SQLite key/database colocation.
- Encryption at rest, HSM backends, or key rotation.
- Backing up or restoring key material; the guard only refuses, it does not repair.
- Any workflow, `.specify` onboarding file, or CI change.

## Assumptions to Validate

- `PI_AUDIT_NO_SIGN=true` is the intended opt-out from audit signing, so the guard can be conditional on it.
- A database probe failure at first boot should be reported as its own error, not conflated with "data present".
- CI can cover the guard with a shell-level test using stubs, without adding a live PostgreSQL service.
