import React, { memo, useCallback, useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { FixedSizeGrid } from 'react-window';
import useVirtualGrid from '../hooks/useVirtualGrid';
import VirtualPhotoGridItem from './VirtualPhotoGridItem';
import EmptyStateMessage from './EmptyStateMessage';
import { GALLERY_CONFIG } from '../constants/config';

/**
 * Simple debounce utility for resize event handler
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function with cleanup
 */
function debounce(fn, delay) {
  let timeoutId = null;
  const debounced = function(...args) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => fn(...args), delay);
  };
  debounced.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
  };
  return debounced;
}

/**
 * VirtualPhotoGrid - Virtualized photo grid using react-window
 * Renders only visible items for optimal performance with large collections
 * Integrates with TanStack Query infinite scroll
 *
 * @param {array} photos - Array of photo objects
 * @param {boolean} isLoading - Loading state from query
 * @param {boolean} isFetchingNextPage - Fetching next page state
 * @param {boolean} hasNextPage - More pages available
 * @param {function} onPhotoClick - Click handler for photos
 * @param {string} viewMode - 'grid' or 'list'
 * @param {object} options - Additional configuration
 * @param {object} scrollRef - Ref for scroll restoration (optional)
 */
const VirtualPhotoGrid = memo(function VirtualPhotoGrid({
  photos = [],
  isLoading = false,
  isFetchingNextPage = false,
  hasNextPage = false,
  onPhotoClick,
  viewMode = 'grid',
  options = {},
  scrollRef
}) {
  // Calculate responsive viewport height
  const [viewportHeight, setViewportHeight] = useState(() => {
    // Default: 80vh or 600px minimum for good UX
    return typeof window !== 'undefined'
      ? Math.max(window.innerHeight * 0.8, 600)
      : 600;
  });

  // Stable callback for height calculation
  const updateViewportHeight = useCallback(() => {
    setViewportHeight(Math.max(window.innerHeight * 0.8, 600));
  }, []);

  // Update viewport height on window resize with debouncing
  useEffect(() => {
    // Debounce resize handler to prevent excessive re-renders
    const debouncedResize = debounce(updateViewportHeight, 150);

    window.addEventListener('resize', debouncedResize);
    return () => {
      window.removeEventListener('resize', debouncedResize);
      debouncedResize.cancel(); // Cancel pending updates on unmount
    };
  }, [updateViewportHeight]);

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
    breakpoints: viewMode === 'list' ? { sm: 0 } : undefined // Force 1 column for list
  });

  // Cell renderer for react-window
  const Cell = useCallback(({ columnIndex, rowIndex, style }) => {
    const photoIndex = rowIndex * columnCount + columnIndex;
    const photo = photos[photoIndex];

    // Handle partial last row
    if (!photo) return null;

    return (
      <div style={style}>
        <VirtualPhotoGridItem
          photo={photo}
          size={options.thumbnailSize || GALLERY_CONFIG.THUMBNAIL.SIZE}
          onClick={() => onPhotoClick?.(photo)}
        />
      </div>
    );
  }, [photos, columnCount, onPhotoClick, options.thumbnailSize]);

  // Empty state
  if (!isLoading && photos.length === 0) {
    return <EmptyStateMessage message="No photos found" />;
  }

  // Loading state (skeleton grid)
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="skeleton-loader aspect-[4/3]" />
        ))}
      </div>
    );
  }

  return (
    <div ref={containerRef} className="virtual-photo-grid-container">
      <FixedSizeGrid
        columnCount={columnCount}
        columnWidth={itemWidth}
        height={viewportHeight} // Responsive viewport height (80vh, min 600px)
        rowCount={rowCount}
        rowHeight={itemHeight}
        width="100%" // Full container width
        overscanRowCount={GALLERY_CONFIG.VIRTUALIZATION.OVERSCAN_ROW_COUNT}
        className="virtual-photo-grid"
        outerRef={scrollRef} // Attach scroll restoration ref
      >
        {Cell}
      </FixedSizeGrid>
      {/* Note: Infinite scroll sentinel is managed by parent Gallery component */}
    </div>
  );
});

VirtualPhotoGrid.propTypes = {
  photos: PropTypes.arrayOf(
    PropTypes.shape({
      path: PropTypes.string.isRequired,
      filename: PropTypes.string.isRequired,
      size: PropTypes.number,
      timestamp: PropTypes.number,
    })
  ).isRequired,
  isLoading: PropTypes.bool,
  isFetchingNextPage: PropTypes.bool,
  hasNextPage: PropTypes.bool,
  onPhotoClick: PropTypes.func,
  viewMode: PropTypes.oneOf(['grid', 'list']),
  options: PropTypes.shape({
    gap: PropTypes.number,
    aspectRatio: PropTypes.number,
    thumbnailSize: PropTypes.oneOf([64, 128, 256]),
  }),
  scrollRef: PropTypes.object // Ref for scroll restoration
};

export default VirtualPhotoGrid;
