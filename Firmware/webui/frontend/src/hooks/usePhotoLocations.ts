import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { getPhotoLocations } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'

interface PhotoLocation {
  filename: string
  path: string
  latitude: number
  longitude: number
  timestamp: string
}

interface PhotoLocationsData {
  locations: PhotoLocation[]
  total_with_gps: number
  total_without_gps: number
}

interface PhotoLocationsParams {
  limit?: number
}

interface PhotoLocationsOptions {
  enabled?: boolean
}

interface UsePhotoLocationsResult {
  locations: PhotoLocation[]
  isLoading: boolean
  isError: boolean
  error: Error | null
  totalWithGps: number
  totalWithoutGps: number
  refetch: () => void
}

/**
 * Custom hook for fetching photo locations using TanStack Query
 *
 * Fetches photos with GPS coordinates for map display. Returns location data
 * along with counts of photos with and without GPS data.
 *
 * @param params - Query parameters for the API
 * @param params.limit - Maximum number of photos to return (1-10000)
 * @param options - TanStack Query options
 * @param options.enabled - Whether to enable the query
 * @returns Object containing locations, loading state, and statistics
 *
 * @example
 * const { locations, isLoading, totalWithGps } = usePhotoLocations()
 * // locations: Array of { filename, path, latitude, longitude, timestamp }
 * // totalWithGps: Count of photos with GPS data
 *
 * @example
 * // With custom limit
 * const { locations } = usePhotoLocations({ limit: 500 })
 *
 * @example
 * // With conditional fetching
 * const { locations, refetch } = usePhotoLocations({}, { enabled: false })
 * // Later: refetch() to manually trigger fetch
 */
export function usePhotoLocations(
  params: PhotoLocationsParams = {},
  options: PhotoLocationsOptions = {}
): UsePhotoLocationsResult {
  const { enabled = true } = options

  // Build query key - include params for cache differentiation
  const hasParams = Object.keys(params).length > 0
  const queryKey = hasParams
    ? [...QUERY_KEYS.PHOTO_LOCATIONS, params]
    : QUERY_KEYS.PHOTO_LOCATIONS

  const query: UseQueryResult<PhotoLocationsData, Error> = useQuery({
    queryKey,

    queryFn: async () => {
      const data = await getPhotoLocations(params)
      return data
    },

    enabled,

    // Cache configuration
    staleTime: 2 * 60 * 1000, // 2 minutes - location data changes less frequently
    gcTime: 10 * 60 * 1000, // 10 minutes
  })

  // Extract data with safe defaults
  const locations = query.data?.locations || []
  const totalWithGps = query.data?.total_with_gps || 0
  const totalWithoutGps = query.data?.total_without_gps || 0

  return {
    locations,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    totalWithGps,
    totalWithoutGps,
    refetch: query.refetch,
  }
}
