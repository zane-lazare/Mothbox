"""Shared camera settings schema — single source of truth for setting types.

Imported by both TakePhoto.py (firmware) and webui/backend/utils.py.
When adding a new setting, add it to the appropriate type set below
and to WEBUI_ONLY_SETTINGS if it should not be passed to picamera2.
"""

# picamera2 expects int
INT_SETTINGS = {
    "ExposureTime",
    "AfMode",
    "AfSpeed",
    "AfRange",
    "AfMetering",
    "AeMeteringMode",
    "AwbMode",
    "NoiseReductionMode",
    # Webui workflow (int)
    "HDR",
    "HDR_width",
    "FocusBracket",
    "ImageFileType",
    "VerticalFlip",
    "AutoCalibration",
    "AutoCalibrationPeriod",
    "FlashDelay_BeforeCapture",
    "FlashDelay_AfterCapture",
    "FocusBracket_SettleDelay",
    "FocusBracket_LockColorGains",
    "FocusPeakingIntensity",
}

# picamera2 expects float
FLOAT_SETTINGS = {
    "Sharpness",
    "Brightness",
    "Contrast",
    "Saturation",
    "LensPosition",
    "ExposureValue",
    "AnalogueGain",
    "ColourGainRed",
    "ColourGainBlue",
    # Webui workflow (float)
    "FocusBracket_Start",
    "FocusBracket_End",
    "FocusBracket_ColorGainRed",
    "FocusBracket_ColorGainBlue",
}

# Stored as "True"/"False" strings, read with value.lower() == "true"
BOOL_STRING_SETTINGS = {
    "AeEnable",
    "AwbEnable",
    "LensShadingEnable",
    "DefectCorrectionEnable",
    "UseCustomTuning",
    "FocusPeakingEnabled",
}

# Plain string settings (no type coercion needed)
STRING_SETTINGS = {
    "Name",
    "FocusPeakingColour",
    "FocusPeakingColor",
    "FocusPeakingAlgorithm",
}

# Settings NOT passed to picamera2.set_controls().
# TakePhoto.py pops these before calling set_controls().
# Some are used by TakePhoto.py logic (HDR, Name, etc.),
# others are webui-only (FocusBracket_Start, FocusPeaking*, etc.).
WEBUI_ONLY_SETTINGS = {
    # Used by TakePhoto.py logic
    "Name",
    "HDR",
    "HDR_width",
    "AutoCalibration",
    "AutoCalibrationPeriod",
    "ImageFileType",
    "VerticalFlip",
    "ColourGainRed",
    "ColourGainBlue",
    # Webui capture workflow
    "FocusBracket",
    "FocusBracket_Start",
    "FocusBracket_End",
    "FocusBracket_SettleDelay",
    "FocusBracket_LockColorGains",
    "FocusBracket_ColorGainRed",
    "FocusBracket_ColorGainBlue",
    "FlashDelay_BeforeCapture",
    "FlashDelay_AfterCapture",
    # ISP features (webui live view only)
    "LensShadingEnable",
    "DefectCorrectionEnable",
    "UseCustomTuning",
    # Focus peaking (webui live view overlay only)
    "FocusPeakingEnabled",
    "FocusPeakingIntensity",
    "FocusPeakingColour",
    "FocusPeakingColor",
    "FocusPeakingAlgorithm",
}
