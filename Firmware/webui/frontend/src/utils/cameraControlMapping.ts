/**
 * Camera Control Naming Convention Mappings
 *
 * Frontend ↔ Backend mapping for camera controls.
 * Mirrors the Python camera_control_mapping.py module.
 *
 * Naming Convention Layers:
 * -------------------------
 * 1. Frontend (this file):  camelCase    - colourGainRed, exposureTime
 * 2. Backend Settings:      snake_case   - colour_gains_red, exposure_time
 * 3. Picamera2 Controls:    PascalCase   - ColourGainRed, ExposureTime
 *
 * Why This File Exists:
 * --------------------
 * - Eliminates hardcoded string literals throughout Camera.jsx
 * - Provides IDE autocomplete for control names
 * - Single source of truth for frontend control mappings
 * - Parallel structure to backend camera_control_mapping.py
 *
 * Usage:
 * ------
 * import { toBackendKey, toPicameraControl, convertFromBackend } from '../utils/cameraControlMapping'
 *
 * // Convert frontend state to backend format
 * const backendKey = toBackendKey('colourGainRed')  // → 'colour_gains_red'
 *
 * // Convert for WebSocket camera control
 * const cameraKey = toPicameraControl('colourGainRed')  // → 'ColourGainRed'
 *
 * // Bulk conversion
 * const backendSettings = convertToBackend(frontendState)
 * const frontendState = convertFromBackend(backendSettings)
 *
 * Adding New Controls:
 * -------------------
 * 1. Add to FRONTEND_TO_BACKEND mapping (camelCase → snake_case)
 * 2. Add to PICAMERA_CONTROLS mapping (camelCase → PascalCase)
 * 3. BACKEND_TO_FRONTEND updates automatically (reverse mapping)
 * 4. Update backend camera_control_mapping.py to match
 * 5. Update unit tests
 *
 * See Also:
 * ---------
 * - Backend: /webui/backend/camera_control_mapping.py
 * - Tests: /Tests/unit/test_camera_control_mapping.py
 * - Documentation: /webui/docs/NAMING_CONVENTION_ANALYSIS.md
 */

/**
 * Camera control mapping configuration
 */
interface CameraControlMapping {
  FRONTEND_TO_BACKEND: Record<string, string>
  BACKEND_TO_FRONTEND: Record<string, string>
  PICAMERA_CONTROLS: Record<string, string>
}

export const CAMERA_CONTROL_MAPPING: CameraControlMapping = {
  // Frontend camelCase → Backend snake_case
  FRONTEND_TO_BACKEND: {
    // Core image quality
    sharpness: 'sharpness',
    brightness: 'brightness',
    contrast: 'contrast',
    saturation: 'saturation',

    // Colour gains (note: separate components)
    colourGainRed: 'colour_gains_red',
    colourGainBlue: 'colour_gains_blue',

    // Exposure
    exposureTime: 'exposure_time',
    analogueGain: 'analogue_gain',
    aeEnable: 'ae_enable',
    aeLocked: 'ae_locked',
    aeMeteringMode: 'ae_metering_mode',

    // White balance
    awbEnable: 'awb_enable',
    awbLocked: 'awb_locked',
    awbMode: 'awb_mode',
    colourTemperature: 'colour_temperature',

    // Focus
    afMode: 'af_mode',
    afSpeed: 'af_speed',
    afRange: 'af_range',
    afState: 'af_state',
    afWindows: 'af_windows',
    lensPosition: 'lens_position',
    focusFom: 'focus_fom',

    // Other
    noiseReductionMode: 'noise_reduction_mode',
    digitalGain: 'digital_gain',
    scalerCrop: 'scaler_crop',
    sensorTimestamp: 'sensor_timestamp',
    frameDuration: 'frame_duration',
    lux: 'lux',

    // Focus peaking (liveview only)
    focusPeakingEnabled: 'focus_peaking_enabled',
    focusPeakingIntensity: 'focus_peaking_intensity',
    focusPeakingColour: 'focus_peaking_colour',
    focusPeakingAlgorithm: 'focus_peaking_algorithm',
  },

  // Auto-generated reverse mapping (Backend → Frontend)
  BACKEND_TO_FRONTEND: {},  // Populated below

  // Frontend camelCase → Picamera2 PascalCase (for WebSocket controls)
  PICAMERA_CONTROLS: {
    // Core image quality
    sharpness: 'Sharpness',
    brightness: 'Brightness',
    contrast: 'Contrast',
    saturation: 'Saturation',

    // Colour gains
    colourGainRed: 'ColourGainRed',
    colourGainBlue: 'ColourGainBlue',

    // Exposure
    exposureTime: 'ExposureTime',
    analogueGain: 'AnalogueGain',
    aeEnable: 'AeEnable',
    aeLocked: 'AeLocked',
    aeMeteringMode: 'AeMeteringMode',

    // White balance
    awbEnable: 'AwbEnable',
    awbLocked: 'AwbLocked',
    awbMode: 'AwbMode',
    colourTemperature: 'ColourTemperature',

    // Focus
    afMode: 'AfMode',
    afSpeed: 'AfSpeed',
    afRange: 'AfRange',
    afState: 'AfState',
    afWindows: 'AfWindows',
    lensPosition: 'LensPosition',
    focusFom: 'FocusFoM',

    // Other
    noiseReductionMode: 'NoiseReductionMode',
    digitalGain: 'DigitalGain',
    scalerCrop: 'ScalerCrop',
    sensorTimestamp: 'SensorTimestamp',
    frameDuration: 'FrameDuration',
    lux: 'Lux',

    // Focus peaking
    focusPeakingIntensity: 'FocusPeakingIntensity',
    focusPeakingColour: 'FocusPeakingColour',
  }
}

// Generate reverse mapping (snake_case → camelCase)
Object.entries(CAMERA_CONTROL_MAPPING.FRONTEND_TO_BACKEND).forEach(([camel, snake]) => {
  CAMERA_CONTROL_MAPPING.BACKEND_TO_FRONTEND[snake] = camel
})

/**
 * Convert frontend camelCase key to backend snake_case
 *
 * @param {string} camelKey - Frontend key in camelCase
 * @returns {string} Backend key in snake_case
 *
 * @example
 * toBackendKey('colourGainRed')  // → 'colour_gains_red'
 * toBackendKey('exposureTime')   // → 'exposure_time'
 */
export const toBackendKey = (camelKey: string): string => {
  return CAMERA_CONTROL_MAPPING.FRONTEND_TO_BACKEND[camelKey] || camelKey
}

/**
 * Convert backend snake_case key to frontend camelCase
 *
 * @param {string} snakeKey - Backend key in snake_case
 * @returns {string} Frontend key in camelCase
 *
 * @example
 * toFrontendKey('colour_gains_red')  // → 'colourGainRed'
 * toFrontendKey('exposure_time')     // → 'exposureTime'
 */
export const toFrontendKey = (snakeKey: string): string => {
  return CAMERA_CONTROL_MAPPING.BACKEND_TO_FRONTEND[snakeKey] || snakeKey
}

/**
 * Convert frontend camelCase key to Picamera2 PascalCase
 * (for WebSocket camera control updates)
 *
 * @param {string} camelKey - Frontend key in camelCase
 * @returns {string} Picamera2 key in PascalCase
 *
 * @example
 * toPicameraControl('colourGainRed')  // → 'ColourGainRed'
 * toPicameraControl('exposureTime')   // → 'ExposureTime'
 */
export const toPicameraControl = (camelKey: string): string => {
  return CAMERA_CONTROL_MAPPING.PICAMERA_CONTROLS[camelKey] || camelKey
}

/**
 * Convert entire frontend state object to backend format
 *
 * @param {Object} frontendState - Frontend state with camelCase keys
 * @returns {Object} Backend settings with snake_case keys
 *
 * @example
 * convertToBackend({
 *   colourGainRed: 2.5,
 *   exposureTime: 500
 * })
 * // → {
 * //   colour_gains_red: 2.5,
 * //   exposure_time: 500
 * // }
 */
export const convertToBackend = (frontendState: Record<string, unknown>): Record<string, unknown> => {
  const backendSettings: Record<string, unknown> = {}
  Object.entries(frontendState).forEach(([key, value]) => {
    const backendKey = toBackendKey(key)
    backendSettings[backendKey] = value
  })
  return backendSettings
}

/**
 * Convert backend settings object to frontend format
 *
 * @param {Object} backendSettings - Backend settings with snake_case keys
 * @returns {Object} Frontend state with camelCase keys
 *
 * @example
 * convertFromBackend({
 *   colour_gains_red: 2.5,
 *   exposure_time: 500
 * })
 * // → {
 *   colourGainRed: 2.5,
 *   exposureTime: 500
 * // }
 */
export const convertFromBackend = (backendSettings: Record<string, unknown>): Record<string, unknown> => {
  const frontendState: Record<string, unknown> = {}
  Object.entries(backendSettings).forEach(([key, value]) => {
    const frontendKey = toFrontendKey(key)
    frontendState[frontendKey] = value
  })
  return frontendState
}

/**
 * Handle colour gains split (tuple → separate components)
 *
 * @param {Array<number>} colourGains - Tuple [red, blue]
 * @returns {Object} Object with colourGainRed and colourGainBlue
 *
 * @example
 * splitColourGains([2.259, 1.5])
 * // → { colourGainRed: 2.259, colourGainBlue: 1.5 }
 */
export const splitColourGains = (colourGains: number[] | null | undefined): { colourGainRed: number; colourGainBlue: number } => {
  if (!Array.isArray(colourGains) || colourGains.length !== 2) {
    return { colourGainRed: 2.259, colourGainBlue: 1.5 }
  }
  return {
    colourGainRed: colourGains[0],
    colourGainBlue: colourGains[1]
  }
}

/**
 * Combine separate colour gain components into tuple
 *
 * @param {number} red - Red gain value
 * @param {number} blue - Blue gain value
 * @returns {Array<number>} Tuple [red, blue]
 *
 * @example
 * combineColourGains(2.259, 1.5)
 * // → [2.259, 1.5]
 */
export const combineColourGains = (red: number, blue: number): [number, number] => {
  return [red, blue]
}
