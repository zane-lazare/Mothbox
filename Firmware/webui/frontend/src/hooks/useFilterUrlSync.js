import { useEffect, useRef } from 'react'
import { DATE_PRESETS } from '../utils/filterQueryBuilder'

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
}

const DEBOUNCE_MS = 300

/**
 * Parse URL search parameters to filter state object
 *
 * @param {URLSearchParams} searchParams - URL search parameters
 * @returns {Object|null} Filter state object or null if no filters in URL
 */
export function parseUrlToFilterState(searchParams) {
  let hasAnyFilter = false
  const filterState = {}

  // Date range
  const dateRangePreset = searchParams.get(URL_KEYS.dateRangePreset)
  const dateStart = searchParams.get(URL_KEYS.dateStart)
  const dateEnd = searchParams.get(URL_KEYS.dateEnd)

  if (dateRangePreset || dateStart || dateEnd) {
    const dateRange = {}
    let hasValidDate = false

    // Validate preset
    if (dateRangePreset && DATE_PRESETS[dateRangePreset]) {
      dateRange.preset = dateRangePreset
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
      filterState.dateRange = dateRange
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
    filterState.species = {}

    if (speciesParam) {
      const species = speciesParam
        .split(',')
        .map((s) => decodeURIComponent(s.trim()))
        .filter(Boolean)
      if (species.length > 0) {
        filterState.species.selected = species
      }
    }

    if (includeUnidentified === '1') {
      filterState.species.includeUnidentified = true
    }
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
      if (!filterState.cameraSettings) filterState.cameraSettings = {}
      filterState.cameraSettings.iso = parsed
    }
  }

  // Camera settings - Aperture range
  const apertureRange = searchParams.get(URL_KEYS.apertureRange)
  if (apertureRange) {
    const parsed = parseRangeParam(apertureRange, parseFloat)
    if (parsed) {
      hasAnyFilter = true
      if (!filterState.cameraSettings) filterState.cameraSettings = {}
      filterState.cameraSettings.aperture = parsed
    }
  }

  // Camera settings - Shutter speed range
  const shutterSpeedRange = searchParams.get(URL_KEYS.shutterSpeedRange)
  if (shutterSpeedRange) {
    const parsed = parseRangeParam(shutterSpeedRange, parseFloat)
    if (parsed) {
      hasAnyFilter = true
      if (!filterState.cameraSettings) filterState.cameraSettings = {}
      filterState.cameraSettings.shutterSpeed = parsed
    }
  }

  // Notes
  const hasNotesParam = searchParams.get(URL_KEYS.hasNotes)
  const notesKeywords = searchParams.get(URL_KEYS.notesKeywords)

  if (hasNotesParam !== null || notesKeywords) {
    hasAnyFilter = true
    filterState.notes = {}

    if (hasNotesParam === '1') {
      filterState.notes.hasNotes = true
    } else if (hasNotesParam === '0') {
      filterState.notes.hasNotes = false
    }

    if (notesKeywords) {
      filterState.notes.keywords = decodeURIComponent(notesKeywords)
    }
  }

  // Custom fields (f_cf_{fieldname}={value})
  const customFields = {}
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
 * @param {string} rangeStr - Range string in format "min-max"
 * @param {Function} parser - Parsing function (parseInt or parseFloat)
 * @returns {Object|null} Object with min/max properties or null if invalid
 */
function parseRangeParam(rangeStr, parser) {
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
 * @param {Object} filterState - Filter state object
 * @returns {URLSearchParams} URL search parameters
 */
export function serializeFilterStateToUrl(filterState) {
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
  if (filterState.tags?.selected?.length > 0) {
    const tags = filterState.tags.selected.map((t) => encodeURIComponent(t)).join(',')
    params.set(URL_KEYS.tags, tags)

    if (filterState.tags.matchMode) {
      params.set(URL_KEYS.tagMatchMode, filterState.tags.matchMode)
    }
  }

  // Species
  if (filterState.species) {
    if (filterState.species.selected?.length > 0) {
      const species = filterState.species.selected.map((s) => encodeURIComponent(s)).join(',')
      params.set(URL_KEYS.species, species)
    }
    if (filterState.species.includeUnidentified) {
      params.set(URL_KEYS.includeUnidentified, '1')
    }
  }

  // File types
  if (filterState.fileTypes?.selected?.length > 0) {
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
 * @param {Object} range - Range object with min/max properties
 * @returns {string|null} Range string or null if invalid
 */
function serializeRange(range) {
  if (!range) return null

  const min = range.min !== null && range.min !== undefined ? String(range.min) : ''
  const max = range.max !== null && range.max !== undefined ? String(range.max) : ''

  if (!min && !max) return null

  return `${min}-${max}`
}

/**
 * Check if two filter states are equal (for preventing sync loops)
 *
 * @param {Object} state1 - First filter state
 * @param {Object} state2 - Second filter state
 * @returns {boolean} True if states are equal
 */
function areFilterStatesEqual(state1, state2) {
  // Simple JSON comparison for deep equality
  // This works because filter state is a plain object
  return JSON.stringify(state1) === JSON.stringify(state2)
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
 * @param {Object} filterState - Current filter state from context
 * @param {Function} loadState - Function to load state into context
 *
 * @example
 * // In a component that uses filter context
 * const { filterState, loadFilterState } = useFilterContext()
 * useFilterUrlSync(filterState, loadFilterState)
 */
export function useFilterUrlSync(filterState, loadState) {
  const isInitialMount = useRef(true)
  const debounceTimer = useRef(null)
  const lastSyncedState = useRef(null)

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
    debounceTimer.current = setTimeout(() => {
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
