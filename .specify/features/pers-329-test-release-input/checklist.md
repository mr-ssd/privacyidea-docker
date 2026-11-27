# Analyze / Converge — pers-329-test-release-input

## Analyze (artifact consistency)

- spec.md, plan.md, tasks.md agree: the change is exactly one Makefile target; no other file is touched by the implementation step.
- Acceptance IDs in spec.md (FEAT-1..3) match the trace manifest `acceptance_ids`/`approved_check_ids` exactly.
- `allowed_paths` in the manifest equals the dispatcher-derived set: `Makefile`, `specs/pers-329-test-release-input/`, `.specify/features/pers-329-test-release-input/`, `.specify/traceability/cases/pers-329-test-release-input.yml`.
- `feature_directory` = `specs/pers-329-test-release-input` (derived from the case key; `.specify/feature.json` is per-checkout run state, excluded from Git).

## Converge (against original criteria)

- FEAT-1 target exists — `check-case.py --id FEAT-1`.
- FEAT-2 exact script invoked — `make -n` output diffed against expected `bash tests/test-release-input.sh`; `check-case.py --id FEAT-2`.
- FEAT-3 propagation — real run rc=0; PATH failure injection rc!=0; `check-case.py --id FEAT-3`.
- PR diff confined to `allowed_paths` — enforced by the fixed dispatcher before any acceptance result (fails closed).
