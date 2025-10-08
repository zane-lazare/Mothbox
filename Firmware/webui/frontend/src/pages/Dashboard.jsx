import { useQuery } from '@tanstack/react-query'
import { getSystemStatus, getPowerStatus, capturePhoto, getPhotos } from '../utils/api'
import { useState } from 'react'

export default function Dashboard() {
  const [capturing, setCapturing] = useState(false)

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
            <p className="text-sm text-gray-500">GPS</p>
            <p className={`font-semibold ${status?.hardware?.gps_enabled ? 'text-green-600' : 'text-gray-400'}`}>
              {status?.hardware?.gps_enabled ? 'Enabled' : 'Disabled'}
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
