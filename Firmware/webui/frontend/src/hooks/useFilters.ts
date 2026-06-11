/**
 * useFilters Hook
 *
 * Provides a convenient API for components to interact with filter state
 * and get computed values for the gallery filter drawer feature.
 *
 * Features:
 * - Access to all filter state from FilterContext
 * - Computed search query string for FTS5 API
 * - Active filter detection and counting
 * - Filter summaries for display chips
 * - Utility functions for checking filter states
 *
 * @module useFilters
 */

import { useMemo, useState, useEffect } from 'react'
import { useFilterContext } from '../contexts/FilterContext'
import {
  buildFilterQuery,
  hasActiveFilters,
  countActiveFilters,
  getActiveFilterSummaries,
} from '../utils/filterQueryBuilder'

interface UseFiltersResult {
  searchQuery: string
  hasFilters: boolean
  activeFilterCount: number
  filterSummaries: Array<{ type: string; label: string }>
  isFilterActive: (filterType: string) => boolean
  [key: string]: unknown
}

/**
 * Main filters hook
 *
 * @returns Filter state, computed values, and utility functions
 */
export function useFilters(): UseFiltersResult {
  const context = useFilterContext()

  // Get the filter query string for search API
  const searchQuery = useMemo(() => {
    return buildFilterQuery({
      dateRange: context.dateRange,
      tags: context.tags,
      species: context.species,
      notes: context.notes,
      customFields: context.customFields,
    })
  }, [
    context.dateRange,
    context.tags,
    context.species,
    context.notes,
    context.customFields,
  ])

  // Check if any filters are active
  const hasFilters = useMemo(() => {
    return hasActiveFilters({
      dateRange: context.dateRange,
      tags: context.tags,
      species: context.species,
      fileTypes: context.fileTypes,
      cameraSettings: context.cameraSettings,
      notes: context.notes,
      customFields: context.customFields,
    })
  }, [
    context.dateRange,
    context.tags,
    context.species,
    context.fileTypes,
    context.cameraSettings,
    context.notes,
    context.customFields,
  ])

  // Count active filter types
  const activeFilterCount = useMemo(() => {
    return countActiveFilters({
      dateRange: context.dateRange,
      tags: context.tags,
      species: context.species,
      fileTypes: context.fileTypes,
      cameraSettings: context.cameraSettings,
      notes: context.notes,
      customFields: context.customFields,
    })
  }, [
    context.dateRange,
    context.tags,
    context.species,
    context.fileTypes,
    context.cameraSettings,
    context.notes,
    context.customFields,
  ])

  // Get summaries for active filter chips
  const filterSummaries = useMemo(() => {
    return getActiveFilterSummaries({
      dateRange: context.dateRange,
      tags: context.tags,
      species: context.species,
      fileTypes: context.fileTypes,
      cameraSettings: context.cameraSettings,
      notes: context.notes,
      customFields: context.customFields,
    })
  }, [
    context.dateRange,
    context.tags,
    context.species,
    context.fileTypes,
    context.cameraSettings,
    context.notes,
    context.customFields,
  ])

  /**
   * Check if a specific filter type is active
   *
   * @param filterType - Filter type to check
   * @returns True if filter type has active values
   */
  const isFilterActive = (filterType: string): boolean => {
    switch (filterType) {
      case 'dateRange':
        return (
          !!context.dateRange?.preset ||
          !!context.dateRange?.startDate ||
          !!context.dateRange?.endDate
        )
      case 'tags':
        return context.tags?.selected?.length ? context.tags.selected.length > 0 : false
      case 'species':
        return (
          (context.species?.selected?.length ? context.species.selected.length > 0 : false) ||
          context.species?.includeUnidentified === true
        )
      case 'fileTypes':
        return context.fileTypes?.selected?.length ? context.fileTypes.selected.length > 0 : false
      case 'cameraSettings': {
        const { iso, aperture, shutterSpeed } = context.cameraSettings || {}
        return (
          iso?.min !== null ||
          iso?.max !== null ||
          aperture?.min !== null ||
          aperture?.max !== null ||
          shutterSpeed?.min !== null ||
          shutterSpeed?.max !== null
        )
      }
      case 'notes':
        return context.notes?.hasNotes !== null || !!context.notes?.keywords
      case 'customFields':
        if (!context.customFields) return false
        return Object.values(context.customFields).some(
          (v) => v !== null && v !== undefined && v !== ''
        )
      default:
        return false
    }
  }

  return {
    // State from context
    ...context,

    // Computed values
    searchQuery,
    hasFilters,
    activeFilterCount,
    filterSummaries,

    // Utility functions
    isFilterActive,
  }
}

interface UseDebouncedFiltersResult {
  debouncedQuery: string
  hasFilters: boolean
  activeFilterCount: number
  isDebouncing: boolean
}

/**
 * Debounced filters hook
 *
 * Returns debounced search query to avoid excessive API calls when
 * users are adjusting filters rapidly.
 *
 * @param delay - Debounce delay in milliseconds (default: 300)
 * @returns Debounced query and filter state
 */
export function useDebouncedFilters(delay = 300): UseDebouncedFiltersResult {
  const { searchQuery, hasFilters, activeFilterCount } = useFilters()
  const [debouncedQuery, setDebouncedQuery] = useState(searchQuery)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery)
    }, delay)

    return () => clearTimeout(timer)
  }, [searchQuery, delay])

  return {
    debouncedQuery,
    hasFilters,
    activeFilterCount,
    isDebouncing: debouncedQuery !== searchQuery,
  }
}
