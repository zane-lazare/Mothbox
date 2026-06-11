import { useEffect, useRef, useState } from 'react'
import ThumbnailGrid from './ThumbnailGrid'
import { HOVER_POPUP_CONFIG } from '../constants/config'
import { ThumbnailGridPhoto } from './ThumbnailGrid'

export interface MarkerHoverPopupCluster {
  cluster_id?: string
  center?: {
    lat: number
    lon: number
  }
  count: number
  photos?: ThumbnailGridPhoto[]
  date_range?: {
    earliest?: string
    latest?: string
  }
}

export interface MarkerHoverPopupPosition {
  x?: number
  y?: number
}

export interface MarkerHoverPopupProps {
  cluster: MarkerHoverPopupCluster | null
  isVisible: boolean
  position?: MarkerHoverPopupPosition
  onPhotoClick?: (photo: ThumbnailGridPhoto) => void
  onClose?: () => void
}

/**
 * MarkerHoverPopup - Displays photo preview popup when hovering over map markers
 *
 * Shows a popup with photo thumbnails, count, date range, and tags for a cluster
 * of photos at a specific location. Positioned absolutely in viewport coordinates.
 * Features smooth fade-in/fade-out animations for better UX.
 *
 * @component
 * @example
 * ```jsx
 * <MarkerHoverPopup
 *   cluster={clusterData}
 *   isVisible={true}
 *   position={{ x: 100, y: 200 }}
 *   onPhotoClick={(photo) => console.log('Photo clicked:', photo)}
 *   onClose={() => console.log('Close popup')}
 * />
 * ```
 */
function MarkerHoverPopup({
  cluster,
  isVisible,
  position,
  onPhotoClick,
  onClose,
}: MarkerHoverPopupProps) {
  const popupRef = useRef<HTMLDivElement>(null)
  const animationTimerRef = useRef<number | null>(null)
  const previousActiveElementRef = useRef<Element | null>(null)
  const isMountedRef = useRef(true)
  const [shouldRender, setShouldRender] = useState(false)
  const [isAnimating, setIsAnimating] = useState(false)

  // Track component mount state to prevent setState on unmounted component
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Handle animation state for smooth enter/exit transitions
  // Uses ref for timer to ensure cleanup on unmount
  useEffect(() => {
    if (isVisible) {
      // Show popup in DOM
      setShouldRender(true)
      // Trigger fade-in animation on next frame (ensures DOM is ready)
      requestAnimationFrame(() => {
        if (isMountedRef.current) {
          setIsAnimating(true)
        }
      })
    } else {
      // Start fade-out animation
      setIsAnimating(false)
      // Remove from DOM after animation completes
      animationTimerRef.current = window.setTimeout(() => {
        if (isMountedRef.current) {
          setShouldRender(false)
        }
      }, HOVER_POPUP_CONFIG.ANIMATION_DURATION)
    }

    return () => {
      if (animationTimerRef.current) {
        clearTimeout(animationTimerRef.current)
        animationTimerRef.current = null
      }
    }
  }, [isVisible])

  // Handle escape key to close popup
  useEffect(() => {
    if (!isVisible) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose?.()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isVisible, onClose])

  // Focus trap - Tab key cycles within popup
  useEffect(() => {
    if (!isVisible) return

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      // Get all focusable elements in popup
      const focusableElements = popupRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )

      if (!focusableElements?.length) return

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]

      // Shift+Tab on first element -> focus last element
      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault()
        lastElement.focus()
      }
      // Tab on last element -> focus first element
      else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault()
        firstElement.focus()
      }
    }

    document.addEventListener('keydown', handleTabKey)
    return () => document.removeEventListener('keydown', handleTabKey)
  }, [isVisible])

  // Focus management - save previous focus and restore on close (for accessibility)
  useEffect(() => {
    if (isVisible && popupRef.current) {
      // Save previously focused element before moving focus to popup
      previousActiveElementRef.current = document.activeElement
      popupRef.current.focus()
    } else if (!isVisible && previousActiveElementRef.current) {
      // Restore focus when popup closes
      if ('focus' in previousActiveElementRef.current) {
        (previousActiveElementRef.current as HTMLElement).focus?.()
      }
      previousActiveElementRef.current = null
    }
  }, [isVisible])

  // Don't render if not in DOM or no cluster data
  if (!shouldRender || !cluster) return null

  /**
   * Format date range for display
   * - Shows single date if earliest equals latest
   * - Shows range if different dates
   * - Shows "No date info" if data is missing
   */
  const formatDateRange = () => {
    const { earliest, latest } = cluster.date_range || {}
    if (!earliest) return 'No date info'
    if (earliest === latest) return earliest
    return `${earliest} - ${latest}`
  }

  /**
   * Extract unique tags from all photos in cluster
   * Limits to 5 tags for display
   */
  const getUniqueTags = () => {
    if (!cluster.photos) return []
    const allTags = cluster.photos.flatMap((p) => p.tags || [])
    return [...new Set(allTags)].slice(0, 5)
  }

  const uniqueTags = getUniqueTags()
  const hasPhotosWithTags = cluster.photos?.some((p) => p.tags?.length && p.tags.length > 0)

  return (
    <div
      ref={popupRef}
      role="dialog"
      aria-modal="true"
      aria-label={`Photo preview for ${cluster.count} photos at this location`}
      tabIndex={-1}
      className={`
        fixed bg-white rounded-lg shadow-xl border border-gray-200
        transition-opacity
        ${isAnimating ? 'opacity-100' : 'opacity-0'}
      `}
      style={{
        left: position?.x || 0,
        top: position?.y || 0,
        width: HOVER_POPUP_CONFIG.POPUP_WIDTH,
        zIndex: HOVER_POPUP_CONFIG.Z_INDEX,
        transitionDuration: `${HOVER_POPUP_CONFIG.ANIMATION_DURATION}ms`,
      }}
    >
      {/* Header - Photo count and date range */}
      <div className="p-3 border-b border-gray-100">
        <h4 className="font-semibold text-sm text-gray-800">
          {cluster.count} photos
        </h4>
        <p className="text-xs text-gray-500 mt-0.5">{formatDateRange()}</p>
      </div>

      {/* Thumbnail Grid */}
      <div className="p-2">
        <ThumbnailGrid
          photos={cluster.photos}
          onPhotoClick={onPhotoClick}
          thumbnailSize={HOVER_POPUP_CONFIG.THUMBNAIL_SIZE}
          maxPhotos={HOVER_POPUP_CONFIG.MAX_PHOTOS}
        />
      </div>

      {/* Tags (only shown if any photos have tags) */}
      {hasPhotosWithTags && (
        <div className="px-3 pb-2">
          <div className="flex flex-wrap gap-1">
            {uniqueTags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 bg-gray-100 text-xs text-gray-600 rounded"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default MarkerHoverPopup
