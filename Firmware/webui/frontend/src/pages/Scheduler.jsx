import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCronJobs, getSchedulerStatus, addCronJob, deleteCronJob } from '../utils/api'
import { useState } from 'react'

export default function Scheduler() {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newJob, setNewJob] = useState({
    command: '',
    schedule: '',
    comment: '',
  })

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['cron-jobs'],
    queryFn: () => getCronJobs().then(res => res.data.jobs),
  })

  const { data: status } = useQuery({
    queryKey: ['scheduler-status'],
    queryFn: () => getSchedulerStatus().then(res => res.data),
  })

  const addMutation = useMutation({
    mutationFn: addCronJob,
    onSuccess: () => {
      queryClient.invalidateQueries(['cron-jobs'])
      setShowAddForm(false)
      setNewJob({ command: '', schedule: '', comment: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteCronJob,
    onSuccess: () => {
      queryClient.invalidateQueries(['cron-jobs'])
    },
  })

  const handleAddJob = (e) => {
    e.preventDefault()
    addMutation.mutate(newJob)
  }

  if (jobsLoading) {
    return <div className="text-center py-12">Loading scheduler...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Scheduler</h2>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          {showAddForm ? 'Cancel' : 'Add Job'}
        </button>
      </div>

      {/* Scheduler Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-2">Status</h3>
        <p className={`text-sm ${status?.cron_active ? 'text-green-600' : 'text-red-600'}`}>
          Cron service: {status?.cron_active ? 'Active' : 'Inactive'}
        </p>
      </div>

      {/* Add Job Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Add New Cron Job</h3>
          <form onSubmit={handleAddJob} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Command
              </label>
              <input
                type="text"
                value={newJob.command}
                onChange={(e) => setNewJob({ ...newJob, command: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., python3 /path/to/script.py"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Schedule (cron format)
              </label>
              <input
                type="text"
                value={newJob.schedule}
                onChange={(e) => setNewJob({ ...newJob, schedule: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., 0 * * * * (hourly)"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                Format: minute hour day month weekday
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Comment (optional)
              </label>
              <input
                type="text"
                value={newJob.comment}
                onChange={(e) => setNewJob({ ...newJob, comment: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Description of this job"
              />
            </div>
            <button
              type="submit"
              disabled={addMutation.isPending}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
            >
              {addMutation.isPending ? 'Adding...' : 'Add Job'}
            </button>
          </form>
        </div>
      )}

      {/* Jobs List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Scheduled Jobs</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {jobs && jobs.length === 0 && (
            <p className="px-6 py-4 text-gray-500">No scheduled jobs</p>
          )}
          {jobs?.map((job, index) => (
            <div key={index} className="px-6 py-4 hover:bg-gray-50">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <p className="font-mono text-sm text-gray-900">{job.command}</p>
                  <p className="text-sm text-gray-600 mt-1">Schedule: {job.schedule}</p>
                  {job.comment && (
                    <p className="text-xs text-gray-500 mt-1">{job.comment}</p>
                  )}
                  <span className={`inline-block mt-2 px-2 py-1 text-xs rounded ${
                    job.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {job.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <button
                  onClick={() => deleteMutation.mutate(job.command)}
                  disabled={deleteMutation.isPending}
                  className="ml-4 text-red-600 hover:text-red-800 text-sm disabled:text-gray-400"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
