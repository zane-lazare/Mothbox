/**
 * TanStack Query key constants
 * Centralized query keys for cache invalidation and consistency
 */

export const QUERY_KEYS = {
  // Photo/Gallery queries
  PHOTOS_INFINITE: ['photos', 'infinite'] as const,
  PHOTOS: ['photos'] as const,
  PHOTO_LOCATIONS: ['photo-locations'] as const,
  PHOTO_METADATA: (path: string) => ['photo-metadata', path] as const,
  SERIES: ['photo-series'] as const,

  // Search queries
  SEARCH_PHOTOS: (query: string) => ['search', 'photos', query] as const,
  SEARCH_TAGS: ['search', 'tags'] as const,
  SEARCH_SPECIES: ['search', 'species'] as const,

  // Camera queries
  CAMERA_SETTINGS: ['camera-settings'] as const,
  CAMERA_PRESETS: ['camera-presets'] as const,
  PRESETS: ['camera-presets'] as const,  // Alias for compatibility
  LIVEVIEW_SETTINGS: ['liveview-settings'] as const,
  WEBUI_SETTINGS: ['liveview-settings'] as const,  // Alias for compatibility

  // System queries
  SYSTEM_INFO: ['system', 'info'] as const,
  SYSTEM_STATUS: ['system', 'status'] as const,
  DIAGNOSTIC_INFO: ['system', 'diagnostic'] as const,

  // GPIO/Hardware queries
  GPIO_STATUS: ['gpio-status'] as const,
  GPIO_HEALTH: ['gpio-health'] as const,
  HARDWARE_CONFIG: ['hardware-config'] as const,
  CONTROLS: ['controls'] as const,

  // Scheduler queries
  SCHEDULES: ['schedules'] as const,
  SCHEDULE: (id: string) => ['schedule', id] as const,
  ACTIVE_SCHEDULE: ['active-schedule'] as const,
  SCHEDULE_PREVIEW: (id: string) => ['schedule-preview', id] as const,
  NEXT_ACTIONS: ['next-actions'] as const,
  BUILTIN_SCHEDULES: ['builtin-schedules'] as const,
  SCHEDULE_CONFLICTS: ['schedule-conflicts'] as const,

  // Export queries
  EXPORT_JOBS: ['export-jobs'] as const,
  EXPORT_JOB: (id: string) => ['export-job', id] as const,
  EXPORT_PRESETS: ['export-presets'] as const,

  // Filter/Preset queries
  FILTER_PRESETS: ['filter-presets'] as const,
  PREFERENCES: ['preferences'] as const,

  // Deployment queries
  DEPLOYMENTS: ['deployments'] as const,
  DEPLOYMENT: (path: string) => ['deployment', path] as const,

  // GPS queries
  GPS_STATUS: ['gps-status'] as const,
  GPS_CONFIG: ['gps-config'] as const,
  GPS_EXIF_CONFIG: ['gps-exif-config'] as const,
  GPS_EXIF_STATUS: ['gps-exif-status'] as const,

  // Tags and Species
  TAGS: ['tags'] as const,
  SPECIES: ['species'] as const,
} as const

export type QueryKeys = typeof QUERY_KEYS
