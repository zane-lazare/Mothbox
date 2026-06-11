import { useQuery, UseQueryResult } from '@tanstack/react-query'
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

interface ClusteringSettings {
  enabled: boolean
  radius: number
  minSize: number
}

interface RawPhoto {
  path: string
  lat: number
  lon: number
  timestamp?: string
  tags?: string[]
}

interface NormalizedPhoto {
  path: string
  filename: string
  latitude: number
  longitude: number
  thumbnail_url: string
  timestamp?: string
  tags?: string[]
  lat: number
  lon: number
}

interface PhotoCluster {
  centroid: { lat: number; lng: number }
  photo_count: number
  photos: NormalizedPhoto[]
  bounds: {
    min_lat: number
    max_lat: number
    min_lng: number
    max_lng: number
  }
}

interface ClusteringMetadata {
  total_photos: number
  cluster_count: number
  unclustered_count: number
  processing_time_ms?: number
  partial_result?: boolean
  warning?: string
}

interface ClusteredLocationsData {
  clusters: PhotoCluster[]
  unclustered: NormalizedPhoto[]
  metadata: ClusteringMetadata
}

export interface UseClusteredLocationsOptions {
  enabled?: boolean
}

export interface UseClusteredLocationsResult {
  clusters: PhotoCluster[]
  unclustered: NormalizedPhoto[]
  metadata: ClusteringMetadata
  isLoading: boolean
  error: Error | null
  isPartialResult: boolean
  partialWarning: string | null
  settings: ClusteringSettings
  setEnabled: (enabled: boolean) => void
  setRadius: (radius: number) => void
  setMinSize: (minSize: number) => void
  refetch: () => void
}

/**
 * Get saved settings from localStorage
 */
function getSavedSettings(): ClusteringSettings {
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
function saveSettings(settings: ClusteringSettings): void {
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
 * @param photo - Raw photo data from backend API
 * @returns Normalized photo object with guaranteed fields
 */
function normalizePhoto(photo: RawPhoto): NormalizedPhoto {
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
function normalizeUnclusteredPhotos(photos: RawPhoto[]): NormalizedPhoto[] {
  return photos.map(normalizePhoto)
}

/**
 * Normalize cluster data including photos within clusters.
 */
function normalizeClusters(clusters: PhotoCluster[]): PhotoCluster[] {
  return clusters.map((cluster) => ({
    ...cluster,
    photos: cluster.photos.map(normalizePhoto),
  }))
}

/**
 * Fetch clustered locations from API
 */
async function fetchClusteredLocations({ enabled, radius, minSize }: ClusteringSettings): Promise<ClusteredLocationsData> {
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
 * @param options - Hook options
 * @param options.enabled - Whether to enable the query (useful for conditional fetching)
 * @returns Clustering state and controls
 *
 * @example
 * const { clusters, unclustered, isLoading, settings, setRadius } = useClusteredLocations()
 */
export function useClusteredLocations(options: UseClusteredLocationsOptions = {}): UseClusteredLocationsResult {
  const { enabled: queryEnabled = true } = options
  const [settings, setSettings] = useState<ClusteringSettings>(getSavedSettings)

  // Save settings to localStorage when they change
  useEffect(() => {
    saveSettings(settings)
  }, [settings])

  // Fetch clustered locations
  const { data, isLoading, error, refetch }: UseQueryResult<ClusteredLocationsData, Error> = useQuery({
    queryKey: ['clusteredLocations', settings],
    queryFn: () => fetchClusteredLocations(settings),
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: false,
    enabled: queryEnabled,
  })

  // Settings setters
  const setEnabled = useCallback((enabled: boolean) => {
    setSettings((prev) => ({ ...prev, enabled }))
  }, [])

  const setRadius = useCallback((radius: number) => {
    setSettings((prev) => ({ ...prev, radius }))
  }, [])

  const setMinSize = useCallback((minSize: number) => {
    setSettings((prev) => ({ ...prev, minSize }))
  }, [])

  // Extract partial result indicators from metadata
  const isPartialResult = data?.metadata?.partial_result ?? false
  const partialWarning = data?.metadata?.warning ?? null

  return {
    clusters: normalizeClusters(data?.clusters || []),
    unclustered: normalizeUnclusteredPhotos(data?.unclustered || []),
    metadata: data?.metadata || {} as ClusteringMetadata,
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
