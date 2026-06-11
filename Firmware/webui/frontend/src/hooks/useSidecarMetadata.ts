import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { getPhotoSidecarMetadata, updatePhotoSidecarMetadata } from '../utils/api'

export interface SidecarMetadata {
  tags: string[]
  species?: string
  notes?: string
  [key: string]: unknown
}

interface SidecarMetadataUpdate {
  tags?: string[]
  species?: string
  notes?: string
  [key: string]: unknown
}

export interface UseSidecarMetadataResult {
  data: SidecarMetadata | undefined
  isLoading: boolean
  isError: boolean
  isSuccess: boolean
  error: Error | null
  updateTags: (tags: string[]) => void
  addTag: (tag: string) => void
  removeTag: (tag: string) => void
  updateSpecies: (species: string) => void
  updateNotes: (notes: string) => void
  updateMetadata: (updates: SidecarMetadataUpdate) => Promise<unknown>
  isUpdating: boolean
  updateError: Error | null
}

/**
 * Custom hook for fetching and mutating photo sidecar metadata
 *
 * Provides sidecar metadata (tags, species, notes) for a given photo with
 * optimistic updates for instant UI feedback. Automatically invalidates
 * related queries on successful updates.
 *
 * @param filename - Photo filename (e.g., "photo_2023-10-31_12-00-00.jpg")
 * @returns Hook state and mutation functions
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
export default function useSidecarMetadata(filename: string | null | undefined): UseSidecarMetadataResult {
  const queryClient = useQueryClient()

  // Per-component ref for debouncing tags cache invalidation
  // Batches rapid tag operations into a single refetch after 1 second of inactivity
  const tagsInvalidationTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Cleanup pending tags invalidation timeout on unmount
  // Prevents memory leaks in fast navigation scenarios
  useEffect(() => {
    return () => {
      if (tagsInvalidationTimeoutRef.current) {
        clearTimeout(tagsInvalidationTimeoutRef.current)
        tagsInvalidationTimeoutRef.current = null
      }
    }
  }, [])

  /**
   * Query for fetching sidecar metadata
   */
  const query: UseQueryResult<SidecarMetadata, Error> = useQuery({
    queryKey: ['sidecarMetadata', filename],
    queryFn: async () => {
      const response = await getPhotoSidecarMetadata(filename!)
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
  const updateMutation: UseMutationResult<unknown, Error, SidecarMetadataUpdate, { previousData: unknown }> = useMutation({
    mutationFn: (updates: SidecarMetadataUpdate) => updatePhotoSidecarMetadata(filename!, updates),
    onMutate: async (updates) => {
      // Cancel outgoing refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: ['sidecarMetadata', filename] })

      // Snapshot previous value for rollback
      const previousData = queryClient.getQueryData(['sidecarMetadata', filename])

      // Optimistically update the cache immediately
      queryClient.setQueryData(['sidecarMetadata', filename], (old: SidecarMetadata | undefined) => ({
        ...old,
        ...updates,
      }))

      // Return context for rollback
      return { previousData }
    },
    onError: (_err, _updates, context) => {
      // Rollback to previous value on error
      if (context?.previousData) {
        queryClient.setQueryData(['sidecarMetadata', filename], context.previousData)
      }
    },
    onSettled: () => {
      // Invalidate sidecar metadata immediately to sync with server
      // Note: This runs on both success and error. After error, the optimistic
      // update is already rolled back in onError, but we still refetch to
      // confirm cache matches server state. This is intentional TanStack Query pattern.
      queryClient.invalidateQueries({ queryKey: ['sidecarMetadata', filename] })

      // Debounce tags invalidation - wait 1 second after last update
      // This batches rapid tag operations into a single tags refetch,
      // preventing excessive network requests when user rapidly tags photos
      if (tagsInvalidationTimeoutRef.current) {
        clearTimeout(tagsInvalidationTimeoutRef.current)
      }
      tagsInvalidationTimeoutRef.current = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['tags'] })
        tagsInvalidationTimeoutRef.current = null
      }, 1000)
    },
  })

  /**
   * Update tags array
   *
   * @param tags - New tags array
   */
  const updateTags = (tags: string[]) => {
    updateMutation.mutate({ tags })
  }

  /**
   * Add a single tag to existing tags
   * Prevents duplicate tags
   * Uses queryClient.getQueryData for fresh data to avoid stale closure issues
   *
   * @param tag - Tag to add
   */
  const addTag = (tag: string) => {
    // Get fresh data from queryClient to avoid stale closure when called
    // immediately after another mutation (optimistic updates modify cache)
    const currentTags = (queryClient.getQueryData(['sidecarMetadata', filename]) as SidecarMetadata)?.tags || []
    const trimmedTag = tag?.trim()

    // Reject empty/whitespace tags
    if (!trimmedTag) return
    // Already exists (compare trimmed)
    if (currentTags.includes(trimmedTag)) return

    updateMutation.mutate({ tags: [...currentTags, trimmedTag] })
  }

  /**
   * Remove a single tag from existing tags
   * Uses queryClient.getQueryData for fresh data to avoid stale closure issues
   *
   * @param tag - Tag to remove
   */
  const removeTag = (tag: string) => {
    // Get fresh data from queryClient to avoid stale closure when called
    // immediately after another mutation (optimistic updates modify cache)
    const currentTags = (queryClient.getQueryData(['sidecarMetadata', filename]) as SidecarMetadata)?.tags || []
    updateMutation.mutate({ tags: currentTags.filter((t) => t !== tag) })
  }

  /**
   * Update species field
   *
   * @param species - Species name
   */
  const updateSpecies = (species: string) => {
    updateMutation.mutate({ species })
  }

  /**
   * Update notes field
   *
   * @param notes - Notes text
   */
  const updateNotes = (notes: string) => {
    updateMutation.mutate({ notes })
  }

  /**
   * Generic update function for any sidecar metadata fields
   * Useful for updating multiple fields at once or custom fields
   * Returns a promise for async/await usage (uses mutateAsync)
   *
   * @param updates - Metadata fields to update
   * @returns Promise that resolves on success, rejects on error
   */
  const updateMetadata = (updates: SidecarMetadataUpdate): Promise<unknown> => {
    return updateMutation.mutateAsync(updates)
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
    updateMetadata,

    // Mutation state
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error,
  }
}
