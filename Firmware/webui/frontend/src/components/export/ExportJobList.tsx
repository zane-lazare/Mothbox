import { useState } from 'react'
import { useExportJobs, useDeleteExportJob } from '../../hooks/useExportJobs'
import type { ExportJob } from '../../types/api'
import {
  ArrowDownTrayIcon,
  TrashIcon,
  CircleStackIcon,
  DocumentTextIcon,
  TableCellsIcon,
} from '@heroicons/react/24/outline'
import ConfirmDialog from '../common/ConfirmDialog'

type ExtendedJob = ExportJob & {
  progress?: {
    total?: number
  }
  result?: {
    file_path?: string
  }
  created_at: string
}

type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'expired'

export default function ExportJobList() {
  const { data, isLoading } = useExportJobs()
  const deleteJobMutation = useDeleteExportJob()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [jobToDelete, setJobToDelete] = useState<string | null>(null)

  const jobs = (data?.jobs || []) as ExtendedJob[]

  const getFormatIcon = (format: string): JSX.Element => {
    const icons: Record<string, typeof CircleStackIcon> = {
      darwin_core: CircleStackIcon,
      inaturalist: CircleStackIcon,
      json: DocumentTextIcon,
      csv: TableCellsIcon,
    }
    const Icon = icons[format] || DocumentTextIcon
    return <Icon className="w-5 h-5 inline mr-2" />
  }

  const getFormatLabel = (format: string): string => {
    const labels: Record<string, string> = {
      darwin_core: 'Darwin Core',
      inaturalist: 'iNaturalist',
      json: 'JSON',
      csv: 'CSV',
    }
    return labels[format] || format
  }

  const getStatusBadge = (status: JobStatus): JSX.Element => {
    const styles: Record<JobStatus, string> = {
      pending: 'bg-gray-100 text-gray-800',
      running: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      cancelled: 'bg-yellow-100 text-yellow-800',
      expired: 'bg-gray-100 text-gray-800',
    }

    const labels: Record<JobStatus, string> = {
      pending: 'Pending',
      running: 'Running',
      completed: 'Completed',
      failed: 'Failed',
      cancelled: 'Cancelled',
      expired: 'Expired',
    }

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}>
        {labels[status] || status}
      </span>
    )
  }

  const handleDownload = (jobId: string) => {
    const downloadUrl = `/api/export/jobs/${jobId}/download`
    window.open(downloadUrl, '_blank')
  }

  const handleDelete = (jobId: string) => {
    setJobToDelete(jobId)
    setShowDeleteConfirm(true)
  }

  const handleConfirmDelete = () => {
    if (jobToDelete) {
      deleteJobMutation.mutate(jobToDelete, {
        onSuccess: () => {
          setShowDeleteConfirm(false)
          setJobToDelete(null)
        },
      })
    }
  }

  const formatRelativeTime = (timestamp: string): string => {
    try {
      const date = new Date(timestamp)
      const now = new Date()
      const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

      if (seconds < 60) return 'just now'
      const minutes = Math.floor(seconds / 60)
      if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
      const hours = Math.floor(minutes / 60)
      if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`
      const days = Math.floor(hours / 24)
      if (days < 30) return `${days} day${days !== 1 ? 's' : ''} ago`
      const months = Math.floor(days / 30)
      if (months < 12) return `${months} month${months !== 1 ? 's' : ''} ago`
      const years = Math.floor(months / 12)
      return `${years} year${years !== 1 ? 's' : ''} ago`
    } catch {
      return 'Unknown'
    }
  }

  if (isLoading) {
    return (
      <div
        className="bg-white rounded-lg shadow p-6"
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
        </div>
        <span className="sr-only">Loading export jobs...</span>
      </div>
    )
  }

  if (!jobs || jobs.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6" role="status">
        <div className="text-center py-12">
          <CircleStackIcon className="mx-auto h-12 w-12 text-gray-400" aria-hidden="true" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No export jobs yet</h3>
          <p className="mt-1 text-sm text-gray-500">
            Start your first export using the form above
          </p>
        </div>
      </div>
    )
  }

  // Limit to last 10 jobs
  const displayJobs = jobs.slice(0, 10)

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-medium text-gray-900">Recent Exports</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Format
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Photos
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {displayJobs.map((job) => (
              <tr key={job.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {getFormatIcon(job.format)}
                  {getFormatLabel(job.format)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(job.status as JobStatus)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {job.progress?.total || 0}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatRelativeTime(job.created_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                  {job.status === 'completed' && job.result?.file_path && (
                    <button
                      onClick={() => handleDownload(job.id)}
                      className="text-blue-600 hover:text-blue-900 inline-flex items-center"
                      title="Download export"
                    >
                      <ArrowDownTrayIcon className="w-4 h-4 mr-1" />
                      Download
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(job.id)}
                    className="text-red-600 hover:text-red-900 inline-flex items-center ml-2"
                    title="Delete job"
                  >
                    <TrashIcon className="w-4 h-4 mr-1" />
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => {
          setShowDeleteConfirm(false)
          setJobToDelete(null)
        }}
        onConfirm={handleConfirmDelete}
        title="Delete Export Job?"
        message="Are you sure you want to delete this export job? This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        isLoading={deleteJobMutation.isPending}
      />
    </div>
  )
}
