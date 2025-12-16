import { useMutation } from '@tanstack/react-query'
import { api } from '../utils/api'

/**
 * @typedef {Object} PhotoAggregationParams
 * @property {Object} [filter] - Filter criteria for photo selection
 * @property {string} [filter.date_start] - ISO 8601 start date
 * @property {string} [filter.date_end] - ISO 8601 end date
 * @property {string} [filter.deployment] - Deployment directory path
 * @property {string[]} [filter.tags] - Tags to filter by
 * @property {string} [filter.series_type] - "hdr" or "focus_bracket"
 * @property {boolean} [filter.has_species] - Only photos with species
 * @property {number} [tolerance_m=50.0] - GPS consistency tolerance in meters
 */

/**
 * @typedef {Object} PhotoAggregationResult
 * @property {number} photo_count - Total photos processed
 * @property {string|null} date_start - Earliest photo date (ISO 8601)
 * @property {string|null} date_end - Latest photo date (ISO 8601)
 * @property {number|null} latitude - GPS latitude (null if inconsistent)
 * @property {number|null} longitude - GPS longitude (null if inconsistent)
 * @property {number|null} altitude - GPS altitude in meters
 * @property {boolean} gps_consistent - True if all GPS within tolerance
 * @property {string|null} gps_error - Error message if GPS inconsistent
 * @property {number} photos_with_gps - Count of photos with GPS data
 * @property {number} photos_with_timestamp - Count of photos with timestamps
 */

/**
 * @typedef {Object} PhotoAggregationError
 * @property {string} message - Error message
 * @property {number} [status] - HTTP status code
 * @property {string} [code] - Error code from server
 */

/**
 * Hook for aggregating photo metadata.
 *
 * Calls POST /api/export/aggregate with filter criteria.
 * Returns aggregated GPS (if consistent), date range, and stats.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<PhotoAggregationResult, PhotoAggregationError, PhotoAggregationParams>}
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
