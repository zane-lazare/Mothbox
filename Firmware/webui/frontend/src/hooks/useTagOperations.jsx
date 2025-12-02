import { useCallback, useRef, useEffect } from 'react'
import toast from 'react-hot-toast'
import useSidecarMetadata from './useSidecarMetadata'
import { TOAST_CONFIG } from '../constants/config'

/**
 * Custom hook for tag operations with toast notifications
 *
 * Wraps useSidecarMetadata to provide tag add/remove operations with user feedback
 * via toast notifications. Includes error handling with undo functionality.
 *
 * Toast behavior:
 * - Success: 3 seconds (add/remove successful)
 * - Error: 5 seconds with undo button
 *
 * @param {string|null|undefined} filename - Photo filename
 * @returns {object} Hook state and mutation functions with toast notifications
 * @returns {object} data - Sidecar metadata object with tags, species, notes
 * @returns {boolean} isLoading - Whether the query is currently loading
 * @returns {boolean} isError - Whether an error occurred during fetch
 * @returns {object} error - Error object if fetch failed
 * @returns {Function} addTag - Add a single tag with success/error toast
 * @returns {Function} removeTag - Remove a single tag with success/error toast
 * @returns {Function} updateTags - Update tags array (no toast)
 * @returns {Function} updateSpecies - Update species field (no toast)
 * @returns {Function} updateNotes - Update notes field (no toast)
 * @returns {boolean} isUpdating - Whether a mutation is in progress
 * @returns {object} updateError - Error object if mutation failed
 *
 * @example
 * const { data, addTag, removeTag, isUpdating } = useTagOperations('photo.jpg')
 *
 * // Add tag with success toast
 * addTag('butterfly')
 *
 * // Remove tag with success toast
 * removeTag('moth')
 *
 * // On error, toast will show with undo button to revert
 */
export default function useTagOperations(filename) {
  const sidecar = useSidecarMetadata(filename)

  // Track previous state for undo functionality
  const previousTagsRef = useRef(null)

  // Track last operation for error handling
  const lastOperationRef = useRef({ type: null, tag: null })

  /**
   * Add a tag with toast notification
   * Shows success toast on add, error toast with undo on failure
   *
   * @param {string} tag - Tag to add
   */
  const addTag = useCallback(
    (tag) => {
      const currentTags = sidecar.data?.tags || []

      // Check for duplicate tag
      if (currentTags.includes(tag)) {
        toast('Tag already exists', {
          duration: TOAST_CONFIG.SUCCESS_DURATION,
          icon: 'ℹ️',
        })
        return
      }

      // Store previous state for potential undo
      previousTagsRef.current = [...currentTags]

      // Track operation for error handling
      lastOperationRef.current = { type: 'add', tag }

      // Perform the mutation (optimistic update happens in useSidecarMetadata)
      sidecar.addTag(tag)

      // Show success toast
      toast.success(`Added tag "${tag}"`, {
        duration: TOAST_CONFIG.SUCCESS_DURATION,
      })
    },
    [sidecar]
  )

  /**
   * Remove a tag with toast notification
   * Shows success toast on remove, error toast with undo on failure
   *
   * @param {string} tag - Tag to remove
   */
  const removeTag = useCallback(
    (tag) => {
      const currentTags = sidecar.data?.tags || []

      // Check if tag exists
      if (!currentTags.includes(tag)) {
        toast('Tag not found', {
          duration: TOAST_CONFIG.SUCCESS_DURATION,
          icon: 'ℹ️',
        })
        return
      }

      // Store previous state for potential undo
      previousTagsRef.current = [...currentTags]

      // Track operation for error handling
      lastOperationRef.current = { type: 'remove', tag }

      // Perform the mutation (optimistic update happens in useSidecarMetadata)
      sidecar.removeTag(tag)

      // Show success toast
      toast.success(`Removed tag "${tag}"`, {
        duration: TOAST_CONFIG.SUCCESS_DURATION,
      })
    },
    [sidecar]
  )

  /**
   * Show error toast with undo button using custom render
   * Note: react-hot-toast doesn't have built-in action buttons,
   * so we use custom content with a button
   */
  const showErrorWithUndo = useCallback(
    (operation, tag) => {
      const undoTags = previousTagsRef.current

      if (undoTags) {
        toast.error(
          (t) => (
            <div className="flex items-center gap-3">
              <span>Failed to {operation} tag &quot;{tag}&quot;</span>
              <button
                onClick={() => {
                  toast.dismiss(t.id)
                  sidecar.updateTags(undoTags)
                  toast.success('Changes undone', { duration: TOAST_CONFIG.SUCCESS_DURATION })
                }}
                className="px-2 py-1 text-xs font-medium text-white bg-white/20 hover:bg-white/30 rounded transition-colors"
              >
                Undo
              </button>
            </div>
          ),
          {
            duration: 5000,
          }
        )
      } else {
        toast.error(`Failed to ${operation} tag "${tag}"`, {
          duration: TOAST_CONFIG.ERROR_DURATION,
        })
      }
    },
    // Note: previousTagsRef is intentionally not in deps - refs are stable and
    // accessing .current always gets the latest value without causing stale closures
    [sidecar]
  )

  // Monitor for mutation errors and show error toast
  // Note: The rollback already happens in useSidecarMetadata's onError
  // We just need to notify the user with the option to manually undo
  const prevUpdateError = useRef(null)

  useEffect(() => {
    if (sidecar.updateError && sidecar.updateError !== prevUpdateError.current) {
      prevUpdateError.current = sidecar.updateError
      const { type, tag } = lastOperationRef.current
      if (type && tag) {
        showErrorWithUndo(type, tag)
      } else {
        toast.error('Failed to update tags', {
          duration: TOAST_CONFIG.ERROR_DURATION,
        })
      }
    }
  }, [sidecar.updateError, showErrorWithUndo])

  return {
    // Query state
    data: sidecar.data,
    isLoading: sidecar.isLoading,
    isError: sidecar.isError,
    isSuccess: sidecar.isSuccess,
    error: sidecar.error,

    // Mutation functions with toast notifications
    addTag,
    removeTag,

    // Pass through other mutation functions (no toast)
    updateTags: sidecar.updateTags,
    updateSpecies: sidecar.updateSpecies,
    updateNotes: sidecar.updateNotes,

    // Mutation state
    isUpdating: sidecar.isUpdating,
    updateError: sidecar.updateError,
  }
}
