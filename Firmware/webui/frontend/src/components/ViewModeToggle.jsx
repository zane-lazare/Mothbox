/**
 * ViewModeToggle Component
 *
 * Toggle button for switching between grid and list gallery layouts.
 * Provides accessible UI with keyboard navigation and screen reader support.
 *
 * @param {Object} props - Component props
 * @param {('grid'|'list'|null)} props.currentView - Current active view mode
 * @param {Function} props.onViewChange - Callback when view mode changes
 * @param {boolean} [props.isLoading=false] - Whether preference is being saved
 */
export default function ViewModeToggle({ currentView, onViewChange, isLoading = false }) {
  // Normalize currentView to handle invalid values
  const normalizedView = currentView === 'list' ? 'list' : 'grid'

  // Warn in development if we received an unexpected non-null invalid value
  if (process.env.NODE_ENV === 'development' &&
      currentView != null &&
      currentView !== 'grid' &&
      currentView !== 'list') {
    console.warn(
      `ViewModeToggle received invalid currentView: "${currentView}". ` +
      `Expected "grid" or "list". Defaulting to "grid". ` +
      `This may indicate a data validation issue.`
    )
  }

  /**
   * Handle view mode change
   * @param {('grid'|'list')} mode - The target view mode
   */
  const handleViewChange = (mode) => {
    // Don't change if already in this mode
    if (mode === normalizedView) {
      return
    }

    onViewChange(mode)
  }

  /**
   * Common button classes
   */
  const baseButtonClasses =
    'px-3 py-2 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed'

  /**
   * Active button styling
   */
  const activeClasses = 'bg-white shadow text-gray-900 font-medium'

  /**
   * Inactive button styling
   */
  const inactiveClasses = 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'

  return (
    <>
      <div
        role="group"
        aria-label="View mode toggle"
        className="flex gap-2 p-1 bg-gray-100 rounded-lg"
      >
        {/* Grid View Button */}
        <button
          type="button"
          aria-label="Grid view"
          aria-pressed={normalizedView === 'grid'}
          disabled={isLoading}
          onClick={() => handleViewChange('grid')}
          className={`${baseButtonClasses} ${normalizedView === 'grid' ? activeClasses : inactiveClasses}`}
        >
          {/* Grid Icon (3x3 grid) */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="w-5 h-5"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
            />
          </svg>
        </button>

        {/* List View Button */}
        <button
          type="button"
          aria-label="List view"
          aria-pressed={normalizedView === 'list'}
          disabled={isLoading}
          onClick={() => handleViewChange('list')}
          className={`${baseButtonClasses} ${normalizedView === 'list' ? activeClasses : inactiveClasses}`}
        >
          {/* List Icon (horizontal bars) */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="w-5 h-5"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z"
            />
          </svg>
        </button>
      </div>

      {/* Screen reader announcement for loading state */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {isLoading && 'Saving view preference...'}
      </div>
    </>
  )
}
