# Research — pers-375-silent-key-regeneration

- **Slug**: pers-375-silent-key-regeneration
- **Created**: 2026-11-27
- **Evidence confidence (overall)**: high for the code facts, medium for runtime consequences

## Sources

All repository citations are at `pilot/spec-kit-baseline` `e64d1ed853de18e6797b8422aacebb3fec9f017e`; the file is byte-identical on `main` `af282761b40dbbb1dafc41fc4b2e777750a4d20a`.

- `README.md:113` — the guard as documented to operators.
- `rootfs/usr/local/bin/configure_privacyidea.sh:198-221` — key-path export, bootstrap marker, skip branches.
- `configure_privacyidea.sh:225-246` — the non-SQLite refusal and its database probe.
- `configure_privacyidea.sh:250-271` — encryption-key and audit-key creation.
- `configure_privacyidea.sh:293-294` — marker written only after a successful bootstrap.
- `bf2c26ee` — the commit that added the refusal, dated four minutes after the issue report; its message cites `#2`.
- `tests/`, `.github/workflows/ci.yml:150-155`, `docker-compose-test.yml:8-18` — CI coverage; the integration suite is SQLite-only.
- GitHub issue #2, `mr-ssd/privacyidea-docker` — the report itself, still open with no comments.
- Upstream privacyIDEA `privacyidea/cli/pimanage/pi_setup.py` — `create_enckey`, `create_audit_keys`, `create_tables` semantics.

## Findings

### The reported total-loss path is already refused

- With a non-SQLite URI, no `PI_ENCFILE`, and no marker, `configure_privacyidea.sh:229` enters the guard, probes the database at `:230-240`, and exits 1 at `:241-245` when `token`, `admin` or `alembic_version` exists. The message tells the operator to restore the key volume. Confidence: high (cited).
- The marker is written only after bootstrap completes (`:293-294`), so a volume that never completed bootstrap does not suppress the guard. Confidence: high (cited).
- Commit `bf2c26ee` states `Refuse to regenerate keys when an existing DB lacks them (#2)`; `git merge-base --is-ancestor bf2c26e e64d1ed` succeeds. Confidence: high (cited).

### Three residual paths are not covered

1. **Audit keys are never guarded.** `configure_privacyidea.sh:264-271` runs `create_audit_keys` whenever `private.pem` is missing, with no database probe. If the encryption key survives but the audit keys do not, the container starts and signs new audit entries with a new key; signatures made with the old key no longer verify. That is the second half of issue #2's stated harm ("old audit signatures stop verifying") and it contradicts `README.md:113`'s "key files" (plural). Confidence: high (cited).
2. **The marker-present path bypasses the guard entirely.** With `.privacyidea_initialized` present, `:218-221` skips the whole bootstrap block, so neither the refusal nor key creation runs. This happens when the data directory survives but a separately mounted key path does not — the overrides at `:201-203` are documented in `README.md:98-99`. What privacyIDEA then does with a missing `PI_ENCFILE` is not verified here (upstream opens the file during security-module construction), but the intended actionable refusal is not reached. Confidence: medium.
3. **The database probe fails open.** The Python block at `:230-240` catches every exception and prints nothing; `schema_present` is then empty and the guard does not fire. A transient database error, a wrong password or a missing permission is therefore read as "no data". Confidence: high for the code path, medium for the operational window.

### The empty-key branch does not do what it says

- `:250-256` treats a missing **or empty** `PI_ENCFILE` as "create a new one". Upstream `create_enckey` refuses to overwrite an existing file and exits non-zero (`pi_setup.py`), and `configure_privacyidea.sh` runs under `set -e`, so an empty key file aborts the boot with "already exist. We do not overwrite it!" rather than the refusal the guard intends. The data is not destroyed, but the operator gets a misleading failure. Confidence: high (cited).

### Evidence for a change

- One of the two harms named in issue #2 — invalidating audit signatures — still has no guard at the point where the key is regenerated.
- `README.md:113` already promises the broader behaviour, so the code and the documented contract differ today.
- No test covers the guard, so the residual paths can regress unnoticed; the existing integration suite cannot reach the guard because it is SQLite.
- The fix is local to one shell script and its tests: no schema, API or workflow change.

### Evidence against a change

- The exact reproduction in issue #2 (lost `/data/privacyidea/keys` on a non-SQLite database) is already refused at the base; a naive "fix issue #2" change would duplicate shipped behaviour.
- Regenerating audit keys is harmless for installations that run with `PI_AUDIT_NO_SIGN=true` or that accept losing verifiability of old entries, and a hard refusal removes that choice unless it is made conditional.
- A missing-key failure is rare and operator-induced; the cost of a wrong refusal (a container that cannot boot) can be higher than the cost of the remaining gap.
- Any change to bootstrap is on the critical start path of every deployment, which raises the review bar.

## Evidence Against the Idea

The strongest case against acting is that the reported reproduction no longer reproduces: the total-loss path exits 1 before any key is written. If the assessment stopped at that repro, the correct answer would be to close issue #2 and change nothing. The case for acting rests only on the audit-key and marker-present paths, which are narrower triggers and are not reproduced by the original report.

## Gaps & Open Questions

- [NEEDS CLARIFICATION: should a missing audit key be fatal when `PI_AUDIT_NO_SIGN=true`, or should the guard apply only when audit signing is active?]
- [UNVERIFIED: what privacyIDEA does at startup when `PI_ENCFILE` is absent but the marker is present; no container run was performed.]
- [UNVERIFIED: whether any deployment actually separates the key path from `PI_DATA_DIR`; the override is documented but no deployment inventory exists in the repository.]
