# TSON Conformance Test Suite

A language-agnostic collection of test vectors for validating TSON implementations against the
[TSON specification](https://tson.io) — starting with Part 1 (lexer and data format). Each vector is a
real `.tn1` input document paired with a TSON sidecar describing the expected outcome. Any implementation,
in any language, should be able to run this suite by reading the `.tn1` file, running its own
lexer/parser/resolver over it, and comparing against the sidecar.

## Layout

```
tests/
  lexer/
    valid/
      <slug>.tn1
      <slug>.tson
    invalid/
      <slug>.tn1
      <slug>.tson
```

Top-level grouping is by **conformance layer** — `lexer`, and eventually `parser`, `resolver`,
`vocabulary`, `schema` — mirroring the four error categories the spec itself defines and treats as
stable for the whole series (spec §8.1: "the categories are defined here for the whole series"). Within
each layer, vectors split into `valid/` (the input is well-formed at this layer) and `invalid/` (the
input MUST be rejected at this layer).

`<slug>` is a short, stable, descriptive name (e.g. `escape-basic`, `lone-high-surrogate`). Slugs are
**not** derived from spec section numbers, so a future spec revision renumbering a section never forces a
rename — the section reference lives inside the sidecar instead (see below), where it's just metadata,
not an identifier anything depends on.

## Why the input document is always a standalone `.tn1` file

Test inputs are never embedded as escaped strings inside another format. Several things this suite needs
to test only exist as raw bytes: a leading byte-order mark, literal NEL/LS/PS characters, un-normalized
(non-NFC) Unicode, mismatched surrogate byte sequences, and so on. Embedding those inside a sidecar string
would require them to survive a round trip through the sidecar format's own escaping — which is exactly
the mechanism under test and would make the fixture ambiguous about what's really being exercised. A raw
`.tn1` file removes that ambiguity: what the implementation reads is exactly what's on disk.

`.tn1` files are UTF-8 unless a vector's sidecar says otherwise (see `encoding` below).

## The sidecar format

The sidecar is itself TSON — deliberately, both because it's the natural choice for a TSON project and
because it dogfoods the format. **Caveat:** as of this writing there is no TSON parser yet (only a lexer,
in [ltr8-io-tson-java](https://github.com/ltr8-io/ltr8-io-tson-java)), so sidecars can't yet be
machine-validated against their own grammar. They're hand-written to be valid per the spec; treat that as
provisional until a conforming parser exists to check them.

### Common fields

| Field         | Meaning |
|---------------|---------|
| `spec`        | The spec section this vector targets, e.g. `"§7.2.2"`. Metadata only — not an identifier, not load-bearing for the test. |
| `description` | One line: what this vector exercises and why it's interesting. |
| `encoding`    | Optional. Present only when the `.tn1` file is not plain UTF-8 (e.g. `utf-16`, or a case with intentionally invalid UTF-8 bytes). Absent means UTF-8. |
| `outcome`     | `valid` or `error`. |

### Valid lexer-layer vectors

`tokens` is the expected token stream: an array of records, each with a `kind` (using the spec's own
token-stream grammar vocabulary, §7.3 — `single-line-token`, `multi-line-token`, `unquoted-token`,
`structural-delimiter`, `absent-token`, `map-arrow-token`, `directive-token`, `range-token`,
`special-token` — not any particular implementation's internal type names) and the token's decoded `text`.
EOF is not listed.

```
!!id:"https://tson.io/test-suite/lexer/valid/escape-basic.tson"
spec: "§7.2.2"
description: "All single-character escape sequences decode to their target characters"
outcome: valid
tokens: [
  { kind: single-line-token text: "\" \\ / \b \f \n \r \t  " }
]
```

### Invalid vectors (any layer)

```
!!id:"https://tson.io/test-suite/lexer/invalid/lone-high-surrogate.tson"
spec: "§7.2.2"
description: "A high surrogate escape not followed by a low surrogate escape is a lexer error"
outcome: error
category: lexer
```

`category` is one of the spec's four §8.1 categories: `lexer`, `parser`, `resolver`, `validation`. It's
included explicitly rather than inferred from the directory the vector lives in, so a vector remains
self-describing if it's ever moved.

Position (line/column/byte-offset) of the error is deliberately **not** asserted — different
implementations may legitimately report an error at slightly different points depending on how far they
look ahead before failing. What's normative is that an error of the given category occurs somewhere.
