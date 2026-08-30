#!/usr/bin/env python3
"""Layout checks for the conformance corpus.

Deliberately narrow: this checks only what a schema cannot. The *shape* of a sidecar is stated by
schemas/<layer>-sidecar.tn and every sidecar names one with !!schema, so field-level checking belongs
there and is done by the implementations, which read every sidecar against its schema as part of
running the corpus (see RUNNER.md). What no schema can see is the filesystem: that a subject and a
sidecar are paired, that they sit under a recognised class/layer/bucket, that the bucket agrees with
the outcome the sidecar states, and that a sidecar names the schema and identity its own path implies.

Stdlib only, and no TSON parser: this repo stays implementation-neutral, so it does not take one of
the implementations under test as a dependency.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
SIDECAR_SUFFIX = "-expected"
IDENTITY_PREFIX = "https://tson.io/test-suite/"
SCHEMA_PREFIX = IDENTITY_PREFIX + "schemas/"

CLASSES = {"class1", "class2"}
LAYERS = {
    "class1": {"lexer", "parser", "resolver", "vocabulary", "reader", "json"},
    "class2": {"schema", "link", "validate"},
}
# The outcome group member each bucket's sidecars must state. `refused` is TSON-DATA 8.1's fifth
# outcome -- a name-hygiene policy refusal (8.2), which is not one of the four error categories.
BUCKET_OUTCOME = {"valid": "valid", "invalid": "error", "schema-document": "schema-document",
                  "refused": "refused"}


def is_sidecar(p: Path) -> bool:
    return p.stem.endswith(SIDECAR_SUFFIX)


def check_pairing(errors: list[str]) -> None:
    all_tn = list(TESTS.rglob("*.tn"))
    subjects = {(p.parent, p.stem): p for p in all_tn if not is_sidecar(p)}
    sidecars = {(p.parent, p.stem[: -len(SIDECAR_SUFFIX)]): p for p in all_tn if is_sidecar(p)}

    for key in sorted(subjects.keys() - sidecars.keys()):
        errors.append(f"{subjects[key].relative_to(ROOT)} has no matching {SIDECAR_SUFFIX}.tn sidecar")
    for key in sorted(sidecars.keys() - subjects.keys()):
        errors.append(f"{sidecars[key].relative_to(ROOT)} has no matching .tn input")


def check_layout(errors: list[str]) -> None:
    """tests/<class>/<layer>/<bucket>/<slug>.tn -- and nothing else under tests/."""
    for path in sorted(TESTS.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(TESTS)
        if path.suffix != ".tn":
            errors.append(f"tests/{rel}: not a .tn file")
            continue
        if len(rel.parts) != 4:
            errors.append(f"tests/{rel}: expected tests/<class>/<layer>/<bucket>/<slug>.tn")
            continue
        cls, layer, bucket, _ = rel.parts
        if cls not in CLASSES:
            errors.append(f"tests/{rel}: unknown conformance class '{cls}'")
        elif layer not in LAYERS[cls]:
            errors.append(f"tests/{rel}: unknown layer '{layer}' for {cls}")
        if bucket not in BUCKET_OUTCOME:
            errors.append(f"tests/{rel}: unknown bucket '{bucket}'")
        elif bucket == "schema-document" and layer != "parser":
            errors.append(f"tests/{rel}: the schema-document bucket is parser-layer only")
        elif bucket == "refused" and layer != "reader":
            errors.append(f"tests/{rel}: the refused bucket is reader-layer only")


def check_sidecar_header(errors: list[str]) -> None:
    for path in sorted(p for p in TESTS.rglob("*.tn") if is_sidecar(p)):
        rel = path.relative_to(TESTS)
        if len(rel.parts) != 4:
            continue  # already reported by check_layout
        cls, layer, bucket, name = rel.parts
        text = path.read_text(encoding="utf-8")

        expected_id = f'!!id:"{IDENTITY_PREFIX}{cls}/{layer}/{bucket}/{name}"'
        if not text.startswith(expected_id):
            errors.append(f"tests/{rel}: !!id must be {expected_id}, matching its own path")

        expected_schema = f'!!schema:"{SCHEMA_PREFIX}{layer}-sidecar.tn"'
        if expected_schema not in text:
            errors.append(f"tests/{rel}: must declare {expected_schema}")

        outcome = BUCKET_OUTCOME.get(bucket)
        if outcome and not re.search(rf"^\s*{re.escape(outcome)}:", text, re.MULTILINE):
            errors.append(f"tests/{rel}: lives under {bucket}/ but does not state '{outcome}'")


def check_schemas_exist(errors: list[str]) -> None:
    for layer in sorted({p.relative_to(TESTS).parts[1] for p in TESTS.rglob("*.tn")
                         if len(p.relative_to(TESTS).parts) == 4}):
        schema = ROOT / "schemas" / f"{layer}-sidecar.tn"
        if not schema.is_file():
            errors.append(f"schemas/{layer}-sidecar.tn is missing, but tests/*/{layer}/ has vectors")


def main() -> int:
    errors: list[str] = []
    check_pairing(errors)
    check_layout(errors)
    check_sidecar_header(errors)
    check_schemas_exist(errors)

    if errors:
        print(f"{len(errors)} problem(s) found:\n")
        for e in errors:
            print(f"  - {e}")
        return 1

    count = len([p for p in TESTS.rglob("*.tn") if not is_sidecar(p)])
    print(f"OK: {count} vector(s), all paired, placed, and naming their own schema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
