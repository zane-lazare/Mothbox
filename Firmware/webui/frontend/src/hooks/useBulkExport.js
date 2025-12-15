/**
 * React hook for bulk photo export (Issue #127)
 *
 * This hook wraps the existing export job system to provide a simplified
 * interface for exporting multiple photos with progress tracking.
 *
 * Features:
 * - Creates export job with photo_paths filter for multiple photos
 * - Auto-polls job status while running (via useExportJob)
 * - Progress tracking during export
 * - Download URL when completed
 * - Cancellation support
 * - Error handling
 * - Optional onComplete callback
 *
 * @param {Object} options - Hook options
 * @param {Function} [options.onComplete] - Callback when export completes
 * @returns {Object} Hook state and actions
 * @returns {Function} exportPhotos - Start export: (photoPaths, format) => Promise<void>
 * @returns {boolean} isExporting - Whether export is in progress (pending/running)
 * @returns {Object|null} progress - Progress data: { current, total, percent, phase }
 * @returns {string|null} error - Error message if export failed
 * @returns {string|null} jobId - Current job ID
 * @returns {string|null} downloadUrl - Download URL when completed
 * @returns {Function} cancel - Cancel running job: () => Promise<void>
 * @returns {Function} reset - Clear all state: () => void
 *
 * @example
 * const { exportPhotos, isExporting, progress, downloadUrl, cancel, reset } = useBulkExport({
 *   onComplete: () => console.log('Export complete!')
 * })
 *
 * // Start export
 * await exportPhotos(['/photos/moth1.jpg', '/photos/moth2.jpg'], 'darwin_core')
 *
 * // Display progress
 * if (isExporting && progress) {
 *   console.log(`Progress: ${progress.percent}% (${progress.phase})`)
 * }
 *
 * // Cancel export
 * await cancel()
 *
 * // Download completed export
 * if (downloadUrl) {
 *   window.open(downloadUrl)
 * }
 *
 * // Reset state
 * reset()
 */

import { useState, useEffect, useRef } from 'react'
import { useCreateExportJob, useExportJob, useCancelExportJob } from './useExportJobs'
import { getExportJobDownloadUrl } from '../utils/exportApi'

export default function useBulkExport({ onComplete } = {}) {
  const [jobId, setJobId] = useState(null)
  const [error, setError] = useState(null)
  const hasCompletedRef = useRef(false)

  const createExportJob = useCreateExportJob()
  const jobQuery = useExportJob(jobId)
  const cancelExportJobMutation = useCancelExportJob()

  // Get job data
  const job = jobQuery.data

  // Determine if export is in progress
  const isExporting = job?.status === 'pending' || job?.status === 'running'

  // Get progress data
  const progress = job?.progress || null

  // Generate download URL when completed
  const downloadUrl = job?.status === 'completed' && jobId ? getExportJobDownloadUrl(jobId) : null

  /**
   * Start export for multiple photos
   *
   * @param {string[]} photoPaths - Array of absolute paths to photo files
   * @param {string} format - Export format (darwin_core, inaturalist, json, csv)
   * @returns {Promise<void>}
   */
  const exportPhotos = async (photoPaths, format) => {
    // Reset state
    setError(null)
    setJobId(null)
    hasCompletedRef.current = false

    try {
      // Create export job
      const response = await createExportJob.mutateAsync({
        format,
        filter: {
          photo_paths: photoPaths,
        },
      })

      const newJobId = response.data.job_id
      setJobId(newJobId)
    } catch (err) {
      setError(err.message || 'Failed to create export job')
      throw err
    }
  }

  /**
   * Cancel running export job
   *
   * @returns {Promise<void>}
   */
  const cancel = async () => {
    if (!jobId) return

    try {
      await cancelExportJobMutation.mutateAsync(jobId)
    } catch (err) {
      setError(err.message || 'Failed to cancel export job')
      throw err
    }
  }

  /**
   * Reset state (clear error, progress, stop polling)
   */
  const reset = () => {
    setJobId(null)
    setError(null)
    hasCompletedRef.current = false
  }

  // Handle job completion and failure
  useEffect(() => {
    if (!job) return

    // Handle successful completion
    if (job.status === 'completed' && !hasCompletedRef.current) {
      hasCompletedRef.current = true

      // Call onComplete callback if provided
      if (onComplete) {
        onComplete()
      }
    }

    // Handle failure
    if (job.status === 'failed') {
      const errorMessage = job.error || 'Export failed'
      setError(errorMessage)
    }
  }, [job, onComplete])

  return {
    exportPhotos,
    isExporting,
    progress,
    error,
    jobId,
    downloadUrl,
    cancel,
    reset,
  }
}
