import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { api } from '../utils/api'

/**
 * Transform photo metadata to include only selected fields
 *
 * @param {Array} photos - Array of photo metadata objects
 * @param {Array} selectedFields - Array of field names to include
 * @returns {Array} Filtered photo objects
 */
function filterFields(photos, selectedFields) {
  return photos.map(photo => {
    const filtered = {}
    selectedFields.forEach(field => {
      if (Object.hasOwn(photo, field)) {
        filtered[field] = photo[field]
      }
    })
    return filtered
  })
}

/**
 * Transform photo data to preview format
 *
 * @param {Array} photos - Array of photo metadata
 * @param {string} format - Export format (json, csv, darwin_core, inaturalist)
 * @param {Array} selectedFields - Fields to include in preview
 * @returns {Object} Formatted preview data
 */
function transformToFormat(photos, format, selectedFields) {
  const filteredPhotos = filterFields(photos, selectedFields)

  if (format === 'csv') {
    return {
      format: 'csv',
      headers: selectedFields,
      data: filteredPhotos
    }
  }

  // JSON, darwin_core, inaturalist all use JSON structure
  return {
    format,
    data: filteredPhotos
  }
}

/**
 * Custom hook for fetching export preview data
 *
 * Fetches sample photos (first 3 matching filter) and transforms them
 * to the specified export format with only selected fields.
 *
 * Features:
 * - Debounced queries (500ms) to avoid excessive API calls
 * - Automatic refetch when format, filter, or fields change
 * - Field filtering based on selectedFields
 * - Format transformation (JSON, CSV, etc.)
 *
 * @param {Object} params - Hook parameters
 * @param {string} params.format - Export format (json, csv, darwin_core, inaturalist)
 * @param {Object} params.filter - Filter criteria for photos
 * @param {Array} params.selectedFields - Fields to include in preview
 * @returns {Object} Query result with previewData, isLoading, isError, error
 *
 * @example
 * const { previewData, isLoading, error } = useExportPreview({
 *   format: 'json',
 *   filter: { date_start: '2024-01-01', tags: ['moth'] },
 *   selectedFields: ['filename', 'tags', 'latitude', 'longitude']
 * })
 *
 * if (isLoading) return <div>Loading preview...</div>
 * if (error) return <div>Error: {error.message}</div>
 * if (previewData) {
 *   console.log(previewData.format) // 'json'
 *   console.log(previewData.data)   // Array of photo objects with selected fields
 * }
 */
export default function useExportPreview({ format, filter, selectedFields }) {
  // Create stable query key including all dependencies
  const queryKey = useMemo(() => {
    return [
      'exportPreview',
      format,
      JSON.stringify(filter),
      selectedFields.sort().join(',')
    ]
  }, [format, filter, selectedFields])

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      // Build query parameters from filter
      const params = {
        limit: 3, // Always fetch first 3 photos for preview
        ...filter
      }

      // Convert tags array to comma-separated string if present
      if (filter.tags && Array.isArray(filter.tags)) {
        params.tags = filter.tags.join(',')
      }

      // Convert series_type to string if present
      if (filter.series_type) {
        params.series_type = filter.series_type
      }

      // Fetch sample photos from sidecar/photos endpoint
      const response = await api.get('/sidecar/photos', { params })

      const photos = response.data.photos || []

      // Transform to preview format
      return transformToFormat(photos, format, selectedFields)
    },

    // Enable query only if we have selectedFields
    enabled: selectedFields && selectedFields.length > 0,

    // Debounce: mark data as stale after 500ms
    staleTime: 500,

    // Keep in cache for 5 minutes
    gcTime: 5 * 60 * 1000,

    // Don't refetch on window focus (preview is not critical)
    refetchOnWindowFocus: false
  })

  return {
    previewData: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error
  }
}
