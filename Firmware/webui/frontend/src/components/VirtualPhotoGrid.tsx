import React, { memo, useCallback, useState, useEffect, useMemo, useRef } from 'react'
import { Grid, CellComponentProps } from 'react-window'
import useVirtualGrid from '../hooks/useVirtualGrid'
import VirtualPhotoGridItem from './VirtualPhotoGridItem'
import EmptyStateMessage from './EmptyStateMessage'
import { GALLERY_CONFIG } from '../constants/config'
import { debounce } from '../utils/debounce'

/**
 * VirtualPhotoGrid - Virtualized photo grid using react-window
 * Renders only visible items for optimal performance with large collections
 * Integrates with TanStack Query infinite scroll
 *
 * @param {array} photos - Array of photo objects
 * @param {boolean} isLoading - Loading state from query
 * @param {function} onPhotoClick - Click handler for photos
 * @param {string} viewMode - 'grid' or 'list'
 * @param {object} options - Additional configuration
 * @param {object} scrollRef - Ref for scroll restoration (optional)
 *
 * Note: Infinite scroll loading indicators are managed by parent Gallery component
 */

export interface VirtualPhotoGridPhoto {
  path: string
  filename: string
  size?: number
  timestamp?: number
}

export interface VirtualPhotoGridOptions {
  gap?: number
  aspectRatio?: number
  thumbnailSize?: 64 | 128 | 256
}

export interface VirtualPhotoGridProps {
  photos?: VirtualPhotoGridPhoto[]
  isLoading?: boolean
  onPhotoClick?: (photo: VirtualPhotoGridPhoto) => void
  viewMode?: 'grid' | 'list'
  options?: VirtualPhotoGridOptions
  scrollRef?: React.RefObject<HTMLElement>
}

const VirtualPhotoGrid = memo(function VirtualPhotoGrid({
  photos = [],
  isLoading = false,
  onPhotoClick,
  viewMode = 'grid',
  options = {},
  scrollRef
}: VirtualPhotoGridProps) {
  // Calculate responsive viewport height
  const [viewportHeight, setViewportHeight] = useState(() => {
    // Default: configured ratio of window height or minimum for good UX
    return typeof window !== 'undefined'
      ? Math.max(
          window.innerHeight * GALLERY_CONFIG.VIRTUALIZATION.VIEWPORT_HEIGHT_RATIO,
          GALLERY_CONFIG.VIRTUALIZATION.MIN_VIEWPORT_HEIGHT
        )
      : GALLERY_CONFIG.VIRTUALIZATION.MIN_VIEWPORT_HEIGHT
  })

  // Stable callback for height calculation
  const updateViewportHeight = useCallback(() => {
    setViewportHeight(
      Math.max(
        window.innerHeight * GALLERY_CONFIG.VIRTUALIZATION.VIEWPORT_HEIGHT_RATIO,
        GALLERY_CONFIG.VIRTUALIZATION.MIN_VIEWPORT_HEIGHT
      )
    )
  }, [])

  // Update viewport height on window resize with debouncing
  useEffect(() => {
    // Debounce resize handler to prevent excessive re-renders
    const debouncedResize = debounce(
      updateViewportHeight,
      GALLERY_CONFIG.VIRTUALIZATION.RESIZE_DEBOUNCE_MS
    )

    window.addEventListener('resize', debouncedResize)
    return () => {
      window.removeEventListener('resize', debouncedResize)
      // Cancel pending updates on unmount if debounce function has cancel method
      if (typeof (debouncedResize as any).cancel === 'function') {
        (debouncedResize as any).cancel()
      }
    }
  }, [updateViewportHeight])

  // Memoize breakpoints object to prevent unnecessary recalculations
  // viewMode changes infrequently (only on user toggle), so this is efficient
  const breakpoints = useMemo(
    () => (viewMode === 'list' ? { sm: 0 } : undefined),
    [viewMode]
  )

  // Get grid layout parameters
  const {
    containerRef,
    columnCount,
    rowCount,
    itemWidth,
    itemHeight
    // totalHeight is not used here - we use responsive viewportHeight instead
  } = useVirtualGrid(photos.length, {
    gap: options.gap,
    aspectRatio: options.aspectRatio,
    breakpoints // Force 1 column for list view
  })

  // Use ref to avoid stale closure in Cell callback
  // Critical: Prevents Cell from recreating on every photo array change (infinite scroll)
  // Without this, react-window would re-render ALL cells on every new page load
  // Update ref synchronously before render to avoid 1-frame delay during rapid infinite scroll
  const photosRef = useRef(photos)
  photosRef.current = photos

  // Cell renderer for react-window
  // IMPORTANT: photos is accessed via photosRef.current to avoid dependency
  // This keeps Cell reference stable during infinite scroll, preventing unnecessary re-renders
  const Cell = useCallback(({ columnIndex, rowIndex, style }: CellComponentProps) => {
    const photoIndex = rowIndex * columnCount + columnIndex
    const photo = photosRef.current[photoIndex]

    // Handle partial last row
    if (!photo) return null

    return (
      <div style={style}>
        <VirtualPhotoGridItem
          photo={photo as any}
          size={options.thumbnailSize || GALLERY_CONFIG.THUMBNAIL.SIZE}
          onClick={() => onPhotoClick?.(photo)}
        />
      </div>
    )
  }, [columnCount, onPhotoClick, options.thumbnailSize]) // photos removed from deps

  // Empty state
  if (!isLoading && photos.length === 0) {
    return <EmptyStateMessage />
  }

  // Loading state (skeleton grid)
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="skeleton-loader aspect-[4/3]" />
        ))}
      </div>
    )
  }

  return (
    <div ref={containerRef} className="virtual-photo-grid-container">
      <Grid
        cellComponent={Cell}
        cellProps={{}}
        columnCount={columnCount}
        columnWidth={itemWidth}
        defaultHeight={viewportHeight}
        rowCount={rowCount}
        rowHeight={itemHeight}
        overscanCount={GALLERY_CONFIG.VIRTUALIZATION.OVERSCAN_ROW_COUNT}
        className="virtual-photo-grid"
        gridRef={scrollRef as any}
      />
      {/* Note: Infinite scroll sentinel is managed by parent Gallery component */}
    </div>
  )
})

export default VirtualPhotoGrid
