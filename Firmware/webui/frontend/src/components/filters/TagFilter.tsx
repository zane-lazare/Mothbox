import { useState, useMemo, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { useFilterContext } from '../../contexts/FilterContext'
import { getAllTags } from '../../utils/api'
import TagChip from '../gallery/TagChip'

interface TagItem {
  tag: string
  count?: number
}

interface TagsResponse {
  tags: TagItem[]
}

/**
 * TagFilter Component
 *
 * Tag selection filter with multi-select, search, and match mode toggle.
 * Integrates with FilterContext for state management.
 *
 * Features:
 * - Multi-select tag checkboxes
 * - Search/filter input to find tags
 * - Selected tags displayed as removable chips
 * - Toggle between "Any" (OR) and "All" (AND) matching
 * - Loading, empty, and error states
 *
 * @component
 * @example
 * <FilterSection id="tags" title="Tags">
 *   <TagFilter />
 * </FilterSection>
 */
export function TagFilter() {
  const { tags, setTags } = useFilterContext()
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch tags from API
  const {
    data: tagsData,
    isLoading,
    isError,
    error,
  } = useQuery<TagsResponse>({
    queryKey: ['tags'],
    queryFn: () => getAllTags().then(res => res.data),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
  })

  // Extract tag list with counts
  const availableTags = useMemo(() => {
    if (!tagsData?.tags) return []
    return tagsData.tags
  }, [tagsData])

  // Filter tags based on search query
  const filteredTags = useMemo(() => {
    if (!searchQuery.trim()) return availableTags

    const query = searchQuery.toLowerCase().trim()
    return availableTags.filter(tagItem =>
      tagItem.tag.toLowerCase().includes(query)
    )
  }, [availableTags, searchQuery])

  // Handle tag selection toggle
  const handleTagToggle = useCallback((tag: string) => {
    const isSelected = tags.selected.includes(tag)
    const newSelected = isSelected
      ? tags.selected.filter(t => t !== tag)
      : [...tags.selected, tag]

    setTags(newSelected, tags.matchMode)
  }, [tags, setTags])

  // Handle removing tag from selected chips
  const handleRemoveTag = useCallback((tag: string) => {
    const newSelected = tags.selected.filter(t => t !== tag)
    setTags(newSelected, tags.matchMode)
  }, [tags, setTags])

  // Handle match mode toggle
  const handleMatchModeToggle = useCallback(() => {
    const newMode = tags.matchMode === 'any' ? 'all' : 'any'
    setTags(tags.selected, newMode)
  }, [tags, setTags])

  // Handle search input change
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value)
  }, [])

  // Clear search
  const handleClearSearch = useCallback(() => {
    setSearchQuery('')
  }, [])

  // Loading state
  if (isLoading) {
    return (
      <div className="p-4">
        <div className="flex items-center justify-center py-8">
          <div className="animate-pulse text-gray-500 dark:text-gray-400">
            Loading tags...
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (isError) {
    return (
      <div className="p-4">
        <div className="text-sm text-red-600 dark:text-red-400">
          Failed to load tags: {error?.message || 'Unknown error'}
        </div>
      </div>
    )
  }

  // Empty state - no tags available
  if (availableTags.length === 0) {
    return (
      <div className="p-4">
        <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
          No tags available
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {/* Selected Tags Chips */}
      {tags.selected.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-gray-700 dark:text-gray-300">
            Selected ({tags.selected.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {tags.selected.map(tag => (
              <TagChip
                key={tag}
                tag={tag}
                removable
                onRemove={() => handleRemoveTag(tag)}
                size="sm"
              />
            ))}
          </div>
        </div>
      )}

      {/* Match Mode Toggle */}
      {tags.selected.length > 1 && (
        <div className="flex items-center gap-2 pb-2 border-b border-gray-200 dark:border-gray-700">
          <span className="text-xs text-gray-600 dark:text-gray-400">
            Match:
          </span>
          <button
            type="button"
            onClick={handleMatchModeToggle}
            className="text-xs font-medium px-3 py-1 rounded-md
                     bg-gray-100 dark:bg-gray-700
                     text-gray-700 dark:text-gray-300
                     hover:bg-gray-200 dark:hover:bg-gray-600
                     focus:outline-none focus:ring-2 focus:ring-blue-500
                     transition-colors duration-150"
            aria-label={`Match mode: ${tags.matchMode}. Click to toggle.`}
          >
            {tags.matchMode === 'any' ? 'Any' : 'All'}
          </button>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {tags.matchMode === 'any'
              ? 'Photos matching any selected tag'
              : 'Photos matching all selected tags'}
          </span>
        </div>
      )}

      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
          <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" aria-hidden="true" />
        </div>
        <input
          type="text"
          placeholder="Search tags..."
          value={searchQuery}
          onChange={handleSearchChange}
          className="w-full pl-10 pr-10 py-2 text-sm
                   border border-gray-300 dark:border-gray-600
                   rounded-md
                   bg-white dark:bg-gray-800
                   text-gray-900 dark:text-gray-100
                   placeholder-gray-400 dark:placeholder-gray-500
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   transition-colors duration-150"
          aria-label="Search tags"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={handleClearSearch}
            className="absolute inset-y-0 right-0 flex items-center pr-3
                     text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Clear search"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Tag List */}
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {filteredTags.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
            No tags match &quot;{searchQuery}&quot;
          </div>
        ) : (
          filteredTags.map(tagItem => {
            const isSelected = tags.selected.includes(tagItem.tag)

            return (
              <label
                key={tagItem.tag}
                className="flex items-center gap-2 p-2 rounded
                         hover:bg-gray-50 dark:hover:bg-gray-700/50
                         cursor-pointer group
                         transition-colors duration-150"
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => handleTagToggle(tagItem.tag)}
                  className="h-4 w-4 rounded
                           border-gray-300 dark:border-gray-600
                           text-blue-600 dark:text-blue-500
                           focus:ring-blue-500 focus:ring-offset-0
                           cursor-pointer"
                  aria-label={`Select tag ${tagItem.tag}`}
                />
                <span className="flex-1 text-sm text-gray-700 dark:text-gray-300">
                  {tagItem.tag}
                </span>
                {tagItem.count !== undefined && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {tagItem.count}
                  </span>
                )}
              </label>
            )
          })
        )}
      </div>
    </div>
  )
}

export default TagFilter
