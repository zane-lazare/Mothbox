import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { api } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { Photo } from '../types'

export interface SeriesParams {
  limit?: number
  offset?: number
  type?: 'hdr' | 'focus_bracket'
}

export interface SeriesOptions {
  enabled?: boolean
}

interface SeriesPagination {
  offset: number
  limit: number
  has_next: boolean
}

interface PhotoSeries {
  id: string
  series_type: 'hdr' | 'focus_bracket'
  photos: Photo[]
  count: number
  cover_photo?: Photo
}

interface SeriesListData {
  series: PhotoSeries[]
  total: number
  pagination: SeriesPagination
}

/**
 * Custom hook for fetching photo series list using TanStack Query
 *
 * Fetches a paginated list of photo series (HDR, Focus Bracket) from the API.
 * Supports filtering by series type and pagination parameters.
 *
 * @param params - Query parameters for the API
 * @param params.limit - Maximum number of series to return
 * @param params.offset - Starting offset for pagination
 * @param params.type - Filter by series type ('hdr' or 'focus_bracket')
 * @param options - TanStack Query options
 * @param options.enabled - Whether to enable the query
 * @returns TanStack Query result object
 *
 * @example
 * const { data, isLoading, isError } = useSeries()
 * // data.series: Array of series objects
 * // data.total: Total count of all series
 * // data.pagination: { offset, limit, has_next }
 *
 * @example
 * // With filtering
 * const { data } = useSeries({ type: 'hdr', limit: 20 })
 */
export function useSeries(
  params: SeriesParams = {},
  options: SeriesOptions = {}
): UseQueryResult<SeriesListData, Error> {
  const { enabled = true } = options

  // Build query key - include params for cache differentiation
  const hasParams = Object.keys(params).length > 0
  const queryKey = hasParams ? [...QUERY_KEYS.SERIES, params] : QUERY_KEYS.SERIES

  return useQuery({
    queryKey,

    queryFn: async () => {
      const response = await api.get('/gallery/series', { params })
      return response.data
    },

    enabled,

    // Cache configuration
    staleTime: 2 * 60 * 1000, // 2 minutes - series data changes less frequently
    gcTime: 10 * 60 * 1000, // 10 minutes
  })
}

/**
 * Custom hook for fetching a single photo series by ID using TanStack Query
 *
 * Fetches detailed information about a specific photo series including
 * all photos in the series with their metadata.
 *
 * @param seriesId - The unique series identifier
 * @returns TanStack Query result object
 *
 * @example
 * const { data, isLoading } = useSeriesById('hdr_moth_2024_01_15__10_00_00')
 *
 * if (data) {
 *   console.log(data.series_type) // 'hdr'
 *   console.log(data.photos) // Array of photo objects
 *   console.log(data.count) // Number of photos in series
 * }
 */
export function useSeriesById(seriesId: string | null | undefined): UseQueryResult<PhotoSeries, Error> {
  return useQuery({
    // Query key: unique identifier for this series in the cache
    queryKey: [QUERY_KEYS.SERIES[0], seriesId],

    queryFn: async () => {
      const endpoint = `/gallery/series/${encodeURIComponent(seriesId!)}`
      const response = await api.get(endpoint)
      return response.data
    },

    // Only fetch when seriesId is truthy
    enabled: !!seriesId,

    // Cache configuration
    staleTime: 5 * 60 * 1000, // 5 minutes - individual series data is more stable
    gcTime: 10 * 60 * 1000, // 10 minutes
  })
}
