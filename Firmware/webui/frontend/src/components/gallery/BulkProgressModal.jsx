import { createPortal } from 'react-dom'
import { XMarkIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { Z_INDEX } from '../../constants/config'

/**
 * BulkProgressModal - Displays progress during bulk operations (tag, species, delete, export)
 *
 * This modal supports two prop interfaces to accommodate different use cases:
 *
 * ## Simplified Interface
 * Use for straightforward progress tracking with custom messages.
 * The modal auto-calculates progress percentage from current/total.
 *
 * Required props: `isOpen`, `onClose`, `status`, `current`, `total`
 * Optional props: `message`, `downloadUrl`, `onCancel`
 *
 * @example
 * // Simplified interface - export with download
 * <BulkProgressModal
 *   isOpen={true}
 *   onClose={() => setOpen(false)}
 *   status="processing"
 *   current={5}
 *   total={10}
 *   message="Exporting photos..."
 *   downloadUrl="/api/export/download/123"  // Shows download button on success
 * />
 *
 * ## Detailed Interface
 * Use for complex operations with batch processing, error tracking, and granular counts.
 * Provides explicit control over all display values.
 *
 * Required props: `isOpen`, `onClose`, `status`, `progress`, `processedCount`, `totalCount`
 * Optional props: `successCount`, `failedCount`, `errors`, `operation`, `currentBatch`, `totalBatches`, `onCancel`
 *
 * @example
 * // Detailed interface - bulk tagging with error tracking
 * <BulkProgressModal
 *   isOpen={true}
 *   onClose={() => setOpen(false)}
 *   status="processing"
 *   operation="tag"
 *   progress={50}
 *   processedCount={5}
 *   totalCount={10}
 *   successCount={4}
 *   failedCount={1}
 *   currentBatch={1}
 *   totalBatches={2}
 *   errors={{ 'photo1.jpg': 'File not found' }}
 * />
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether modal is visible
 * @param {Function} props.onClose - Callback when modal closes (after completion)
 * @param {Function} [props.onCancel] - Callback when user cancels operation
 * @param {'processing'|'success'|'error'} props.status - Current operation status
 *
 * @param {number} [props.current] - Current count (simplified interface, triggers simplified mode)
 * @param {number} [props.total] - Total count (simplified interface, required with current)
 * @param {string} [props.message] - Custom status message (simplified interface)
 * @param {string} [props.downloadUrl] - Download URL for completed export (simplified interface)
 *
 * @param {number} [props.progress] - Progress percentage 0-100 (detailed interface)
 * @param {number} [props.processedCount] - Photos processed so far (detailed interface)
 * @param {number} [props.totalCount] - Total photos to process (detailed interface)
 * @param {number} [props.successCount] - Successfully processed photos (detailed interface)
 * @param {number} [props.failedCount] - Failed photos (detailed interface)
 * @param {Object} [props.errors] - Map of filename -> error message (detailed interface)
 * @param {'tag'|'species'|'delete'|'export'} [props.operation='tag'] - Operation type (detailed interface)
 * @param {number} [props.currentBatch] - Current batch number (detailed interface)
 * @param {number} [props.totalBatches] - Total batches (detailed interface)
 */
export default function BulkProgressModal({
  isOpen,
  onClose,
  onCancel,
  status,
  progress,
  current,
  total,
  message,
  currentBatch,
  totalBatches,
  processedCount,
  totalCount,
  successCount,
  failedCount,
  errors,
  operation = 'tag',
  downloadUrl
}) {
  if (!isOpen) return null

  // Support both simplified and detailed interfaces
  const useSimplified = current !== undefined && total !== undefined
  const displayProcessed = useSimplified ? current : processedCount
  const displayTotal = useSimplified ? total : totalCount
  const displayProgress = useSimplified
    ? (total > 0 ? Math.round((current / total) * 100) : 0)
    : progress
  const displaySuccess = useSimplified ? current : successCount
  const displayFailed = useSimplified ? 0 : failedCount

  const operationText = {
    tag: 'Tagging',
    species: 'Updating species',
    delete: 'Deleting',
    export: 'Exporting'
  }[operation]

  const handleCancelClick = () => {
    if (onCancel) {
      onCancel()
    }
  }

  const modal = (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center`}>
      {/* Backdrop - non-interactive during processing */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Modal content */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`${operationText} progress`}
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6"
      >
        {status === 'processing' && (
          <>
            <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
              {useSimplified && message ? message : `${operationText} photos...`}
            </h2>

            {/* Progress bar */}
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-4">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all"
                style={{ width: `${displayProgress}%` }}
                role="progressbar"
                aria-valuenow={displayProgress}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>

            {!useSimplified && (
              <p
                role="status"
                aria-live="polite"
                aria-atomic="true"
                className="text-sm text-gray-600 dark:text-gray-400 mb-4"
              >
                Processing {displayProcessed} of {displayTotal} photos
                {totalBatches > 1 && ` (Batch ${currentBatch} of ${totalBatches})`}
              </p>
            )}

            <button
              onClick={handleCancelClick}
              className="w-full px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="flex items-center gap-3 mb-4">
              <CheckCircleIcon className="h-8 w-8 text-green-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {useSimplified && message ? message : 'Complete!'}
              </h2>
            </div>

            {!useSimplified && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Successfully processed {displaySuccess} photos
                {displayFailed > 0 && `, ${displayFailed} failed`}
              </p>
            )}

            {downloadUrl ? (
              <div className="flex gap-2">
                <a
                  href={downloadUrl}
                  download
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-center"
                >
                  Download
                </a>
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  Close
                </button>
              </div>
            ) : (
              <button
                onClick={onClose}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Done
              </button>
            )}
          </>
        )}

        {status === 'error' && (
          <>
            <div className="flex items-center gap-3 mb-4">
              <ExclamationCircleIcon className="h-8 w-8 text-red-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Error
              </h2>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {useSimplified && message ? message : `${displayFailed} photos failed to process`}
            </p>

            {!useSimplified && errors && Object.keys(errors).length > 0 && (
              <div className="max-h-32 overflow-y-auto mb-4 text-sm">
                {Object.entries(errors).slice(0, 5).map(([file, error]) => (
                  <p key={file} className="text-red-600 dark:text-red-400 mb-1">
                    {file}: {error}
                  </p>
                ))}
                {Object.keys(errors).length > 5 && (
                  <p className="text-gray-500 dark:text-gray-400">
                    ...and {Object.keys(errors).length - 5} more
                  </p>
                )}
              </div>
            )}

            <button
              onClick={onClose}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Close
            </button>
          </>
        )}
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
