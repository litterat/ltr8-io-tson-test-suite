# Writing a runner

← back to the [README](README.md)

This document is **normative for runners**. The README explains the corpus; this says what a program
must do with it. It exists because the contract used to live only in README prose, and the two
runners written against that prose already disagreed — over whether a subject is fed as bytes or as
a re-encoded string, and over whether an error vector's `category` is checked at all. A third
implementation should not have to guess a third way.

The sidecar's own shape is not described here. It is stated formally, per layer, by the schemas in
[`schemas/`](schemas), and every sidecar imports one with `!!import`. Read those; this document covers
only what a runner *does*.

## Discovery

Vectors are found by walking the tree — there is no manifest.

```
tests/<class>/<layer>/<bucket>/<slug>.tn            the subject
tests/<class>/<layer>/<bucket>/<slug>-expected.tn   the sidecar
```

`<class>` is `class1` or `class2`, matching the spec's own two conformance classes ([TSON-DATA]
§1.5, [TSON-SCHEMA] §1.3). A Class 1 processor runs `class1/` and skips `class2/` — that is what the
directory is for. `<bucket>` is `valid`, `invalid`, `refused`, or `schema-document`; it must agree with which
member of the sidecar's outcome group is present, and `scripts/check_vectors.py` enforces that.

`proposed/` mirrors the same layout and is **not part of a conformance claim** — see below.

## The rules

### 1. Feed the subject's bytes, never a decoded string

A subject is handed to the lexer as the bytes on disk. Reading it into a string first re-encodes it,
which is harmless for most vectors and destroys exactly the ones that exist to be destroyed: for
`encoding: invalid-utf8`, the decode substitutes U+FFFD before the lexer sees anything, so the runner
would assert that a *different* document is rejected. The README's "Why the input document is always
a standalone `.tn` file" section is the reasoning; this is the obligation that follows from it.

### 2. Parse the sidecar with your own parser

The sidecar is TSON. Parse it with the implementation under test — the circularity is deliberate
dogfooding, and a broken parser fails loudly rather than quietly agreeing with itself.

Sidecars are written in a conservative subset so a from-scratch implementation can read them before
its own parser is finished: **records, arrays, the three token forms, the void sentinel `_`, and
the `!!id`/`!!import` header directives**. No maps, no type-refs, no annotations beyond the `@doc`
in `schemas/`. A vector that needs more than this subset is a vector in the wrong format.

### 3. Assert the category on every error vector, at every layer

An `error` outcome names one of [TSON-DATA] §8.1's four categories — `lexer`, `parser`, `resolver`,
`validation` — and a runner must check that the error it got is of that category. Asserting merely
that *something* was thrown passes a lexer that rejects a document for the wrong reason.

The category is **not** derivable from the layer. The layers are processing stages; the categories
are the spec's. The vocabulary layer raises `resolver` and `validation` errors and never a
"vocabulary" one.

### 3a. At the reader layer, check that the subject parses

A `class1/reader/` error vector exists because no tier below the reader can fail on it. A runner must
therefore parse the subject cleanly *first*, and only then assert that the read reports. That is how this
layer satisfies rule 3: the stated `resolver` category means the reader rejected the document, not the
lexer or the parser, and a vector that had accidentally become a parse error would otherwise pass for the
wrong reason.

### 3b. At the Class 2 schema and link layers, the category is the phase's

An `error` vector under `class2/schema/` or `class2/link/` states `category: resolver`, and it always
will. [TSON-DATA] §8.1 settles it outright for Part 2: "every error that makes a schema fail to load or
ingest — incoherent constraint values, invalid defaults, refuted assertions, failed ingest checks — is a
resolver error, however value-like the violated rule, because it is detected while resolving the schema.
Validation errors are reserved for data checked against a successfully loaded schema."

So a runner satisfies rule 3 at those layers by establishing that the schema did not load. What it must
*not* do is read the category off whatever internal code it happens to raise: an implementation that
catches a schema-authoring mistake through the kernel's own readers will have a record-shaped code in
hand, and it is still a resolver error. The code says which rule; the phase says which category.

`class2/validate/` is the other way round, and is where the `validation` category finally has vectors: the
schema loaded, so what a diagnostic says about the *data* is the category.

### 3c. A diagnostic that is not a verdict does not satisfy an error vector

An implementation may report that it could not judge something — a construct it has not implemented, a
schema it could not obtain, a binding its own host application got wrong. None of those is one of §8.1's
four categories, and none of them is a document being invalid. A runner that lets one satisfy an `error`
vector reports a pass for a vector it did not run.

### 3d. A refusal is not an error, and must be told apart from one

A `refused` vector states one of [TSON-DATA] §8.2's three name-hygiene mechanisms, not one of §8.1's four
categories. §8.2 is explicit that a document failing one of those checks is **refused by this processor**
— a fifth, distinguishable outcome that MUST NOT be reported in any of the four. So a runner must
establish two things: that the document was refused, and that the refusal is distinguishable from a
validity error in whatever the implementation reports. An implementation that reports a confusable pair
the way it reports an out-of-range integer has not passed the vector, however red the document goes.

The distinction is the point of the whole layer. The mechanisms read `confusables.txt`,
`IdentifierStatus.txt` and the script tables, none of which the Unicode Consortium freezes, so a verdict
can change under a routine UCD refresh — and a content-addressed document must mean the same thing
forever. That is why none of this may decide validity, and why the outcome is its own.

### 3e. At the identity layer, judge the subject's first directive

The subject of an identity vector is a header and an empty body, and the vector is about its first
directive's argument alone. Nothing is fetched or resolved. If the directive is `!!id`, it is a document's
own name, and §2.2.1 requires that it be written in canonical form. If it is `!!import`, it is a reference,
read in any spelling of its identity. A `valid` vector's `identity` is the canonical identity: host plus
path, with no scheme or query. The runner compares it byte for byte with the one it computed. An `error`
vector's `category` is `resolver`.

### 4. Do not assert position

Sidecars carry no line, column, or byte offset, and a runner must not require one. Implementations
legitimately fail at different points depending on how far they look ahead before giving up. §8.1's
MUST is that a processor *report* a position, not that two processors agree on one.

### 5. Report every skip, and skip only for these reasons

A conformance claim that silently skips is not a claim. A runner MUST report what it skipped and
why. Exactly three grounds are legitimate:

- **An encoding the implementation does not read.** §9.1 permits `utf-16` and `utf-32`; not reading
  them is a gap in the implementation, not a failed conformance claim. `invalid-utf8` is *not* such a
  ground — it must reach the lexer and be rejected there.
- **A `class2/` vector under a Class 1 processor.** Declared by conformance class, not per vector.
- **A vector under `proposed/`.**
- **A `refused` vector whose `unicode` version the implementation does not carry.** §8.2 says two
  conforming implementations may legitimately disagree on a refusal and that the UTS #39 data version is
  the only thing that explains it, so a runner at a different version has no verdict to give rather than
  a wrong one. It MUST compare versions and report the skip; it MUST NOT skip a vector whose version it
  *does* carry.

Anything else — a vector the implementation cannot currently pass — is a failure. Recording it as a
skip is how a corpus stops measuring anything.

### 6. Normalise a resolver-minted name before comparing (Class 2)

The entries a resolver mints for itself — a synthetic lifted from a sugar form, an instantiation closed
from a template application — carry a name ending in an implementation-chosen content hash.
[TSON-SCHEMA] §8.2 keys identity on structure, not on that spelling, so it is **not normative**: both
sides reduce a trailing `_[0-9a-f]{8}` to a fixed placeholder before comparing, wherever such a name
appears — as an entry's own key, inside a body, or in a list of names a sidecar states. A runner that
compares the hashes is testing its own hash function.

## Every subject is a complete document

A subject carries its own header: an optional `!!id`, then an `!!import` for each schema it needs, each named
by its full, unpinned identity (`https://tson.io/2026/39/m/core.tn`). A runner adds nothing to it and feeds it
as it is on disk (rule 1). The bundled schemas' identities carry the spec revision, so a revision bump rewrites
them in every subject, as it rewrites them in the fixtures; nothing else in the corpus moves with the revision.

**The corpus's own schemas are named by their path under `schemas/`**: `fixtures/link-money.tn` is
`https://tson.io/test-suite/schemas/fixtures/link-money.tn`, which a runner serves from its checkout. That is a
*rule*, not a table, so a runner needs no edit when the corpus grows a fixture. Any other identity a Class 2
subject imports is one of the bundled schemas, which a processor already holds; a Class 1 subject's imports are
never fetched.

A subject is a schema document exactly when its root is tagged `!schema`, after any root annotations; any other
root is data. So a `class2/schema/` or `class2/link/` subject is tagged, a `class2/validate/` subject names its
root's type, and nothing in a sidecar says which kind of document a subject is.

The link layer's §2.2.3 vectors need this: an import closure cannot be exercised with one document, and the
topology lives in the fixture schemas' own `!!import` headers, so a chain, a diamond or a wide fan-in is a
matter of which files exist rather than of anything a runner knows. Fixtures are named for what they declare
rather than for the vector that uses them, the namespace being shared, and each one resolves on its own — the
collisions those vectors are about exist only in the importer. The one exception is `fixtures/a-data-document.tn`,
which is data by design: it is there to be refused as an import.

## A fixture schema's own records

A fixture schema may declare records of its own and namespace types holding them ([TSON-SCHEMA] §4.1): an
entry whose tag names one of them (`myapi => !api { … }`, `chosen => !api_pick { … }`) is a value, not a type, and in
a language that binds an implementation may read it into a host class it supplies itself, or hold it as a value it
has no class for; either way the vector's verdict is the same. A runner that binds MUST supply a class for every such
record before it runs a vector whose schema holds a value of it, and lacking one is not a ground for a skip (rule 5).
The fixtures say which: a fixture under `schemas/fixtures/` whose types a subject holds values of lists in its `@doc`
the records involved, and the declaration is the whole of the shape — nothing else about the representation is
normative.

A `class2/schema/` vector's expected resolved output is read under the subject's own imports, and under the
pre-loaded kernel alone when the subject has none. For a subject importing `meta.tn` or `core.tn` that is the
ordinary reading; a fixture that declares types of its own imports `meta.tn` and adds them, and a value of one of
them is typed there and nowhere else.

## `proposed/`

`proposed/` holds vectors for spec questions that are still open — behaviour an implementation has
had to choose because the current revision does not settle it. They exist so an adjudication has
executable evidence rather than prose.

A runner SHOULD execute them and MUST report them separately. They never count toward a conformance
claim, and failing one is not a defect: it means an implementation made the other reasonable choice.
Each such sidecar names the question it embodies.
