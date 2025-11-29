import { useEffect } from 'react'
import MothIcon from './MothIcon'
import useProgressiveImage from '../hooks/useProgressiveImage'

/**
 * ProgressiveImage Component
 *
 * Displays images with progressive loading (blur-up effect) and graceful error handling.
 * Loads low-res thumbnail first, then transitions to full resolution for smooth UX.
 * Shows fade-in animation when image loads and moth icon fallback on error.
 *
 * @param {Object} props - Component props
 * @param {string} props.src - Direct image URL (fallback for non-progressive loading) OR photo path for progressive loading
 * @param {string} props.photoPath - Photo path for progressive loading (takes precedence over src)
 * @param {string} props.alt - Image alt text for accessibility
 * @param {string} [props.className=''] - Optional CSS classes for the image
 * @param {Function} [props.onLoad] - Optional callback when image loads successfully
 * @param {Function} [props.onError] - Optional callback when image fails to load
 * @param {boolean} [props.showFilenameOnError=false] - Show filename when image fails
 * @param {number} [props.iconSize=200] - Size of moth icon in error fallback (px)
 * @param {number} [props.thumbnailSize=64] - Thumbnail size for progressive loading
 * @param {number} [props.fullSize=256] - Full image size for progressive loading
 * @param {boolean} [props.progressive=true] - Enable progressive loading (blur-up effect)
 */
export default function ProgressiveImage({
  src,
  photoPath,
  alt,
  className = '',
  onLoad,
  onError,
  showFilenameOnError = false,
  iconSize = 200,
  thumbnailSize = 64,
  fullSize = 256,
  progressive = true,
}) {
  // Only use progressive loading hook if photoPath is provided
  const shouldUseProgressive = !!photoPath && progressive;

  const {
    src: progressiveSrc,
    isLoading,
    error,
    stage
  } = useProgressiveImage(shouldUseProgressive ? photoPath : null, {
    thumbnailSize,
    fullSize,
    autoLoad: shouldUseProgressive,
  });

  // Determine which source to use
  const imageSrc = shouldUseProgressive ? progressiveSrc : src;
  const hasError = shouldUseProgressive ? !!error : false;
  const isBlurred = shouldUseProgressive && stage === 'thumbnail';

  // Call onLoad callback when full image loads
  useEffect(() => {
    if (stage === 'loaded' && onLoad) {
      onLoad();
    }
  }, [stage, onLoad]);

  // Call onError callback when image fails
  useEffect(() => {
    if (error && onError) {
      onError(error);
    }
  }, [error, onError]);

  return (
    <div className="relative">
      {/* Main image with progressive loading and blur-up transition */}
      {imageSrc && !hasError && (
        <img
          src={imageSrc}
          alt={alt}
          className={`transition-all duration-300 ${
            isBlurred ? 'opacity-80 blur-sm scale-105' : 'opacity-100 blur-0 scale-100'
          } ${className}`}
          onError={() => {
            // Handle direct src errors (non-progressive mode)
            if (!progressive || !photoPath) {
              onError?.();
            }
          }}
        />
      )}

      {/* Broken image fallback - moth icon */}
      {hasError && (
        <div className={`flex flex-col items-center justify-center bg-gray-100 ${className}`}>
          <MothIcon size={iconSize} />
          {showFilenameOnError && (
            <div className="text-xs text-gray-600 mt-2 px-2 text-center break-all">
              {alt}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
