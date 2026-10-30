CRS = "http://ns.adobe.com/camera-raw-settings/1.0/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
NAMESPACES = {"crs": CRS, "rdf": RDF, "x": "adobe:ns:meta/"}

DECIMALS = frozenset("""
Exposure2012 Contrast2012 Highlights2012 Shadows2012 Whites2012 Blacks2012
Clarity2012 Texture Dehaze Vibrance Saturation Temperature Tint
IncrementalTemperature IncrementalTint Sharpness SharpenRadius SharpenDetail
SharpenEdgeMasking LuminanceSmoothing LuminanceNoiseReductionDetail
LuminanceNoiseReductionContrast ColorNoiseReduction ColorNoiseReductionDetail
GrainAmount GrainSize GrainFrequency PostCropVignetteAmount
PostCropVignetteMidpoint PostCropVignetteFeather PostCropVignetteRoundness
""".split())
BOOLEANS = frozenset({"ConvertToGrayscale", "AutoTone"})
BOOLEAN_VALUES = {"True": True, "False": False, "true": True, "false": False, "1": True, "0": False}
CURVES = frozenset("""
ToneCurve ToneCurveRed ToneCurveGreen ToneCurveBlue
ToneCurvePV2012 ToneCurvePV2012Red ToneCurvePV2012Green ToneCurvePV2012Blue
""".split())
METADATA = frozenset("""
Name UUID ShortName SortName Group Description Copyright ContactInfo PresetType
Cluster SupportsAmount SupportsColor SupportsMonochrome SupportsHighDynamicRange
SupportsNormalDynamicRange SupportsSceneReferred SupportsOutputReferred
CameraModelRestriction Version ProcessVersion
""".split())
PROCESS_VERSIONS = frozenset({"11.0"})
KINDS = {**dict.fromkeys(DECIMALS, "decimal"), **dict.fromkeys(BOOLEANS, "boolean"), **dict.fromkeys(CURVES, "curve")}
