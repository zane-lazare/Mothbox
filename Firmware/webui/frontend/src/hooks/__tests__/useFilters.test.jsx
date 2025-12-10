import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useFilters, useDebouncedFilters } from '../useFilters'
import * as FilterContext from '../../contexts/FilterContext'
import * as filterQueryBuilder from '../../utils/filterQueryBuilder'

// Mock the FilterContext
vi.mock('../../contexts/FilterContext', () => ({
  useFilterContext: vi.fn(),
}))

// Spy on filterQueryBuilder functions
vi.mock('../../utils/filterQueryBuilder', async () => {
  const actual = await vi.importActual('../../utils/filterQueryBuilder')
  return {
    ...actual,
    buildFilterQuery: vi.fn(actual.buildFilterQuery),
    hasActiveFilters: vi.fn(actual.hasActiveFilters),
    countActiveFilters: vi.fn(actual.countActiveFilters),
    getActiveFilterSummaries: vi.fn(actual.getActiveFilterSummaries),
  }
})

describe('useFilters', () => {
  const mockContextValue = {
    dateRange: null,
    tags: { selected: [], matchMode: 'any' },
    species: { selected: [], includeUnidentified: false },
    fileTypes: { selected: [] },
    cameraSettings: {
      iso: { min: null, max: null },
      aperture: { min: null, max: null },
      shutterSpeed: { min: null, max: null },
    },
    notes: { hasNotes: null, keywords: '' },
    customFields: {},
    setDateRange: vi.fn(),
    setTags: vi.fn(),
    setSpecies: vi.fn(),
    setFileTypes: vi.fn(),
    setCameraSettings: vi.fn(),
    setNotes: vi.fn(),
    setCustomFields: vi.fn(),
    clearAllFilters: vi.fn(),
  }

  beforeEach(() => {
    FilterContext.useFilterContext.mockReturnValue(mockContextValue)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Functionality', () => {
    it('should return all context values', () => {
      const { result } = renderHook(() => useFilters())

      expect(result.current.dateRange).toEqual(mockContextValue.dateRange)
      expect(result.current.tags).toEqual(mockContextValue.tags)
      expect(result.current.species).toEqual(mockContextValue.species)
      expect(result.current.setDateRange).toBe(mockContextValue.setDateRange)
      expect(result.current.clearAllFilters).toBe(mockContextValue.clearAllFilters)
    })

    it('should compute searchQuery from filter state', () => {
      const { result } = renderHook(() => useFilters())

      expect(filterQueryBuilder.buildFilterQuery).toHaveBeenCalledWith({
        dateRange: mockContextValue.dateRange,
        tags: mockContextValue.tags,
        species: mockContextValue.species,
        notes: mockContextValue.notes,
        customFields: mockContextValue.customFields,
      })
      expect(result.current.searchQuery).toBeDefined()
    })

    it('should compute hasFilters from filter state', () => {
      const { result } = renderHook(() => useFilters())

      expect(filterQueryBuilder.hasActiveFilters).toHaveBeenCalledWith({
        dateRange: mockContextValue.dateRange,
        tags: mockContextValue.tags,
        species: mockContextValue.species,
        fileTypes: mockContextValue.fileTypes,
        cameraSettings: mockContextValue.cameraSettings,
        notes: mockContextValue.notes,
        customFields: mockContextValue.customFields,
      })
      expect(result.current.hasFilters).toBe(false)
    })

    it('should compute activeFilterCount from filter state', () => {
      const { result } = renderHook(() => useFilters())

      expect(filterQueryBuilder.countActiveFilters).toHaveBeenCalled()
      expect(typeof result.current.activeFilterCount).toBe('number')
    })

    it('should compute filterSummaries from filter state', () => {
      const { result } = renderHook(() => useFilters())

      expect(filterQueryBuilder.getActiveFilterSummaries).toHaveBeenCalled()
      expect(Array.isArray(result.current.filterSummaries)).toBe(true)
    })
  })

  describe('isFilterActive', () => {
    it('should detect active dateRange filter with preset', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        dateRange: { preset: 'today' },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('dateRange')).toBe(true)
    })

    it('should detect active dateRange filter with startDate', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        dateRange: { startDate: '2024-01-01' },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('dateRange')).toBe(true)
    })

    it('should detect active dateRange filter with endDate', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        dateRange: { endDate: '2024-12-31' },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('dateRange')).toBe(true)
    })

    it('should detect inactive dateRange filter', () => {
      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('dateRange')).toBe(false)
    })

    it('should detect active tags filter', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        tags: { selected: ['moth', 'butterfly'], matchMode: 'any' },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('tags')).toBe(true)
    })

    it('should detect inactive tags filter', () => {
      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('tags')).toBe(false)
    })

    it('should detect active species filter with selections', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        species: { selected: ['Actias luna'], includeUnidentified: false },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('species')).toBe(true)
    })

    it('should detect active species filter with includeUnidentified', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        species: { selected: [], includeUnidentified: true },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('species')).toBe(true)
    })

    it('should detect inactive species filter', () => {
      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('species')).toBe(false)
    })

    it('should detect active fileTypes filter', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        fileTypes: { selected: ['jpg', 'png'] },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('fileTypes')).toBe(true)
    })

    it('should detect active cameraSettings filter with ISO', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        cameraSettings: {
          iso: { min: 100, max: 800 },
          aperture: { min: null, max: null },
          shutterSpeed: { min: null, max: null },
        },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('cameraSettings')).toBe(true)
    })

    it('should detect active cameraSettings filter with aperture', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        cameraSettings: {
          iso: { min: null, max: null },
          aperture: { min: 1.4, max: 5.6 },
          shutterSpeed: { min: null, max: null },
        },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('cameraSettings')).toBe(true)
    })

    it('should detect active cameraSettings filter with shutterSpeed', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        cameraSettings: {
          iso: { min: null, max: null },
          aperture: { min: null, max: null },
          shutterSpeed: { min: 1 / 1000, max: 1 / 30 },
        },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('cameraSettings')).toBe(true)
    })

    it('should detect active notes filter with hasNotes true', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        notes: { hasNotes: true, keywords: '' },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('notes')).toBe(true)
    })

    it('should detect active notes filter with hasNotes false', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        notes: { hasNotes: false, keywords: '' },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('notes')).toBe(true)
    })

    it('should detect active notes filter with keywords', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        notes: { hasNotes: null, keywords: 'specimen' },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('notes')).toBe(true)
    })

    it('should detect active customFields filter', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        customFields: { location: 'backyard', weather: 'clear' },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('customFields')).toBe(true)
    })

    it('should detect inactive customFields filter with empty values', () => {
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        customFields: { location: '', weather: null },
      })

      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('customFields')).toBe(false)
    })

    it('should return false for unknown filter type', () => {
      const { result } = renderHook(() => useFilters())
      expect(result.current.isFilterActive('unknownType')).toBe(false)
    })
  })

  describe('Reactivity', () => {
    it('should recompute searchQuery when filters change', () => {
      const { result, rerender } = renderHook(() => useFilters())

      const initialQuery = result.current.searchQuery

      // Change tags filter
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        tags: { selected: ['moth'], matchMode: 'any' },
      })

      rerender()

      expect(result.current.searchQuery).not.toBe(initialQuery)
    })

    it('should recompute hasFilters when filters change', () => {
      const { result, rerender } = renderHook(() => useFilters())

      expect(result.current.hasFilters).toBe(false)

      // Add a date filter
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        dateRange: { preset: 'today' },
      })

      rerender()

      expect(result.current.hasFilters).toBe(true)
    })

    it('should recompute activeFilterCount when filters change', () => {
      const { result, rerender } = renderHook(() => useFilters())

      const initialCount = result.current.activeFilterCount

      // Add multiple filters
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        dateRange: { preset: 'today' },
        tags: { selected: ['moth'], matchMode: 'any' },
      })

      rerender()

      expect(result.current.activeFilterCount).toBeGreaterThan(initialCount)
    })

    it('should recompute filterSummaries when filters change', () => {
      const { result, rerender } = renderHook(() => useFilters())

      expect(result.current.filterSummaries.length).toBe(0)

      // Add filters
      FilterContext.useFilterContext.mockReturnValue({
        ...mockContextValue,
        tags: { selected: ['moth', 'butterfly'], matchMode: 'any' },
      })

      rerender()

      expect(result.current.filterSummaries.length).toBeGreaterThan(0)
    })
  })
})

describe('useDebouncedFilters', () => {
  const mockContextValue = {
    dateRange: null,
    tags: { selected: [], matchMode: 'any' },
    species: { selected: [], includeUnidentified: false },
    fileTypes: { selected: [] },
    cameraSettings: {
      iso: { min: null, max: null },
      aperture: { min: null, max: null },
      shutterSpeed: { min: null, max: null },
    },
    notes: { hasNotes: null, keywords: '' },
    customFields: {},
    setDateRange: vi.fn(),
    setTags: vi.fn(),
    setSpecies: vi.fn(),
    setFileTypes: vi.fn(),
    setCameraSettings: vi.fn(),
    setNotes: vi.fn(),
    setCustomFields: vi.fn(),
    clearAllFilters: vi.fn(),
  }

  beforeEach(() => {
    vi.useFakeTimers()
    FilterContext.useFilterContext.mockReturnValue(mockContextValue)
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
  })

  it('should return debounced query', () => {
    const { result } = renderHook(() => useDebouncedFilters())

    expect(result.current.debouncedQuery).toBeDefined()
    expect(result.current.hasFilters).toBeDefined()
    expect(result.current.activeFilterCount).toBeDefined()
    expect(result.current.isDebouncing).toBe(false)
  })

  it('should debounce query changes by default delay (300ms)', async () => {
    const { result, rerender } = renderHook(() => useDebouncedFilters())

    const initialQuery = result.current.debouncedQuery

    // Change filters
    FilterContext.useFilterContext.mockReturnValue({
      ...mockContextValue,
      tags: { selected: ['moth'], matchMode: 'any' },
    })

    rerender()

    // Initially, debounced query should not change
    expect(result.current.isDebouncing).toBe(true)
    expect(result.current.debouncedQuery).toBe(initialQuery)

    // Advance time by 200ms - still not updated
    act(() => {
      vi.advanceTimersByTime(200)
    })

    expect(result.current.isDebouncing).toBe(true)

    // Advance time by 100ms more (total 300ms) - now updated
    act(() => {
      vi.advanceTimersByTime(100)
    })

    expect(result.current.isDebouncing).toBe(false)
    expect(result.current.debouncedQuery).not.toBe(initialQuery)
  })

  it('should respect custom delay parameter', async () => {
    const { result, rerender } = renderHook(() => useDebouncedFilters(500))

    const initialQuery = result.current.debouncedQuery

    // Change filters
    FilterContext.useFilterContext.mockReturnValue({
      ...mockContextValue,
      tags: { selected: ['moth'], matchMode: 'any' },
    })

    rerender()

    // After 300ms, should still be debouncing
    act(() => {
      vi.advanceTimersByTime(300)
    })

    expect(result.current.isDebouncing).toBe(true)
    expect(result.current.debouncedQuery).toBe(initialQuery)

    // After 500ms total, should be updated
    act(() => {
      vi.advanceTimersByTime(200)
    })

    expect(result.current.isDebouncing).toBe(false)
    expect(result.current.debouncedQuery).not.toBe(initialQuery)
  })

  it('should cancel previous debounce on new change', async () => {
    const { result, rerender } = renderHook(() => useDebouncedFilters(300))

    const initialQuery = result.current.debouncedQuery

    // First change
    FilterContext.useFilterContext.mockReturnValue({
      ...mockContextValue,
      tags: { selected: ['moth'], matchMode: 'any' },
    })

    rerender()

    // Advance by 200ms
    act(() => {
      vi.advanceTimersByTime(200)
    })

    // Second change (should cancel previous timer)
    FilterContext.useFilterContext.mockReturnValue({
      ...mockContextValue,
      tags: { selected: ['moth', 'butterfly'], matchMode: 'any' },
    })

    rerender()

    // Advance by 200ms (total 400ms from first change, but only 200ms from second)
    act(() => {
      vi.advanceTimersByTime(200)
    })

    // Should still be debouncing
    expect(result.current.isDebouncing).toBe(true)

    // Advance by 100ms more (300ms from second change)
    act(() => {
      vi.advanceTimersByTime(100)
    })

    // Should be updated with second change
    expect(result.current.isDebouncing).toBe(false)
    expect(result.current.debouncedQuery).not.toBe(initialQuery)
  })

  it('should maintain hasFilters and activeFilterCount during debounce', () => {
    FilterContext.useFilterContext.mockReturnValue({
      ...mockContextValue,
      tags: { selected: ['moth'], matchMode: 'any' },
    })

    const { result } = renderHook(() => useDebouncedFilters())

    expect(result.current.hasFilters).toBe(true)
    expect(typeof result.current.activeFilterCount).toBe('number')
  })
})
