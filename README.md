# preset-overlap

See which adjustments your Lightroom presets share before combining them.

[![CI](https://github.com/itzjk/preset-overlap/actions/workflows/ci.yml/badge.svg)](https://github.com/itzjk/preset-overlap/actions/workflows/ci.yml)
[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

![Three XMP presets compared in a terminal](docs/demo.gif)

## Quick start

Install with [pipx](https://pipx.pypa.io/stable/installation/) and Python 3.9 or newer:

```sh
pipx install git+https://github.com/itzjk/preset-overlap.git
```

Point it at your local preset files:

```sh
preset-overlap color.xmp grain.xmp finish.xmp --json report.json
```

The terminal shows one row per supported adjustment and one column per input, followed by shared-field counts, hashes, and XML locations. A dot means the file does not declare that adjustment. The JSON report is created at the path you specify; existing files are never overwritten.

## Features

- Find equal and different values shared across any number of explicitly supplied presets.
- Keep an omitted setting separate from an explicit zero.
- Compare decimal values and ordered tone curves without losing their literal XML values.
- Trace each declaration to its input hash and XML location, regardless of namespace prefix.
- Keep known results visible when masks, profiles, unknown properties, or ambiguous declarations need inspection.

## Why

A [discussion about keeping Lightroom presets when changing editors](https://x.com/dhh/status/2114386945375711448) points to the value of preserving adjustments; it does not establish demand for an overlap checker. Preset names can conceal extra settings, so this tool tests a narrower idea: a matrix makes explicit shared declarations easier to inspect than opening each XML file. [Adobe describes presets as reusable sets of adjustments](https://developer.adobe.com/firefly-services/docs/lightroom/guides/apply-presets/); the [alternatives check](docs/alternatives.md) records why extraction and catalog-based version comparison answer different questions.

## How it works

Files are read in argument order. Properties are identified by namespace URI and local name, then checked against a [documented coverage table](docs/coverage.md). Supported decimals use `Decimal`, booleans use an explicit spelling table, and tone curves use ordered numeric point sequences. Names, UUIDs, and preset metadata stay outside the adjustment matrix. Every duplicate declaration is ambiguous, even if both values match. Neither argument order nor an overlap predicts which setting an editor will apply.

## Usage

| Argument or option | Effect |
| --- | --- |
| `PRESET.xmp ...` | Read these files only, preserving their order. |
| `--json REPORT.json` | Create a new, versioned JSON report with input hashes. |
| `--help` | Show command syntax. |
| `--version` | Print the installed version. |

Exit status is `0` for complete structural coverage, `1` for partial coverage, and `2` for invalid input, command usage, or report creation failure. Shared values, including different ones, do not cause an error. With partial or invalid inputs, the report retains the declarations successfully read from other files. See the [report contract](docs/report-format.md) for automation.

## FAQ

**Does this need Lightroom?** No. Analysis runs offline without an editor, catalog, plugin, or account. Installation downloads the Python package and its parser dependency.

**Does it change my presets?** No. Inputs are opened for reading. Only the optional new JSON file is written; pointing that output at an existing file is rejected.

**Can I try the included example?** From a clone, install with `pipx install .`, then run:

```sh
preset-overlap examples/color.xmp examples/grain.xmp examples/finish.xmp
```

The examples share exposure with equal numeric values and contrast with different values. Grain is exclusive. Changing only an XML prefix preserves the comparison, while changing the file hash. Removing contrast from the grain preset removes just that overlap.

**Are equal values visually equivalent?** Equality here describes explicit declarations. Process versions, profiles, omitted defaults, and editor behavior can change the photograph's appearance.

## Limitations

- Supports the listed global scalars and tone-curve sequences; masks, profiles, and other properties appear under coverage pending.
- Recognizes process version `11.0` as a documented structural case. Other explicit versions make coverage partial.
- Reads XMP only, with limits of 4 MiB, 64 XML levels, and 50,000 elements per input. DTDs and entities are rejected.
- Does not convert, repair, render, or certify presets for any editor. Time savings and willingness to pay have not been measured.

## Contributing

From a clone, install test dependencies with `python -m pip install ".[test]"` and run `python -m pytest`; add self-authored XMP fixtures for new coverage.

## License

[MIT](LICENSE).
