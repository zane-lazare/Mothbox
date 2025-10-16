import { useState, useEffect, useRef } from 'react'
import { capturePhoto, triggerAutofocus, autoCalibrate, copySettings, testCapture, freezeSettings } from '../utils/api'
import { io } from 'socket.io-client'
import toast from 'react-hot-toast'

export default function Camera() {
  const [capturing, setCapturing] = useState(false)
  const [lastCapture, setLastCapture] = useState(null)
  const [previewActive, setPreviewActive] = useState(false)
  const [currentFrame, setCurrentFrame] = useState(null)
  const [connected, setConnected] = useState(false)
  const [metadata, setMetadata] = useState(null)
  const [autofocusing, setAutofocusing] = useState(false)
  const [calibrating, setCalibrating] = useState(false)
  const [freezing, setFreezing] = useState(false)
  const [copyingSettings, setCopyingSettings] = useState(false)
  const [actionResult, setActionResult] = useState(null)
  const [testCapturing, setTestCapturing] = useState(false)
  const [testCaptureResult, setTestCaptureResult] = useState(null)
  const [calibrationProgress, setCalibrationProgress] = useState(null)  // Task 4: Real-time progress
  const [liveControls, setLiveControls] = useState({  // Task 5: Real-time control sliders
    sharpness: 1.0,
    brightness: 0.0,
    contrast: 1.0,
    saturation: 1.0
  })
  const [cameraSettings, setCameraSettings] = useState(null)  // HDR and other camera settings
  const socketRef = useRef(null)
  const metadataIntervalRef = useRef(null)
  const debounceTimerRef = useRef(null)  // Task 5: Debounce timer for control updates

  // Debounced function to emit control updates to backend (Task 5)
  const debouncedEmitControl = (controlName, value) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }
    debounceTimerRef.current = setTimeout(() => {
      if (socketRef.current && previewActive) {
        socketRef.current.emit('update_preview_control', {
          [controlName]: value
        })
        console.log(`Emitting control update: ${controlName}=${value}`)
      }
    }, 150) // 150ms debounce - balances responsiveness vs network usage
  }

  useEffect(() => {
    // Fetch camera settings on mount (for HDR status display)
    const fetchSettings = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const response = await fetch(`${API_URL}/camera/settings`)
        if (response.ok) {
          const data = await response.json()
          setCameraSettings(data)
        }
      } catch (error) {
        console.error('Failed to fetch camera settings:', error)
      }
    }
    fetchSettings()

    // Connect to WebSocket server using current window location
    // This ensures it works whether accessed via localhost, IP, or hostname
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = window.location.port || (window.location.protocol === 'https:' ? '443' : '80')
    const wsUrl = `${window.location.protocol}//${host}:${port}`

    console.log('Connecting to WebSocket at:', wsUrl)

    socketRef.current = io(wsUrl, {
      transports: ['websocket', 'polling']
    })

    socketRef.current.on('connect', () => {
      console.log('WebSocket connected')
      setConnected(true)
    })

    socketRef.current.on('disconnect', () => {
      console.log('WebSocket disconnected')
      setConnected(false)
      setPreviewActive(false)
    })

    socketRef.current.on('camera_frame', (data) => {
      setCurrentFrame(data.image)
    })

    socketRef.current.on('preview_status', (data) => {
      setPreviewActive(data.streaming)
    })

    socketRef.current.on('metadata_update', (data) => {
      setMetadata(data)
    })

    socketRef.current.on('calibration_progress', (data) => {
      console.log('Calibration progress:', data)
      setCalibrationProgress(data)
    })

    socketRef.current.on('control_updated', (data) => {
      if (data.success) {
        console.log('Control updated successfully:', data.control)
      } else {
        console.error('Control update failed:', data.error)
        toast.error(`Failed to update control: ${data.error}`)
      }
    })

    return () => {
      if (socketRef.current) {
        socketRef.current.emit('stop_preview')
        socketRef.current.disconnect()
      }
      if (metadataIntervalRef.current) {
        clearInterval(metadataIntervalRef.current)
      }
    }
  }, [])

  // Poll metadata when preview is active (Phase 2.2)
  useEffect(() => {
    if (previewActive && socketRef.current) {
      // Request metadata every 500ms
      metadataIntervalRef.current = setInterval(() => {
        socketRef.current.emit('get_metadata')
      }, 500)
    } else {
      if (metadataIntervalRef.current) {
        clearInterval(metadataIntervalRef.current)
        metadataIntervalRef.current = null
      }
      setMetadata(null)
    }

    return () => {
      if (metadataIntervalRef.current) {
        clearInterval(metadataIntervalRef.current)
      }
    }
  }, [previewActive])

  const handleCapture = async () => {
    setCapturing(true)
    try {
      const response = await capturePhoto()
      setLastCapture(response.data)

      // Display HDR-aware success message
      if (response.data.hdr_mode) {
        toast.success(
          `HDR capture complete: ${response.data.hdr_count} exposures with ${response.data.hdr_width}µs bracket width`,
          { duration: 5000 }
        )
      } else {
        toast.success('Photo captured successfully!')
      }
    } catch (error) {
      console.error('Capture failed:', error)
      const message = error.response?.data?.error || 'Failed to capture photo'
      toast.error(`Capture failed: ${message}`)
    } finally {
      setCapturing(false)
    }
  }

  const togglePreview = () => {
    if (!socketRef.current) return

    if (previewActive) {
      socketRef.current.emit('stop_preview')
      setCurrentFrame(null)
    } else {
      socketRef.current.emit('start_preview')
    }
  }

  const handleAutofocus = async () => {
    setAutofocusing(true)
    setActionResult(null)
    try {
      const response = await triggerAutofocus()
      const { lens_position, af_state, duration_seconds } = response.data
      toast.success(
        `Autofocus ${af_state}: Locked at ${lens_position}D (${(duration_seconds * 1000).toFixed(0)}ms)`,
        { duration: 4000 }
      )
      setActionResult({
        type: 'success',
        title: 'Autofocus Complete',
        message: `Focus locked at ${lens_position} diopters (${af_state})`
      })
    } catch (error) {
      console.error('Autofocus failed:', error)
      const message = error.response?.data?.error || 'Failed to trigger autofocus'
      toast.error(`Autofocus failed: ${message}`)
      setActionResult({
        type: 'error',
        title: 'Autofocus Failed',
        message
      })
    } finally {
      setAutofocusing(false)
    }
  }

  const handleCalibrate = async () => {
    setCalibrating(true)
    setActionResult(null)
    setCalibrationProgress(null)  // Reset progress at start
    try {
      const response = await autoCalibrate({
        update_capture: true,
        update_preview: true
      })
      const { before, after } = response.data
      toast.success('Camera calibrated successfully!', { duration: 4000 })
      setActionResult({
        type: 'success',
        title: 'Calibration Complete',
        message: `Exposure: ${before.ExposureTime || before.exposure_time}µs → ${after.ExposureTime || after.exposure_time}µs, Gain: ${before.AnalogueGain || before.analogue_gain} → ${after.AnalogueGain || after.analogue_gain}, Focus: ${before.LensPosition || before.lens_position} → ${after.LensPosition || after.lens_position}`
      })
    } catch (error) {
      console.error('Calibration failed:', error)
      const message = error.response?.data?.error || 'Failed to calibrate camera'
      toast.error(`Calibration failed: ${message}`)
      setActionResult({
        type: 'error',
        title: 'Calibration Failed',
        message
      })
    } finally {
      setCalibrating(false)
      // Reset progress after 2s delay (so user sees 100%)
      setTimeout(() => setCalibrationProgress(null), 2000)
    }
  }

  const handleFreezeSettings = async () => {
    setFreezing(true)
    setActionResult(null)
    try {
      const response = await freezeSettings()
      const { frozen_settings } = response.data
      toast.success(`Settings frozen! Exp=${frozen_settings.ExposureTime}µs, Gain=${frozen_settings.AnalogueGain}, Focus=${frozen_settings.LensPosition}D`, { duration: 5000 })
      setActionResult({
        type: 'success',
        title: 'Settings Frozen',
        message: `Locked to: Exp=${frozen_settings.ExposureTime}µs, Gain=${frozen_settings.AnalogueGain}, Focus=${frozen_settings.LensPosition}D. Auto modes disabled.`
      })
    } catch (error) {
      console.error('Freeze failed:', error)
      const message = error.response?.data?.error || 'Failed to freeze settings'
      toast.error(`Freeze failed: ${message}`)
      setActionResult({
        type: 'error',
        title: 'Freeze Failed',
        message
      })
    } finally {
      setFreezing(false)
    }
  }

  const handleCopyPreviewToCapture = async () => {
    setCopyingSettings(true)
    setActionResult(null)
    try {
      const response = await copySettings({
        direction: 'preview_to_capture'
      })
      toast.success(`Copied ${response.data.copied_count} settings from preview to capture`)
      setActionResult({
        type: 'success',
        title: 'Settings Copied',
        message: `Copied ${response.data.copied_count} settings from preview to capture`
      })
    } catch (error) {
      console.error('Copy settings failed:', error)
      const message = error.response?.data?.error || 'Failed to copy settings'
      toast.error(`Copy failed: ${message}`)
      setActionResult({
        type: 'error',
        title: 'Copy Failed',
        message
      })
    } finally {
      setCopyingSettings(false)
    }
  }

  const handleCopyCaptureToPreview = async () => {
    setCopyingSettings(true)
    setActionResult(null)
    try {
      const response = await copySettings({
        direction: 'capture_to_preview'
      })
      toast.success(`Copied ${response.data.copied_count} settings from capture to preview`)
      setActionResult({
        type: 'success',
        title: 'Settings Copied',
        message: `Copied ${response.data.copied_count} settings from capture to preview`
      })
    } catch (error) {
      console.error('Copy settings failed:', error)
      const message = error.response?.data?.error || 'Failed to copy settings'
      toast.error(`Copy failed: ${message}`)
      setActionResult({
        type: 'error',
        title: 'Copy Failed',
        message
      })
    } finally {
      setCopyingSettings(false)
    }
  }

  const handleTestCapture = async () => {
    setTestCapturing(true)
    setTestCaptureResult(null)
    try {
      const response = await testCapture()
      toast.success(`Test photo captured: ${response.data.test_photo_path}`)
      setTestCaptureResult({
        success: true,
        test_photo_path: response.data.test_photo_path,
        metadata: response.data.metadata
      })
    } catch (error) {
      console.error('Test capture failed:', error)
      const message = error.response?.data?.error || 'Failed to capture test photo'
      toast.error(`Test capture failed: ${message}`)
      setTestCaptureResult({
        success: false,
        error: message
      })
    } finally {
      setTestCapturing(false)
    }
  }

  // Task 5: Real-time control slider handlers
  const handleControlChange = (controlName, value) => {
    // Update local state immediately for responsive UI
    const key = controlName.toLowerCase()
    setLiveControls(prev => ({
      ...prev,
      [key]: value
    }))

    // Emit to backend (debounced)
    debouncedEmitControl(controlName, value)
  }

  const handleResetControls = () => {
    const defaults = {
      sharpness: 1.0,
      brightness: 0.0,
      contrast: 1.0,
      saturation: 1.0
    }

    setLiveControls(defaults)

    // Emit all resets to backend
    if (socketRef.current && previewActive) {
      Object.entries(defaults).forEach(([key, value]) => {
        // Convert lowercase key to PascalCase (sharpness -> Sharpness)
        const controlName = key.charAt(0).toUpperCase() + key.slice(1)
        socketRef.current.emit('update_preview_control', {
          [controlName]: value
        })
      })
      toast.success('Controls reset to defaults')
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Camera Control</h2>

      {/* Connection Status */}
      <div className={`px-4 py-2 rounded-lg ${connected ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
        <p className="text-sm">
          WebSocket: {connected ? '✓ Connected' : '✗ Disconnected'}
        </p>
      </div>

      {/* Two-Column Layout: Camera Stream (Left) + Metadata & Controls (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* LEFT COLUMN: Camera Stream */}
        <div className="space-y-6">
          {/* Camera Preview */}
          <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Live Preview</h3>
          <button
            onClick={togglePreview}
            disabled={!connected}
            className={`px-4 py-2 rounded-lg font-medium ${
              previewActive
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-green-600 text-white hover:bg-green-700'
            } disabled:bg-gray-400`}
          >
            {previewActive ? 'Stop Preview' : 'Start Preview'}
          </button>
        </div>

        <div className="bg-gray-900 rounded-lg overflow-hidden" style={{ minHeight: '400px' }}>
          {currentFrame ? (
            <img
              src={currentFrame}
              alt="Camera preview"
              className="w-full h-auto"
            />
          ) : (
            <div className="h-96 flex items-center justify-center">
              <p className="text-gray-400">
                {previewActive ? 'Loading preview...' : 'Click "Start Preview" to begin'}
              </p>
            </div>
          )}
        </div>

        {previewActive && (
          <p className="text-xs text-gray-500 mt-2">
            Preview running at ~10 FPS (1024x768) with continuous autofocus
          </p>
        )}

        {/* HDR Mode Indicator (Feature 11) */}
        {cameraSettings && (
          <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">🌄 HDR Mode</span>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                parseInt(cameraSettings.HDR || 1) > 1
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}>
                {parseInt(cameraSettings.HDR || 1) === 1
                  ? 'Single Exposure'
                  : `${cameraSettings.HDR} Exposures (HDR)`}
              </span>
            </div>
            {parseInt(cameraSettings.HDR || 1) > 1 && (
              <p className="mt-2 text-xs text-purple-700">
                Bracket width: {cameraSettings.HDR_width || 7000}µs · Captures {cameraSettings.HDR} images with different exposures
              </p>
            )}
          </div>
        )}
          </div>
        </div>

        {/* RIGHT COLUMN: Metadata & Controls */}
        <div className="space-y-6">

          {/* Live Metadata Display (Phase 2.2) */}
          {previewActive && metadata && !metadata.error && (
            <div className="bg-white rounded-lg shadow p-6">
              <h4 className="text-lg font-semibold text-gray-900 mb-4">📊 Live Camera Metadata</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-blue-600 font-medium mb-1">Exposure</p>
                  <p className="text-blue-900 text-lg font-semibold">{metadata.exposure_time} µs</p>
                </div>
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-blue-600 font-medium mb-1">Gain (ISO)</p>
                  <p className="text-blue-900 text-lg font-semibold">{metadata.analogue_gain}</p>
                </div>
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-blue-600 font-medium mb-1">Focus</p>
                  <p className="text-blue-900 text-lg font-semibold">{metadata.lens_position} dpt</p>
                </div>
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-blue-600 font-medium mb-1">AF State</p>
                  <p className="text-blue-900 text-lg font-semibold">{metadata.af_state}</p>
                </div>
                <div className="p-3 bg-blue-50 rounded-lg col-span-2">
                  <p className="text-blue-600 font-medium mb-1">Color Temp</p>
                  <p className="text-blue-900 text-lg font-semibold">{metadata.colour_temperature}K</p>
                </div>
              </div>
            </div>
          )}

          {/* Live Controls (Task 5: Real-time Control Sliders) */}
          {previewActive && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">🎨 Live Controls</h3>
                <button
                  onClick={handleResetControls}
                  className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                >
                  Reset to Defaults
                </button>
              </div>

              <p className="text-sm text-gray-600 mb-4">
                Adjust image quality settings in real-time. Changes apply instantly to the preview.
              </p>

              <div className="grid grid-cols-1 gap-4">
                {/* Sharpness Slider */}
                <div>
                  <label className="flex justify-between items-center text-sm font-medium text-gray-700 mb-2">
                    <span>Sharpness</span>
                    <span className="text-blue-600 font-mono">{liveControls.sharpness.toFixed(1)}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="16"
                    step="0.1"
                    value={liveControls.sharpness}
                    onChange={(e) => handleControlChange('Sharpness', parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Soft (0)</span>
                    <span className="font-medium">Default (1.0)</span>
                    <span>Sharp (16)</span>
                  </div>
                </div>

                {/* Brightness Slider */}
                <div>
                  <label className="flex justify-between items-center text-sm font-medium text-gray-700 mb-2">
                    <span>Brightness</span>
                    <span className="text-blue-600 font-mono">{liveControls.brightness.toFixed(1)}</span>
                  </label>
                  <input
                    type="range"
                    min="-1"
                    max="1"
                    step="0.1"
                    value={liveControls.brightness}
                    onChange={(e) => handleControlChange('Brightness', parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Dark (-1)</span>
                    <span className="font-medium">Default (0)</span>
                    <span>Bright (+1)</span>
                  </div>
                </div>

                {/* Contrast Slider */}
                <div>
                  <label className="flex justify-between items-center text-sm font-medium text-gray-700 mb-2">
                    <span>Contrast</span>
                    <span className="text-blue-600 font-mono">{liveControls.contrast.toFixed(1)}</span>
                  </label>
                  <input
                    type="range"
                    min="-1"
                    max="1"
                    step="0.1"
                    value={liveControls.contrast}
                    onChange={(e) => handleControlChange('Contrast', parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Low (-1)</span>
                    <span className="font-medium">Default (1.0)</span>
                    <span>High (+1)</span>
                  </div>
                </div>

                {/* Saturation Slider */}
                <div>
                  <label className="flex justify-between items-center text-sm font-medium text-gray-700 mb-2">
                    <span>Saturation</span>
                    <span className="text-blue-600 font-mono">{liveControls.saturation.toFixed(1)}</span>
                  </label>
                  <input
                    type="range"
                    min="-1"
                    max="1"
                    step="0.1"
                    value={liveControls.saturation}
                    onChange={(e) => handleControlChange('Saturation', parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Gray (-1)</span>
                    <span className="font-medium">Default (1.0)</span>
                    <span>Vivid (+1)</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-800">
                  <strong>💡 Tip:</strong> These controls only affect the live preview. To save settings permanently,
                  adjust them in Settings → Stream Settings, then restart the preview.
                </p>
              </div>
            </div>
          )}

          {/* Quick Actions (Phase 2.2) */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
            <div className="grid grid-cols-1 gap-3">
              <button
                onClick={handleAutofocus}
                disabled={autofocusing || !connected}
                className="px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 font-medium"
              >
                {autofocusing ? '🔍 Focusing...' : '🔍 Trigger Autofocus'}
              </button>
              <button
                onClick={handleCalibrate}
                disabled={calibrating || !connected}
                className="px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 font-medium"
              >
                {calibrating ? '🔧 Calibrating...' : '🔧 Auto-Calibrate'}
              </button>
              <button
                onClick={handleFreezeSettings}
                disabled={freezing || !connected}
                className="px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 font-medium"
              >
                {freezing ? '❄️ Freezing...' : '❄️ Freeze Settings'}
              </button>
            </div>

            <div className="mt-3 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600">
                <strong>Autofocus:</strong> Quickly lock focus on the current scene<br/>
                <strong>Calibrate:</strong> Optimize exposure, gain, and focus for current conditions<br/>
                <strong>Freeze Settings:</strong> Lock current camera values and disable auto-adjustments
              </p>
            </div>

            {/* Calibration Progress Indicator (Task 4) */}
            {calibrationProgress && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-blue-900">
                    Step {calibrationProgress.step} of {calibrationProgress.total_steps}
                  </span>
                  <span className="text-sm font-medium text-blue-900">
                    {calibrationProgress.progress}%
                  </span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2.5 mb-2">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${calibrationProgress.progress}%` }}
                  ></div>
                </div>
                <p className="text-sm text-blue-700">
                  {calibrationProgress.message}
                </p>
              </div>
            )}

            {/* Action Results */}
            {actionResult && (
              <div className={`mt-4 p-4 rounded-lg border-2 ${
                actionResult.type === 'success'
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}>
                <p className={`font-semibold ${
                  actionResult.type === 'success' ? 'text-green-900' : 'text-red-900'
                }`}>
                  {actionResult.title}
                </p>
                <p className={`text-sm mt-1 ${
                  actionResult.type === 'success' ? 'text-green-700' : 'text-red-700'
                }`}>
                  {actionResult.message}
                </p>
              </div>
            )}
          </div>

          {/* Settings Transfer (Phase 2.2) */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Settings Transfer</h3>
            <p className="text-sm text-gray-600 mb-4">
              Mothbox has two separate camera configurations: <strong>Preview</strong> (stream settings)
              and <strong>Capture</strong> (full-resolution photo settings). Use these buttons to synchronize them.
            </p>

            <div className="grid grid-cols-1 gap-4">
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">📹 Preview Settings</h4>
                <p className="text-sm text-blue-700 mb-3">
                  Used for live stream (1024x768, ~10 FPS). Adjust in Settings → Stream Settings tab.
                </p>
                <button
                  onClick={handleCopyPreviewToCapture}
                  disabled={copyingSettings || !connected}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {copyingSettings ? 'Copying...' : 'Copy to Capture →'}
                </button>
              </div>

              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <h4 className="font-semibold text-green-900 mb-2">📷 Capture Settings</h4>
                <p className="text-sm text-green-700 mb-3">
                  Used for full-res photos (4608x2592). Adjust in Settings → Camera Settings tab.
                </p>
                <button
                  onClick={handleCopyCaptureToPreview}
                  disabled={copyingSettings || !connected}
                  className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400"
                >
                  {copyingSettings ? 'Copying...' : '← Copy to Preview'}
                </button>
              </div>
            </div>

            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-xs text-yellow-800">
                <strong>⚠️ Note:</strong> Only compatible settings are copied (sharpness, contrast, saturation, focus mode, white balance, etc.).
                Some settings like resolution and frame rate are specific to each mode.
              </p>
            </div>
          </div>

          {/* Test Capture (Phase 4.5) */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">🧪 Test Capture</h3>
            <p className="text-sm text-gray-600 mb-4">
              Capture a full-resolution test photo using your current <strong>preview settings</strong>.
              This doesn't affect your scheduled capture settings.
            </p>

            <button
              onClick={handleTestCapture}
              disabled={testCapturing || !connected}
              className="w-full px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 font-medium"
            >
              {testCapturing ? '📸 Capturing Test Photo...' : '🧪 Test Capture (Preview Settings)'}
            </button>

            {testCaptureResult && (
              <div className={`mt-4 p-4 rounded-lg border-2 ${
                testCaptureResult.success
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}>
                <p className={`font-semibold ${
                  testCaptureResult.success ? 'text-green-900' : 'text-red-900'
                }`}>
                  {testCaptureResult.success ? 'Test Capture Successful!' : 'Test Capture Failed'}
                </p>
                {testCaptureResult.success && (
                  <>
                    <p className="text-sm text-green-700 mt-1">
                      Photo saved: {testCaptureResult.test_photo_path}
                    </p>
                    <p className="text-xs text-green-600 mt-2">
                      Exposure: {testCaptureResult.metadata.exposure_time}µs |
                      Gain: {testCaptureResult.metadata.analogue_gain} |
                      Focus: {testCaptureResult.metadata.lens_position}D
                    </p>
                  </>
                )}
                {!testCaptureResult.success && (
                  <p className="text-sm text-red-700 mt-1">{testCaptureResult.error}</p>
                )}
              </div>
            )}

            <div className="mt-3 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600">
                <strong>Tip:</strong> Use this to test your preview settings at full resolution
                before copying them to capture settings. Test photos are saved in
                <code className="px-1 bg-gray-200 rounded ml-1">test_captures/</code>
              </p>
            </div>
          </div>

          {/* Capture Controls */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Capture Control</h3>
            <button
              onClick={handleCapture}
              disabled={capturing}
              className="w-full bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 text-lg font-semibold"
            >
              {capturing ? 'Capturing...' : 'Capture Photo'}
            </button>

            {lastCapture && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg">
                <p className="text-green-800 font-medium">Last capture successful!</p>
                {lastCapture.latest_photo && (
                  <p className="text-sm text-green-600 mt-1">
                    Photo: {lastCapture.latest_photo}
                  </p>
                )}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
