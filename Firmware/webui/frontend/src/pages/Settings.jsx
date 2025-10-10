import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getControls, updateControls, getCameraSettings, updateCameraSettings, getSystemInfo, getDiagnosticInfo, getWebUISettings, updateWebUISettings } from '../utils/api'
import { useState, useEffect, useRef } from 'react'
import { io } from 'socket.io-client'

export default function Settings() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('system')
  const socketRef = useRef(null)

  const { data: controls, isLoading: controlsLoading } = useQuery({
    queryKey: ['controls'],
    queryFn: () => getControls().then(res => res.data),
  })

  const { data: cameraSettings, isLoading: cameraLoading } = useQuery({
    queryKey: ['camera-settings'],
    queryFn: () => getCameraSettings().then(res => res.data),
  })

  const { data: webuiSettings, isLoading: webuiLoading } = useQuery({
    queryKey: ['webui-settings'],
    queryFn: () => getWebUISettings().then(res => res.data),
  })

  const { data: systemInfo } = useQuery({
    queryKey: ['system-info'],
    queryFn: () => getSystemInfo().then(res => res.data),
  })

  const { data: diagnosticInfo } = useQuery({
    queryKey: ['diagnostic-info'],
    queryFn: () => getDiagnosticInfo().then(res => res.data),
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

  const updateWebuiMutation = useMutation({
    mutationFn: updateWebUISettings,
    onSuccess: () => {
      queryClient.invalidateQueries(['webui-settings'])
      // Notify backend to reload settings via WebSocket
      if (socketRef.current) {
        socketRef.current.emit('reload_stream_settings')
      }
      alert('Stream settings updated successfully. Changes will apply to new preview sessions.')
    },
  })

  const [controlsForm, setControlsForm] = useState({})
  const [cameraForm, setCameraForm] = useState({})
  const [webuiForm, setWebuiForm] = useState({})

  // Initialize forms when data loads
  if (controls && Object.keys(controlsForm).length === 0) {
    setControlsForm(controls)
  }
  if (cameraSettings && Object.keys(cameraForm).length === 0) {
    setCameraForm(cameraSettings)
  }
  if (webuiSettings && Object.keys(webuiForm).length === 0) {
    setWebuiForm(webuiSettings)
  }

  // Setup WebSocket connection for stream settings reload
  useEffect(() => {
    const wsUrl = `${window.location.protocol}//${window.location.hostname}:${window.location.port || (window.location.protocol === 'https:' ? '443' : '80')}`
    socketRef.current = io(wsUrl, { transports: ['websocket', 'polling'] })

    socketRef.current.on('settings_reloaded', (data) => {
      console.log('Stream settings reloaded:', data)
    })

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect()
      }
    }
  }, [])

  const handleControlsSubmit = (e) => {
    e.preventDefault()
    updateControlsMutation.mutate(controlsForm)
  }

  const handleCameraSubmit = (e) => {
    e.preventDefault()
    updateCameraMutation.mutate(cameraForm)
  }

  const handleWebuiSubmit = (e) => {
    e.preventDefault()
    updateWebuiMutation.mutate(webuiForm)
  }

  // Resolution presets
  const resolutionPresets = [
    { label: '1920x1080 (Full HD)', width: 1920, height: 1080 },
    { label: '1280x720 (HD)', width: 1280, height: 720 },
    { label: '1024x768 (Default)', width: 1024, height: 768 },
    { label: '800x600', width: 800, height: 600 },
    { label: '640x480 (VGA)', width: 640, height: 480 },
  ]

  if (controlsLoading || cameraLoading || webuiLoading) {
    return <div className="text-center py-12">Loading settings...</div>
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Settings</h2>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('system')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'system'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            System Info
          </button>
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
          <button
            onClick={() => setActiveTab('diagnostic')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'diagnostic'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Diagnostic
          </button>
          <button
            onClick={() => setActiveTab('stream')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'stream'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Stream Settings
          </button>
        </nav>
      </div>

      {/* System Info Tab */}
      {activeTab === 'system' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Installation Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Installation Type</p>
                <p className="font-medium capitalize">{systemInfo?.installation_type || 'Loading...'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Firmware Version</p>
                <p className="font-medium">{systemInfo?.firmware_version || 'Loading...'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Mothbox Home</p>
                <p className="font-mono text-xs">{systemInfo?.mothbox_home || 'Loading...'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Config Directory</p>
                <p className="font-mono text-xs">{systemInfo?.config_dir || 'Loading...'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Firmware Directory</p>
                <p className="font-mono text-xs">{systemInfo?.firmware_dir || 'Loading...'}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">GPIO Pin Configuration</h3>
            <p className="text-sm text-gray-600 mb-4">
              Source: <span className="font-medium">{systemInfo?.gpio_source || 'Loading...'}</span>
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-500">Relay Ch1 (Attract Light)</p>
                <p className="font-mono text-lg">{systemInfo?.gpio_pins?.Relay_Ch1 || '?'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Relay Ch2 (Flash)</p>
                <p className="font-mono text-lg">{systemInfo?.gpio_pins?.Relay_Ch2 || '?'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Relay Ch3 (UV Light)</p>
                <p className="font-mono text-lg">{systemInfo?.gpio_pins?.Relay_Ch3 || '?'}</p>
              </div>
            </div>
            {systemInfo?.gpio_source === 'defaults' && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                <p className="text-sm text-yellow-800">
                  ⚠️ Using default GPIO pins. To customize, add Relay_Ch1, Relay_Ch2, and Relay_Ch3 to controls.txt
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Diagnostic Tab */}
      {activeTab === 'diagnostic' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Diagnostic Information</h3>

          <div className="space-y-6">
            <div>
              <h4 className="font-medium mb-2">File Paths</h4>
              <div className="space-y-2 text-sm font-mono">
                {diagnosticInfo?.paths && Object.entries(diagnosticInfo.paths).map(([key, value]) => (
                  <div key={key} className="flex items-start">
                    <span className="text-gray-500 w-48">{key}:</span>
                    <span className={typeof value === 'boolean' ? (value ? 'text-green-600' : 'text-red-600') : ''}>
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-2">Controls File Content</h4>
              <div className="space-y-2 text-sm">
                <p>Raw lines: {diagnosticInfo?.controls_content?.raw_lines || 0}</p>
                <p>Parsed keys: {diagnosticInfo?.controls_content?.parsed_keys?.length || 0}</p>
                <p>Has GPIO pins: {diagnosticInfo?.controls_content?.has_gpio_pins ? '✓ Yes' : '✗ No'}</p>
                <div className="mt-2">
                  <p className="font-medium">Sample values:</p>
                  <div className="font-mono text-xs bg-gray-50 p-2 rounded mt-1">
                    {diagnosticInfo?.controls_content?.sample_values &&
                      Object.entries(diagnosticInfo.controls_content.sample_values).map(([key, value]) => (
                        <div key={key}>{key}: {value}</div>
                      ))
                    }
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-2">Hardware Modules</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {diagnosticInfo?.hardware_config && Object.entries(diagnosticInfo.hardware_config).map(([key, value]) => (
                  key.endsWith('_enabled') && (
                    <div key={key} className="p-2 border rounded">
                      <p className="text-xs text-gray-500">{key.replace('_enabled', '')}</p>
                      <p className={`font-semibold ${value ? 'text-green-600' : 'text-gray-400'}`}>
                        {value ? 'Enabled' : 'Disabled'}
                      </p>
                    </div>
                  )
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

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

      {/* Stream Settings Tab */}
      {activeTab === 'stream' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Camera Stream Configuration</h3>
          <p className="text-sm text-gray-600 mb-6">
            Configure the camera preview stream quality and performance. Changes apply to new preview sessions.
          </p>

          <form onSubmit={handleWebuiSubmit} className="space-y-6">
            {/* Resolution Preset Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Resolution Preset
              </label>
              <select
                value={`${webuiForm.preview_width}x${webuiForm.preview_height}`}
                onChange={(e) => {
                  const preset = resolutionPresets.find(p => `${p.width}x${p.height}` === e.target.value)
                  if (preset) {
                    setWebuiForm({
                      ...webuiForm,
                      preview_width: preset.width,
                      preview_height: preset.height
                    })
                  }
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {resolutionPresets.map((preset) => (
                  <option key={preset.label} value={`${preset.width}x${preset.height}`}>
                    {preset.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Current: {webuiForm.preview_width} x {webuiForm.preview_height}
              </p>
            </div>

            {/* Frame Rate Slider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Frame Rate: {webuiForm.frame_rate} FPS
              </label>
              <input
                type="range"
                min="1"
                max="30"
                value={webuiForm.frame_rate}
                onChange={(e) => setWebuiForm({ ...webuiForm, frame_rate: parseInt(e.target.value) })}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>1 FPS (Slow)</span>
                <span>15 FPS</span>
                <span>30 FPS (Fast)</span>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                Lower frame rates reduce CPU and network usage
              </p>
            </div>

            {/* JPEG Quality Slider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                JPEG Quality: {webuiForm.jpeg_quality}%
              </label>
              <input
                type="range"
                min="50"
                max="100"
                value={webuiForm.jpeg_quality}
                onChange={(e) => setWebuiForm({ ...webuiForm, jpeg_quality: parseInt(e.target.value) })}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>50% (Lower quality, faster)</span>
                <span>75%</span>
                <span>100% (Best quality)</span>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                Higher quality produces sharper images but uses more bandwidth
              </p>
            </div>

            {/* Info Box */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> Changes will take effect when you start a new camera preview session.
                If the preview is currently running, stop it and start it again to apply the new settings.
              </p>
            </div>

            <button
              type="submit"
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
            >
              Save Stream Settings
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
