import { useState } from 'react'
import MothIcon from './MothIcon'

/**
 * ProgressiveImage Component
 *
 * Displays images with progressive loading and graceful error handling.
 * Shows fade-in animation when image loads and moth icon fallback on error.
 *
 * @param {Object} props - Component props
 * @param {string} props.src - Image source URL
 * @param {string} props.alt - Image alt text for accessibility
 * @param {string} [props.className=''] - Optional CSS classes for the image
 * @param {Function} [props.onLoad] - Optional callback when image loads successfully
 * @param {Function} [props.onError] - Optional callback when image fails to load
 * @param {boolean} [props.showFilenameOnError=false] - Show filename when image fails
 */
export default function ProgressiveImage({
  src,
  alt,
  className = '',
  onLoad,
  onError,
  showFilenameOnError = false,
}) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [hasError, setHasError] = useState(false)

  const handleLoad = () => {
    setIsLoaded(true)
    onLoad?.()
  }

  const handleError = () => {
    setHasError(true)
    onError?.()
  }

  return (
    <div className="relative">
      {/* Main image with fade-in transition */}
      <img
        src={src}
        alt={alt}
        className={`transition-opacity duration-300 ${
          isLoaded ? 'opacity-100' : 'opacity-0'
        } ${hasError ? 'hidden' : ''} ${className}`}
        onLoad={handleLoad}
        onError={handleError}
      />

      {/* Broken image fallback - moth icon */}
      {hasError && (
        <div className="flex flex-col items-center justify-center bg-gray-100 aspect-square">
          <MothIcon size={200} />
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
