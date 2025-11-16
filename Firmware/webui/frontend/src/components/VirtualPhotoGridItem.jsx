import React, { memo } from 'react';
import PropTypes from 'prop-types';
import LazyImage from './LazyImage';

/**
 * VirtualPhotoGridItem - Individual photo item in virtual grid
 * Wrapper around LazyImage for grid-specific styling and behavior
 *
 * @param {object} photo - Photo object
 * @param {number} size - Thumbnail size
 * @param {function} onClick - Click handler
 */
const VirtualPhotoGridItem = memo(function VirtualPhotoGridItem({
  photo,
  size = 256,
  onClick
}) {
  return (
    <div className="virtual-photo-grid-item group cursor-pointer">
      <LazyImage
        photo={photo}
        size={size}
        alt={photo.filename}
        onClick={onClick}
        className="rounded-lg overflow-hidden"
      />

      {/* Hover overlay */}
      <div className="
        absolute inset-0
        bg-black bg-opacity-0
        group-hover:bg-opacity-20
        transition-opacity duration-200
        pointer-events-none
      " />
    </div>
  );
});

VirtualPhotoGridItem.propTypes = {
  photo: PropTypes.shape({
    path: PropTypes.string.isRequired,
    filename: PropTypes.string.isRequired,
  }).isRequired,
  size: PropTypes.oneOf([64, 128, 256]),
  onClick: PropTypes.func
};

export default VirtualPhotoGridItem;
