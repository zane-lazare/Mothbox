import { useState } from 'react'
import PropTypes from 'prop-types'
import { ChevronRightIcon } from '@heroicons/react/24/outline'
import TagAutocomplete from '../gallery/TagAutocomplete'

function FilterPanel({
  filter,
  onChange,
  photoCount = null,
  isLoadingCount = false,
  disabled = false,
}) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [dateError, setDateError] = useState(null)

  const handleFilterChange = (field, value) => {
    // Validate date range
    if (field === 'date_start' || field === 'date_end') {
      const newFilter = { ...filter, [field]: value }

      if (newFilter.date_start && newFilter.date_end) {
        if (new Date(newFilter.date_start) > new Date(newFilter.date_end)) {
          setDateError('End date must be after start date')
          return
        }
      }
      setDateError(null)
    }

    onChange({ ...filter, [field]: value })
  }

  const handleTagSelect = (tag) => {
    const newTags = [...(filter.tags || []), tag]
    handleFilterChange('tags', newTags)
  }

  const handleTagCreate = (tag) => {
    // Just add the tag to the filter (don't create in backend)
    handleTagSelect(tag)
  }

  const handleTagRemove = (tagToRemove) => {
    const newTags = (filter.tags || []).filter((tag) => tag !== tagToRemove)
    handleFilterChange('tags', newTags)
  }

  return (
    <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800
                   hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        aria-expanded={isExpanded}
        aria-controls="filter-panel-content"
      >
        <span className="font-semibold text-gray-900 dark:text-gray-100">
          Photo Filters
        </span>
        <ChevronRightIcon
          className={`h-5 w-5 text-gray-600 dark:text-gray-400 transition-transform
                     ${isExpanded ? 'rotate-90' : ''}`}
          data-testid="chevron-icon"
        />
      </button>

      {/* Content */}
      {isExpanded && (
        <div id="filter-panel-content" className="p-4 space-y-4 bg-white dark:bg-gray-900">
          {/* Date Range */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="date-start"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Start Date
              </label>
              <input
                type="date"
                id="date-start"
                value={filter.date_start || ''}
                onChange={(e) => handleFilterChange('date_start', e.target.value || null)}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                          focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                          bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                          disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            <div>
              <label
                htmlFor="date-end"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                End Date
              </label>
              <input
                type="date"
                id="date-end"
                value={filter.date_end || ''}
                onChange={(e) => handleFilterChange('date_end', e.target.value || null)}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                          focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                          bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                          disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>

          {dateError && (
            <p className="text-sm text-red-600 dark:text-red-400">
              {dateError}
            </p>
          )}

          {/* Deployment */}
          <div>
            <label
              htmlFor="deployment"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Deployment
            </label>
            <select
              id="deployment"
              value={filter.deployment || ''}
              onChange={(e) => handleFilterChange('deployment', e.target.value || null)}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                        focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                        bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                        disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">All deployments</option>
              {/* TODO: Load deployments from API */}
            </select>
          </div>

          {/* Tags */}
          <div>
            <label
              htmlFor="tags-input"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Tags
            </label>
            <div className="space-y-2">
              <TagAutocomplete
                selectedTags={filter.tags || []}
                onSelect={handleTagSelect}
                onCreate={handleTagCreate}
                disabled={disabled}
                placeholder="Add tags to filter..."
              />
              {(filter.tags || []).length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {filter.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 px-2 py-1 text-sm
                                bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200
                                rounded-md"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => handleTagRemove(tag)}
                        disabled={disabled}
                        className="text-blue-600 dark:text-blue-300 hover:text-blue-800
                                  dark:hover:text-blue-100 disabled:opacity-50"
                        aria-label={`Remove tag ${tag}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Series Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Series Type
            </label>
            <div className="space-y-2" role="radiogroup" aria-label="Series type">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="series-type"
                  value=""
                  checked={!filter.series_type}
                  onChange={() => handleFilterChange('series_type', null)}
                  disabled={disabled}
                  className="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500
                            disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <span className="text-gray-900 dark:text-gray-100">All</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="series-type"
                  value="hdr"
                  checked={filter.series_type === 'hdr'}
                  onChange={() => handleFilterChange('series_type', 'hdr')}
                  disabled={disabled}
                  className="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500
                            disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <span className="text-gray-900 dark:text-gray-100">HDR Only</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="series-type"
                  value="focus_bracket"
                  checked={filter.series_type === 'focus_bracket'}
                  onChange={() => handleFilterChange('series_type', 'focus_bracket')}
                  disabled={disabled}
                  className="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500
                            disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <span className="text-gray-900 dark:text-gray-100">Focus Bracket Only</span>
              </label>
            </div>
          </div>

          {/* Has Species */}
          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={filter.has_species || false}
                onChange={(e) => handleFilterChange('has_species', e.target.checked)}
                disabled={disabled}
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                          disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <span className="text-sm text-gray-900 dark:text-gray-100">
                Only photos with species identification
              </span>
            </label>
          </div>

          {/* Photo Count */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {isLoadingCount ? (
                <span>Counting photos...</span>
              ) : photoCount !== null ? (
                <span>{photoCount} photos match</span>
              ) : (
                <span>Select filters to see count</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

FilterPanel.propTypes = {
  filter: PropTypes.shape({
    date_start: PropTypes.string,
    date_end: PropTypes.string,
    deployment: PropTypes.string,
    tags: PropTypes.arrayOf(PropTypes.string),
    series_type: PropTypes.string,
    has_species: PropTypes.bool,
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  photoCount: PropTypes.number,
  isLoadingCount: PropTypes.bool,
  disabled: PropTypes.bool,
}

export default FilterPanel
