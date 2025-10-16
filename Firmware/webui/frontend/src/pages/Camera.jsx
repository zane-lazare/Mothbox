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
  const [zoomLevel, setZoomLevel] = useState(1.0)  // Digital zoom level (1.0 = no zoom, 4.0 = 4x)
  const [cameraSettings, setCameraSettings] = useState(null)  // HDR and other camera settings
  const socketRef = useRef(null)
  const metadataIntervalRef = useRef(null)
  const debounceTimerRef = useRef(null)  // Task 5: Debounce timer for control updates
  const zoomDebounceTimerRef = useRef(null)  // Debounce timer for zoom updates

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

  // Debounced function to emit zoom updates to backend
  const debouncedEmitZoom = (zoomLevel) => {
    if (zoomDebounceTimerRef.current) {
      clearTimeout(zoomDebounceTimerRef.current)
    }
    zoomDebounceTimerRef.current = setTimeout(() => {
      if (socketRef.current && previewActive) {
        socketRef.current.emit('set_zoom', {
          zoom_level: zoomLevel
        })
        console.log(`Emitting zoom update: ${zoomLevel}x`)
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

    socketRef.current.on('zoom_updated', (data) => {
      if (data.success) {
        console.log('Zoom updated successfully:', data.zoom_level)
      } else {
        console.error('Zoom update failed:', data.error)
        toast.error(`Failed to update zoom: ${data.error}`)
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

  const handleZoomChange = (value) => {
    // Update local state immediately for responsive UI
    setZoomLevel(value)

    // Emit to backend (debounced)
    debouncedEmitZoom(value)
  }

  const handleResetControls = () => {
    const defaults = {
      sharpness: 1.0,
      brightness: 0.0,
      contrast: 1.0,
      saturation: 1.0
    }

    setLiveControls(defaults)
    setZoomLevel(1.0)  // Reset zoom to 1x

    // Emit all resets to backend
    if (socketRef.current && previewActive) {
      Object.entries(defaults).forEach(([key, value]) => {
        // Convert lowercase key to PascalCase (sharpness -> Sharpness)
        const controlName = key.charAt(0).toUpperCase() + key.slice(1)
        socketRef.current.emit('update_preview_control', {
          [controlName]: value
        })
      })
      // Reset zoom
      socketRef.current.emit('set_zoom', { zoom_level: 1.0 })
      toast.success('Controls and zoom reset to defaults')
    }
  }

  return (
    <div className="space-y-2">
      <h2 className="text-2xl font-bold text-gray-900">Camera Control</h2>

      {/* Connection Status */}
      <div className={`px-4 py-2 rounded-lg ${connected ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
        <p className="text-sm">
          WebSocket: {connected ? '✓ Connected' : '✗ Disconnected'}
        </p>
      </div>

      {/* Full-Width Camera Stream with Overlay Controls */}
      <div className="space-y-2">
        {/* Camera Preview with Control Overlays */}
        <div className="bg-white rounded-lg shadow p-3">
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

          <div className="bg-gray-900 rounded-lg overflow-hidden relative" style={{ minHeight: '600px' }}>
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

            {/* Metadata Overlay - Top Right */}
            {previewActive && metadata && !metadata.error && (
              <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg max-w-xs">
                <h4 className="text-sm font-semibold mb-2 text-gray-200">📊 Live Metadata</h4>
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Exposure:</span>
                    <span className="font-semibold text-blue-300">{metadata.exposure_time} µs</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Gain (ISO):</span>
                    <span className="font-semibold text-blue-300">{metadata.analogue_gain}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Focus:</span>
                    <span className="font-semibold text-blue-300">{metadata.lens_position} dpt</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">AF State:</span>
                    <span className="font-semibold text-blue-300">{metadata.af_state}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Color Temp:</span>
                    <span className="font-semibold text-blue-300">{metadata.colour_temperature}K</span>
                  </div>
                </div>
              </div>
            )}

            {/* Live Controls Overlay - Top Left */}
            {previewActive && (
              <div className="absolute top-2 left-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg w-72 max-h-[calc(100vh-200px)] overflow-y-auto">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-sm font-semibold text-gray-200">🎨 Live Controls</h3>
                  <button
                    onClick={handleResetControls}
                    className="px-2 py-1 text-xs bg-white/20 text-white rounded hover:bg-white/30"
                  >
                    Reset
                  </button>
                </div>

                <div className="space-y-3">
                  {/* Sharpness Slider */}
                  <div>
                    <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                      <span>Sharpness</span>
                      <span className="text-blue-300 font-mono">{liveControls.sharpness.toFixed(1)}</span>
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="16"
                      step="0.1"
                      value={liveControls.sharpness}
                      onChange={(e) => handleControlChange('Sharpness', parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>0</span>
                      <span>1.0</span>
                      <span>16</span>
                    </div>
                  </div>

                  {/* Brightness Slider */}
                  <div>
                    <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                      <span>Brightness</span>
                      <span className="text-blue-300 font-mono">{liveControls.brightness.toFixed(1)}</span>
                    </label>
                    <input
                      type="range"
                      min="-1"
                      max="1"
                      step="0.1"
                      value={liveControls.brightness}
                      onChange={(e) => handleControlChange('Brightness', parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>-1</span>
                      <span>0</span>
                      <span>+1</span>
                    </div>
                  </div>

                  {/* Contrast Slider */}
                  <div>
                    <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                      <span>Contrast</span>
                      <span className="text-blue-300 font-mono">{liveControls.contrast.toFixed(1)}</span>
                    </label>
                    <input
                      type="range"
                      min="-1"
                      max="1"
                      step="0.1"
                      value={liveControls.contrast}
                      onChange={(e) => handleControlChange('Contrast', parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>-1</span>
                      <span>1.0</span>
                      <span>+1</span>
                    </div>
                  </div>

                  {/* Saturation Slider */}
                  <div>
                    <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                      <span>Saturation</span>
                      <span className="text-blue-300 font-mono">{liveControls.saturation.toFixed(1)}</span>
                    </label>
                    <input
                      type="range"
                      min="-1"
                      max="1"
                      step="0.1"
                      value={liveControls.saturation}
                      onChange={(e) => handleControlChange('Saturation', parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>-1</span>
                      <span>1.0</span>
                      <span>+1</span>
                    </div>
                  </div>

                  {/* Zoom Slider */}
                  <div className="pt-2 mt-2 border-t border-white/20">
                    <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                      <span>🔍 Digital Zoom</span>
                      <span className="text-green-300 font-mono">{zoomLevel.toFixed(1)}x</span>
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="4"
                      step="0.1"
                      value={zoomLevel}
                      onChange={(e) => handleZoomChange(parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-green-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>1.0x</span>
                      <span>2.5x</span>
                      <span>4.0x</span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 p-2 bg-blue-500/20 border border-blue-400/30 rounded text-[10px] text-blue-200">
                  <strong>💡 Tip:</strong> Changes apply instantly to preview only.
                </div>
              </div>
            )}

            {/* Quick Actions Overlay - Bottom Left */}
            <div className="absolute bottom-2 left-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg w-64">
              <h3 className="text-sm font-semibold text-gray-200 mb-2">⚡ Quick Actions</h3>
              <div className="space-y-2">
                <button
                  onClick={handleAutofocus}
                  disabled={autofocusing || !connected}
                  className="w-full px-3 py-2 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:bg-gray-600 font-medium"
                >
                  {autofocusing ? '🔍 Focusing...' : '🔍 Autofocus'}
                </button>
                <button
                  onClick={handleCalibrate}
                  disabled={calibrating || !connected}
                  className="w-full px-3 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-600 font-medium"
                >
                  {calibrating ? '🔧 Calibrating...' : '🔧 Calibrate'}
                </button>
                <button
                  onClick={handleFreezeSettings}
                  disabled={freezing || !connected}
                  className="w-full px-3 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:bg-gray-600 font-medium"
                >
                  {freezing ? '❄️ Freezing...' : '❄️ Freeze'}
                </button>
              </div>

              {/* Calibration Progress Indicator (Task 4) */}
              {calibrationProgress && (
                <div className="mt-2 p-2 bg-blue-500/20 border border-blue-400/30 rounded">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-medium text-blue-200">
                      Step {calibrationProgress.step}/{calibrationProgress.total_steps}
                    </span>
                    <span className="text-[10px] font-medium text-blue-200">
                      {calibrationProgress.progress}%
                    </span>
                  </div>
                  <div className="w-full bg-blue-300/30 rounded-full h-1.5 mb-1">
                    <div
                      className="bg-blue-400 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${calibrationProgress.progress}%` }}
                    ></div>
                  </div>
                  <p className="text-[10px] text-blue-200">
                    {calibrationProgress.message}
                  </p>
                </div>
              )}

              {/* Action Results */}
              {actionResult && (
                <div className={`mt-2 p-2 rounded border ${
                  actionResult.type === 'success'
                    ? 'bg-green-500/20 border-green-400/30'
                    : 'bg-red-500/20 border-red-400/30'
                }`}>
                  <p className={`text-xs font-semibold ${
                    actionResult.type === 'success' ? 'text-green-200' : 'text-red-200'
                  }`}>
                    {actionResult.title}
                  </p>
                  <p className={`text-[10px] mt-0.5 ${
                    actionResult.type === 'success' ? 'text-green-300' : 'text-red-300'
                  }`}>
                    {actionResult.message}
                  </p>
                </div>
              )}
            </div>

            {/* Settings Transfer Overlay - Bottom Center-Left */}
            <div className="absolute bottom-2 left-72 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg w-56">
              <h3 className="text-sm font-semibold text-gray-200 mb-2">🔄 Settings Transfer</h3>
              <div className="space-y-2">
                <button
                  onClick={handleCopyPreviewToCapture}
                  disabled={copyingSettings || !connected}
                  className="w-full px-3 py-2 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-600 font-medium"
                >
                  {copyingSettings ? 'Copying...' : '📹 Preview → 📷 Capture'}
                </button>
                <button
                  onClick={handleCopyCaptureToPreview}
                  disabled={copyingSettings || !connected}
                  className="w-full px-3 py-2 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-600 font-medium"
                >
                  {copyingSettings ? 'Copying...' : '📷 Capture → 📹 Preview'}
                </button>
              </div>
              <div className="mt-2 p-2 bg-yellow-500/20 border border-yellow-400/30 rounded text-[10px] text-yellow-200">
                <strong>⚠️</strong> Sync settings between preview and capture modes
              </div>
            </div>

            {/* Test Capture Overlay - Bottom Center */}
            <div className="absolute bottom-2 right-80 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg w-60">
              <h3 className="text-sm font-semibold text-gray-200 mb-2">🧪 Test Capture</h3>
              <button
                onClick={handleTestCapture}
                disabled={testCapturing || !connected}
                className="w-full px-3 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:bg-gray-600 font-medium"
              >
                {testCapturing ? '📸 Capturing...' : '🧪 Test Photo'}
              </button>

              {testCaptureResult && (
                <div className={`mt-2 p-2 rounded border ${
                  testCaptureResult.success
                    ? 'bg-green-500/20 border-green-400/30'
                    : 'bg-red-500/20 border-red-400/30'
                }`}>
                  <p className={`text-xs font-semibold ${
                    testCaptureResult.success ? 'text-green-200' : 'text-red-200'
                  }`}>
                    {testCaptureResult.success ? 'Success!' : 'Failed'}
                  </p>
                  {testCaptureResult.success && (
                    <p className="text-[10px] text-green-300 mt-0.5">
                      {testCaptureResult.metadata.exposure_time}µs |
                      {testCaptureResult.metadata.analogue_gain}x |
                      {testCaptureResult.metadata.lens_position}D
                    </p>
                  )}
                  {!testCaptureResult.success && (
                    <p className="text-[10px] text-red-300 mt-0.5">{testCaptureResult.error}</p>
                  )}
                </div>
              )}

              <div className="mt-2 p-2 bg-gray-500/20 border border-gray-400/30 rounded text-[10px] text-gray-300">
                <strong>💡</strong> Test preview settings at full resolution
              </div>
            </div>

            {/* Capture Control Overlay - Bottom Right */}
            <div className="absolute bottom-2 right-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg w-64">
              <h3 className="text-sm font-semibold text-gray-200 mb-2">📷 Capture Control</h3>
              <button
                onClick={handleCapture}
                disabled={capturing}
                className="w-full px-4 py-3 text-base bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-600 font-semibold"
              >
                {capturing ? 'Capturing...' : '📸 Capture Photo'}
              </button>

              {lastCapture && (
                <div className="mt-2 p-2 bg-green-500/20 border border-green-400/30 rounded">
                  <p className="text-xs font-semibold text-green-200">Last capture successful!</p>
                  {lastCapture.latest_photo && (
                    <p className="text-[10px] text-green-300 mt-0.5 truncate">
                      {lastCapture.latest_photo}
                    </p>
                  )}
                </div>
              )}
            </div>

          </div>

          {/* Preview Info & HDR Indicator - Below Stream */}
          <div className="mt-2 flex flex-col sm:flex-row gap-2">
            {previewActive && (
              <div className="flex-1 bg-gray-50 rounded-lg px-3 py-2 border border-gray-200">
                <p className="text-xs text-gray-600">
                  📹 Preview running at ~10 FPS (1024x768) with continuous autofocus
                </p>
              </div>
            )}

            {cameraSettings && (
              <div className="flex-1 bg-purple-50 border border-purple-200 rounded-lg px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-700">🌄 HDR Mode</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    parseInt(cameraSettings.HDR || 1) > 1
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {parseInt(cameraSettings.HDR || 1) === 1
                      ? 'Single'
                      : `${cameraSettings.HDR} Exp HDR`}
                  </span>
                </div>
                {parseInt(cameraSettings.HDR || 1) > 1 && (
                  <p className="mt-1 text-[10px] text-purple-700">
                    Bracket: {cameraSettings.HDR_width || 7000}µs · {cameraSettings.HDR} images
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
