import { useMemo } from 'react'
import PropTypes from 'prop-types'
import { useFilterContext } from '../../contexts/FilterContext'
import { DATE_PRESETS } from '../../utils/filterQueryBuilder'

/**
 * DateRangeFilter Component
 *
 * Provides date filtering with preset buttons and custom date range inputs.
 * Integrates with FilterContext for state management.
 *
 * Features:
 * - Preset buttons (Today, Last 7 Days, Last 30 Days, etc.)
 * - Custom date range inputs (start and end dates)
 * - Active state highlighting
 * - Clear button to reset filter
 * - Dark mode compatible
 * - Full keyboard accessibility
 *
 * @component
 * @example
 * <DateRangeFilter />
 */
export function DateRangeFilter() {
  const { dateRange, setDateRange, clearFilter } = useFilterContext()

  // Get preset button configurations
  const presetButtons = useMemo(() => {
    return Object.entries(DATE_PRESETS).map(([key, config]) => ({
      key,
      label: config.label,
    }))
  }, [])

  // Determine if a preset is currently active
  const isPresetActive = (presetKey) => {
    return dateRange.preset === presetKey
  }

  // Determine if we're in custom mode (dates set but no preset, or preset is empty string)
  const isCustomMode = useMemo(() => {
    return (!dateRange.preset || dateRange.preset === '') && (dateRange.startDate || dateRange.endDate)
  }, [dateRange.preset, dateRange.startDate, dateRange.endDate])

  // Handle preset button click
  const handlePresetClick = (presetKey) => {
    setDateRange(presetKey, null, null)
  }

  // Handle custom date input changes
  const handleStartDateChange = (e) => {
    const value = e.target.value
    // Clear preset by passing empty string when custom date is entered
    setDateRange('', value, dateRange.endDate)
  }

  const handleEndDateChange = (e) => {
    const value = e.target.value
    // Clear preset by passing empty string when custom date is entered
    setDateRange('', dateRange.startDate, value)
  }

  // Handle clear button
  const handleClear = () => {
    clearFilter('dateRange')
  }

  // Check if filter has any values (treat empty string preset as no preset)
  const hasValues = useMemo(() => {
    const hasPreset = dateRange.preset && dateRange.preset !== ''
    return Boolean(hasPreset || dateRange.startDate || dateRange.endDate)
  }, [dateRange.preset, dateRange.startDate, dateRange.endDate])

  return (
    <div className="p-4 space-y-4">
      {/* Preset Buttons */}
      <div>
        <label
          id="date-preset-label"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Quick Select
        </label>
        <div
          className="grid grid-cols-2 gap-2"
          role="group"
          aria-labelledby="date-preset-label"
        >
          {presetButtons.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handlePresetClick(key)}
              className={`px-3 py-2 text-sm rounded border transition-colors duration-150
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                         dark:focus:ring-offset-gray-800
                         ${
                           isPresetActive(key)
                             ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700'
                             : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                         }`}
              type="button"
              aria-pressed={isPresetActive(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Custom Date Range */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label
            id="custom-date-label"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Custom Range
          </label>
          {isCustomMode && (
            <span
              className="text-xs text-blue-600 dark:text-blue-400"
              aria-label="Custom date range active"
            >
              Custom
            </span>
          )}
        </div>
        <div className="space-y-2" role="group" aria-labelledby="custom-date-label">
          {/* Start Date Input */}
          <div>
            <label
              htmlFor="start-date-input"
              className="block text-xs text-gray-600 dark:text-gray-400 mb-1"
            >
              Start Date
            </label>
            <input
              id="start-date-input"
              type="date"
              value={dateRange.startDate || ''}
              onChange={handleStartDateChange}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600
                         rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         dark:focus:ring-blue-400"
              aria-label="Start date"
            />
          </div>

          {/* End Date Input */}
          <div>
            <label
              htmlFor="end-date-input"
              className="block text-xs text-gray-600 dark:text-gray-400 mb-1"
            >
              End Date
            </label>
            <input
              id="end-date-input"
              type="date"
              value={dateRange.endDate || ''}
              onChange={handleEndDateChange}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600
                         rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         dark:focus:ring-blue-400"
              aria-label="End date"
            />
          </div>
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
            aria-label="Clear date filter"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  )
}

DateRangeFilter.propTypes = {
  // No props - uses FilterContext for state
}

export default DateRangeFilter
