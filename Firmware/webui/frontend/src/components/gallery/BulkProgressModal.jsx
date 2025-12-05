import { createPortal } from 'react-dom'
import { XMarkIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'

/**
 * BulkProgressModal - Displays progress during bulk operations (tag, species, delete)
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether modal is visible
 * @param {Function} props.onClose - Callback when modal closes (after completion)
 * @param {Function} [props.onCancel] - Callback when user cancels operation
 * @param {'processing'|'success'|'error'} props.status - Current operation status
 * @param {number} props.progress - Progress percentage (0-100)
 * @param {number} [props.currentBatch] - Current batch number (for multi-batch operations)
 * @param {number} [props.totalBatches] - Total number of batches
 * @param {number} props.processedCount - Number of photos processed so far
 * @param {number} props.totalCount - Total number of photos to process
 * @param {number} [props.successCount] - Number of successfully processed photos (for completion)
 * @param {number} [props.failedCount] - Number of failed photos (for completion)
 * @param {Object} [props.errors] - Map of filename -> error message
 * @param {'tag'|'species'|'delete'} [props.operation='tag'] - Type of operation
 */
export default function BulkProgressModal({
  isOpen,
  onClose,
  onCancel,
  status,
  progress,
  currentBatch,
  totalBatches,
  processedCount,
  totalCount,
  successCount,
  failedCount,
  errors,
  operation = 'tag'
}) {
  if (!isOpen) return null

  const operationText = {
    tag: 'Tagging',
    species: 'Updating species',
    delete: 'Deleting'
  }[operation]

  const handleCancelClick = () => {
    if (onCancel) {
      onCancel()
    }
  }

  const modal = (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
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
              {operationText} photos...
            </h2>

            {/* Progress bar */}
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-4">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all"
                style={{ width: `${progress}%` }}
                role="progressbar"
                aria-valuenow={progress}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Processing {processedCount} of {totalCount} photos
              {totalBatches > 1 && ` (Batch ${currentBatch} of ${totalBatches})`}
            </p>

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
                Complete!
              </h2>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Successfully processed {successCount} photos
              {failedCount > 0 && `, ${failedCount} failed`}
            </p>

            <button
              onClick={onClose}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Done
            </button>
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
              {failedCount} photos failed to process
            </p>

            {errors && Object.keys(errors).length > 0 && (
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
