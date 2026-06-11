import { memo, useCallback, useMemo } from 'react'
import { XMarkIcon } from '@heroicons/react/20/solid'

type TagSize = 'sm' | 'md'

export interface TagChipProps {
  /** Tag name to display */
  tag: string
  /** Optional count to show */
  count?: number
  /** Whether tag is selected/applied */
  selected?: boolean
  /** Show remove (X) button */
  removable?: boolean
  /** Click handler for selection */
  onClick?: () => void
  /** Remove button handler */
  onRemove?: () => void
  /** Size variant */
  size?: TagSize
  /** Additional classes */
  className?: string
}

/**
 * TagChip Component
 *
 * Reusable tag badge component for displaying and interacting with tags.
 * Supports selection, removal, and count display.
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
}: TagChipProps) {
  // Memoize computed class strings
  const { baseClasses, stateClasses } = useMemo(() => {
    const sizeClasses: Record<TagSize, string> = {
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

  const handleRemove = useCallback((e: React.MouseEvent<HTMLSpanElement> | React.KeyboardEvent<HTMLSpanElement>) => {
    e.stopPropagation()
    if (onRemove) {
      onRemove()
    }
  }, [onRemove])

  const handleRemoveKeyDown = useCallback((e: React.KeyboardEvent<HTMLSpanElement>) => {
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

export default memo(TagChip)
