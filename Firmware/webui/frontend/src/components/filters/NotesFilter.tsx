import { useState, useEffect, useCallback } from 'react'
import { useFilterContext } from '../../contexts/FilterContext'

/**
 * NotesFilter Component
 *
 * Provides filtering for photos based on notes presence and content.
 * Integrates with FilterContext for state management.
 *
 * Features:
 * - Three-state toggle: All, Has Notes, No Notes
 * - Keyword search within notes content
 * - Debounced search input (300ms)
 * - Clear button for keyword search
 * - Dark mode compatible
 * - Full keyboard accessibility
 *
 * @component
 * @example
 * <NotesFilter />
 */
export function NotesFilter() {
  const { notes, setNotes, clearFilter } = useFilterContext()
  const [searchInput, setSearchInput] = useState(notes.keywords || '')

  // Sync local search input with context when context changes externally
  useEffect(() => {
    setSearchInput(notes.keywords || '')
  }, [notes.keywords])

  // Debounced keyword update (300ms)
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchInput !== notes.keywords) {
        setNotes(notes.hasNotes, searchInput)
      }
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [searchInput, notes.hasNotes, notes.keywords, setNotes])

  // Handle toggle button click
  const handleToggleClick = useCallback((value: boolean | null) => {
    // Special handling for null value due to FilterContext using ?? operator
    // which treats null as "undefined" rather than an explicit value
    if (value === null && notes.hasNotes !== null) {
      // Need to reset hasNotes to null - use clearFilter then restore keywords
      const savedKeywords = searchInput
      clearFilter('notes')
      // Update local state to restore keywords
      if (savedKeywords) {
        setSearchInput(savedKeywords)
      }
    } else if (value !== null) {
      setNotes(value, searchInput)
    }
    // If value is null and hasNotes is already null, do nothing
  }, [notes.hasNotes, searchInput, setNotes, clearFilter])

  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchInput(e.target.value)
  }

  // Handle clear search button
  const handleClearSearch = useCallback(() => {
    setSearchInput('')
    setNotes(notes.hasNotes, '')
  }, [notes.hasNotes, setNotes])

  // Handle clear all button
  const handleClear = () => {
    clearFilter('notes')
    setSearchInput('')
  }

  // Determine if filter has any values
  // Check both context keywords and local searchInput to handle debounce delay
  const hasValues = notes.hasNotes !== null || notes.keywords !== '' || searchInput !== ''

  // Determine active toggle button
  const getToggleClass = (value: boolean | null) => {
    const isActive = notes.hasNotes === value
    return `px-4 py-2 text-sm rounded-none first:rounded-l last:rounded-r border transition-colors duration-150
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:z-10
            dark:focus:ring-offset-gray-800
            ${
              isActive
                ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`
  }

  return (
    <div className="p-4 space-y-4">
      {/* Toggle Buttons */}
      <div>
        <label
          id="notes-toggle-label"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Notes Status
        </label>
        <div
          className="inline-flex"
          role="group"
          aria-labelledby="notes-toggle-label"
        >
          <button
            onClick={() => handleToggleClick(null)}
            className={getToggleClass(null)}
            type="button"
            aria-pressed={notes.hasNotes === null}
            aria-label="Show all photos"
          >
            All
          </button>
          <button
            onClick={() => handleToggleClick(true)}
            className={getToggleClass(true)}
            type="button"
            aria-pressed={notes.hasNotes === true}
            aria-label="Show only photos with notes"
          >
            Has Notes
          </button>
          <button
            onClick={() => handleToggleClick(false)}
            className={getToggleClass(false)}
            type="button"
            aria-pressed={notes.hasNotes === false}
            aria-label="Show only photos without notes"
          >
            No Notes
          </button>
        </div>
      </div>

      {/* Keyword Search */}
      <div>
        <label
          htmlFor="notes-keyword-search"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Search in Notes
        </label>
        <div className="relative">
          {/* Search Icon */}
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg
              className="h-4 w-4 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          {/* Search Input */}
          <input
            id="notes-keyword-search"
            type="text"
            value={searchInput}
            onChange={handleSearchChange}
            placeholder="Search in notes..."
            className="w-full pl-10 pr-10 py-2 text-sm border border-gray-300 dark:border-gray-600
                       rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                       placeholder-gray-400 dark:placeholder-gray-500
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:focus:ring-blue-400"
            aria-label="Search in notes"
          />

          {/* Clear Search Button */}
          {searchInput && (
            <button
              onClick={handleClearSearch}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              type="button"
              aria-label="Clear search"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Clear Button */}
      {hasValues && (
        <div>
          <button
            onClick={handleClear}
            className="w-full px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300
                       bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600
                       border border-gray-300 dark:border-gray-600 rounded
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                       dark:focus:ring-offset-gray-800
                       transition-colors duration-150"
            type="button"
            aria-label="Clear notes filter"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  )
}

export default NotesFilter
