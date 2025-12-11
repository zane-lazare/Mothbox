import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useFilterUrlSync, parseUrlToFilterState, serializeFilterStateToUrl, areFilterStatesEqual } from '../useFilterUrlSync'

describe('parseUrlToFilterState', () => {
  it('returns null when no filter params are present', () => {
    const params = new URLSearchParams('')
    const result = parseUrlToFilterState(params)
    expect(result).toBeNull()
  })

  it('parses date range preset', () => {
    const params = new URLSearchParams('f_dr=7days')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      dateRange: {
        preset: '7days',
      },
    })
  })

  it('parses custom date range', () => {
    const params = new URLSearchParams('f_ds=2024-01-01&f_de=2024-01-31')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      dateRange: {
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      },
    })
  })

  it('parses tags with match mode', () => {
    const params = new URLSearchParams('f_tags=moth,luna&f_tm=all')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      tags: {
        selected: ['moth', 'luna'],
        matchMode: 'all',
      },
    })
  })

  it('defaults tag match mode to "any"', () => {
    const params = new URLSearchParams('f_tags=moth')
    const result = parseUrlToFilterState(params)
    expect(result.tags.matchMode).toBe('any')
  })

  it('parses URL-encoded tags', () => {
    const params = new URLSearchParams('f_tags=Luna%20Moth,Actias%20luna')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      tags: {
        selected: ['Luna Moth', 'Actias luna'],
        matchMode: 'any',
      },
    })
  })

  it('parses species', () => {
    const params = new URLSearchParams('f_species=Actias%20luna,Papilio')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      species: {
        selected: ['Actias luna', 'Papilio'],
      },
    })
  })

  it('parses includeUnidentified flag', () => {
    const params = new URLSearchParams('f_ui=1')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      species: {
        includeUnidentified: true,
      },
    })
  })

  it('parses file types', () => {
    const params = new URLSearchParams('f_ft=jpg,png')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      fileTypes: {
        selected: ['jpg', 'png'],
      },
    })
  })

  it('parses ISO range', () => {
    const params = new URLSearchParams('f_iso=100-3200')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      cameraSettings: {
        iso: {
          min: 100,
          max: 3200,
        },
      },
    })
  })

  it('parses aperture range', () => {
    const params = new URLSearchParams('f_ap=2.8-8')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      cameraSettings: {
        aperture: {
          min: 2.8,
          max: 8,
        },
      },
    })
  })

  it('parses shutter speed range', () => {
    const params = new URLSearchParams('f_ss=0.001-0.016')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      cameraSettings: {
        shutterSpeed: {
          min: 0.001,
          max: 0.016,
        },
      },
    })
  })

  it('parses multiple camera settings', () => {
    const params = new URLSearchParams('f_iso=100-3200&f_ap=2.8-8&f_ss=0.001-0.016')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      cameraSettings: {
        iso: { min: 100, max: 3200 },
        aperture: { min: 2.8, max: 8 },
        shutterSpeed: { min: 0.001, max: 0.016 },
      },
    })
  })

  it('parses hasNotes flag (true)', () => {
    const params = new URLSearchParams('f_hn=1')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      notes: {
        hasNotes: true,
      },
    })
  })

  it('parses hasNotes flag (false)', () => {
    const params = new URLSearchParams('f_hn=0')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      notes: {
        hasNotes: false,
      },
    })
  })

  it('parses notes keywords', () => {
    const params = new URLSearchParams('f_nk=specimen')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      notes: {
        keywords: 'specimen',
      },
    })
  })

  it('parses URL-encoded notes keywords', () => {
    const params = new URLSearchParams('f_nk=rare%20specimen')
    const result = parseUrlToFilterState(params)
    expect(result.notes.keywords).toBe('rare specimen')
  })

  it('parses custom fields', () => {
    const params = new URLSearchParams('f_cf_location=forest&f_cf_weather=sunny')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      customFields: {
        location: 'forest',
        weather: 'sunny',
      },
    })
  })

  it('parses URL-encoded custom fields', () => {
    const params = new URLSearchParams('f_cf_location=Oak%20Forest')
    const result = parseUrlToFilterState(params)
    expect(result.customFields.location).toBe('Oak Forest')
  })

  it('parses complex combined filters', () => {
    const params = new URLSearchParams(
      'f_dr=7days&f_tags=moth,luna&f_tm=all&f_species=Actias%20luna&f_ui=1&f_iso=100-3200&f_hn=1&f_cf_location=forest'
    )
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      dateRange: {
        preset: '7days',
      },
      tags: {
        selected: ['moth', 'luna'],
        matchMode: 'all',
      },
      species: {
        selected: ['Actias luna'],
        includeUnidentified: true,
      },
      cameraSettings: {
        iso: {
          min: 100,
          max: 3200,
        },
      },
      notes: {
        hasNotes: true,
      },
      customFields: {
        location: 'forest',
      },
    })
  })

  it('ignores invalid date formats', () => {
    const params = new URLSearchParams('f_ds=invalid-date&f_de=not-a-date')
    const result = parseUrlToFilterState(params)
    // Should return null because no valid dates were parsed
    expect(result).toBeNull()
  })

  it('parses dates that match format even if semantically invalid', () => {
    // Note: We only validate format (YYYY-MM-DD), not semantic validity
    // This is intentional to keep parsing simple and let the backend/UI handle validation
    const params = new URLSearchParams('f_ds=2024-13-45')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      dateRange: {
        startDate: '2024-13-45',
      },
    })
  })

  it('ignores invalid date preset', () => {
    const params = new URLSearchParams('f_dr=invalid-preset')
    const result = parseUrlToFilterState(params)
    // Should return null because preset is invalid
    expect(result).toBeNull()
  })

  it('parses valid date even with invalid preset', () => {
    const params = new URLSearchParams('f_dr=invalid&f_ds=2024-01-01')
    const result = parseUrlToFilterState(params)
    // Should parse the valid date, ignore invalid preset
    expect(result).toEqual({
      dateRange: {
        startDate: '2024-01-01',
      },
    })
  })

  it('ignores invalid range formats', () => {
    const params = new URLSearchParams('f_iso=invalid')
    const result = parseUrlToFilterState(params)
    expect(result).toBeNull()
  })

  it('handles partial ranges (min only)', () => {
    const params = new URLSearchParams('f_iso=100-')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      cameraSettings: {
        iso: {
          min: 100,
          max: null,
        },
      },
    })
  })

  it('handles partial ranges (max only)', () => {
    const params = new URLSearchParams('f_iso=-3200')
    const result = parseUrlToFilterState(params)
    expect(result).toEqual({
      cameraSettings: {
        iso: {
          min: null,
          max: 3200,
        },
      },
    })
  })

  it('filters out empty tags', () => {
    const params = new URLSearchParams('f_tags=moth,,luna,')
    const result = parseUrlToFilterState(params)
    expect(result.tags.selected).toEqual(['moth', 'luna'])
  })

  it('filters out empty species', () => {
    const params = new URLSearchParams('f_species=,Actias%20luna,')
    const result = parseUrlToFilterState(params)
    expect(result.species.selected).toEqual(['Actias luna'])
  })

  describe('URL parameter limits', () => {
    it('returns null when URL has too many parameters', () => {
      const params = new URLSearchParams()
      // Add more than 50 parameters
      for (let i = 0; i < 60; i++) {
        params.set(`f_cf_field${i}`, `value${i}`)
      }

      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const result = parseUrlToFilterState(params)

      expect(result).toBeNull()
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Too many URL filter parameters')
      )

      consoleWarnSpy.mockRestore()
    })

    it('processes URL with exactly 50 parameters', () => {
      const params = new URLSearchParams()
      for (let i = 0; i < 50; i++) {
        params.set(`f_cf_field${i}`, `value${i}`)
      }

      const result = parseUrlToFilterState(params)

      expect(result).not.toBeNull()
      expect(Object.keys(result.customFields)).toHaveLength(50)
    })

    it('processes URL with fewer than 50 parameters', () => {
      const params = new URLSearchParams()
      for (let i = 0; i < 10; i++) {
        params.set(`f_cf_field${i}`, `value${i}`)
      }

      const result = parseUrlToFilterState(params)

      expect(result).not.toBeNull()
      expect(Object.keys(result.customFields)).toHaveLength(10)
    })
  })
})

describe('serializeFilterStateToUrl', () => {
  it('returns empty params for null state', () => {
    const params = serializeFilterStateToUrl(null)
    expect(params.toString()).toBe('')
  })

  it('returns empty params for empty state', () => {
    const params = serializeFilterStateToUrl({})
    expect(params.toString()).toBe('')
  })

  it('serializes date range preset', () => {
    const filterState = {
      dateRange: {
        preset: '7days',
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_dr')).toBe('7days')
  })

  it('serializes custom date range', () => {
    const filterState = {
      dateRange: {
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_ds')).toBe('2024-01-01')
    expect(params.get('f_de')).toBe('2024-01-31')
  })

  it('serializes tags with match mode', () => {
    const filterState = {
      tags: {
        selected: ['moth', 'luna'],
        matchMode: 'all',
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_tags')).toBe('moth,luna')
    expect(params.get('f_tm')).toBe('all')
  })

  it('URL-encodes tags with special characters', () => {
    const filterState = {
      tags: {
        selected: ['Luna Moth', 'Actias luna'],
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_tags')).toBe('Luna%20Moth,Actias%20luna')
  })

  it('serializes species', () => {
    const filterState = {
      species: {
        selected: ['Actias luna', 'Papilio'],
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_species')).toBe('Actias%20luna,Papilio')
  })

  it('serializes includeUnidentified flag', () => {
    const filterState = {
      species: {
        includeUnidentified: true,
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_ui')).toBe('1')
  })

  it('serializes file types', () => {
    const filterState = {
      fileTypes: {
        selected: ['jpg', 'png'],
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_ft')).toBe('jpg,png')
  })

  it('serializes ISO range', () => {
    const filterState = {
      cameraSettings: {
        iso: {
          min: 100,
          max: 3200,
        },
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_iso')).toBe('100-3200')
  })

  it('serializes aperture range', () => {
    const filterState = {
      cameraSettings: {
        aperture: {
          min: 2.8,
          max: 8,
        },
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_ap')).toBe('2.8-8')
  })

  it('serializes shutter speed range', () => {
    const filterState = {
      cameraSettings: {
        shutterSpeed: {
          min: 0.001,
          max: 0.016,
        },
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_ss')).toBe('0.001-0.016')
  })

  it('serializes hasNotes flag (true)', () => {
    const filterState = {
      notes: {
        hasNotes: true,
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_hn')).toBe('1')
  })

  it('serializes hasNotes flag (false)', () => {
    const filterState = {
      notes: {
        hasNotes: false,
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_hn')).toBe('0')
  })

  it('serializes notes keywords', () => {
    const filterState = {
      notes: {
        keywords: 'specimen',
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_nk')).toBe('specimen')
  })

  it('URL-encodes notes keywords', () => {
    const filterState = {
      notes: {
        keywords: 'rare specimen',
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_nk')).toBe('rare%20specimen')
  })

  it('serializes custom fields', () => {
    const filterState = {
      customFields: {
        location: 'forest',
        weather: 'sunny',
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_cf_location')).toBe('forest')
    expect(params.get('f_cf_weather')).toBe('sunny')
  })

  it('URL-encodes custom fields', () => {
    const filterState = {
      customFields: {
        location: 'Oak Forest',
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_cf_location')).toBe('Oak%20Forest')
  })

  it('skips null/empty custom field values', () => {
    const filterState = {
      customFields: {
        location: 'forest',
        weather: null,
        temperature: '',
        humidity: undefined,
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_cf_location')).toBe('forest')
    expect(params.get('f_cf_weather')).toBeNull()
    expect(params.get('f_cf_temperature')).toBeNull()
    expect(params.get('f_cf_humidity')).toBeNull()
  })

  it('serializes complex combined filters', () => {
    const filterState = {
      dateRange: {
        preset: '7days',
      },
      tags: {
        selected: ['moth', 'luna'],
        matchMode: 'all',
      },
      species: {
        selected: ['Actias luna'],
        includeUnidentified: true,
      },
      cameraSettings: {
        iso: {
          min: 100,
          max: 3200,
        },
      },
      notes: {
        hasNotes: true,
      },
      customFields: {
        location: 'forest',
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_dr')).toBe('7days')
    expect(params.get('f_tags')).toBe('moth,luna')
    expect(params.get('f_tm')).toBe('all')
    expect(params.get('f_species')).toBe('Actias%20luna')
    expect(params.get('f_ui')).toBe('1')
    expect(params.get('f_iso')).toBe('100-3200')
    expect(params.get('f_hn')).toBe('1')
    expect(params.get('f_cf_location')).toBe('forest')
  })

  it('handles partial ranges (min only)', () => {
    const filterState = {
      cameraSettings: {
        iso: {
          min: 100,
          max: null,
        },
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_iso')).toBe('100-')
  })

  it('handles partial ranges (max only)', () => {
    const filterState = {
      cameraSettings: {
        iso: {
          min: null,
          max: 3200,
        },
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_iso')).toBe('-3200')
  })

  it('skips empty ranges', () => {
    const filterState = {
      cameraSettings: {
        iso: {
          min: null,
          max: null,
        },
      },
    }
    const params = serializeFilterStateToUrl(filterState)
    expect(params.get('f_iso')).toBeNull()
  })
})

describe('Round-trip serialization', () => {
  it('preserves filter state through parse -> serialize cycle', () => {
    const originalState = {
      dateRange: {
        preset: '7days',
      },
      tags: {
        selected: ['moth', 'luna'],
        matchMode: 'all',
      },
      species: {
        selected: ['Actias luna'],
        includeUnidentified: true,
      },
      fileTypes: {
        selected: ['jpg', 'png'],
      },
      cameraSettings: {
        iso: { min: 100, max: 3200 },
        aperture: { min: 2.8, max: 8 },
        shutterSpeed: { min: 0.001, max: 0.016 },
      },
      notes: {
        hasNotes: true,
        keywords: 'specimen',
      },
      customFields: {
        location: 'forest',
        weather: 'sunny',
      },
    }

    const params = serializeFilterStateToUrl(originalState)
    const parsedState = parseUrlToFilterState(params)

    expect(parsedState).toEqual(originalState)
  })

  it('preserves filter state through serialize -> parse cycle', () => {
    const urlString =
      'f_dr=7days&f_tags=moth,luna&f_tm=all&f_species=Actias%20luna&f_ui=1&f_ft=jpg,png&f_iso=100-3200&f_ap=2.8-8&f_ss=0.001-0.016&f_hn=1&f_nk=specimen&f_cf_location=forest&f_cf_weather=sunny'
    const params = new URLSearchParams(urlString)
    const parsedState = parseUrlToFilterState(params)
    const serializedParams = serializeFilterStateToUrl(parsedState)

    // Decode both for comparison (URL encoding is implementation detail)
    const decodeParams = (params) => {
      const decoded = {}
      for (const [key, value] of params.entries()) {
        decoded[key] = decodeURIComponent(value)
      }
      return decoded
    }

    const originalDecoded = decodeParams(params)
    const resultDecoded = decodeParams(serializedParams)

    expect(resultDecoded).toEqual(originalDecoded)
  })
})

describe('useFilterUrlSync hook', () => {
  let originalLocation
  let replaceStateSpy

  beforeEach(() => {
    // Save original location
    originalLocation = window.location

    // Mock window.location
    delete window.location
    window.location = {
      pathname: '/gallery',
      search: '',
      href: 'http://localhost/gallery',
    }

    // Mock history.replaceState
    replaceStateSpy = vi.spyOn(window.history, 'replaceState').mockImplementation(() => {})
  })

  afterEach(() => {
    // Restore original location
    window.location = originalLocation

    // Restore replaceState
    replaceStateSpy.mockRestore()

    vi.clearAllTimers()
  })

  it('loads filter state from URL on mount', () => {
    window.location.search = '?f_tags=moth&f_tm=any'

    const loadState = vi.fn()
    const filterState = {}

    renderHook(() => useFilterUrlSync(filterState, loadState))

    expect(loadState).toHaveBeenCalledWith({
      tags: {
        selected: ['moth'],
        matchMode: 'any',
      },
    })
  })

  it('does not load state if URL has no filters', () => {
    window.location.search = ''

    const loadState = vi.fn()
    const filterState = {}

    renderHook(() => useFilterUrlSync(filterState, loadState))

    expect(loadState).not.toHaveBeenCalled()
  })

  it('updates URL when filter state changes', () => {
    vi.useFakeTimers()

    window.location.search = ''

    const loadState = vi.fn()
    const { rerender } = renderHook(
      ({ filterState }) => useFilterUrlSync(filterState, loadState),
      {
        initialProps: {
          filterState: {},
        },
      }
    )

    // Change filter state
    const newFilterState = {
      tags: {
        selected: ['moth'],
        matchMode: 'any',
      },
    }

    rerender({ filterState: newFilterState })

    // Fast-forward debounce timer
    vi.advanceTimersByTime(300)

    expect(replaceStateSpy).toHaveBeenCalled()
    const [, , newUrl] = replaceStateSpy.mock.calls[0]
    expect(newUrl).toContain('f_tags=moth')
    expect(newUrl).toContain('f_tm=any')

    vi.useRealTimers()
  })

  it('debounces URL updates', () => {
    vi.useFakeTimers()

    window.location.search = ''

    const loadState = vi.fn()
    const { rerender } = renderHook(
      ({ filterState }) => useFilterUrlSync(filterState, loadState),
      {
        initialProps: {
          filterState: {},
        },
      }
    )

    // Rapidly change filter state multiple times
    rerender({
      filterState: {
        tags: { selected: ['moth'], matchMode: 'any' },
      },
    })

    vi.advanceTimersByTime(100)

    rerender({
      filterState: {
        tags: { selected: ['moth', 'luna'], matchMode: 'any' },
      },
    })

    vi.advanceTimersByTime(100)

    rerender({
      filterState: {
        tags: { selected: ['moth', 'luna', 'actias'], matchMode: 'all' },
      },
    })

    // Fast-forward past debounce
    vi.advanceTimersByTime(300)

    // Should only update URL once with the final state
    expect(replaceStateSpy).toHaveBeenCalledTimes(1)
    const [, , newUrl] = replaceStateSpy.mock.calls[0]
    // URL encoding converts commas to %2C
    expect(newUrl).toContain('f_tags=moth%2Cluna%2Cactias')
    expect(newUrl).toContain('f_tm=all')

    vi.useRealTimers()
  })

  it('clears URL params when filters are cleared', () => {
    vi.useFakeTimers()

    window.location.search = '?f_tags=moth'

    const loadState = vi.fn()
    const { rerender } = renderHook(
      ({ filterState }) => useFilterUrlSync(filterState, loadState),
      {
        initialProps: {
          filterState: {
            tags: { selected: ['moth'], matchMode: 'any' },
          },
        },
      }
    )

    // Clear filters
    rerender({ filterState: {} })

    // Fast-forward debounce timer
    vi.advanceTimersByTime(300)

    expect(replaceStateSpy).toHaveBeenCalled()
    const [, , newUrl] = replaceStateSpy.mock.calls[0]
    expect(newUrl).toBe('/gallery')

    vi.useRealTimers()
  })

  it('does not update URL if state matches last synced state', () => {
    vi.useFakeTimers()

    window.location.search = ''

    const loadState = vi.fn()
    const filterState = {
      tags: { selected: ['moth'], matchMode: 'any' },
    }

    const { rerender } = renderHook(
      ({ filterState }) => useFilterUrlSync(filterState, loadState),
      {
        initialProps: { filterState },
      }
    )

    // First update from initial state
    vi.advanceTimersByTime(300)

    // Clear the spy for the next check
    replaceStateSpy.mockClear()

    // Re-render with the same state
    rerender({ filterState })

    vi.advanceTimersByTime(300)

    // Should not have called replaceState again (state hasn't changed)
    expect(replaceStateSpy).not.toHaveBeenCalled()

    vi.useRealTimers()
  })

  it('uses replaceState instead of pushState', () => {
    vi.useFakeTimers()

    window.location.search = ''

    // Spy on pushState too
    const pushStateSpy = vi.spyOn(window.history, 'pushState').mockImplementation(() => {})

    const loadState = vi.fn()
    const { rerender } = renderHook(
      ({ filterState }) => useFilterUrlSync(filterState, loadState),
      {
        initialProps: {
          filterState: {},
        },
      }
    )

    // Change filter state
    rerender({
      filterState: {
        tags: { selected: ['moth'], matchMode: 'any' },
      },
    })

    vi.advanceTimersByTime(300)

    expect(replaceStateSpy).toHaveBeenCalled()
    expect(pushStateSpy).not.toHaveBeenCalled()

    pushStateSpy.mockRestore()
    vi.useRealTimers()
  })
})

describe('areFilterStatesEqual', () => {
  describe('basic equality', () => {
    it('returns true for same reference', () => {
      const state = { tags: { selected: ['moth'], matchMode: 'any' } }
      expect(areFilterStatesEqual(state, state)).toBe(true)
    })

    it('returns true for both null', () => {
      expect(areFilterStatesEqual(null, null)).toBe(true)
    })

    it('returns true for both undefined', () => {
      expect(areFilterStatesEqual(undefined, undefined)).toBe(true)
    })

    it('returns false when one is null', () => {
      expect(areFilterStatesEqual({ tags: { selected: ['moth'] } }, null)).toBe(false)
      expect(areFilterStatesEqual(null, { tags: { selected: ['moth'] } })).toBe(false)
    })

    it('returns true for empty objects', () => {
      expect(areFilterStatesEqual({}, {})).toBe(true)
    })
  })

  describe('property order independence', () => {
    it('returns true for tags with different property order', () => {
      const state1 = { tags: { selected: ['moth'], matchMode: 'any' } }
      const state2 = { tags: { matchMode: 'any', selected: ['moth'] } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })

    it('returns true for dateRange with different property order', () => {
      const state1 = { dateRange: { preset: '7days', startDate: '2024-01-01', endDate: '2024-01-31' } }
      const state2 = { dateRange: { endDate: '2024-01-31', preset: '7days', startDate: '2024-01-01' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })

    it('returns true for species with different property order', () => {
      const state1 = { species: { selected: ['Actias luna'], includeUnidentified: true } }
      const state2 = { species: { includeUnidentified: true, selected: ['Actias luna'] } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })

    it('returns true for cameraSettings with different property order', () => {
      const state1 = { cameraSettings: { iso: { min: 100, max: 3200 }, aperture: { min: 2.8, max: 8 } } }
      const state2 = { cameraSettings: { aperture: { min: 2.8, max: 8 }, iso: { min: 100, max: 3200 } } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })

    it('returns true for notes with different property order', () => {
      const state1 = { notes: { hasNotes: true, keywords: 'specimen' } }
      const state2 = { notes: { keywords: 'specimen', hasNotes: true } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })
  })

  describe('array order independence', () => {
    it('returns true for tags with same values in different order', () => {
      const state1 = { tags: { selected: ['moth', 'luna', 'actias'], matchMode: 'any' } }
      const state2 = { tags: { selected: ['actias', 'moth', 'luna'], matchMode: 'any' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })

    it('returns true for species with same values in different order', () => {
      const state1 = { species: { selected: ['Actias luna', 'Papilio'] } }
      const state2 = { species: { selected: ['Papilio', 'Actias luna'] } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })

    it('returns true for fileTypes with same values in different order', () => {
      const state1 = { fileTypes: { selected: ['jpg', 'png', 'raw'] } }
      const state2 = { fileTypes: { selected: ['raw', 'jpg', 'png'] } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })
  })

  describe('difference detection', () => {
    it('returns false for different tag selections', () => {
      const state1 = { tags: { selected: ['moth'], matchMode: 'any' } }
      const state2 = { tags: { selected: ['luna'], matchMode: 'any' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(false)
    })

    it('returns false for different tag match modes', () => {
      const state1 = { tags: { selected: ['moth'], matchMode: 'any' } }
      const state2 = { tags: { selected: ['moth'], matchMode: 'all' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(false)
    })

    it('returns false for different dateRange presets', () => {
      const state1 = { dateRange: { preset: '7days' } }
      const state2 = { dateRange: { preset: '30days' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(false)
    })

    it('returns false for different camera settings', () => {
      const state1 = { cameraSettings: { iso: { min: 100, max: 3200 } } }
      const state2 = { cameraSettings: { iso: { min: 200, max: 3200 } } }
      expect(areFilterStatesEqual(state1, state2)).toBe(false)
    })

    it('returns false for different custom fields', () => {
      const state1 = { customFields: { location: 'forest' } }
      const state2 = { customFields: { location: 'meadow' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(false)
    })

    it('returns false for different number of custom fields', () => {
      const state1 = { customFields: { location: 'forest' } }
      const state2 = { customFields: { location: 'forest', weather: 'sunny' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(false)
    })
  })

  describe('null vs undefined vs missing', () => {
    it('returns true when both tags are missing', () => {
      const state1 = { dateRange: { preset: '7days' } }
      const state2 = { dateRange: { preset: '7days' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })

    it('returns false when one has tags and other does not', () => {
      const state1 = { tags: { selected: ['moth'], matchMode: 'any' } }
      const state2 = {}
      expect(areFilterStatesEqual(state1, state2)).toBe(false)
    })

    it('handles empty arrays correctly', () => {
      const state1 = { tags: { selected: [], matchMode: 'any' } }
      const state2 = { tags: { selected: [], matchMode: 'any' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })

    it('returns false for empty vs non-empty arrays', () => {
      const state1 = { tags: { selected: [], matchMode: 'any' } }
      const state2 = { tags: { selected: ['moth'], matchMode: 'any' } }
      expect(areFilterStatesEqual(state1, state2)).toBe(false)
    })
  })

  describe('complex combined states', () => {
    it('returns true for identical complex states', () => {
      const state1 = {
        dateRange: { preset: '7days' },
        tags: { selected: ['moth', 'luna'], matchMode: 'all' },
        species: { selected: ['Actias luna'], includeUnidentified: true },
        fileTypes: { selected: ['jpg', 'png'] },
        cameraSettings: {
          iso: { min: 100, max: 3200 },
          aperture: { min: 2.8, max: 8 },
        },
        notes: { hasNotes: true, keywords: 'specimen' },
        customFields: { location: 'forest', weather: 'sunny' },
      }
      const state2 = {
        dateRange: { preset: '7days' },
        tags: { selected: ['moth', 'luna'], matchMode: 'all' },
        species: { selected: ['Actias luna'], includeUnidentified: true },
        fileTypes: { selected: ['jpg', 'png'] },
        cameraSettings: {
          iso: { min: 100, max: 3200 },
          aperture: { min: 2.8, max: 8 },
        },
        notes: { hasNotes: true, keywords: 'specimen' },
        customFields: { location: 'forest', weather: 'sunny' },
      }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })

    it('returns true for complex states with different property/array order', () => {
      const state1 = {
        dateRange: { preset: '7days' },
        tags: { selected: ['moth', 'luna'], matchMode: 'all' },
        species: { selected: ['Actias luna', 'Papilio'] },
      }
      const state2 = {
        species: { selected: ['Papilio', 'Actias luna'] },
        tags: { matchMode: 'all', selected: ['luna', 'moth'] },
        dateRange: { preset: '7days' },
      }
      expect(areFilterStatesEqual(state1, state2)).toBe(true)
    })
  })
})
