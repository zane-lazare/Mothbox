import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query'
import { getPreferences, setPreference } from '../utils/api'

/**
 * View mode type
 */
type ViewMode = 'grid' | 'list' | 'map'

/**
 * Preferences API response type
 */
interface Preferences {
  [key: string]: unknown
  gallery_view_mode?: ViewMode
}

/**
 * Return type for useViewMode hook
 */
interface UseViewModeResult {
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void
  isLoading: boolean
}

/**
 * Custom hook for managing gallery view mode preference
 *
 * Provides view mode state (grid vs list) with backend API persistence
 * for cross-device synchronization. Implements optimistic updates for
 * instant UI feedback.
 *
 * @returns {Object} Hook state
 * @returns {('grid'|'list'|'map')} viewMode - Current view mode
 * @returns {Function} setViewMode - Function to change view mode
 * @returns {boolean} isLoading - Whether preference is being loaded
 *
 * @example
 * const { viewMode, setViewMode, isLoading } = useViewMode()
 *
 * // Change view mode
 * setViewMode('list')
 */
export function useViewMode(): UseViewModeResult {
  const queryClient = useQueryClient()
  const DEFAULT_VIEW_MODE: ViewMode = 'grid'
  const PREFERENCE_KEY = 'gallery_view_mode'

  /**
   * Fetch current preference from backend API
   */
  const { data: preferences, isLoading }: UseQueryResult<Preferences, Error> = useQuery({
    queryKey: ['preferences'],
    queryFn: async () => {
      const response = await getPreferences()
      return response.data
    },
    staleTime: Infinity, // Preferences don't change often, cache indefinitely
    retry: false, // Don't retry on error, use default
  })

  /**
   * Extract view mode from preferences, with validation
   */
  const viewMode: ViewMode = (() => {
    const savedMode = preferences?.[PREFERENCE_KEY]

    // Validate the saved preference
    if (savedMode === 'grid' || savedMode === 'list' || savedMode === 'map') {
      return savedMode
    }

    // Default to grid if invalid or missing
    return DEFAULT_VIEW_MODE
  })()

  /**
   * Mutation for saving preference to backend API
   */
  const mutation = useMutation({
    mutationFn: async (newViewMode: ViewMode) => {
      const response = await setPreference(PREFERENCE_KEY, newViewMode)
      return response.data
    },
    onMutate: async (newViewMode: ViewMode) => {
      // Cancel outgoing refetches to prevent overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: ['preferences'] })

      // Snapshot previous value for rollback
      const previousPreferences = queryClient.getQueryData<Preferences>(['preferences'])

      // Optimistically update the cache immediately
      queryClient.setQueryData<Preferences>(['preferences'], (old) => ({
        ...old,
        [PREFERENCE_KEY]: newViewMode,
      }))

      // Return context for rollback
      return { previousPreferences }
    },
    onError: (_error, _newViewMode, context) => {
      // Rollback to previous value on error
      if (context?.previousPreferences) {
        queryClient.setQueryData(['preferences'], context.previousPreferences)
      }
    },
    onSuccess: () => {
      // Invalidate to refetch and ensure sync with server
      queryClient.invalidateQueries({ queryKey: ['preferences'] })
    },
  })

  /**
   * Set view mode with validation
   *
   * @param {('grid'|'list'|'map')} newViewMode - The view mode to switch to
   */
  const setViewMode = (newViewMode: ViewMode) => {
    // Validate input
    if (newViewMode !== 'grid' && newViewMode !== 'list' && newViewMode !== 'map') {
      console.warn('Invalid view mode:', newViewMode)
      return
    }

    // Don't make API call if already in this mode
    if (newViewMode === viewMode) {
      return
    }

    // Trigger mutation (optimistic update happens in onMutate)
    mutation.mutate(newViewMode)
  }

  return {
    viewMode,
    setViewMode,
    isLoading,
  }
}
