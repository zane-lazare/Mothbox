import PropTypes from 'prop-types'
import { XMarkIcon } from '@heroicons/react/24/outline'
import { useEffect, useRef } from 'react'

/**
 * SearchHelp component - Shows search syntax help
 *
 * @param {Object} props
 * @param {function} props.onClose - Callback when help is closed
 */
export function SearchHelp({ onClose }) {
  const dialogRef = useRef(null)

  // Handle escape key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  // Focus trap
  useEffect(() => {
    const firstFocusable = dialogRef.current?.querySelector('button')
    firstFocusable?.focus()
  }, [])

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-label="Search help"
      className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600
                 rounded-lg shadow-xl p-4 w-80"
    >
      {/* Header */}
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Search Syntax
        </h3>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close help"
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <XMarkIcon className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      {/* Syntax examples */}
      <dl className="space-y-3 text-sm">
        <div>
          <dt className="font-mono text-blue-600 dark:text-blue-400">tag:moth</dt>
          <dd className="text-gray-600 dark:text-gray-400 ml-4">Search by tag</dd>
        </div>

        <div>
          <dt className="font-mono text-blue-600 dark:text-blue-400">species:actias</dt>
          <dd className="text-gray-600 dark:text-gray-400 ml-4">Search by species</dd>
        </div>

        <div>
          <dt className="font-mono text-blue-600 dark:text-blue-400">&quot;luna moth&quot;</dt>
          <dd className="text-gray-600 dark:text-gray-400 ml-4">Exact phrase</dd>
        </div>

        <div>
          <dt className="font-mono text-blue-600 dark:text-blue-400">luna*</dt>
          <dd className="text-gray-600 dark:text-gray-400 ml-4">Prefix match</dd>
        </div>

        <div>
          <dt className="font-mono text-blue-600 dark:text-blue-400">moth AND luna</dt>
          <dd className="text-gray-600 dark:text-gray-400 ml-4">Both terms required</dd>
        </div>

        <div>
          <dt className="font-mono text-blue-600 dark:text-blue-400">moth OR butterfly</dt>
          <dd className="text-gray-600 dark:text-gray-400 ml-4">Either term</dd>
        </div>

        <div>
          <dt className="font-mono text-blue-600 dark:text-blue-400">moth -butterfly</dt>
          <dd className="text-gray-600 dark:text-gray-400 ml-4">Exclude term</dd>
        </div>

        <div>
          <dt className="font-mono text-blue-600 dark:text-blue-400">date:2024-11-01..2024-11-06</dt>
          <dd className="text-gray-600 dark:text-gray-400 ml-4">Date range</dd>
        </div>
      </dl>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={onClose}
          className="w-full px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Close
        </button>
      </div>
    </div>
  )
}

SearchHelp.propTypes = {
  onClose: PropTypes.func.isRequired,
}
