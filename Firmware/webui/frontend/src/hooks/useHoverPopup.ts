import { useState, useRef, useCallback, useEffect } from 'react'
import { HOVER_POPUP_CONFIG } from '../constants/config'

interface ClusterPosition {
  x: number
  y: number
}

interface ClusterCenter {
  lat: number
  lon: number
}

interface Cluster {
  cluster_id?: string
  center?: ClusterCenter
  [key: string]: unknown
}

interface UseHoverPopupResult {
  isVisible: boolean
  targetCluster: Cluster | null
  position: ClusterPosition | null
  handleMouseEnter: (cluster: Cluster, event: React.MouseEvent) => void
  handleMouseLeave: () => void
  handleClick: (cluster: Cluster) => void
  handlePopupOpen: (cluster: Cluster) => void
  handlePopupClose: () => void
  isMobile: boolean
}

/**
 * useHoverPopup Hook
 *
 * Manages hover state for map cluster popups with debouncing, show/hide delays,
 * and mobile touch detection. Provides consistent hover behavior across desktop
 * and mobile devices.
 *
 * @returns Popup state and handlers
 * @returns isVisible - Whether the popup should be displayed
 * @returns targetCluster - The cluster currently being hovered
 * @returns position - Popup position {x, y} relative to viewport
 * @returns handleMouseEnter - Handler for mouse enter events
 * @returns handleMouseLeave - Handler for mouse leave events
 * @returns handleClick - Handler for click/tap events (mobile)
 * @returns handlePopupOpen - Handler for Leaflet popup open events
 * @returns handlePopupClose - Handler for Leaflet popup close events
 * @returns isMobile - Whether the device is detected as mobile/touch
 *
 * @example
 * const {
 *   isVisible,
 *   targetCluster,
 *   position,
 *   handleMouseEnter,
 *   handleMouseLeave,
 *   isMobile
 * } = useHoverPopup()
 *
 * // Desktop: Use mouse events
 * <ClusterMarker
 *   onMouseEnter={(e) => handleMouseEnter(cluster, e)}
 *   onMouseLeave={handleMouseLeave}
 * />
 *
 * // Mobile: Use click events
 * <ClusterMarker
 *   onClick={() => handleClick(cluster)}
 * />
 */
export function useHoverPopup(): UseHoverPopupResult {
  // State management
  const [isVisible, setIsVisible] = useState(false)
  const [targetCluster, setTargetCluster] = useState<Cluster | null>(null)
  const [position, setPosition] = useState<ClusterPosition | null>(null)
  const [clickedClusterId, setClickedClusterId] = useState<string | null>(null)

  // Timer references for cleanup
  const showTimerRef = useRef<number | null>(null)
  const hideTimerRef = useRef<number | null>(null)

  // Detect mobile/touch devices
  const isMobile =
    typeof window !== 'undefined' &&
    ('ontouchstart' in window || window.matchMedia('(pointer: coarse)').matches)

  /**
   * Clear all pending timers
   */
  const clearTimers = useCallback(() => {
    if (showTimerRef.current) {
      clearTimeout(showTimerRef.current)
      showTimerRef.current = null
    }
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
  }, [])

  /**
   * Get a unique identifier for a cluster
   * Prefers native cluster_id, falls back to coordinate-based ID
   *
   * @param cluster - The cluster object
   * @returns Cluster identifier or null if invalid
   */
  const getClusterId = useCallback((cluster: Cluster): string | null => {
    // Prefer native cluster_id if available (better performance)
    if (cluster?.cluster_id) {
      return cluster.cluster_id
    }

    // Fallback to coordinate-based ID
    const lat = cluster?.center?.lat
    const lon = cluster?.center?.lon

    if (typeof lat !== 'number' || typeof lon !== 'number') {
      return null
    }

    // Use colon separator and fixed precision to avoid collisions
    return `${lat.toFixed(6)}:${lon.toFixed(6)}`
  }, [])

  /**
   * Handle mouse enter event
   *
   * Sets the target cluster and position immediately, then schedules
   * the popup to be shown after SHOW_DELAY_MS. Skips if this cluster
   * has an open click popup.
   *
   * @param cluster - The cluster being hovered
   * @param event - The mouse event containing position
   */
  const handleMouseEnter = useCallback(
    (cluster: Cluster, event: React.MouseEvent) => {
      // Skip hover if this cluster has click popup open
      const clusterId = getClusterId(cluster)
      if (clusterId && clickedClusterId === clusterId) {
        return
      }

      // Clear any pending timers
      clearTimers()

      // Set target and position immediately
      setTargetCluster(cluster)
      setPosition({ x: event.clientX, y: event.clientY })

      // Schedule popup to show after delay
      showTimerRef.current = window.setTimeout(() => {
        setIsVisible(true)
      }, HOVER_POPUP_CONFIG.SHOW_DELAY_MS)
    },
    [clearTimers, clickedClusterId, getClusterId]
  )

  /**
   * Handle mouse leave event
   *
   * Schedules the popup to be hidden after HIDE_DELAY_MS to prevent
   * flickering when the mouse briefly leaves and re-enters.
   */
  const handleMouseLeave = useCallback(() => {
    // Clear any pending timers
    clearTimers()

    // Schedule popup to hide after delay
    hideTimerRef.current = window.setTimeout(() => {
      setIsVisible(false)
      setTargetCluster(null)
      setPosition(null)
    }, HOVER_POPUP_CONFIG.HIDE_DELAY_MS)
  }, [clearTimers])

  /**
   * Handle click event (for mobile/touch devices)
   *
   * Toggles the popup visibility immediately without delays.
   * Sets the target cluster when showing.
   *
   * @param cluster - The cluster being clicked
   */
  const handleClick = useCallback((cluster: Cluster) => {
    setTargetCluster(cluster)
    setIsVisible((prev) => !prev)
  }, [])

  /**
   * Handle Leaflet popup open event
   *
   * Tracks which cluster has an open click popup so we can
   * suppress hover popups for that cluster.
   *
   * @param cluster - The cluster whose popup was opened
   */
  const handlePopupOpen = useCallback(
    (cluster: Cluster) => {
      const clusterId = getClusterId(cluster)
      setClickedClusterId(clusterId)
      // Also hide any visible hover popup for this cluster
      clearTimers()
      setIsVisible(false)
    },
    [getClusterId, clearTimers]
  )

  /**
   * Handle Leaflet popup close event
   *
   * Clears the clicked cluster ID so hover popups can work again.
   */
  const handlePopupClose = useCallback(() => {
    setClickedClusterId(null)
  }, [])

  /**
   * Cleanup timers on unmount
   */
  useEffect(() => {
    return clearTimers
  }, [clearTimers])

  return {
    isVisible,
    targetCluster,
    position,
    handleMouseEnter,
    handleMouseLeave,
    handleClick,
    handlePopupOpen,
    handlePopupClose,
    isMobile,
  }
}
