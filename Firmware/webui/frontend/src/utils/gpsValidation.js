/**
 * GPS configuration validation utilities
 */

/**
 * Validate GPS device path
 * @param {string} devicePath - The GPS device path to validate
 * @returns {{valid: boolean, error: string|null}} Validation result
 */
export const validateDevicePath = (devicePath) => {
  if (!devicePath || devicePath.trim() === '') {
    return { valid: false, error: 'Device path cannot be empty' }
  }

  // Must start with /dev/
  if (!devicePath.startsWith('/dev/')) {
    return { valid: false, error: 'Device path must start with /dev/' }
  }

  // Common GPS device patterns
  const validPatterns = [
    /^\/dev\/ttyAMA\d+$/,     // Raspberry Pi UART
    /^\/dev\/ttyS\d+$/,       // Standard serial port
    /^\/dev\/ttyUSB\d+$/,     // USB serial adapter
    /^\/dev\/serial\d+$/,     // Generic serial
  ]

  const isValid = validPatterns.some(pattern => pattern.test(devicePath))

  if (!isValid) {
    return {
      valid: false,
      error: 'Invalid device path format. Expected /dev/ttyAMA0, /dev/ttyUSB0, etc.'
    }
  }

  return { valid: true, error: null }
}

/**
 * Validate GPS baudrate
 * @param {number} baudrate - The baudrate to validate
 * @returns {{valid: boolean, error: string|null}} Validation result
 */
export const validateBaudrate = (baudrate) => {
  const validBaudrates = [4800, 9600, 19200, 38400, 57600, 115200]

  if (!Number.isInteger(baudrate)) {
    return { valid: false, error: 'Baudrate must be an integer' }
  }

  if (!validBaudrates.includes(baudrate)) {
    return {
      valid: false,
      error: `Baudrate must be one of: ${validBaudrates.join(', ')}`
    }
  }

  return { valid: true, error: null }
}

/**
 * Validate GPS timeout
 * @param {number} timeout - The timeout in seconds
 * @returns {{valid: boolean, error: string|null}} Validation result
 */
export const validateTimeout = (timeout) => {
  if (!Number.isInteger(timeout) && !Number.isFinite(timeout)) {
    return { valid: false, error: 'Timeout must be a number' }
  }

  if (timeout < 5) {
    return { valid: false, error: 'Timeout must be at least 5 seconds' }
  }

  if (timeout > 300) {
    return { valid: false, error: 'Timeout cannot exceed 300 seconds (5 minutes)' }
  }

  return { valid: true, error: null }
}

/**
 * Validate complete GPS configuration
 * @param {Object} config - GPS configuration object
 * @returns {{valid: boolean, errors: Object}} Validation result with field-specific errors
 */
export const validateGpsConfig = (config) => {
  const errors = {}
  let isValid = true

  if (config.device !== undefined) {
    const deviceResult = validateDevicePath(config.device)
    if (!deviceResult.valid) {
      errors.device = deviceResult.error
      isValid = false
    }
  }

  if (config.baudrate !== undefined) {
    const baudrateResult = validateBaudrate(config.baudrate)
    if (!baudrateResult.valid) {
      errors.baudrate = baudrateResult.error
      isValid = false
    }
  }

  if (config.timeout !== undefined) {
    const timeoutResult = validateTimeout(config.timeout)
    if (!timeoutResult.valid) {
      errors.timeout = timeoutResult.error
      isValid = false
    }
  }

  return { valid: isValid, errors }
}
