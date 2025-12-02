import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPhotoSidecarMetadata, updatePhotoSidecarMetadata } from '../utils/api'

/**
 * Custom hook for fetching and mutating photo sidecar metadata
 *
 * Provides sidecar metadata (tags, species, notes) for a given photo with
 * optimistic updates for instant UI feedback. Automatically invalidates
 * related queries on successful updates.
 *
 * @param {string|null|undefined} filename - Photo filename (e.g., "photo_2023-10-31_12-00-00.jpg")
 * @returns {object} Hook state and mutation functions
 * @returns {object} data - Sidecar metadata object with tags, species, notes
 * @returns {boolean} isLoading - Whether the query is currently loading
 * @returns {boolean} isError - Whether an error occurred during fetch
 * @returns {object} error - Error object if fetch failed
 * @returns {Function} updateTags - Update tags array
 * @returns {Function} addTag - Add a single tag (prevents duplicates)
 * @returns {Function} removeTag - Remove a single tag
 * @returns {Function} updateSpecies - Update species field
 * @returns {Function} updateNotes - Update notes field
 * @returns {boolean} isUpdating - Whether a mutation is in progress
 * @returns {object} updateError - Error object if mutation failed
 *
 * @example
 * const {
 *   data,
 *   isLoading,
 *   updateTags,
 *   addTag,
 *   removeTag,
 *   updateSpecies,
 *   updateNotes,
 *   isUpdating
 * } = useSidecarMetadata('photo_2023-10-31_12-00-00.jpg')
 *
 * if (isLoading) return <div>Loading...</div>
 * if (data) {
 *   return (
 *     <div>
 *       <p>Tags: {data.tags.join(', ')}</p>
 *       <button onClick={() => addTag('new_tag')}>Add Tag</button>
 *       <button onClick={() => updateSpecies('Luna Moth')}>Set Species</button>
 *     </div>
 *   )
 * }
 */
export default function useSidecarMetadata(filename) {
  const queryClient = useQueryClient()

  /**
   * Query for fetching sidecar metadata
   */
  const query = useQuery({
    queryKey: ['sidecarMetadata', filename],
    queryFn: async () => {
      const response = await getPhotoSidecarMetadata(filename)
      return response.data
    },
    enabled: !!filename,
    staleTime: 5 * 60 * 1000, // 5 minutes
    // Retry transient failures (network issues, temporary server errors)
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })

  /**
   * Mutation for updating sidecar metadata with optimistic updates
   */
  const updateMutation = useMutation({
    mutationFn: (updates) => updatePhotoSidecarMetadata(filename, updates),
    onMutate: async (updates) => {
      // Cancel outgoing refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: ['sidecarMetadata', filename] })

      // Snapshot previous value for rollback
      const previousData = queryClient.getQueryData(['sidecarMetadata', filename])

      // Optimistically update the cache immediately
      queryClient.setQueryData(['sidecarMetadata', filename], (old) => ({
        ...old,
        ...updates,
      }))

      // Return context for rollback
      return { previousData }
    },
    onError: (err, updates, context) => {
      // Rollback to previous value on error
      if (context?.previousData) {
        queryClient.setQueryData(['sidecarMetadata', filename], context.previousData)
      }
    },
    onSettled: () => {
      // Invalidate related queries to ensure sync with server
      // Note: This runs on both success and error. After error, the optimistic
      // update is already rolled back in onError, but we still refetch to
      // confirm cache matches server state. This is intentional TanStack Query pattern.
      queryClient.invalidateQueries({ queryKey: ['sidecarMetadata', filename] })
      queryClient.invalidateQueries({ queryKey: ['tags'] })
    },
  })

  /**
   * Update tags array
   *
   * @param {string[]} tags - New tags array
   */
  const updateTags = (tags) => {
    updateMutation.mutate({ tags })
  }

  /**
   * Add a single tag to existing tags
   * Prevents duplicate tags
   *
   * @param {string} tag - Tag to add
   */
  const addTag = (tag) => {
    const currentTags = query.data?.tags || []
    if (!currentTags.includes(tag)) {
      updateMutation.mutate({ tags: [...currentTags, tag] })
    }
  }

  /**
   * Remove a single tag from existing tags
   *
   * @param {string} tag - Tag to remove
   */
  const removeTag = (tag) => {
    const currentTags = query.data?.tags || []
    updateMutation.mutate({ tags: currentTags.filter((t) => t !== tag) })
  }

  /**
   * Update species field
   *
   * @param {string} species - Species name
   */
  const updateSpecies = (species) => {
    updateMutation.mutate({ species })
  }

  /**
   * Update notes field
   *
   * @param {string} notes - Notes text
   */
  const updateNotes = (notes) => {
    updateMutation.mutate({ notes })
  }

  return {
    // Query state
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    isSuccess: query.isSuccess,
    error: query.error,

    // Mutation functions
    updateTags,
    addTag,
    removeTag,
    updateSpecies,
    updateNotes,

    // Mutation state
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error,
  }
}
