import { useState, useEffect, useRef } from 'react'
import { capturePhoto, triggerAutofocus, autoCalibrate, copySettings, testCapture, freezeSettings, getPresets, applyPreset, createPreset } from '../utils/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { io } from 'socket.io-client'
import toast from 'react-hot-toast'
import SavePresetModal from '../components/SavePresetModal'

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
    saturation: 1.0,
    aeMeteringMode: 0,
    aeEnable: true,  // Auto exposure enabled by default
    exposureTime: 500,  // Manual exposure time in microseconds
    analogueGain: 8.0,  // Manual gain/ISO
    noiseReductionMode: 0,
    // Focus controls
    afMode: 2,  // 0=Manual, 1=Auto Single, 2=Continuous (default for live preview)
    lensPosition: 3.0,  // Diopters (0.0-10.0, middle position default)
    afRange: 0,  // 0=Normal, 1=Macro, 2=Full
    afSpeed: 0  // 0=Normal, 1=Fast
  })
  const [zoomLevel, setZoomLevel] = useState(1.0)  // Digital zoom level (1.0 = no zoom, 4.0 = 4x)
  const [zoomCenter, setZoomCenter] = useState({ x: 0.5, y: 0.5 })  // Normalized zoom center (0.5, 0.5 = center)
  const [afWindow, setAfWindow] = useState(null)  // AF window: {x, y, active, focusing} or null
  const [cameraSettings, setCameraSettings] = useState(null)  // HDR and other camera settings
  const socketRef = useRef(null)
  const metadataIntervalRef = useRef(null)
  const debounceTimerRef = useRef(null)  // Task 5: Debounce timer for control updates
  const zoomDebounceTimerRef = useRef(null)  // Debounce timer for zoom updates

  // Preset management
  const queryClient = useQueryClient()
  const [selectedPreset, setSelectedPreset] = useState('')
  const [showSaveModal, setShowSaveModal] = useState(false)

  // Fetch available presets
  const { data: presetsData } = useQuery({
    queryKey: ['presets'],
    queryFn: () => getPresets().then(res => res.data),
    staleTime: 30000 // 30 seconds
  })

  // Apply preset mutation
  const applyPresetMutation = useMutation({
    mutationFn: ({ name, applyTo }) => applyPreset(name, applyTo),
    onSuccess: () => {
      queryClient.invalidateQueries(['webuiSettings'])
      queryClient.invalidateQueries(['cameraSettings'])
    }
  })

  // Create preset mutation
  const createPresetMutation = useMutation({
    mutationFn: createPreset,
    onSuccess: () => {
      queryClient.invalidateQueries(['presets'])
    }
  })

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
      }
    }, 150) // 150ms debounce - balances responsiveness vs network usage
  }

  // Debounced function to emit zoom updates to backend
  const debouncedEmitZoom = (zoomLevel, centerX, centerY) => {
    if (zoomDebounceTimerRef.current) {
      clearTimeout(zoomDebounceTimerRef.current)
    }
    zoomDebounceTimerRef.current = setTimeout(() => {
      if (socketRef.current && previewActive) {
        socketRef.current.emit('set_zoom', {
          zoom_level: zoomLevel,
          center_x: centerX,
          center_y: centerY
        })
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

    // Fetch webui settings to initialize live controls with actual values
    const fetchWebuiSettings = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const response = await fetch(`${API_URL}/config/webui`)
        if (response.ok) {
          const data = await response.json()
          // Update live controls with actual settings from backend
          setLiveControls({
            sharpness: data.sharpness !== undefined ? data.sharpness : 1.0,
            brightness: data.brightness !== undefined ? data.brightness : 0.0,
            contrast: data.contrast !== undefined ? data.contrast : 1.0,
            saturation: data.saturation !== undefined ? data.saturation : 1.0,
            noiseReductionMode: data.noise_reduction_mode !== undefined ? data.noise_reduction_mode : 0,
            // Exposure controls - load from backend or use defaults
            aeMeteringMode: data.ae_metering_mode !== undefined ? data.ae_metering_mode : 0,
            aeEnable: data.ae_enable !== undefined ? data.ae_enable : true,
            exposureTime: data.exposure_time !== undefined ? data.exposure_time : 500,
            analogueGain: data.analogue_gain !== undefined ? data.analogue_gain : 8.0,
            // Focus controls - load from backend or use defaults
            afMode: data.af_mode !== undefined ? data.af_mode : 2,  // Default: Continuous AF
            lensPosition: data.lens_position !== undefined ? data.lens_position : 3.0,
            afRange: data.af_range !== undefined ? data.af_range : 0,  // Default: Normal range
            afSpeed: data.af_speed !== undefined ? data.af_speed : 0  // Default: Normal speed
          })
          console.log('Loaded live controls from settings:', data)
        }
      } catch (error) {
        console.error('Failed to fetch webui settings:', error)
      }
    }

    fetchSettings()
    fetchWebuiSettings()

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
      if (!data.success) {
        console.error('Control update failed:', data.error)
        toast.error(`Failed to update control: ${data.error}`)
      }
    })

    socketRef.current.on('zoom_updated', (data) => {
      if (!data.success) {
        console.error('Zoom update failed:', data.error)
        toast.error(`Failed to update zoom: ${data.error}`)
      }
    })

    socketRef.current.on('af_window_updated', (data) => {
      if (data.success) {
        // Update AF window state with animation trigger
        if (data.x !== null && data.y !== null) {
          setAfWindow({
            x: data.x,
            y: data.y,
            active: true,
            focusing: true
          })
          // Auto-dismiss after 3 seconds
          setTimeout(() => {
            setAfWindow(prev => prev ? { ...prev, focusing: false } : null)
          }, 3000)
        } else {
          // Window cleared
          setAfWindow(null)
        }
      } else {
        console.error('AF window update failed:', data.error)
        toast.error(`Failed to update AF window: ${data.error}`)
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

  // Helper: Convert PascalCase control names to camelCase for state keys
  // e.g., 'AeMeteringMode' -> 'aeMeteringMode', 'Sharpness' -> 'sharpness'
  const pascalToCamelCase = (str) => {
    return str.charAt(0).toLowerCase() + str.slice(1)
  }

  // Task 5: Real-time control slider handlers
  const handleControlChange = (controlName, value) => {
    // Convert PascalCase control name to camelCase state key
    // e.g., 'NoiseReductionMode' -> 'noiseReductionMode', 'Sharpness' -> 'sharpness'
    const key = controlName.charAt(0).toLowerCase() + controlName.slice(1)

    // Update local state immediately for responsive UI
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

    // Emit to backend (debounced) with current zoom center
    debouncedEmitZoom(value, zoomCenter.x, zoomCenter.y)
  }

  const handlePreviewClick = (e) => {
    // Only process clicks when zoomed (zoom > 1.0)
    if (zoomLevel <= 1.0 || !previewActive) return

    // Get click position relative to image element
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // Convert to normalized coordinates (0-1)
    const normalizedX = Math.max(0, Math.min(x / rect.width, 1))
    const normalizedY = Math.max(0, Math.min(y / rect.height, 1))

    // Update zoom center state
    setZoomCenter({ x: normalizedX, y: normalizedY })

    // Emit to backend immediately (no debounce for clicks - user expects instant response)
    if (socketRef.current) {
      socketRef.current.emit('set_zoom', {
        zoom_level: zoomLevel,
        center_x: normalizedX,
        center_y: normalizedY
      })
    }
  }

  const handleAfWindowClick = (e) => {
    // Process clicks for AF window when NOT zoomed (zoom = 1.0)
    // This allows click-to-focus without interfering with zoom repositioning
    if (zoomLevel > 1.0 || !previewActive) return

    // Get click position relative to image element
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // Convert to normalized coordinates (0-1)
    const normalizedX = Math.max(0, Math.min(x / rect.width, 1))
    const normalizedY = Math.max(0, Math.min(y / rect.height, 1))

    // Emit AF window update to backend
    if (socketRef.current) {
      socketRef.current.emit('set_af_window', {
        x: normalizedX,
        y: normalizedY,
        window_size: 0.2  // 20% of frame
      })
      toast.success(`Focusing at (${(normalizedX * 100).toFixed(0)}%, ${(normalizedY * 100).toFixed(0)}%)`)
    }
  }

  const handleResetControls = () => {
    const defaults = {
      sharpness: 1.0,
      brightness: 0.0,
      contrast: 1.0,
      saturation: 1.0,
      // Focus control defaults
      afMode: 2,  // Continuous AF
      lensPosition: 3.0,  // Middle position
      afRange: 0,  // Normal range
      afSpeed: 0  // Normal speed
    }

    setLiveControls(prev => ({
      ...prev,
      ...defaults
    }))
    setZoomLevel(1.0)  // Reset zoom to 1x
    setZoomCenter({ x: 0.5, y: 0.5 })  // Reset zoom center to center
    setAfWindow(null)  // Clear AF window

    // Emit all resets to backend
    if (socketRef.current && previewActive) {
      Object.entries(defaults).forEach(([key, value]) => {
        // Convert camelCase key to PascalCase (sharpness -> Sharpness, afMode -> AfMode)
        const controlName = key.charAt(0).toUpperCase() + key.slice(1)
        socketRef.current.emit('update_preview_control', {
          [controlName]: value
        })
      })
      // Reset zoom with centered position
      socketRef.current.emit('set_zoom', {
        zoom_level: 1.0,
        center_x: 0.5,
        center_y: 0.5
      })
      // Clear AF window
      socketRef.current.emit('set_af_window', {
        x: null,
        y: null
      })
      toast.success('Controls, focus, zoom, and AF window reset to defaults')
    }
  }

  const handleApplyPreset = async (presetName) => {
    if (!presetName) {
      return  // Silently ignore empty selection
    }

    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'preview'
      })

      // Find the display name for the toast message
      const preset = presetsData?.presets?.find(p => p.name === presetName)
      const displayName = preset?.display_name || presetName

      toast.success(`Applied "${displayName}" to stream`)

      // Reload webui settings to update live controls
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${API_URL}/config/webui`)
      if (response.ok) {
        const data = await response.json()
        // Update live controls with new preset values
        setLiveControls(prev => ({
          ...prev,
          sharpness: data.sharpness ?? prev.sharpness,
          brightness: data.brightness ?? prev.brightness,
          contrast: data.contrast ?? prev.contrast,
          saturation: data.saturation ?? prev.saturation,
          noiseReductionMode: data.noise_reduction_mode ?? prev.noiseReductionMode,
          aeMeteringMode: data.ae_metering_mode ?? prev.aeMeteringMode,
          afMode: data.af_mode ?? prev.afMode,
          afRange: data.af_range ?? prev.afRange,
          afSpeed: data.af_speed ?? prev.afSpeed
        }))
      }
    } catch (error) {
      console.error('Apply preset failed:', error)
      const message = error.response?.data?.error || 'Failed to apply preset'
      toast.error(`Apply failed: ${message}`)
      // Reset selection on error
      setSelectedPreset('')
    }
  }

  const handleSavePreset = async (presetData) => {
    try {
      await createPresetMutation.mutateAsync(presetData)

      toast.success(`Preset "${presetData.name}" saved successfully`)
      setShowSaveModal(false)
    } catch (error) {
      console.error('Save preset failed:', error)
      const message = error.response?.data?.error || 'Failed to save preset'
      toast.error(`Save failed: ${message}`)
      throw error  // Re-throw so modal can handle it
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
              <>
                <img
                  src={currentFrame}
                  alt="Camera preview"
                  className={`w-full h-auto ${zoomLevel > 1.0 ? 'cursor-crosshair' : 'cursor-pointer'}`}
                  onClick={(e) => {
                    handlePreviewClick(e)
                    handleAfWindowClick(e)
                  }}
                />

                {/* Zoom Center Indicator - Only show when zoomed */}
                {zoomLevel > 1.0 && (
                  <div
                    className="absolute pointer-events-none"
                    style={{
                      left: `${zoomCenter.x * 100}%`,
                      top: `${zoomCenter.y * 100}%`,
                      transform: 'translate(-50%, -50%)'
                    }}
                  >
                    {/* Crosshair */}
                    <div className="relative">
                      {/* Horizontal line */}
                      <div className="absolute w-8 h-0.5 bg-green-400 -left-4 top-1/2 -translate-y-1/2"></div>
                      {/* Vertical line */}
                      <div className="absolute h-8 w-0.5 bg-green-400 -top-4 left-1/2 -translate-x-1/2"></div>
                      {/* Center dot */}
                      <div className="w-2 h-2 bg-green-400 rounded-full border-2 border-gray-900"></div>
                    </div>
                  </div>
                )}

                {/* AF Window Indicator - Show when AF window is active */}
                {afWindow && afWindow.active && (
                  <div
                    className="absolute pointer-events-none"
                    style={{
                      left: `${afWindow.x * 100}%`,
                      top: `${afWindow.y * 100}%`,
                      transform: 'translate(-50%, -50%)',
                      width: '20%',
                      height: '20%'
                    }}
                  >
                    {/* Animated focus box */}
                    <div className={`relative w-full h-full ${afWindow.focusing ? 'animate-pulse' : ''}`}>
                      {/* Focus box border */}
                      <div className="absolute inset-0 border-2 border-yellow-400 rounded">
                        {/* Corner indicators */}
                        <div className="absolute -top-1 -left-1 w-4 h-4 border-t-4 border-l-4 border-yellow-400"></div>
                        <div className="absolute -top-1 -right-1 w-4 h-4 border-t-4 border-r-4 border-yellow-400"></div>
                        <div className="absolute -bottom-1 -left-1 w-4 h-4 border-b-4 border-l-4 border-yellow-400"></div>
                        <div className="absolute -bottom-1 -right-1 w-4 h-4 border-b-4 border-r-4 border-yellow-400"></div>
                      </div>
                      {/* Center cross */}
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                        <div className="w-6 h-0.5 bg-yellow-400"></div>
                        <div className="w-0.5 h-6 bg-yellow-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"></div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="h-96 flex items-center justify-center">
                <p className="text-gray-400">
                  {previewActive ? 'Loading preview...' : 'Click "Start Preview" to begin'}
                </p>
              </div>
            )}

            {/* Metadata Overlay - Top Right */}
            {previewActive && metadata && !metadata.error && (
              <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg max-w-sm">
                <h4 className="text-sm font-semibold text-gray-200 mb-2">📊 Live Metadata</h4>

                {/* Primary Metadata (Always Visible) */}
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Exposure:</span>
                    <span className="font-semibold text-blue-300">
                      {metadata.exposure_time}µs/{liveControls.aeEnable ? 'Auto' : 'Man.'}
                    </span>
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

                {/* Extended Metadata (Collapsible) */}
                <details className="mt-2">
                  <summary className="text-xs cursor-pointer text-gray-300 hover:text-white select-none">
                    More Details ▼
                  </summary>
                  <div className="space-y-1.5 text-xs mt-2 pt-2 border-t border-gray-600">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Digital Gain:</span>
                      <span className="text-blue-300">{metadata.digital_gain}x</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Focus FoM:</span>
                      <span className="text-blue-300">{metadata.focus_fom}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Sensor Time:</span>
                      <span className="text-blue-300">{metadata.sensor_timestamp} µs</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Colour Gains:</span>
                      <span className="text-blue-300">
                        R:{metadata.colour_gains?.[0] ?? 0} B:{metadata.colour_gains?.[1] ?? 0}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Frame Duration:</span>
                      <span className="text-blue-300">{metadata.frame_duration} µs</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Black Level:</span>
                      <span className="text-blue-300">{metadata.sensor_black_level}</span>
                    </div>
                    {metadata.sensor_temperature !== null && metadata.sensor_temperature !== undefined && (
                      <div className="flex justify-between items-center">
                        <span className="text-gray-300">Sensor Temp:</span>
                        <span className="text-blue-300">{metadata.sensor_temperature}°C</span>
                      </div>
                    )}
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Scaler Crop:</span>
                      <span className="text-blue-300 text-[10px]">
                        {metadata.scaler_crop?.[0]},{metadata.scaler_crop?.[1]} {metadata.scaler_crop?.[2]}x{metadata.scaler_crop?.[3]}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">AE Lock:</span>
                      <span className={metadata.ae_locked ? "text-yellow-300" : "text-green-300"}>
                        {metadata.ae_locked ? "Locked" : "Auto"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">AWB Lock:</span>
                      <span className={metadata.awb_locked ? "text-yellow-300" : "text-green-300"}>
                        {metadata.awb_locked ? "Locked" : "Auto"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Lux:</span>
                      <span className="text-blue-300">{metadata.lux}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Saturation:</span>
                      <span className="text-blue-300">{metadata.saturation}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Contrast:</span>
                      <span className="text-blue-300">{metadata.contrast}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Sharpness:</span>
                      <span className="text-blue-300">{metadata.sharpness}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Brightness:</span>
                      <span className="text-blue-300">{metadata.brightness}</span>
                    </div>
                  </div>
                </details>
              </div>
            )}

            {/* Live Controls Overlay - Top Left */}
            {previewActive && (
              <div className="absolute top-2 left-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg w-72 max-h-[calc(100vh-200px)] overflow-y-auto">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-sm font-semibold text-gray-200">🎨 Live Controls</h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowSaveModal(true)}
                      className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      💾 Save
                    </button>
                    <button
                      onClick={handleResetControls}
                      className="px-2 py-1 text-xs bg-white/20 text-white rounded hover:bg-white/30"
                    >
                      Reset
                    </button>
                  </div>
                </div>

                {/* Quick Presets Selector */}
                <div className="mb-3 pb-3 border-b border-white/20">
                  <label className="block text-xs font-medium text-gray-200 mb-2">
                    📋 Quick Presets {applyPresetMutation.isPending && <span className="text-blue-300">(applying...)</span>}
                  </label>
                  <select
                    value={selectedPreset}
                    onChange={(e) => {
                      const newValue = e.target.value
                      setSelectedPreset(newValue)
                      handleApplyPreset(newValue)
                    }}
                    disabled={applyPresetMutation.isPending}
                    className="w-full px-2 py-1 text-xs bg-white/10 text-white rounded border border-white/20 hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <option value="">Select preset...</option>
                    {presetsData?.presets?.map((preset) => (
                      <option key={preset.name} value={preset.name}>
                        {preset.display_name}
                      </option>
                    ))}
                  </select>
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
                      max="4"
                      step="0.1"
                      value={liveControls.sharpness}
                      onChange={(e) => handleControlChange('Sharpness', parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>0</span>
                      <span>1.0</span>
                      <span>4</span>
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
                      min="0"
                      max="4"
                      step="0.1"
                      value={liveControls.contrast}
                      onChange={(e) => handleControlChange('Contrast', parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>0</span>
                      <span>1.0</span>
                      <span>4</span>
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
                      min="0"
                      max="4"
                      step="0.1"
                      value={liveControls.saturation}
                      onChange={(e) => handleControlChange('Saturation', parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>0</span>
                      <span>1.0</span>
                      <span>4</span>
                    </div>
                  </div>

                  {/* Exposure Mode Toggle */}
                  <div className="pt-2 mt-2 border-t border-white/20">
                    <label className="block text-xs font-medium text-gray-200 mb-1">
                      💡 Exposure Mode
                    </label>
                    <select
                      value={liveControls.aeEnable ? 'true' : 'false'}
                      onChange={(e) => {
                        const newValue = e.target.value === 'true'
                        setLiveControls(prev => ({ ...prev, aeEnable: newValue }))
                        handleControlChange('AeEnable', newValue)
                      }}
                      className="w-full px-2 py-1.5 text-xs bg-white/10 text-white border border-white/20 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="true" className="bg-gray-800">✨ Auto Exposure</option>
                      <option value="false" className="bg-gray-800">🔧 Manual Exposure</option>
                    </select>
                    <div className="mt-1 text-[10px] text-gray-300">
                      {liveControls.aeEnable ? 'Camera adjusts exposure automatically' : 'Using fixed exposure settings'}
                    </div>
                  </div>

                  {/* Manual Exposure Controls - Show only when Manual mode */}
                  {!liveControls.aeEnable && (
                    <>
                      {/* Exposure Time Slider */}
                      <div className="pt-2 mt-2">
                        <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                          <span>⏱️ Exposure Time</span>
                          <span className="text-orange-300 font-mono">{liveControls.exposureTime} µs</span>
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="1"
                          value={(() => {
                            // Convert exposure time to logarithmic slider position (base-2)
                            const exposure = liveControls.exposureTime || 500
                            const minLog = Math.log2(100)      // ~6.64
                            const maxLog = Math.log2(200000)   // ~17.61
                            const logValue = Math.log2(Math.max(100, Math.min(200000, exposure)))
                            return Math.round(((logValue - minLog) / (maxLog - minLog)) * 100)
                          })()}
                          onChange={(e) => {
                            // Convert logarithmic slider position to exposure time (base-2)
                            const sliderValue = parseInt(e.target.value)
                            const minLog = Math.log2(100)
                            const maxLog = Math.log2(200000)
                            const logValue = minLog + (sliderValue / 100) * (maxLog - minLog)
                            const exposureTime = Math.round(Math.pow(2, logValue))
                            setLiveControls(prev => ({ ...prev, exposureTime: exposureTime }))
                            handleControlChange('ExposureTime', exposureTime)
                          }}
                          className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-orange-500"
                        />
                        <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                          <span>100µs</span>
                          <span>3ms</span>
                          <span>200ms</span>
                        </div>
                      </div>

                      {/* Analogue Gain Slider */}
                      <div className="pt-2 mt-2">
                        <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                          <span>📈 Gain (ISO)</span>
                          <span className="text-orange-300 font-mono">{liveControls.analogueGain.toFixed(1)}x</span>
                        </label>
                        <input
                          type="range"
                          min="1"
                          max="16"
                          step="0.5"
                          value={liveControls.analogueGain}
                          onChange={(e) => {
                            const newValue = parseFloat(e.target.value)
                            setLiveControls(prev => ({ ...prev, analogueGain: newValue }))
                            handleControlChange('AnalogueGain', newValue)
                          }}
                          className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-orange-500"
                        />
                        <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                          <span>1x</span>
                          <span>8x</span>
                          <span>16x</span>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Exposure Metering Mode Dropdown - Only show in Auto mode */}
                  {liveControls.aeEnable && (
                    <div className="pt-2 mt-2 border-t border-white/20">
                      <label className="block text-xs font-medium text-gray-200 mb-1">
                        📊 Metering Mode
                      </label>
                      <select
                        value={liveControls.aeMeteringMode}
                        onChange={(e) => handleControlChange('AeMeteringMode', parseInt(e.target.value))}
                        className="w-full px-2 py-1.5 text-xs bg-white/10 text-white border border-white/20 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="0" className="bg-gray-800">Centre-Weighted</option>
                        <option value="1" className="bg-gray-800">Spot</option>
                        <option value="2" className="bg-gray-800">Matrix/Average</option>
                      </select>
                      <div className="mt-1 text-[10px] text-gray-300">
                        {liveControls.aeMeteringMode === 0 && '⚪ Centre: Prioritizes center of frame'}
                        {liveControls.aeMeteringMode === 1 && '🎯 Spot: Uses small center area only'}
                        {liveControls.aeMeteringMode === 2 && '🌐 Matrix: Evaluates entire frame'}
                      </div>
                    </div>
                  )}

                  {/* Focus Controls Section */}
                  <div className="pt-2 mt-2 border-t border-white/20">
                    <label className="block text-xs font-medium text-gray-200 mb-1">
                      🎯 Focus Mode
                    </label>
                    <select
                      value={liveControls.afMode}
                      onChange={(e) => {
                        const newValue = parseInt(e.target.value)
                        setLiveControls(prev => ({ ...prev, afMode: newValue }))
                        handleControlChange('AfMode', newValue)
                      }}
                      className="w-full px-2 py-1.5 text-xs bg-white/10 text-white border border-white/20 rounded focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                    >
                      <option value="0" className="bg-gray-800">🔧 Manual Focus</option>
                      <option value="1" className="bg-gray-800">🎯 Auto Single (One-shot)</option>
                      <option value="2" className="bg-gray-800">♾️ Continuous AF</option>
                    </select>
                    <div className="mt-1 text-[10px] text-gray-300">
                      {liveControls.afMode === 0 && '🔧 Manual: Full control via slider'}
                      {liveControls.afMode === 1 && '🎯 Single: One-time focus cycle'}
                      {liveControls.afMode === 2 && '♾️ Continuous: Auto-maintains focus'}
                    </div>
                  </div>

                  {/* Manual Focus Slider - Only show when Manual mode */}
                  {liveControls.afMode === 0 && (
                    <div className="pt-2 mt-2">
                      <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                        <span>🔍 Lens Position</span>
                        <span className="text-orange-300 font-mono">{liveControls.lensPosition.toFixed(1)} dpt</span>
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="10"
                        step="0.1"
                        value={liveControls.lensPosition}
                        onChange={(e) => {
                          const newValue = parseFloat(e.target.value)
                          setLiveControls(prev => ({ ...prev, lensPosition: newValue }))
                          handleControlChange('LensPosition', newValue)
                        }}
                        className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-orange-500"
                      />
                      <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                        <span>∞ Far (0.0)</span>
                        <span>5.0</span>
                        <span>Close (10.0)</span>
                      </div>
                    </div>
                  )}

                  {/* AF Range - Only show in Auto modes */}
                  {(liveControls.afMode === 1 || liveControls.afMode === 2) && (
                    <div className="pt-2 mt-2">
                      <label className="block text-xs font-medium text-gray-200 mb-1">
                        📏 AF Range
                      </label>
                      <select
                        value={liveControls.afRange}
                        onChange={(e) => handleControlChange('AfRange', parseInt(e.target.value))}
                        className="w-full px-2 py-1.5 text-xs bg-white/10 text-white border border-white/20 rounded focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                      >
                        <option value="0" className="bg-gray-800">Normal (0.5m - ∞)</option>
                        <option value="1" className="bg-gray-800">Macro (10cm - 50cm)</option>
                        <option value="2" className="bg-gray-800">Full (10cm - ∞)</option>
                      </select>
                      <div className="mt-1 text-[10px] text-gray-300">
                        {liveControls.afRange === 0 && '📐 Normal: General purpose (0.5m+)'}
                        {liveControls.afRange === 1 && '🐛 Macro: Close-up insects (10-50cm)'}
                        {liveControls.afRange === 2 && '🌍 Full: Maximum range (10cm+)'}
                      </div>
                    </div>
                  )}

                  {/* AF Speed - Only show in Auto modes */}
                  {(liveControls.afMode === 1 || liveControls.afMode === 2) && (
                    <div className="pt-2 mt-2">
                      <label className="block text-xs font-medium text-gray-200 mb-1">
                        ⚡ AF Speed
                      </label>
                      <select
                        value={liveControls.afSpeed}
                        onChange={(e) => handleControlChange('AfSpeed', parseInt(e.target.value))}
                        className="w-full px-2 py-1.5 text-xs bg-white/10 text-white border border-white/20 rounded focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                      >
                        <option value="0" className="bg-gray-800">Normal (Accurate)</option>
                        <option value="1" className="bg-gray-800">Fast (May hunt)</option>
                      </select>
                      <div className="mt-1 text-[10px] text-gray-300">
                        {liveControls.afSpeed === 0 && '🎯 Normal: Accurate, slower'}
                        {liveControls.afSpeed === 1 && '⚡ Fast: Quick but may hunt'}
                      </div>
                    </div>
                  )}

                  {/* Noise Reduction Mode Dropdown */}
                  <div className="pt-2 mt-2 border-t border-white/20">
                    <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                      <span>Noise Reduction</span>
                      <span className="text-blue-300 font-mono">
                        {liveControls.noiseReductionMode === 0 ? 'Off' :
                         liveControls.noiseReductionMode === 1 ? 'Fast' : 'High Quality'}
                      </span>
                    </label>
                    <select
                      value={liveControls.noiseReductionMode}
                      onChange={(e) => handleControlChange('NoiseReductionMode', parseInt(e.target.value))}
                      className="w-full px-2 py-1.5 bg-white/20 text-white text-xs rounded border border-white/30 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="0">Off</option>
                      <option value="1">Fast</option>
                      <option value="2">High Quality</option>
                    </select>
                    <p className="mt-1 text-[10px] text-gray-400">
                      Critical for night insect photography
                    </p>
                  </div>

                  {/* ISP Features (Phase: ISP Tuning) */}

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
                    {zoomLevel > 1.0 && (
                      <div className="mt-1 text-[10px] text-green-300">
                        🎯 Click on preview to reposition zoom
                      </div>
                    )}
                  </div>

                  {/* AF Window Indicator */}
                  <div className="pt-2 mt-2 border-t border-white/20">
                    <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                      <span>🎯 Click-to-Focus</span>
                      {afWindow && afWindow.active ? (
                        <span className="text-yellow-300 font-mono text-[10px]">
                          Active ({(afWindow.x * 100).toFixed(0)}%, {(afWindow.y * 100).toFixed(0)}%)
                        </span>
                      ) : (
                        <span className="text-gray-400 font-mono text-[10px]">Ready</span>
                      )}
                    </label>
                    <div className="text-[10px] text-gray-300 mt-1">
                      {afWindow && afWindow.active ? (
                        <div className="flex items-center justify-between">
                          <span className="text-yellow-300">✓ AF window set</span>
                          <button
                            onClick={() => {
                              if (socketRef.current) {
                                socketRef.current.emit('set_af_window', { x: null, y: null })
                                setAfWindow(null)
                                toast.success('AF window cleared')
                              }
                            }}
                            className="px-2 py-0.5 text-[10px] bg-white/20 text-white rounded hover:bg-white/30"
                          >
                            Clear
                          </button>
                        </div>
                      ) : (
                        <span>Click on preview to set focus region</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-3 p-2 bg-blue-500/20 border border-blue-400/30 rounded text-[10px] text-blue-200">
                  <strong>💡 Tip:</strong> Changes apply instantly to preview only. Click preview to focus on specific area.
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

      {/* Save Preset Modal */}
      <SavePresetModal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        onSave={handleSavePreset}
        isSaving={createPresetMutation.isPending}
      />
    </div>
  )
}
