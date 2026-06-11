import { useMutation, UseMutationResult } from '@tanstack/react-query'
import { api } from '../utils/api'

export interface PhotoAggregationFilter {
  date_start?: string
  date_end?: string
  deployment?: string
  tags?: string[]
  series_type?: 'hdr' | 'focus_bracket'
  has_species?: boolean
}

export interface PhotoAggregationParams {
  filter?: PhotoAggregationFilter
  tolerance_m?: number
}

export interface PhotoAggregationResult {
  photo_count: number
  date_start: string | null
  date_end: string | null
  latitude: number | null
  longitude: number | null
  altitude: number | null
  gps_consistent: boolean
  gps_error: string | null
  photos_with_gps: number
  photos_with_timestamp: number
}

export interface PhotoAggregationError {
  message: string
  status?: number
  code?: string
}

/**
 * Hook for aggregating photo metadata.
 *
 * Calls POST /api/export/aggregate with filter criteria.
 * Returns aggregated GPS (if consistent), date range, and stats.
 *
 * @returns TanStack Query mutation for photo aggregation
 *
 * @example
 * const aggregateMutation = usePhotoAggregation()
 *
 * // Trigger aggregation
 * aggregateMutation.mutate({
 *   filter: { date_start: '2024-01-01' },
 *   tolerance_m: 50.0
 * })
 *
 * // Access results
 * if (aggregateMutation.isSuccess) {
 *   const { date_start, date_end, latitude, longitude, gps_consistent } = aggregateMutation.data
 * }
 *
 * // Handle errors
 * if (aggregateMutation.isError) {
 *   console.error(aggregateMutation.error.message)
 * }
 */
export function usePhotoAggregation(): UseMutationResult<
  PhotoAggregationResult,
  PhotoAggregationError,
  PhotoAggregationParams
> {
  return useMutation({
    mutationFn: async ({ filter, tolerance_m = 50.0 }: PhotoAggregationParams) => {
      const response = await api.post('/export/aggregate', {
        filter,
        tolerance_m
      })
      return response.data
    }
  })
}
