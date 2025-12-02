import { useRef, useEffect, useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/react'
import { XMarkIcon, CheckIcon, MagnifyingGlassIcon } from '@heroicons/react/20/solid'
import TagChip from './TagChip'
import useTags from '../../hooks/useTags'
import useSidecarMetadata from '../../hooks/useSidecarMetadata'

function QuickTagDropdown({ filename, isOpen, onClose, anchorEl }) {
  const dropdownRef = useRef(null)
  const searchInputRef = useRef(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch all tags sorted by count
  const { data: tagsData, isLoading: tagsLoading, isError: tagsError } = useTags({
    sort: 'count',
    order: 'desc'
  })

  // Fetch and manage photo's sidecar metadata
  const {
    data: sidecarData,
    isLoading: sidecarLoading,
    addTag,
    removeTag,
    isUpdating
  } = useSidecarMetadata(filename)

  // Floating UI for positioning
  const { refs, floatingStyles } = useFloating({
    placement: 'bottom-start',
    middleware: [
      offset(4),
      flip({ fallbackPlacements: ['top-start', 'bottom-end', 'top-end'] }),
      shift({ padding: 8 })
    ],
    whileElementsMounted: autoUpdate,
  })

  // Update reference element
  useEffect(() => {
    refs.setReference(anchorEl)
  }, [anchorEl, refs])

  // Focus search input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 0)
    }
  }, [isOpen])

  // Close on Escape or click outside - only attach listeners when open
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }

    const handleClickOutside = (e) => {
      if (dropdownRef.current &&
          !dropdownRef.current.contains(e.target) &&
          !anchorEl?.contains(e.target)) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, onClose, anchorEl])

  if (!isOpen) return null

  const allTags = tagsData?.tags || []
  const appliedTags = sidecarData?.tags || []
  const quickTags = allTags.slice(0, 8)

  // Filter tags based on search query
  const filteredTags = searchQuery
    ? allTags.filter(tag =>
        tag.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : allTags

  // Check if search query matches an existing tag
  const exactMatch = filteredTags.find(
    tag => tag.name.toLowerCase() === searchQuery.toLowerCase()
  )

  // Show create option if search query is not empty and doesn't match exactly
  const showCreateOption = searchQuery.trim() && !exactMatch

  const handleToggleTag = useCallback((tagName) => {
    if (appliedTags.includes(tagName)) {
      removeTag(tagName)
    } else {
      addTag(tagName)
    }
  }, [appliedTags, addTag, removeTag])

  const handleCreateTag = useCallback((tagName) => {
    const trimmedTag = tagName.trim()
    if (trimmedTag && !appliedTags.includes(trimmedTag)) {
      addTag(trimmedTag)
      setSearchQuery('') // Clear search after creating
    }
  }, [appliedTags, addTag])

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value)
  }

  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter' && showCreateOption) {
      handleCreateTag(searchQuery)
    }
  }

  const isLoading = tagsLoading || sidecarLoading

  return (
    <div
      ref={(node) => {
        dropdownRef.current = node
        refs.setFloating(node)
      }}
      style={floatingStyles}
      className={`
        z-50 w-72 bg-white dark:bg-gray-800 rounded-lg shadow-xl
        border border-gray-200 dark:border-gray-700
        transition-all duration-150 origin-top-left
        ${isOpen ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}
      `}
      role="dialog"
      aria-label="Add tags to photo"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          Quick Tags
        </h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          aria-label="Close"
        >
          <XMarkIcon className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {isLoading ? (
        <div className="p-4 text-center text-gray-500">Loading tags...</div>
      ) : tagsError ? (
        <div className="p-4 text-center text-red-500">Failed to load tags</div>
      ) : (
        <>
          {/* Quick Tags Section */}
          {!searchQuery && (
            <div className="p-3 border-b border-gray-200 dark:border-gray-700">
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                Frequently Used
              </div>
              <div className="flex flex-wrap gap-1.5">
                {quickTags.length > 0 ? (
                  quickTags.map(tag => (
                    <TagChip
                      key={tag.name}
                      tag={tag.name}
                      selected={appliedTags.includes(tag.name)}
                      onClick={() => handleToggleTag(tag.name)}
                      size="sm"
                    />
                  ))
                ) : (
                  <span className="text-sm text-gray-500">No tags yet</span>
                )}
              </div>
            </div>
          )}

          {/* Search Section */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search or create tag..."
                value={searchQuery}
                onChange={handleSearchChange}
                onKeyDown={handleSearchKeyDown}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600
                           rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                           focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Create New Tag Option */}
          {showCreateOption && (
            <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
              <button
                onClick={() => handleCreateTag(searchQuery)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded
                           hover:bg-blue-50 dark:hover:bg-blue-900/30 text-left
                           text-blue-600 dark:text-blue-400 font-medium"
              >
                <span className="text-sm">Create &quot;{searchQuery.trim()}&quot;</span>
              </button>
            </div>
          )}

          {/* All Tags Section */}
          <div className="max-h-48 overflow-y-auto p-3">
            <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
              All Tags ({filteredTags.length})
            </div>
            <div className="space-y-1">
              {filteredTags.map(tag => {
                const isApplied = appliedTags.includes(tag.name)
                return (
                  <button
                    key={tag.name}
                    className={`w-full flex items-center justify-between px-2 py-1.5 rounded
                               hover:bg-gray-100 dark:hover:bg-gray-700 text-left
                               ${isApplied ? 'bg-blue-50 dark:bg-blue-900/30' : ''}`}
                    onClick={() => handleToggleTag(tag.name)}
                  >
                    <span className="flex items-center gap-2">
                      {isApplied && (
                        <CheckIcon className="w-4 h-4 text-blue-500" data-testid="check-icon" />
                      )}
                      <span className={`text-sm ${isApplied ? 'text-blue-600 dark:text-blue-400' : 'text-gray-900 dark:text-gray-100'}`}>
                        {tag.name}
                      </span>
                    </span>
                    <span className="text-xs text-gray-500">{tag.count}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Applied Tags Summary */}
          {appliedTags.length > 0 && (
            <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 rounded-b-lg">
              <div className="text-xs text-gray-500 mb-1">Applied ({appliedTags.length})</div>
              <div className="flex flex-wrap gap-1">
                {appliedTags.map(tag => (
                  <TagChip
                    key={tag}
                    tag={tag}
                    removable
                    onRemove={() => removeTag(tag)}
                    size="sm"
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Updating indicator */}
      {isUpdating && (
        <div className="absolute inset-0 bg-white/50 dark:bg-gray-800/50 flex items-center justify-center rounded-lg">
          <div className="text-sm text-gray-500">Saving...</div>
        </div>
      )}
    </div>
  )
}

QuickTagDropdown.propTypes = {
  filename: PropTypes.string.isRequired,
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  anchorEl: PropTypes.instanceOf(Element),
}

export default QuickTagDropdown
