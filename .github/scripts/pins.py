#!/usr/bin/env python3
"""Plan pin tooling for the convergence protocol (schema plan-pins/1).

Implements section 4 of the phase-1 design note (PERS-398, comment
01a220da-b781-7a54-a41e-e17e7ca60b79) exactly:

  render  write every pin site in the plan from plan-pins.json
  check   fail closed on a stale site, an unrendered or raw marker, a 64-hex
          digest in prose, or a ledger-revision reference that does not match
  sweep   move pins in the ledger, re-render every site, print the diff and the
          resulting plan SHA-256 as one operation

Marker convention:
  <!-- pin:key -->rendered content<!-- /pin:key -->

  semver / url -> "key: <value>"
  sha256       -> "key: pinned at ledger r<n> (plan-pins.json)"

Hex values never enter the plan; a sha256 site names the ledger revision that
holds them. Pin keys are stable snake_case ids.

Exit codes:
  0  clean
  1  findings (`check` failure, or `sweep` refused because a finding would remain)
  2  tool error: invalid ledger or plan structure, IO failure, bad arguments

Standard library only; no network.
"""

import argparse
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "plan-pins/1"
KINDS = ("semver", "sha256", "url")

PIN_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
VALUE_RE = {
    "semver": re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)*$"),
    "sha256": re.compile(r"^[0-9a-f]{64}$"),
    "url": re.compile(r"^https?://\S+$"),
}

SITE_RE = re.compile(
    r"<!--\s*pin:(?P<open>[a-z][a-z0-9_]*)\s*-->"
    r"(?P<body>.*?)"
    r"<!--\s*/pin:(?P<close>[a-z][a-z0-9_]*)\s*-->",
    re.DOTALL,
)
OPEN_RE = re.compile(r"<!--\s*pin:[a-z][a-z0-9_]*\s*-->")
CLOSE_RE = re.compile(r"<!--\s*/pin:[a-z][a-z0-9_]*\s*-->")
HEX64_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
LEDGER_REF_RE = re.compile(r"ledger r(\d+)")


class ToolError(Exception):
    """A condition under which the tool cannot act (exit 2)."""

    def __init__(self, cause, detail):
        super().__init__("%s: %s" % (cause, detail))
        self.cause = cause
        self.detail = detail


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def mask_spans(text, spans):
    """Blank the given spans, keeping length and newlines so offsets stay valid."""
    chars = list(text)
    for start, end in spans:
        for index in range(start, end):
            if chars[index] != "\n":
                chars[index] = " "
    return "".join(chars)


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ToolError("file-missing", "%s: %s" % (path, exc.strerror or exc))


def load_ledger(path):
    raw = read_text(path)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolError("ledger-invalid", "%s: not valid JSON (%s)" % (path, exc))
    validate_ledger(data, path)
    return data, raw


def require(condition, detail):
    if not condition:
        raise ToolError("ledger-invalid", detail)


def validate_ledger(data, path):
    where = str(path)
    require(isinstance(data, dict), "%s: top level must be an object" % where)
    require(
        data.get("schema") == SCHEMA,
        "%s: schema must be %r, got %r" % (where, SCHEMA, data.get("schema")),
    )
    rollout = data.get("rollout")
    require(
        isinstance(rollout, str) and rollout.strip(),
        "%s: rollout must be a non-empty string" % where,
    )
    revision = data.get("ledger_revision")
    require(
        isinstance(revision, int) and not isinstance(revision, bool) and revision >= 1,
        "%s: ledger_revision must be an integer >= 1" % where,
    )
    budget = data.get("budget")
    require(isinstance(budget, dict), "%s: budget must be an object" % where)
    declared = budget.get("declared_max_sub_issues")
    consumed = budget.get("consumed")
    require(
        isinstance(declared, int) and not isinstance(declared, bool) and declared >= 1,
        "%s: budget.declared_max_sub_issues must be an integer >= 1" % where,
    )
    require(
        isinstance(consumed, int) and not isinstance(consumed, bool) and consumed >= 0,
        "%s: budget.consumed must be an integer >= 0" % where,
    )
    pins = data.get("pins")
    require(isinstance(pins, dict) and pins, "%s: pins must be a non-empty object" % where)
    for key, pin in pins.items():
        require(bool(PIN_KEY_RE.match(key)), "%s: pin key %r is not snake_case" % (where, key))
        require(isinstance(pin, dict), "%s: pin %r must be an object" % (where, key))
        kind = pin.get("kind")
        value = pin.get("value")
        require(
            kind in KINDS,
            "%s: pin %r kind must be one of %s" % (where, key, ", ".join(KINDS)),
        )
        require(
            isinstance(value, str) and bool(VALUE_RE[kind].match(value)),
            "%s: pin %r value %r does not match kind %r" % (where, key, value, kind),
        )


def expected_body(key, pin, ledger_revision):
    if pin["kind"] == "sha256":
        return "%s: pinned at ledger r%d (plan-pins.json)" % (key, ledger_revision)
    return "%s: %s" % (key, pin["value"])


def parse_sites(text):
    """Return (sites, prose, problems); prose is the plan with sites blanked."""
    sites = []
    spans = []
    problems = []
    for match in SITE_RE.finditer(text):
        spans.append(match.span())
        if match.group("open") != match.group("close"):
            problems.append(
                (
                    "pin-site-malformed",
                    "line %d: <!-- pin:%s --> closed by <!-- /pin:%s -->"
                    % (line_of(text, match.start()), match.group("open"), match.group("close")),
                )
            )
            continue
        sites.append(
            {
                "key": match.group("open"),
                "body": match.group("body"),
                "line": line_of(text, match.start()),
                "span": match.span(),
            }
        )
    prose = mask_spans(text, spans)
    raw = OPEN_RE.search(prose) or CLOSE_RE.search(prose)
    if raw:
        problems.append(
            (
                "pin-raw-marker",
                "line %d: unmatched marker %r"
                % (line_of(text, raw.start()), text[raw.start():raw.end()]),
            )
        )
    return sites, prose, problems


def check_plan(text, ledger):
    """Return (findings, missing_keys, site_count); findings are (cause, detail)."""
    sites, prose, problems = parse_sites(text)
    findings = list(problems)
    pins = ledger["pins"]
    revision = ledger["ledger_revision"]
    first_line = {}
    for site in sites:
        key = site["key"]
        if key not in pins:
            findings.append(
                (
                    "pin-site-unknown",
                    "line %d: site %r has no pin in plan-pins.json" % (site["line"], key),
                )
            )
            continue
        if key in first_line:
            findings.append(
                (
                    "pin-site-duplicate",
                    "line %d: second site for pin %r (first at line %d)"
                    % (site["line"], key, first_line[key]),
                )
            )
            continue
        first_line[key] = site["line"]
        body = site["body"].strip()
        if not body:
            findings.append(
                (
                    "pin-site-unrendered",
                    "line %d: site %r is empty" % (site["line"], key),
                )
            )
            continue
        expected = expected_body(key, pins[key], revision)
        if body == expected:
            continue
        if pins[key]["kind"] == "sha256":
            reference = re.match(
                r"^%s: pinned at ledger r(\d+) \(plan-pins\.json\)$" % re.escape(key),
                body,
            )
            if reference and int(reference.group(1)) != revision:
                findings.append(
                    (
                        "pin-ledger-revision-mismatch",
                        "line %d: site %r names ledger r%s, ledger is r%d"
                        % (site["line"], key, reference.group(1), revision),
                    )
                )
                continue
        findings.append(
            (
                "pin-stale",
                "line %d: site %r is %r, ledger renders %r"
                % (site["line"], key, body, expected),
            )
        )

    for match in LEDGER_REF_RE.finditer(prose):
        if int(match.group(1)) != revision:
            findings.append(
                (
                    "pin-ledger-revision-mismatch",
                    "line %d: reference names ledger r%s, ledger is r%d"
                    % (line_of(prose, match.start()), match.group(1), revision),
                )
            )

    for match in HEX64_RE.finditer(prose):
        findings.append(
            (
                "literal-digest",
                "line %d: 64-hex digest in prose: %s"
                % (line_of(prose, match.start()), match.group(0)),
            )
        )

    missing = [key for key in pins if key not in first_line]
    return findings, missing, len(sites)


def render_text(text, ledger):
    """Render every site; returns (new_text, changed_keys, site_count)."""
    sites, _prose, problems = parse_sites(text)
    if problems:
        raise ToolError(problems[0][0], problems[0][1])
    pins = ledger["pins"]
    revision = ledger["ledger_revision"]
    seen = set()
    for site in sites:
        key = site["key"]
        if key not in pins:
            raise ToolError(
                "pin-site-unknown",
                "line %d: site %r has no pin in plan-pins.json" % (site["line"], key),
            )
        if key in seen:
            raise ToolError(
                "pin-site-duplicate",
                "line %d: second site for pin %r" % (site["line"], key),
            )
        seen.add(key)

    chunks = []
    cursor = 0
    changed = []
    for site in sites:
        start, end = site["span"]
        expected = expected_body(site["key"], pins[site["key"]], revision)
        chunks.append(text[cursor:start])
        chunks.append("<!-- pin:%s -->%s<!-- /pin:%s -->" % (site["key"], expected, site["key"]))
        cursor = end
        if site["body"] != expected:
            changed.append(site["key"])
    chunks.append(text[cursor:])
    return "".join(chunks), changed, len(sites)


def plan_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def detect_indent(raw):
    match = re.search(r"\n( +)\S", raw)
    return len(match.group(1)) if match else 2


def dump_ledger(data, original_raw):
    return json.dumps(data, indent=detect_indent(original_raw), ensure_ascii=False) + "\n"


def write_text(path, text):
    try:
        path.write_text(text, encoding="utf-8", newline="")
    except OSError as exc:
        raise ToolError("write-failed", "%s: %s" % (path, exc.strerror or exc))


def report_findings(findings):
    for cause, detail in findings:
        print("FAIL %s: %s" % (cause, detail))
    print("exit=1 (findings: %d)" % len(findings))


def cmd_render(args):
    ledger, _raw = load_ledger(args.ledger)
    text = read_text(args.plan)
    rendered, changed, site_count = render_text(text, ledger)
    if changed:
        write_text(args.plan, rendered)
        for key in changed:
            print("rendered %s" % key)
    else:
        print("render: no changes")
    print("sites=%d changed=%d" % (site_count, len(changed)))
    print("plan_sha256=%s" % plan_digest(rendered))
    return 0


def cmd_check(args):
    ledger, _raw = load_ledger(args.ledger)
    text = read_text(args.plan)
    findings, missing, site_count = check_plan(text, ledger)
    if findings:
        report_findings(findings)
        return 1
    for key in missing:
        print("WARN pin-site-missing: ledger pin %r has no plan site (ledger-only)" % key)
    print(
        "OK plan pins match ledger r%d (%d sites, 0 findings)"
        % (ledger["ledger_revision"], site_count)
    )
    return 0


def parse_pin_arguments(values, ledger):
    updates = {}
    for item in values:
        if "=" not in item:
            raise ToolError("pin-invalid", "--pin %r is not KEY=VALUE" % item)
        key, value = item.split("=", 1)
        if key in updates:
            raise ToolError("pin-argument-duplicate", "--pin %r given more than once" % key)
        if key not in ledger["pins"]:
            raise ToolError(
                "pin-unknown",
                "--pin %r is not declared in plan-pins.json (declared: %s)"
                % (key, ", ".join(sorted(ledger["pins"]))),
            )
        kind = ledger["pins"][key]["kind"]
        if not VALUE_RE[kind].match(value):
            raise ToolError(
                "pin-invalid", "--pin %r value %r does not match kind %r" % (key, value, kind)
            )
        updates[key] = value
    if not updates:
        raise ToolError("pin-invalid", "sweep needs at least one --pin KEY=VALUE")
    return updates


def cmd_sweep(args):
    ledger, ledger_raw = load_ledger(args.ledger)
    plan_text = read_text(args.plan)
    updates = parse_pin_arguments(args.pin, ledger)
    old_revision = ledger["ledger_revision"]
    new_revision = args.ledger_revision if args.ledger_revision is not None else old_revision + 1
    if new_revision < 1:
        raise ToolError("pin-invalid", "--ledger-revision must be >= 1")

    new_ledger = json.loads(json.dumps(ledger))
    for key, value in updates.items():
        new_ledger["pins"][key]["value"] = value
    new_ledger["ledger_revision"] = new_revision

    new_plan, changed, site_count = render_text(plan_text, new_ledger)
    findings, _missing, _count = check_plan(new_plan, new_ledger)
    if findings:
        print("sweep refused: the rendered plan would still fail check")
        report_findings(findings)
        print("sweep_written=0")
        return 1

    new_ledger_text = dump_ledger(new_ledger, ledger_raw)
    digest = plan_digest(new_plan)

    print("--- plan-pins.json (ledger r%d)" % old_revision)
    sys.stdout.writelines(
        difflib.unified_diff(
            ledger_raw.splitlines(True),
            new_ledger_text.splitlines(True),
            fromfile="plan-pins.json@r%d" % old_revision,
            tofile="plan-pins.json@r%d" % new_revision,
        )
    )
    sys.stdout.writelines(
        difflib.unified_diff(
            plan_text.splitlines(True),
            new_plan.splitlines(True),
            fromfile="plan.md@r%d" % old_revision,
            tofile="plan.md@r%d" % new_revision,
        )
    )
    print("ledger_revision=%d" % new_revision)
    print("sites=%d changed=%d" % (site_count, len(changed)))
    print("plan_sha256=%s" % digest)

    if args.dry_run:
        print("sweep_written=0 (dry-run)")
        return 0

    write_text(args.ledger, new_ledger_text)
    if new_plan != plan_text:
        write_text(args.plan, new_plan)
    print("sweep_written=1")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Render, check and sweep plan pins (plan-pins.json schema v1)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="write every pin site from the ledger")
    render.add_argument("--plan", required=True, type=Path)
    render.add_argument("--ledger", required=True, type=Path)
    render.set_defaults(func=cmd_render)

    check = sub.add_parser("check", help="fail closed when a pin site, marker or prose digest is wrong")
    check.add_argument("--plan", required=True, type=Path)
    check.add_argument("--ledger", required=True, type=Path)
    check.set_defaults(func=cmd_check)

    sweep = sub.add_parser("sweep", help="move pins, re-render every site, print diff and plan digest")
    sweep.add_argument("--plan", required=True, type=Path)
    sweep.add_argument("--ledger", required=True, type=Path)
    sweep.add_argument("--pin", action="append", default=[], metavar="KEY=VALUE")
    sweep.add_argument(
        "--ledger-revision",
        type=int,
        default=None,
        help="ledger revision to write (default: current + 1)",
    )
    sweep.add_argument("--dry-run", action="store_true", help="print the result, write nothing")
    sweep.set_defaults(func=cmd_sweep)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ToolError as exc:
        print("FAIL %s: %s" % (exc.cause, exc.detail), file=sys.stderr)
        print("exit=2 (tool-error %s)" % exc.cause, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
