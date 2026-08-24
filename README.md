# TSON Conformance Test Suite

A language-agnostic collection of test vectors for validating TSON implementations against the
[TSON specification](https://tson.io) — starting with Part 1 (lexer and data format). Each vector is a
real `.tn` input document paired with a TSON sidecar describing the expected outcome. Any implementation,
in any language, should be able to run this suite by reading the `.tn` file, running its own
lexer/parser/resolver over it, and comparing against the sidecar.

**`.tn`, not `.tn1`:** the spec reserves `.tn1` as a positive stability claim for the eventual, frozen
"TSON version 1" release — not yet reached, since the spec itself is still a pre-release, 2026-revision-
series draft (see `SPEC-FEEDBACK.md` #20 in the sibling
[ltr8-io-tson-java](https://github.com/litterat/ltr8-io-tson-java) repo). This suite's own vectors use
the unversioned `.tn` extension for as long as that remains true.

## Layout

```
tests/
  lexer/
    valid/
      <slug>.tn
      <slug>-expected.tn
    invalid/
      <slug>.tn
      <slug>-expected.tn
  parser/
    valid/
      <slug>.tn
      <slug>-expected.tn
    invalid/
      <slug>.tn
      <slug>-expected.tn
    schema-document/
      <slug>.tn
      <slug>-expected.tn
  resolver/
    valid/
      <slug>.tn
      <slug>-expected.tn
  vocabulary/
    valid/
      <slug>.tn
      <slug>-expected.tn
    invalid/
      <slug>.tn
      <slug>-expected.tn
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

## Why the input document is always a standalone `.tn` file

Test inputs are never embedded as escaped strings inside another format. Several things this suite needs
to test only exist as raw bytes: a leading byte-order mark, literal NEL/LS/PS characters, un-normalized
(non-NFC) Unicode, mismatched surrogate byte sequences, and so on. Embedding those inside a sidecar string
would require them to survive a round trip through the sidecar format's own escaping — which is exactly
the mechanism under test and would make the fixture ambiguous about what's really being exercised. A raw
`.tn` file removes that ambiguity: what the implementation reads is exactly what's on disk.

`.tn` files are UTF-8 unless a vector's sidecar says otherwise (see `encoding` below).

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

**The [`schemas/`](schemas) directory holds one real TSON schema per conformance layer**
(`lexer-sidecar.tn`, `parser-sidecar.tn`, `resolver-sidecar.tn`, `vocabulary-sidecar.tn`) — a formal,
machine-checkable description of each layer's own sidecar shape, replacing the ad hoc BNF-like
notation (`document = { ... } / { ... }`, `<string-or-absent>` placeholders) an earlier revision of
this README used. Each one resolves and links cleanly against the real bundled meta.tn/core.tn chain
(`SidecarSchemasTest` in `ltr8-io-tson-java`, run alongside the conformance suite itself, so drift
between these schemas and the toolchain that's meant to validate them fails loudly, not silently).
They live outside `tests/` deliberately, so `scripts/check_vectors.py`'s own subject/sidecar pairing
check doesn't see them. **Not yet wired onto the real sidecars themselves** — no existing
`-expected.tn` file carries a `!!schema` directive pointing at one of these yet, so today they're
documentation with a resolver behind it, not live validation; retrofitting the ~120 existing sidecars
(and fixing whatever real shape mismatches that surfaces) is tracked as separate follow-up work.

### Common fields

| Field         | Meaning |
|---------------|---------|
| `spec`        | The spec section this vector targets, e.g. `"§7.2.2"`. Metadata only — not an identifier, not load-bearing for the test. |
| `description` | One line: what this vector exercises and why it's interesting. |
| `encoding`    | Optional. Present only when the `.tn` file is not plain UTF-8. Absent means UTF-8. Values in use: `invalid-utf8` (the subject is deliberately not decodable — §9.1 vectors), `utf-16`, `utf-32`. **A runner must feed the subject's bytes to its lexer unchanged for these**: reading the file into a string first re-encodes it, and for `invalid-utf8` the decode substitutes U+FFFD before the lexer sees anything, so the vector would assert against a different document than the one on disk. An implementation that reads only UTF-8 should *skip* a `utf-16`/`utf-32` vector rather than fail it — §9.1 permits those encodings, so not reading them is a gap in the implementation, not a failed conformance claim. |
| `outcome`     | `valid`, `error`, or (parser layer only) `schema-document`. |

### Schema-governed vectors

Some vectors need their subject document's own `!!meta`/`!!import` to point at a real, working
schema — not the fake `example.com` placeholders `parser`-layer vectors use, where no real
resolution ever happens. Hardcoding the real, versioned identity (e.g.
`https://tson.io/2026/32/m/core.tn`) into every such vector's own `.tn` file would mean every one of
them needs editing whenever the spec revision bumps. Instead, the *sidecar* names the target by a
short, unversioned name, and the runner splices in the real directive before parsing:

| Field    | Meaning |
|----------|---------|
| `meta`   | Optional. A short name (see table below) for the subject's own `!!meta` target. |
| `import` | Optional. An array of short names for the subject's own `!!import` entries, in order — always an array, even for a single entry. |

| Short name       | Current real identity |
|------------------|------------------------|
| `meta-kernel.tn` | `https://tson.io/2026/32/m/meta-kernel.tn` |
| `meta.tn`        | `https://tson.io/2026/32/m/meta.tn` |
| `core.tn`        | `https://tson.io/2026/32/m/core.tn` |

These are the three schema documents this suite's own reference implementation
([ltr8-io-tson-java](https://github.com/litterat/ltr8-io-tson-java)) bundles. Any implementation
running this suite hard-codes this same three-entry table however is natural for it — in
`ltr8-io-tson-java`'s own case, directly off `TsonBundledSchemas`'s constants, so a version bump only
ever touches that one class. When the spec revision bumps, it's this table — not every vector that
imports `core.tn` — that changes.

A runner resolves `meta`/`import` and splices the real `!!meta:"..."`/`!!import:"..."` directives
into the subject's own header before parsing it — right after the subject's own `!!id` line (a
schema document requires `!!meta` "immediately after `!!id` if present", Part 2 §2.2), or at the
very start if the subject has no `!!id` at all. A subject using this mechanism writes its own
`!!id` but omits `!!meta`/`!!import` entirely; the runner adds those:

```
!!id:"https://tson.io/test-suite/schema/valid/some-vector.tn"
{ my_int => integer }
```

```
!!id:"https://tson.io/test-suite/schema/valid/some-vector-expected.tn"
{
  spec: "§8.3"
  description: "A bare reference to a real core.tn constructor resolves"
  outcome: valid
  meta: "meta.tn"
  import: ["core.tn"]
}
```

What actually gets parsed, spliced together, is equivalent to:

```
!!id:"https://tson.io/test-suite/schema/valid/some-vector.tn"
!!meta:"https://tson.io/2026/32/m/meta.tn"
!!import:"https://tson.io/2026/32/m/core.tn"
{ my_int => integer }
```

No vector uses this yet — it's plumbing for the not-yet-added `schema` conformance layer (and any
other layer whose subject ever needs a real governing schema), added ahead of the vectors themselves
specifically so those vectors never have to hardcode a versioned identity.

### Valid lexer-layer vectors

`tokens` is the expected token stream: an array of records, each with a `kind` (using the spec's own
token-stream grammar vocabulary, §7.3 — `single-line-token`, `multi-line-token`, `unquoted-token`,
`structural-delimiter`, `absent-token`, `map-arrow-token`, `directive-token`, `range-token`,
`special-token` — not any particular implementation's internal type names) and the token's decoded `text`.
EOF is not listed. Formally described by [`schemas/lexer-sidecar.tn`](schemas/lexer-sidecar.tn).

```
!!id:"https://tson.io/test-suite/lexer/valid/escape-basic-expected.tn"
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

`document` is the expected parse tree, formally described by
[`schemas/parser-sidecar.tn`](schemas/parser-sidecar.tn) — a real TSON schema, resolved and
regression-tested against the reference implementation's own compiler (see
`SidecarSchemasTest` in `ltr8-io-tson-java`), not ad hoc grammar notation. It uses the spec's own
grammar vocabulary (§2.3, §7.4) rather than any implementation's internal type names, so it stays
language-agnostic — `document`/`data_value`/`sidecar_annotation` (`annotation` collides with a name
`core.tn` already declares)/`scoped_value`/`core_value`, the last discriminated by a `kind` field
covering the six core-value shapes (`token`/`absent`/`empty-brace`/`record`/`map`/`array`) rather than
one BNF alternative per shape.

Every optional field (`id`, `schema`, `type_ref`, an annotation's own `value`, ...) uses the absent
sentinel `_` when the thing isn't present — chosen over simply omitting the field so every
`document`/`data_value`/`sidecar_annotation`/`scoped_value` record has a fixed, predictable shape
regardless of content.

```
!!id:"https://tson.io/test-suite/parser/valid/simple-record-expected.tn"
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
!!id:"https://tson.io/test-suite/parser/schema-document/meta-directive-header-expected.tn"
{
  spec: "§1.5"
  description: "A header containing !!meta identifies a schema document, not a data document"
  outcome: schema-document
}
```

### Valid resolver-layer vectors

The `.tn` file is a single bare token as the whole document (a token alone is a complete, valid
data-value). `base-value` is the expected result of base type resolution (§4), formally described by
[`schemas/resolver-sidecar.tn`](schemas/resolver-sidecar.tn) — `base_value`/`number_form`/`exponent`,
using the spec's own vocabulary for which of the four number-grammar forms a number matched (§7.6)
rather than any particular implementation's internal type names — deliberately **identification
only**: which grammar form and its components, not a bound host numeric type
(`long`/`double`/`BigInteger`/`BigDecimal`). The spec leaves that binding as "an implementation
concern" (§4.3), and different implementations may reasonably choose different host representations,
so this suite doesn't assert one.

```
!!id:"https://tson.io/test-suite/resolver/valid/hex-based-integer-expected.tn"
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

The `.tn` file is a single bare `!type-ref value` data-value — a type-ref immediately followed by its
token (a token alone is a complete data-value at every other layer; here the type-ref is what selects a
built-in atom's parsing contract, §5). `type-ref` restates the annotation name for self-description;
`value`, on a `valid` vector, is the atom's accepted value as a plain decimal string — deliberately
**host-representation-neutral**, the same reasoning as the resolver layer's `base-value`: §5.2 requires an
implementation to preserve the parsed value's information content but leaves the concrete host type
implementation-defined, so this suite asserts the underlying value, not a bound Java/whatever type.
Formally described by [`schemas/vocabulary-sidecar.tn`](schemas/vocabulary-sidecar.tn) — see that
schema's own `@doc` for the two atom families (`complex`, `duration`) whose real `value` is actually a
small nested record, which its own single `text` field is a deliberate simplification of, not a
precise per-family shape (the notes below spell out each family's own real shape in prose):

```
!!id:"https://tson.io/test-suite/vocabulary/valid/int32-plain-expected.tn"
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
`float32`, `float64`, `rational`, `complex`, and (§5.5) `uuid`/`uri`/`ipv4`/`ipv6` are all fully published as-is, so
those aren't similarly restricted. `text` is deliberately *not* covered at all — `text_type` exists in
meta-kernel.tn but `!text` never appears in §5's published table (see this repo's sibling
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
`"-1/2"`) — compared by *value*, not written form (meta.tn: "the token is preserved as written and `2/4`
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

**`value`'s shape for `uri` (§5.5).** `value` is the plain URI string, compared as-is (no normalization —
`uri_type` doesn't claim any). §5.5 cites RFC 3986; be aware that a widely-used implementation
(`java.net.URI`) actually implements the older RFC 2396 (as amended by RFC 2732), not RFC 3986. Vectors in
this suite stick to constructs valid under both revisions (a plain `https://` authority form, a
scheme-less relative reference, a `urn:` scheme) rather than exercising the handful of constructs where
the two revisions disagree, so passing this suite doesn't by itself certify RFC 3986 conformance for an
RFC-2396-based implementation.

**`value`'s shape for `ipv4` (§5.5).** `value` is the plain dotted-quad string, compared by numeric
address value. `ipv4_type` cites RFC 3986's `IPv4address` production (the ABNF used inside a URI's host
component), which is a materially *stricter* grammar than what widely-used IP-address parsers accept —
notably, no leading zeros on an octet and exactly four dotted octets, full stop. This isn't just a
spec-fidelity nicety: a parser that leniently accepts a leading zero (historically read as octal by some
libraries), a short "class-based" form, or a bare 32-bit integer literal as an IP address is exactly the
ambiguity behind real SSRF-filter-bypass techniques, where a validator and the actual network stack
disagree about what address a string denotes. `vocabulary/invalid` includes vectors for exactly these
three lenient-but-non-conformant forms (`ipv4-leading-zero-rejected`, `ipv4-bare-integer-rejected`,
`ipv4-short-form-rejected`) for that reason, not merely as edge-case padding.

**`value`'s shape for `ipv6` (§5.5) — deliberately *not* a textual IPv6 literal.** Unlike every other
vocabulary family in this suite, `value` here is a plain 32-character hex string of the address's 16 raw
bytes (the same convention the binary family uses for its decoded bytes), not an RFC 4291 §2.2 text form.
The reason is specific to IPv6: a widely-used host implementation's own `InetAddress.getByAddress(byte[])`
silently returns a *different Java type* (`Inet4Address` instead of `Inet6Address`) for a 16-byte array in
the IPv4-mapped range (the shape produced by input like `::ffff:192.0.2.1`) — so a comparison oracle built
by handing this suite's own `value` string to that same kind of JDK literal parser would be trustworthy for
some vectors and silently wrong for others, depending on which narrow sub-range the address falls in. A
raw-bytes comparison sidesteps that ambiguity entirely: any implementation can decode 32 hex characters to
16 bytes without needing to trust *any* particular address-literal parser as ground truth.
`vocabulary/valid` includes a vector for exactly this IPv4-mapped form (`ipv6-ipv4-mapped`) for that
reason, not merely as coverage padding — a conformant implementation must still report it as a genuine
IPv6 value, not silently reinterpret it as `ipv4`'s type.

Invalid vocabulary vectors use the same `outcome: error` / `category` shape as any other layer (see
below) — but see the categorization note there before assuming `category: resolver` on these is settled.

### Invalid vectors (any layer)

```
!!id:"https://tson.io/test-suite/lexer/invalid/lone-high-surrogate-expected.tn"
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

`scripts/check_vectors.py` (stdlib-only) checks that every `.tn` has a matching `-expected.tn` sidecar
and vice versa,
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
