/**
 * React hook for single-photo export with auto-download
 *
 * This hook wraps the existing export job system to provide a simplified
 * interface for exporting a single photo with automatic download on completion.
 *
 * Features:
 * - Creates export job with photo_paths filter for single photo
 * - Auto-polls job status while running (via useExportJob)
 * - Automatically triggers download when job completes
 * - Progress tracking during export
 * - Error handling with toast notifications
 *
 * @returns {Object} Hook state and actions
 * @returns {Function} exportPhoto - Start export: (photoPath, format) => void
 * @returns {boolean} isExporting - Whether export is in progress
 * @returns {Object|null} progress - Progress data: { current, total, percent, phase }
 * @returns {string|null} error - Error message if export failed
 * @returns {Function} reset - Clear error and progress state
 *
 * @example
 * const { exportPhoto, isExporting, progress, error, reset } = useSinglePhotoExport()
 *
 * // Start export
 * exportPhoto('/photos/moth.jpg', 'json')
 *
 * // Display progress
 * if (isExporting && progress) {
 *   console.log(`Progress: ${progress.percent}% (${progress.phase})`)
 * }
 *
 * // Handle errors
 * if (error) {
 *   console.error('Export failed:', error)
 *   reset() // Clear error state
 * }
 */

import { useState, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { useCreateExportJob, useExportJob } from './useExportJobs'
import { getExportJobDownloadUrl } from '../utils/exportApi'

interface Progress {
  current: number
  total: number
  percent: number
  phase: string
}

interface UseSinglePhotoExportResult {
  exportPhoto: (photoPath: string, format: string) => void
  isExporting: boolean
  progress: Progress | null
  error: string | null
  reset: () => void
}

export function useSinglePhotoExport(): UseSinglePhotoExportResult {
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hasDownloaded, setHasDownloaded] = useState<boolean>(false)
  const toastIdRef = useRef<string | null>(null)

  const createExportJob = useCreateExportJob()
  const jobQuery = useExportJob(jobId)

  // Get job data
  const job = jobQuery.data

  // Determine if export is in progress
  const isExporting = job?.status === 'pending' || job?.status === 'running'

  // Get progress data
  const progress = job?.progress || null

  /**
   * Start export for a single photo
   *
   * @param {string} photoPath - Absolute path to photo file
   * @param {string} format - Export format (json, csv, darwin_core, inaturalist)
   */
  const exportPhoto = (photoPath: string, format: string): void => {
    // Reset state
    setError(null)
    setHasDownloaded(false)
    setJobId(null)

    // Show loading toast
    toastIdRef.current = toast.loading('Preparing export...')

    // Create export job
    createExportJob.mutate(
      {
        format,
        filter: {
          photo_paths: [photoPath],
        },
      },
      {
        onSuccess: (response) => {
          const newJobId = response.data.job_id
          setJobId(newJobId)
          // Keep loading toast - will dismiss when job completes/fails
        },
        onError: (err) => {
          setError(err as string)
          if (toastIdRef.current) {
            toast.dismiss(toastIdRef.current)
          }
          toast.error('Failed to start export')
          toastIdRef.current = null
        },
      }
    )
  }

  /**
   * Reset state (clear error, progress, stop polling)
   */
  const reset = (): void => {
    setJobId(null)
    setError(null)
    setHasDownloaded(false)
    if (toastIdRef.current) {
      toast.dismiss(toastIdRef.current)
      toastIdRef.current = null
    }
  }

  // Handle job completion
  useEffect(() => {
    if (!job) return

    // Handle successful completion
    if (job.status === 'completed' && !hasDownloaded) {
      setHasDownloaded(true)

      // Dismiss loading toast
      if (toastIdRef.current) {
        toast.dismiss(toastIdRef.current)
        toastIdRef.current = null
      }

      // Trigger download
      const downloadUrl = getExportJobDownloadUrl(job.job_id)
      const anchor = document.createElement('a')
      anchor.href = downloadUrl
      anchor.style.display = 'none'
      document.body.appendChild(anchor)
      anchor.click()
      document.body.removeChild(anchor)

      // Show success toast
      toast.success('Export downloaded successfully')

      // Clear job ID to stop polling
      setJobId(null)
    }

    // Handle failure
    if (job.status === 'failed') {
      const errorMessage = job.error_message || 'Unknown error'
      setError(errorMessage)

      // Dismiss loading toast
      if (toastIdRef.current) {
        toast.dismiss(toastIdRef.current)
        toastIdRef.current = null
      }

      toast.error(`Export failed: ${errorMessage}`)

      // Clear job ID to stop polling
      setJobId(null)
    }
  }, [job, hasDownloaded])

  return {
    exportPhoto,
    isExporting,
    progress,
    error,
    reset,
  }
}
