import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getControls, updateControls, getCameraSettings, updateCameraSettings, getSystemInfo, getDiagnosticInfo, getWebUISettings, updateWebUISettings } from '../utils/api'
import { useState, useEffect, useRef } from 'react'
import { io } from 'socket.io-client'
import toast from 'react-hot-toast'

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
      toast.success('Hardware controls updated successfully!')
    },
    onError: (error) => {
      const message = error.response?.data?.error || 'Failed to update controls'
      toast.error(`Error: ${message}`)
    },
  })

  const updateCameraMutation = useMutation({
    mutationFn: updateCameraSettings,
    onSuccess: () => {
      queryClient.invalidateQueries(['camera-settings'])
      toast.success('Camera settings updated successfully!')
    },
    onError: (error) => {
      const message = error.response?.data?.error || 'Failed to update camera settings'
      toast.error(`Error: ${message}`)
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
      toast.success('Stream settings updated successfully! Changes will apply to new stream sessions.')
    },
    onError: (error) => {
      const message = error.response?.data?.error || 'Failed to update stream settings'
      toast.error(`Error: ${message}`)
    },
  })

  const [controlsForm, setControlsForm] = useState({})
  const [cameraForm, setCameraForm] = useState({})
  const [webuiForm, setWebuiForm] = useState({})

  // Initialize forms when data loads - use useEffect to avoid re-render loop
  useEffect(() => {
    if (controls && Object.keys(controlsForm).length === 0) {
      setControlsForm(controls)
    }
  }, [controls, controlsForm])

  useEffect(() => {
    if (cameraSettings && Object.keys(cameraForm).length === 0) {
      setCameraForm(cameraSettings)
    }
  }, [cameraSettings, cameraForm])

  useEffect(() => {
    if (webuiSettings && Object.keys(webuiForm).length === 0) {
      setWebuiForm(webuiSettings)
    }
  }, [webuiSettings, webuiForm])

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
              disabled={updateControlsMutation.isPending}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {updateControlsMutation.isPending ? (
                <>
                  <span className="inline-block animate-spin mr-2">⏳</span>
                  Saving...
                </>
              ) : (
                'Save Controls'
              )}
            </button>
          </form>
        </div>
      )}

      {/* Camera Settings Tab */}
      {activeTab === 'camera' && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Full-Resolution Capture Configuration</h3>
          <p className="text-sm text-gray-600 mb-6">
            These settings control full-resolution photo captures (not preview). Changes take effect on next photo.
          </p>

          <form onSubmit={handleCameraSubmit} className="space-y-6">

            {/* Auto-Calibration Section (Phase 2.1 - Prominent at top) */}
            <div className="p-4 bg-green-50 border-2 border-green-200 rounded-lg">
              <h4 className="text-md font-semibold text-gray-800 mb-3">🔧 Auto-Calibration</h4>
              <p className="text-sm text-gray-600 mb-4">
                Automatically optimize exposure, gain, and focus periodically
              </p>

              <div className="space-y-4">
                {/* Auto-Calibration Enable */}
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={cameraForm.AutoCalibration === '1' || cameraForm.AutoCalibration === 1}
                      onChange={(e) => setCameraForm({...cameraForm, AutoCalibration: e.target.checked ? '1' : '0'})}
                      className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">
                      Enable Auto-Calibration
                    </span>
                  </label>
                </div>

                {/* Auto-Calibration Period */}
                {(cameraForm.AutoCalibration === '1' || cameraForm.AutoCalibration === 1) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Calibration Frequency: Every {cameraForm.AutoCalibrationPeriod || 600} photos
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="1000"
                      value={cameraForm.AutoCalibrationPeriod || 600}
                      onChange={(e) => setCameraForm({ ...cameraForm, AutoCalibrationPeriod: e.target.value })}
                      className="w-full cursor-pointer"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Every photo</span>
                      <span>Every 100</span>
                      <span>Every 1000</span>
                    </div>
                    <p className="mt-2 text-xs text-gray-600">
                      More frequent = better adaptation to changing conditions, but more time spent calibrating
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Exposure Section (Phase 2.1) */}
            <div className="pt-4">
              <h4 className="text-md font-semibold text-gray-800 mb-4">📷 Exposure Settings</h4>

              {/* Exposure Time */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Exposure Time: {cameraForm.ExposureTime || 0} µs
                </label>
                <input
                  type="range"
                  min="100"
                  max="200000"
                  step="100"
                  value={cameraForm.ExposureTime || 499}
                  onChange={(e) => setCameraForm({ ...cameraForm, ExposureTime: e.target.value })}
                  className="w-full cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>100µs (Fast)</span>
                  <span>50ms</span>
                  <span>200ms (Long)</span>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Shorter = less motion blur, Longer = brighter in low light
                </p>
              </div>

              {/* Analogue Gain */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ISO (Analogue Gain): {parseFloat(cameraForm.AnalogueGain || 1).toFixed(1)}x
                </label>
                <input
                  type="range"
                  min="1"
                  max="16"
                  step="0.5"
                  value={cameraForm.AnalogueGain || 8.0}
                  onChange={(e) => setCameraForm({ ...cameraForm, AnalogueGain: e.target.value })}
                  className="w-full cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1x (Clean)</span>
                  <span>8x</span>
                  <span>16x (Noisy)</span>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Higher ISO = brighter but more noise
                </p>
              </div>

              {/* Exposure Value */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Exposure Compensation: {parseFloat(cameraForm.ExposureValue || 0).toFixed(1)} EV
                </label>
                <input
                  type="range"
                  min="-8"
                  max="8"
                  step="0.1"
                  value={cameraForm.ExposureValue || 0.6}
                  onChange={(e) => setCameraForm({ ...cameraForm, ExposureValue: e.target.value })}
                  className="w-full cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>-8 EV (Much darker)</span>
                  <span>0 EV</span>
                  <span>+8 EV (Much brighter)</span>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Adjust auto-exposure bias (positive = brighter, negative = darker)
                </p>
              </div>
            </div>

            {/* HDR/Bracketing Section (Phase 2.1) */}
            <div className="pt-4 mt-4 border-t border-gray-200">
              <h4 className="text-md font-semibold text-gray-800 mb-4">🌄 HDR / Exposure Bracketing</h4>
              <p className="text-sm text-gray-600 mb-4">
                Capture multiple exposures to preserve detail in highlights and shadows
              </p>

              {/* HDR Count */}
              <div className="mb-4">
                <label htmlFor="hdr_count" className="block text-sm font-medium text-gray-700 mb-2">
                  Number of Exposures
                </label>
                <select
                  id="hdr_count"
                  value={cameraForm.HDR || '1'}
                  onChange={(e) => setCameraForm({...cameraForm, HDR: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="1">Single Exposure (No HDR)</option>
                  <option value="3">3 Exposures (Standard HDR)</option>
                  <option value="5">5 Exposures (Extended HDR)</option>
                  <option value="7">7 Exposures (Maximum HDR)</option>
                </select>
                <p className="mt-2 text-xs text-gray-500">
                  More exposures = better dynamic range, but slower capture
                </p>
              </div>

              {/* HDR Bracket Step (only if HDR enabled) */}
              {(parseInt(cameraForm.HDR) > 1) && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Bracket Step: {cameraForm.HDR_width || 7000} µs
                  </label>
                  <input
                    type="range"
                    min="1000"
                    max="50000"
                    step="1000"
                    value={cameraForm.HDR_width || 7000}
                    onChange={(e) => setCameraForm({ ...cameraForm, HDR_width: e.target.value })}
                    className="w-full cursor-pointer"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>1ms (Small steps)</span>
                    <span>25ms</span>
                    <span>50ms (Large steps)</span>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    Distance between exposure times in the bracket
                  </p>
                </div>
              )}
            </div>

            {/* Focus Section (Phase 2.1) */}
            <div className="pt-4 mt-4 border-t border-gray-200">
              <h4 className="text-md font-semibold text-gray-800 mb-4">🎯 Focus Controls</h4>

              {/* Focus Mode */}
              <div className="mb-4">
                <label htmlFor="af_mode_capture" className="block text-sm font-medium text-gray-700 mb-2">
                  Focus Mode
                </label>
                <select
                  id="af_mode_capture"
                  value={cameraForm.AfMode || '0'}
                  onChange={(e) => setCameraForm({...cameraForm, AfMode: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="0">Manual Focus</option>
                  <option value="1">Auto Focus (Single)</option>
                  <option value="2">Auto Focus (Continuous)</option>
                </select>
              </div>

              {/* Lens Position (if manual) */}
              {cameraForm.AfMode === '0' && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Focus Position: {parseFloat(cameraForm.LensPosition || 0.5).toFixed(2)} diopters
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.1"
                    value={cameraForm.LensPosition || 0.5}
                    onChange={(e) => setCameraForm({ ...cameraForm, LensPosition: e.target.value })}
                    className="w-full cursor-pointer"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>0 (Far)</span>
                    <span>5</span>
                    <span>10 (Near)</span>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    Higher values = closer focus distance. Use auto-calibrate to find optimal value.
                  </p>
                </div>
              )}

              {/* Focus Range */}
              <div className="mb-4">
                <label htmlFor="af_range_capture" className="block text-sm font-medium text-gray-700 mb-2">
                  Focus Range
                </label>
                <select
                  id="af_range_capture"
                  value={cameraForm.AfRange || '1'}
                  onChange={(e) => setCameraForm({...cameraForm, AfRange: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="0">Normal (0.5m - infinity)</option>
                  <option value="1">Macro (10cm - 50cm) - For insects</option>
                  <option value="2">Full (10cm - infinity)</option>
                </select>
              </div>

              {/* Focus Speed */}
              <div className="mb-4">
                <label htmlFor="af_speed_capture" className="block text-sm font-medium text-gray-700 mb-2">
                  Focus Speed
                </label>
                <select
                  id="af_speed_capture"
                  value={cameraForm.AfSpeed || '1'}
                  onChange={(e) => setCameraForm({...cameraForm, AfSpeed: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="0">Normal (Accurate)</option>
                  <option value="1">Fast</option>
                </select>
              </div>
            </div>

            {/* Image Format Section (Phase 2.1) */}
            <div className="pt-4 mt-4 border-t border-gray-200">
              <h4 className="text-md font-semibold text-gray-800 mb-4">🖼️ Image Format</h4>

              {/* File Type */}
              <div className="mb-4">
                <label htmlFor="image_file_type" className="block text-sm font-medium text-gray-700 mb-2">
                  File Format
                </label>
                <select
                  id="image_file_type"
                  value={cameraForm.ImageFileType || '0'}
                  onChange={(e) => setCameraForm({...cameraForm, ImageFileType: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="0">JPEG (Fast, compressed) - Recommended</option>
                  <option value="1">PNG (Slow, lossless)</option>
                  <option value="2">BMP (Huge files, very fast)</option>
                </select>
                <p className="mt-2 text-xs text-gray-500">
                  JPEG is best for most uses. PNG preserves all detail but creates much larger files.
                </p>
              </div>

              {/* Vertical Flip */}
              <div className="mb-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={cameraForm.VerticalFlip === '1' || cameraForm.VerticalFlip === 1}
                    onChange={(e) => setCameraForm({...cameraForm, VerticalFlip: e.target.checked ? '1' : '0'})}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm font-medium text-gray-700">
                    Flip Image Vertically
                  </span>
                </label>
                <p className="mt-2 ml-6 text-xs text-gray-500">
                  Enable if camera is mounted upside-down
                </p>
              </div>
            </div>

            {/* Advanced/Other Settings (collapsed by default) */}
            <details className="pt-4 mt-4 border-t border-gray-200">
              <summary className="cursor-pointer text-md font-semibold text-gray-800 mb-4">
                ⚙️ Advanced Settings (Click to expand)
              </summary>
              <div className="mt-4 space-y-4">
                {Object.entries(cameraForm)
                  .filter(([key]) => !['AutoCalibration', 'AutoCalibrationPeriod', 'ExposureTime', 'AnalogueGain',
                    'ExposureValue', 'HDR', 'HDR_width', 'AfMode', 'LensPosition', 'AfRange', 'AfSpeed',
                    'ImageFileType', 'VerticalFlip'].includes(key))
                  .map(([key, value]) => (
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
              </div>
            </details>

            {/* Info Box */}
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800">
                <strong>Note:</strong> These settings affect full-resolution captures only (not preview).
                Use Auto-Calibration to automatically optimize settings, or use the Camera page to manually test focus and exposure.
              </p>
            </div>

            <button
              type="submit"
              disabled={updateCameraMutation.isPending}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {updateCameraMutation.isPending ? (
                <>
                  <span className="inline-block animate-spin mr-2">⏳</span>
                  Saving...
                </>
              ) : (
                'Save Camera Settings'
              )}
            </button>
          </form>
        </div>
      )}

      {/* Stream Settings Tab */}
      {activeTab === 'stream' && (
        <div className="bg-white rounded-lg shadow p-6">
          <style>{`
            /* Slider track styling for better visibility */
            input[type="range"]::-webkit-slider-runnable-track {
              height: 8px;
              border: 1px solid #d1d5db;
              border-radius: 4px;
              background: #e5e7eb;
            }
            input[type="range"]::-moz-range-track {
              height: 8px;
              border: 1px solid #d1d5db;
              border-radius: 4px;
              background: #e5e7eb;
            }
            /* Slider thumb styling for better visibility */
            input[type="range"]::-webkit-slider-thumb {
              -webkit-appearance: none;
              appearance: none;
              width: 20px;
              height: 20px;
              border-radius: 50%;
              background: #3b82f6;
              cursor: pointer;
              border: 2px solid white;
              box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            input[type="range"]::-moz-range-thumb {
              width: 20px;
              height: 20px;
              border-radius: 50%;
              background: #3b82f6;
              cursor: pointer;
              border: 2px solid white;
              box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
          `}</style>
          <h3 className="text-lg font-semibold mb-4">Camera Stream Configuration</h3>
          <p className="text-sm text-gray-600 mb-6">
            Configure the live camera stream quality and performance. Changes apply to new stream sessions.
          </p>

          <form onSubmit={handleWebuiSubmit} className="space-y-6">
            {/* Resolution Preset Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Resolution Preset
              </label>
              <select
                value={`${webuiForm.stream_width}x${webuiForm.stream_height}`}
                onChange={(e) => {
                  const preset = resolutionPresets.find(p => `${p.width}x${p.height}` === e.target.value)
                  if (preset) {
                    setWebuiForm({
                      ...webuiForm,
                      stream_width: preset.width,
                      stream_height: preset.height
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
                Current: {webuiForm.stream_width} x {webuiForm.stream_height}
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
                className="w-full cursor-pointer"
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
                className="w-full cursor-pointer"
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

            {/* Image Quality Controls (Phase 2.1) */}
            <div className="pt-6 mt-6 border-t border-gray-200">
              <h4 className="text-md font-semibold text-gray-800 mb-4">📸 Image Quality</h4>

              {/* Sharpness Slider */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Sharpness: {webuiForm.sharpness !== undefined ? webuiForm.sharpness.toFixed(1) : '1.0'}
                </label>
                <input
                  type="range"
                  min="0"
                  max="4"
                  step="0.1"
                  value={webuiForm.sharpness !== undefined ? webuiForm.sharpness : 1.0}
                  onChange={(e) => setWebuiForm({ ...webuiForm, sharpness: parseFloat(e.target.value) })}
                  className="w-full cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0.0 (Soft)</span>
                  <span>1.0 (Default)</span>
                  <span>4.0 (Sharp)</span>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Increase for more detail, decrease for softer images. 1.0 is the normal setting.
                </p>
              </div>

              {/* Brightness Slider */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Brightness: {webuiForm.brightness !== undefined ? webuiForm.brightness.toFixed(2) : '0.00'}
                </label>
                <input
                  type="range"
                  min="-1"
                  max="1"
                  step="0.05"
                  value={webuiForm.brightness !== undefined ? webuiForm.brightness : 0}
                  onChange={(e) => setWebuiForm({ ...webuiForm, brightness: parseFloat(e.target.value) })}
                  className="w-full cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>-1.0 (Darker)</span>
                  <span>0.0 (Default)</span>
                  <span>+1.0 (Brighter)</span>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Adjust overall image brightness
                </p>
              </div>

              {/* Contrast Slider */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Contrast: {webuiForm.contrast !== undefined ? webuiForm.contrast.toFixed(1) : '1.0'}
                </label>
                <input
                  type="range"
                  min="0"
                  max="4"
                  step="0.1"
                  value={webuiForm.contrast !== undefined ? webuiForm.contrast : 1.0}
                  onChange={(e) => setWebuiForm({ ...webuiForm, contrast: parseFloat(e.target.value) })}
                  className="w-full cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0.0 (Flat)</span>
                  <span>1.0 (Default)</span>
                  <span>4.0 (High)</span>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Adjust difference between light and dark areas. 0.0 = no contrast, 1.0 = normal.
                </p>
              </div>

              {/* Saturation Slider */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Saturation: {webuiForm.saturation !== undefined ? webuiForm.saturation.toFixed(1) : '1.0'}
                </label>
                <input
                  type="range"
                  min="0"
                  max="4"
                  step="0.1"
                  value={webuiForm.saturation !== undefined ? webuiForm.saturation : 1.0}
                  onChange={(e) => setWebuiForm({ ...webuiForm, saturation: parseFloat(e.target.value) })}
                  className="w-full cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0.0 (Grayscale)</span>
                  <span>1.0 (Default)</span>
                  <span>4.0 (Vivid)</span>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Adjust color intensity. 0.0 = grayscale, 1.0 = normal saturation.
                </p>
              </div>
            </div>

            {/* Focus Controls (Phase 2.1) */}
            <div className="pt-6 mt-6 border-t border-gray-200">
              <h4 className="text-md font-semibold text-gray-800 mb-4">🎯 Focus Settings</h4>

              {/* Focus Mode Dropdown */}
              <div className="mb-6">
                <label htmlFor="af_mode" className="block text-sm font-medium text-gray-700 mb-2">
                  Focus Mode
                </label>
                <select
                  id="af_mode"
                  value={webuiForm.af_mode !== undefined ? webuiForm.af_mode : 2}
                  onChange={(e) => setWebuiForm({...webuiForm, af_mode: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="0">Manual Focus</option>
                  <option value="1">Auto Focus (Single)</option>
                  <option value="2">Auto Focus (Continuous) - Recommended</option>
                </select>
                <p className="mt-2 text-xs text-gray-500">
                  Continuous AF keeps subjects in focus automatically
                </p>
              </div>

              {/* Focus Speed Dropdown */}
              <div className="mb-6">
                <label htmlFor="af_speed" className="block text-sm font-medium text-gray-700 mb-2">
                  Focus Speed
                </label>
                <select
                  id="af_speed"
                  value={webuiForm.af_speed !== undefined ? webuiForm.af_speed : 0}
                  onChange={(e) => setWebuiForm({...webuiForm, af_speed: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="0">Normal (Accurate)</option>
                  <option value="1">Fast (May hunt)</option>
                </select>
                <p className="mt-2 text-xs text-gray-500">
                  Normal is more accurate, Fast may cause focus hunting
                </p>
              </div>

              {/* Focus Range Dropdown */}
              <div className="mb-6">
                <label htmlFor="af_range" className="block text-sm font-medium text-gray-700 mb-2">
                  Focus Range
                </label>
                <select
                  id="af_range"
                  value={webuiForm.af_range !== undefined ? webuiForm.af_range : 0}
                  onChange={(e) => setWebuiForm({...webuiForm, af_range: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="0">Normal (0.5m - infinity)</option>
                  <option value="1">Macro (10cm - 50cm)</option>
                  <option value="2">Full (10cm - infinity)</option>
                </select>
                <p className="mt-2 text-xs text-gray-500">
                  Macro mode for close-up insect photography
                </p>
              </div>
            </div>

            {/* Exposure Metering Controls */}
            <div className="pt-6 mt-6 border-t border-gray-200">
              <h4 className="text-md font-semibold text-gray-800 mb-4">📊 Exposure Metering</h4>

              {/* AeMeteringMode Dropdown */}
              <div className="mb-6">
                <label htmlFor="ae_metering_mode" className="block text-sm font-medium text-gray-700 mb-2">
                  Metering Mode
                </label>
                <select
                  id="ae_metering_mode"
                  value={webuiForm.ae_metering_mode !== undefined ? webuiForm.ae_metering_mode : 0}
                  onChange={(e) => setWebuiForm({...webuiForm, ae_metering_mode: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="0">Centre-Weighted</option>
                  <option value="1">Spot</option>
                  <option value="2">Matrix/Average</option>
                </select>
                <p className="mt-2 text-xs text-gray-500">
                  Controls which part of the frame is used for exposure calculation.
                  Centre-Weighted prioritizes the center, Spot uses a small center area only, Matrix evaluates the entire frame.
                </p>
              </div>
            </div>

            {/* White Balance Controls (Phase 2.1) */}
            <div className="pt-6 mt-6 border-t border-gray-200">
              <h4 className="text-md font-semibold text-gray-800 mb-4">🌡️ White Balance</h4>

              {/* AWB Enable Checkbox */}
              <div className="mb-6">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={webuiForm.awb_enable !== undefined ? webuiForm.awb_enable : true}
                    onChange={(e) => setWebuiForm({...webuiForm, awb_enable: e.target.checked})}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm font-medium text-gray-700">
                    Auto White Balance
                  </span>
                </label>
                <p className="mt-2 ml-6 text-xs text-gray-500">
                  Let camera automatically adjust color temperature
                </p>
              </div>

              {/* AWB Mode Dropdown (only if AWB disabled) */}
              {webuiForm.awb_enable === false && (
                <div className="mb-6">
                  <label htmlFor="awb_mode" className="block text-sm font-medium text-gray-700 mb-2">
                    White Balance Preset
                  </label>
                  <select
                    id="awb_mode"
                    value={webuiForm.awb_mode !== undefined ? webuiForm.awb_mode : 0}
                    onChange={(e) => setWebuiForm({...webuiForm, awb_mode: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="0">Auto</option>
                    <option value="1">Incandescent (2800K)</option>
                    <option value="2">Tungsten</option>
                    <option value="3">Fluorescent</option>
                    <option value="4">Indoor</option>
                    <option value="5">Daylight (5600K)</option>
                    <option value="6">Cloudy (6500K)</option>
                    <option value="7">Custom</option>
                  </select>
                  <p className="mt-2 text-xs text-gray-500">
                    Manual white balance for specific lighting conditions
                  </p>
                </div>
              )}
            </div>

            {/* Stream Mode Selection */}
            <div className="pt-6 mt-6 border-t border-gray-200">
              <h4 className="text-md font-semibold text-gray-800 mb-4">⚙️ Encoding</h4>
              <label htmlFor="stream_mode" className="block text-sm font-medium text-gray-700 mb-2">
                Encoding Mode
              </label>
              <select
                id="stream_mode"
                value={webuiForm.stream_mode || 'simplejpeg'}
                onChange={(e) => setWebuiForm({...webuiForm, stream_mode: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="simplejpeg">Fast Software (simplejpeg) - Recommended</option>
                <option value="mjpeg_hardware">Hardware MJPEG (Experimental)</option>
              </select>
              <p className="mt-2 text-xs text-gray-500">
                simplejpeg provides 5-7x faster encoding than PIL. Hardware MJPEG is experimental and may offer lower latency.
              </p>
            </div>

            {/* Info Box */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> Changes will take effect when you start a new stream session.
                If the stream is currently running, stop it and start it again to apply the new settings.
              </p>
            </div>

            <button
              type="submit"
              disabled={updateWebuiMutation.isPending}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {updateWebuiMutation.isPending ? (
                <>
                  <span className="inline-block animate-spin mr-2">⏳</span>
                  Saving...
                </>
              ) : (
                'Save Stream Settings'
              )}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
