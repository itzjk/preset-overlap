# Report contract, schema 1.0

JSON uses UTF-8, two-space indentation, escaped control characters, and a
trailing newline. There are no timestamps, random identifiers, or absolute
path expansion. The same bytes and argument strings produce the same report
bytes. Path strings reflect the arguments supplied by the caller. Read order
does not express application precedence.

| Key | Meaning |
| --- | --- |
| `schema_version` | `1.0`; incompatible changes require a new major version. |
| `status` | `complete`, `partial`, or `invalid`, corresponding to exit 0, 1, or 2. |
| `namespaces` | Fixed aliases used by location paths. Property identity also includes the explicit URI. |
| `inputs` | Argument order, IDs `p1`, `p2`, etc.; path, SHA-256 of bytes read, size, coverage status, and preset metadata. |
| `fields` | Supported global adjustments, sorted by local name, with one cell per input. |
| `summary` | Field counts by classification, count of fields in multiple inputs, and pending coverage record count. |
| `coverage_pending` | Unsupported properties or representations with file ID, location, reason, and preserved value. |
| `errors` | Invalid input messages; other readable inputs still contribute results. |

Each field has `namespace`, `name`, `kind`, `classification`, `declared_in`,
and `cells`. Classifications are `exclusive`, `shared_equal`,
`shared_different`, and `ambiguous`. `shared_fields` counts every field
declared in multiple input slots, including ambiguous ones. Ambiguity takes
precedence over the other classifications. A field with three declarations,
two equal and one different, is `shared_different`; each occurrence remains
available. Repeating a file argument creates another input slot.

Each cell contains `input_id`, `state`, and `occurrences`. `unavailable` means
the input was invalid or unreadable; no absence or value is inferred. `absent` has an
empty occurrence list; it never has a numeric value. `declared` contains one
interpreted occurrence. `ambiguous` contains duplicates or an uninterpretable
value, without selecting one. Each occurrence keeps `literal`, `path`, and
`representation`. Successfully read values add `normalized`: a canonical
decimal string, JSON boolean, or ordered list of decimal coordinate pairs.
Complex elements add `xml`, a prefix-independent tree of expanded tag and
attribute names, decoded text, tail text, and ordered children. The scalar
`literal` is the decoded attribute value or element's leading text. For
curves the complete literal point strings are in `xml`. XML parsing normalizes
line endings and attribute whitespace; this is not a byte-range source map.
The hash identifies the original bytes.

Locations use fixed aliases, per-name sibling indexes, and `/@` for
attributes, for example:

`/x:xmpmeta[1]/rdf:RDF[1]/rdf:Description[1]/@crs:Exposure2012`

Unknown namespaces in locations use expanded `{URI}name` notation. They are
display locations, not executable XPath expressions. Every namespace alias
is declared in the report. Prefix-only edits preserve comparisons and
locations but change input hashes and potentially sizes.

Unreadable, oversized, or non-regular inputs have `sha256: null` and
`size_bytes: null`. Malformed XML within the size limit still receives a
hash. Parsing stops at 4 MiB, 64 levels, or 50,000 elements; DTDs, declared
entities, and external references are forbidden by defusedxml. Standard XML
character references remain valid.

Reports are created exclusively. An existing path, symlink, or hard link is
never overwritten, including links to an input. Report creation failures
exit 2 on stderr. A report marked invalid can still have useful known rows;
its counts describe only declarations successfully read, not every input.
