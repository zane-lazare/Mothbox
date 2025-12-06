import { CheckCircleIcon, XMarkIcon } from '@heroicons/react/24/outline'
import useSelection from '../../hooks/useSelection'

/**
 * SelectModeToggle Component
 *
 * Toggle button for entering/exiting photo selection mode in the gallery.
 * Provides accessible UI with keyboard navigation and screen reader support.
 *
 * @returns {JSX.Element} The selection mode toggle button
 */
export default function SelectModeToggle() {
  const { isSelectMode, toggleSelectMode } = useSelection()

  /**
   * Common button classes matching ViewModeToggle pattern
   */
  const baseButtonClasses =
    'flex items-center gap-2 px-3 py-2 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500'

  /**
   * Active button styling (when in select mode)
   */
  const activeClasses = 'bg-blue-600 hover:bg-blue-700 text-white font-medium shadow'

  /**
   * Inactive button styling (when not in select mode)
   */
  const inactiveClasses = 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-300'

  return (
    <button
      type="button"
      onClick={toggleSelectMode}
      aria-pressed={isSelectMode}
      aria-label={isSelectMode ? 'Exit selection mode' : 'Enter selection mode'}
      className={`${baseButtonClasses} ${isSelectMode ? activeClasses : inactiveClasses}`}
    >
      {isSelectMode ? (
        <>
          <XMarkIcon className="h-5 w-5" aria-hidden="true" />
          <span>Cancel</span>
        </>
      ) : (
        <>
          <CheckCircleIcon className="h-5 w-5" aria-hidden="true" />
          <span>Select</span>
        </>
      )}
    </button>
  )
}
