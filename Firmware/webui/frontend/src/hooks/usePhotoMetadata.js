import { useQuery } from '@tanstack/react-query'

/**
 * Custom hook for fetching photo metadata using TanStack Query
 *
 * Fetches EXIF, GPS, and file metadata for a given photo path. The hook uses
 * TanStack Query for caching, loading states, and error handling.
 *
 * @param {string|null|undefined} photoPath - Full path to the photo file (e.g., "/var/lib/mothbox/photos/photo.jpg")
 * @returns {object} TanStack Query result object containing:
 *   - data: Photo metadata object with file, exif, and gps properties
 *   - isLoading: Boolean indicating if the query is currently loading
 *   - isError: Boolean indicating if an error occurred
 *   - isSuccess: Boolean indicating if the query was successful
 *   - error: Error object if an error occurred, null otherwise
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
export default function usePhotoMetadata(photoPath) {
  return useQuery({
    // Query key: unique identifier for this query in the cache
    // Format: ['photoMetadata', photoPath]
    queryKey: ['photoMetadata', photoPath],

    // Query function: fetches the metadata from the API
    queryFn: async () => {
      // Build API endpoint with URL-encoded photo path
      const endpoint = `/api/metadata/photo/${encodeURIComponent(photoPath)}/metadata`

      // Fetch metadata from backend
      const response = await fetch(endpoint)

      // Handle non-OK responses
      if (!response.ok) {
        throw new Error(
          `Failed to fetch metadata: ${response.status} ${response.statusText}`
        )
      }

      // Parse and return JSON response
      const data = await response.json()
      return data
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
