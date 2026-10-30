# Alternatives check

Checked on 2026-10-29 before building the analyzer. These are bounded workflow
checks, not a claim that no other tool exists. The three inputs are the
self-authored files in `examples/`; no catalog or third-party preset was read.

## ExifTool

Source revision:
[`980409314fddbd83d9092b5c160fafab7f67fd52`](https://github.com/exiftool/exiftool/tree/980409314fddbd83d9092b5c160fafab7f67fd52).
Running its Perl executable from a source checkout succeeded:

```sh
exiftool -j -G1 -s -XMP-crs:all examples/color.xmp examples/grain.xmp examples/finish.xmp
```

The returned setting records were:

```json
[
  {"SourceFile":"examples/color.xmp","XMP-crs:Exposure2012":0.30,"XMP-crs:Contrast2012":10},
  {"SourceFile":"examples/grain.xmp","XMP-crs:Contrast2012":0,"XMP-crs:GrainAmount":20},
  {"SourceFile":"examples/finish.xmp","XMP-crs:Exposure2012":0.3}
]
```

ExifTool already solves general extraction. That command does not produce a
cross-file matrix, classify shared values, or attach XML locations to each
cell. Writing a separate aggregation script would supply the workflow this
project packages. Use ExifTool when extracting broader metadata is the task.

## Lightroom MCP

Source revision:
[`55cd17f9cc9942468bac438b965908ab76b62a9d`](https://github.com/Automaat/lightroom-mcp/tree/55cd17f9cc9942468bac438b965908ab76b62a9d).
Its actual `compare_develop_presets` input schema was compiled with Ajv and
tested with the following requests:

```json
{"files":["examples/color.xmp","examples/grain.xmp","examples/finish.xmp"]}
```

Rejected: `base` and `candidate` are required; `files` is not allowed.

```json
{"base":{"path":"examples/color.xmp"},"candidate":{"path":"examples/grain.xmp"}}
```

Rejected: selectors require `preset_uuid` or `preset_name`; `path` is not
allowed. The
[handler](https://github.com/Automaat/lightroom-mcp/blob/55cd17f9cc9942468bac438b965908ab76b62a9d/plugin/LightroomMCP.lrplugin/HandlerDevelop.lua)
resolves two Lightroom presets and returns changed settings, excluding equal
ones. Its documented workflow requires Lightroom Classic and its plugin.
This was a schema-level attempt with local files, not an end-to-end Lightroom
run. No plugin was installed and no Lightroom session was used. The tool
fits catalog-based preset iteration; it does not accept this independent
multi-file demo through that interface.

## Conversion

[LRtemplate2XMPPresets](https://github.com/yuzukumo/LRtemplate2XMPPresets)
converts legacy presets to XMP. That is separate from inspecting declarations
already present in several XMP files. Conversion was not rerun for this task.

## Evidence boundary

The brief supplied a snapshot of a
[preset-portability discussion](https://x.com/dhh/status/2114386945375711448),
dated 2026-10-25, with 2,678 likes, 145 replies, and 88 reposts captured on
2026-10-29. Those counters are supplied evidence, not a fresh query. The
author did not request an overlap detector. The value of a shared-field
matrix, its frequency of use, time savings, and willingness to pay remain
unmeasured. The example proves structural comparison, not photographic
results or visual incompatibility.
