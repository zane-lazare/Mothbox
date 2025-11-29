import React from 'react'
import PropTypes from 'prop-types'
import { HOVER_POPUP_CONFIG } from '../constants/config'

/**
 * ThumbnailSkeleton - Pulsing skeleton loader for thumbnail images
 *
 * Displays an animated placeholder while thumbnail images are loading,
 * providing visual feedback during asynchronous data fetching.
 *
 * @component
 * @param {Object} props - Component props
 * @param {number} [props.size=128] - Size in pixels (width and height)
 * @param {string} [props.className=''] - Additional CSS classes to apply
 *
 * @example
 * // Default 128px skeleton
 * <ThumbnailSkeleton />
 *
 * @example
 * // Custom size with additional styling
 * <ThumbnailSkeleton size={256} className="shadow-md" />
 */
function ThumbnailSkeleton({ size = HOVER_POPUP_CONFIG.THUMBNAIL_SIZE, className = '' }) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading thumbnail"
      className={`bg-gray-200 animate-pulse rounded-lg ${className}`}
      style={{ width: size, height: size }}
    />
  )
}

ThumbnailSkeleton.propTypes = {
  size: PropTypes.number,
  className: PropTypes.string,
}

export default ThumbnailSkeleton
