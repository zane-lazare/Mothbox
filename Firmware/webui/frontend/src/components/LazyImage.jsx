import React, { useState, memo } from 'react';
import PropTypes from 'prop-types';
import useInViewport from '../hooks/useInViewport';
import { getThumbnailUrl } from '../utils/api';
import MothIcon from './MothIcon';
import './LazyImage.css';

/**
 * LazyImage - Lazy loads images when they enter viewport
 * Prevents layout shift with aspect ratio container
 * Integrates with IntersectionObserver for viewport detection
 *
 * @param {object} photo - Photo object with path, filename
 * @param {number} size - Thumbnail size (64, 128, 256)
 * @param {string} alt - Alt text for accessibility
 * @param {string} className - Additional CSS classes
 * @param {function} onClick - Click handler
 * @param {number} aspectRatio - Width/height ratio (default: 4/3)
 */
const LazyImage = memo(function LazyImage({
  photo,
  size = 256,
  alt,
  className = '',
  onClick,
  aspectRatio = 4 / 3
}) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  // Use viewport detection hook
  const { ref, hasBeenInViewport } = useInViewport({
    rootMargin: '100px', // Preload 100px before visible
    threshold: 0.1       // Trigger when 10% visible
  });

  // Only load image once it has entered viewport
  const shouldLoadImage = hasBeenInViewport;
  const imageUrl = shouldLoadImage ? getThumbnailUrl(photo.path, size) : null;

  const handleLoad = () => {
    setIsLoaded(true);
  };

  const handleError = () => {
    setHasError(true);
    setIsLoaded(true); // Stop showing loading state
  };

  return (
    <div
      ref={ref}
      className={`lazy-image-container ${className}`}
      style={{
        aspectRatio: `${aspectRatio}`
      }}
      onClick={onClick}
    >
      {/* Placeholder state */}
      {!shouldLoadImage && (
        <div className="skeleton-loader" />
      )}

      {/* Loading/Loaded state */}
      {shouldLoadImage && !hasError && (
        <img
          src={imageUrl}
          alt={alt || photo.filename}
          loading="lazy" // Native lazy loading as backup
          onLoad={handleLoad}
          onError={handleError}
          className={`
            lazy-image
            ${isLoaded ? 'opacity-100' : 'opacity-0'}
            transition-opacity duration-300
          `}
        />
      )}

      {/* Error state */}
      {hasError && (
        <div className="error-placeholder">
          <MothIcon className="w-16 h-16 text-gray-400" />
        </div>
      )}

      {/* Loading indicator (optional) */}
      {shouldLoadImage && !isLoaded && !hasError && (
        <div className="loading-indicator" />
      )}
    </div>
  );
});

LazyImage.propTypes = {
  photo: PropTypes.shape({
    path: PropTypes.string.isRequired,
    filename: PropTypes.string.isRequired,
  }).isRequired,
  size: PropTypes.oneOf([64, 128, 256]).isRequired,
  alt: PropTypes.string,
  className: PropTypes.string,
  onClick: PropTypes.func,
  aspectRatio: PropTypes.number
};

export default LazyImage;
