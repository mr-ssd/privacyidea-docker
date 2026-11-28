#!/usr/bin/env python3
"""Positive and negative controls for the plan pin tooling.

Covers .github/scripts/pins.py (render/check/sweep) and
.github/scripts/plan_lint.py against the fixtures in
tests/fixtures/plan-tooling. Every case prints its command, the tool output and
the exit code the tool returned, so a failure always has evidence beside it.
Standard library only; no network.

Run from anywhere: python3 tests/test-plan-tooling.py
Exit code: 0 when every control behaves as expected, 1 otherwise.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / ".github" / "scripts" / "pins.py"
LINT = ROOT / ".github" / "scripts" / "plan_lint.py"
FIXTURES = ROOT / "tests" / "fixtures" / "plan-tooling"

NEW_DIGEST = "0123456789abcdef" * 4
TMP_ROOT = Path(tempfile.mkdtemp(prefix="plan-tooling-tests."))


class CaseFailure(Exception):
    pass


def run(args):
    completed = subprocess.run(
        [sys.executable] + [str(item) for item in args],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.returncode, completed.stdout


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fresh(fixture):
    target = Path(tempfile.mkdtemp(prefix="%s." % fixture, dir=str(TMP_ROOT)))
    shutil.copytree(str(FIXTURES / fixture), str(target), dirs_exist_ok=True)
    return target


def require(condition, message):
    if not condition:
        raise CaseFailure(message)


CASES = []


def case(name, args, expect_rc, cause=None, after=None):
    CASES.append((name, [str(item) for item in args], expect_rc, cause, after))


def main():
    clean_plan = FIXTURES / "clean" / "plan.md"
    clean_ledger = FIXTURES / "clean" / "plan-pins.json"
    stale_plan = FIXTURES / "stale-pin" / "plan.md"
    stale_ledger = FIXTURES / "stale-pin" / "plan-pins.json"
    oversize_plan = FIXTURES / "oversize" / "plan.md"
    oversize_ledger = FIXTURES / "oversize" / "plan-pins.json"
    duplicate_plan = FIXTURES / "duplicate-literal" / "plan.md"
    duplicate_ledger = FIXTURES / "duplicate-literal" / "plan-pins.json"

    # -- clean controls -----------------------------------------------------
    case("clean-lint", [LINT, "--plan", clean_plan], 0)
    case("clean-check", [PINS, "check", "--plan", clean_plan, "--ledger", clean_ledger], 0)

    idem = fresh("clean")
    before = sha256_of(idem / "plan.md")

    def idempotent(_out):
        require(sha256_of(idem / "plan.md") == before, "render rewrote an already-rendered plan")

    case(
        "clean-render-idempotent",
        [PINS, "render", "--plan", idem / "plan.md", "--ledger", idem / "plan-pins.json"],
        0,
        "no changes",
        idempotent,
    )

    # -- negative controls: stale pin, oversize plan, literal digest --------
    case("stale-pin-check", [PINS, "check", "--plan", stale_plan, "--ledger", stale_ledger], 1, "pin-stale")
    case("stale-pin-lint", [LINT, "--plan", stale_plan], 0)
    case("oversize-plan-lint", [LINT, "--plan", oversize_plan], 1, "size-cap-exceeded")
    case(
        "duplicate-literal-lint",
        [LINT, "--plan", duplicate_plan],
        1,
        "literal-digest",
    )
    case(
        "duplicate-literal-check",
        [PINS, "check", "--plan", duplicate_plan, "--ledger", duplicate_ledger],
        1,
        "literal-digest",
    )

    # -- recorded-reason override for the size cap --------------------------
    recorded = fresh("oversize")
    plan_text = (recorded / "plan.md").read_text()
    limit = len(plan_text.encode()) + 1024
    plan_text = plan_text.replace(
        "Protocol: convergence/1 · Parent: PERS-DEMO · Lead: Build\n",
        "Protocol: convergence/1 · Parent: PERS-DEMO · Lead: Build\n"
        "Size override: %d — reason: fixture keeps a padded inventory to prove "
        "the recorded-reason path\n" % limit,
        1,
    )
    (recorded / "plan.md").write_text(plan_text)
    case(
        "oversize-plan-recorded-override-lint",
        [LINT, "--plan", recorded / "plan.md"],
        0,
        "size override recorded",
    )

    short_override = fresh("oversize")
    plan_text = (short_override / "plan.md").read_text().replace(
        "Protocol: convergence/1 · Parent: PERS-DEMO · Lead: Build\n",
        "Protocol: convergence/1 · Parent: PERS-DEMO · Lead: Build\n"
        "Size override: %d — reason: limit set below the actual size on purpose\n"
        % (len((short_override / "plan.md").read_text().encode()) - 4096),
        1,
    )
    (short_override / "plan.md").write_text(plan_text)
    case(
        "oversize-plan-override-below-size-lint",
        [LINT, "--plan", short_override / "plan.md"],
        1,
        "size-override-invalid",
    )

    # -- sweep: one operation moves every site, then check and lint pass ----
    swept = fresh("stale-pin")

    def sweep_moved_all(out):
        plan = (swept / "plan.md").read_text()
        ledger = json.loads((swept / "plan-pins.json").read_text())
        require("runbook_version: 1.0.7" in plan, "semver site did not move to 1.0.7")
        require(
            "archive_sha256: pinned at ledger r7 (plan-pins.json)" in plan,
            "sha256 site did not move to ledger r7",
        )
        require(NEW_DIGEST not in plan, "hex digest leaked into the plan")
        require(ledger["ledger_revision"] == 7, "ledger revision did not move to 7")
        require(
            ledger["pins"]["archive_sha256"]["value"] == NEW_DIGEST,
            "ledger archive_sha256 was not updated",
        )
        printed = re.search(r"plan_sha256=([0-9a-f]{64})", out)
        require(printed is not None, "sweep did not print a plan SHA-256")
        require(
            printed.group(1) == sha256_of(swept / "plan.md"),
            "printed plan SHA-256 does not match the written plan",
        )

    case(
        "sweep-moves-every-site",
        [
            PINS,
            "sweep",
            "--plan",
            swept / "plan.md",
            "--ledger",
            swept / "plan-pins.json",
            "--pin",
            "runbook_version=1.0.7",
            "--pin",
            "archive_sha256=%s" % NEW_DIGEST,
        ],
        0,
        "sweep_written=1",
        sweep_moved_all,
    )
    case("sweep-result-check", [PINS, "check", "--plan", swept / "plan.md", "--ledger", swept / "plan-pins.json"], 0)
    case("sweep-result-lint", [LINT, "--plan", swept / "plan.md"], 0)

    # A deliberately missed site: the ledger moves on but one site stays empty.
    missed = fresh("clean")
    missed_plan = missed / "plan.md"
    missed_plan.write_text(
        missed_plan.read_text().replace(
            "<!-- pin:runbook_version -->runbook_version: 1.0.6<!-- /pin:runbook_version -->",
            "<!-- pin:runbook_version --><!-- /pin:runbook_version -->",
            1,
        )
    )
    case(
        "missed-site-check",
        [PINS, "check", "--plan", missed_plan, "--ledger", missed / "plan-pins.json"],
        1,
        "pin-site-unrendered",
    )

    drifted = fresh("clean")
    ledger = json.loads((drifted / "plan-pins.json").read_text())
    ledger["ledger_revision"] = 7
    (drifted / "plan-pins.json").write_text(json.dumps(ledger, indent=2) + "\n")
    case(
        "ledger-bumped-without-render-check",
        [PINS, "check", "--plan", drifted / "plan.md", "--ledger", drifted / "plan-pins.json"],
        1,
        "pin-ledger-revision-mismatch",
    )

    # -- fail-closed tool behaviour: nothing is written on a bad request ----
    refused = fresh("duplicate-literal")
    before_ledger = (refused / "plan-pins.json").read_text()
    before_plan = (refused / "plan.md").read_text()

    def refused_unchanged(_out):
        require(
            (refused / "plan-pins.json").read_text() == before_ledger
            and (refused / "plan.md").read_text() == before_plan,
            "refused sweep still wrote a file",
        )

    case(
        "sweep-refuses-preexisting-literal",
        [
            PINS,
            "sweep",
            "--plan",
            refused / "plan.md",
            "--ledger",
            refused / "plan-pins.json",
            "--pin",
            "runbook_version=1.0.7",
        ],
        1,
        "literal-digest",
        refused_unchanged,
    )

    # A sweep re-renders every site, not only the pins named on the command
    # line, so a hand-edited site elsewhere cannot survive a pin move.
    repaired = fresh("clean")
    repaired_plan = repaired / "plan.md"
    repaired_plan.write_text(
        repaired_plan.read_text().replace(
            "gist_url: https://gist.github.com/example/runbook-evidence",
            "gist_url: https://gist.github.com/example/runbook-evidence-old",
            1,
        )
    )

    def other_site_repaired(_out):
        text = repaired_plan.read_text()
        require(
            "gist_url: https://gist.github.com/example/runbook-evidence" in text,
            "sweep did not re-render the gist_url site",
        )
        require("runbook-evidence-old" not in text, "sweep left the stale gist_url value")

    case(
        "sweep-renders-every-site",
        [
            PINS,
            "sweep",
            "--plan",
            repaired_plan,
            "--ledger",
            repaired / "plan-pins.json",
            "--pin",
            "runbook_version=1.0.7",
        ],
        0,
        "sweep_written=1",
        other_site_repaired,
    )

    unknown = fresh("clean")
    unknown_ledger = (unknown / "plan-pins.json").read_text()

    def unknown_unchanged(_out):
        require(
            (unknown / "plan-pins.json").read_text() == unknown_ledger,
            "unknown-pin sweep wrote the ledger",
        )

    case(
        "sweep-unknown-pin",
        [
            PINS,
            "sweep",
            "--plan",
            unknown / "plan.md",
            "--ledger",
            unknown / "plan-pins.json",
            "--pin",
            "not_a_pin=1",
        ],
        2,
        "pin-unknown",
        unknown_unchanged,
    )

    invalid = fresh("clean")
    ledger = json.loads((invalid / "plan-pins.json").read_text())
    ledger["schema"] = "plan-pins/2"
    (invalid / "plan-pins.json").write_text(json.dumps(ledger, indent=2) + "\n")
    case(
        "bad-schema-check",
        [PINS, "check", "--plan", invalid / "plan.md", "--ledger", invalid / "plan-pins.json"],
        2,
        "ledger-invalid",
    )

    duplicate_site = fresh("clean")
    duplicate_site_plan = duplicate_site / "plan.md"
    duplicate_site_plan.write_text(
        duplicate_site_plan.read_text().rstrip("\n")
        + "\n<!-- pin:runbook_version -->runbook_version: 1.0.6<!-- /pin:runbook_version -->\n"
    )
    case(
        "duplicate-site-check",
        [
            PINS,
            "check",
            "--plan",
            duplicate_site_plan,
            "--ledger",
            duplicate_site / "plan-pins.json",
        ],
        1,
        "pin-site-duplicate",
    )

    raw_marker = fresh("clean")
    raw_marker_plan = raw_marker / "plan.md"
    raw_marker_plan.write_text(
        raw_marker_plan.read_text().rstrip("\n") + "\n<!-- pin:orphan -->\n"
    )
    case(
        "raw-marker-check",
        [PINS, "check", "--plan", raw_marker_plan, "--ledger", raw_marker / "plan-pins.json"],
        1,
        "pin-raw-marker",
    )

    # -- linter structure controls -----------------------------------------
    arithmetic = fresh("clean")
    arithmetic_plan = arithmetic / "plan.md"
    arithmetic_plan.write_text(
        arithmetic_plan.read_text().replace("Remaining: 17", "Remaining: 99", 1)
    )
    case(
        "budget-arithmetic-lint",
        [LINT, "--plan", arithmetic_plan],
        1,
        "budget-arithmetic",
    )

    missing_section = fresh("clean")
    missing_plan = missing_section / "plan.md"
    missing_plan.write_text(
        missing_plan.read_text().replace("## Evidence pointers", "## Evidence", 1)
    )
    case(
        "missing-section-lint",
        [LINT, "--plan", missing_plan],
        1,
        "missing-section",
    )

    # -- run the controls ---------------------------------------------------
    failures = 0
    print("plan tooling controls — %d cases" % len(CASES))
    for name, args, expect_rc, cause, after in CASES:
        rc, output = run(args)
        problems = []
        if rc != expect_rc:
            problems.append("exit %d, expected %d" % (rc, expect_rc))
        if cause is not None and cause not in output:
            problems.append("output does not contain %r" % cause)
        if after is not None:
            try:
                after(output)
            except CaseFailure as exc:
                problems.append(str(exc))
        status = "PASS" if not problems else "FAIL"
        print("\n=== CASE %s" % name)
        print("$ %s" % " ".join(_display(arg) for arg in args))
        for line in output.rstrip("\n").splitlines():
            print("  " + line)
        print(
            "--- %s: exit=%d expected=%d cause=%s %s"
            % (name, rc, expect_rc, cause or "-", status)
        )
        for problem in problems:
            print("!!! %s: %s" % (name, problem))
        if problems:
            failures += 1

    print("\n=== SUMMARY %d/%d passed, %d failed" % (len(CASES) - failures, len(CASES), failures))
    return 1 if failures else 0


def _display(arg):
    text = str(arg)
    try:
        return str(Path(text).relative_to(ROOT))
    except ValueError:
        return text


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        shutil.rmtree(str(TMP_ROOT), ignore_errors=True)
