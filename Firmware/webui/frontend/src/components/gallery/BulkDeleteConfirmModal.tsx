import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { Z_INDEX } from '../../constants/config'

export interface BulkDeleteConfirmModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Close handler */
  onClose: () => void
  /** Confirm deletion handler */
  onConfirm: () => void
  /** Array of photo filenames to delete */
  selectedPhotos: string[]
  /** Loading state during deletion */
  isLoading?: boolean
}

/**
 * BulkDeleteConfirmModal Component
 *
 * Confirmation modal for bulk delete operations with destructive styling.
 * Shows file preview and irreversibility warning.
 */
export default function BulkDeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  selectedPhotos,
  isLoading = false
}: BulkDeleteConfirmModalProps) {
  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const photoCount = selectedPhotos.length
  const photosToShow = selectedPhotos.slice(0, 5)
  const remainingCount = photoCount - photosToShow.length

  const modal = (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center`}>
      {/* Backdrop with click-to-close */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal content */}
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="bulk-delete-title"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Warning icon and title */}
        <div className="flex items-start gap-3 mb-4">
          <ExclamationTriangleIcon className="h-6 w-6 text-red-600 dark:text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2
              id="bulk-delete-title"
              className="text-lg font-semibold text-gray-900 dark:text-gray-100"
            >
              Delete {photoCount} photo{photoCount !== 1 ? 's' : ''}?
            </h2>
          </div>
        </div>

        {/* File preview */}
        <div className="mb-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
            Files to delete:
          </p>
          <ul className="bg-gray-50 dark:bg-gray-900 rounded-md p-3 max-h-40 overflow-y-auto">
            {photosToShow.map((photo, index) => (
              <li
                key={index}
                className="text-sm text-gray-700 dark:text-gray-300 truncate py-1"
                title={photo}
              >
                {photo}
              </li>
            ))}
            {remainingCount > 0 && (
              <li className="text-sm text-gray-500 dark:text-gray-400 italic py-1">
                ...and {remainingCount} more
              </li>
            )}
          </ul>
        </div>

        {/* Warning message */}
        <p className="text-sm text-red-600 dark:text-red-400 mb-6 font-medium">
          This action cannot be undone.
        </p>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                       hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            aria-label={isLoading ? 'Deleting photos' : 'Delete photos'}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md
                       hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed
                       font-medium"
          >
            {isLoading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
