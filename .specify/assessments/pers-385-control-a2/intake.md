# Intake — pers-375-silent-key-regeneration (PERS-375)

Prompt: PERS-375, first real Spec Kit idea case on `mr-ssd/privacyidea-docker`. Subject: GitHub issue #2, "Silent encryption-key regeneration on lost volume" (open, created 2026-11-06T03:28:57Z). Assess on repository evidence whether a change is warranted; do not implement.

## Request

Decide, from the repository at `pilot/spec-kit-baseline` (`e64d1ed853de18e6797b8422aacebb3fec9f017e`), whether the silent key-regeneration defect reported in issue #2 still needs work, and record a go / needs-clarification / kill verdict. The issue asks for one behaviour: refuse to regenerate keys when a non-SQLite database already holds privacyIDEA data but the key files are missing, and require a key-volume restore instead.

## Evidence gathered (sources)

- `rootfs/usr/local/bin/configure_privacyidea.sh:198-203` — key paths are resolved and exported once, so the guards and privacyIDEA read the same `PI_ENCFILE`, `PI_AUDIT_KEY_PRIVATE_PATH` and `PI_AUDIT_KEY_PUBLIC_PATH`.
- `configure_privacyidea.sh:208-221` — a `.privacyidea_initialized` marker in `PI_DATA_DIR` decides whether bootstrap runs; `PI_SKIP_BOOTSTRAP=true` also skips it.
- `configure_privacyidea.sh:225-246` — for a non-SQLite database with no `PI_ENCFILE`, a SQLAlchemy probe lists the tables and the script exits 1 if `token`, `admin` or `alembic_version` exists.
- `configure_privacyidea.sh:250-271` — the encryption key is created when the file is missing **or empty**; audit keys are created whenever `private.pem` is missing, with no database check.
- `README.md:113` — documents the guard as "startup refuses to generate new keys if privacyIDEA data exists but key files are missing" (plural keys).
- `bf2c26eea0a83d68b3b4c2af8dbe6ea688abfa56` (2026-11-06 03:32:43Z, ~4 minutes after issue #2 was filed) — commit message names `Refs #1, #2, #4, #7, #12` and adds the refusal; it is an ancestor of `e64d1ed`, and the file is byte-identical on `main` (`af282761b40dbbb1dafc41fc4b2e777750a4d20a`).
- Upstream privacyIDEA `cli/pimanage/pi_setup.py` — `create_enckey` and `create_audit_keys` refuse to overwrite an existing file; `create_tables` refuses a database that already holds privacyIDEA tables unless `--force`.
- `tests/` and `.github/workflows/ci.yml` — no test exercises bootstrap key loss; the Compose suite uses SQLite, which the guard excludes.

## Uncertainty

- No container was built or run for this assessment. The consequence of reaching Gunicorn with the marker present and the key file absent depends on when privacyIDEA initialises its default security module; that is not verified here.
- The privacyIDEA package version is resolved from PyPI at image build (`Dockerfile:2,17-29`), so upstream CLI behaviour is not pinned by this repository.
- Whether a missing audit key should be fatal, and whether `PI_AUDIT_NO_SIGN=true` should exempt it, is a maintainer policy question rather than a code fact.

## Confidence

High that the reported total-loss path on a non-SQLite database is already mitigated at the base and that the audit-key path is not. Medium on the runtime severity of the marker-present path; low on any claim about a live deployment, which was not exercised.
