import { memo, useCallback, useMemo } from 'react'
import PropTypes from 'prop-types'
import { XMarkIcon } from '@heroicons/react/20/solid'

/**
 * TagChip Component
 *
 * TypeScript types: ./TagChip.d.ts (keep in sync)
 *
 * Reusable tag badge component for displaying and interacting with tags.
 * Supports selection, removal, and count display.
 *
 * @component
 * @example
 * // Basic tag
 * <TagChip tag="moth" />
 *
 * @example
 * // Tag with count
 * <TagChip tag="nocturnal" count={5} />
 *
 * @example
 * // Selectable tag
 * <TagChip tag="moth" selected onClick={() => console.log('clicked')} />
 *
 * @example
 * // Removable tag
 * <TagChip tag="moth" removable onRemove={() => console.log('removed')} />
 */
function TagChip({
  tag,
  count,
  selected = false,
  removable = false,
  onClick,
  onRemove,
  size = 'sm',
  className = '',
}) {
  // Memoize computed class strings
  const { baseClasses, stateClasses } = useMemo(() => {
    const sizeClasses = {
      sm: 'text-xs px-2 py-0.5',
      md: 'text-sm px-3 py-1',
    }

    const base = `
      inline-flex items-center gap-1 rounded-full font-medium
      transition-colors duration-150
      ${sizeClasses[size]}
    `.trim().replace(/\s+/g, ' ')

    const state = selected
      ? 'bg-blue-500 text-white dark:bg-blue-600'
      : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-800'

    return { baseClasses: base, stateClasses: state }
  }, [size, selected])

  const handleClick = useCallback(() => {
    if (onClick) {
      onClick()
    }
  }, [onClick])

  const handleRemove = useCallback((e) => {
    e.stopPropagation()
    if (onRemove) {
      onRemove()
    }
  }, [onRemove])

  const handleRemoveKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      handleRemove(e)
    }
  }, [handleRemove])

  return (
    <button
      type="button"
      className={`${baseClasses} ${stateClasses} ${className}`}
      onClick={handleClick}
      aria-pressed={selected}
      aria-label={`Tag: ${tag}${count !== undefined ? `, used ${count} times` : ''}`}
    >
      <span>{tag}</span>
      {count !== undefined && (
        <span className="opacity-70">({count})</span>
      )}
      {removable && (
        <span
          role="button"
          tabIndex={0}
          className="ml-0.5 hover:text-red-600 dark:hover:text-red-400 cursor-pointer"
          onClick={handleRemove}
          onKeyDown={handleRemoveKeyDown}
          aria-label={`Remove tag ${tag}`}
        >
          <XMarkIcon className="h-3 w-3" />
        </span>
      )}
    </button>
  )
}

TagChip.propTypes = {
  /** Tag name to display */
  tag: PropTypes.string.isRequired,
  /** Optional count to show */
  count: PropTypes.number,
  /** Whether tag is selected/applied */
  selected: PropTypes.bool,
  /** Show remove (X) button */
  removable: PropTypes.bool,
  /** Click handler for selection */
  onClick: PropTypes.func,
  /** Remove button handler */
  onRemove: PropTypes.func,
  /** Size variant */
  size: PropTypes.oneOf(['sm', 'md']),
  /** Additional classes */
  className: PropTypes.string,
}

export default memo(TagChip)
