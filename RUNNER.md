# Writing a runner

← back to the [README](README.md)

This document is **normative for runners**. The README explains the corpus; this says what a program
must do with it. It exists because the contract used to live only in README prose, and the two
runners written against that prose already disagreed — over whether a subject is fed as bytes or as
a re-encoded string, and over whether an error vector's `category` is checked at all. A third
implementation should not have to guess a third way.

The sidecar's own shape is not described here. It is stated formally, per layer, by the schemas in
[`schemas/`](schemas), and every sidecar names one with `!!schema`. Read those; this document covers
only what a runner *does*.

## Discovery

Vectors are found by walking the tree — there is no manifest.

```
tests/<class>/<layer>/<bucket>/<slug>.tn            the subject
tests/<class>/<layer>/<bucket>/<slug>-expected.tn   the sidecar
```

`<class>` is `class1` or `class2`, matching the spec's own two conformance classes ([TSON-DATA]
§1.5, [TSON-SCHEMA] §1.3). A Class 1 processor runs `class1/` and skips `class2/` — that is what the
directory is for. `<bucket>` is `valid`, `invalid`, or `schema-document`; it must agree with which
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
its own parser is finished: **records, arrays, the three token forms, the absent sentinel `_`, and
the `!!id`/`!!schema` header directives**. No maps, no type-refs, no annotations beyond the `@doc`
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
catches a schema-authoring mistake through its meta-schema's own reader will have a record-shaped code in
hand, and it is still a resolver error. The code says which rule; the phase says which category.

`class2/validate/` is the other way round, and is where the `validation` category finally has vectors: the
schema loaded, so what a diagnostic says about the *data* is the category.

### 3c. A diagnostic that is not a verdict does not satisfy an error vector

An implementation may report that it could not judge something — a construct it has not implemented, a
schema it could not obtain, a binding its own host application got wrong. None of those is one of §8.1's
four categories, and none of them is a document being invalid. A runner that lets one satisfy an `error`
vector reports a pass for a vector it did not run.

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

Anything else — a vector the implementation cannot currently pass — is a failure. Recording it as a
skip is how a corpus stops measuring anything.

### 6. Normalise a resolver-minted name before comparing (Class 2)

The entries a resolver mints for itself — a synthetic lifted from a sugar form, an instantiation closed
from a template application — carry a name ending in an implementation-chosen content hash.
[TSON-SCHEMA] §8.2 keys identity on structure, not on that spelling, so it is **not normative**: both
sides reduce a trailing `_[0-9a-f]{8}` to a fixed placeholder before comparing, wherever such a name
appears — as an entry's own key, inside a body, or in a list of names a sidecar states. A runner that
compares the hashes is testing its own hash function.

## Schema-governed vectors

A vector whose subject needs a real `!!meta`/`!!import`/`!!schema` does not hardcode one: the
*sidecar* names the target by a short, unversioned name (`meta.tn`, `core.tn`) in its `meta`, `import`
or `schema` field, and the runner splices the real, current directive into the subject's header before
parsing. `meta`/`import` govern a schema-document subject, which is what the `class2/schema/` and
`class2/link/` layers use; `schema` governs a data-document subject, which is what `class2/validate/`
uses. Hardcoding
`https://tson.io/2026/34/m/core.tn` in every such subject would mean editing all of them at each
revision bump.

The splice is not a prepend. The header grammar is a fixed sequence — optional `!!id`, then `!!meta`
immediately after it, then `!!import` — so the directives go in right after the subject's own `!!id`
line, or at the very start when it has none.

## `proposed/`

`proposed/` holds vectors for spec questions that are still open — behaviour an implementation has
had to choose because the current revision does not settle it. They exist so an adjudication has
executable evidence rather than prose.

A runner SHOULD execute them and MUST report them separately. They never count toward a conformance
claim, and failing one is not a defect: it means an implementation made the other reasonable choice.
Each such sidecar names the question it embodies.
