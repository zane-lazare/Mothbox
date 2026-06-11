import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, getBulkSidecarMetadata } from '../utils/api'
import { API_LIMITS } from '../constants/config'

const MAX_BATCH_SIZE = API_LIMITS.MAX_BATCH_SIZE

interface ProgressCallback {
  currentBatch: number
  totalBatches: number
  processedCount: number
  totalCount: number
}

interface BulkOperationResult {
  success: string[]
  failed: string[]
  errors: Record<string, string>
  previousState: Record<string, any> | null
  undoFetchedCount: number
  undoFailedCount: number
}

interface SidecarMetadata {
  [key: string]: any
}

interface BulkSidecarResponse {
  success: Record<string, SidecarMetadata>
  failed?: string[]
}

interface PreviousStateResult {
  state: Record<string, any>
  fetchedCount: number
  failedCount: number
}

interface UseBulkOperationsReturn {
  bulkAddTags: (filenames: string[], tags: string[], onProgress?: ((progress: ProgressCallback) => void) | null) => Promise<BulkOperationResult>
  bulkReplaceTags: (filenames: string[], tags: string[], onProgress?: ((progress: ProgressCallback) => void) | null) => Promise<BulkOperationResult>
  bulkRemoveTags: (filenames: string[], tagsToRemove: string[], onProgress?: ((progress: ProgressCallback) => void) | null) => Promise<BulkOperationResult>
  bulkUpdateSpecies: (filenames: string[], speciesData: SpeciesData, onProgress?: ((progress: ProgressCallback) => void) | null) => Promise<BulkOperationResult>
  bulkDelete: (filenames: string[], onProgress?: ((progress: ProgressCallback) => void) | null) => Promise<BulkOperationResult>
  isProcessing: boolean
}

interface SpeciesData {
  species: string
  species_confidence?: string
  species_common_name?: string
}

/**
 * Custom hook for bulk operations on photos (tag, species, delete)
 *
 * Provides batching support for large selections (>100 photos),
 * progress tracking, and undo support via previousState snapshots.
 *
 * @returns {object} Hook state and operation functions
 * @returns {Function} bulkAddTags - Add tags to photos (mode: append)
 * @returns {Function} bulkReplaceTags - Replace all tags (mode: replace)
 * @returns {Function} bulkRemoveTags - Remove specific tags from photos
 * @returns {Function} bulkUpdateSpecies - Update species field
 * @returns {Function} bulkDelete - Delete photos (NO undo)
 * @returns {boolean} isProcessing - Whether operation is in progress
 *
 * @example
 * const { bulkAddTags, isProcessing } = useBulkOperations()
 *
 * const handleAddTags = async () => {
 *   const result = await bulkAddTags(
 *     ['photo1.jpg', 'photo2.jpg'],
 *     ['moth', 'night'],
 *     (progress) => console.log(`Batch ${progress.currentBatch}/${progress.totalBatches}`)
 *   )
 *
 *   console.log(`Success: ${result.success.length}, Failed: ${result.failed.length}`)
 *
 *   // Undo support with fetch metadata
 *   if (result.previousState) {
 *     // Can restore previous tags using result.previousState
 *     // Check if some photos failed to backup for undo
 *     if (result.undoFailedCount > 0) {
 *       console.warn(`Undo available for ${result.undoFetchedCount} of ${filenames.length} photos`)
 *     }
 *   }
 * }
 */
export default function useBulkOperations(): UseBulkOperationsReturn {
  const [isProcessing, setIsProcessing] = useState(false)
  const queryClient = useQueryClient()

  /**
   * Helper function to chunk array into batches
   */
  const chunkArray = useCallback(<T,>(arr: T[], size: number): T[][] => {
    const chunks: T[][] = []
    for (let i = 0; i < arr.length; i += size) {
      chunks.push(arr.slice(i, i + size))
    }
    return chunks
  }, [])

  /**
   * Helper function to fetch previous state for undo support
   *
   * Uses the bulk GET /api/sidecar/bulk endpoint to fetch all metadata in a
   * single request instead of N individual API calls.
   *
   * Note: There is a small window between fetching previousState and executing
   * the operation where another process could modify the same photos. In a
   * single-user scenario (typical for Mothbox), this is extremely unlikely.
   * If multi-user support is added, consider optimistic locking or timestamps.
   *
   * @returns {Object} { state: previousState, fetchedCount, failedCount }
   */
  const fetchPreviousState = useCallback(async (filenames: string[], fields: string[] = ['tags', 'species']): Promise<PreviousStateResult> => {
    const previousState: Record<string, any> = {}
    let fetchedCount = 0
    let failedCount = 0

    try {
      // Use bulk endpoint instead of N individual requests
      const response = await getBulkSidecarMetadata(filenames)
      const { success, failed } = response.data as BulkSidecarResponse

      // Extract only requested fields from each photo's metadata
      for (const [filename, metadata] of Object.entries(success)) {
        const state: Record<string, any> = {}
        fields.forEach(field => {
          if (metadata[field] !== undefined) {
            state[field] = metadata[field]
          }
        })
        previousState[filename] = state
      }

      fetchedCount = Object.keys(success).length
      failedCount = failed?.length || 0
    } catch (error) {
      // Warning: If bulk fetch fails completely, return empty previousState.
      // This means undo will not work for any photos.
      // Partial undo is better than no undo, but callers should be aware.
      console.warn('Failed to fetch previous state:', error)
      failedCount = filenames.length
    }

    return { state: previousState, fetchedCount, failedCount }
  }, [])

  /**
   * Generic batched operation handler
   * Splits large operations into batches and aggregates results
   */
  const batchedOperation = useCallback(async (
    filenames: string[],
    operation: (batch: string[]) => Promise<any>,
    onProgress: ((progress: ProgressCallback) => void) | null = null,
    fetchUndo: boolean = false,
    undoFields: string[] = ['tags']
  ): Promise<BulkOperationResult> => {
    setIsProcessing(true)

    try {
      // Fetch previous state for undo support if requested
      let previousState: Record<string, any> | null = null
      let undoFetchedCount = 0
      let undoFailedCount = 0

      if (fetchUndo) {
        const undoResult = await fetchPreviousState(filenames, undoFields)
        previousState = undoResult.state
        undoFetchedCount = undoResult.fetchedCount
        undoFailedCount = undoResult.failedCount
      }

      const batches = chunkArray(filenames, MAX_BATCH_SIZE)
      const results: BulkOperationResult = {
        success: [],
        failed: [],
        errors: {},
        previousState,
        undoFetchedCount,
        undoFailedCount
      }

      for (let i = 0; i < batches.length; i++) {
        // Fire progress callback before processing batch
        if (onProgress) {
          onProgress({
            currentBatch: i + 1,
            totalBatches: batches.length,
            processedCount: i * MAX_BATCH_SIZE,
            totalCount: filenames.length
          })
        }

        const batchResult = await operation(batches[i])

        // Aggregate results from this batch
        if (batchResult.success) {
          results.success.push(...batchResult.success)
        }
        if (batchResult.failed) {
          results.failed.push(...batchResult.failed)
        }
        if (batchResult.errors) {
          Object.assign(results.errors, batchResult.errors)
        }
      }

      return results
    } finally {
      setIsProcessing(false)
    }
  }, [chunkArray, fetchPreviousState])

  /**
   * Add tags to photos (appends to existing tags)
   *
   * @param {string[]} filenames - Photo filenames
   * @param {string[]} tags - Tags to add
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise<object>} Result with success/failed/errors/previousState
   */
  const bulkAddTags = useCallback(async (filenames: string[], tags: string[], onProgress: ((progress: ProgressCallback) => void) | null = null): Promise<BulkOperationResult> => {
    const result = await batchedOperation(
      filenames,
      async (batch) => {
        const response = await api.post('/sidecar/bulk', {
          filenames: batch,
          updates: { tags },
          mode: 'append'
        })
        return response.data
      },
      onProgress,
      true, // fetchUndo
      ['tags'] // undoFields
    )

    // Invalidate caches on success
    if (result.success.length > 0) {
      queryClient.invalidateQueries({ queryKey: ['sidecarMetadata'] })
      queryClient.invalidateQueries({ queryKey: ['tags'] })
    }

    return result
  }, [batchedOperation, queryClient])

  /**
   * Replace all tags on photos
   *
   * @param {string[]} filenames - Photo filenames
   * @param {string[]} tags - New tags array
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise<object>} Result with success/failed/errors/previousState
   */
  const bulkReplaceTags = useCallback(async (filenames: string[], tags: string[], onProgress: ((progress: ProgressCallback) => void) | null = null): Promise<BulkOperationResult> => {
    const result = await batchedOperation(
      filenames,
      async (batch) => {
        const response = await api.post('/sidecar/bulk', {
          filenames: batch,
          updates: { tags },
          mode: 'replace'
        })
        return response.data
      },
      onProgress,
      true, // fetchUndo
      ['tags'] // undoFields
    )

    // Invalidate caches on success
    if (result.success.length > 0) {
      queryClient.invalidateQueries({ queryKey: ['sidecarMetadata'] })
      queryClient.invalidateQueries({ queryKey: ['tags'] })
    }

    return result
  }, [batchedOperation, queryClient])

  /**
   * Remove specific tags from photos
   * Fetches existing tags, filters out specified tags, then updates
   *
   * @param {string[]} filenames - Photo filenames
   * @param {string[]} tagsToRemove - Tags to remove
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise<object>} Result with success/failed/errors/previousState
   */
  const bulkRemoveTags = useCallback(async (filenames: string[], tagsToRemove: string[], onProgress: ((progress: ProgressCallback) => void) | null = null): Promise<BulkOperationResult> => {
    setIsProcessing(true)

    try {
      // Fetch previous state for undo (will also be used for current tags)
      const { state: previousState, fetchedCount, failedCount } = await fetchPreviousState(filenames, ['tags'])

      // Use previousState (which has current tags) to build photoUpdates
      // This avoids a second round of N API calls
      const photoUpdates: Record<string, { tags: string[] }> = {}
      const failedFetches: Array<{ filename: string; error: string }> = []

      for (const filename of filenames) {
        const state = previousState[filename]
        if (state) {
          const currentTags: string[] = state.tags || []
          // Filter out tags to remove
          const filteredTags = currentTags.filter(tag => !tagsToRemove.includes(tag))
          photoUpdates[filename] = { tags: filteredTags }
        } else {
          failedFetches.push({
            filename,
            error: 'Failed to fetch metadata'
          })
        }
      }

      // If all fetches failed, return early
      if (Object.keys(photoUpdates).length === 0) {
        setIsProcessing(false)
        return {
          success: [],
          failed: failedFetches.map(f => f.filename),
          errors: Object.fromEntries(failedFetches.map(f => [f.filename, f.error])),
          previousState,
          undoFetchedCount: fetchedCount,
          undoFailedCount: failedCount
        }
      }

      // Update photos with filtered tags
      const successfulFilenames = Object.keys(photoUpdates)

      const result = await batchedOperation(
        successfulFilenames,
        async (batch) => {
          // Build updates for this batch
          const batchUpdates: Record<string, { tags: string[] }> = {}
          batch.forEach(filename => {
            batchUpdates[filename] = photoUpdates[filename]
          })

          const response = await api.post('/sidecar/bulk', {
            filenames: batch,
            updates: batchUpdates,
            mode: 'individual'
          })
          return response.data
        },
        onProgress,
        false // Don't fetch undo again - we already have it
      )

      // Add fetch failures to result
      result.failed.push(...failedFetches.map(f => f.filename))
      Object.assign(result.errors, Object.fromEntries(failedFetches.map(f => [f.filename, f.error])))

      // Restore previousState from our fetch
      result.previousState = previousState
      result.undoFetchedCount = fetchedCount
      result.undoFailedCount = failedCount

      // Invalidate caches on success
      if (result.success.length > 0) {
        queryClient.invalidateQueries({ queryKey: ['sidecarMetadata'] })
        queryClient.invalidateQueries({ queryKey: ['tags'] })
      }

      return result
    } finally {
      setIsProcessing(false)
    }
  }, [batchedOperation, fetchPreviousState, queryClient])

  /**
   * Update species fields for photos
   *
   * @param {string[]} filenames - Photo filenames
   * @param {object} speciesData - Species data object with backend field names
   * @param {string} speciesData.species - Scientific name
   * @param {string} [speciesData.species_confidence] - Confidence level
   * @param {string} [speciesData.species_common_name] - Common name
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise<object>} Result with success/failed/errors/previousState
   */
  const bulkUpdateSpecies = useCallback(async (filenames: string[], speciesData: SpeciesData, onProgress: ((progress: ProgressCallback) => void) | null = null): Promise<BulkOperationResult> => {
    const result = await batchedOperation(
      filenames,
      async (batch) => {
        const response = await api.post('/sidecar/bulk', {
          filenames: batch,
          updates: speciesData,
          mode: 'replace'
        })
        return response.data
      },
      onProgress,
      true, // fetchUndo
      ['species', 'species_confidence', 'species_common_name'] // undoFields
    )

    // Invalidate caches on success
    if (result.success.length > 0) {
      queryClient.invalidateQueries({ queryKey: ['sidecarMetadata'] })
      queryClient.invalidateQueries({ queryKey: ['species'] })
    }

    return result
  }, [batchedOperation, queryClient])

  /**
   * Delete photos (destructive - NO undo)
   *
   * Note: fetchUndo=false because delete is irreversible at filesystem level.
   * Files are permanently removed and cannot be restored from metadata alone.
   * To support undo, the backend would need a trash/recycle bin feature.
   *
   * @param {string[]} filenames - Photo filenames
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise<object>} Result with success/failed/errors (no previousState)
   */
  const bulkDelete = useCallback(async (filenames: string[], onProgress: ((progress: ProgressCallback) => void) | null = null): Promise<BulkOperationResult> => {
    const result = await batchedOperation(
      filenames,
      async (batch) => {
        const response = await api.delete('/gallery/photos/bulk', {
          data: { filenames: batch }
        })
        return response.data
      },
      onProgress,
      false // No undo - files are permanently deleted from filesystem
    )

    // Invalidate caches on success
    if (result.success.length > 0) {
      queryClient.invalidateQueries({ queryKey: ['photos'] })
      queryClient.invalidateQueries({ queryKey: ['sidecarMetadata'] })
      queryClient.invalidateQueries({ queryKey: ['tags'] })
      queryClient.invalidateQueries({ queryKey: ['species'] })
    }

    return result
  }, [batchedOperation, queryClient])

  return {
    bulkAddTags,
    bulkReplaceTags,
    bulkRemoveTags,
    bulkUpdateSpecies,
    bulkDelete,
    isProcessing
  }
}
