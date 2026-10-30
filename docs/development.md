# Development

Use Python 3.9 or newer. From a clone:

```sh
python -m venv .venv
.venv/bin/python -m pip install ".[test]"
.venv/bin/python -m pytest
```

On Windows the environment's executables are in `.venv\Scripts`.

The suite uses complete, self-authored XMP documents. It covers the supplied
three-preset case, equivalent namespace prefixes, URI mismatches, attribute
and element representations, explicit zero, decimal and boolean spellings,
ordered curves, duplicates, metadata, unsupported settings and masks,
malformed XML, DTDs including UTF-16, parser limits, deterministic reports,
read-only inputs, and output aliases. CI runs the suite on Linux, macOS, and
Windows with Python 3.9 and 3.13.

During initial verification, three deliberate implementation mutations were
tested separately. The suite failed each mutated implementation:

| Mutation | Regression that caught it |
| --- | --- |
| Accept a Camera Raw local name from any URI | `test_same_local_name_wrong_uri_is_not_camera_raw` |
| Supply zero for absent cells | `test_absent_is_not_zero` |
| Sort curve points before comparison | `test_curves_use_ordered_decimal_points` |

## Record the demo

Install VHS, ttyd, ffmpeg, and a working Chromium browser, then install the
CLI in the environment and run from the repository root:

```sh
PATH="$PWD/.venv/bin:$PATH" vhs docs/demo.tape
```

The tape copies the example presets into `.work/demo`, records the command
and its complete output, and writes `docs/demo.gif`. It only replaces the
scratch demo's previous report. The CLI itself always refuses overwrites.
The sample report `docs/example-report.json` uses paths relative to the
repository root. No photograph is processed in either demo.

## Comparison checks

`test_prefix_only_changes_hash` changes the XML prefix in place and asserts
that the report is unchanged apart from the hash and size. Hashes are
intentionally sensitive to original bytes. The contrast-removal regression
checks the other demo transformation:

```text
Original:        Shared fields: 2 (1 equal, 1 different, 0 ambiguous)
Prefix renamed: Shared fields: 2 (1 equal, 1 different, 0 ambiguous)
Contrast absent: Shared fields: 1 (1 equal, 0 different, 0 ambiguous)
```

These are structural results. They make no assertion about rendering,
Lightroom import, compatibility, or which preset takes precedence.
