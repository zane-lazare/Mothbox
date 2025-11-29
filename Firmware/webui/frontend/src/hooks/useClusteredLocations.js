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

  return {
    clusters: data?.clusters || [],
    unclustered: data?.unclustered || [],
    metadata: data?.metadata || {},
    isLoading,
    error,
    settings,
    setEnabled,
    setRadius,
    setMinSize,
    refetch,
  }
}

export default useClusteredLocations
