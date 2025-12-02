import { useState, useRef, useCallback } from 'react'
import PropTypes from 'prop-types'
import { TagIcon } from '@heroicons/react/24/outline'
import QuickTagDropdown from './QuickTagDropdown'
import useSidecarMetadata from '../../hooks/useSidecarMetadata'

/**
 * QuickTagButton Component
 *
 * Tag icon button that appears on photo thumbnails to quickly add/remove tags.
 * Opens a QuickTagDropdown for tag management.
 *
 * Features:
 * - Shows tag count badge if photo has tags
 * - Visual feedback when dropdown is active
 * - Stops event propagation to prevent lightbox opening
 * - Accessible with proper ARIA attributes
 * - Loading indicator while fetching tags
 *
 * @param {string} filename - Photo filename for tag operations
 * @param {string} [className] - Additional CSS classes
 * @param {Function} [onDropdownOpenChange] - Callback when dropdown state changes
 */
function QuickTagButton({ filename, className = '', onDropdownOpenChange }) {
  const [isOpen, setIsOpen] = useState(false)
  const buttonRef = useRef(null)

  // Get current tags for badge count
  const { data, isLoading } = useSidecarMetadata(filename)
  const tagCount = data?.tags?.length || 0

  const handleClick = useCallback((e) => {
    e.stopPropagation()
    e.preventDefault()
    setIsOpen(prev => {
      const newState = !prev
      onDropdownOpenChange?.(newState)
      return newState
    })
  }, [onDropdownOpenChange])

  const handleClose = useCallback(() => {
    setIsOpen(false)
    onDropdownOpenChange?.(false)
    // Restore focus to trigger button for keyboard accessibility
    buttonRef.current?.focus()
  }, [onDropdownOpenChange])

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={handleClick}
        className={`
          relative p-1.5 rounded-full transition-all duration-150
          ${isOpen
            ? 'bg-blue-500 text-white shadow-lg'
            : 'bg-white/90 dark:bg-gray-800/90 text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-700 hover:shadow-md'}
          ${className}
        `}
        aria-label={`Add tags to photo${tagCount > 0 ? ` (${tagCount} tags)` : ''}`}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
      >
        <TagIcon className="w-4 h-4" />

        {/* Tag count badge */}
        {tagCount > 0 && !isLoading && (
          <span className={`
            absolute -top-1 -right-1 min-w-[18px] h-[18px]
            flex items-center justify-center
            text-xs font-medium rounded-full
            ${isOpen
              ? 'bg-white text-blue-500'
              : 'bg-blue-500 text-white'}
          `}>
            {tagCount}
          </span>
        )}

        {/* Loading indicator */}
        {isLoading && (
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-gray-300 rounded-full animate-pulse" />
        )}
      </button>

      <QuickTagDropdown
        filename={filename}
        isOpen={isOpen}
        onClose={handleClose}
        anchorEl={buttonRef.current}
      />
    </>
  )
}

QuickTagButton.propTypes = {
  filename: PropTypes.string.isRequired,
  className: PropTypes.string,
  onDropdownOpenChange: PropTypes.func,
}

export default QuickTagButton
