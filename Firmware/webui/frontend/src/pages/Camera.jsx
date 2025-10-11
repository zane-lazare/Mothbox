import { useState, useEffect, useRef } from 'react'
import { capturePhoto, triggerAutofocus, autoCalibrate, copySettings } from '../utils/api'
import { io } from 'socket.io-client'

export default function Camera() {
  const [capturing, setCapturing] = useState(false)
  const [lastCapture, setLastCapture] = useState(null)
  const [previewActive, setPreviewActive] = useState(false)
  const [currentFrame, setCurrentFrame] = useState(null)
  const [connected, setConnected] = useState(false)
  const [metadata, setMetadata] = useState(null)
  const [autofocusing, setAutofocusing] = useState(false)
  const [calibrating, setCalibrating] = useState(false)
  const [copyingSettings, setCopyingSettings] = useState(false)
  const [actionResult, setActionResult] = useState(null)
  const socketRef = useRef(null)
  const metadataIntervalRef = useRef(null)

  useEffect(() => {
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
      alert('Photo captured successfully!')
    } catch (error) {
      console.error('Capture failed:', error)
      alert('Failed to capture photo')
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
      setActionResult({
        type: 'success',
        title: 'Autofocus Complete',
        message: `Focus locked at ${response.data.lens_position} diopters (${response.data.af_state}) in ${response.data.duration_ms}ms`
      })
    } catch (error) {
      console.error('Autofocus failed:', error)
      setActionResult({
        type: 'error',
        title: 'Autofocus Failed',
        message: error.response?.data?.error || 'Failed to trigger autofocus'
      })
    } finally {
      setAutofocusing(false)
    }
  }

  const handleCalibrate = async () => {
    setCalibrating(true)
    setActionResult(null)
    try {
      const response = await autoCalibrate({
        update_capture: true,
        update_preview: true
      })
      const { before, after } = response.data
      setActionResult({
        type: 'success',
        title: 'Calibration Complete',
        message: `Exposure: ${before.exposure_time}µs → ${after.exposure_time}µs, Gain: ${before.analogue_gain} → ${after.analogue_gain}, Focus: ${before.lens_position} → ${after.lens_position}`
      })
    } catch (error) {
      console.error('Calibration failed:', error)
      setActionResult({
        type: 'error',
        title: 'Calibration Failed',
        message: error.response?.data?.error || 'Failed to calibrate camera'
      })
    } finally {
      setCalibrating(false)
    }
  }

  const handleCopyPreviewToCapture = async () => {
    setCopyingSettings(true)
    setActionResult(null)
    try {
      const response = await copySettings({
        direction: 'preview_to_capture'
      })
      setActionResult({
        type: 'success',
        title: 'Settings Copied',
        message: `Copied ${response.data.copied_count} settings from preview to capture`
      })
    } catch (error) {
      console.error('Copy settings failed:', error)
      setActionResult({
        type: 'error',
        title: 'Copy Failed',
        message: error.response?.data?.error || 'Failed to copy settings'
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
      setActionResult({
        type: 'success',
        title: 'Settings Copied',
        message: `Copied ${response.data.copied_count} settings from capture to preview`
      })
    } catch (error) {
      console.error('Copy settings failed:', error)
      setActionResult({
        type: 'error',
        title: 'Copy Failed',
        message: error.response?.data?.error || 'Failed to copy settings'
      })
    } finally {
      setCopyingSettings(false)
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

        {/* Live Metadata Display (Phase 2.2) */}
        {previewActive && metadata && !metadata.error && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="text-sm font-semibold text-blue-900 mb-3">📊 Live Camera Metadata</h4>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
              <div>
                <p className="text-blue-600 font-medium">Exposure</p>
                <p className="text-blue-900">{metadata.exposure_time} µs</p>
              </div>
              <div>
                <p className="text-blue-600 font-medium">Gain (ISO)</p>
                <p className="text-blue-900">{metadata.analogue_gain}</p>
              </div>
              <div>
                <p className="text-blue-600 font-medium">Focus</p>
                <p className="text-blue-900">{metadata.lens_position} dpt</p>
              </div>
              <div>
                <p className="text-blue-600 font-medium">AF State</p>
                <p className="text-blue-900">{metadata.af_state}</p>
              </div>
              <div>
                <p className="text-blue-600 font-medium">Color Temp</p>
                <p className="text-blue-900">{metadata.colour_temperature}K</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions (Phase 2.2) */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
            onClick={handleCopyPreviewToCapture}
            disabled={copyingSettings || !connected}
            className="px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-400 font-medium"
          >
            {copyingSettings ? '⏳ Copying...' : '📋 Preview → Capture'}
          </button>
        </div>

        <div className="mt-3 p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-600">
            <strong>Autofocus:</strong> Quickly lock focus on the current scene<br/>
            <strong>Calibrate:</strong> Optimize exposure, gain, and focus for current conditions<br/>
            <strong>Preview → Capture:</strong> Copy preview settings to full-resolution capture settings
          </p>
        </div>

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

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

      {/* Capture Controls */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Capture Control</h3>
        <button
          onClick={handleCapture}
          disabled={capturing}
          className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 text-lg font-semibold"
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
  )
}
