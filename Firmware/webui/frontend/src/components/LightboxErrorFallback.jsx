import { createPortal } from 'react-dom'
import { Z_INDEX } from '../constants/config'

/**
 * Error fallback component for PhotoLightbox errors.
 *
 * Displays a fullscreen error modal that matches the lightbox design,
 * allowing users to dismiss and try again without breaking the page layout.
 *
 * @component
 * @param {Object} props - Component props
 * @param {Error} props.error - The error that was caught
 * @param {Function} props.onClose - Callback to close the error modal
 * @param {Function} props.onRetry - Optional callback to retry the failed operation
 *
 * @example
 * <LightboxErrorFallback
 *   error={new Error('Failed to load image')}
 *   onClose={() => setSelectedPhoto(null)}
 *   onRetry={() => window.location.reload()}
 * />
 */
function LightboxErrorFallback({ error, onClose, onRetry }) {
  return createPortal(
    <div
      className={`fixed inset-0 bg-black/90 ${Z_INDEX.MODAL} flex items-center justify-center`}
      role="alertdialog"
      aria-labelledby="lightbox-error-title"
      aria-describedby="lightbox-error-description"
    >
      <div className="max-w-md w-full bg-white rounded-lg shadow-2xl p-8 mx-4">
        {/* Error Icon */}
        <div className="flex items-center justify-center w-16 h-16 mx-auto bg-red-100 rounded-full">
          <svg
            className="w-8 h-8 text-red-600"
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
        <h2
          id="lightbox-error-title"
          className="mt-6 text-center text-2xl font-bold text-gray-900"
        >
          Lightbox Error
        </h2>

        {/* Description */}
        <p id="lightbox-error-description" className="mt-3 text-center text-sm text-gray-600">
          {error?.message || 'An error occurred while displaying the photo.'}
        </p>

        {/* Technical details (collapsed by default, only in development) */}
        {import.meta.env.DEV && error?.stack && (
          <details className="mt-4 text-xs">
            <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
              Show technical details
            </summary>
            <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto max-h-32">
              {error.stack}
            </pre>
          </details>
        )}

        {/* Action Buttons */}
        <div className="mt-8 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 bg-gray-200 text-gray-900 px-4 py-3 rounded-lg font-medium hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 transition-colors"
          >
            Close
          </button>
          {onRetry && (
            <button
              onClick={() => {
                onClose()
                onRetry()
              }}
              className="flex-1 bg-blue-600 text-white px-4 py-3 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body
  )
}

export default LightboxErrorFallback
