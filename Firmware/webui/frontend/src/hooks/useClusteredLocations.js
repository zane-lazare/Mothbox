import { useQuery } from '@tanstack/react-query'
import { useState, useCallback, useEffect } from 'react'
import { getClusteredLocations } from '../utils/api'

const STORAGE_KEY = 'mothbox_clustering_settings'

// Default clustering settings
const DEFAULT_SETTINGS = {
  enabled: true,
  radius: 100, // meters
  minSize: 2,
}

/**
 * Get saved settings from localStorage
 */
function getSavedSettings() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) }
    }
  } catch (e) {
    console.warn('Failed to parse clustering settings:', e)
  }
  return DEFAULT_SETTINGS
}

/**
 * Save settings to localStorage
 */
function saveSettings(settings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch (e) {
    console.warn('Failed to save clustering settings:', e)
  }
}

/**
 * Normalize unclustered photo data to expected field names.
 * Backend returns: photo_id, lat, lon, timestamp, tags
 * Frontend expects: filename, latitude, longitude, thumbnail_url, timestamp
 */
function normalizeUnclusteredPhotos(photos) {
  return photos.map((photo) => ({
    filename: photo.photo_id,
    latitude: photo.lat,
    longitude: photo.lon,
    thumbnail_url: `/api/gallery/photos/${encodeURIComponent(photo.photo_id)}/thumbnail`,
    timestamp: photo.timestamp,
    tags: photo.tags,
    // Preserve original fields for backward compatibility
    photo_id: photo.photo_id,
    lat: photo.lat,
    lon: photo.lon,
  }))
}

/**
 * Fetch clustered locations from API
 */
async function fetchClusteredLocations({ enabled, radius, minSize }) {
  const params = {
    enabled: enabled.toString(),
    radius: radius.toString(),
    min_size: minSize.toString(),
  }

  return getClusteredLocations(params)
}

/**
 * Custom hook for managing clustered photo locations.
 *
 * @returns {Object} Clustering state and controls
 *   - clusters: Array of photo clusters
 *   - unclustered: Array of individual photos
 *   - metadata: Clustering metadata (total photos, processing time, etc.)
 *   - isLoading: Loading state
 *   - error: Error object if failed
 *   - isPartialResult: True if clustering timed out and returned partial results
 *   - partialWarning: Warning message when partial results are returned
 *   - settings: Current clustering settings
 *   - setEnabled: Toggle clustering on/off
 *   - setRadius: Set clustering radius in meters
 *   - setMinSize: Set minimum cluster size
 *   - refetch: Manually refetch data
 */
export function useClusteredLocations() {
  const [settings, setSettings] = useState(getSavedSettings)

  // Save settings to localStorage when they change
  useEffect(() => {
    saveSettings(settings)
  }, [settings])

  // Fetch clustered locations
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['clusteredLocations', settings],
    queryFn: () => fetchClusteredLocations(settings),
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: false,
  })

  // Settings setters
  const setEnabled = useCallback((enabled) => {
    setSettings((prev) => ({ ...prev, enabled }))
  }, [])

  const setRadius = useCallback((radius) => {
    setSettings((prev) => ({ ...prev, radius }))
  }, [])

  const setMinSize = useCallback((minSize) => {
    setSettings((prev) => ({ ...prev, minSize }))
  }, [])

  // Extract partial result indicators from metadata
  const isPartialResult = data?.metadata?.partial_result ?? false
  const partialWarning = data?.metadata?.warning ?? null

  return {
    clusters: data?.clusters || [],
    unclustered: normalizeUnclusteredPhotos(data?.unclustered || []),
    metadata: data?.metadata || {},
    isLoading,
    error,
    isPartialResult,
    partialWarning,
    settings,
    setEnabled,
    setRadius,
    setMinSize,
    refetch,
  }
}

export default useClusteredLocations
