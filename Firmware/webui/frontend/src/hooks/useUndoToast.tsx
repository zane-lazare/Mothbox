import { useCallback } from 'react'
import toast from 'react-hot-toast'

const UNDO_TIMEOUT = 5000 // 5 seconds

/**
 * Return type for the useUndoToast hook
 */
interface UseUndoToastReturn {
  showUndoToast: (message: string, onUndo: () => void) => string
  dismissToast: (toastId: string) => void
}

/**
 * Custom hook for displaying success toasts with an Undo button
 *
 * Provides a simple interface for showing toast notifications with undo functionality.
 * The toast automatically dismisses after 5 seconds, but users can click the Undo button
 * to execute a callback and dismiss the toast immediately.
 *
 * Toast behavior:
 * - Duration: 5 seconds (auto-dismiss)
 * - Position: bottom-center (less intrusive than top-right)
 * - Action: Undo button executes callback and dismisses toast immediately
 *
 * @returns {UseUndoToastReturn} Hook functions
 * @returns {Function} showUndoToast - Show toast with undo button
 * @returns {Function} dismissToast - Dismiss specific toast by ID
 *
 * @example
 * const { showUndoToast, dismissToast } = useUndoToast()
 *
 * // Show toast with undo callback
 * const toastId = showUndoToast('Tag deleted', () => {
 *   console.log('Undo clicked!')
 *   // Restore the deleted tag
 * })
 *
 * // Optionally dismiss programmatically
 * dismissToast(toastId)
 */

export default function useUndoToast(): UseUndoToastReturn {
  /**
   * Show a toast notification with an Undo button
   *
   * @param {string} message - Message to display in the toast
   * @param {Function} onUndo - Callback function to execute when Undo is clicked
   * @returns {string} Toast ID for programmatic dismissal
   */
  const showUndoToast = useCallback((message: string, onUndo: () => void): string => {
    const toastId = toast(
      (t) => (
        <div className="flex items-center gap-3">
          <span>{message}</span>
          <button
            onClick={() => {
              onUndo()
              toast.dismiss(t.id)
            }}
            className="px-2 py-1 text-sm font-medium text-blue-600
                       hover:text-blue-800 rounded"
          >
            Undo
          </button>
        </div>
      ),
      {
        duration: UNDO_TIMEOUT,
        position: 'bottom-center',
      }
    )

    return toastId
  }, [])

  /**
   * Dismiss a specific toast by ID
   *
   * @param {string} toastId - ID of the toast to dismiss
   */
  const dismissToast = useCallback((toastId: string): void => {
    toast.dismiss(toastId)
  }, [])

  return {
    showUndoToast,
    dismissToast,
  }
}
