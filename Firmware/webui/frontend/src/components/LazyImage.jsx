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
        aspectRatio: `${aspectRatio}`,
        width: '100%',
        backgroundColor: '#f3f4f6', // Gray placeholder
        position: 'relative',
        overflow: 'hidden'
      }}
      onClick={onClick}
    >
      {/* Placeholder state */}
      {!shouldLoadImage && (
        <div className="skeleton-loader" style={{
          width: '100%',
          height: '100%',
          background: 'linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%)',
          backgroundSize: '200% 100%',
          animation: 'skeleton-loading 1.5s ease-in-out infinite'
        }} />
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
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
        />
      )}

      {/* Error state */}
      {hasError && (
        <div className="error-placeholder" style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
          height: '100%',
          backgroundColor: '#f9fafb'
        }}>
          <MothIcon className="w-16 h-16 text-gray-400" />
        </div>
      )}

      {/* Loading indicator (optional) */}
      {shouldLoadImage && !isLoaded && !hasError && (
        <div className="loading-indicator" style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '32px',
          height: '32px',
          border: '3px solid #e5e7eb',
          borderTopColor: '#3b82f6',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite'
        }} />
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
