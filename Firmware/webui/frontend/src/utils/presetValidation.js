/**
 * Frontend Preset Validation
 *
 * @deprecated Will be replaced by Zod schemas in src/schemas/camera-preset.ts
 * during Phase 1 of the form validation standardization (#197). Do not add new imports.
 *
 * Mirrors backend validation rules from webui/backend/utils.py (ALLOWED_LIVEVIEW_SETTINGS)
 * to provide client-side validation before API calls.
 *
 * Purpose:
 * - Catch invalid preset settings before sending to backend
 * - Provide clear, user-friendly error messages
 * - Prevent confusing backend validation errors
 *
 * Boolean Settings:
 * Boolean settings accept both actual booleans (true/false) from form state
 * and string literals ("true"/"false") from backend CSV storage.
 *
 * Usage:
 * ```js
 * import { validatePresetSettings } from '../utils/presetValidation'
 *
 * const errors = validatePresetSettings(settings)
 * if (errors.length > 0) {
 *   // Show errors to user
 * }
 * ```
 *
 * See Also:
 * - Backend: /webui/backend/utils.py (lines 267-302)
 * - Camera mapping: /webui/frontend/src/utils/cameraControlMapping.js
 */

import { toBackendKey } from './cameraControlMapping'

/**
 * Validation rule types for different control categories
 */

/**
 * Create a boolean validator (must be "true" or "false" strings)
 * Note: Actual boolean values (true/false) are NOT allowed - backend expects string literals
 * @returns {Function} Validator function
 */
const createBooleanValidator = () => {
  return (value) => {
    // Accept actual booleans (from form state) and string "true"/"false" (from backend)
    if (typeof value === 'boolean') {
      return true
    }
    const strValue = String(value).toLowerCase()
    return strValue === 'true' || strValue === 'false'
  }
}

/**
 * Create an enum validator (must be one of allowed integer values)
 * @param {Array<number>} allowedValues - Array of valid integer values
 * @returns {Function} Validator function
 */
const createEnumValidator = (allowedValues) => {
  return (value) => {
    try {
      const intValue = parseInt(value, 10)
      if (isNaN(intValue)) return false
      return allowedValues.includes(intValue)
    } catch {
      return false
    }
  }
}

/**
 * Create a range validator (must be a number within min/max range)
 * @param {number} min - Minimum value (inclusive)
 * @param {number} max - Maximum value (inclusive)
 * @param {boolean} isInteger - Whether value must be an integer
 * @returns {Function} Validator function
 */
const createRangeValidator = (min, max, isInteger = false) => {
  return (value) => {
    try {
      const numValue = isInteger ? parseInt(value, 10) : parseFloat(value)
      if (isNaN(numValue)) return false
      return numValue >= min && numValue <= max
    } catch {
      return false
    }
  }
}

/**
 * Create a string enum validator (must be one of allowed string values)
 * @param {Array<string>} allowedValues - Array of valid string values (case-insensitive)
 * @returns {Function} Validator function
 */
const createStringEnumValidator = (allowedValues) => {
  return (value) => {
    const strValue = String(value).toLowerCase()
    return allowedValues.includes(strValue)
  }
}

/**
 * Liveview settings validation rules
 * Mirrors backend ALLOWED_LIVEVIEW_SETTINGS from webui/backend/utils.py
 *
 * Key format: snake_case (backend format)
 * Values: { validator: Function, errorMessage: string }
 *
 * @type {Object.<string, {validator: Function, errorMessage: string}>}
 * @property {Object} focus_peaking_enabled - Boolean: "true" or "false"
 * @property {Object} awb_enable - Boolean: "true" or "false"
 * @property {Object} ae_enable - Boolean: "true" or "false"
 * @property {Object} lens_shading_enable - Boolean: "true" or "false"
 * @property {Object} defect_correction_enable - Boolean: "true" or "false"
 * @property {Object} use_custom_tuning - Boolean: "true" or "false"
 * @property {Object} af_mode - Enum: 0 (Manual), 1 (Auto Single), 2 (Continuous)
 * @property {Object} af_speed - Enum: 0 (Normal), 1 (Fast)
 * @property {Object} af_range - Enum: 0 (Normal), 1 (Macro), 2 (Full)
 * @property {Object} awb_mode - Enum: 0-7 (Auto, Incandescent, etc.)
 * @property {Object} noise_reduction_mode - Enum: 0 (Off), 1 (Fast), 2 (High Quality)
 * @property {Object} ae_metering_mode - Enum: 0 (Centre), 1 (Spot), 2 (Matrix)
 * @property {Object} sharpness - Float: 0.0 to 4.0
 * @property {Object} brightness - Float: -1.0 to 1.0
 * @property {Object} contrast - Float: 0.0 to 4.0
 * @property {Object} saturation - Float: 0.0 to 4.0
 * @property {Object} lens_position - Float: 0.0 to 10.0 diopters
 * @property {Object} exposure_value - Float: -8.0 to 8.0 EV
 * @property {Object} analogue_gain - Float: 1.0 to 16.0
 * @property {Object} colour_gains_red - Float: 1.0 to 4.0
 * @property {Object} colour_gains_blue - Float: 1.0 to 4.0
 * @property {Object} exposure_time - Integer: 1 to 999,999 microseconds
 * @property {Object} focus_peaking_intensity - Integer: 50 to 200
 * @property {Object} focus_peaking_colour - String: green, red, yellow, cyan, magenta
 * @property {Object} focus_peaking_color - String: green, red, yellow, cyan, magenta (US spelling)
 * @property {Object} focus_peaking_algorithm - String: laplacian, sobel, canny
 */
export const LIVEVIEW_VALIDATION_RULES = {
  // Boolean controls - Enable/disable features
  focus_peaking_enabled: {
    validator: createBooleanValidator(),
    errorMessage: 'Focus peaking enabled must be "true" or "false"'
  },
  awb_enable: {
    validator: createBooleanValidator(),
    errorMessage: 'AWB enable must be "true" or "false"'
  },
  ae_enable: {
    validator: createBooleanValidator(),
    errorMessage: 'AE enable must be "true" or "false"'
  },
  lens_shading_enable: {
    validator: createBooleanValidator(),
    errorMessage: 'Lens shading enable must be "true" or "false"'
  },
  defect_correction_enable: {
    validator: createBooleanValidator(),
    errorMessage: 'Defect correction enable must be "true" or "false"'
  },
  use_custom_tuning: {
    validator: createBooleanValidator(),
    errorMessage: 'Use custom tuning must be "true" or "false"'
  },

  // Integer enumeration controls (modes/ranges/speeds)
  af_mode: {
    validator: createEnumValidator([0, 1, 2]),
    errorMessage: 'AF mode must be 0 (Manual), 1 (Auto Single), or 2 (Continuous)'
  },
  af_speed: {
    validator: createEnumValidator([0, 1]),
    errorMessage: 'AF speed must be 0 (Normal) or 1 (Fast)'
  },
  af_range: {
    validator: createEnumValidator([0, 1, 2]),
    errorMessage: 'AF range must be 0 (Normal), 1 (Macro), or 2 (Full)'
  },
  // Note: af_metering is NOT validated here - it's set automatically by click-to-focus
  // and is not included in currentSettings/liveControls passed to the modal
  awb_mode: {
    validator: createEnumValidator([0, 1, 2, 3, 4, 5, 6, 7]),
    errorMessage: 'AWB mode must be between 0 (Auto) and 7'
  },
  noise_reduction_mode: {
    validator: createEnumValidator([0, 1, 2]),
    errorMessage: 'Noise reduction mode must be 0 (Off), 1 (Fast), or 2 (High Quality)'
  },
  ae_metering_mode: {
    validator: createEnumValidator([0, 1, 2]),
    errorMessage: 'AE metering mode must be 0 (Centre), 1 (Spot), or 2 (Matrix)'
  },

  // Float controls - Image quality and camera parameters
  sharpness: {
    validator: createRangeValidator(0.0, 4.0),
    errorMessage: 'Sharpness must be between 0.0 and 4.0'
  },
  brightness: {
    validator: createRangeValidator(-1.0, 1.0),
    errorMessage: 'Brightness must be between -1.0 and 1.0'
  },
  contrast: {
    validator: createRangeValidator(0.0, 4.0),
    errorMessage: 'Contrast must be between 0.0 and 4.0'
  },
  saturation: {
    validator: createRangeValidator(0.0, 4.0),
    errorMessage: 'Saturation must be between 0.0 and 4.0'
  },
  lens_position: {
    validator: createRangeValidator(0.0, 10.0),
    errorMessage: 'Lens position must be between 0.0 and 10.0 diopters'
  },
  exposure_value: {
    validator: createRangeValidator(-8.0, 8.0),
    errorMessage: 'Exposure value must be between -8.0 and 8.0 EV'
  },
  analogue_gain: {
    validator: createRangeValidator(1.0, 16.0),
    errorMessage: 'Analogue gain must be between 1.0 and 16.0'
  },
  colour_gains_red: {
    validator: createRangeValidator(1.0, 4.0),
    errorMessage: 'Red colour gain must be between 1.0 and 4.0'
  },
  colour_gains_blue: {
    validator: createRangeValidator(1.0, 4.0),
    errorMessage: 'Blue colour gain must be between 1.0 and 4.0'
  },

  // Integer controls - Timing and discrete values
  exposure_time: {
    validator: (value) => {
      try {
        const intValue = parseInt(value, 10)
        if (isNaN(intValue)) return false
        return intValue > 0 && intValue < 1000000 // 1µs to just under 1 second
      } catch {
        return false
      }
    },
    errorMessage: 'Exposure time must be between 1 and 999,999 microseconds'
  },

  // Focus peaking overlay controls (preview-only visual aid)
  focus_peaking_intensity: {
    validator: createRangeValidator(50, 200, true),
    errorMessage: 'Focus peaking intensity must be between 50 and 200'
  },
  focus_peaking_colour: {
    validator: createStringEnumValidator(['green', 'red', 'yellow', 'cyan', 'magenta']),
    errorMessage: 'Focus peaking colour must be green, red, yellow, cyan, or magenta'
  },
  focus_peaking_color: {
    validator: createStringEnumValidator(['green', 'red', 'yellow', 'cyan', 'magenta']),
    errorMessage: 'Focus peaking color must be green, red, yellow, cyan, or magenta'
  },
  focus_peaking_algorithm: {
    validator: createStringEnumValidator(['laplacian', 'sobel', 'canny']),
    errorMessage: 'Focus peaking algorithm must be laplacian, sobel, or canny'
  }
}

/**
 * Validate a single setting value
 *
 * @param {string} key - Setting key (can be camelCase or snake_case)
 * @param {any} value - Setting value to validate
 * @returns {Object|null} Error object {key, value, message} or null if valid
 *
 * @example
 * validateSetting('sharpness', 2.5)  // null (valid)
 * validateSetting('sharpness', 5.0)  // {key: 'sharpness', value: 5.0, message: '...'}
 * validateSetting('colourGainRed', 2.0)  // null (auto-converts to colour_gains_red)
 */
export const validateSetting = (key, value) => {
  // Convert camelCase to snake_case if needed
  const backendKey = toBackendKey(key)

  // Get validation rule
  const rule = LIVEVIEW_VALIDATION_RULES[backendKey]

  // If no rule exists, skip validation (setting not in liveview scope)
  if (!rule) {
    return null
  }

  // Run validator
  const isValid = rule.validator(value)

  if (!isValid) {
    return {
      key: backendKey,
      value: value,
      message: rule.errorMessage
    }
  }

  return null
}

/**
 * Validate an entire preset settings object
 *
 * @param {Object} settings - Settings object (can have camelCase or snake_case keys)
 * @returns {Array<Object>} Array of error objects [{key, value, message}, ...]
 *
 * @example
 * const errors = validatePresetSettings({
 *   sharpness: 5.0,  // invalid
 *   brightness: 0.5,  // valid
 *   colourGainRed: 0.5  // invalid (min is 1.0)
 * })
 * // Returns:
 * // [
 * //   {key: 'sharpness', value: 5.0, message: 'Sharpness must be between 0.0 and 4.0'},
 * //   {key: 'colour_gains_red', value: 0.5, message: 'Red colour gain must be between 1.0 and 4.0'}
 * // ]
 */
export const validatePresetSettings = (settings) => {
  const errors = []

  // Validate each setting
  Object.entries(settings).forEach(([key, value]) => {
    const error = validateSetting(key, value)
    if (error) {
      errors.push(error)
    }
  })

  return errors
}

/**
 * Format validation errors into a user-friendly message
 *
 * @param {Array<Object>} errors - Array of error objects from validatePresetSettings()
 * @param {number} maxErrors - Maximum number of errors to show (default: 5)
 * @returns {string} Formatted error message
 *
 * @example
 * const errors = validatePresetSettings(settings)
 * if (errors.length > 0) {
 *   toast.error(formatValidationErrors(errors))
 * }
 */
export const formatValidationErrors = (errors, maxErrors = 5) => {
  if (errors.length === 0) {
    return ''
  }

  const errorCount = errors.length
  const displayErrors = errors.slice(0, maxErrors)

  let message = `Invalid preset settings (${errorCount} error${errorCount > 1 ? 's' : ''}):\n\n`

  displayErrors.forEach((error, index) => {
    message += `${index + 1}. ${error.key} = ${error.value}\n   ${error.message}\n`
  })

  if (errorCount > maxErrors) {
    message += `\n... and ${errorCount - maxErrors} more error${errorCount - maxErrors > 1 ? 's' : ''}`
  }

  return message.trim()
}
