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
  parser/
    valid/
      <slug>.tn1
      <slug>.tson
    invalid/
      <slug>.tn1
      <slug>.tson
    schema-document/
      <slug>.tn1
      <slug>.tson
  resolver/
    valid/
      <slug>.tn1
      <slug>.tson
  vocabulary/
    valid/
      <slug>.tn1
      <slug>.tson
    invalid/
      <slug>.tn1
      <slug>.tson
```

Top-level grouping is by **conformance layer** — `lexer`, `parser`, `resolver`, `vocabulary`, and
eventually `schema` — mirroring the four error categories the spec itself defines and treats as stable
for the whole series (spec §8.1: "the categories are defined here for the whole series"). Within each
layer, vectors split into `valid/` (the input is well-formed at this layer), `invalid/` (the input MUST
be rejected at this layer), and — parser layer only — `schema-document/` (see below). `resolver` has no
`invalid/` bucket: base type resolution (§4) never rejects a token, it always resolves to *something*
(worst case, string) — see "Valid resolver-layer vectors" below. `vocabulary` (§5, the built-in type
vocabulary) does have both: a built-in atom's parsing contract can reject a token outright.

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
because it dogfoods the format. The whole sidecar body (everything after the `!!id` header directive) is
a single record `{ ... }`: a bare `field: value` sequence with no enclosing braces is *not* a valid
top-level TSON data-value (records require braces), so every example below is wrapped accordingly — an
earlier revision of this file got that wrong throughout, caught only once
[ltr8-io-tson-java](https://github.com/litterat/ltr8-io-tson-java) had a real structural parser to check
against, which is exactly why "eat your own dog food" is worth doing early. **Caveat:**
`scripts/check_vectors.py`, run in this repo's own CI, still validates sidecars only shallowly
(regex-based field checks, not a real parse) — see "Validating vectors" below. Sidecars are cross-checked
against `ltr8-io-tson-java`'s real lexer/parser before being committed, but that cross-check isn't wired
into this repo's own CI yet.

### Common fields

| Field         | Meaning |
|---------------|---------|
| `spec`        | The spec section this vector targets, e.g. `"§7.2.2"`. Metadata only — not an identifier, not load-bearing for the test. |
| `description` | One line: what this vector exercises and why it's interesting. |
| `encoding`    | Optional. Present only when the `.tn1` file is not plain UTF-8 (e.g. `utf-16`, or a case with intentionally invalid UTF-8 bytes). Absent means UTF-8. |
| `outcome`     | `valid`, `error`, or (parser layer only) `schema-document`. |

### Valid lexer-layer vectors

`tokens` is the expected token stream: an array of records, each with a `kind` (using the spec's own
token-stream grammar vocabulary, §7.3 — `single-line-token`, `multi-line-token`, `unquoted-token`,
`structural-delimiter`, `absent-token`, `map-arrow-token`, `directive-token`, `range-token`,
`special-token` — not any particular implementation's internal type names) and the token's decoded `text`.
EOF is not listed.

```
!!id:"https://tson.io/test-suite/lexer/valid/escape-basic.tson"
{
  spec: "§7.2.2"
  description: "All single-character escape sequences decode to their target characters"
  outcome: valid
  tokens: [
    { kind: single-line-token text: "\" \\ / \b \f \n \r \t  " }
  ]
}
```

### Valid parser-layer vectors

`document` is the expected parse tree, using the spec's own grammar vocabulary (§2.3, §7.4) rather than
any implementation's internal type names, so it stays language-agnostic:

```
document = { id: <string-or-absent> schema: <string-or-absent> root: <data-value> }

data-value  = { annotations: [ <annotation> ... ] type-ref: <string-or-absent> core: <core-value> }
annotation  = { name: <string> value: <data-value-or-absent> }
scoped-value = { schema-ref: <string-or-absent> value: <data-value> }

core-value  = { kind: token  form: unquoted|single-line|multi-line  text: <string> }
            / { kind: absent }
            / { kind: empty-brace }
            / { kind: record  fields: [ { name: <string> value: <scoped-value> } ... ] }
            / { kind: map     entries: [ { key: <data-value> value: <scoped-value> } ... ] }
            / { kind: array   elements: [ <scoped-value> ... ] }
```

`<string-or-absent>` and `<data-value-or-absent>` use the absent sentinel `_` when the optional thing
isn't present (there's no id-directive, no schema-directive, no type-ref, no annotation value) — chosen
over simply omitting the field so every `document`/`data-value`/`annotation`/`scoped-value` record has a
fixed, predictable shape regardless of content.

```
!!id:"https://tson.io/test-suite/parser/valid/simple-record.tson"
{
  spec: "§2.5"
  description: "A record with one field"
  outcome: valid
  document: {
    id: _
    schema: _
    root: {
      annotations: []
      type-ref: _
      core: {
        kind: record
        fields: [
          { name: "name" value: { schema-ref: _ value: { annotations: [] type-ref: _ core: { kind: token form: unquoted text: "Alice" } } } }
        ]
      }
    }
  }
}
```

### Schema-document vectors (parser layer only)

A document whose header contains `!!meta` is a *schema* document (§2.2), not a data document. A Class 1
(data-format-only) processor MUST recognise and reject it with a distinct, categorized diagnostic — not
treat it as malformed input, and not attempt to parse it as data (§1.5, §8.1). These vectors capture that
third outcome, distinct from both `valid` and `error`:

```
!!id:"https://tson.io/test-suite/parser/schema-document/meta-directive-header.tson"
{
  spec: "§1.5"
  description: "A header containing !!meta identifies a schema document, not a data document"
  outcome: schema-document
}
```

### Valid resolver-layer vectors

The `.tn1` file is a single bare token as the whole document (a token alone is a complete, valid
data-value). `base-value` is the expected result of base type resolution (§4), using the spec's own
vocabulary for which of the four number-grammar forms a number matched (§7.6) rather than any particular
implementation's internal type names — deliberately **identification only**: which grammar form and its
components, not a bound host numeric type (`long`/`double`/`BigInteger`/`BigDecimal`). The spec leaves that
binding as "an implementation concern" (§4.3), and different implementations may reasonably choose
different host representations, so this suite doesn't assert one:

```
base-value = { kind: null }
           / { kind: boolean value: true|false }
           / { kind: string text: <string> }
           / { kind: number form: <number-form> }

number-form = { shape: integer        sign: plus|minus|_  digits: <string> }
            / { shape: based-integer  sign: plus|minus|_  radix: hex|octal|binary  digits: <string> }
            / { shape: float          sign: plus|minus|_  integer-part: <string-or-absent>
                                       fraction-digits: <string-or-absent>  exponent: <exponent-or-absent> }
            / { shape: special-value  sign: plus|minus|_  kind: nan|infinity }

exponent = { sign: plus|minus|_ digits: <string> }
```

```
!!id:"https://tson.io/test-suite/resolver/valid/hex-based-integer.tson"
{
  spec: "§4.3"
  description: "An unquoted 0x-prefixed token identifies as a based-integer number in hex"
  outcome: valid
  base-value: {
    kind: number
    form: { shape: based-integer sign: _ radix: hex digits: "FF" }
  }
}
```

### Vocabulary-layer vectors

The `.tn1` file is a single bare `!type-ref value` data-value — a type-ref immediately followed by its
token (a token alone is a complete data-value at every other layer; here the type-ref is what selects a
built-in atom's parsing contract, §5). `type-ref` restates the annotation name for self-description;
`value`, on a `valid` vector, is the atom's accepted value as a plain decimal string — deliberately
**host-representation-neutral**, the same reasoning as the resolver layer's `base-value`: §5.2 requires an
implementation to preserve the parsed value's information content but leaves the concrete host type
implementation-defined, so this suite asserts the underlying value, not a bound Java/whatever type:

```
!!id:"https://tson.io/test-suite/vocabulary/valid/int32-plain.tson"
{
  spec: "§5.6"
  description: "!int32 accepts a plain decimal integer within the signed 32-bit range"
  outcome: valid
  type-ref: "int32"
  value: "200"
}
```

Vectors only exercise annotations §5.6 currently publishes — the integer family is restricted to
`int32`/`int64`/`uint32`/`uint64` for now. The core type library's `integer_type` constructor also backs
`int8`/`int16`/`int128`/`int256`, the matching `uint*` widths, and the `positive_integer`/
`non_negative_integer`/`negative_integer`/`non_positive_integer` refinements, but none of those names
appear in §5.6's *published* table — asserting a vector against one would bind every implementation
running this suite to one implementation's reading of an already-flagged spec gap, not to the spec text
itself, and a strictly-literal implementation would correctly treat e.g. `!int8` as an unrecognized marker
rather than a built-in atom. Add vectors for those names once §5.6 actually publishes them. `number`,
`float32`, `float64`, `rational`, `complex`, and (§5.5) `uuid` are all fully published as-is, so those
aren't similarly restricted. `text` is deliberately *not* covered at all — `text_type` exists in
meta-kernel.tn1 but `!text` never appears in §5's published table (see this repo's sibling
implementation's `SPEC-FEEDBACK.md` #9).

**`value` and floating-point precision.** For the exact atoms (the integer family, `number`), `value` is
unambiguous — compare it as an arbitrary-precision decimal, done. For the approximate atoms (`float32`/
`float64`), the *accepted* value is whatever the token rounds to on the named IEEE 754 grid, which two
different (correct) implementations could format differently as text at the same underlying value. To
sidestep that entirely, `vocabulary/valid` float vectors are restricted to inputs whose rounded value is
**exactly representable in decimal at the chosen `value`'s precision** (`12.5`, `-3.5`, hex-floats that
land on values like `12.0`/`1.0`) — deliberately avoiding inputs like `3.14` or `0.1` that have no exact
binary representation, where the rounded binary32/binary64 value's *exact* decimal expansion is a long,
implementation-comparison-hostile string. Consuming implementations should compare `value` against the
atom's result via numeric equality (e.g. `BigDecimal.compareTo`, not `equals` — scale isn't normative),
matching the resolver layer's own "information content, not canonical form" philosophy. `NaN`/`Infinity`
results aren't yet representable in this sidecar shape at all (`value` is a plain decimal string) — add a
dedicated field for them when a vector actually needs to assert one.

**`value`'s shape for `rational`/`complex`.** Neither has a natural `BigDecimal` representation — a
rational is an exact fraction (not always a terminating decimal, e.g. `1/3`), and a complex number is a
pair. `rational` vectors give `value` as a `"numerator/denominator"` string instead (e.g. `"2/3"`,
`"-1/2"`) — compared by *value*, not written form (meta.tn1: "the token is preserved as written and `2/4`
round-trips as `2/4`... equality operates on the value", so a vector may legitimately assert `value:
"-1/2"` against an input written as `"-2/4"`, and a conforming implementation must still pass). `complex`
vectors give `value` as a small record, `{ real: "<decimal>" imaginary: "<decimal>" }`, each part compared
the same way the `BigDecimal`-based families are (exact for this atom — `complex`'s default component
type is `NUMBER`, so no rounding concern the way `float32`/`float64` have).

**`value`'s shape for the binary family (`base64`/`base64url`/`base32`/`hex`, §5.3).** The host value is a
byte array, not anything `BigDecimal`-comparable — `value` is a plain hex string of the decoded bytes
(e.g. `"4d616e"` for `"Man"`), compared against the atom's result byte-for-byte. Note for `base64url`
vectors specifically: pick byte sequences that actually need the URL-safe alphabet's `-`/`_` (i.e. would
produce `+`/`/` under the standard alphabet) — a byte sequence both alphabets encode identically wouldn't
exercise anything `base64url`-specific.

**`value`'s shape for the temporal family (§5.4).** `date`/`time`/`datetime` give `value` as the plain
RFC 3339 string, in canonical form (uppercase `T`/`Z`) regardless of the input's exact casing — it
represents the resulting value, not an echo of the input. `duration` has no single common representation
to compare against (confirmed during development that no common library type covers the combined
`PnYnMnDTnHnMnS` form directly), so `value` is a small record splitting the calendar and clock parts into
their own independently-parseable ISO 8601 substrings: `{ period: "P1Y2M3D" clock: "PT4H5M6S" }`.

Invalid vocabulary vectors use the same `outcome: error` / `category` shape as any other layer (see
below) — but see the categorization note there before assuming `category: resolver` on these is settled.

### Invalid vectors (any layer)

```
!!id:"https://tson.io/test-suite/lexer/invalid/lone-high-surrogate.tson"
{
  spec: "§7.2.2"
  description: "A high surrogate escape not followed by a low surrogate escape is a lexer error"
  outcome: error
  category: lexer
}
```

`category` is one of the spec's four §8.1 categories: `lexer`, `parser`, `resolver`, `validation`. It's
included explicitly rather than inferred from the directory the vector lives in, so a vector remains
self-describing if it's ever moved.

**Categorization note for vocabulary-layer parse failures.** §5.2 phrases a built-in atom rejecting a
token's format as "is a parse error", and §8.1's canonical-phrasing table maps that exact phrase to the
`parser` category. But §8.1's own `parser`-category description ("structural mismatches: unclosed
brackets, adjacency violations, unexpected tokens, missing separators...") doesn't describe an atom's
value-format contract, and the check happens well after the structural parser has already accepted the
document as well-formed (`!int32 twelve` is a syntactically complete data-value; only interpreting
`twelve` against `int32`'s contract fails) — which every implementation this suite is aware of detects
during resolution, architecturally, not during structural parsing. This suite's `vocabulary/invalid`
vectors currently assert `category: resolver` for this case as the more architecturally coherent reading,
but flag it as provisional in each vector's own `description` — treat only the `error` outcome as settled
for these specific vectors until the spec clarifies which category actually governs. Range/constraint
violations (`9999999999` under `!int32`, `-10` under `!uint32`) are unambiguous: §8.1 explicitly assigns
"range violations by the numeric atoms" to the `validation` category.

Position (line/column/byte-offset) of the error is deliberately **not** asserted — different
implementations may legitimately report an error at slightly different points depending on how far they
look ahead before failing. What's normative is that an error of the given category occurs somewhere.

## Validating vectors

`scripts/check_vectors.py` (stdlib-only) checks that every `.tn1` has a matching `.tson` and vice versa,
and that each sidecar has the required fields with sane values. It's deliberately shallow — a regex-based
check, not a real parse — since this repo doesn't wire in a TSON implementation of its own to parse
sidecars with (that would mean picking one implementation as a dependency for a repo meant to be
implementation-neutral). Runs in CI on every push and PR. Each vector is additionally cross-checked
against `ltr8-io-tson-java`'s real lexer/parser before being committed, but that step is manual, not part
of this repo's own CI.

```
python3 scripts/check_vectors.py
```

## Related

- [ltr8-io-tson-java](https://github.com/litterat/ltr8-io-tson-java) — the Java TSON implementation this
  suite was seeded and cross-checked against.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
