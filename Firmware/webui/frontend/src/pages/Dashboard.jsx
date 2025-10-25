import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSystemStatus, getPowerStatus, capturePhoto, getPhotos, syncGPS } from '../utils/api'
import { formatTimestamp } from '../utils/helpers'
import { useState } from 'react'
import toast from 'react-hot-toast'

export default function Dashboard() {
  const [capturing, setCapturing] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const queryClient = useQueryClient()

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => getSystemStatus().then(res => res.data),
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const { data: power } = useQuery({
    queryKey: ['power-status'],
    queryFn: () => getPowerStatus().then(res => res.data),
    refetchInterval: 5000,
  })

  const { data: photos } = useQuery({
    queryKey: ['photos'],
    queryFn: () => getPhotos().then(res => res.data.photos),
  })

  const handleCapturePhoto = async () => {
    setCapturing(true)
    try {
      await capturePhoto()
      // Refetch photos after capture
      setTimeout(() => {
        window.location.reload() // Simple refresh for now
      }, 2000)
    } catch (error) {
      console.error('Failed to capture photo:', error)
    } finally {
      setCapturing(false)
    }
  }

  const handleSyncGPS = async () => {
    setSyncing(true)
    try {
      await syncGPS()
      // Refetch system status to get updated GPS data
      queryClient.invalidateQueries(['system-status'])
      toast.success('GPS synced successfully!')
    } catch (error) {
      console.error('Failed to sync GPS:', error)
      toast.error(`GPS sync failed: ${error.response?.data?.message || error.message}`)
    } finally {
      setSyncing(false)
    }
  }

  if (statusLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  const latestPhoto = photos?.[0]

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <button
          onClick={handleCapturePhoto}
          disabled={capturing}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
        >
          {capturing ? 'Capturing...' : 'Capture Photo'}
        </button>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* CPU Temperature */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">CPU Temperature</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">
            {status?.cpu_temp ? `${status.cpu_temp.toFixed(1)}°C` : 'N/A'}
          </p>
        </div>

        {/* Disk Space */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Disk Space</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">
            {status?.disk?.free_gb ? `${status.disk.free_gb.toFixed(1)} GB` : 'N/A'}
          </p>
          <p className="text-sm text-gray-500">
            {status?.disk?.used_percent ? `${status.disk.used_percent.toFixed(1)}% used` : ''}
          </p>
        </div>

        {/* Photo Count */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Photos</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">
            {status?.photo_count ?? 'N/A'}
          </p>
        </div>
      </div>

      {/* Hardware Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Hardware Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-500">INA260</p>
            <p className={`font-semibold ${status?.hardware?.ina260_enabled ? 'text-green-600' : 'text-gray-400'}`}>
              {status?.hardware?.ina260_enabled ? 'Enabled' : 'Disabled'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">E-Paper</p>
            <p className={`font-semibold ${status?.hardware?.epaper_enabled ? 'text-green-600' : 'text-gray-400'}`}>
              {status?.hardware?.epaper_enabled ? 'Enabled' : 'Disabled'}
            </p>
          </div>
          {power?.enabled && (
            <div>
              <p className="text-sm text-gray-500">Power</p>
              <p className="font-semibold text-blue-600">
                {power?.power ? `${power.power}W` : 'Monitoring'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* GPS Status Card */}
      {status?.gps?.enabled && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">GPS Status</h3>
            <button
              onClick={handleSyncGPS}
              disabled={syncing}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 text-sm"
            >
              {syncing ? 'Syncing...' : 'Sync Now'}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="flex items-center mb-2">
                <div className={`w-3 h-3 rounded-full mr-2 ${
                  status?.gps?.has_fix ? 'bg-green-500' : 'bg-red-500'
                }`}></div>
                <p className="text-sm font-medium text-gray-700">
                  {status?.gps?.has_fix ? 'GPS Fix Acquired' : 'No GPS Fix'}
                </p>
              </div>

              {status?.gps?.has_fix ? (
                <div className="space-y-1">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Latitude:</span> {status.gps.latitude}
                  </p>
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Longitude:</span> {status.gps.longitude}
                  </p>
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">UTC Offset:</span> {status.gps.utc_offset}h
                  </p>
                </div>
              ) : (
                <p className="text-sm text-gray-500">
                  Click "Sync Now" to acquire GPS position
                </p>
              )}
            </div>

            <div>
              <p className="text-sm text-gray-500 mb-1">Last Sync</p>
              <p className="text-sm font-medium text-gray-900">
                {formatTimestamp(status?.gps?.last_sync)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Latest Photo */}
      {latestPhoto && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Latest Photo</h3>
          <div className="space-y-2">
            <p className="text-sm text-gray-600">{latestPhoto.filename}</p>
            <p className="text-xs text-gray-500">{new Date(latestPhoto.date).toLocaleString()}</p>
          </div>
        </div>
      )}
    </div>
  )
}
