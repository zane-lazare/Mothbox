import React, { memo, useCallback } from 'react';
import PropTypes from 'prop-types';
import { FixedSizeGrid } from 'react-window';
import useVirtualGrid from '../hooks/useVirtualGrid';
import VirtualPhotoGridItem from './VirtualPhotoGridItem';
import EmptyStateMessage from './EmptyStateMessage';
import LoadingSpinner from './LoadingSpinner';
import { GALLERY_CONFIG } from '../constants/config';

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
 */
const VirtualPhotoGrid = memo(function VirtualPhotoGrid({
  photos = [],
  isLoading = false,
  isFetchingNextPage = false,
  hasNextPage = false,
  onPhotoClick,
  viewMode = 'grid',
  options = {}
}) {
  // Get grid layout parameters
  const {
    containerRef,
    columnCount,
    rowCount,
    itemWidth,
    itemHeight,
    totalHeight
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
        height={600} // Viewport height (scrollable container)
        rowCount={rowCount}
        rowHeight={itemHeight}
        width="100%" // Full container width
        overscanRowCount={GALLERY_CONFIG.VIRTUALIZATION.OVERSCAN_ROW_COUNT}
        className="virtual-photo-grid"
      >
        {Cell}
      </FixedSizeGrid>

      {/* Infinite scroll sentinel */}
      {hasNextPage && (
        <div className="infinite-scroll-sentinel">
          {isFetchingNextPage && <LoadingSpinner />}
        </div>
      )}
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
  })
};

export default VirtualPhotoGrid;
