export interface FilterErrorFallbackProps {
  /** The error that was caught */
  error?: Error
  /** Callback to reset the error boundary and retry */
  onRetry: () => void
}

/**
 * Error fallback component for FilterDrawer errors.
 *
 * Displays an inline error message that matches the filter drawer design,
 * allowing users to retry without breaking the gallery page layout.
 *
 * @component
 * @param {Object} props - Component props
 * @param {Error} props.error - The error that was caught
 * @param {Function} props.onRetry - Callback to reset the error boundary and retry
 *
 * @example
 * <FilterErrorFallback
 *   error={new Error('Failed to load filters')}
 *   onRetry={() => resetErrorBoundary()}
 * />
 */
function FilterErrorFallback({ error, onRetry }: FilterErrorFallbackProps) {
  return (
    <aside
      role="complementary"
      aria-label="Filter error"
      className="fixed bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 z-40 flex flex-col lg:w-80 lg:top-0 lg:left-0 lg:bottom-0 md:w-72 md:top-0 md:left-0 md:bottom-0"
    >
      <div className="p-4 flex flex-col items-center justify-center h-full">
        {/* Error Icon */}
        <div className="flex items-center justify-center w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full">
          <svg
            className="w-6 h-6 text-red-600 dark:text-red-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        {/* Title */}
        <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
          Filter Error
        </h3>

        {/* Description */}
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 text-center">
          {error?.message || 'Unable to load filters'}
        </p>

        {/* Technical details (collapsed by default, only in development) */}
        {import.meta.env.DEV && error?.stack && (
          <details className="mt-3 w-full text-xs">
            <summary className="cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
              Show technical details
            </summary>
            <pre className="mt-2 p-2 bg-gray-100 dark:bg-gray-700 rounded text-xs overflow-auto max-h-32 text-gray-800 dark:text-gray-200">
              {error.stack}
            </pre>
          </details>
        )}

        {/* Retry Button */}
        <button
          onClick={onRetry}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors"
        >
          Try Again
        </button>
      </div>
    </aside>
  )
}

export default FilterErrorFallback
