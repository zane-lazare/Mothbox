import { useState, useRef, useEffect } from 'react'
import { MagnifyingGlassIcon, XMarkIcon, QuestionMarkCircleIcon } from '@heroicons/react/24/outline'
import { SearchHelp } from './SearchHelp'
import { Z_INDEX } from '../../constants/config'

const MAX_RECENT_SEARCHES = 5
const RECENT_SEARCHES_KEY = 'recentSearches'

export interface SearchBarProps {
  value: string
  onChange?: (value: string) => void
  onSearch?: (query: string) => void
  onClear?: () => void
  isLoading?: boolean
  placeholder?: string
  autoFocus?: boolean
  className?: string
}

/**
 * SearchBar component for photo search
 */
export function SearchBar({
  value,
  onChange,
  onSearch,
  onClear,
  isLoading = false,
  placeholder = 'Search photos by tag, species, filename, notes...',
  autoFocus = false,
  className = ''
}: SearchBarProps) {
  const [showHelp, setShowHelp] = useState(false)
  const [showRecentSearches, setShowRecentSearches] = useState(false)
  const [recentSearches, setRecentSearches] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const helpRef = useRef<HTMLDivElement>(null)
  const recentSearchesRef = useRef<HTMLDivElement>(null)

  // Load recent searches from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(RECENT_SEARCHES_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed)) {
          setRecentSearches(parsed.slice(0, MAX_RECENT_SEARCHES))
        }
      }
    } catch (error) {
      console.warn('Failed to load recent searches:', error)
      setRecentSearches([])
    }
  }, [])

  // Save recent searches to localStorage
  const saveRecentSearches = (searches: string[]) => {
    try {
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(searches))
      setRecentSearches(searches)
    } catch (error) {
      console.warn('Failed to save recent searches:', error)
    }
  }

  // Add search to recent searches
  const addToRecentSearches = (query: string) => {
    const trimmed = query.trim()
    if (!trimmed) return

    // Remove if already exists and add to front
    const filtered = recentSearches.filter(s => s !== trimmed)
    const updated = [trimmed, ...filtered].slice(0, MAX_RECENT_SEARCHES)
    saveRecentSearches(updated)
  }

  // Clear recent searches
  const clearRecentSearches = () => {
    saveRecentSearches([])
  }

  // Handle click outside to close help and recent searches
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (helpRef.current && !helpRef.current.contains(event.target as Node)) {
        setShowHelp(false)
      }
      if (
        recentSearchesRef.current &&
        !recentSearchesRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowRecentSearches(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  // Handle input change
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange?.(e.target.value)
  }

  // Handle key down
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const trimmed = value.trim()
      if (trimmed) {
        addToRecentSearches(trimmed)
        onSearch?.(trimmed)
        setShowRecentSearches(false)
      }
    } else if (e.key === 'Escape') {
      if (value) {
        onClear?.()
      }
      setShowRecentSearches(false)
    }
  }

  // Handle clear button click
  const handleClear = () => {
    onClear?.()
    inputRef.current?.focus()
  }

  // Handle help button click
  const handleHelpClick = () => {
    setShowHelp(!showHelp)
  }

  // Handle help close
  const handleHelpClose = () => {
    setShowHelp(false)
  }

  // Handle input focus
  const handleFocus = () => {
    if (recentSearches.length > 0) {
      setShowRecentSearches(true)
    }
  }

  // Handle input blur
  const handleBlur = () => {
    // Delay to allow click events on dropdown items to fire
    setTimeout(() => {
      setShowRecentSearches(false)
    }, 150)
  }

  // Handle recent search click
  const handleRecentSearchClick = (query: string) => {
    onChange?.(query)
    onSearch?.(query)
    addToRecentSearches(query)
    setShowRecentSearches(false)
  }

  // Handle clear history click
  const handleClearHistory = () => {
    clearRecentSearches()
    setShowRecentSearches(false)
  }

  return (
    <div className={`relative ${className}`}>
      <div className="relative">
        {/* Search icon */}
        <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
          <MagnifyingGlassIcon
            className="w-5 h-5 text-gray-400"
            aria-label="Search"
            aria-hidden="true"
          />
        </div>

        {/* Search input */}
        <input
          ref={inputRef}
          type="search"
          role="searchbox"
          aria-label="Search photos"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className="w-full pl-10 pr-20 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                     bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                     placeholder-gray-500 dark:placeholder-gray-400"
        />

        {/* Right side buttons */}
        <div className="absolute inset-y-0 right-0 flex items-center pr-2 gap-1">
          {/* Loading spinner */}
          {isLoading && (
            <div role="status" data-testid="search-loading">
              <svg
                className="animate-spin h-5 w-5 text-blue-500"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
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
              <span className="sr-only">Loading...</span>
            </div>
          )}

          {/* Clear button */}
          {value && (
            <button
              type="button"
              onClick={handleClear}
              aria-label="Clear search"
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <XMarkIcon className="w-5 h-5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" />
            </button>
          )}

          {/* Help button */}
          <button
            type="button"
            onClick={handleHelpClick}
            aria-label="Search help"
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <QuestionMarkCircleIcon className="w-5 h-5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" />
          </button>
        </div>
      </div>

      {/* Recent searches dropdown */}
      {showRecentSearches && recentSearches.length > 0 && (
        <div
          ref={recentSearchesRef}
          role="listbox"
          className={`absolute ${Z_INDEX.DROPDOWN} w-full mt-1 bg-white dark:bg-gray-800 border
                     border-gray-300 dark:border-gray-600 rounded-md shadow-lg
                     max-h-60 overflow-auto`}
        >
          {recentSearches.slice(0, MAX_RECENT_SEARCHES).map((query, index) => (
            <div
              key={index}
              role="option"
              aria-selected="false"
              onClick={() => handleRecentSearchClick(query)}
              className="px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700
                         text-gray-900 dark:text-gray-100"
            >
              {query}
            </div>
          ))}
          <div
            className="px-3 py-2 border-t border-gray-200 dark:border-gray-700"
          >
            <button
              type="button"
              onClick={handleClearHistory}
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
            >
              Clear history
            </button>
          </div>
        </div>
      )}

      {/* Help dialog */}
      {showHelp && (
        <div ref={helpRef} className="absolute z-20 right-0 mt-2">
          <SearchHelp onClose={handleHelpClose} />
        </div>
      )}
    </div>
  )
}
