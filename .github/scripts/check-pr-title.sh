#!/usr/bin/env bash
#
# Validate an agent pull request title against the issue-key rule.
#
# Usage: check-pr-title.sh [--key KEY] TITLE
#
# Grammar (PERS-192 §3): ^[A-Z]+-[0-9]+: \S.*$
#   The key is anchored at position 0, is case-sensitive (uppercase prefix,
#   one hyphen, digits), and is followed by exactly one space and a non-empty
#   description. A conventional-commit prefix, when used, belongs to the
#   description: "PERS-123: fix(bootstrap): description" is valid.
#
# --key KEY adds the exact-key check the creation step needs: the title must
# start with "KEY: " verbatim, so the key is the current issue's identifier and
# not merely a well-formed key. Without --key only the grammar is checked,
# which is all the CI backstop can do: an agent branch (agent/<role>/<id>)
# carries no issue key, so CI cannot know which key is current.
#
# Failure behaviour (PERS-192 §4) is one rule: block, never auto-correct.
#   missing key            exit 1  missing issue key: title must start with '<KEY>: '
#   malformed key or title exit 1  malformed issue key or title: expected '^[A-Z]+-[0-9]+: \S.*$'
#   key mismatch           exit 1  issue key mismatch: title has '<T>', current issue is '<K>'
# A usage error (no TITLE, unknown option, extra argument) exits 2.
set -euo pipefail

usage='usage: check-pr-title.sh [--key KEY] TITLE'

# Detail first, then the usage line: the detail is the actionable half.
usage_error() {
  printf '%s\n%s\n' "${1:-invalid arguments}" "$usage" >&2
  exit 2
}

key=''
have_key=0

while (( $# > 0 )); do
  case "$1" in
    --key)
      (( $# >= 2 )) || usage_error "--key requires a value"
      key="$2"
      have_key=1
      shift 2
      ;;
    --key=*)
      key="${1#--key=}"
      have_key=1
      shift
      ;;
    -h | --help)
      printf '%s\n' "$usage"
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      usage_error "unknown option: $1"
      ;;
    *)
      break
      ;;
  esac
done

(( $# == 1 )) || usage_error "expected exactly one TITLE argument"
title="$1"

# An explicitly empty key is the "key cannot be determined at PR time" path:
# fail closed instead of validating the grammar only (PERS-192 §2).
if (( have_key )) && [[ -z "$key" ]]; then
  echo "issue key unavailable; pass --key <PREFIX>-<n> explicitly" >&2
  exit 1
fi

# POSIX ERE only: bash has no \S, so the description's first character is
# [^[:space:]].
title_re='^[A-Z]+-[0-9]+: [^[:space:]].*$'

# The text before the separator tells "no key at all" apart from "a key was
# attempted but is malformed", which the design note reports with distinct
# messages.
head=${title%%:*}
head=${head%"${head##*[![:space:]]}"}

if [[ ! "$title" =~ $title_re ]]; then
  # A leading single token that carries a hyphen or a digit is an attempted
  # key ("PERS-12A", "pers-123", "PERS123"); anything else ("fix(bootstrap):",
  # "docs: add ... (PERS-190)") is a title with no key at position 0.
  if [[ "$head" =~ ^[A-Za-z][A-Za-z0-9]*(-[A-Za-z0-9]+)?$ ]] &&
    [[ "$head" == *-* || "$head" == *[0-9]* ]]; then
    echo "malformed issue key or title: expected '^[A-Z]+-[0-9]+: \S.*\$'" >&2
  elif (( have_key )); then
    echo "missing issue key: title must start with '${key}: '" >&2
  else
    echo "missing issue key: title must start with '<KEY>: '" >&2
  fi
  exit 1
fi

# Grammar passed: the title starts with a well-formed key. Exact-key mode
# additionally requires that key to be the current issue's, compared as a
# case-sensitive prefix.
if (( have_key )) && [[ "$title" != "${key}: "* ]]; then
  echo "issue key mismatch: title has '${title%%:*}', current issue is '${key}'" >&2
  exit 1
fi

printf 'pr title ok: %s\n' "$title"
