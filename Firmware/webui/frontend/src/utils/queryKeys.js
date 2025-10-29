/**
 * React Query Keys - Centralized Definition
 *
 * This file provides a single source of truth for all React Query cache keys
 * used throughout the application. Using constants prevents typos and makes
 * refactoring safer.
 *
 * Naming Convention:
 * ------------------
 * 1. Simple plural nouns for collections:
 *    - ['photos'], ['presets'], ['preferences'], ['controls']
 *    - Use when referring to a list/collection of items
 *
 * 2. Kebab-case for compound names:
 *    - ['camera-settings'], ['system-status'], ['gps-config']
 *    - Use for settings, status, config, and other compound concepts
 *
 * Why this convention?
 * - Simple plurals are natural and readable for collections
 * - Kebab-case is consistent with URL patterns and easy to read
 * - Avoids confusion with camelCase (which doesn't match the hyphenated pattern)
 *
 * Usage:
 * ------
 * import { QUERY_KEYS } from '../utils/queryKeys'
 *
 * // In useQuery:
 * const { data } = useQuery({
 *   queryKey: QUERY_KEYS.PHOTOS,
 *   queryFn: getPhotos
 * })
 *
 * // In mutations:
 * queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)
 */

export const QUERY_KEYS = {
  // Collections (simple plural nouns)
  PHOTOS: ['photos'],
  PRESETS: ['presets'],
  PREFERENCES: ['preferences'],
  CONTROLS: ['controls'],
  CRON_JOBS: ['cron-jobs'],

  // Status queries (kebab-case compound names)
  SYSTEM_STATUS: ['system-status'],
  POWER_STATUS: ['power-status'],
  GPIO_STATUS: ['gpio-status'],
  SCHEDULER_STATUS: ['scheduler-status'],
  GPS_STATUS: ['gps-status'],

  // Settings and configuration (kebab-case compound names)
  CAMERA_SETTINGS: ['camera-settings'],
  WEBUI_SETTINGS: ['webui-settings'],
  GPS_CONFIG: ['gps-config'],

  // System information (kebab-case compound names)
  SYSTEM_INFO: ['system-info'],
  DIAGNOSTIC_INFO: ['diagnostic-info'],
}
