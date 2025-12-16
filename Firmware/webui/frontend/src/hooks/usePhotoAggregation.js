import { useMutation } from '@tanstack/react-query'
import { api } from '../utils/api'

/**
 * Hook for aggregating photo metadata.
 *
 * Calls POST /api/export/aggregate with filter criteria.
 * Returns aggregated GPS (if consistent), date range, and stats.
 *
 * @returns {Object} TanStack Query mutation object
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
 */
export function usePhotoAggregation() {
  return useMutation({
    mutationFn: async ({ filter, tolerance_m = 50.0 }) => {
      const response = await api.post('/export/aggregate', {
        filter,
        tolerance_m
      })
      return response.data
    }
  })
}
