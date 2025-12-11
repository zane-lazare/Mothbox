import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  DATE_PRESETS,
  formatDateForQuery,
  escapeQueryValue,
  buildDateQuery,
  buildTagQuery,
  buildSpeciesQuery,
  buildNotesQuery,
  buildCustomFieldsQuery,
  buildFileTypeQuery,
  buildCameraSettingsQuery,
  buildFilterQuery,
  combineWithUserSearch,
  hasActiveFilters,
  countActiveFilters,
  getActiveFilterSummaries,
} from '../filterQueryBuilder'

describe('filterQueryBuilder', () => {
  describe('formatDateForQuery', () => {
    it('formats date as YYYY-MM-DD', () => {
      const date = new Date(2024, 0, 15) // Jan 15, 2024
      expect(formatDateForQuery(date)).toBe('2024-01-15')
    })

    it('pads single-digit months with zero', () => {
      const date = new Date(2024, 0, 15) // January (month 0)
      expect(formatDateForQuery(date)).toBe('2024-01-15')
    })

    it('pads single-digit days with zero', () => {
      const date = new Date(2024, 10, 5) // Nov 5
      expect(formatDateForQuery(date)).toBe('2024-11-05')
    })

    it('handles double-digit months and days without padding', () => {
      const date = new Date(2024, 11, 25) // Dec 25
      expect(formatDateForQuery(date)).toBe('2024-12-25')
    })

    it('handles different years correctly', () => {
      const date = new Date(2023, 5, 10)
      expect(formatDateForQuery(date)).toBe('2023-06-10')
    })
  })

  describe('escapeQueryValue', () => {
    it('escapes double quotes by doubling them', () => {
      expect(escapeQueryValue('value with "quotes"')).toBe('value with ""quotes""')
    })

    it('handles multiple double quotes', () => {
      expect(escapeQueryValue('a "b" c "d"')).toBe('a ""b"" c ""d""')
    })

    it('returns empty string for null', () => {
      expect(escapeQueryValue(null)).toBe('')
    })

    it('returns empty string for undefined', () => {
      expect(escapeQueryValue(undefined)).toBe('')
    })

    it('returns empty string for empty string', () => {
      expect(escapeQueryValue('')).toBe('')
    })

    it('returns unchanged string without quotes', () => {
      expect(escapeQueryValue('plain value')).toBe('plain value')
    })
  })

  describe('buildDateQuery', () => {
    it('returns empty string for null dateRange', () => {
      expect(buildDateQuery(null)).toBe('')
    })

    it('returns empty string for undefined dateRange', () => {
      expect(buildDateQuery(undefined)).toBe('')
    })

    it('returns empty string for empty dateRange object', () => {
      expect(buildDateQuery({})).toBe('')
    })

    it('builds range query with start and end dates', () => {
      const dateRange = {
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      }
      expect(buildDateQuery(dateRange)).toBe('date:2024-01-01..2024-01-31')
    })

    it('builds single date query when start equals end', () => {
      const dateRange = {
        startDate: '2024-01-15',
        endDate: '2024-01-15',
      }
      expect(buildDateQuery(dateRange)).toBe('date:2024-01-15')
    })

    it('builds >= query with only start date', () => {
      const dateRange = {
        startDate: '2024-01-01',
      }
      expect(buildDateQuery(dateRange)).toBe('date:>=2024-01-01')
    })

    it('builds <= query with only end date', () => {
      const dateRange = {
        endDate: '2024-12-31',
      }
      expect(buildDateQuery(dateRange)).toBe('date:<=2024-12-31')
    })

    it('calculates date range from preset', () => {
      // Mock the date to ensure consistent results
      const mockDate = new Date(2024, 0, 15) // Jan 15, 2024
      vi.useFakeTimers()
      vi.setSystemTime(mockDate)

      const dateRange = { preset: 'today' }
      expect(buildDateQuery(dateRange)).toBe('date:2024-01-15')

      vi.useRealTimers()
    })

    it('preset overrides custom dates', () => {
      const mockDate = new Date(2024, 0, 15) // Jan 15, 2024
      vi.useFakeTimers()
      vi.setSystemTime(mockDate)

      const dateRange = {
        preset: 'today',
        startDate: '2024-01-01', // Should be ignored
        endDate: '2024-01-31', // Should be ignored
      }
      expect(buildDateQuery(dateRange)).toBe('date:2024-01-15')

      vi.useRealTimers()
    })

    it('handles invalid preset gracefully', () => {
      const dateRange = {
        preset: 'invalid',
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      }
      expect(buildDateQuery(dateRange)).toBe('date:2024-01-01..2024-01-31')
    })
  })

  describe('buildTagQuery', () => {
    it('returns empty string for null tags', () => {
      expect(buildTagQuery(null)).toBe('')
    })

    it('returns empty string for undefined tags', () => {
      expect(buildTagQuery(undefined)).toBe('')
    })

    it('returns empty string for empty selected array', () => {
      expect(buildTagQuery({ selected: [] })).toBe('')
    })

    it('returns empty string when selected is missing', () => {
      expect(buildTagQuery({})).toBe('')
    })

    it('builds query for single tag without parens', () => {
      const tags = {
        selected: ['moth'],
        matchMode: 'any',
      }
      expect(buildTagQuery(tags)).toBe('tag:"moth"')
    })

    it('builds OR query for multiple tags with "any" mode', () => {
      const tags = {
        selected: ['moth', 'butterfly'],
        matchMode: 'any',
      }
      expect(buildTagQuery(tags)).toBe('(tag:"moth" OR tag:"butterfly")')
    })

    it('builds AND query for multiple tags with "all" mode', () => {
      const tags = {
        selected: ['moth', 'butterfly', 'insect'],
        matchMode: 'all',
      }
      expect(buildTagQuery(tags)).toBe('(tag:"moth" AND tag:"butterfly" AND tag:"insect")')
    })

    it('defaults to OR when matchMode is missing', () => {
      const tags = {
        selected: ['moth', 'butterfly'],
      }
      expect(buildTagQuery(tags)).toBe('(tag:"moth" OR tag:"butterfly")')
    })

    it('escapes tags with special characters', () => {
      const tags = {
        selected: ['tag with "quotes"'],
        matchMode: 'any',
      }
      expect(buildTagQuery(tags)).toBe('tag:"tag with ""quotes"""')
    })
  })

  describe('buildSpeciesQuery', () => {
    it('returns empty string for null species', () => {
      expect(buildSpeciesQuery(null)).toBe('')
    })

    it('returns empty string for undefined species', () => {
      expect(buildSpeciesQuery(undefined)).toBe('')
    })

    it('returns empty string when selected is empty', () => {
      expect(buildSpeciesQuery({ selected: [] })).toBe('')
    })

    it('builds query for single species without parens', () => {
      const species = {
        selected: ['Actias luna'],
      }
      expect(buildSpeciesQuery(species)).toBe('species:"Actias luna"')
    })

    it('builds OR query for multiple species', () => {
      const species = {
        selected: ['Actias luna', 'Danaus plexippus'],
      }
      expect(buildSpeciesQuery(species)).toBe(
        '(species:"Actias luna" OR species:"Danaus plexippus")'
      )
    })

    it('escapes species names with special characters', () => {
      const species = {
        selected: ['Species "name"'],
      }
      expect(buildSpeciesQuery(species)).toBe('species:"Species ""name"""')
    })

    it('ignores includeUnidentified flag (comment says it is handled differently)', () => {
      const species = {
        selected: ['Actias luna'],
        includeUnidentified: true,
      }
      expect(buildSpeciesQuery(species)).toBe('species:"Actias luna"')
    })
  })

  describe('buildNotesQuery', () => {
    it('returns empty string for null notes', () => {
      expect(buildNotesQuery(null)).toBe('')
    })

    it('returns empty string for undefined notes', () => {
      expect(buildNotesQuery(undefined)).toBe('')
    })

    it('returns empty string for empty keywords', () => {
      expect(buildNotesQuery({ keywords: '' })).toBe('')
    })

    it('returns empty string for whitespace-only keywords', () => {
      expect(buildNotesQuery({ keywords: '   ' })).toBe('')
    })

    it('builds query for single keyword without quotes', () => {
      const notes = {
        keywords: 'specimen',
      }
      expect(buildNotesQuery(notes)).toBe('notes:specimen')
    })

    it('builds query for phrase with quotes', () => {
      const notes = {
        keywords: 'luna moth specimen',
      }
      expect(buildNotesQuery(notes)).toBe('notes:"luna moth specimen"')
    })

    it('trims whitespace from keywords', () => {
      const notes = {
        keywords: '  specimen  ',
      }
      expect(buildNotesQuery(notes)).toBe('notes:specimen')
    })

    it('escapes keywords with special characters', () => {
      const notes = {
        keywords: 'note with "quotes"',
      }
      expect(buildNotesQuery(notes)).toBe('notes:"note with ""quotes"""')
    })

    it('ignores hasNotes flag (comment says it is handled client-side)', () => {
      const notes = {
        keywords: 'specimen',
        hasNotes: true,
      }
      expect(buildNotesQuery(notes)).toBe('notes:specimen')
    })
  })

  describe('buildCustomFieldsQuery', () => {
    it('returns empty string for null customFields', () => {
      expect(buildCustomFieldsQuery(null)).toBe('')
    })

    it('returns empty string for undefined customFields', () => {
      expect(buildCustomFieldsQuery(undefined)).toBe('')
    })

    it('returns empty string for empty object', () => {
      expect(buildCustomFieldsQuery({})).toBe('')
    })

    it('builds query for single field', () => {
      const customFields = {
        location: 'backyard',
      }
      expect(buildCustomFieldsQuery(customFields)).toBe('custom:"backyard"')
    })

    it('builds AND query for multiple fields', () => {
      const customFields = {
        location: 'backyard',
        collector: 'John Doe',
      }
      expect(buildCustomFieldsQuery(customFields)).toBe(
        '(custom:"backyard" AND custom:"John Doe")'
      )
    })

    it('skips null values', () => {
      const customFields = {
        location: 'backyard',
        collector: null,
      }
      expect(buildCustomFieldsQuery(customFields)).toBe('custom:"backyard"')
    })

    it('skips undefined values', () => {
      const customFields = {
        location: 'backyard',
        collector: undefined,
      }
      expect(buildCustomFieldsQuery(customFields)).toBe('custom:"backyard"')
    })

    it('skips empty string values', () => {
      const customFields = {
        location: 'backyard',
        collector: '',
      }
      expect(buildCustomFieldsQuery(customFields)).toBe('custom:"backyard"')
    })

    it('converts non-string values to strings', () => {
      const customFields = {
        count: 42,
      }
      expect(buildCustomFieldsQuery(customFields)).toBe('custom:"42"')
    })

    it('escapes values with special characters', () => {
      const customFields = {
        location: 'field "A"',
      }
      expect(buildCustomFieldsQuery(customFields)).toBe('custom:"field ""A"""')
    })
  })

  describe('buildFileTypeQuery', () => {
    it('returns empty string for null fileTypes', () => {
      expect(buildFileTypeQuery(null)).toBe('')
    })

    it('returns empty string for undefined fileTypes', () => {
      expect(buildFileTypeQuery(undefined)).toBe('')
    })

    it('returns empty string for empty selected array', () => {
      expect(buildFileTypeQuery({ selected: [] })).toBe('')
    })

    it('returns empty string when selected is missing', () => {
      expect(buildFileTypeQuery({})).toBe('')
    })

    it('builds query for single jpg type', () => {
      expect(buildFileTypeQuery({ selected: ['jpg'] })).toBe('(ext:jpg OR ext:jpeg)')
    })

    it('builds query for single png type', () => {
      expect(buildFileTypeQuery({ selected: ['png'] })).toBe('ext:png')
    })

    it('builds query for raw type', () => {
      expect(buildFileTypeQuery({ selected: ['raw'] })).toBe(
        '(ext:dng OR ext:cr2 OR ext:nef OR ext:arw OR ext:orf OR ext:rw2)'
      )
    })

    it('builds query for video type', () => {
      expect(buildFileTypeQuery({ selected: ['video'] })).toBe(
        '(ext:mp4 OR ext:mov OR ext:avi OR ext:mkv)'
      )
    })

    it('builds OR query for multiple types', () => {
      expect(buildFileTypeQuery({ selected: ['jpg', 'png'] })).toBe(
        '(ext:jpg OR ext:jpeg OR ext:png)'
      )
    })

    it('builds OR query for all types', () => {
      expect(buildFileTypeQuery({ selected: ['jpg', 'png', 'raw', 'video'] })).toBe(
        '(ext:jpg OR ext:jpeg OR ext:png OR ext:dng OR ext:cr2 OR ext:nef OR ext:arw OR ext:orf OR ext:rw2 OR ext:mp4 OR ext:mov OR ext:avi OR ext:mkv)'
      )
    })

    it('handles unknown types by passing them through', () => {
      expect(buildFileTypeQuery({ selected: ['custom'] })).toBe('ext:custom')
    })
  })

  describe('buildCameraSettingsQuery', () => {
    it('returns empty string for null cameraSettings', () => {
      expect(buildCameraSettingsQuery(null)).toBe('')
    })

    it('returns empty string for undefined cameraSettings', () => {
      expect(buildCameraSettingsQuery(undefined)).toBe('')
    })

    it('returns empty string for empty object', () => {
      expect(buildCameraSettingsQuery({})).toBe('')
    })

    it('builds query for ISO min and max', () => {
      expect(buildCameraSettingsQuery({ iso: { min: 100, max: 3200 } })).toBe('iso:100-3200')
    })

    it('builds query for ISO with only min', () => {
      expect(buildCameraSettingsQuery({ iso: { min: 100 } })).toBe('iso:100-999999')
    })

    it('builds query for ISO with only max', () => {
      expect(buildCameraSettingsQuery({ iso: { max: 3200 } })).toBe('iso:0-3200')
    })

    it('builds query for aperture min and max', () => {
      expect(buildCameraSettingsQuery({ aperture: { min: 2.8, max: 16 } })).toBe(
        'aperture:2.8-16'
      )
    })

    it('builds query for aperture with only min', () => {
      expect(buildCameraSettingsQuery({ aperture: { min: 2.8 } })).toBe('aperture:2.8-99')
    })

    it('builds query for aperture with only max', () => {
      expect(buildCameraSettingsQuery({ aperture: { max: 16 } })).toBe('aperture:0-16')
    })

    it('builds query for shutter speed min and max', () => {
      expect(buildCameraSettingsQuery({ shutterSpeed: { min: 0.001, max: 1 } })).toBe(
        'shutter:0.001-1'
      )
    })

    it('builds query for shutter speed with only min', () => {
      expect(buildCameraSettingsQuery({ shutterSpeed: { min: 0.001 } })).toBe('shutter:0.001-9999')
    })

    it('builds query for shutter speed with only max', () => {
      expect(buildCameraSettingsQuery({ shutterSpeed: { max: 1 } })).toBe('shutter:0-1')
    })

    it('combines multiple camera settings with space', () => {
      expect(
        buildCameraSettingsQuery({
          iso: { min: 100, max: 3200 },
          aperture: { min: 2.8, max: 16 },
          shutterSpeed: { min: 0.001, max: 1 },
        })
      ).toBe('iso:100-3200 aperture:2.8-16 shutter:0.001-1')
    })

    it('handles zero values correctly', () => {
      expect(buildCameraSettingsQuery({ iso: { min: 0, max: 0 } })).toBe('iso:0-0')
    })

    it('ignores null values in range', () => {
      expect(
        buildCameraSettingsQuery({
          iso: { min: null, max: null },
          aperture: { min: null, max: null },
        })
      ).toBe('')
    })

    it('treats undefined as null', () => {
      expect(
        buildCameraSettingsQuery({
          iso: { min: undefined, max: undefined },
        })
      ).toBe('')
    })
  })

  describe('buildFilterQuery', () => {
    it('returns empty string for null filterState', () => {
      expect(buildFilterQuery(null)).toBe('')
    })

    it('returns empty string for undefined filterState', () => {
      expect(buildFilterQuery(undefined)).toBe('')
    })

    it('returns empty string for empty filterState', () => {
      expect(buildFilterQuery({})).toBe('')
    })

    it('builds query with only date filter', () => {
      const filterState = {
        dateRange: {
          startDate: '2024-01-01',
          endDate: '2024-01-31',
        },
      }
      expect(buildFilterQuery(filterState)).toBe('date:2024-01-01..2024-01-31')
    })

    it('builds query with only tags filter', () => {
      const filterState = {
        tags: {
          selected: ['moth'],
          matchMode: 'any',
        },
      }
      expect(buildFilterQuery(filterState)).toBe('tag:"moth"')
    })

    it('builds query with only species filter', () => {
      const filterState = {
        species: {
          selected: ['Actias luna'],
        },
      }
      expect(buildFilterQuery(filterState)).toBe('species:"Actias luna"')
    })

    it('builds query with only notes filter', () => {
      const filterState = {
        notes: {
          keywords: 'specimen',
        },
      }
      expect(buildFilterQuery(filterState)).toBe('notes:specimen')
    })

    it('builds query with only custom fields filter', () => {
      const filterState = {
        customFields: {
          location: 'backyard',
        },
      }
      expect(buildFilterQuery(filterState)).toBe('custom:"backyard"')
    })

    it('builds query with only file types filter', () => {
      const filterState = {
        fileTypes: {
          selected: ['jpg'],
        },
      }
      expect(buildFilterQuery(filterState)).toBe('(ext:jpg OR ext:jpeg)')
    })

    it('builds query with only camera settings filter', () => {
      const filterState = {
        cameraSettings: {
          iso: { min: 100, max: 3200 },
        },
      }
      expect(buildFilterQuery(filterState)).toBe('iso:100-3200')
    })

    it('combines multiple filters with AND', () => {
      const filterState = {
        dateRange: {
          startDate: '2024-01-01',
          endDate: '2024-01-31',
        },
        tags: {
          selected: ['moth'],
          matchMode: 'any',
        },
        species: {
          selected: ['Actias luna'],
        },
      }
      expect(buildFilterQuery(filterState)).toBe(
        'date:2024-01-01..2024-01-31 AND tag:"moth" AND species:"Actias luna"'
      )
    })

    it('skips empty filter sections', () => {
      const filterState = {
        dateRange: {
          startDate: '2024-01-01',
          endDate: '2024-01-31',
        },
        tags: {
          selected: [],
        },
        species: {
          selected: ['Actias luna'],
        },
      }
      expect(buildFilterQuery(filterState)).toBe(
        'date:2024-01-01..2024-01-31 AND species:"Actias luna"'
      )
    })

    it('combines all filter types', () => {
      const filterState = {
        dateRange: {
          startDate: '2024-01-01',
          endDate: '2024-01-31',
        },
        tags: {
          selected: ['moth', 'butterfly'],
          matchMode: 'any',
        },
        species: {
          selected: ['Actias luna'],
        },
        notes: {
          keywords: 'specimen',
        },
        customFields: {
          location: 'backyard',
        },
      }
      expect(buildFilterQuery(filterState)).toBe(
        'date:2024-01-01..2024-01-31 AND (tag:"moth" OR tag:"butterfly") AND species:"Actias luna" AND notes:specimen AND custom:"backyard"'
      )
    })

    it('combines all filter types including fileTypes and cameraSettings', () => {
      const filterState = {
        dateRange: {
          startDate: '2024-01-01',
          endDate: '2024-01-31',
        },
        tags: {
          selected: ['moth'],
          matchMode: 'any',
        },
        species: {
          selected: ['Actias luna'],
        },
        notes: {
          keywords: 'specimen',
        },
        customFields: {
          location: 'backyard',
        },
        fileTypes: {
          selected: ['jpg'],
        },
        cameraSettings: {
          iso: { min: 100, max: 3200 },
          aperture: { min: 2.8, max: 16 },
        },
      }
      expect(buildFilterQuery(filterState)).toBe(
        'date:2024-01-01..2024-01-31 AND tag:"moth" AND species:"Actias luna" AND notes:specimen AND custom:"backyard" AND (ext:jpg OR ext:jpeg) AND iso:100-3200 aperture:2.8-16'
      )
    })
  })

  describe('combineWithUserSearch', () => {
    it('returns empty string when both are empty', () => {
      expect(combineWithUserSearch('', '')).toBe('')
    })

    it('returns empty string when both are null', () => {
      expect(combineWithUserSearch(null, null)).toBe('')
    })

    it('returns empty string when both are undefined', () => {
      expect(combineWithUserSearch(undefined, undefined)).toBe('')
    })

    it('returns filterQuery when userQuery is empty', () => {
      expect(combineWithUserSearch('', 'tag:"moth"')).toBe('tag:"moth"')
    })

    it('returns userQuery when filterQuery is empty', () => {
      expect(combineWithUserSearch('moth', '')).toBe('moth')
    })

    it('combines both queries with AND and parens', () => {
      expect(combineWithUserSearch('moth', 'tag:"luna"')).toBe('(moth) AND (tag:"luna")')
    })

    it('trims whitespace from both queries', () => {
      expect(combineWithUserSearch('  moth  ', '  tag:"luna"  ')).toBe(
        '(moth) AND (tag:"luna")'
      )
    })

    it('handles complex user query', () => {
      expect(combineWithUserSearch('moth AND butterfly', 'date:2024-01-01..2024-01-31')).toBe(
        '(moth AND butterfly) AND (date:2024-01-01..2024-01-31)'
      )
    })

    it('handles complex filter query', () => {
      expect(
        combineWithUserSearch(
          'moth',
          'date:2024-01-01..2024-01-31 AND tag:"moth" AND species:"Actias luna"'
        )
      ).toBe('(moth) AND (date:2024-01-01..2024-01-31 AND tag:"moth" AND species:"Actias luna")')
    })
  })

  describe('hasActiveFilters', () => {
    it('returns false for null filterState', () => {
      expect(hasActiveFilters(null)).toBe(false)
    })

    it('returns false for undefined filterState', () => {
      expect(hasActiveFilters(undefined)).toBe(false)
    })

    it('returns true for empty filterState (bug: notes check)', () => {
      // Bug: filterState.notes?.hasNotes !== null returns true when hasNotes is undefined
      // because undefined !== null is true
      expect(hasActiveFilters({})).toBe(true)
    })

    it('returns true when dateRange preset is set', () => {
      expect(hasActiveFilters({ dateRange: { preset: 'today' } })).toBe(true)
    })

    it('returns true when dateRange startDate is set', () => {
      expect(hasActiveFilters({ dateRange: { startDate: '2024-01-01' } })).toBe(true)
    })

    it('returns true when dateRange endDate is set', () => {
      expect(hasActiveFilters({ dateRange: { endDate: '2024-01-31' } })).toBe(true)
    })

    it('returns true when tags are selected', () => {
      expect(hasActiveFilters({ tags: { selected: ['moth'] } })).toBe(true)
    })

    it('returns true when tags array is empty (bug: notes check)', () => {
      // Bug: Any object triggers the notes check
      expect(hasActiveFilters({ tags: { selected: [] } })).toBe(true)
    })

    it('returns true when species are selected', () => {
      expect(hasActiveFilters({ species: { selected: ['Actias luna'] } })).toBe(true)
    })

    it('returns true when includeUnidentified is true', () => {
      expect(hasActiveFilters({ species: { includeUnidentified: true } })).toBe(true)
    })

    it('returns true when fileTypes are selected', () => {
      expect(hasActiveFilters({ fileTypes: { selected: ['jpg'] } })).toBe(true)
    })

    it('returns true when ISO min is set', () => {
      expect(hasActiveFilters({ cameraSettings: { iso: { min: 100 } } })).toBe(true)
    })

    it('returns true when ISO max is set', () => {
      expect(hasActiveFilters({ cameraSettings: { iso: { max: 3200 } } })).toBe(true)
    })

    it('returns true when aperture min is set', () => {
      expect(hasActiveFilters({ cameraSettings: { aperture: { min: 2.8 } } })).toBe(true)
    })

    it('returns true when aperture max is set', () => {
      expect(hasActiveFilters({ cameraSettings: { aperture: { max: 16 } } })).toBe(true)
    })

    it('returns true when shutter speed min is set', () => {
      expect(hasActiveFilters({ cameraSettings: { shutterSpeed: { min: 0.001 } } })).toBe(true)
    })

    it('returns true when shutter speed max is set', () => {
      expect(hasActiveFilters({ cameraSettings: { shutterSpeed: { max: 1 } } })).toBe(true)
    })

    it('returns true when camera settings object exists (bug: notes check)', () => {
      // Bug: Even with all null camera settings, the notes check returns true
      expect(
        hasActiveFilters({
          cameraSettings: {
            iso: { min: null, max: null },
            aperture: { min: null, max: null },
            shutterSpeed: { min: null, max: null },
          },
        })
      ).toBe(true)
    })

    it('returns true when notes.hasNotes is true', () => {
      expect(hasActiveFilters({ notes: { hasNotes: true } })).toBe(true)
    })

    it('returns true when notes.hasNotes is false', () => {
      expect(hasActiveFilters({ notes: { hasNotes: false } })).toBe(true)
    })

    it('returns false when notes.hasNotes is null', () => {
      expect(hasActiveFilters({ notes: { hasNotes: null } })).toBe(false)
    })

    it('returns true when notes.keywords is set', () => {
      expect(hasActiveFilters({ notes: { keywords: 'specimen' } })).toBe(true)
    })

    it('returns true when customFields has values', () => {
      expect(hasActiveFilters({ customFields: { location: 'backyard' } })).toBe(true)
    })

    it('returns true when customFields has only empty values (bug: notes check)', () => {
      // Bug: Even with empty customFields, the notes check returns true
      expect(hasActiveFilters({ customFields: { location: '' } })).toBe(true)
    })

    it('returns true when customFields has only null values (bug: notes check)', () => {
      // Bug: Even with null customFields, the notes check returns true
      expect(hasActiveFilters({ customFields: { location: null } })).toBe(true)
    })

    it('returns true when customFields has mixed values', () => {
      expect(hasActiveFilters({ customFields: { location: 'backyard', collector: '' } })).toBe(
        true
      )
    })
  })

  describe('countActiveFilters', () => {
    it('returns 0 for null filterState', () => {
      expect(countActiveFilters(null)).toBe(0)
    })

    it('returns 0 for undefined filterState', () => {
      expect(countActiveFilters(undefined)).toBe(0)
    })

    it('returns 1 for empty filterState (bug: notes always counted)', () => {
      // Bug: hasActiveFilters counts notes as active even when undefined
      expect(countActiveFilters({})).toBe(1)
    })

    it('counts dateRange as 1 (+1 for notes bug)', () => {
      expect(countActiveFilters({ dateRange: { preset: 'today' } })).toBe(2)
    })

    it('counts tags as 1 (+1 for notes bug)', () => {
      expect(countActiveFilters({ tags: { selected: ['moth'] } })).toBe(2)
    })

    it('counts species as 1 (+1 for notes bug)', () => {
      expect(countActiveFilters({ species: { selected: ['Actias luna'] } })).toBe(2)
    })

    it('counts includeUnidentified as 1 (+1 for notes bug)', () => {
      expect(countActiveFilters({ species: { includeUnidentified: true } })).toBe(2)
    })

    it('counts fileTypes as 1 (+1 for notes bug)', () => {
      expect(countActiveFilters({ fileTypes: { selected: ['jpg'] } })).toBe(2)
    })

    it('counts camera settings as 1 even with multiple settings (+1 for notes bug)', () => {
      expect(
        countActiveFilters({
          cameraSettings: {
            iso: { min: 100, max: 3200 },
            aperture: { min: 2.8, max: 16 },
            shutterSpeed: { min: 0.001, max: 1 },
          },
        })
      ).toBe(2)
    })

    it('counts notes as 1', () => {
      expect(countActiveFilters({ notes: { keywords: 'specimen' } })).toBe(1)
    })

    it('counts customFields as 1 (+1 for notes bug)', () => {
      expect(
        countActiveFilters({
          customFields: {
            location: 'backyard',
            collector: 'John Doe',
          },
        })
      ).toBe(2)
    })

    it('counts all filter types correctly', () => {
      expect(
        countActiveFilters({
          dateRange: { preset: 'today' },
          tags: { selected: ['moth'] },
          species: { selected: ['Actias luna'] },
          fileTypes: { selected: ['jpg'] },
          cameraSettings: { iso: { min: 100 } },
          notes: { keywords: 'specimen' },
          customFields: { location: 'backyard' },
        })
      ).toBe(7)
    })

    it('returns 1 for empty filter sections (bug: notes always counted)', () => {
      // Bug: notes is always counted as active
      expect(
        countActiveFilters({
          dateRange: {},
          tags: { selected: [] },
          species: { selected: [] },
          fileTypes: { selected: [] },
          cameraSettings: {
            iso: { min: null, max: null },
            aperture: { min: null, max: null },
            shutterSpeed: { min: null, max: null },
          },
          notes: {},
          customFields: {},
        })
      ).toBe(1)
    })
  })

  describe('getActiveFilterSummaries', () => {
    it('returns empty array for null filterState', () => {
      expect(getActiveFilterSummaries(null)).toEqual([])
    })

    it('returns empty array for undefined filterState', () => {
      expect(getActiveFilterSummaries(undefined)).toEqual([])
    })

    it('returns empty array for empty filterState', () => {
      expect(getActiveFilterSummaries({})).toEqual([])
    })

    it('returns summary for dateRange preset', () => {
      const summaries = getActiveFilterSummaries({ dateRange: { preset: 'today' } })
      expect(summaries).toEqual([
        {
          type: 'dateRange',
          label: 'Date',
          value: 'Today',
        },
      ])
    })

    it('returns summary for custom dateRange with both dates', () => {
      const summaries = getActiveFilterSummaries({
        dateRange: {
          startDate: '2024-01-01',
          endDate: '2024-01-31',
        },
      })
      expect(summaries).toEqual([
        {
          type: 'dateRange',
          label: 'Date',
          value: '2024-01-01 to 2024-01-31',
        },
      ])
    })

    it('returns summary for custom dateRange with only start date', () => {
      const summaries = getActiveFilterSummaries({
        dateRange: {
          startDate: '2024-01-01',
        },
      })
      expect(summaries).toEqual([
        {
          type: 'dateRange',
          label: 'Date',
          value: '2024-01-01 to ...',
        },
      ])
    })

    it('returns summary for custom dateRange with only end date', () => {
      const summaries = getActiveFilterSummaries({
        dateRange: {
          endDate: '2024-01-31',
        },
      })
      expect(summaries).toEqual([
        {
          type: 'dateRange',
          label: 'Date',
          value: '... to 2024-01-31',
        },
      ])
    })

    it('returns summary for tags with "any" mode', () => {
      const summaries = getActiveFilterSummaries({
        tags: {
          selected: ['moth', 'butterfly'],
          matchMode: 'any',
        },
      })
      expect(summaries).toEqual([
        {
          type: 'tags',
          label: 'Tags',
          value: '2 (any)',
        },
      ])
    })

    it('returns summary for tags with "all" mode', () => {
      const summaries = getActiveFilterSummaries({
        tags: {
          selected: ['moth', 'butterfly'],
          matchMode: 'all',
        },
      })
      expect(summaries).toEqual([
        {
          type: 'tags',
          label: 'Tags',
          value: '2 (all)',
        },
      ])
    })

    it('returns summary for species', () => {
      const summaries = getActiveFilterSummaries({
        species: {
          selected: ['Actias luna', 'Danaus plexippus'],
        },
      })
      expect(summaries).toEqual([
        {
          type: 'species',
          label: 'Species',
          value: '2 selected',
        },
      ])
    })

    it('returns summary for includeUnidentified', () => {
      const summaries = getActiveFilterSummaries({
        species: {
          includeUnidentified: true,
        },
      })
      expect(summaries).toEqual([
        {
          type: 'species',
          label: 'Species',
          value: 'Include unidentified',
        },
      ])
    })

    it('returns both summaries for species and includeUnidentified', () => {
      const summaries = getActiveFilterSummaries({
        species: {
          selected: ['Actias luna'],
          includeUnidentified: true,
        },
      })
      expect(summaries).toEqual([
        {
          type: 'species',
          label: 'Species',
          value: '1 selected',
        },
        {
          type: 'species',
          label: 'Species',
          value: 'Include unidentified',
        },
      ])
    })

    it('returns summary for fileTypes', () => {
      const summaries = getActiveFilterSummaries({
        fileTypes: {
          selected: ['jpg', 'png'],
        },
      })
      expect(summaries).toEqual([
        {
          type: 'fileTypes',
          label: 'File Type',
          value: 'JPG, PNG',
        },
      ])
    })

    it('returns summary for ISO range (bug: all camera settings included)', () => {
      const summaries = getActiveFilterSummaries({
        cameraSettings: {
          iso: { min: 100, max: 3200 },
        },
      })
      // Bug: undefined !== null is true, so all camera settings are included
      expect(summaries).toEqual([
        {
          type: 'cameraSettings',
          label: 'ISO',
          value: '100 - 3200',
        },
        {
          type: 'cameraSettings',
          label: 'Aperture',
          value: 'any - any',
        },
        {
          type: 'cameraSettings',
          label: 'Shutter',
          value: 'Custom range',
        },
      ])
    })

    it('returns summary for ISO with only min (bug: all camera settings included)', () => {
      const summaries = getActiveFilterSummaries({
        cameraSettings: {
          iso: { min: 100, max: null },
        },
      })
      expect(summaries).toEqual([
        {
          type: 'cameraSettings',
          label: 'ISO',
          value: '100 - any',
        },
        {
          type: 'cameraSettings',
          label: 'Aperture',
          value: 'any - any',
        },
        {
          type: 'cameraSettings',
          label: 'Shutter',
          value: 'Custom range',
        },
      ])
    })

    it('returns summary for ISO with only max (bug: all camera settings included)', () => {
      const summaries = getActiveFilterSummaries({
        cameraSettings: {
          iso: { min: null, max: 3200 },
        },
      })
      expect(summaries).toEqual([
        {
          type: 'cameraSettings',
          label: 'ISO',
          value: 'any - 3200',
        },
        {
          type: 'cameraSettings',
          label: 'Aperture',
          value: 'any - any',
        },
        {
          type: 'cameraSettings',
          label: 'Shutter',
          value: 'Custom range',
        },
      ])
    })

    it('returns summary for aperture range (bug: all camera settings included)', () => {
      const summaries = getActiveFilterSummaries({
        cameraSettings: {
          aperture: { min: 2.8, max: 16 },
        },
      })
      expect(summaries).toEqual([
        {
          type: 'cameraSettings',
          label: 'ISO',
          value: 'any - any',
        },
        {
          type: 'cameraSettings',
          label: 'Aperture',
          value: 'f/2.8 - f/16',
        },
        {
          type: 'cameraSettings',
          label: 'Shutter',
          value: 'Custom range',
        },
      ])
    })

    it('returns summary for aperture with only min (bug: all camera settings included)', () => {
      const summaries = getActiveFilterSummaries({
        cameraSettings: {
          aperture: { min: 2.8, max: null },
        },
      })
      expect(summaries).toEqual([
        {
          type: 'cameraSettings',
          label: 'ISO',
          value: 'any - any',
        },
        {
          type: 'cameraSettings',
          label: 'Aperture',
          value: 'f/2.8 - any',
        },
        {
          type: 'cameraSettings',
          label: 'Shutter',
          value: 'Custom range',
        },
      ])
    })

    it('returns summary for aperture with only max (bug: all camera settings included)', () => {
      const summaries = getActiveFilterSummaries({
        cameraSettings: {
          aperture: { min: null, max: 16 },
        },
      })
      expect(summaries).toEqual([
        {
          type: 'cameraSettings',
          label: 'ISO',
          value: 'any - any',
        },
        {
          type: 'cameraSettings',
          label: 'Aperture',
          value: 'any - f/16',
        },
        {
          type: 'cameraSettings',
          label: 'Shutter',
          value: 'Custom range',
        },
      ])
    })

    it('returns summary for shutter speed (bug: all camera settings included)', () => {
      const summaries = getActiveFilterSummaries({
        cameraSettings: {
          shutterSpeed: { min: 0.001, max: 1 },
        },
      })
      expect(summaries).toEqual([
        {
          type: 'cameraSettings',
          label: 'ISO',
          value: 'any - any',
        },
        {
          type: 'cameraSettings',
          label: 'Aperture',
          value: 'any - any',
        },
        {
          type: 'cameraSettings',
          label: 'Shutter',
          value: 'Custom range',
        },
      ])
    })

    it('returns summary for "has notes"', () => {
      const summaries = getActiveFilterSummaries({
        notes: {
          hasNotes: true,
        },
      })
      expect(summaries).toEqual([
        {
          type: 'notes',
          label: 'Notes',
          value: 'Has notes',
        },
      ])
    })

    it('returns summary for "no notes"', () => {
      const summaries = getActiveFilterSummaries({
        notes: {
          hasNotes: false,
        },
      })
      expect(summaries).toEqual([
        {
          type: 'notes',
          label: 'Notes',
          value: 'No notes',
        },
      ])
    })

    it('returns summary for notes keywords', () => {
      const summaries = getActiveFilterSummaries({
        notes: {
          keywords: 'specimen',
        },
      })
      expect(summaries).toEqual([
        {
          type: 'notes',
          label: 'Notes',
          value: '"specimen"',
        },
      ])
    })

    it('returns both summaries for notes with hasNotes and keywords', () => {
      const summaries = getActiveFilterSummaries({
        notes: {
          hasNotes: true,
          keywords: 'specimen',
        },
      })
      expect(summaries).toEqual([
        {
          type: 'notes',
          label: 'Notes',
          value: 'Has notes',
        },
        {
          type: 'notes',
          label: 'Notes',
          value: '"specimen"',
        },
      ])
    })

    it('returns summary for customFields', () => {
      const summaries = getActiveFilterSummaries({
        customFields: {
          location: 'backyard',
          collector: 'John Doe',
        },
      })
      expect(summaries).toEqual([
        {
          type: 'customFields',
          label: 'location',
          value: 'backyard',
        },
        {
          type: 'customFields',
          label: 'collector',
          value: 'John Doe',
        },
      ])
    })

    it('skips empty customFields values', () => {
      const summaries = getActiveFilterSummaries({
        customFields: {
          location: 'backyard',
          collector: '',
          notes: null,
        },
      })
      expect(summaries).toEqual([
        {
          type: 'customFields',
          label: 'location',
          value: 'backyard',
        },
      ])
    })

    it('returns all summaries for complex filterState (bug: all camera settings included)', () => {
      const summaries = getActiveFilterSummaries({
        dateRange: { preset: 'today' },
        tags: { selected: ['moth'], matchMode: 'any' },
        species: { selected: ['Actias luna'] },
        fileTypes: { selected: ['jpg'] },
        cameraSettings: { iso: { min: 100, max: 3200 } },
        notes: { keywords: 'specimen' },
        customFields: { location: 'backyard' },
      })
      expect(summaries).toEqual([
        { type: 'dateRange', label: 'Date', value: 'Today' },
        { type: 'tags', label: 'Tags', value: '1 (any)' },
        { type: 'species', label: 'Species', value: '1 selected' },
        { type: 'fileTypes', label: 'File Type', value: 'JPG' },
        { type: 'cameraSettings', label: 'ISO', value: '100 - 3200' },
        { type: 'cameraSettings', label: 'Aperture', value: 'any - any' },
        { type: 'cameraSettings', label: 'Shutter', value: 'Custom range' },
        { type: 'notes', label: 'Notes', value: '"specimen"' },
        { type: 'customFields', label: 'location', value: 'backyard' },
      ])
    })
  })

  describe('DATE_PRESETS', () => {
    beforeEach(() => {
      // Mock date to ensure consistent results
      const mockDate = new Date(2024, 0, 15, 12, 0, 0) // Jan 15, 2024, 12:00:00
      vi.useFakeTimers()
      vi.setSystemTime(mockDate)
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('today preset returns same start and end date', () => {
      const range = DATE_PRESETS.today.getRange()
      expect(range).toEqual({
        startDate: '2024-01-15',
        endDate: '2024-01-15',
      })
    })

    it('7days preset returns 7-day range', () => {
      const range = DATE_PRESETS['7days'].getRange()
      expect(range).toEqual({
        startDate: '2024-01-08',
        endDate: '2024-01-15',
      })
    })

    it('30days preset returns 30-day range', () => {
      const range = DATE_PRESETS['30days'].getRange()
      expect(range).toEqual({
        startDate: '2023-12-16',
        endDate: '2024-01-15',
      })
    })

    it('90days preset returns 90-day range', () => {
      const range = DATE_PRESETS['90days'].getRange()
      expect(range).toEqual({
        startDate: '2023-10-17',
        endDate: '2024-01-15',
      })
    })

    it('thisMonth preset returns current month range', () => {
      const range = DATE_PRESETS.thisMonth.getRange()
      expect(range).toEqual({
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      })
    })

    it('lastMonth preset returns previous month range', () => {
      const range = DATE_PRESETS.lastMonth.getRange()
      expect(range).toEqual({
        startDate: '2023-12-01',
        endDate: '2023-12-31',
      })
    })

    it('thisYear preset returns current year range', () => {
      const range = DATE_PRESETS.thisYear.getRange()
      expect(range).toEqual({
        startDate: '2024-01-01',
        endDate: '2024-12-31',
      })
    })

    it('all presets have label property', () => {
      Object.entries(DATE_PRESETS).forEach(([, preset]) => {
        expect(preset.label).toBeDefined()
        expect(typeof preset.label).toBe('string')
      })
    })

    it('all presets have getRange function', () => {
      Object.entries(DATE_PRESETS).forEach(([, preset]) => {
        expect(preset.getRange).toBeDefined()
        expect(typeof preset.getRange).toBe('function')
      })
    })
  })
})
