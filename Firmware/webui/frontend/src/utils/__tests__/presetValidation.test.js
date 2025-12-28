/**
 * Tests for Frontend Preset Validation
 *
 * Verifies that frontend validation rules match backend validation from
 * webui/backend/utils.py (ALLOWED_LIVEVIEW_SETTINGS)
 */

import { describe, it, expect } from 'vitest'
import {
  LIVEVIEW_VALIDATION_RULES,
  validateSetting,
  validatePresetSettings,
  formatValidationErrors
} from '../presetValidation'

describe('presetValidation', () => {
  describe('LIVEVIEW_VALIDATION_RULES', () => {
    it('should have validation rules for all expected settings', () => {
      const expectedKeys = [
        // Boolean controls
        'focus_peaking_enabled',
        'awb_enable',
        'ae_enable',
        'lens_shading_enable',
        'defect_correction_enable',
        'use_custom_tuning',
        // Integer enums
        'af_mode',
        'af_speed',
        'af_range',
        'af_metering',
        'awb_mode',
        'noise_reduction_mode',
        'ae_metering_mode',
        // Float ranges
        'sharpness',
        'brightness',
        'contrast',
        'saturation',
        'lens_position',
        'exposure_value',
        'analogue_gain',
        'colour_gains_red',
        'colour_gains_blue',
        // Integer controls
        'exposure_time',
        // Focus peaking
        'focus_peaking_intensity',
        'focus_peaking_colour',
        'focus_peaking_color',
        'focus_peaking_algorithm'
      ]

      expectedKeys.forEach(key => {
        expect(LIVEVIEW_VALIDATION_RULES[key]).toBeDefined()
        expect(LIVEVIEW_VALIDATION_RULES[key].validator).toBeInstanceOf(Function)
        expect(LIVEVIEW_VALIDATION_RULES[key].errorMessage).toBeTruthy()
      })
    })
  })

  describe('validateSetting - Boolean Controls', () => {
    const booleanSettings = [
      'focus_peaking_enabled',
      'awb_enable',
      'ae_enable',
      'lens_shading_enable',
      'defect_correction_enable',
      'use_custom_tuning'
    ]

    booleanSettings.forEach(setting => {
      it(`should accept "true" and "false" strings for ${setting}`, () => {
        expect(validateSetting(setting, 'true')).toBeNull()
        expect(validateSetting(setting, 'false')).toBeNull()
        expect(validateSetting(setting, 'True')).toBeNull() // case-insensitive
        expect(validateSetting(setting, 'FALSE')).toBeNull()
      })

      it(`should reject invalid values for ${setting}`, () => {
        expect(validateSetting(setting, '1')).not.toBeNull()
        expect(validateSetting(setting, 'yes')).not.toBeNull()
        expect(validateSetting(setting, true)).not.toBeNull() // actual boolean
      })
    })
  })

  describe('validateSetting - Integer Enum Controls', () => {
    it('should validate af_mode (0, 1, 2)', () => {
      expect(validateSetting('af_mode', 0)).toBeNull()
      expect(validateSetting('af_mode', 1)).toBeNull()
      expect(validateSetting('af_mode', 2)).toBeNull()
      expect(validateSetting('af_mode', '1')).toBeNull() // string numbers ok
      expect(validateSetting('af_mode', 3)).not.toBeNull()
      expect(validateSetting('af_mode', -1)).not.toBeNull()
    })

    it('should validate af_speed (0, 1)', () => {
      expect(validateSetting('af_speed', 0)).toBeNull()
      expect(validateSetting('af_speed', 1)).toBeNull()
      expect(validateSetting('af_speed', 2)).not.toBeNull()
    })

    it('should validate af_range (0, 1, 2)', () => {
      expect(validateSetting('af_range', 0)).toBeNull()
      expect(validateSetting('af_range', 1)).toBeNull()
      expect(validateSetting('af_range', 2)).toBeNull()
      expect(validateSetting('af_range', 3)).not.toBeNull()
    })

    it('should validate af_metering (0, 1, 2)', () => {
      expect(validateSetting('af_metering', 0)).toBeNull()
      expect(validateSetting('af_metering', 1)).toBeNull()
      expect(validateSetting('af_metering', 2)).toBeNull()
      expect(validateSetting('af_metering', 3)).not.toBeNull()
    })

    it('should validate awb_mode (0-7)', () => {
      for (let i = 0; i <= 7; i++) {
        expect(validateSetting('awb_mode', i)).toBeNull()
      }
      expect(validateSetting('awb_mode', 8)).not.toBeNull()
      expect(validateSetting('awb_mode', -1)).not.toBeNull()
    })

    it('should validate noise_reduction_mode (0, 1, 2)', () => {
      expect(validateSetting('noise_reduction_mode', 0)).toBeNull()
      expect(validateSetting('noise_reduction_mode', 1)).toBeNull()
      expect(validateSetting('noise_reduction_mode', 2)).toBeNull()
      expect(validateSetting('noise_reduction_mode', 3)).not.toBeNull()
    })

    it('should validate ae_metering_mode (0, 1, 2)', () => {
      expect(validateSetting('ae_metering_mode', 0)).toBeNull()
      expect(validateSetting('ae_metering_mode', 1)).toBeNull()
      expect(validateSetting('ae_metering_mode', 2)).toBeNull()
      expect(validateSetting('ae_metering_mode', 3)).not.toBeNull()
    })
  })

  describe('validateSetting - Float Range Controls', () => {
    it('should validate sharpness (0.0 - 4.0)', () => {
      expect(validateSetting('sharpness', 0.0)).toBeNull()
      expect(validateSetting('sharpness', 2.0)).toBeNull()
      expect(validateSetting('sharpness', 4.0)).toBeNull()
      expect(validateSetting('sharpness', '2.5')).toBeNull() // string numbers ok
      expect(validateSetting('sharpness', -0.1)).not.toBeNull()
      expect(validateSetting('sharpness', 4.1)).not.toBeNull()
    })

    it('should validate brightness (-1.0 - 1.0)', () => {
      expect(validateSetting('brightness', -1.0)).toBeNull()
      expect(validateSetting('brightness', 0.0)).toBeNull()
      expect(validateSetting('brightness', 1.0)).toBeNull()
      expect(validateSetting('brightness', -1.1)).not.toBeNull()
      expect(validateSetting('brightness', 1.1)).not.toBeNull()
    })

    it('should validate contrast (0.0 - 4.0)', () => {
      expect(validateSetting('contrast', 0.0)).toBeNull()
      expect(validateSetting('contrast', 2.0)).toBeNull()
      expect(validateSetting('contrast', 4.0)).toBeNull()
      expect(validateSetting('contrast', -0.1)).not.toBeNull()
      expect(validateSetting('contrast', 4.1)).not.toBeNull()
    })

    it('should validate saturation (0.0 - 4.0)', () => {
      expect(validateSetting('saturation', 0.0)).toBeNull()
      expect(validateSetting('saturation', 2.0)).toBeNull()
      expect(validateSetting('saturation', 4.0)).toBeNull()
      expect(validateSetting('saturation', -0.1)).not.toBeNull()
      expect(validateSetting('saturation', 4.1)).not.toBeNull()
    })

    it('should validate lens_position (0.0 - 10.0)', () => {
      expect(validateSetting('lens_position', 0.0)).toBeNull()
      expect(validateSetting('lens_position', 5.0)).toBeNull()
      expect(validateSetting('lens_position', 10.0)).toBeNull()
      expect(validateSetting('lens_position', -0.1)).not.toBeNull()
      expect(validateSetting('lens_position', 10.1)).not.toBeNull()
    })

    it('should validate exposure_value (-8.0 - 8.0)', () => {
      expect(validateSetting('exposure_value', -8.0)).toBeNull()
      expect(validateSetting('exposure_value', 0.0)).toBeNull()
      expect(validateSetting('exposure_value', 8.0)).toBeNull()
      expect(validateSetting('exposure_value', -8.1)).not.toBeNull()
      expect(validateSetting('exposure_value', 8.1)).not.toBeNull()
    })

    it('should validate analogue_gain (1.0 - 16.0)', () => {
      expect(validateSetting('analogue_gain', 1.0)).toBeNull()
      expect(validateSetting('analogue_gain', 8.0)).toBeNull()
      expect(validateSetting('analogue_gain', 16.0)).toBeNull()
      expect(validateSetting('analogue_gain', 0.9)).not.toBeNull() // min is 1.0
      expect(validateSetting('analogue_gain', 16.1)).not.toBeNull()
    })

    it('should validate colour_gains_red (1.0 - 4.0)', () => {
      expect(validateSetting('colour_gains_red', 1.0)).toBeNull()
      expect(validateSetting('colour_gains_red', 2.5)).toBeNull()
      expect(validateSetting('colour_gains_red', 4.0)).toBeNull()
      expect(validateSetting('colour_gains_red', 0.9)).not.toBeNull() // min is 1.0
      expect(validateSetting('colour_gains_red', 4.1)).not.toBeNull()
    })

    it('should validate colour_gains_blue (1.0 - 4.0)', () => {
      expect(validateSetting('colour_gains_blue', 1.0)).toBeNull()
      expect(validateSetting('colour_gains_blue', 2.5)).toBeNull()
      expect(validateSetting('colour_gains_blue', 4.0)).toBeNull()
      expect(validateSetting('colour_gains_blue', 0.9)).not.toBeNull() // min is 1.0
      expect(validateSetting('colour_gains_blue', 4.1)).not.toBeNull()
    })
  })

  describe('validateSetting - Special Controls', () => {
    it('should validate exposure_time (1 - 999,999 µs)', () => {
      expect(validateSetting('exposure_time', 1)).toBeNull()
      expect(validateSetting('exposure_time', 500)).toBeNull()
      expect(validateSetting('exposure_time', 999999)).toBeNull()
      expect(validateSetting('exposure_time', '1000')).toBeNull() // string ok
      expect(validateSetting('exposure_time', 0)).not.toBeNull() // must be > 0
      expect(validateSetting('exposure_time', 1000000)).not.toBeNull() // must be < 1s
    })

    it('should validate focus_peaking_intensity (50 - 200)', () => {
      expect(validateSetting('focus_peaking_intensity', 50)).toBeNull()
      expect(validateSetting('focus_peaking_intensity', 100)).toBeNull()
      expect(validateSetting('focus_peaking_intensity', 200)).toBeNull()
      expect(validateSetting('focus_peaking_intensity', 49)).not.toBeNull()
      expect(validateSetting('focus_peaking_intensity', 201)).not.toBeNull()
    })

    it('should validate focus_peaking_colour (green, red, yellow, cyan, magenta)', () => {
      const validColors = ['green', 'red', 'yellow', 'cyan', 'magenta']
      validColors.forEach(color => {
        expect(validateSetting('focus_peaking_colour', color)).toBeNull()
        expect(validateSetting('focus_peaking_colour', color.toUpperCase())).toBeNull() // case-insensitive
      })
      expect(validateSetting('focus_peaking_colour', 'blue')).not.toBeNull()
      expect(validateSetting('focus_peaking_colour', 'white')).not.toBeNull()
    })

    it('should validate focus_peaking_color (American spelling)', () => {
      const validColors = ['green', 'red', 'yellow', 'cyan', 'magenta']
      validColors.forEach(color => {
        expect(validateSetting('focus_peaking_color', color)).toBeNull()
      })
      expect(validateSetting('focus_peaking_color', 'blue')).not.toBeNull()
    })

    it('should validate focus_peaking_algorithm (laplacian, sobel, canny)', () => {
      const validAlgorithms = ['laplacian', 'sobel', 'canny']
      validAlgorithms.forEach(algo => {
        expect(validateSetting('focus_peaking_algorithm', algo)).toBeNull()
        expect(validateSetting('focus_peaking_algorithm', algo.toUpperCase())).toBeNull() // case-insensitive
      })
      expect(validateSetting('focus_peaking_algorithm', 'prewitt')).not.toBeNull()
    })
  })

  describe('validateSetting - camelCase key conversion', () => {
    it('should convert camelCase keys to snake_case before validation', () => {
      // colourGainRed → colour_gains_red
      expect(validateSetting('colourGainRed', 2.5)).toBeNull()
      expect(validateSetting('colourGainRed', 0.5)).not.toBeNull() // invalid

      // exposureTime → exposure_time
      expect(validateSetting('exposureTime', 500)).toBeNull()
      expect(validateSetting('exposureTime', 2000000)).not.toBeNull() // invalid

      // focusPeakingEnabled → focus_peaking_enabled
      expect(validateSetting('focusPeakingEnabled', 'true')).toBeNull()
      expect(validateSetting('focusPeakingEnabled', '1')).not.toBeNull() // invalid
    })

    it('should return null for unknown settings (not in liveview scope)', () => {
      // Settings not in LIVEVIEW_VALIDATION_RULES should be skipped
      expect(validateSetting('unknown_setting', 'anything')).toBeNull()
      expect(validateSetting('random_key', 123)).toBeNull()
    })
  })

  describe('validatePresetSettings', () => {
    it('should return empty array for valid settings', () => {
      const validSettings = {
        sharpness: 2.0,
        brightness: 0.5,
        contrast: 1.0,
        saturation: 1.0,
        exposure_time: 500,
        analogue_gain: 2.0,
        colour_gains_red: 2.259,
        colour_gains_blue: 1.5,
        focus_peaking_enabled: 'true',
        af_mode: 1
      }

      const errors = validatePresetSettings(validSettings)
      expect(errors).toEqual([])
    })

    it('should detect multiple invalid settings', () => {
      const invalidSettings = {
        sharpness: 5.0, // invalid (max 4.0)
        brightness: 2.0, // invalid (max 1.0)
        colour_gains_red: 0.5, // invalid (min 1.0)
        exposure_time: 2000000, // invalid (max 999,999)
        af_mode: 99 // invalid (max 2)
      }

      const errors = validatePresetSettings(invalidSettings)
      expect(errors.length).toBe(5)
      expect(errors.every(e => e.key && e.value !== undefined && e.message)).toBe(true)
    })

    it('should work with camelCase keys', () => {
      const invalidSettings = {
        colourGainRed: 0.5, // invalid (min 1.0)
        exposureTime: 2000000, // invalid (max 999,999)
        afMode: 99 // invalid (max 2)
      }

      const errors = validatePresetSettings(invalidSettings)
      expect(errors.length).toBe(3)
      expect(errors[0].key).toBe('colour_gains_red') // converted to snake_case
      expect(errors[1].key).toBe('exposure_time')
      expect(errors[2].key).toBe('af_mode')
    })

    it('should skip validation for unknown settings', () => {
      const mixedSettings = {
        sharpness: 5.0, // invalid
        unknown_setting: 'anything', // skip (not in validation rules)
        brightness: 0.5, // valid
        random_key: 123 // skip
      }

      const errors = validatePresetSettings(mixedSettings)
      expect(errors.length).toBe(1)
      expect(errors[0].key).toBe('sharpness')
    })
  })

  describe('formatValidationErrors', () => {
    it('should return empty string for no errors', () => {
      expect(formatValidationErrors([])).toBe('')
    })

    it('should format single error', () => {
      const errors = [
        { key: 'sharpness', value: 5.0, message: 'Sharpness must be between 0.0 and 4.0' }
      ]

      const formatted = formatValidationErrors(errors)
      expect(formatted).toContain('1 error')
      expect(formatted).toContain('sharpness = 5') // JavaScript converts 5.0 to 5
      expect(formatted).toContain('Sharpness must be between 0.0 and 4.0')
    })

    it('should format multiple errors', () => {
      const errors = [
        { key: 'sharpness', value: 5.0, message: 'Sharpness must be between 0.0 and 4.0' },
        { key: 'brightness', value: 2.0, message: 'Brightness must be between -1.0 and 1.0' },
        { key: 'colour_gains_red', value: 0.5, message: 'Red colour gain must be between 1.0 and 4.0' }
      ]

      const formatted = formatValidationErrors(errors)
      expect(formatted).toContain('3 errors')
      expect(formatted).toContain('1. sharpness = 5') // JavaScript converts 5.0 to 5
      expect(formatted).toContain('2. brightness = 2') // JavaScript converts 2.0 to 2
      expect(formatted).toContain('3. colour_gains_red = 0.5')
    })

    it('should truncate errors beyond maxErrors limit', () => {
      const errors = Array.from({ length: 10 }, (_, i) => ({
        key: `setting_${i}`,
        value: i,
        message: `Error message ${i}`
      }))

      const formatted = formatValidationErrors(errors, 3)
      expect(formatted).toContain('10 errors')
      expect(formatted).toContain('1. setting_0 = 0')
      expect(formatted).toContain('2. setting_1 = 1')
      expect(formatted).toContain('3. setting_2 = 2')
      expect(formatted).toContain('... and 7 more errors')
      expect(formatted).not.toContain('setting_3')
    })
  })
})
