#!/usr/bin/env python3
"""Structural consistency check for the conformance vectors under tests/.

This is deliberately shallow: it checks pairing (every <slug>.tn has a matching
<slug>-expected.tn sidecar and vice versa) and a handful of required fields via
substring/regex matching, not a real parse of the sidecar's own TSON content
(see README.md's caveat on this). Replace this with a real parser-based check
once this repo wires in a TSON implementation to read sidecars with.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "tests"
VALID_CATEGORIES = {"lexer", "parser", "resolver", "validation"}
SIDECAR_SUFFIX = "-expected"


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def is_sidecar(p: Path) -> bool:
    return p.stem.endswith(SIDECAR_SUFFIX)


def check_pairing(errors: list[str]) -> None:
    all_tn = list(ROOT.rglob("*.tn"))
    subjects = {p for p in all_tn if not is_sidecar(p)}
    sidecars = {p for p in all_tn if is_sidecar(p)}

    subject_keys = {(p.parent, p.stem): p for p in subjects}
    sidecar_keys = {(p.parent, p.stem[: -len(SIDECAR_SUFFIX)]): p for p in sidecars}

    for key in sorted(subject_keys.keys() - sidecar_keys.keys()):
        fail(f"{subject_keys[key]} has no matching {SIDECAR_SUFFIX}.tn sidecar", errors)
    for key in sorted(sidecar_keys.keys() - subject_keys.keys()):
        fail(f"{sidecar_keys[key]} has no matching .tn input", errors)


def check_sidecar_fields(errors: list[str]) -> None:
    for sidecar_path in sorted(p for p in ROOT.rglob("*.tn") if is_sidecar(p)):
        text = sidecar_path.read_text(encoding="utf-8")
        rel = sidecar_path.relative_to(ROOT.parent)

        outcome_match = re.search(r"\boutcome:\s*(\S+)", text)
        if not outcome_match:
            fail(f"{rel}: missing 'outcome' field", errors)
            continue
        outcome = outcome_match.group(1)
        if outcome not in ("valid", "error", "schema-document"):
            fail(f"{rel}: outcome must be 'valid', 'error', or 'schema-document', found '{outcome}'", errors)
            continue

        bucket_to_outcome = {
            "invalid": "error",
            "valid": "valid",
            "schema-document": "schema-document",
        }
        for bucket, expected_outcome in bucket_to_outcome.items():
            if f"/{bucket}/" in str(sidecar_path) and outcome != expected_outcome:
                fail(
                    f"{rel}: lives under {bucket}/ but outcome is '{outcome}', expected '{expected_outcome}'",
                    errors,
                )

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

    count = len([p for p in ROOT.rglob("*.tn") if not is_sidecar(p)])
    print(f"OK: {count} vector(s), all paired and all sidecars have required fields.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
