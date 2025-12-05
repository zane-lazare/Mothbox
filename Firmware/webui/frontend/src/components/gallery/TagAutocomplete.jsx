import { useState, useRef, useEffect } from 'react'
import PropTypes from 'prop-types'
import { METADATA_VALIDATION } from '../../constants/config'

// Import the fuzzy search hook for API-based autocomplete
import useTagAutocomplete from '../../hooks/useTagAutocomplete'

/**
 * HighlightedMatch - Highlights the matched portion of a tag
 * @param {string} text - The full tag text
 * @param {string} query - The search query
 */
function HighlightedMatch({ text, query }) {
  if (!query || !text) {
    return <span data-testid="highlighted-match">{text}</span>
  }

  // Find the query in the text (case-insensitive)
  const lowerText = text.toLowerCase()
  const lowerQuery = query.toLowerCase()
  const index = lowerText.indexOf(lowerQuery)

  if (index === -1) {
    return <span data-testid="highlighted-match">{text}</span>
  }

  // Split text into before, match, and after
  const before = text.slice(0, index)
  const match = text.slice(index, index + query.length)
  const after = text.slice(index + query.length)

  return (
    <span data-testid="highlighted-match">
      {before}
      <mark className="bg-yellow-200 dark:bg-yellow-700 font-semibold">
        {match}
      </mark>
      {after}
    </span>
  )
}

HighlightedMatch.propTypes = {
  text: PropTypes.string.isRequired,
  query: PropTypes.string,
}

function TagAutocomplete({
  tags = [],
  selectedTags = [],
  onSelect,
  onCreate,
  onValidationError,
  placeholder = 'Search or create tags...',
  disabled = false,
  className = '',
}) {
  const [inputValue, setInputValue] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const inputRef = useRef(null)
  const listRef = useRef(null)
  const blurTimeoutRef = useRef(null)

  /**
   * Backwards compatibility: The `tags` prop enables local filtering mode.
   * This is deprecated - new code should rely on fuzzy search API.
   * TODO: Remove tags prop support in next major version.
   */
  const shouldUseFuzzySearch = !tags.length
  // Hook returns normalized data: { name, count, score } (compatible with component expectations)
  // Always call the hook but disable it when using local filtering (React hooks rules)
  const fuzzySearchResult = useTagAutocomplete(inputValue, {
    enabled: shouldUseFuzzySearch && inputValue.trim().length > 0
  })

  // Cleanup blur timeout on unmount to prevent memory leak
  useEffect(() => {
    return () => {
      if (blurTimeoutRef.current) {
        clearTimeout(blurTimeoutRef.current)
      }
    }
  }, [])

  // Deprecation warning for tags prop (only warn once on mount)
  useEffect(() => {
    if (tags.length > 0) {
      console.warn(
        '[TagAutocomplete] The `tags` prop is deprecated and will be removed in a future version. ' +
        'Use the fuzzy search API instead (omit the tags prop to enable).'
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Scroll highlighted item into view during keyboard navigation
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const highlightedElement = listRef.current.querySelector(
        `[data-index="${highlightedIndex}"]`
      )
      highlightedElement?.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth'
      })
    }
  }, [highlightedIndex])

  // Choose between fuzzy search results or local filtering
  const localFilteredTags = tags.filter(
    (tag) =>
      tag.name.toLowerCase().includes(inputValue.toLowerCase()) &&
      !selectedTags.includes(tag.name)
  )

  const filteredTags = shouldUseFuzzySearch
    ? fuzzySearchResult.suggestions.filter((tag) => !selectedTags.includes(tag.name))
    : localFilteredTags

  // Check if exact match exists (check both sources)
  const allTags = shouldUseFuzzySearch ? fuzzySearchResult.suggestions : tags
  const exactMatch = allTags.some(
    (t) => t.name.toLowerCase() === inputValue.toLowerCase()
  )
  const showCreateOption =
    inputValue.trim() && !exactMatch && !selectedTags.includes(inputValue.trim())

  // Get loading state from hook
  const isLoading = shouldUseFuzzySearch && fuzzySearchResult.isLoading

  // Total number of options (filtered tags + create option if shown)
  const totalOptions = filteredTags.length + (showCreateOption ? 1 : 0)

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        if (inputValue.trim()) {
          setIsOpen(true)
        }
      }
      return
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setHighlightedIndex((prev) => {
          if (prev === -1) return 0
          return (prev + 1) % totalOptions
        })
        break
      case 'ArrowUp':
        e.preventDefault()
        setHighlightedIndex((prev) => {
          if (prev === -1) return totalOptions - 1
          return (prev - 1 + totalOptions) % totalOptions
        })
        break
      case 'Enter':
        e.preventDefault()
        if (highlightedIndex >= 0 && highlightedIndex < totalOptions) {
          if (highlightedIndex < filteredTags.length) {
            handleSelect(filteredTags[highlightedIndex].name)
          } else if (showCreateOption) {
            handleCreate()
          }
        } else if (showCreateOption) {
          handleCreate()
        }
        break
      case 'Tab':
        // Tab key: select highlighted item if any, then allow default tab behavior
        if (highlightedIndex >= 0 && highlightedIndex < totalOptions) {
          e.preventDefault()
          if (highlightedIndex < filteredTags.length) {
            handleSelect(filteredTags[highlightedIndex].name)
          } else if (showCreateOption) {
            handleCreate()
          }
        }
        // If no highlight, just close dropdown and let tab move focus naturally
        setIsOpen(false)
        setHighlightedIndex(-1)
        break
      case 'Escape':
        setIsOpen(false)
        setHighlightedIndex(-1)
        break
    }
  }

  const handleSelect = (tag) => {
    onSelect(tag)
    setInputValue('')
    setIsOpen(false)
    setHighlightedIndex(-1)
    inputRef.current?.focus()
  }

  const handleCreate = () => {
    const newTag = inputValue.trim()
    if (!newTag || selectedTags.includes(newTag)) {
      return
    }

    // Validate tag length before sending to backend
    if (newTag.length > METADATA_VALIDATION.MAX_TAG_LENGTH) {
      onValidationError?.(`Tag cannot exceed ${METADATA_VALIDATION.MAX_TAG_LENGTH} characters`)
      return
    }

    onCreate(newTag)
    setInputValue('')
    setIsOpen(false)
    setHighlightedIndex(-1)
  }

  const handleInputChange = (e) => {
    const value = e.target.value
    setInputValue(value)
    if (value.trim()) {
      setIsOpen(true)
    } else {
      setIsOpen(false)
    }
    setHighlightedIndex(-1)
  }

  const handleFocus = () => {
    if (inputValue.trim()) {
      setIsOpen(true)
    }
  }

  const handleBlur = () => {
    // Delay to allow click events on dropdown items to fire
    // Store ref for cleanup on unmount
    blurTimeoutRef.current = setTimeout(() => {
      setIsOpen(false)
    }, 150)
  }

  return (
    <div className={`relative ${className}`}>
      <input
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={isOpen}
        aria-controls="tag-listbox"
        aria-activedescendant={
          highlightedIndex >= 0 ? `tag-option-${highlightedIndex}` : undefined
        }
        aria-autocomplete="list"
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                   focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                   bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                   placeholder-gray-500 dark:placeholder-gray-400
                   disabled:opacity-50 disabled:cursor-not-allowed"
      />

      {isOpen && isLoading && (
        <div
          role="status"
          className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border
                     border-gray-300 dark:border-gray-600 rounded-md shadow-lg p-3"
        >
          <div className="flex items-center justify-center gap-2">
            <svg
              className="animate-spin h-5 w-5 text-blue-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="text-gray-600 dark:text-gray-400">Loading suggestions...</span>
          </div>
        </div>
      )}

      {isOpen && fuzzySearchResult.error && !isLoading && (
        <div
          role="alert"
          className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border
                     border-red-300 dark:border-red-600 rounded-md shadow-lg p-3"
        >
          <div className="flex items-center justify-center gap-2">
            <svg
              className="h-5 w-5 text-red-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <span className="text-red-600 dark:text-red-400">Failed to load suggestions</span>
          </div>
        </div>
      )}

      {isOpen && !isLoading && totalOptions > 0 && (
        <ul
          id="tag-listbox"
          role="listbox"
          ref={listRef}
          className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border
                     border-gray-300 dark:border-gray-600 rounded-md shadow-lg
                     max-h-60 overflow-auto"
        >
          {filteredTags.map((tag, index) => (
            <li
              key={tag.name}
              id={`tag-option-${index}`}
              data-index={index}
              role="option"
              aria-selected={highlightedIndex === index}
              className={`px-3 py-2 cursor-pointer flex justify-between items-center
                         ${
                           highlightedIndex === index
                             ? 'bg-blue-100 dark:bg-blue-900'
                             : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                         }`}
              onClick={() => handleSelect(tag.name)}
              onMouseEnter={() => setHighlightedIndex(index)}
            >
              <div className="flex items-center gap-2 flex-1">
                <HighlightedMatch text={tag.name} query={inputValue} />
                {tag.score !== undefined && shouldUseFuzzySearch && (
                  <span
                    data-testid="match-score"
                    className="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-800
                               text-blue-700 dark:text-blue-300"
                    title={`Match quality: ${Math.round(tag.score * 100)}%`}
                  >
                    {Math.round(tag.score * 100)}%
                  </span>
                )}
              </div>
              <span className="text-gray-500 text-sm ml-2">({tag.count})</span>
            </li>
          ))}

          {showCreateOption && (
            <li
              id={`tag-option-${filteredTags.length}`}
              data-index={filteredTags.length}
              role="option"
              aria-selected={highlightedIndex === filteredTags.length}
              className={`px-3 py-2 cursor-pointer flex items-center gap-2
                         ${
                           highlightedIndex === filteredTags.length
                             ? 'bg-green-100 dark:bg-green-900'
                             : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                         }`}
              onClick={handleCreate}
              onMouseEnter={() => setHighlightedIndex(filteredTags.length)}
            >
              <span className="text-green-600 dark:text-green-400">
                + Create
              </span>
              <span className="font-medium">&quot;{inputValue.trim()}&quot;</span>
            </li>
          )}
        </ul>
      )}
    </div>
  )
}

TagAutocomplete.propTypes = {
  tags: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      count: PropTypes.number.isRequired,
    })
  ),
  selectedTags: PropTypes.arrayOf(PropTypes.string),
  onSelect: PropTypes.func.isRequired,
  onCreate: PropTypes.func.isRequired,
  onValidationError: PropTypes.func,
  placeholder: PropTypes.string,
  disabled: PropTypes.bool,
  className: PropTypes.string,
}

export default TagAutocomplete
