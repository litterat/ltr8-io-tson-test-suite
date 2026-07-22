#!/usr/bin/env python3
"""Structural consistency check for the conformance vectors under tests/.

There's no TSON parser yet to validate sidecars against their own grammar
(see README.md's caveat on this), so this is deliberately shallow: it checks
pairing (every .tn1 has a matching .tson and vice versa) and a handful of
required fields via substring/regex matching, not a real parse. Replace this
with a real parser-based check once one exists.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "tests"
VALID_CATEGORIES = {"lexer", "parser", "resolver", "validation"}


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def check_pairing(errors: list[str]) -> None:
    tn1_files = {p.with_suffix("") for p in ROOT.rglob("*.tn1")}
    tson_files = {p.with_suffix("") for p in ROOT.rglob("*.tson")}

    for missing_sidecar in sorted(tn1_files - tson_files):
        fail(f"{missing_sidecar}.tn1 has no matching .tson sidecar", errors)
    for missing_input in sorted(tson_files - tn1_files):
        fail(f"{missing_input}.tson has no matching .tn1 input", errors)


def check_sidecar_fields(errors: list[str]) -> None:
    for tson_path in sorted(ROOT.rglob("*.tson")):
        text = tson_path.read_text(encoding="utf-8")
        rel = tson_path.relative_to(ROOT.parent)

        outcome_match = re.search(r"\boutcome:\s*(\S+)", text)
        if not outcome_match:
            fail(f"{rel}: missing 'outcome' field", errors)
            continue
        outcome = outcome_match.group(1)
        if outcome not in ("valid", "error"):
            fail(f"{rel}: outcome must be 'valid' or 'error', found '{outcome}'", errors)
            continue

        is_invalid_bucket = "/invalid/" in str(tson_path)
        is_valid_bucket = "/valid/" in str(tson_path)
        if is_invalid_bucket and outcome != "error":
            fail(f"{rel}: lives under invalid/ but outcome is '{outcome}', expected 'error'", errors)
        if is_valid_bucket and outcome != "valid":
            fail(f"{rel}: lives under valid/ but outcome is '{outcome}', expected 'valid'", errors)

        if outcome == "error":
            category_match = re.search(r"\bcategory:\s*(\S+)", text)
            if not category_match:
                fail(f"{rel}: outcome is 'error' but missing 'category' field", errors)
            elif category_match.group(1) not in VALID_CATEGORIES:
                fail(
                    f"{rel}: category '{category_match.group(1)}' is not one of {sorted(VALID_CATEGORIES)}",
                    errors,
                )

        if not re.search(r'\bspec:\s*"', text):
            fail(f"{rel}: missing 'spec' field", errors)
        if not re.search(r'\bdescription:\s*"', text):
            fail(f"{rel}: missing 'description' field", errors)


def main() -> int:
    errors: list[str] = []
    check_pairing(errors)
    check_sidecar_fields(errors)

    if errors:
        print(f"{len(errors)} problem(s) found:\n")
        for e in errors:
            print(f"  - {e}")
        return 1

    count = len(list(ROOT.rglob("*.tn1")))
    print(f"OK: {count} vector(s), all paired and all sidecars have required fields.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
