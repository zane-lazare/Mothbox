import { useQuery, UseQueryResult } from '@tanstack/react-query'
import { api } from '../utils/api'

interface FileMetadata {
  name: string
  size: number
  modified?: string
}

interface ExifMetadata {
  make?: string
  model?: string
  iso?: number
  aperture?: number
  shutter_speed?: number
  focal_length?: number
  exposure_mode?: string
  metering_mode?: string
  white_balance?: string
  [key: string]: unknown
}

interface GpsMetadata {
  lat?: number
  lon?: number
  altitude?: number
  precision?: number
}

export interface PhotoMetadata {
  file: FileMetadata
  exif: ExifMetadata
  gps: GpsMetadata
}

/**
 * Custom hook for fetching photo metadata using TanStack Query
 *
 * Fetches EXIF, GPS, and file metadata for a given photo path. The hook uses
 * TanStack Query for caching, loading states, and error handling.
 *
 * @param photoPath - Full path to the photo file (e.g., "/var/lib/mothbox/photos/photo.jpg")
 * @returns TanStack Query result object
 *
 * @example
 * const { data, isLoading, isError, error } = usePhotoMetadata('/var/lib/mothbox/photos/photo.jpg')
 *
 * if (isLoading) return <div>Loading metadata...</div>
 * if (isError) return <div>Error: {error.message}</div>
 * if (data) {
 *   return (
 *     <div>
 *       <p>File: {data.file.name}</p>
 *       <p>Size: {data.file.size} bytes</p>
 *       <p>GPS: {data.gps.lat}, {data.gps.lon}</p>
 *     </div>
 *   )
 * }
 */
export default function usePhotoMetadata(photoPath: string | null | undefined): UseQueryResult<PhotoMetadata, Error> {
  return useQuery({
    // Query key: unique identifier for this query in the cache
    // Format: ['photoMetadata', photoPath]
    queryKey: ['photoMetadata', photoPath],

    // Query function: fetches the metadata from the API
    queryFn: async () => {
      // Build API endpoint with URL-encoded photo path
      const endpoint = `/metadata/photo/${encodeURIComponent(photoPath!)}/metadata`

      // Fetch metadata from backend using centralized API client
      // This automatically includes CSRF tokens, base URL, and error handling
      const response = await api.get(endpoint)

      // Return the data from axios response
      return response.data
    },

    // Only fetch when photoPath is truthy (not null, undefined, or empty string)
    enabled: !!photoPath,

    // Cache configuration
    // staleTime: How long data is considered fresh (5 minutes)
    // After this time, data is marked as stale and will be refetched in the background
    staleTime: 5 * 60 * 1000, // 5 minutes in milliseconds

    // gcTime: How long inactive data stays in cache (10 minutes)
    // After this time, unused cached data is garbage collected
    gcTime: 10 * 60 * 1000, // 10 minutes in milliseconds
  })
}
