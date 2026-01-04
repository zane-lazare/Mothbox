/**
 * Constants for RoutineEditor components
 */

export const ROUTINE_LIMITS = {
  NAME_MAX_LENGTH: 200,
  DESCRIPTION_MAX_LENGTH: 2000,
}

export const ACTION_LIMITS = {
  DESCRIPTION_MAX_LENGTH: 500,
  MIN_OFFSET_MINUTES: 0,
  MAX_OFFSET_MINUTES: 1440, // 24 hours
}

/**
 * Available action types and their corresponding action names.
 * Update this when new action types are added to the backend.
 */
export const ACTION_NAMES = {
  gpio: ['attract_on', 'attract_off', 'flash_on', 'flash_off'],
  camera: ['takephoto'],
  gps_sync: ['sync'],
  service: ['backup', 'update_display'],
}
