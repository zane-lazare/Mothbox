import { useCallback, useRef, useEffect } from 'react'
import toast from 'react-hot-toast'
import useSidecarMetadata, { SidecarMetadata, UseSidecarMetadataResult } from './useSidecarMetadata'
import { TOAST_CONFIG } from '../constants/config'

/**
 * Operation type for tracking last tag operation
 */
interface TagOperation {
  type: 'add' | 'remove' | null
  tag: string | null
}

/**
 * Return type for useTagOperations hook
 */
export interface UseTagOperationsResult {
  // Query state
  data: SidecarMetadata | undefined
  isLoading: boolean
  isError: boolean
  isSuccess: boolean
  error: Error | null

  // Mutation functions with toast notifications
  addTag: (tag: string) => void
  removeTag: (tag: string) => void

  // Pass through other mutation functions (no toast)
  updateTags: (tags: string[]) => void
  updateSpecies: (species: string) => void
  updateNotes: (notes: string) => void

  // Mutation state
  isUpdating: boolean
  updateError: Error | null
}

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
 * @param filename - Photo filename
 * @returns Hook state and mutation functions with toast notifications
 * @returns data - Sidecar metadata object with tags, species, notes
 * @returns isLoading - Whether the query is currently loading
 * @returns isError - Whether an error occurred during fetch
 * @returns error - Error object if fetch failed
 * @returns addTag - Add a single tag with success/error toast
 * @returns removeTag - Remove a single tag with success/error toast
 * @returns updateTags - Update tags array (no toast)
 * @returns updateSpecies - Update species field (no toast)
 * @returns updateNotes - Update notes field (no toast)
 * @returns isUpdating - Whether a mutation is in progress
 * @returns updateError - Error object if mutation failed
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
export default function useTagOperations(filename: string | null | undefined): UseTagOperationsResult {
  const sidecar: UseSidecarMetadataResult = useSidecarMetadata(filename)

  // Track previous state for undo functionality
  const previousTagsRef = useRef<string[] | null>(null)

  // Track last operation for error handling
  const lastOperationRef = useRef<TagOperation>({ type: null, tag: null })

  /**
   * Add a tag with toast notification
   * Shows success toast on add, error toast with undo on failure
   *
   * @param tag - Tag to add
   */
  const addTag = useCallback(
    (tag: string) => {
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
   * @param tag - Tag to remove
   */
  const removeTag = useCallback(
    (tag: string) => {
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
    (operation: 'add' | 'remove', tag: string) => {
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
            duration: TOAST_CONFIG.ERROR_DURATION,
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
  // Track previous error reference to detect new errors vs same error persisting
  const prevErrorRef = useRef<Error | null>(null)

  useEffect(() => {
    // Only show toast if this is a new error (not the same reference)
    if (sidecar.updateError && sidecar.updateError !== prevErrorRef.current) {
      prevErrorRef.current = sidecar.updateError
      const { type, tag } = lastOperationRef.current
      if (type && tag) {
        showErrorWithUndo(type, tag)
      } else {
        toast.error('Failed to update tags', {
          duration: TOAST_CONFIG.ERROR_DURATION,
        })
      }
    }
    // Clear the ref when error is resolved
    if (!sidecar.updateError) {
      prevErrorRef.current = null
    }
    // Include isUpdating to trigger on each mutation cycle, catching consecutive
    // failures even if the error object reference is the same
  }, [sidecar.updateError, sidecar.isUpdating, showErrorWithUndo])

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
