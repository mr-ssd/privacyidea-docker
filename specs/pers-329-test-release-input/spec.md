# Spec — `test-release-input` make target

- Case: `pers-329-test-release-input` (issue PERS-329), type: feature
- Base: `pilot/spec-kit-baseline` @ `7d859e08499cede49002f17830a9e89f113af760` on `mr-ssd/privacyidea-docker`
- Plan authority: V12 revision 3 on PERS-312, comment `01a21b87-f322-7d36-9e5b-811d4768046b`, §6 feature case
- Prompt: "Issue PERS-329, case pers-329-test-release-input. Add only a make target test-release-input that runs bash tests/test-release-input.sh and propagates success/failure. Set SPECIFY_FEATURE_DIRECTORY=specs/pers-329-test-release-input."

## Change

Add exactly one make target to `Makefile`:

```make
test-release-input:
	bash tests/test-release-input.sh
```

The target runs the existing regression script `tests/test-release-input.sh` (release-input accept/reject cases plus the `release.yml` wiring guard; no network, GitHub or Docker needed) and propagates its exit status: success iff the script succeeds.

## Clarifications

- The existing CI entry that runs this script is `.github/workflows/ci.yml:84` (`bash tests/test-release-input.sh`); the new target is a local/operator convenience wrapper around the same script — it must not duplicate or alter the script.
- No other `Makefile` behavior changes; `Makefile` is listed in `.gitignore` and is staged with `git add -f` through the exact-path gate.

## Acceptance criteria

- FEAT-1: the target `test-release-input` exists in `Makefile`.
- FEAT-2: the target invokes exactly `bash tests/test-release-input.sh` (`make -n test-release-input` prints exactly that line).
- FEAT-3: the target propagates success iff the script succeeds (a failing `bash` injected through `PATH` must fail `make test-release-input`).
