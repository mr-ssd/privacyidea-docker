# Plan — `test-release-input` make target (pers-329-test-release-input)

## Implementation

1. Edit `Makefile` only: insert the `test-release-input` target directly after the existing `test:` target, recipe tab-indented `bash tests/test-release-input.sh`.
2. Author the Spec Kit artifacts under `specs/pers-329-test-release-input/` (this spec, plan, tasks) and the run record under `.specify/features/pers-329-test-release-input/`.
3. Add the trace manifest `.specify/traceability/cases/pers-329-test-release-input.yml` with the exact `allowed_paths` set.
4. Stage every changed path through the exact-path gate (`stage-exact.sh`), commit, and verify commit scope (`check-commit-scope.sh`).
5. Open one PR from branch `pers-329-test-release-input` against `pilot/spec-kit-baseline`; leave it unmerged for human approval.

## Verification (local, pre-push)

- `make -n test-release-input` stdout is exactly `bash tests/test-release-input.sh` (FEAT-2).
- `make test-release-input` exits 0 (FEAT-3 positive; the script passes on this base — measured rc=0 at base `f3c01c28`).
- Failure injection: `PATH=<failbin>:$PATH make test-release-input` with a stub `bash` exiting 37 for `tests/test-release-input.sh` fails nonzero (FEAT-3 negative).
- `check-case.py --id FEAT-1|FEAT-2|FEAT-3 --base <baseline> --head HEAD --manifest <manifest>` all PASS.

## CI

- Existing `ci.yml` is untouched and still runs `bash tests/test-release-input.sh` at line 84.
- The additive `spec-kit-trace.yml` runs the fixed dispatcher over FEAT-1..3 in case mode and uploads evidence.
