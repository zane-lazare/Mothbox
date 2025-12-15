import { useQuery } from '@tanstack/react-query'
import { useState, useCallback, useEffect } from 'react'
import { getClusteredLocations } from '../utils/api'
import { getThumbnailUrl } from '../utils/thumbnailUrl'

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
 * Normalizes backend photo data to frontend field names.
 *
 * Backend API returns: path, lat, lon, timestamp, tags
 * Frontend expects: path, filename, latitude, longitude, thumbnail_url
 *
 * This normalization guarantees all fields exist, so consumers can
 * safely access photo.filename without fallback logic.
 *
 * @param {Object} photo - Raw photo data from backend API
 * @param {string} photo.path - Relative path from PHOTOS_DIR (e.g., "2024-11-10/photo.jpg")
 * @param {number} photo.lat - Latitude coordinate
 * @param {number} photo.lon - Longitude coordinate
 * @param {string} [photo.timestamp] - Photo timestamp
 * @param {string[]} [photo.tags] - Photo tags
 * @returns {Object} Normalized photo object with guaranteed fields
 */
function normalizePhoto(photo) {
  return {
    // Standardized field name
    path: photo.path,
    // Derived fields for UI components
    filename: (photo.path || '').split('/').pop() || photo.path || 'unknown',
    latitude: photo.lat,
    longitude: photo.lon,
    thumbnail_url: getThumbnailUrl(photo.path),
    timestamp: photo.timestamp,
    tags: photo.tags,
    // Preserve original lat/lon for components expecting them
    lat: photo.lat,
    lon: photo.lon,
  }
}

/**
 * Normalize unclustered photo data to expected field names.
 */
function normalizeUnclusteredPhotos(photos) {
  return photos.map(normalizePhoto)
}

/**
 * Normalize cluster data including photos within clusters.
 */
function normalizeClusters(clusters) {
  return clusters.map((cluster) => ({
    ...cluster,
    photos: cluster.photos.map(normalizePhoto),
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
 * @param {Object} options - Hook options
 * @param {boolean} [options.enabled=true] - Whether to enable the query (useful for conditional fetching)
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
export function useClusteredLocations(options = {}) {
  const { enabled: queryEnabled = true } = options
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
    enabled: queryEnabled,
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
    clusters: normalizeClusters(data?.clusters || []),
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
