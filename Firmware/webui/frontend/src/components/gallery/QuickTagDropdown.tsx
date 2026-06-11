import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/react'
import { XMarkIcon, CheckIcon, MagnifyingGlassIcon } from '@heroicons/react/20/solid'
import TagChip from './TagChip'
import useTags from '../../hooks/useTags'
import useSidecarMetadata from '../../hooks/useSidecarMetadata'
import { METADATA_VALIDATION, Z_INDEX } from '../../constants/config'

interface QuickTagDropdownProps {
  filename: string
  isOpen: boolean
  onClose: () => void
  anchorEl: Element | null
}

function QuickTagDropdown({ filename, isOpen, onClose, anchorEl }: QuickTagDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(-1)

  // Use refs to stabilize event listener dependencies and prevent memory leaks
  // when onClose or anchorEl props change while dropdown is open
  const onCloseRef = useRef(onClose)
  const anchorElRef = useRef(anchorEl)

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

  // Derive tag data from queries (must be before early return for hooks rules)
  // Memoize to prevent new array references on each render when data is undefined
  const allTags = useMemo(() => tagsData?.tags || [], [tagsData?.tags])
  const appliedTags = useMemo(() => sidecarData?.tags || [], [sidecarData?.tags])
  const quickTags = useMemo(() => allTags.slice(0, 8), [allTags])

  // Event handlers (must be before early return for hooks rules)
  const handleToggleTag = useCallback((tagName: string) => {
    if (appliedTags.includes(tagName)) {
      removeTag(tagName)
    } else {
      addTag(tagName)
    }
  }, [appliedTags, addTag, removeTag])

  const handleCreateTag = useCallback((tagName: string) => {
    const trimmedTag = tagName.trim()
    if (trimmedTag && !appliedTags.includes(trimmedTag)) {
      addTag(trimmedTag)
      setSearchQuery('')
    }
  }, [appliedTags, addTag])

  // Keep refs updated with latest prop values
  useEffect(() => {
    onCloseRef.current = onClose
    anchorElRef.current = anchorEl
  })

  // Update reference element
  useEffect(() => {
    refs.setReference(anchorEl)
  }, [anchorEl, refs])

  // Focus search input when opened and reset highlight
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 0)
      setHighlightedIndex(-1)
    }
  }, [isOpen])

  // Scroll highlighted item into view during keyboard navigation
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const highlightedElement = listRef.current.querySelector<HTMLButtonElement>(
        `[data-tag-index="${highlightedIndex}"]`
      )
      highlightedElement?.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth'
      })
    }
  }, [highlightedIndex])

  // Close on Escape or click outside - only attach listeners when open
  // Uses refs to prevent memory leaks when props change during open state
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current()
    }

    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current &&
          !dropdownRef.current.contains(e.target as Node) &&
          !anchorElRef.current?.contains(e.target as Node)) {
        onCloseRef.current()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])  // Only isOpen as dependency - refs are always current

  if (!isOpen) return null

  // Filter tags based on search query
  // Pre-compute lowercase search query once, not per-tag in filter callback
  const searchLower = searchQuery.toLowerCase()
  const filteredTags = searchQuery
    ? allTags.filter(tag => tag.name.toLowerCase().includes(searchLower))
    : allTags

  // Check if search query matches an existing tag
  const exactMatch = filteredTags.find(
    tag => tag.name.toLowerCase() === searchLower
  )

  // Show create option if search query is not empty and doesn't match exactly
  const showCreateOption = searchQuery.trim() && !exactMatch

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value)
    setHighlightedIndex(-1)  // Reset highlight when search changes
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Calculate total navigable options:
    // - Create option (if shown) at index 0
    // - Filtered tags at subsequent indices
    const totalOptions = filteredTags.length + (showCreateOption ? 1 : 0)

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        if (totalOptions > 0) {
          setHighlightedIndex((prev) => {
            if (prev === -1) return 0
            return (prev + 1) % totalOptions
          })
        }
        break
      case 'ArrowUp':
        e.preventDefault()
        if (totalOptions > 0) {
          setHighlightedIndex((prev) => {
            if (prev === -1) return totalOptions - 1
            return (prev - 1 + totalOptions) % totalOptions
          })
        }
        break
      case 'Enter':
        e.preventDefault()
        if (highlightedIndex >= 0) {
          // If create option is shown, it's at index 0
          if (showCreateOption && highlightedIndex === 0) {
            handleCreateTag(searchQuery)
          } else {
            // Adjust index based on whether create option is shown
            const tagIndex = showCreateOption ? highlightedIndex - 1 : highlightedIndex
            if (tagIndex >= 0 && tagIndex < filteredTags.length) {
              handleToggleTag(filteredTags[tagIndex].name)
            }
          }
        } else if (showCreateOption) {
          // No highlight but create option available - create the tag
          handleCreateTag(searchQuery)
        }
        break
      // Note: Escape is handled by document-level listener
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
        ${Z_INDEX.MODAL} w-72 bg-white dark:bg-gray-800 rounded-lg shadow-xl
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
                maxLength={METADATA_VALIDATION.MAX_TAG_LENGTH}
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
                data-tag-index={0}
                onClick={() => handleCreateTag(searchQuery)}
                onMouseEnter={() => setHighlightedIndex(0)}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded
                           hover:bg-blue-50 dark:hover:bg-blue-900/30 text-left
                           text-blue-600 dark:text-blue-400 font-medium
                           ${highlightedIndex === 0 ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/30' : ''}`}
              >
                <span className="text-sm">Create &quot;{searchQuery.trim()}&quot;</span>
              </button>
            </div>
          )}

          {/* All Tags Section */}
          <div ref={listRef} className="max-h-48 overflow-y-auto p-3">
            <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
              All Tags ({filteredTags.length})
            </div>
            <div className="space-y-1">
              {filteredTags.map((tag, index) => {
                const isApplied = appliedTags.includes(tag.name)
                // Tag indices start after create option (if shown)
                const tagIndex = showCreateOption ? index + 1 : index
                const isHighlighted = highlightedIndex === tagIndex
                return (
                  <button
                    key={tag.name}
                    data-tag-index={tagIndex}
                    onMouseEnter={() => setHighlightedIndex(tagIndex)}
                    className={`w-full flex items-center justify-between px-2 py-1.5 rounded
                               hover:bg-gray-100 dark:hover:bg-gray-700 text-left
                               ${isApplied ? 'bg-blue-50 dark:bg-blue-900/30' : ''}
                               ${isHighlighted ? 'ring-2 ring-blue-500' : ''}`}
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

export default QuickTagDropdown
