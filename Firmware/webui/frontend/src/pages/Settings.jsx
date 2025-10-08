import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getControls, updateControls, getCameraSettings, updateCameraSettings } from '../utils/api'
import { useState } from 'react'

export default function Settings() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('controls')

  const { data: controls, isLoading: controlsLoading } = useQuery({
    queryKey: ['controls'],
    queryFn: () => getControls().then(res => res.data),
  })

  const { data: cameraSettings, isLoading: cameraLoading } = useQuery({
    queryKey: ['camera-settings'],
    queryFn: () => getCameraSettings().then(res => res.data),
  })

  const updateControlsMutation = useMutation({
    mutationFn: updateControls,
    onSuccess: () => {
      queryClient.invalidateQueries(['controls'])
      alert('Controls updated successfully')
    },
  })

  const updateCameraMutation = useMutation({
    mutationFn: updateCameraSettings,
    onSuccess: () => {
      queryClient.invalidateQueries(['camera-settings'])
      alert('Camera settings updated successfully')
    },
  })

  const [controlsForm, setControlsForm] = useState({})
  const [cameraForm, setCameraForm] = useState({})

  // Initialize forms when data loads
  if (controls && Object.keys(controlsForm).length === 0) {
    setControlsForm(controls)
  }
  if (cameraSettings && Object.keys(cameraForm).length === 0) {
    setCameraForm(cameraSettings)
  }

  const handleControlsSubmit = (e) => {
    e.preventDefault()
    updateControlsMutation.mutate(controlsForm)
  }

  const handleCameraSubmit = (e) => {
    e.preventDefault()
    updateCameraMutation.mutate(cameraForm)
  }

  if (controlsLoading || cameraLoading) {
    return <div className="text-center py-12">Loading settings...</div>
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Settings</h2>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('controls')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'controls'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Hardware Controls
          </button>
          <button
            onClick={() => setActiveTab('camera')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'camera'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Camera Settings
          </button>
        </nav>
      </div>

      {/* Controls Tab */}
      {activeTab === 'controls' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Hardware Configuration</h3>
          <form onSubmit={handleControlsSubmit} className="space-y-4">
            {Object.entries(controlsForm).map(([key, value]) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {key}
                </label>
                <input
                  type="text"
                  value={value}
                  onChange={(e) => setControlsForm({ ...controlsForm, [key]: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}
            <button
              type="submit"
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
            >
              Save Controls
            </button>
          </form>
        </div>
      )}

      {/* Camera Settings Tab */}
      {activeTab === 'camera' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Camera Configuration</h3>
          <form onSubmit={handleCameraSubmit} className="space-y-4">
            {Object.entries(cameraForm).map(([key, value]) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {key}
                </label>
                <input
                  type="text"
                  value={value}
                  onChange={(e) => setCameraForm({ ...cameraForm, [key]: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            ))}
            <button
              type="submit"
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
            >
              Save Camera Settings
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
