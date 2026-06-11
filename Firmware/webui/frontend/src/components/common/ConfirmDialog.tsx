import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { Z_INDEX } from '../../constants/config'

export interface ConfirmDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean
  /** Close handler (Cancel button or backdrop click) */
  onClose: () => void
  /** Confirm handler (Confirm button click) */
  onConfirm: () => void
  /** Dialog title */
  title: string
  /** Dialog message/description */
  message: string
  /** Confirm button label */
  confirmLabel?: string
  /** Cancel button label */
  cancelLabel?: string
  /** Visual variant: 'default', 'warning', or 'danger' */
  variant?: 'default' | 'warning' | 'danger'
  /** Loading state - disables buttons */
  isLoading?: boolean
}

/**
 * ConfirmDialog Component
 *
 * A reusable confirmation dialog that follows proper React/UX patterns.
 * Replaces window.confirm for better UX and testability.
 *
 * @component
 * @example
 * // Basic usage
 * <ConfirmDialog
 *   isOpen={showConfirm}
 *   onClose={() => setShowConfirm(false)}
 *   onConfirm={() => handleAction()}
 *   title="Discard changes?"
 *   message="You have unsaved changes. Are you sure you want to discard them?"
 * />
 *
 * @example
 * // Danger variant
 * <ConfirmDialog
 *   isOpen={showDelete}
 *   onClose={() => setShowDelete(false)}
 *   onConfirm={() => handleDelete()}
 *   title="Delete item?"
 *   message="This action cannot be undone."
 *   confirmLabel="Delete"
 *   variant="danger"
 * />
 */
export default function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  isLoading = false
}: ConfirmDialogProps) {
  const confirmButtonRef = useRef<HTMLButtonElement>(null)

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, isLoading, onClose])

  // Focus confirm button on open for keyboard accessibility
  useEffect(() => {
    if (isOpen && confirmButtonRef.current) {
      confirmButtonRef.current.focus()
    }
  }, [isOpen])

  if (!isOpen) return null

  // Variant-specific styling
  const variantStyles = {
    danger: {
      icon: 'text-red-600 dark:text-red-500',
      confirmButton: 'bg-red-600 hover:bg-red-700 text-white',
      title: 'text-gray-900 dark:text-gray-100'
    },
    warning: {
      icon: 'text-amber-600 dark:text-amber-500',
      confirmButton: 'bg-amber-600 hover:bg-amber-700 text-white',
      title: 'text-gray-900 dark:text-gray-100'
    },
    default: {
      icon: 'text-blue-600 dark:text-blue-500',
      confirmButton: 'bg-blue-600 hover:bg-blue-700 text-white',
      title: 'text-gray-900 dark:text-gray-100'
    }
  }

  const styles = variantStyles[variant] || variantStyles.default
  const showIcon = variant === 'danger' || variant === 'warning'
  const dialogRole = variant === 'danger' ? 'alertdialog' : 'dialog'

  const handleBackdropClick = () => {
    if (!isLoading) {
      onClose()
    }
  }

  const handleConfirm = () => {
    onConfirm()
  }

  const modal = (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center`}>
      {/* Backdrop with click-to-close */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleBackdropClick}
        data-testid="confirm-dialog-backdrop"
      />

      {/* Modal content */}
      <div
        role={dialogRole}
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        data-testid="confirm-dialog"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-md p-6 mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Icon and title */}
        <div className="flex items-start gap-3 mb-4">
          {showIcon && (
            <ExclamationTriangleIcon
              className={`h-6 w-6 flex-shrink-0 mt-0.5 ${styles.icon}`}
              aria-hidden="true"
            />
          )}
          <div className="flex-1">
            <h2
              id="confirm-dialog-title"
              className={`text-lg font-semibold ${styles.title}`}
            >
              {title}
            </h2>
          </div>
        </div>

        {/* Message */}
        <p
          id="confirm-dialog-message"
          className="text-sm text-gray-600 dark:text-gray-400 mb-6"
        >
          {message}
        </p>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            data-testid="confirm-dialog-cancel"
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                       hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            onClick={handleConfirm}
            disabled={isLoading}
            data-testid="confirm-dialog-confirm"
            className={`flex-1 px-4 py-2 rounded-md font-medium
                       disabled:opacity-50 disabled:cursor-not-allowed ${styles.confirmButton}`}
          >
            {isLoading ? 'Loading...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
