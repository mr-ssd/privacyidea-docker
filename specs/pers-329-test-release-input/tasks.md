# Tasks — pers-329-test-release-input (dependency-ordered)

1. Add `test-release-input` target to `Makefile` (recipe: `bash tests/test-release-input.sh`).
2. Author `specs/pers-329-test-release-input/{spec,plan,tasks}.md`.
3. Record analyze/converge result in `.specify/features/pers-329-test-release-input/checklist.md`.
4. Write trace manifest `.specify/traceability/cases/pers-329-test-release-input.yml`.
5. Stage via exact-path gate; commit; check commit scope.
6. Run local FEAT-1..3 checks with `check-case.py` plus make dry-run/run/failure-injection evidence.
7. Push branch `pers-329-test-release-input`; open PR against `pilot/spec-kit-baseline` (unmerged).
8. CI: `spec-kit-trace.yml` case-mode run on the PR produces `checks.jsonl` with FEAT-1..3 PASS and uploads the evidence artifact.
