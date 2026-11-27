# privacyidea-docker Constitution

Repository-owned constitution for Spec Kit onboarding, derived from the reviewed
project profile (`docs/project-profile.md`, verified 2026-11-26 against
`f3c01c28cefd6f3df6ea2fe95c4653088ee4024e`). Prepared for human review as part
of the isolated Spec Kit pilot (PERS-327); amendments require human maintainer
approval through review.

## Principles

1. **Runtime safety.** The container runs non-root (`USER nobody`) under `tini`
   as PID 1 with Gunicorn `exec`'d as its direct child, so signals are delivered
   correctly (`Dockerfile:61-70`, `rootfs/usr/local/bin/privacyidea_entrypoint.sh:33-50`).
2. **Reproducible builds.** The Docker base image is pinned by index digest and
   GitHub Actions are pinned by full commit SHA (`Dockerfile:1,10,48`;
   `.github/workflows/ci.yml:22-28`).
3. **Release discipline.** CI success alone never authorizes publication. Release
   writes and tag meanings follow the approval boundaries in
   `docs/release-runbook.md:5-22`; the release-input resolver and promotion
   scripts are the validated entry points (`.github/scripts/resolve-release-input.sh`,
   `.github/scripts/promote-release.sh`).
4. **Docs must match source.** README wording is verified against the `rootfs`
   scripts it describes; known drift is recorded in the project profile's
   "Known drift and verification limits" section.
5. **Tracked CI is the test contract.** Hadolint (error threshold), ShellCheck
   (error severity), actionlint, `tests/test-release-input.sh` (which also runs
   `tests/test-release-promotion.sh`), image builds on amd64/arm64,
   container-structure-test, and the Compose integration suite
   (`.github/workflows/ci.yml`). There is no separate unit-test framework.
6. **Spec Kit onboarding standard (runbook 1.0.0).** `specify` is pinned at
   1.4.5 (`6ba8beefff8d6408cadd62038e92d459093e33a8`) with the codex, opencode
   and omp integrations and the opt-in bug/assess extensions. The trusted
   checker (`.specify/onboarding/check.py`) and manifest
   (`.specify/onboarding/managed-files.json`) are captured from an independent
   clean generation, never from a candidate. All onboarding and case changes are
   staged through the exact-path staging gate; broad `git add -A` is prohibited.
   The bootstrap receipt (`.specify/bootstrap-receipt.json`) is committed and
   verified with `check.py verify` before any trace workflow runs. Case PRs are
   dispatched by the fixed checker `.specify/onboarding/check-case.py` with
   exact `allowed_paths` scope that fails closed. Pull requests stay open for
   human merge approval; nothing is merged, deployed or released by automation
   alone.
