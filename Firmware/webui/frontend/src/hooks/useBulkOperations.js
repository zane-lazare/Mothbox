import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../utils/api'

const MAX_BATCH_SIZE = 100

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
 *   // Undo support
 *   if (result.previousState) {
 *     // Can restore previous tags using result.previousState
 *   }
 * }
 */
export default function useBulkOperations() {
  const [isProcessing, setIsProcessing] = useState(false)
  const queryClient = useQueryClient()

  /**
   * Helper function to chunk array into batches
   */
  const chunkArray = useCallback((arr, size) => {
    const chunks = []
    for (let i = 0; i < arr.length; i += size) {
      chunks.push(arr.slice(i, i + size))
    }
    return chunks
  }, [])

  /**
   * Helper function to fetch previous state for undo support
   */
  const fetchPreviousState = useCallback(async (filenames, fields = ['tags', 'species']) => {
    const previousState = {}

    await Promise.all(
      filenames.map(async (filename) => {
        try {
          const response = await api.get(`/sidecar/photos/${encodeURIComponent(filename)}`)
          const data = response.data

          // Extract only requested fields
          const state = {}
          fields.forEach(field => {
            if (data[field] !== undefined) {
              state[field] = data[field]
            }
          })

          previousState[filename] = state
        } catch (error) {
          // Warning: Failed fetches are silently omitted from previousState.
          // This means undo will only restore photos with successful fetches.
          // Partial undo is better than no undo, but callers should be aware.
          console.warn(`Failed to fetch previous state for ${filename}:`, error)
        }
      })
    )

    return previousState
  }, [])

  /**
   * Generic batched operation handler
   * Splits large operations into batches and aggregates results
   */
  const batchedOperation = useCallback(async (
    filenames,
    operation,
    onProgress = null,
    fetchUndo = false,
    undoFields = ['tags']
  ) => {
    setIsProcessing(true)

    try {
      // Fetch previous state for undo support if requested
      const previousState = fetchUndo
        ? await fetchPreviousState(filenames, undoFields)
        : null

      const batches = chunkArray(filenames, MAX_BATCH_SIZE)
      const results = {
        success: [],
        failed: [],
        errors: {},
        previousState
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
  const bulkAddTags = useCallback(async (filenames, tags, onProgress = null) => {
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
  const bulkReplaceTags = useCallback(async (filenames, tags, onProgress = null) => {
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
  const bulkRemoveTags = useCallback(async (filenames, tagsToRemove, onProgress = null) => {
    setIsProcessing(true)

    try {
      // Fetch previous state for undo
      const previousState = await fetchPreviousState(filenames, ['tags'])

      // Fetch current tags for each photo
      const photoUpdates = {}
      const failedFetches = []

      await Promise.all(
        filenames.map(async (filename) => {
          try {
            const response = await api.get(`/sidecar/photos/${encodeURIComponent(filename)}`)
            const currentTags = response.data.tags || []

            // Filter out tags to remove
            const filteredTags = currentTags.filter(tag => !tagsToRemove.includes(tag))
            photoUpdates[filename] = { tags: filteredTags }
          } catch (error) {
            failedFetches.push({
              filename,
              error: error.message || 'Failed to fetch metadata'
            })
          }
        })
      )

      // If all fetches failed, return early
      if (Object.keys(photoUpdates).length === 0) {
        setIsProcessing(false)
        return {
          success: [],
          failed: failedFetches.map(f => f.filename),
          errors: Object.fromEntries(failedFetches.map(f => [f.filename, f.error])),
          previousState
        }
      }

      // Update photos with filtered tags
      const successfulFilenames = Object.keys(photoUpdates)

      const result = await batchedOperation(
        successfulFilenames,
        async (batch) => {
          // Build updates for this batch
          const batchUpdates = {}
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
   * Update species field for photos
   *
   * @param {string[]} filenames - Photo filenames
   * @param {string} species - Species name
   * @param {Function} onProgress - Progress callback (optional)
   * @returns {Promise<object>} Result with success/failed/errors/previousState
   */
  const bulkUpdateSpecies = useCallback(async (filenames, species, onProgress = null) => {
    const result = await batchedOperation(
      filenames,
      async (batch) => {
        const response = await api.post('/sidecar/bulk', {
          filenames: batch,
          updates: { species },
          mode: 'replace'
        })
        return response.data
      },
      onProgress,
      true, // fetchUndo
      ['species'] // undoFields
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
  const bulkDelete = useCallback(async (filenames, onProgress = null) => {
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
