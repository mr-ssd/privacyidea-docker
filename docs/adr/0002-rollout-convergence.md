# ADR 0002 — Rollout convergence: pins, freeze, round cap and budget

- Status: accepted (protocol approved on PERS-398, 2026-11-28T06:33Z; tooling enforcement lands in PERS-399)
- Issue: PERS-399 (phase 2 of PERS-397); design note: PERS-398 comment `01a220da-b781-7a54-a41e-e17e7ca60b79`
- Scope: process decisions plus the tooling that enforces them in this repository. Nothing here changes the deployed trace gate, the runbook, or any agent configuration.

## Context

The PERS-311 rollout cost 77 sub-issues and about 30 hours against a 150 KB plan:
19 plan folds, 11 re-gates and 15 revisions. The structural cause was that the
plan embedded the runbook version and tarball digest in five operative sites, so
every promotion changed the plan's bytes and forced a fold plus an independent
full-plan gate. Reviews were open-ended (each gate returned one or two new
findings with no round cap), duplicated literals went stale (revision 13 still
named 1.0.4 after 1.0.6 landed), and the rollout never declared how many
sub-issues it was allowed to spend.

Phase 1 (PERS-398) fixed the process as decisions D1–D7 and a rule set R1–R8,
with `plan-pins.json` schema v1, a 15 KB plan template and gate checklist
G1–G8. This ADR records those decisions where the enforcement lives, and fixes
the few implementation details phase 1 left open (override syntax, exit codes,
named causes, artifact layout). Where this ADR and the design note disagree, the
design note wins for the protocol; this ADR owns the implementation contract.

## Decision

- **D1 Plan as index.** Each pin appears in exactly one machine-rendered site;
  prose carries no pin literals. Promotion touches rendered sites only.
  *Reversible:* `pins.py render` regenerates sites; prose is untouched.
- **D2 Single pin ledger.** All pin values live in `plan-pins.json` (schema
  `plan-pins/1`). Scripts read values from the ledger at execution time; the
  plan never re-quotes them. *Reversible:* values migrate in either direction
  with one command.
- **D3 Freeze-before-gate.** Entering review records the artifact revision id
  and SHA-256 in the gate issue; the reviewer approves that exact digest. Edits
  during a round queue for the next revision. *Reversible:* policy only.
- **D4 Diff-scoped re-gate.** A re-gate receives the changed hunks
  r(n−1)→r(n), the G1–G8 checklist and `pins.py check` output, not the full
  document. Full read only at a rollout's first gate or where a checklist item
  names full-read evidence. *Reversible:* policy; staleness risk is covered
  mechanically by `check` and G2/G3.
- **D5 Round cap.** At most two review rounds per artifact per gate; every
  finding returns in one pass. Findings after round 2 become a follow-up
  ticket, never a new fold/gate stage. *Irreversible in effect:* a closed
  round-2 review cannot be reopened; a deferred finding re-enters only as a
  follow-up ticket. The policy itself is reversible.
- **D6 Declared sub-issue budget.** The plan declares its budget (default
  ≤20) before work; folds, re-gates and pin moves consume it; crossing it
  pauses the rollout for member approval. *Irreversible in effect* once an
  approval is recorded; reversible as policy.
- **D7 Scripted pin moves.** A promotion is one issue running
  `pins.py sweep` (ledger + re-render + printed diff + resulting plan digest)
  plus one hunk-scoped gate round — never a manual fold plus full re-gate.
  *Reversible:* revert the sweep commit. Until this tooling existed, the manual
  PERS-394 sweep was the fallback and counted as the same one-issue move.

## Implementation contract

Layout, all standard library, no network:

| Path | Purpose |
|---|---|
| `.github/scripts/pins.py` | `render`, `check`, `sweep` over `plan-pins.json` |
| `.github/scripts/plan_lint.py` | plan structure, size cap, budget field, literal digests |
| `.github/workflows/spec-kit-plan-lint.yml` | additive CI job; G1–G3 evidence on plan-artifact PRs |
| `tests/test-plan-tooling.py` | self-contained controls, including the four required fixtures |
| `tests/fixtures/plan-tooling/` | clean, stale-pin, oversize, duplicate-literal plans |

A plan artifact is a directory holding `plan.md` next to `plan-pins.json`.
Fixture directories under `tests/fixtures/` are excluded from the CI job's
discovery, because their broken plans are intentional.

**Markers and rendering (D1, D2).** A site is
`<!-- pin:<key> -->…<!-- /pin:<key> -->`. `render` fills it with
`<key>: <value>` for `semver`/`url` pins and with
`<key>: pinned at ledger r<n> (plan-pins.json)` for `sha256` pins. Hex values
never enter the plan; a sha256 site points at the ledger revision that holds
them. Every `ledger r<n>` reference in a plan must name the current ledger
revision. A ledger pin with no site is allowed (ledger-only, e.g. a digest used
only by scripts) and reported as `pin-site-missing` warning.

**`check` causes (G2, G3), exit 1:** `pin-stale`, `pin-site-unrendered`,
`pin-site-unknown`, `pin-site-duplicate`, `pin-site-malformed`,
`pin-raw-marker`, `pin-ledger-revision-mismatch`, `literal-digest`. Exit 2 means
the tool could not act: `ledger-invalid`, `ledger-missing`, `file-missing`,
`pin-unknown`, `pin-invalid`, `write-failed`.

**`sweep` (D7).** `sweep --pin key=value …` validates every value against the
pin's kind, bumps `ledger_revision` (or takes `--ledger-revision N`), re-renders
every site, prints the ledger and plan diffs plus the new plan SHA-256, and only
then writes. If the rendered plan would still fail `check` for a reason
unrelated to the move (a prose digest, a duplicate site), it writes nothing and
exits 1. `--dry-run` prints without writing.

**Linter (R1, R6), exit 1:** `missing-header`, `missing-protocol`,
`missing-section`, `missing-budget`, `budget-arithmetic`, `size-cap-exceeded`,
`size-override-invalid`, `literal-digest`; plus a non-failing warning when
`Consumed > Declared` (the approval itself is G7's human evidence).

**Size cap and override (R1).** The default cap is 15360 bytes
(`--max-bytes`). A larger plan must carry one line in its header block:

```
Size override: <bytes> — reason: <recorded reason>
```

`<bytes>` is the acknowledged limit and must be at least the actual plan size;
the reason must be non-empty. This is the "recorded reason, never a new round"
escape hatch from PERS-397.

**Required sections (R1):** `## Objective & scope`, `## Inventory`,
`## Rules & constraints`, `## Stage plan`, `## Sub-issue budget`,
`## Pins (generated — do not edit by hand)`, `## Evidence pointers`,
`## Revision log`; plus the H1 `# Rollout plan — <id> (r<n>)` and the
`Protocol: … convergence/1` line. The budget section carries
`Declared: N · Consumed: M · Remaining: K` with `K = N − M`.

## Consequences

- A promotion is mechanical: one `sweep`, one hunk-scoped round. The plan's
  prose does not change, so its size stays flat across promotions.
- CI produces G1–G3 evidence (linter and `check` exit codes, byte count,
  literal-digest scan, ledger diff); G4–G8 stay human evidence in the gate
  issue, because they depend on the review record and on the deployed baseline.
- The trace gate and runbook 1.0.6 are untouched: no file in this change writes
  to `.github/workflows/spec-kit-trace.yml` or `docs/release-runbook.md`, and
  the PR records their SHA-256 before and after.
- Known limit: a runbook version literal in prose is not detectable without
  false positives (plans legitimately mention other versions), so R1's
  "no pin literals in prose" stays a review check (G2/G3); `check` enforces the
  mechanical part — 64-hex digests and rendered sites. The same applies to the
  budget approval, which the linter can only warn about.

## Rollback

- Per-decision: D1/D2 via `pins.py render`; D3/D4/D6 as policy; D7 by reverting
  the sweep commit.
- Protocol itself: mark this ADR superseded; delete or disable the additive
  `spec-kit-plan-lint` workflow (config revert, no state to unwind); render
  literal values back with `pins.py render` if a plan must return to literal
  form; future rollouts simply do not declare the protocol.
- No step touches the trace gate, the runbook, repository variables or the
  agent cohort.

## Irreversible decisions

D5 and D6 as stated: a spent review round and a recorded budget approval cannot
be reclaimed; both are reversible only prospectively and only as policy.
