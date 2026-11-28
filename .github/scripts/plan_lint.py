#!/usr/bin/env python3
"""Plan linter for the convergence protocol (PERS-398 design note, section 5).

Checks a plan artifact against the fixed template:

  * size cap: 15360 bytes by default, or a recorded-reason override
    ("Size override: <bytes> — reason: <text>" with <bytes> >= actual size)
  * required sections, header and protocol line
  * the declared sub-issue budget field and its arithmetic
  * no literal 64-hex digest in prose (max configurable; default 0)

Every failure names its cause and exits non-zero. Pin-site integrity and
currency are `pins.py check`'s job; the CI job runs both.

Exit codes: 0 clean, 1 findings, 2 tool error (missing plan, bad arguments).

Standard library only; no network.
"""

import argparse
import re
import sys
from pathlib import Path

DEFAULT_MAX_BYTES = 15 * 1024
DEFAULT_MAX_LITERAL_DIGESTS = 0

REQUIRED_SECTIONS = (
    "## Objective & scope",
    "## Inventory",
    "## Rules & constraints",
    "## Stage plan",
    "## Sub-issue budget",
    "## Pins (generated — do not edit by hand)",
    "## Evidence pointers",
    "## Revision log",
)

HEADER_RE = re.compile(r"^#\s+Rollout plan\b", re.MULTILINE)
PROTOCOL_RE = re.compile(r"^Protocol:.*convergence/1\b", re.MULTILINE)
HEX64_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
BUDGET_RE = re.compile(
    r"Declared:\s*(\d+)\s*(?:·|\||,|;)\s*"
    r"Consumed:\s*(\d+)\s*(?:·|\||,|;)\s*"
    r"Remaining:\s*(\d+)",
    re.IGNORECASE,
)
OVERRIDE_RE = re.compile(
    r"^Size override:\s*(\d+)\s*(?:—|–|-)\s*reason:\s*(\S.*)$",
    re.MULTILINE,
)


class ToolError(Exception):
    def __init__(self, cause, detail):
        super().__init__("%s: %s" % (cause, detail))
        self.cause = cause
        self.detail = detail


def normalize(text):
    for dash in ("\u2014", "\u2013", "\u2212"):
        text = text.replace(dash, "-")
    return re.sub(r"\s+", " ", text).strip().casefold()


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def section_bodies(text):
    """Map normalized '## heading' to (heading text, body, line)."""
    sections = {}
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    for index, match in enumerate(matches):
        start = match.end() + 1
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[normalize("## " + match.group(1))] = (
            match.group(1),
            text[start:end],
            line_of(text, match.start()),
        )
    return sections


def lint_plan(text, raw_bytes, max_bytes, max_literal_digests):
    findings = []
    sections = section_bodies(text)

    if not HEADER_RE.search(text):
        findings.append(
            ("missing-header", "expected '# Rollout plan — <rollout id> (r<n>)' as the first H1")
        )
    if not PROTOCOL_RE.search(text):
        findings.append(
            ("missing-protocol", "expected a 'Protocol: ... convergence/1 ...' line")
        )

    for required in REQUIRED_SECTIONS:
        if normalize(required) not in sections:
            findings.append(("missing-section", "missing section %r" % required))

    budget_entry = sections.get(normalize("## Sub-issue budget"))
    if budget_entry is None:
        findings.append(
            ("missing-budget", "no '## Sub-issue budget' section with Declared/Consumed/Remaining")
        )
    else:
        match = BUDGET_RE.search(budget_entry[1])
        if not match:
            findings.append(
                (
                    "missing-budget",
                    "section at line %d has no 'Declared: N · Consumed: M · Remaining: K' line"
                    % budget_entry[2],
                )
            )
        else:
            declared, consumed, remaining = (int(item) for item in match.groups())
            if remaining != declared - consumed:
                findings.append(
                    (
                        "budget-arithmetic",
                        "Declared %d - Consumed %d != Remaining %d"
                        % (declared, consumed, remaining),
                    )
                )

    actual_bytes = len(raw_bytes)
    if actual_bytes > max_bytes:
        override = OVERRIDE_RE.search(text)
        if override is None:
            findings.append(
                (
                    "size-cap-exceeded",
                    "plan is %d bytes, cap %d; record 'Size override: <bytes> — reason: <text>' "
                    "with <bytes> >= %d" % (actual_bytes, max_bytes, actual_bytes),
                )
            )
        else:
            limit = int(override.group(1))
            reason = override.group(2).strip()
            if limit < actual_bytes:
                findings.append(
                    (
                        "size-override-invalid",
                        "Size override limit %d is below the plan's %d bytes" % (limit, actual_bytes),
                    )
                )
            elif len(reason) < 5:
                findings.append(
                    ("size-override-invalid", "Size override reason is too short to be recorded")
                )

    digests = list(HEX64_RE.finditer(text))
    if len(digests) > max_literal_digests:
        for match in digests:
            findings.append(
                (
                    "literal-digest",
                    "line %d: 64-hex digest in plan text: %s"
                    % (line_of(text, match.start()), match.group(0)),
                )
            )

    return findings, sections, len(digests)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lint a convergence-protocol plan artifact (sections, size, budget, digests)."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument(
        "--max-literal-digests", type=int, default=DEFAULT_MAX_LITERAL_DIGESTS
    )
    args = parser.parse_args(argv)

    try:
        raw_bytes = args.plan.read_bytes()
    except OSError as exc:
        print(
            "FAIL plan-missing: %s: %s" % (args.plan, exc.strerror or exc),
            file=sys.stderr,
        )
        print("exit=2 (tool-error plan-missing)", file=sys.stderr)
        return 2

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        print("FAIL plan-invalid: %s is not UTF-8 (%s)" % (args.plan, exc), file=sys.stderr)
        print("exit=2 (tool-error plan-invalid)", file=sys.stderr)
        return 2

    findings, sections, digest_count = lint_plan(
        text, raw_bytes, args.max_bytes, args.max_literal_digests
    )

    if findings:
        for cause, detail in findings:
            print("FAIL %s: %s" % (cause, detail))
        print("exit=1 (findings: %d)" % len(findings))
        return 1

    budget_match = BUDGET_RE.search(sections[normalize("## Sub-issue budget")][1])
    declared, consumed = (int(item) for item in budget_match.groups()[:2])
    matched_sections = sum(1 for required in REQUIRED_SECTIONS if normalize(required) in sections)
    if consumed > declared:
        print(
            "WARN budget-exceeded: consumed %d > declared %d; requires a member approval "
            "recorded in the gate issue (G7)" % (consumed, declared)
        )
    size_note = "%d bytes <= %d" % (len(raw_bytes), args.max_bytes)
    if len(raw_bytes) > args.max_bytes:
        size_note = "%d bytes > %d cap, override %d" % (
            len(raw_bytes),
            args.max_bytes,
            int(OVERRIDE_RE.search(text).group(1)),
        )
    print(
        "OK plan structure: %s, %d/%d sections, %d literal digests, budget %d/%d"
        % (
            size_note,
            matched_sections,
            len(REQUIRED_SECTIONS),
            digest_count,
            consumed,
            declared,
        )
    )
    if len(raw_bytes) > args.max_bytes:
        print("OK size override recorded: %s" % OVERRIDE_RE.search(text).group(2).strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
