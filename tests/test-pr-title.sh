#!/usr/bin/env bash
#
# Regression tests for .github/scripts/check-pr-title.sh
#
# The PR-title rule is the gate on agent PRs, so its grammar, its failure
# messages and the difference between grammar-only mode (CI backstop) and
# exact-key mode (creation step) are tested as behaviour: every case asserts
# the exact exit code, the exact stderr text and the exact stdout the design
# note (PERS-192 §3-§6) specifies.
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
script="${repo_root}/.github/scripts/check-pr-title.sh"
[[ -x "$script" ]] || { echo "missing or non-executable: ${script}" >&2; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

passed=0
failed=0

report_failure() {
  local label="$1" detail="$2"
  failed=$((failed + 1))
  echo "FAIL: ${label}" >&2
  echo "      ${detail}" >&2
  echo "----- stdout -----" >&2
  cat "$tmp/stdout" >&2
  echo "----- stderr -----" >&2
  cat "$tmp/stderr" >&2
  echo "------------------" >&2
}

# assert_case <label> <expected-exit> <expected-stderr> <expected-stdout> [ARGS...]
#
# stderr and stdout are compared exactly, not by substring: the design note
# fixes the message text, so a reworded message is a regression.
assert_case() {
  local label="$1" expected_exit="$2" expected_stderr="$3" expected_stdout="$4"
  shift 4

  local status=0
  bash "$script" "$@" >"$tmp/stdout" 2>"$tmp/stderr" || status=$?

  if [[ "$status" -ne "$expected_exit" ]]; then
    report_failure "$label" "expected exit ${expected_exit}, got ${status}"
    return
  fi

  local actual_stderr actual_stdout
  actual_stderr="$(cat "$tmp/stderr")"
  actual_stdout="$(cat "$tmp/stdout")"

  if [[ "$actual_stderr" != "$expected_stderr" ]]; then
    report_failure "$label" "stderr mismatch; expected: ${expected_stderr}"
    return
  fi

  if [[ "$actual_stdout" != "$expected_stdout" ]]; then
    report_failure "$label" "stdout mismatch; expected: ${expected_stdout}"
    return
  fi

  passed=$((passed + 1))
  echo "ok: ${label}"
}

malformed_msg="malformed issue key or title: expected '^[A-Z]+-[0-9]+: \\S.*$'"
usage="$(
  echo 'expected exactly one TITLE argument'
  echo 'usage: check-pr-title.sh [--key KEY] TITLE'
)"

# --- 1. valid --------------------------------------------------------------

assert_case "key-prefixed conventional commit is valid" 0 "" \
  "pr title ok: PERS-123: fix(bootstrap): eliminate warnings" \
  --key PERS-123 "PERS-123: fix(bootstrap): eliminate warnings"

assert_case "plain key-prefixed description is valid" 0 "" \
  "pr title ok: PERS-123: description" \
  --key PERS-123 "PERS-123: description"

assert_case "--key=VALUE form is accepted" 0 "" \
  "pr title ok: PERS-123: description" \
  --key=PERS-123 "PERS-123: description"

assert_case "grammar-only mode accepts a key-prefixed title" 0 "" \
  "pr title ok: PERS-190: docs: add project profile" \
  "PERS-190: docs: add project profile"

assert_case "grammar-only mode accepts any well-formed key (no current key known)" 0 "" \
  "pr title ok: PERS-999: description" \
  "PERS-999: description"

# --- 2. missing ------------------------------------------------------------

assert_case "leading conventional commit without a key is rejected" 1 \
  "missing issue key: title must start with 'PERS-123: '" "" \
  --key PERS-123 "fix(bootstrap): eliminate warnings"

assert_case "grammar-only mode rejects the same keyless title" 1 \
  "missing issue key: title must start with '<KEY>: '" "" \
  "fix(bootstrap): eliminate warnings"

assert_case "trailing key is rejected (key must be at position 0)" 1 \
  "missing issue key: title must start with 'PERS-123: '" "" \
  --key PERS-123 "docs: add project profile (PERS-190)"

assert_case "grammar-only mode rejects a trailing key" 1 \
  "missing issue key: title must start with '<KEY>: '" "" \
  "docs: add project profile (PERS-190)"

# --- 3. malformed ----------------------------------------------------------

assert_case "non-numeric key suffix is rejected" 1 \
  "${malformed_msg}" "" \
  --key PERS-123 "PERS-12A: bad key"

assert_case "key without a hyphen is rejected" 1 \
  "${malformed_msg}" "" \
  --key PERS-123 "PERS123: no hyphen"

assert_case "separator without the space is rejected" 1 \
  "${malformed_msg}" "" \
  --key PERS-123 "PERS-123:description"

assert_case "empty description is rejected" 1 \
  "${malformed_msg}" "" \
  --key PERS-123 "PERS-123: "

# --- 4. case-sensitive -----------------------------------------------------

assert_case "lowercase key prefix is rejected" 1 \
  "${malformed_msg}" "" \
  --key PERS-123 "pers-123: lowercase prefix"

assert_case "lowercase key prefix is rejected in grammar-only mode" 1 \
  "${malformed_msg}" "" \
  "pers-123: lowercase prefix"

# --- exact-key enforcement (supporting case) ------------------------------

assert_case "well-formed key for another issue is a mismatch" 1 \
  "issue key mismatch: title has 'PERS-192', current issue is 'PERS-191'" "" \
  --key PERS-191 "PERS-192: something"

assert_case "prefix comparison is exact, not a string prefix of the key" 1 \
  "issue key mismatch: title has 'PERS-12', current issue is 'PERS-123'" "" \
  --key PERS-123 "PERS-12: description"

# --- fail closed on an unavailable key / usage errors ----------------------

assert_case "an empty --key fails closed instead of checking grammar only" 1 \
  "issue key unavailable; pass --key <PREFIX>-<n> explicitly" "" \
  --key "" "PERS-123: description"

assert_case "no arguments is a usage error" 2 \
  "${usage}" ""

assert_case "two positional titles is a usage error" 2 \
  "${usage}" "" \
  --key PERS-123 "PERS-123: description" "PERS-123: duplicate"

echo
if [[ "$failed" -gt 0 ]]; then
  echo "${failed} case(s) failed, ${passed} passed" >&2
  exit 1
fi

# Wiring guards: the rule is only enforced if the job, the script invocation
# and the documented usage stay in step. Renaming one side alone would turn a
# blocking gate back into a suggestion.
workflow="${repo_root}/.github/workflows/ci.yml"
agents_md="${repo_root}/AGENTS.md"
wiring_failed=0

check_file() {
  local file="$1" needle
  while IFS= read -r needle; do
    [[ -n "$needle" ]] || continue
    if ! grep -Fq -- "$needle" "$file"; then
      echo "FAIL: ${file#"${repo_root}"/} is missing: ${needle}" >&2
      wiring_failed=1
    fi
  done
}

check_file "$workflow" <<'EOF'
if: startsWith(github.event.pull_request.head.ref, 'agent/')
TITLE: ${{ github.event.pull_request.title }}
bash .github/scripts/check-pr-title.sh "$TITLE"
run: bash tests/test-pr-title.sh
EOF

check_file "$agents_md" <<'EOF'
Agent PR titles must be `<ISSUE-KEY>: <title>`
check-pr-title.sh --key "$ISSUE_KEY" "$TITLE"
EOF

if [[ "$wiring_failed" -ne 0 ]]; then
  echo "wiring check failed, ${passed} case(s) passed" >&2
  exit 1
fi

echo "all ${passed} PR title cases passed"
