import { useEffect, useRef } from 'react'
import { DATE_PRESETS } from '../utils/filterQueryBuilder'
import type { FilterState, DateRangeFilter, TagFilter, SpeciesFilter, FileTypeFilter, CameraSettingsFilter, NotesFilter, CustomFieldsFilter } from '../types'

/**
 * Filter URL Synchronization Hook
 *
 * This hook provides bidirectional sync between filter state and URL parameters.
 *
 * DESIGN DECISION: Filter state intentionally persists in URL when navigating away.
 * This enables:
 * - Bookmarkable filtered views (users can save/share specific filter combinations)
 * - Browser back/forward navigation through filter states
 * - Page refresh preserves current filters
 *
 * If you need to clear filters when leaving Gallery, call clearAllFilters() from
 * FilterContext before navigation, or use the "Clear All" button in the UI.
 */

/**
 * URL parameter keys for filter state synchronization
 */
const URL_KEYS = {
  // Date range
  dateRangePreset: 'f_dr',
  dateStart: 'f_ds',
  dateEnd: 'f_de',

  // Tags
  tags: 'f_tags',
  tagMatchMode: 'f_tm',

  // Species
  species: 'f_species',
  includeUnidentified: 'f_ui',

  // File types
  fileTypes: 'f_ft',

  // Camera settings
  isoRange: 'f_iso',
  apertureRange: 'f_ap',
  shutterSpeedRange: 'f_ss',

  // Notes
  hasNotes: 'f_hn',
  notesKeywords: 'f_nk',

  // Custom fields (dynamic, prefixed with f_cf_)
  customFieldPrefix: 'f_cf_',
} as const

const DEBOUNCE_MS = 300
const MAX_URL_PARAMS = 50

interface RangeParam {
  min: number | null
  max: number | null
}

/**
 * Parse URL search parameters to filter state object
 *
 * @param searchParams - URL search parameters
 * @returns Filter state object or null if no filters in URL
 */
export function parseUrlToFilterState(searchParams: URLSearchParams): Partial<FilterState> | null {
  // Prevent memory exhaustion from malicious URLs with many parameters
  const paramCount = Array.from(searchParams.keys()).length
  if (paramCount > MAX_URL_PARAMS) {
    console.warn(
      `Too many URL filter parameters (${paramCount}), ignoring URL state`
    )
    return null
  }

  let hasAnyFilter = false
  const filterState: Partial<FilterState> = {}

  // Date range
  const dateRangePreset = searchParams.get(URL_KEYS.dateRangePreset)
  const dateStart = searchParams.get(URL_KEYS.dateStart)
  const dateEnd = searchParams.get(URL_KEYS.dateEnd)

  if (dateRangePreset || dateStart || dateEnd) {
    const dateRange: Partial<DateRangeFilter> = {}
    let hasValidDate = false

    // Validate preset
    if (dateRangePreset && DATE_PRESETS[dateRangePreset as keyof typeof DATE_PRESETS]) {
      dateRange.preset = dateRangePreset as DateRangeFilter['preset']
      hasValidDate = true
    }

    // Parse dates (YYYY-MM-DD format)
    if (dateStart && /^\d{4}-\d{2}-\d{2}$/.test(dateStart)) {
      dateRange.startDate = dateStart
      hasValidDate = true
    }
    if (dateEnd && /^\d{4}-\d{2}-\d{2}$/.test(dateEnd)) {
      dateRange.endDate = dateEnd
      hasValidDate = true
    }

    // Only add dateRange if we found valid values
    if (hasValidDate) {
      filterState.dateRange = dateRange as DateRangeFilter
      hasAnyFilter = true
    }
  }

  // Tags
  const tagsParam = searchParams.get(URL_KEYS.tags)
  const tagMatchMode = searchParams.get(URL_KEYS.tagMatchMode)

  if (tagsParam) {
    hasAnyFilter = true
    const tags = tagsParam.split(',').map((t) => decodeURIComponent(t.trim())).filter(Boolean)
    if (tags.length > 0) {
      filterState.tags = {
        selected: tags,
        matchMode: tagMatchMode === 'all' ? 'all' : 'any',
      }
    }
  }

  // Species
  const speciesParam = searchParams.get(URL_KEYS.species)
  const includeUnidentified = searchParams.get(URL_KEYS.includeUnidentified)

  if (speciesParam || includeUnidentified) {
    hasAnyFilter = true
    const species: Partial<SpeciesFilter> = {}

    if (speciesParam) {
      const speciesList = speciesParam
        .split(',')
        .map((s) => decodeURIComponent(s.trim()))
        .filter(Boolean)
      if (speciesList.length > 0) {
        species.selected = speciesList
      }
    }

    if (includeUnidentified === '1') {
      species.includeUnidentified = true
    }

    filterState.species = species as SpeciesFilter
  }

  // File types
  const fileTypesParam = searchParams.get(URL_KEYS.fileTypes)
  if (fileTypesParam) {
    hasAnyFilter = true
    const fileTypes = fileTypesParam.split(',').map((ft) => ft.trim().toLowerCase()).filter(Boolean)
    if (fileTypes.length > 0) {
      filterState.fileTypes = { selected: fileTypes }
    }
  }

  // Camera settings - ISO range
  const isoRange = searchParams.get(URL_KEYS.isoRange)
  if (isoRange) {
    const parsed = parseRangeParam(isoRange, parseInt)
    if (parsed) {
      hasAnyFilter = true
      if (!filterState.cameraSettings) filterState.cameraSettings = {} as CameraSettingsFilter
      filterState.cameraSettings.iso = parsed
    }
  }

  // Camera settings - Aperture range
  const apertureRange = searchParams.get(URL_KEYS.apertureRange)
  if (apertureRange) {
    const parsed = parseRangeParam(apertureRange, parseFloat)
    if (parsed) {
      hasAnyFilter = true
      if (!filterState.cameraSettings) filterState.cameraSettings = {} as CameraSettingsFilter
      filterState.cameraSettings.aperture = parsed
    }
  }

  // Camera settings - Shutter speed range
  const shutterSpeedRange = searchParams.get(URL_KEYS.shutterSpeedRange)
  if (shutterSpeedRange) {
    const parsed = parseRangeParam(shutterSpeedRange, parseFloat)
    if (parsed) {
      hasAnyFilter = true
      if (!filterState.cameraSettings) filterState.cameraSettings = {} as CameraSettingsFilter
      filterState.cameraSettings.shutterSpeed = parsed
    }
  }

  // Notes
  const hasNotesParam = searchParams.get(URL_KEYS.hasNotes)
  const notesKeywords = searchParams.get(URL_KEYS.notesKeywords)

  if (hasNotesParam !== null || notesKeywords) {
    hasAnyFilter = true
    const notes: Partial<NotesFilter> = {}

    if (hasNotesParam === '1') {
      notes.hasNotes = true
    } else if (hasNotesParam === '0') {
      notes.hasNotes = false
    }

    if (notesKeywords) {
      notes.keywords = decodeURIComponent(notesKeywords)
    }

    filterState.notes = notes as NotesFilter
  }

  // Custom fields (f_cf_{fieldname}={value})
  const customFields: CustomFieldsFilter = {}
  for (const [key, value] of searchParams.entries()) {
    if (key.startsWith(URL_KEYS.customFieldPrefix)) {
      const fieldName = key.substring(URL_KEYS.customFieldPrefix.length)
      if (fieldName && value) {
        customFields[fieldName] = decodeURIComponent(value)
        hasAnyFilter = true
      }
    }
  }

  if (Object.keys(customFields).length > 0) {
    filterState.customFields = customFields
  }

  return hasAnyFilter ? filterState : null
}

/**
 * Parse a range parameter (e.g., "100-3200" or "2.8-8")
 *
 * @param rangeStr - Range string in format "min-max"
 * @param parser - Parsing function (parseInt or parseFloat)
 * @returns Object with min/max properties or null if invalid
 */
function parseRangeParam(
  rangeStr: string,
  parser: typeof parseInt | typeof parseFloat
): RangeParam | null {
  if (!rangeStr) return null

  const parts = rangeStr.split('-')
  if (parts.length !== 2) return null

  const min = parts[0] ? parser(parts[0], 10) : null
  const max = parts[1] ? parser(parts[1], 10) : null

  // Validate parsed values
  if ((min !== null && isNaN(min)) || (max !== null && isNaN(max))) {
    return null
  }

  return { min, max }
}

/**
 * Serialize filter state to URL search parameters
 *
 * @param filterState - Filter state object
 * @returns URL search parameters
 */
export function serializeFilterStateToUrl(filterState: Partial<FilterState>): URLSearchParams {
  const params = new URLSearchParams()

  if (!filterState) return params

  // Date range
  if (filterState.dateRange) {
    if (filterState.dateRange.preset) {
      params.set(URL_KEYS.dateRangePreset, filterState.dateRange.preset)
    }
    if (filterState.dateRange.startDate) {
      params.set(URL_KEYS.dateStart, filterState.dateRange.startDate)
    }
    if (filterState.dateRange.endDate) {
      params.set(URL_KEYS.dateEnd, filterState.dateRange.endDate)
    }
  }

  // Tags
  if (filterState.tags?.selected?.length && filterState.tags.selected.length > 0) {
    const tags = filterState.tags.selected.map((t) => encodeURIComponent(t)).join(',')
    params.set(URL_KEYS.tags, tags)

    if (filterState.tags.matchMode) {
      params.set(URL_KEYS.tagMatchMode, filterState.tags.matchMode)
    }
  }

  // Species
  if (filterState.species) {
    if (filterState.species.selected?.length && filterState.species.selected.length > 0) {
      const species = filterState.species.selected.map((s) => encodeURIComponent(s)).join(',')
      params.set(URL_KEYS.species, species)
    }
    if (filterState.species.includeUnidentified) {
      params.set(URL_KEYS.includeUnidentified, '1')
    }
  }

  // File types
  if (filterState.fileTypes?.selected?.length && filterState.fileTypes.selected.length > 0) {
    const fileTypes = filterState.fileTypes.selected.join(',')
    params.set(URL_KEYS.fileTypes, fileTypes)
  }

  // Camera settings
  if (filterState.cameraSettings) {
    // ISO range
    if (filterState.cameraSettings.iso) {
      const range = serializeRange(filterState.cameraSettings.iso)
      if (range) params.set(URL_KEYS.isoRange, range)
    }

    // Aperture range
    if (filterState.cameraSettings.aperture) {
      const range = serializeRange(filterState.cameraSettings.aperture)
      if (range) params.set(URL_KEYS.apertureRange, range)
    }

    // Shutter speed range
    if (filterState.cameraSettings.shutterSpeed) {
      const range = serializeRange(filterState.cameraSettings.shutterSpeed)
      if (range) params.set(URL_KEYS.shutterSpeedRange, range)
    }
  }

  // Notes
  if (filterState.notes) {
    if (filterState.notes.hasNotes === true) {
      params.set(URL_KEYS.hasNotes, '1')
    } else if (filterState.notes.hasNotes === false) {
      params.set(URL_KEYS.hasNotes, '0')
    }

    if (filterState.notes.keywords) {
      params.set(URL_KEYS.notesKeywords, encodeURIComponent(filterState.notes.keywords))
    }
  }

  // Custom fields
  if (filterState.customFields) {
    for (const [fieldName, value] of Object.entries(filterState.customFields)) {
      if (value !== null && value !== undefined && value !== '') {
        const key = `${URL_KEYS.customFieldPrefix}${fieldName}`
        params.set(key, encodeURIComponent(String(value)))
      }
    }
  }

  return params
}

/**
 * Serialize a range object to string format "min-max"
 *
 * @param range - Range object with min/max properties
 * @returns Range string or null if invalid
 */
function serializeRange(range: RangeParam): string | null {
  if (!range) return null

  const min = range.min !== null && range.min !== undefined ? String(range.min) : ''
  const max = range.max !== null && range.max !== undefined ? String(range.max) : ''

  if (!min && !max) return null

  return `${min}-${max}`
}

/**
 * Check if two filter states are equal (for preventing sync loops)
 *
 * Uses explicit property comparison instead of JSON.stringify to avoid:
 * - Property order sensitivity ({a:1, b:2} vs {b:2, a:1})
 * - Special value handling (undefined, NaN, Infinity)
 * - Performance overhead of serialization
 *
 * @param state1 - First filter state
 * @param state2 - Second filter state
 * @returns True if states are equal
 */
function areFilterStatesEqual(state1: Partial<FilterState> | null, state2: Partial<FilterState> | null): boolean {
  // Fast path: same reference
  if (state1 === state2) return true

  // Null/undefined check
  if (!state1 || !state2) return !state1 && !state2

  // Compare dateRange
  if (!areDateRangesEqual(state1.dateRange, state2.dateRange)) return false

  // Compare tags (array order independent)
  if (!areTagsEqual(state1.tags, state2.tags)) return false

  // Compare species
  if (!areSpeciesEqual(state1.species, state2.species)) return false

  // Compare fileTypes
  if (!areArraySelectionsEqual(state1.fileTypes?.selected, state2.fileTypes?.selected)) return false

  // Compare cameraSettings
  if (!areCameraSettingsEqual(state1.cameraSettings, state2.cameraSettings)) return false

  // Compare notes
  if (!areNotesEqual(state1.notes, state2.notes)) return false

  // Compare customFields
  if (!areCustomFieldsEqual(state1.customFields, state2.customFields)) return false

  return true
}

// Helper: Compare date ranges
function areDateRangesEqual(dr1?: Partial<DateRangeFilter>, dr2?: Partial<DateRangeFilter>): boolean {
  if (!dr1 && !dr2) return true
  if (!dr1 || !dr2) return false
  return dr1.preset === dr2.preset &&
         dr1.startDate === dr2.startDate &&
         dr1.endDate === dr2.endDate
}

// Helper: Compare tags (sort arrays for order-independent comparison)
function areTagsEqual(t1?: Partial<TagFilter>, t2?: Partial<TagFilter>): boolean {
  if (!t1 && !t2) return true
  if (!t1 || !t2) return false
  if (t1.matchMode !== t2.matchMode) return false
  return areArraySelectionsEqual(t1.selected, t2.selected)
}

// Helper: Compare species
function areSpeciesEqual(s1?: Partial<SpeciesFilter>, s2?: Partial<SpeciesFilter>): boolean {
  if (!s1 && !s2) return true
  if (!s1 || !s2) return false
  if (s1.includeUnidentified !== s2.includeUnidentified) return false
  return areArraySelectionsEqual(s1.selected, s2.selected)
}

// Helper: Compare sorted arrays (order-independent)
function areArraySelectionsEqual(arr1?: string[], arr2?: string[]): boolean {
  if (!arr1 && !arr2) return true
  if (!arr1 || !arr2) return false
  if (arr1.length !== arr2.length) return false
  const sorted1 = [...arr1].sort()
  const sorted2 = [...arr2].sort()
  return sorted1.every((v, i) => v === sorted2[i])
}

// Helper: Compare camera settings (range objects)
function areCameraSettingsEqual(cs1?: Partial<CameraSettingsFilter>, cs2?: Partial<CameraSettingsFilter>): boolean {
  if (!cs1 && !cs2) return true
  if (!cs1 || !cs2) return false
  return areRangesEqual(cs1.iso, cs2.iso) &&
         areRangesEqual(cs1.aperture, cs2.aperture) &&
         areRangesEqual(cs1.shutterSpeed, cs2.shutterSpeed)
}

// Helper: Compare range objects
function areRangesEqual(r1?: RangeParam, r2?: RangeParam): boolean {
  if (!r1 && !r2) return true
  if (!r1 || !r2) return false
  return r1.min === r2.min && r1.max === r2.max
}

// Helper: Compare notes
function areNotesEqual(n1?: Partial<NotesFilter>, n2?: Partial<NotesFilter>): boolean {
  if (!n1 && !n2) return true
  if (!n1 || !n2) return false
  return n1.hasNotes === n2.hasNotes && n1.keywords === n2.keywords
}

// Helper: Compare custom fields objects
function areCustomFieldsEqual(cf1?: CustomFieldsFilter, cf2?: CustomFieldsFilter): boolean {
  if (!cf1 && !cf2) return true
  if (!cf1 || !cf2) return false
  const keys1 = Object.keys(cf1)
  const keys2 = Object.keys(cf2)
  if (keys1.length !== keys2.length) return false
  return keys1.every(key => cf1[key] === cf2[key])
}

/**
 * Custom hook for bidirectional URL <-> filter state synchronization
 *
 * Synchronizes filter state with URL query parameters:
 * - On mount: Reads URL params and loads into filter state
 * - On filter state change: Updates URL params (debounced)
 *
 * Uses window.history.replaceState to avoid polluting browser history.
 *
 * @param filterState - Current filter state from context
 * @param loadState - Function to load state into context
 *
 * @example
 * // In a component that uses filter context
 * const { filterState, loadFilterState } = useFilterContext()
 * useFilterUrlSync(filterState, loadFilterState)
 */
export function useFilterUrlSync(
  filterState: Partial<FilterState>,
  loadState: (state: Partial<FilterState>) => void
): void {
  const isInitialMount = useRef(true)
  const debounceTimer = useRef<number | null>(null)
  const lastSyncedState = useRef<Partial<FilterState> | null>(null)

  // On mount: Parse URL and load into state
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false

      const searchParams = new URLSearchParams(window.location.search)
      const urlFilterState = parseUrlToFilterState(searchParams)

      if (urlFilterState) {
        // Only load if state is different from current
        if (!areFilterStatesEqual(urlFilterState, filterState)) {
          lastSyncedState.current = urlFilterState
          loadState(urlFilterState)
        }
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // On filter state change: Update URL (debounced)
  useEffect(() => {
    // Skip if this is the initial mount
    if (isInitialMount.current) return

    // Skip if state hasn't changed (prevent loops)
    if (areFilterStatesEqual(filterState, lastSyncedState.current)) {
      return
    }

    // Clear existing timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }

    // Debounce URL update
    debounceTimer.current = window.setTimeout(() => {
      const params = serializeFilterStateToUrl(filterState)
      const newUrl = params.toString()
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname

      // Update URL without adding to history
      window.history.replaceState(null, '', newUrl)
      lastSyncedState.current = filterState
    }, DEBOUNCE_MS)

    // Cleanup timer on unmount
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current)
      }
    }
  }, [filterState])
}

// Export for testing
export { areFilterStatesEqual }
