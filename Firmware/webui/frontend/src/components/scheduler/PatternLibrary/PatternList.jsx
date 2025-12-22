import { useState, useMemo, useCallback } from 'react'
import PropTypes from 'prop-types'
import { useBuiltinPatterns } from '../../../hooks/useEventPatterns'
import PatternCard from './PatternCard'
import PatternFilters from './PatternFilters'
import PatternDetailsDrawer from './PatternDetailsDrawer'

/**
 * PatternList - Display and filter list of event patterns
 *
 * Supports two modes:
 * - standalone: Full filters, search, view modes, and details drawer
 * - embedded: Compact view with category filter only, direct selection
 */
function PatternList({
  onPatternSelect,
  selectedPatternId = null,
  mode = 'standalone',
  className = ''
}) {
  // Fetch patterns from API
  const { data, isLoading, isError, error, refetch } = useBuiltinPatterns()

  // Filter state
  const [category, setCategory] = useState('all')
  const [viewMode, setViewMode] = useState('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTags, setSelectedTags] = useState([])

  // Drawer state (standalone mode only)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedPattern, setSelectedPattern] = useState(null)

  // Compute available tags with counts
  const availableTags = useMemo(() => {
    if (!data?.patterns) return []

    const tagCounts = {}
    data.patterns.forEach(p => {
      p.tags?.forEach(tag => {
        tagCounts[tag] = (tagCounts[tag] || 0) + 1
      })
    })

    return Object.entries(tagCounts)
      .map(([tag, count]) => ({ tag, count }))
      .sort((a, b) => b.count - a.count)
  }, [data?.patterns])

  // Filter patterns
  const filteredPatterns = useMemo(() => {
    if (!data?.patterns) return []

    return data.patterns
      .filter(p => category === 'all' || p.category === category)
      .filter(p =>
        selectedTags.length === 0 ||
        selectedTags.some(t => p.tags?.includes(t))
      )
      .filter(p =>
        !searchQuery ||
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
  }, [data?.patterns, category, selectedTags, searchQuery])

  // Reset all filters
  const handleResetFilters = useCallback(() => {
    setCategory('all')
    setSearchQuery('')
    setSelectedTags([])
    setViewMode('grid')
  }, [])

  // Handle card click
  const handleCardClick = useCallback((pattern) => {
    if (mode === 'standalone') {
      // Open drawer in standalone mode
      setSelectedPattern(pattern)
      setDrawerOpen(true)
    } else {
      // Direct selection in embedded mode
      onPatternSelect(pattern)
    }
  }, [mode, onPatternSelect])

  // Handle "Use Pattern" from card
  const handleUsePattern = useCallback((pattern) => {
    onPatternSelect(pattern)
  }, [onPatternSelect])

  // Handle drawer close
  const handleDrawerClose = useCallback(() => {
    setDrawerOpen(false)
  }, [])

  // Handle "Use Pattern" from drawer
  const handleDrawerUsePattern = useCallback((pattern) => {
    onPatternSelect(pattern)
    setDrawerOpen(false)
  }, [onPatternSelect])

  // Loading state
  if (isLoading) {
    return (
      <div data-testid="loading-skeleton" className={`space-y-4 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-12 bg-gray-200 rounded" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-48 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (isError) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <div className="text-red-600 mb-4">
          <h2 className="text-lg font-semibold">Failed to load patterns</h2>
          <p className="text-sm mt-2">
            {error?.message || 'An unexpected error occurred'}
          </p>
        </div>
        <button
          onClick={refetch}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    )
  }

  // Empty state (no patterns at all)
  if (!data?.patterns || data.patterns.length === 0) {
    return (
      <div className={`text-center py-8 text-gray-500 ${className}`}>
        <p className="text-lg">No patterns available</p>
        <p className="text-sm mt-2">
          Pattern library is empty. Add patterns to get started.
        </p>
      </div>
    )
  }

  const totalCount = data.patterns.length
  const filteredCount = filteredPatterns.length

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Warnings banner */}
      {data.warnings && data.warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-yellow-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">Warnings</h3>
              <div className="mt-2 text-sm text-yellow-700">
                <ul className="list-disc list-inside space-y-1">
                  {data.warnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <PatternFilters
        category={category}
        onCategoryChange={setCategory}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedTags={selectedTags}
        onTagsChange={setSelectedTags}
        availableTags={availableTags}
        showViewToggle={mode === 'standalone'}
      />

      {/* Filter count and reset */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Showing {filteredCount} of {totalCount} patterns
        </p>
        {(category !== 'all' || searchQuery || selectedTags.length > 0) && (
          <button
            onClick={handleResetFilters}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Reset filters
          </button>
        )}
      </div>

      {/* Empty filtered state */}
      {filteredPatterns.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p className="text-lg">No patterns match your filters</p>
          <p className="text-sm mt-2">
            Try adjusting your filters or search query.
          </p>
        </div>
      )}

      {/* Pattern grid or list */}
      {filteredPatterns.length > 0 && (
        <>
          {viewMode === 'grid' ? (
            <div
              data-testid="pattern-grid"
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            >
              {filteredPatterns.map(pattern => (
                <PatternCard
                  key={pattern.pattern_id}
                  pattern={pattern}
                  onClick={() => handleCardClick(pattern)}
                  onSelect={() => handleUsePattern(pattern)}
                  isSelected={pattern.pattern_id === selectedPatternId}
                />
              ))}
            </div>
          ) : (
            <div
              data-testid="pattern-list"
              className="flex flex-col space-y-4"
            >
              {filteredPatterns.map(pattern => (
                <PatternCard
                  key={pattern.pattern_id}
                  pattern={pattern}
                  onClick={() => handleCardClick(pattern)}
                  onSelect={() => handleUsePattern(pattern)}
                  isSelected={pattern.pattern_id === selectedPatternId}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Details drawer (standalone mode only) */}
      {mode === 'standalone' && (
        <PatternDetailsDrawer
          isOpen={drawerOpen}
          pattern={selectedPattern}
          onClose={handleDrawerClose}
          onSelect={handleDrawerUsePattern}
        />
      )}
    </div>
  )
}

PatternList.propTypes = {
  onPatternSelect: PropTypes.func.isRequired,
  selectedPatternId: PropTypes.string,
  mode: PropTypes.oneOf(['standalone', 'embedded']),
  className: PropTypes.string
}

export default PatternList
