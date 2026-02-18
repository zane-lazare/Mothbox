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
  PHOTOS_INFINITE: ['photos', 'infinite'],
  PHOTO_LOCATIONS: ['photo-locations'],
  SERIES: ['series'],
  PRESETS: ['presets'],
  PREFERENCES: ['preferences'],
  CONTROLS: ['controls'],
  CRON_JOBS: ['cron-jobs'],

  // Status queries (kebab-case compound names)
  SYSTEM_STATUS: ['system-status'],
  POWER_STATUS: ['power-status'],
  GPIO_STATUS: ['gpio-status'],
  GPIO_HEALTH: ['gpio', 'health'],
  SCHEDULER_STATUS: ['scheduler-status'],
  GPS_STATUS: ['gps-status'],

  // Settings and configuration (kebab-case compound names)
  CAMERA_SETTINGS: ['camera-settings'],
  WEBUI_SETTINGS: ['webui-settings'],
  GPS_CONFIG: ['gps-config'],
  GPS_EXIF_STATUS: ['gps-exif-status'],
  GPS_EXIF_CONFIG: ['gps-exif-config'],

  // System information (kebab-case compound names)
  SYSTEM_INFO: ['system-info'],
  DIAGNOSTIC_INFO: ['diagnostic-info'],

  // Export Jobs (Issue #125)
  EXPORT_JOBS: ['export-jobs'],
  EXPORT_JOB: (id) => ['export-jobs', id],

  // Export Presets (Issue #125)
  EXPORT_PRESETS: ['export-presets'],
  EXPORT_PRESET: (name) => ['export-presets', name],

  // Deployment Metadata (Issue #125, Subtask 3)
  DEPLOYMENTS: ['deployments'],
  DEPLOYMENT: (directory) => ['deployment', directory],

  // Scheduler (Issue #221)
  SCHEDULES: ['schedules'],
  SCHEDULE: (id) => ['schedules', id],
  ACTIVE_SCHEDULE: ['schedules', 'active'],
  NEXT_ACTIONS: ['schedules', 'active', 'next-actions'],  // Issue #331
  SCHEDULE_PREVIEW: (id) => ['schedules', id, 'preview'],
  BUILTIN_SCHEDULES: ['schedules', 'builtin'],
  BUILTIN_ROUTINES: ['schedules', 'routines', 'builtin'],

  // Cron Validation (Issue #233)
  CRON_VALIDATION: (expression) => ['cron-validation', expression],
}
