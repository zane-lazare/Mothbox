import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  MagnifyingGlassIcon,
  XMarkIcon,
  Squares2X2Icon,
  ListBulletIcon,
} from '@heroicons/react/24/outline';

/**
 * PatternFilters component for filtering pattern library items
 *
 * Provides category filtering (all/built-in/user), tag filtering,
 * search, and view mode toggle (grid/list).
 */
function PatternFilters({
  category,
  onCategoryChange,
  selectedTags = [],
  onTagsChange,
  availableTags = [],
  searchQuery,
  onSearchChange,
  viewMode,
  onViewModeChange,
  showViewToggle = true,
}) {
  // Local state for debounced search
  const [localSearch, setLocalSearch] = useState(searchQuery);

  // Sync local search with prop changes
  useEffect(() => {
    setLocalSearch(searchQuery);
  }, [searchQuery]);

  // Debounce search input (300ms)
  // Note: Parent component should memoize onSearchChange with useCallback
  // to prevent unnecessary re-renders when the callback reference changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localSearch !== searchQuery) {
        onSearchChange(localSearch);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [localSearch, searchQuery, onSearchChange]);

  const handleTagClick = (tag) => {
    const safeSelectedTags = selectedTags || [];
    if (safeSelectedTags.includes(tag)) {
      onTagsChange(safeSelectedTags.filter((t) => t !== tag));
    } else {
      onTagsChange([...safeSelectedTags, tag]);
    }
  };

  const handleClearSearch = () => {
    setLocalSearch('');
    onSearchChange('');
  };

  const categories = [
    { value: 'all', label: 'All' },
    { value: 'built-in', label: 'Built-in' },
    { value: 'user', label: 'User' },
  ];

  return (
    <div className="space-y-3">
      {/* Row 1: Category filters and view toggle */}
      <div className="flex items-center justify-between">
        {/* Category buttons */}
        <div className="flex gap-2">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => onCategoryChange(cat.value)}
              aria-pressed={category === cat.value}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                category === cat.value
                  ? 'bg-blue-600 text-white dark:bg-blue-500'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* View mode toggle */}
        {showViewToggle && (
          <div className="flex gap-1 bg-gray-100 dark:bg-gray-700 rounded-md p-1">
            <button
              onClick={() => onViewModeChange('grid')}
              aria-pressed={viewMode === 'grid'}
              aria-label="Grid view"
              className={`p-2 rounded transition-colors ${
                viewMode === 'grid'
                  ? 'bg-white text-blue-600 dark:bg-gray-600 dark:text-blue-400'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <Squares2X2Icon className="h-5 w-5" />
            </button>
            <button
              onClick={() => onViewModeChange('list')}
              aria-pressed={viewMode === 'list'}
              aria-label="List view"
              className={`p-2 rounded transition-colors ${
                viewMode === 'list'
                  ? 'bg-white text-blue-600 dark:bg-gray-600 dark:text-blue-400'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <ListBulletIcon className="h-5 w-5" />
            </button>
          </div>
        )}
      </div>

      {/* Row 2: Search input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="text"
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
          placeholder="Search patterns..."
          aria-label="Search patterns"
          className="block w-full pl-10 pr-10 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {localSearch && (
          <button
            onClick={handleClearSearch}
            aria-label="Clear search"
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Row 3: Tag filters (scrollable) */}
      {availableTags && availableTags.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
          {availableTags.map(({ tag, count }) => {
            const isSelected = (selectedTags || []).includes(tag);
            return (
              <button
                key={tag}
                onClick={() => handleTagClick(tag)}
                data-testid={`tag-${tag}`}
                className={`flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  isSelected
                    ? 'bg-blue-600 text-white dark:bg-blue-500'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {tag} ({count})
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

PatternFilters.propTypes = {
  /** Current category filter value */
  category: PropTypes.oneOf(['all', 'built-in', 'user']).isRequired,
  /** Callback when category changes */
  onCategoryChange: PropTypes.func.isRequired,
  /** Currently selected tag filters */
  selectedTags: PropTypes.arrayOf(PropTypes.string),
  /** Callback when selected tags change */
  onTagsChange: PropTypes.func.isRequired,
  /** Available tags with counts for filter chips */
  availableTags: PropTypes.arrayOf(
    PropTypes.shape({
      tag: PropTypes.string.isRequired,
      count: PropTypes.number.isRequired,
    })
  ),
  /** Current search query */
  searchQuery: PropTypes.string.isRequired,
  /**
   * Callback when search query changes (debounced 300ms internally).
   * IMPORTANT: Should be memoized with useCallback to prevent unnecessary re-renders.
   */
  onSearchChange: PropTypes.func.isRequired,
  /** Current view mode */
  viewMode: PropTypes.oneOf(['grid', 'list']).isRequired,
  /** Callback when view mode changes */
  onViewModeChange: PropTypes.func.isRequired,
  /** Whether to show the grid/list view toggle (hidden in embedded mode) */
  showViewToggle: PropTypes.bool,
};

export default PatternFilters;
