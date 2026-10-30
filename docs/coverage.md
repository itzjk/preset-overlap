# Structural coverage

All adjustment names below belong to
`http://ns.adobe.com/camera-raw-settings/1.0/`. A spelling such as `crs` or
`adjust` has no effect on identity. Only attributes of top-level
`rdf:Description` nodes and their immediate property elements are global.
The description must be an immediate child of `rdf:RDF`, either the document
root or immediately inside `x:xmpmeta`. Nested local adjustments never enter
the global matrix. Both supported representations of the same property in
one input count as duplicate declarations.

## Global scalar table

Each name in a row is a separate supported property. The table defines
comparison types, not Lightroom slider bounds or editor support.

| Group | Decimal properties |
| --- | --- |
| Basic tone | Exposure2012, Contrast2012, Highlights2012, Shadows2012, Whites2012, Blacks2012 |
| Presence and color | Clarity2012, Texture, Dehaze, Vibrance, Saturation |
| White balance | Temperature, Tint, IncrementalTemperature, IncrementalTint |
| Detail | Sharpness, SharpenRadius, SharpenDetail, SharpenEdgeMasking |
| Noise | LuminanceSmoothing, LuminanceNoiseReductionDetail, LuminanceNoiseReductionContrast, ColorNoiseReduction, ColorNoiseReductionDetail |
| Grain | GrainAmount, GrainSize, GrainFrequency |
| Vignette | PostCropVignetteAmount, PostCropVignetteMidpoint, PostCropVignetteFeather, PostCropVignetteRoundness |

All numeric comparisons use exact `decimal.Decimal` values without float
conversion or context rounding. Leading signs and surrounding whitespace are
accepted; scientific notation, non-finite values, and malformed numbers make
the declaration ambiguous. No missing value is supplied. No range validation
or interpretation of the setting's effect is performed.

| Boolean properties | True spellings | False spellings |
| --- | --- | --- |
| ConvertToGrayscale, AutoTone | `True`, `true`, `1` | `False`, `false`, `0` |

Only surrounding whitespace is removed for boolean comparison. Other
capitalizations and spellings are ambiguous.

## Ordered tone curves

Supported names: ToneCurve, ToneCurveRed, ToneCurveGreen, ToneCurveBlue,
ToneCurvePV2012, ToneCurvePV2012Red, ToneCurvePV2012Green,
ToneCurvePV2012Blue.

The property must contain exactly one unqualified `rdf:Seq` with at least one
simple `rdf:li` item. Each item contains two decimal values separated by a
comma. Numeric formatting and whitespace do not change equality; point order
and point count do. The tool does not sort points or validate a curve's visual
meaning. Qualified, empty, or otherwise complex forms stay ambiguous and
appear in coverage pending. The original points remain in the occurrence's
`xml` tree, with their decoded text intact.

## Preset metadata

These properties are retained under each input's `metadata`, outside the
adjustment matrix: Name, UUID, ShortName, SortName, Group, Description,
Copyright, ContactInfo, PresetType, Cluster, SupportsAmount, SupportsColor,
SupportsMonochrome, SupportsHighDynamicRange, SupportsNormalDynamicRange,
SupportsSceneReferred, SupportsOutputReferred, CameraModelRestriction,
Version, ProcessVersion. Structured metadata, including localized names, is
retained as an expanded-name XML tree. Duplicate metadata is listed in
coverage pending without selecting a preferred occurrence.

`ProcessVersion="11.0"` is a recognized structural case from the
[template linked by Adobe's API guide](https://github.com/AdobeDocs/cis-photoshop-api-docs/blob/main/sample-code/lr-sample-app/crs.xml).
Other explicit process versions and qualified version elements are pending;
known adjustment values remain available for structural comparison. Absence
of ProcessVersion means it was not declared, not that a version was inferred.
Recognition is not renderer compatibility testing.

## Pending coverage

Every other Camera Raw property, including CameraProfile, Look, masks, and
future settings, is reported with its file identifier, URI, name, and location.
Unknown structures retain attributes, text, child order, and tail text in an
XML tree. Nested Camera Raw properties are also reported at their own paths.
Invalid representations of known adjustments appear both as ambiguous matrix
cells and pending coverage. Non-Camera-Raw namespaces are outside this
inspection's scope. A complete status means this structural table covered
the Camera Raw declarations encountered, not that a preset is safe to stack.

Field names and structure references were checked against
[ExifTool's Camera Raw table](https://github.com/exiftool/exiftool/blob/980409314fddbd83d9092b5c160fafab7f67fd52/lib/Image/ExifTool/XMP.pm)
on 2026-10-29. The fixtures here are self-authored, not copies of presets.
