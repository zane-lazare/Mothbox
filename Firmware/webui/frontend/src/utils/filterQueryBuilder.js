/**
 * Filter Query Builder
 *
 * Transforms filter state into FTS5 query strings compatible with the
 * Mothbox search API. Handles date ranges, tags, species, notes, and
 * custom fields.
 *
 * @module filterQueryBuilder
 */

/**
 * Date preset definitions with their range calculations
 */
export const DATE_PRESETS = {
  today: {
    label: 'Today',
    getRange: () => {
      const today = new Date()
      const dateStr = formatDateForQuery(today)
      return { startDate: dateStr, endDate: dateStr }
    },
  },
  '7days': {
    label: 'Last 7 Days',
    getRange: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 7)
      return { startDate: formatDateForQuery(start), endDate: formatDateForQuery(end) }
    },
  },
  '30days': {
    label: 'Last 30 Days',
    getRange: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 30)
      return { startDate: formatDateForQuery(start), endDate: formatDateForQuery(end) }
    },
  },
  '90days': {
    label: 'Last 90 Days',
    getRange: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 90)
      return { startDate: formatDateForQuery(start), endDate: formatDateForQuery(end) }
    },
  },
  thisMonth: {
    label: 'This Month',
    getRange: () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), now.getMonth(), 1)
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
      return { startDate: formatDateForQuery(start), endDate: formatDateForQuery(end) }
    },
  },
  lastMonth: {
    label: 'Last Month',
    getRange: () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const end = new Date(now.getFullYear(), now.getMonth(), 0)
      return { startDate: formatDateForQuery(start), endDate: formatDateForQuery(end) }
    },
  },
  thisYear: {
    label: 'This Year',
    getRange: () => {
      const now = new Date()
      const start = new Date(now.getFullYear(), 0, 1)
      const end = new Date(now.getFullYear(), 11, 31)
      return { startDate: formatDateForQuery(start), endDate: formatDateForQuery(end) }
    },
  },
}

/**
 * Format a Date object to YYYY-MM-DD string for query
 * @param {Date} date - Date to format
 * @returns {string} Formatted date string
 */
export function formatDateForQuery(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Escape special characters in search values for FTS5 queries
 * @param {string} value - Value to escape
 * @returns {string} Escaped value
 */
export function escapeQueryValue(value) {
  if (!value) return ''
  // Escape double quotes by doubling them
  return value.replace(/"/g, '""')
}

/**
 * Build date range query string
 * @param {Object} dateRange - Date range filter state
 * @param {string|null} dateRange.preset - Preset identifier
 * @param {string|null} dateRange.startDate - Start date (YYYY-MM-DD)
 * @param {string|null} dateRange.endDate - End date (YYYY-MM-DD)
 * @returns {string} Date query string or empty string
 */
export function buildDateQuery(dateRange) {
  if (!dateRange) return ''

  let startDate = dateRange.startDate
  let endDate = dateRange.endDate

  // If using a preset, calculate the range
  if (dateRange.preset && DATE_PRESETS[dateRange.preset]) {
    const range = DATE_PRESETS[dateRange.preset].getRange()
    startDate = range.startDate
    endDate = range.endDate
  }

  // Build query based on available dates
  if (startDate && endDate) {
    if (startDate === endDate) {
      return `date:${startDate}`
    }
    return `date:${startDate}..${endDate}`
  } else if (startDate) {
    return `date:>=${startDate}`
  } else if (endDate) {
    return `date:<=${endDate}`
  }

  return ''
}

/**
 * Build tag filter query string
 * @param {Object} tags - Tag filter state
 * @param {string[]} tags.selected - Selected tag names
 * @param {string} tags.matchMode - 'any' for OR, 'all' for AND
 * @returns {string} Tag query string or empty string
 */
export function buildTagQuery(tags) {
  if (!tags || !tags.selected || tags.selected.length === 0) {
    return ''
  }

  const tagQueries = tags.selected.map((tag) => `tag:"${escapeQueryValue(tag)}"`)

  if (tagQueries.length === 1) {
    return tagQueries[0]
  }

  const operator = tags.matchMode === 'all' ? ' AND ' : ' OR '
  return `(${tagQueries.join(operator)})`
}

/**
 * Build species filter query string
 * @param {Object} species - Species filter state
 * @param {string[]} species.selected - Selected species names
 * @param {boolean} species.includeUnidentified - Include photos without species
 * @returns {string} Species query string or empty string
 */
export function buildSpeciesQuery(species) {
  if (!species) return ''

  const parts = []

  // Add selected species
  if (species.selected && species.selected.length > 0) {
    const speciesQueries = species.selected.map(
      (s) => `species:"${escapeQueryValue(s)}"`
    )
    if (speciesQueries.length === 1) {
      parts.push(speciesQueries[0])
    } else {
      parts.push(`(${speciesQueries.join(' OR ')})`)
    }
  }

  // Note: includeUnidentified is handled differently - it's a filter flag
  // that affects result filtering, not the FTS query itself

  if (parts.length === 0) return ''
  return parts.join(' OR ')
}

/**
 * Build notes filter query string
 * @param {Object} notes - Notes filter state
 * @param {boolean|null} notes.hasNotes - Filter for photos with/without notes
 * @param {string} notes.keywords - Keywords to search in notes
 * @returns {string} Notes query string or empty string
 */
export function buildNotesQuery(notes) {
  if (!notes) return ''

  const parts = []

  // Keyword search in notes
  if (notes.keywords && notes.keywords.trim()) {
    const keywords = notes.keywords.trim()
    // If multiple words, wrap in quotes for phrase search
    if (keywords.includes(' ')) {
      parts.push(`notes:"${escapeQueryValue(keywords)}"`)
    } else {
      parts.push(`notes:${escapeQueryValue(keywords)}`)
    }
  }

  // Note: hasNotes filter is handled client-side as FTS5 doesn't support
  // "field exists" queries directly

  return parts.join(' AND ')
}

/**
 * Build custom fields query string
 * @param {Object} customFields - Custom fields filter state (key-value pairs)
 * @returns {string} Custom fields query string or empty string
 */
export function buildCustomFieldsQuery(customFields) {
  if (!customFields || Object.keys(customFields).length === 0) {
    return ''
  }

  const parts = []

  for (const [, value] of Object.entries(customFields)) {
    if (value !== null && value !== undefined && value !== '') {
      // Custom fields are stored in the 'custom' column in the search index
      // We search for the value in the custom fields content
      parts.push(`custom:"${escapeQueryValue(String(value))}"`)
    }
  }

  if (parts.length === 0) return ''
  if (parts.length === 1) return parts[0]
  return `(${parts.join(' AND ')})`
}

/**
 * Build complete filter query from filter state
 * @param {Object} filterState - Complete filter state object
 * @returns {string} Combined FTS5 query string
 */
export function buildFilterQuery(filterState) {
  if (!filterState) return ''

  const queryParts = []

  // Date range
  const dateQuery = buildDateQuery(filterState.dateRange)
  if (dateQuery) queryParts.push(dateQuery)

  // Tags
  const tagQuery = buildTagQuery(filterState.tags)
  if (tagQuery) queryParts.push(tagQuery)

  // Species
  const speciesQuery = buildSpeciesQuery(filterState.species)
  if (speciesQuery) queryParts.push(speciesQuery)

  // Notes
  const notesQuery = buildNotesQuery(filterState.notes)
  if (notesQuery) queryParts.push(notesQuery)

  // Custom fields
  const customQuery = buildCustomFieldsQuery(filterState.customFields)
  if (customQuery) queryParts.push(customQuery)

  // Join all parts with AND
  if (queryParts.length === 0) return ''
  if (queryParts.length === 1) return queryParts[0]
  return queryParts.join(' AND ')
}

/**
 * Combine user search query with filter query
 * @param {string} userQuery - User's text search query
 * @param {string} filterQuery - Generated filter query
 * @returns {string} Combined query string
 */
export function combineWithUserSearch(userQuery, filterQuery) {
  const trimmedUser = userQuery?.trim() || ''
  const trimmedFilter = filterQuery?.trim() || ''

  if (!trimmedUser && !trimmedFilter) return ''
  if (!trimmedUser) return trimmedFilter
  if (!trimmedFilter) return trimmedUser

  return `(${trimmedUser}) AND (${trimmedFilter})`
}

/**
 * Check if filter state has any active filters
 * @param {Object} filterState - Filter state to check
 * @returns {boolean} True if any filters are active
 */
export function hasActiveFilters(filterState) {
  if (!filterState) return false

  // Date range
  if (
    filterState.dateRange?.preset ||
    filterState.dateRange?.startDate ||
    filterState.dateRange?.endDate
  ) {
    return true
  }

  // Tags
  if (filterState.tags?.selected?.length > 0) {
    return true
  }

  // Species
  if (
    filterState.species?.selected?.length > 0 ||
    filterState.species?.includeUnidentified
  ) {
    return true
  }

  // File types
  if (filterState.fileTypes?.selected?.length > 0) {
    return true
  }

  // Camera settings
  if (filterState.cameraSettings) {
    const { iso, aperture, shutterSpeed } = filterState.cameraSettings
    if (iso?.min !== null || iso?.max !== null) return true
    if (aperture?.min !== null || aperture?.max !== null) return true
    if (shutterSpeed?.min !== null || shutterSpeed?.max !== null) return true
  }

  // Notes
  if (filterState.notes?.hasNotes !== null || filterState.notes?.keywords) {
    return true
  }

  // Custom fields
  if (filterState.customFields && Object.keys(filterState.customFields).length > 0) {
    const hasValue = Object.values(filterState.customFields).some(
      (v) => v !== null && v !== undefined && v !== ''
    )
    if (hasValue) return true
  }

  return false
}

/**
 * Count the number of active filter types
 * @param {Object} filterState - Filter state to count
 * @returns {number} Number of active filter types
 */
export function countActiveFilters(filterState) {
  if (!filterState) return 0

  let count = 0

  // Date range
  if (
    filterState.dateRange?.preset ||
    filterState.dateRange?.startDate ||
    filterState.dateRange?.endDate
  ) {
    count++
  }

  // Tags
  if (filterState.tags?.selected?.length > 0) {
    count++
  }

  // Species
  if (
    filterState.species?.selected?.length > 0 ||
    filterState.species?.includeUnidentified
  ) {
    count++
  }

  // File types
  if (filterState.fileTypes?.selected?.length > 0) {
    count++
  }

  // Camera settings (count as one if any are set)
  if (filterState.cameraSettings) {
    const { iso, aperture, shutterSpeed } = filterState.cameraSettings
    const hasIso = iso?.min !== null || iso?.max !== null
    const hasAperture = aperture?.min !== null || aperture?.max !== null
    const hasShutter = shutterSpeed?.min !== null || shutterSpeed?.max !== null
    if (hasIso || hasAperture || hasShutter) count++
  }

  // Notes
  if (filterState.notes?.hasNotes !== null || filterState.notes?.keywords) {
    count++
  }

  // Custom fields (count as one if any are set)
  if (filterState.customFields && Object.keys(filterState.customFields).length > 0) {
    const hasValue = Object.values(filterState.customFields).some(
      (v) => v !== null && v !== undefined && v !== ''
    )
    if (hasValue) count++
  }

  return count
}

/**
 * Get human-readable summary of active filters
 * @param {Object} filterState - Filter state to summarize
 * @returns {Array<{type: string, label: string, value: string}>} Filter summaries
 */
export function getActiveFilterSummaries(filterState) {
  if (!filterState) return []

  const summaries = []

  // Date range
  if (filterState.dateRange?.preset) {
    const preset = DATE_PRESETS[filterState.dateRange.preset]
    summaries.push({
      type: 'dateRange',
      label: 'Date',
      value: preset?.label || filterState.dateRange.preset,
    })
  } else if (filterState.dateRange?.startDate || filterState.dateRange?.endDate) {
    const start = filterState.dateRange.startDate || '...'
    const end = filterState.dateRange.endDate || '...'
    summaries.push({
      type: 'dateRange',
      label: 'Date',
      value: `${start} to ${end}`,
    })
  }

  // Tags
  if (filterState.tags?.selected?.length > 0) {
    const mode = filterState.tags.matchMode === 'all' ? 'all' : 'any'
    summaries.push({
      type: 'tags',
      label: 'Tags',
      value: `${filterState.tags.selected.length} (${mode})`,
    })
  }

  // Species
  if (filterState.species?.selected?.length > 0) {
    summaries.push({
      type: 'species',
      label: 'Species',
      value: `${filterState.species.selected.length} selected`,
    })
  }
  if (filterState.species?.includeUnidentified) {
    summaries.push({
      type: 'species',
      label: 'Species',
      value: 'Include unidentified',
    })
  }

  // File types
  if (filterState.fileTypes?.selected?.length > 0) {
    summaries.push({
      type: 'fileTypes',
      label: 'File Type',
      value: filterState.fileTypes.selected.join(', ').toUpperCase(),
    })
  }

  // Camera settings
  if (filterState.cameraSettings) {
    const { iso, aperture, shutterSpeed } = filterState.cameraSettings
    if (iso?.min !== null || iso?.max !== null) {
      const min = iso?.min ?? 'any'
      const max = iso?.max ?? 'any'
      summaries.push({
        type: 'cameraSettings',
        label: 'ISO',
        value: `${min} - ${max}`,
      })
    }
    if (aperture?.min !== null || aperture?.max !== null) {
      const min = aperture?.min ? `f/${aperture.min}` : 'any'
      const max = aperture?.max ? `f/${aperture.max}` : 'any'
      summaries.push({
        type: 'cameraSettings',
        label: 'Aperture',
        value: `${min} - ${max}`,
      })
    }
    if (shutterSpeed?.min !== null || shutterSpeed?.max !== null) {
      summaries.push({
        type: 'cameraSettings',
        label: 'Shutter',
        value: 'Custom range',
      })
    }
  }

  // Notes
  if (filterState.notes?.hasNotes === true) {
    summaries.push({
      type: 'notes',
      label: 'Notes',
      value: 'Has notes',
    })
  } else if (filterState.notes?.hasNotes === false) {
    summaries.push({
      type: 'notes',
      label: 'Notes',
      value: 'No notes',
    })
  }
  if (filterState.notes?.keywords) {
    summaries.push({
      type: 'notes',
      label: 'Notes',
      value: `"${filterState.notes.keywords}"`,
    })
  }

  // Custom fields
  if (filterState.customFields) {
    for (const [fieldName, value] of Object.entries(filterState.customFields)) {
      if (value !== null && value !== undefined && value !== '') {
        summaries.push({
          type: 'customFields',
          label: fieldName,
          value: String(value),
        })
      }
    }
  }

  return summaries
}
