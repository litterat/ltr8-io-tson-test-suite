# TSON Conformance Test Suite

A language-agnostic collection of test vectors for validating TSON implementations against the
[TSON specification](https://tson.io). Each vector is a real `.tn` input document paired with a TSON
sidecar stating the expected outcome. Any implementation, in any language, runs this corpus by
reading the `.tn` file, running its own lexer/parser/resolver over it, and comparing against the
sidecar.

- **[RUNNER.md](RUNNER.md)** — normative: what a runner must do. Read this before writing one.
- **[`schemas/`](schemas)** — normative: the shape of a sidecar, one real TSON schema per layer.
  Every sidecar names its own with `!!schema`.
- **[COVERAGE.md](COVERAGE.md)** — generated: what the corpus currently covers, and so what it does not.

This file is neither. It explains why the corpus is shaped the way it is.

**`.tn`, not `.tn1`:** the spec reserves `.tn1` as a positive stability claim for the eventual, frozen
"TSON version 1" release — not yet reached, since the spec itself is still a pre-release, 2026-revision-
series draft. [TSON-DATA] §7.1 states the rule: `.tn` "makes no stability claim: it is the extension of
the 2026 revision series", while `.tn1` "MUST NOT be used before that release". This suite's own vectors
use `.tn` for as long as that remains true.

## Spec revision, and how to consume this repo

The corpus states what **one** spec revision settles. `REVISION` names it — currently `33` — and the
repository is tagged per revision (`rev-33`, `rev-34`, …) at the last commit that targets it. A vector
encodes a revision's behaviour, so a revision bump can legitimately move a vector's expected outcome;
that is a corpus change, not a regression in whoever was passing before.

**Consume this repo at a pinned commit, never at a branch.** An implementation that tracks `main` goes
red when a vector is added upstream, with no change of its own — which has already happened to a
consumer here. Pinning makes the bump a deliberate commit: fetch the corpus at a fixed SHA, and move
the pin when you are ready to answer whatever it now asks. Both current implementations do this with a
small `scripts/fetch-references.sh`.

## Layout

```
tests/
  class1/                      the data-format processor ([TSON-DATA] §1.5)
    lexer/{valid,invalid}/                 §7.2, §7.3
    parser/{valid,invalid,schema-document}/  §2, §3, §7.4, §7.5
    resolver/valid/                        §4
    vocabulary/{valid,invalid}/            §5
    reader/{valid,invalid}/                §2.5, §2.6, §2.8, §2.9
  class2/                      the schema-aware processor ([TSON-SCHEMA] §1.3)
schemas/                       one sidecar schema per layer
  fixtures/                    schemas the link layer's vectors import
```

Top-level grouping is by **conformance class**, because the spec defines exactly two and an
implementation claims one: a Class 1 processor runs `class1/` and skips `class2/` without having to
know which layers happen to be Part 2.

Below that, grouping is by **processing layer**. The layers are *not* [TSON-DATA] §8.1's four error
categories, and an earlier revision of this file wrongly said they were. §8.1's categories are
`lexer`/`parser`/`resolver`/`validation`; the layers are stages of a pipeline. They cross: the
vocabulary layer raises `resolver` and `validation` errors and never a "vocabulary" one. That is why
every error vector writes its category out rather than leaving it to be inferred from a directory.

`resolver` has no `invalid/` bucket: base type resolution (§4) never rejects a token, it always
resolves to *something* — worst case, string.

### The reader layer

The other layers stop below the readers. §1.2 leaves a set of rules to no tier at all: the token stream
and the structural parser both decline to dedupe fields or keys, resolve an empty brace, or interpret
token text. So §2.5's unique field names, §2.6's key identity, §2.8's empty brace and §2.9's
absent-key restriction have nowhere else to be tested from outside an implementation — a
`parser/invalid/` vector cannot fail on `{ a: 1  a: 2 }`, because the parser accepts it by design.

This is the layer where a Class 1 document gets its verdict, and the first that can. §2.6's own
"a processor that decodes values compares decoded values" is the clearest case: `{ 0xFF => 1  255 => 2 }`
has two textually distinct keys and one decoded one, so only a reader can see the duplicate.

An `error` vector here states `category: resolver`, and its subject **must parse** — that is what makes
it a reader-layer vector rather than a parser-layer one, and `RUNNER.md` requires a runner to check it.

### The Class 2 layers

A Class 2 processor resolves a schema, links it, and validates data against it, and the three layers are
those three answers.

**`schema/` needs no invented expectation format.** [TSON-SCHEMA] §1.3 makes producing a resolved schema
value a MUST and §8 fixes its serialization, so a valid vector's subject is a schema document and its
expected side is the resolved output that document denotes, written in the spec's own §8 form. A runner
reads that output with its own meta.tn-governed reader before comparing, which makes the expected side
validated data rather than a transcript of whoever wrote it.

The expected side is carried as a multi-line token rather than modelled field by field. Modelling it
would restate meta.tn inside a sidecar schema and leave two statements of one shape to drift; a
multi-line token escapes nothing, so this stays inside the conservative subset RUNNER.md rule 2 states.

**No `schema/` subject declares a template**, and the reason is about where the comparison happens rather
than about what §8 admits. A resolver holds an open entry's body as the application as written, held
unread until materialisation (§5.10); the same declaration written as §8 output and read back binds an
ordinary record body, `type_ref.name` being typed `identifier` and a parameter being one. So the two sides
of such a vector agree as documents and differ as values, and a runner comparing values has nothing it can
state.

§8.1 does not settle which side should move — it says "no `type_definition` could carry" a held body, and
then specifies how a parameter reference is read "in any `type_ref`, at any depth ... against the enclosing
entry's `parameters` list", a rule with no position to apply at if the first sentence holds. What a
template resolves to is stated at the link layer instead, over the entries it mints, until that is
answered.

**`link/` states individual facts** about the linked namespace rather than a whole document: what
§2.2.3's import closure binds, what §5.4 derives for a choice, what §8.2's `subtypes` index holds.
Linking derives a handful of things and merges a namespace, and a vector exercising one of them should
not have to write out every entry of core.tn to say so.

**`validate/` is where §8.1's `validation` category finally has vectors** — it is "reserved for data
checked against a successfully loaded schema", which is exactly what a subject here is. The expected side
of a failure is the neutral half of a diagnostic and only that: the category, and the RFC 6901 pointer
into the *data*. Never a message, never a position, and never a schema pointer — where in a schema a
constraint is written is an implementation's choice of route, and two conforming processors legitimately
name different ones.

### The fifth outcome

`reader/refused/` and `class2/schema/refused/` are the buckets that are not a verdict on the document. §8.2's name-hygiene
mechanisms — skeleton distinctness, `Identifier_Status`, and the restriction level — refuse a document
*without making it invalid*, and §8.1 gives that its own outcome, which MUST NOT be reported in any of
the four error categories.

The reason is that none of them can be validity. Each reads data the Unicode Consortium declines to
freeze (`confusables.txt`, `IdentifierStatus.txt`, the script tables), so a verdict can change under a
routine UCD refresh, and a content-addressed document must mean the same thing forever. Skeleton
distinctness has a second disqualification: it does not compose across `!!import`, and it has pure-ASCII
false positives — `comer` and `corner` share a skeleton through `m → rn`, which this corpus carries as a
vector precisely because it is the argument. A sound basis for a default; an unsound one for a rule.

[TSON-SCHEMA] §11.4 supplies the schema layer's scopes — the members of one enum, the field names of one
record definition with its groups' member labels, the declared names of one schema, and the merged
namespace at `!!import` — and `class2/schema/refused/` is where those are stated. It carries the positions
an implementation is most likely to miss: an enum member and a group's member labels reach a schema through
a constructor's own vocabulary rather than through a declaration, so a processor that applies a mechanism
where a name is *read* rather than where a scope is *walked* can pass every other vector and fail those.

So a `refused` sidecar names the mechanism and the **UTS #39 data version** it was computed against.
§8.2 says two conforming implementations may legitimately disagree and that the version is the only
thing that explains it — which makes the version a runner's fourth legitimate skip ground, and the
only one that is about the vector rather than the implementation's conformance class.

`<slug>` is a short, stable, descriptive name (`escape-basic`, `lone-high-surrogate`). Slugs are
**not** derived from spec section numbers, so a future revision renumbering a section never forces a
rename; the section reference lives in the sidecar, where it is metadata rather than an identifier.

## Why the input document is always a standalone `.tn` file

Test inputs are never embedded as escaped strings inside another format. Several things this corpus
needs to test only exist as raw bytes: a leading byte-order mark, literal NEL/LS/PS characters,
un-normalized (non-NFC) Unicode, mismatched surrogate byte sequences. Embedding those inside a
sidecar string would require them to survive a round trip through the sidecar format's own escaping —
which is the mechanism under test, and would make the fixture ambiguous about what is really being
exercised. A raw `.tn` file removes that ambiguity: what the implementation reads is exactly what is
on disk. RUNNER.md turns this into an obligation on the runner.

## Why the sidecar is itself TSON

The natural choice for a TSON project, and it dogfoods the format: every sidecar is parsed by the
implementation under test, so a broken parser fails loudly rather than quietly agreeing with itself.
The circularity is the point.

It also means the sidecars are held to their own schemas. `schemas/<layer>-sidecar.tn` is a real TSON
schema resolving against the bundled meta.tn/core.tn chain, and each layer's sidecars declare it with
`!!schema`. Each is one **field group** ([TSON-SCHEMA] §5.11) over the layer's outcomes, so exactly
one of `valid`/`error`/`schema-document` is present and the member label *is* the outcome — there is
no separate `outcome` field that could disagree with the payload beside it. `valid` cannot omit what
it exists to carry, and `error` cannot carry it. The parser layer's `core_value` is a group over the
six core-value kinds for the same reason: a token carries `form` and `text` and cannot carry a
record's `fields`.

**Validation runs in the implementations, not here.** Each runner reads every sidecar against its
declared schema as part of running the corpus, which is where a real TSON implementation already is.
This repo's own CI checks only what a schema cannot see — pairing, placement, and that a sidecar names
the schema and identity its own path implies (`scripts/check_vectors.py`) — deliberately, so that a
corpus meant to be implementation-neutral does not take one of the implementations under test as a
dependency of its own build.

## Schema-governed vectors

Some vectors need their subject's own `!!meta`/`!!import` to point at a real, working schema, rather
than the placeholder identities parser-layer vectors use where no resolution ever happens. Hardcoding
the versioned identity into every such subject would mean editing all of them at each revision bump.
Instead the *sidecar* names the target by a short, unversioned name and the runner splices the real
directive in before parsing:

| Short name       | Current real identity                      |
|------------------|--------------------------------------------|
| `meta-kernel.tn` | `https://tson.io/2026/35/m/meta-kernel.tn` |
| `meta.tn`        | `https://tson.io/2026/35/m/meta.tn`        |
| `core.tn`        | `https://tson.io/2026/35/m/core.tn`        |

Any other short name is the corpus's own schema, named by its path under `schemas/` — so
`fixtures/link-money.tn` is `https://tson.io/test-suite/schemas/fixtures/link-money.tn`. The three
bundled names are listed because their identities carry the spec revision; everything else is derived,
which is what lets the corpus grow a fixture without every runner editing a constant to keep up.

## Two things the sidecars deliberately do not pin

**Host representation.** The resolver layer's `base-value` is *identification only* — which of §7.6's
four number-grammar forms a token matched, and its components — never a bound host numeric type. §4.3
leaves that binding an implementation concern. The vocabulary layer's `value` follows the same rule
for the same reason (§5.2 requires the parsed value's information content to be preserved and leaves
the concrete host type implementation-defined), and names which textual form it used:
`decimal`/`hex`/`rational`/`text`/`complex`/`duration`. See
[`schemas/vocabulary-sidecar.tn`](schemas/vocabulary-sidecar.tn) for which atoms use which.

**Error position.** Sidecars carry no line, column, or byte offset. Implementations legitimately fail
at different points depending on how far they look ahead before giving up. What is normative is that
an error of the stated category occurs; §8.1's MUST is that a processor *report* a position, not that
two processors agree on one.

### One category that is not settled

§5.2 phrases a built-in atom rejecting a token's format as "is a parse error", and §8.1's
canonical-phrasing table maps that phrase to the `parser` category. But §8.1's own `parser` description
("structural mismatches: unclosed brackets, adjacency violations, unexpected tokens, missing
separators…") does not describe an atom's value-format contract, and the check happens well after the
structural parser has accepted the document — `!int32 twelve` is a syntactically complete data-value,
and only interpreting `twelve` against `int32`'s contract fails. Every implementation this corpus knows
of detects it during resolution, architecturally.

Those vectors therefore state `category: resolver` as the more architecturally coherent reading, and
say so in their own `description`. Treat only the `error` outcome as settled for them until the spec
clarifies. Range and constraint violations are unambiguous: §8.1 assigns "range violations by the
numeric atoms" to `validation` explicitly.

## Checking the corpus

```
python3 scripts/check_vectors.py    # pairing, placement, declared schema and identity
python3 scripts/coverage.py         # regenerate COVERAGE.md
```

Both are stdlib-only and run in CI on every push and PR.

## Related

- [ltr8-io-tson-java](https://github.com/litterat/ltr8-io-tson-java) — the reference implementation,
  which this corpus was seeded from and is cross-checked against.
- [ltr8-io-tson-typescript](https://github.com/litterat/ltr8-io-tson-typescript) — the TypeScript port.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
