import { useState, useEffect, useRef } from 'react'
import { capturePhoto, triggerAutofocus, autoCalibrate, copySettings, testCaptureLiveview, freezeSettings, getPresets, applyPreset, createPreset, getPreferences, setPreference, updateWebuiSettings } from '../utils/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import { io } from 'socket.io-client'
import toast from 'react-hot-toast'
import SavePresetModal from '../components/SavePresetModal'
import { convertFromBackend, toPicameraControl } from '../utils/cameraControlMapping'

/**
 * Field list constants for API response validation
 *
 * These constants define which fields to validate in different contexts.
 * Different API endpoints and workflows expose different subsets of settings.
 *
 * Field Categories:
 * - BASIC_SETTINGS_FIELDS: Core image quality settings (sharpness, brightness, contrast, saturation)
 * - CAMERA_CONTROL_FIELDS: Camera mode/behavior settings (noise reduction, metering, AF modes)
 * - AE_FIELDS: Auto-exposure enable flag (used when AE state is relevant)
 * - MANUAL_CONTROL_FIELDS: Manual exposure/focus values (exposure_time, gain, lens_position)
 *
 * Validation Strategy by Context:
 *
 * 1. settings_reloaded event (SSE):
 *    - Validates: BASIC + CAMERA_CONTROL + AE_FIELDS
 *    - Rationale: Cross-page settings updates include AE state but not manual control values
 *
 * 2. preview start settings refresh:
 *    - Validates: BASIC + CAMERA_CONTROL + AE_FIELDS + MANUAL_CONTROL_FIELDS
 *    - Rationale: Live preview needs all settings including manual controls for UI consistency
 *
 * 3. preset initialization:
 *    - Validates: BASIC + CAMERA_CONTROL (no AE_FIELDS or MANUAL_CONTROL_FIELDS)
 *    - Rationale: Preset application focuses on core settings, manual values handled separately
 *
 * 4. settings update after preset:
 *    - Validates: BASIC + CAMERA_CONTROL (no AE_FIELDS or MANUAL_CONTROL_FIELDS)
 *    - Rationale: Same as preset initialization - core settings only
 *
 * Why different field lists?
 * - Not all API endpoints return the same fields
 * - Manual control values are only relevant during live preview
 * - Validating unused fields would create false warnings
 * - This approach makes validation intent explicit and maintainable
 */
const BASIC_SETTINGS_FIELDS = ['sharpness', 'brightness', 'contrast', 'saturation']
const CAMERA_CONTROL_FIELDS = ['noise_reduction_mode', 'ae_metering_mode', 'af_mode', 'af_range', 'af_speed']
const AE_FIELDS = ['ae_enable']
const MANUAL_CONTROL_FIELDS = ['exposure_time', 'analogue_gain', 'lens_position']

/**
 * Validates API response has expected fields, warns in dev mode if missing.
 * Helps debug silent fallback issues where missing API fields use previous values.
 *
 * @param {object} data - API response data
 * @param {string[]} expectedFields - Array of expected field names
 * @param {string} context - Description of where this validation is happening
 * @returns {object} - Same data object (for chaining)
 */
const validateApiResponse = (data, expectedFields, context = 'API response') => {
  if (import.meta.env.DEV) {
    const missing = expectedFields.filter(field => data[field] === undefined)
    if (missing.length > 0) {
      console.warn(
        `[${context}] Missing fields in API response:`,
        missing.join(', '),
        '\n→ Falling back to previous values for these fields'
      )
    }
  }
  return data
}

export default function Camera() {
  const [capturing, setCapturing] = useState(false)
  const [lastCapture, setLastCapture] = useState(null)
  const [liveViewActive, setLiveViewActive] = useState(false)
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
  const [calibrationProgress, setCalibrationProgress] = useState(null)
  const [liveControls, setLiveControls] = useState({
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
    afMode: 2,  // 0=Manual, 1=Auto Single, 2=Continuous (default for live view)
    lensPosition: 3.0,  // Diopters (0.0-10.0, middle position default)
    afRange: 0,  // 0=Normal, 1=Macro, 2=Full
    afSpeed: 0,  // 0=Normal, 1=Fast
    // White balance / Colour gains
    colourGainRed: 2.259,  // Red channel gain (1.0-4.0)
    colourGainBlue: 1.500,  // Blue channel gain (1.0-4.0)
    // Focus peaking controls (live view-only overlay)
    focusPeakingEnabled: false,
    focusPeakingIntensity: 100,  // 50-200 range
    focusPeakingColour: 'green',  // green, red, yellow, cyan, magenta
    focusPeakingAlgorithm: 'laplacian'  // laplacian, sobel, canny
  })
  const [zoomLevel, setZoomLevel] = useState(1.0)  // Digital zoom level (1.0 = no zoom, 4.0 = 4x)
  const [zoomCenter, setZoomCenter] = useState({ x: 0.5, y: 0.5 })  // Normalized zoom center (0.5, 0.5 = center)
  const [afWindow, setAfWindow] = useState(null)  // AF window: {x, y, active, focusing} or null - also serves as visual indicator for area of interest
  const [cameraSettings, setCameraSettings] = useState(null)  // HDR and other camera settings
  const socketRef = useRef(null)
  const metadataIntervalRef = useRef(null)
  const debounceTimerRef = useRef(null)
  const zoomDebounceTimerRef = useRef(null)  // Debounce timer for zoom updates

  // Preset management
  const queryClient = useQueryClient()
  const [selectedPhotoPreset, setSelectedPhotoPreset] = useState('')
  const [selectedLiveViewPreset, setSelectedLiveViewPreset] = useState('')
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveModalWorkflow, setSaveModalWorkflow] = useState('both')

  // Track whether presets have been initialized (to prevent toast spam on mount)
  const photoPresetInitialized = useRef(false)
  const liveViewPresetInitialized = useRef(false)

  // Fetch available presets
  const { data: presetsData } = useQuery({
    queryKey: QUERY_KEYS.PRESETS,
    queryFn: () => getPresets().then(res => res.data),
    staleTime: 30000 // 30 seconds
  })

  // Fetch user preferences
  const { data: preferences } = useQuery({
    queryKey: QUERY_KEYS.PREFERENCES,
    queryFn: () => getPreferences().then(res => res.data),
  })

  // Apply preset mutation
  const applyPresetMutation = useMutation({
    mutationFn: ({ name, applyTo }) => applyPreset(name, applyTo),
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
      queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)
    }
  })

  // Create preset mutation
  const createPresetMutation = useMutation({
    mutationFn: createPreset,
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.PRESETS)
    }
  })

  // Update webui settings mutation
  const updateWebuiMutation = useMutation({
    mutationFn: updateWebuiSettings,
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
    },
    onError: (error) => {
      const message = error.response?.data?.error || 'Failed to update stream settings'
      toast.error(`Error: ${message}`)
    }
  })

  // Filter presets by workflow
  const photoPresets = presetsData?.presets?.filter(p => p.workflow === 'photo' || p.workflow === 'both') || []
  const liveViewPresets = presetsData?.presets?.filter(p => p.workflow === 'liveview' || p.workflow === 'both') || []

  // Load default photo preset from preferences on mount
  useEffect(() => {
    if (presetsData?.presets && preferences !== undefined && !photoPresetInitialized.current && !selectedPhotoPreset) {
      const defaultPreset = preferences?.default_capture_preset || 'Balanced'
      const presetExists = presetsData.presets.some(p =>
        p.name === defaultPreset && (p.workflow === 'photo' || p.workflow === 'both')
      )
      if (presetExists) {
        setSelectedPhotoPreset(defaultPreset)
        initializePhotoPreset(defaultPreset)
        photoPresetInitialized.current = true
      }
    }
  }, [presetsData, preferences, selectedPhotoPreset])

  // Load default liveview preset from preferences on mount
  useEffect(() => {
    if (presetsData?.presets && preferences !== undefined && !liveViewPresetInitialized.current && !selectedLiveViewPreset) {
      const defaultPreset = preferences?.default_liveview_preset || 'Balanced'
      const presetExists = presetsData.presets.some(p =>
        p.name === defaultPreset && (p.workflow === 'liveview' || p.workflow === 'both')
      )
      if (presetExists) {
        initializeLiveViewPreset(defaultPreset).then(() => {
          setSelectedLiveViewPreset(defaultPreset)
          liveViewPresetInitialized.current = true
        }).catch((error) => {
          console.error('Failed to initialize liveview preset:', error)
          liveViewPresetInitialized.current = false
          const preset = presetsData?.presets?.find(p => p.name === defaultPreset)
          const displayName = preset?.display_name || defaultPreset
          const message = error.response?.data?.error || 'Failed to load preset'
          toast.error(`Preset "${displayName}" failed to load: ${message}`)
        })
      }
    }
  }, [presetsData, preferences, selectedLiveViewPreset])

  // Debounced function to emit control updates to backend
  const debouncedEmitControl = (controlName, value) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }
    debounceTimerRef.current = setTimeout(() => {
      if (socketRef.current && liveViewActive) {
        socketRef.current.emit('update_liveview_control', {
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
      if (socketRef.current && liveViewActive) {
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

          // Use centralized mapping from cameraControlMapping.js
          // This eliminates manual snake_case → camelCase conversion
          const frontendControls = convertFromBackend(data)

          // Apply defaults for missing fields
          const defaultControls = {
            sharpness: 1.0,
            brightness: 0.0,
            contrast: 1.0,
            saturation: 1.0,
            noiseReductionMode: 0,
            aeMeteringMode: 0,
            aeEnable: true,
            exposureTime: 500,
            analogueGain: 8.0,
            afMode: 2,  // Default: Continuous AF
            lensPosition: 3.0,
            afRange: 0,  // Default: Normal range
            afSpeed: 0,  // Default: Normal speed
            colourGainRed: 2.259,
            colourGainBlue: 1.500
          }

          // Update live controls with merged defaults and backend data
          setLiveControls({
            ...defaultControls,
            ...frontendControls
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
      setLiveViewActive(false)
    })

    socketRef.current.on('camera_frame', (data) => {
      setCurrentFrame(data.image)
    })

    socketRef.current.on('liveview_status', (data) => {
      setLiveViewActive(data.streaming)
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

    socketRef.current.on('settings_reloaded', async (data) => {
      console.log('Settings reloaded, refreshing live controls:', data)
      try {
        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const response = await fetch(`${API_URL}/config/webui`)
        if (response.ok) {
          const data = await response.json()
          // Validate basic settings + camera controls + AE enable
          const validatedData = validateApiResponse(data, [
            ...BASIC_SETTINGS_FIELDS,
            ...CAMERA_CONTROL_FIELDS,
            ...AE_FIELDS
          ], 'settings_reloaded event')

          setLiveControls(prev => ({
            ...prev,
            sharpness: validatedData.sharpness ?? prev.sharpness,
            brightness: validatedData.brightness ?? prev.brightness,
            contrast: validatedData.contrast ?? prev.contrast,
            saturation: validatedData.saturation ?? prev.saturation,
            noiseReductionMode: validatedData.noise_reduction_mode ?? prev.noiseReductionMode,
            aeMeteringMode: validatedData.ae_metering_mode ?? prev.aeMeteringMode,
            aeEnable: validatedData.ae_enable ?? prev.aeEnable,
            afMode: validatedData.af_mode ?? prev.afMode,
            afRange: validatedData.af_range ?? prev.afRange,
            afSpeed: validatedData.af_speed ?? prev.afSpeed
          }))
          // No toast - this event fires on preview start too, not just cross-page updates
        }
      } catch (error) {
        console.error('Failed to refresh settings after settings_reloaded event:', error)
      }
    })

    return () => {
      if (socketRef.current) {
        socketRef.current.emit('stop_liveview')
        socketRef.current.disconnect()
      }
      if (metadataIntervalRef.current) {
        clearInterval(metadataIntervalRef.current)
      }
    }
  }, [])

  // Poll metadata when preview is active
  useEffect(() => {
    if (liveViewActive && socketRef.current) {
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
  }, [liveViewActive])

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

  const toggleLiveView = async () => {
    if (!socketRef.current) return

    if (liveViewActive) {
      socketRef.current.emit('stop_liveview')
      setCurrentFrame(null)
    } else {
      // Fetch latest settings and reload backend before starting preview
      try {
        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const response = await fetch(`${API_URL}/config/webui`)
        if (response.ok) {
          const data = await response.json()
          // Validate all settings including manual controls for live preview
          const validatedData = validateApiResponse(data, [
            ...BASIC_SETTINGS_FIELDS,
            ...CAMERA_CONTROL_FIELDS,
            ...AE_FIELDS,
            ...MANUAL_CONTROL_FIELDS
          ], 'preview start settings refresh')

          setLiveControls(prev => ({
            ...prev,
            sharpness: validatedData.sharpness ?? prev.sharpness,
            brightness: validatedData.brightness ?? prev.brightness,
            contrast: validatedData.contrast ?? prev.contrast,
            saturation: validatedData.saturation ?? prev.saturation,
            noiseReductionMode: validatedData.noise_reduction_mode ?? prev.noiseReductionMode,
            aeMeteringMode: validatedData.ae_metering_mode ?? prev.aeMeteringMode,
            aeEnable: validatedData.ae_enable ?? prev.aeEnable,
            exposureTime: validatedData.exposure_time ?? prev.exposureTime,
            analogueGain: validatedData.analogue_gain ?? prev.analogueGain,
            afMode: validatedData.af_mode ?? prev.afMode,
            lensPosition: validatedData.lens_position ?? prev.lensPosition,
            afRange: validatedData.af_range ?? prev.afRange,
            afSpeed: validatedData.af_speed ?? prev.afSpeed
          }))
          console.log('Refreshed live controls from backend before preview start')

          // Tell backend to reload settings from file before starting stream
          // This ensures backend CameraStreamer uses fresh settings, not cached values
          console.log('Requesting backend to reload settings before preview start')
          await new Promise((resolve) => {
            let isResolved = false
            const timeoutMs = 1000

            const handleReloaded = (data) => {
              if (isResolved) return
              isResolved = true
              clearTimeout(timeoutId)
              socketRef.current.off('settings_reloaded', handleReloaded)

              // Check if backend reported error during reload
              if (data && data.success === false) {
                console.warn(
                  `[${new Date().toISOString()}] Backend settings reload failed:`,
                  data.error,
                  `| Socket connected: ${socketRef.current?.connected}`
                )
                toast.error(`Settings reload failed: ${data.error}. Stream may use cached settings.`, { duration: 5000 })
              } else {
                console.log('Backend settings reloaded successfully:', data)
              }

              resolve()  // Always resolve to allow stream start (degraded mode)
            }

            const timeoutId = setTimeout(() => {
              if (isResolved) return
              isResolved = true
              socketRef.current.off('settings_reloaded', handleReloaded)

              console.error(
                `[${new Date().toISOString()}] Settings reload timed out after ${timeoutMs}ms`,
                `| Socket connected: ${socketRef.current?.connected}`
              )
              toast.error(`Settings reload timed out. Stream will use cached settings.`, { duration: 5000 })

              resolve()  // Resolve even on timeout (degraded mode)
            }, timeoutMs)

            // Check socket connection before emitting
            if (!socketRef.current?.connected) {
              clearTimeout(timeoutId)
              console.error(
                `[${new Date().toISOString()}] Cannot reload settings: WebSocket not connected`
              )
              toast.error('WebSocket disconnected. Cannot reload settings.', { duration: 5000 })
              resolve()  // Continue anyway
              return
            }

            socketRef.current.once('settings_reloaded', handleReloaded)
            socketRef.current.emit('reload_stream_settings')
          })

          console.log('Backend settings reload completed, starting preview')
        }
      } catch (error) {
        console.error('Failed to refresh settings before preview start:', error)
      }

      socketRef.current.emit('start_liveview')
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

  const handleCopyLiveViewToCapture = async () => {
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

  const handleCopyCaptureToLiveView = async () => {
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
      const response = await testCaptureLiveview()
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

  // Real-time control slider handlers
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

  /**
   * Handle zoom level changes from the slider control.
   *
   * State Management:
   * - zoomLevel: Current zoom magnification (1.0 = no zoom, 4.0 = 4x digital zoom)
   * - zoomCenter: Default center position for zoom operations (0-1 normalized)
   * - afWindow: User's last clicked "area of interest" (persists across zoom levels)
   *
   * Zoom Center Priority:
   * 1. If afWindow is set (user clicked): zoom centers on clicked point
   * 2. Otherwise: zoom centers on zoomCenter state (default 0.5, 0.5)
   *
   * This provides intuitive workflow:
   * - User clicks on subject at 1.0x → afWindow set to click position
   * - User drags zoom slider to 2.0x → zoom centers on clicked subject
   * - User resets to 1.0x → zoomCenter resets to (0.5, 0.5), but afWindow persists
   * - User zooms to 3.0x again → still centers on original click position
   *
   * The afWindow serves triple purpose:
   * - Visual marker: Shows yellow "area of interest" box on screen
   * - Autofocus target: Directs hardware AF to focus on this region
   * - Zoom anchor: Subsequent zoom operations center on this point
   *
   * State Synchronization (see also: handleImageClick line 708):
   * - When user clicks, BOTH zoomCenter and afWindow are updated simultaneously
   * - This ensures zoom slider always has correct coordinates to use
   * - afWindow takes priority in this function for backward compatibility
   *
   * @param {number} value - New zoom level (1.0 to 4.0)
   */
  const handleZoomChange = (value) => {
    // Update local state immediately for responsive UI
    setZoomLevel(value)

    // If zooming back to 1.0x, reset zoom center but KEEP AF window
    // AF window persists across zoom levels to maintain area of interest
    if (value === 1.0) {
      setZoomCenter({ x: 0.5, y: 0.5 })
      // Note: afWindow state is NOT cleared - it persists to show continued focus region
    }

    // Determine zoom center: prioritize afWindow (area of interest marker) if set
    // This ensures zoom centers on the marker position
    // Since handleImageClick (line 708) now updates zoomCenter on every click,
    // both afWindow and zoomCenter should have the same value, but we check
    // afWindow first for backward compatibility and explicitness
    const centerX = afWindow?.x ?? zoomCenter.x
    const centerY = afWindow?.y ?? zoomCenter.y

    // Emit to backend (debounced) with area of interest position
    debouncedEmitZoom(value, centerX, centerY)
  }

  const handleImageClick = (e) => {
    // Unified handler: Sets BOTH zoom center AND AF window to create a single "area of interest"
    // Works at ALL zoom levels - clicking defines both where to zoom and where to focus
    if (!liveViewActive) return

    // Get click position relative to image element
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // Convert to normalized coordinates (0-1) in VIEWPORT space
    const viewportX = Math.max(0, Math.min(x / rect.width, 1))
    const viewportY = Math.max(0, Math.min(y / rect.height, 1))

    // ========================================
    // Forward Coordinate Transformation: Viewport → Sensor
    // ========================================
    // This is the INVERSE of the marker rendering transformation (line 1010)
    //
    // Derivation:
    //   At zoom=1.0: viewport (0-1) = full sensor (0-1) [identity transform]
    //   At zoom>1.0: viewport (0-1) = cropped region of sensor
    //
    //   Crop properties:
    //     - Center: (currentCenterX, currentCenterY) in sensor space
    //     - Size: cropFraction of full sensor (e.g., 0.5 at 2x zoom means 50% visible)
    //
    //   Viewport range [0, 1] maps to sensor range [center - size/2, center + size/2]
    //
    //   Mathematical derivation:
    //     viewportPos ranges from 0 to 1
    //     We want to map this to [center - fraction/2, center + fraction/2]
    //
    //     Linear mapping: output = a * input + b
    //     At viewportPos=0: sensorPos = center - fraction/2
    //     At viewportPos=1: sensorPos = center + fraction/2
    //
    //     Setting up equations:
    //       center - fraction/2 = a * 0 + b  →  b = center - fraction/2
    //       center + fraction/2 = a * 1 + b  →  a = (center + fraction/2) - b = fraction
    //
    //     Therefore: sensorPos = fraction * viewportPos + (center - fraction/2)
    //                          = fraction * viewportPos + center - fraction/2
    //                          = center + fraction * (viewportPos - 0.5)
    //
    //   Final formula: sensorPos = currentCenter + (viewportPos - 0.5) * cropFraction
    //
    //   Why (viewportPos - 0.5)? It centers the mapping:
    //     viewportPos=0.0 → sensor = center - 0.5*fraction (left edge of visible region)
    //     viewportPos=0.5 → sensor = center (center of visible region)
    //     viewportPos=1.0 → sensor = center + 0.5*fraction (right edge of visible region)
    //
    // Inverse formula (marker rendering, line 1078):
    //   viewportPos = (sensorPos - currentCenter) / cropFraction + 0.5
    //
    // See also:
    //   - Marker rendering (line 1010): Inverse transformation (sensor → viewport)
    //   - websocket_handlers.py (line 235): Backend metadata emission
    //   - calculate_scaler_crop() in liveview_stream.py: Crop calculation

    let sensorX, sensorY

    if (zoomLevel > 1.0) {
      // When zoomed: Transform from viewport space to sensor space
      // The displayed image shows only a fraction of the full sensor
      // We need to map the click from "what's visible" to "full sensor coordinates"

      // Get current crop center from metadata (where the crop is actually centered)
      // Falls back to zoomCenter if metadata not available yet
      const currentCenterX = metadata?.actual_zoom_center_x ?? zoomCenter.x
      const currentCenterY = metadata?.actual_zoom_center_y ?? zoomCenter.y

      // Calculate how much of the sensor is currently visible
      // Use actual crop fractions from backend (handles aspect ratio preservation)
      // When sensor and output have different aspect ratios (e.g., 4:3 sensor → 16:9 output),
      // the crop fractions will be asymmetric (X and Y different)
      const cropFractionX = metadata?.crop_fraction_x ?? (1.0 / zoomLevel)
      const cropFractionY = metadata?.crop_fraction_y ?? (1.0 / zoomLevel)

      // Transform click from viewport space to sensor space
      // Formula: sensorPos = currentCenter + (clickInViewport - 0.5) * cropFraction
      // Example: 2x zoom at center (0.5, 0.5), click right edge of viewport (1.0)
      //   With symmetric crop (16:9 → 16:9): sensor_x = 0.5 + (1.0 - 0.5) * 0.5 = 0.75
      //   With asymmetric crop (4:3 → 16:9): sensor_x = 0.5 + (1.0 - 0.5) * 0.667 = 0.833
      sensorX = currentCenterX + (viewportX - 0.5) * cropFractionX
      sensorY = currentCenterY + (viewportY - 0.5) * cropFractionY
    } else {
      // At 1.0x zoom: Viewport coordinates = sensor coordinates (no transformation needed)
      sensorX = viewportX
      sensorY = viewportY
    }

    // Clamp to valid sensor range (0-1)
    const clampedX = Math.max(0, Math.min(sensorX, 1))
    const clampedY = Math.max(0, Math.min(sensorY, 1))

    // Update local state
    // Always update zoom center - clicking sets both AF window AND future zoom center
    // This ensures zoom slider will center on the most recent clicked position
    // (at 1.0x, no crop shift occurs, but zoom center is prepared for when user zooms)
    setZoomCenter({ x: clampedX, y: clampedY })

    // Always update AF window (focus works at all zoom levels)
    setAfWindow({
      x: clampedX,  // Use sensor coordinates for AF window position
      y: clampedY,
      active: true,
      focusing: true  // Trigger focusing animation
    })

    // Emit to backend
    if (socketRef.current) {
      // Only emit set_zoom when zoomed > 1.0x (don't shift crop at 1.0x)
      // At 1.0x, the full sensor view should be shown without any crop shift
      if (zoomLevel > 1.0) {
        socketRef.current.emit('set_zoom', {
          zoom_level: zoomLevel,
          center_x: clampedX,
          center_y: clampedY
        })
      }

      // Always set AF window (hardware autofocus region)
      socketRef.current.emit('set_af_window', {
        x: clampedX,
        y: clampedY,
        window_size: 0.2  // 20% of frame
      })

      toast.success(`Area of interest: (${(clampedX * 100).toFixed(0)}%, ${(clampedY * 100).toFixed(0)}%)`)
    }

    // Auto-stop focusing animation after 3 seconds (but keep box visible)
    setTimeout(() => {
      setAfWindow(prev => prev ? { ...prev, focusing: false } : null)
    }, 3000)
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
      afSpeed: 0,  // Normal speed
      // Colour balance defaults
      colourGainRed: 2.259,
      colourGainBlue: 1.500
    }

    setLiveControls(prev => ({
      ...prev,
      ...defaults
    }))
    setZoomLevel(1.0)  // Reset zoom to 1x
    setZoomCenter({ x: 0.5, y: 0.5 })  // Reset zoom center to center
    setCrosshairPos({ x: 0.5, y: 0.5 })  // Reset crosshair to center
    setAfWindow(null)  // Clear AF window

    // Emit all resets to backend
    if (socketRef.current && liveViewActive) {
      Object.entries(defaults).forEach(([key, value]) => {
        // Convert camelCase key to PascalCase (sharpness -> Sharpness, afMode -> AfMode)
        const controlName = key.charAt(0).toUpperCase() + key.slice(1)
        socketRef.current.emit('update_liveview_control', {
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

  // Silent initialization for photo preset (no toast)
  const initializePhotoPreset = async (presetName) => {
    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'capture'
      })
      console.log(`Initialized photo preset: ${presetName}`)
    } catch (error) {
      console.error('Failed to initialize photo preset:', error)
      const preset = presetsData?.presets?.find(p => p.name === presetName)
      const displayName = preset?.display_name || presetName
      const message = error.response?.data?.error || 'Failed to load preset'
      toast.error(`Preset "${displayName}" failed to load: ${message}`)
    }
  }

  const handleApplyPhotoPreset = async (presetName) => {
    if (!presetName) {
      return  // Silently ignore empty selection
    }

    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'capture'
      })

      const preset = presetsData?.presets?.find(p => p.name === presetName)
      const displayName = preset?.display_name || presetName
      // Only show toast after initialization
      if (photoPresetInitialized.current) {
        toast.success(`Applied "${displayName}" to capture settings`)
      }
    } catch (error) {
      console.error('Apply photo preset failed:', error)
      const message = error.response?.data?.error || 'Failed to apply preset'
      toast.error(`Apply failed: ${message}`)
      setSelectedPhotoPreset('')
    }
  }

  // Silent initialization for video preset (no toast)
  const initializeLiveViewPreset = async (presetName) => {
    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'liveview'
      })

      // Reload webui settings to update live controls
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${API_URL}/config/webui`)
      if (response.ok) {
        const data = await response.json()
        // Validate basic settings + camera controls (no manual fields for preset init)
        const validatedData = validateApiResponse(data, [
          ...BASIC_SETTINGS_FIELDS,
          ...CAMERA_CONTROL_FIELDS
        ], 'preset initialization')

        setLiveControls(prev => ({
          ...prev,
          sharpness: validatedData.sharpness ?? prev.sharpness,
          brightness: validatedData.brightness ?? prev.brightness,
          contrast: validatedData.contrast ?? prev.contrast,
          saturation: validatedData.saturation ?? prev.saturation,
          noiseReductionMode: validatedData.noise_reduction_mode ?? prev.noiseReductionMode,
          aeMeteringMode: validatedData.ae_metering_mode ?? prev.aeMeteringMode,
          afMode: validatedData.af_mode ?? prev.afMode,
          afRange: validatedData.af_range ?? prev.afRange,
          afSpeed: validatedData.af_speed ?? prev.afSpeed
        }))
      }
      console.log(`Initialized video preset: ${presetName}`)
    } catch (error) {
      console.error('Failed to initialize video preset:', error)
      liveViewPresetInitialized.current = false
      throw error // Re-throw to allow caller to handle
    }
  }

  const handleApplyLiveViewPreset = async (presetName) => {
    if (!presetName) {
      return  // Silently ignore empty selection
    }

    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'liveview'
      })

      const preset = presetsData?.presets?.find(p => p.name === presetName)
      const displayName = preset?.display_name || presetName
      // Only show toast after initialization
      if (liveViewPresetInitialized.current) {
        toast.success(`Applied "${displayName}" to stream`)
      }

      // Reload webui settings to update live controls
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${API_URL}/config/webui`)
      if (response.ok) {
        const data = await response.json()
        // Validate basic settings + camera controls (no manual fields after preset)
        const validatedData = validateApiResponse(data, [
          ...BASIC_SETTINGS_FIELDS,
          ...CAMERA_CONTROL_FIELDS
        ], 'settings update after preset')

        // Update live controls with new preset values
        setLiveControls(prev => ({
          ...prev,
          sharpness: validatedData.sharpness ?? prev.sharpness,
          brightness: validatedData.brightness ?? prev.brightness,
          contrast: validatedData.contrast ?? prev.contrast,
          saturation: validatedData.saturation ?? prev.saturation,
          noiseReductionMode: validatedData.noise_reduction_mode ?? prev.noiseReductionMode,
          aeMeteringMode: validatedData.ae_metering_mode ?? prev.aeMeteringMode,
          afMode: validatedData.af_mode ?? prev.afMode,
          afRange: validatedData.af_range ?? prev.afRange,
          afSpeed: validatedData.af_speed ?? prev.afSpeed
        }))
      }
    } catch (error) {
      console.error('Apply video preset failed:', error)
      const message = error.response?.data?.error || 'Failed to apply preset'
      toast.error(`Apply failed: ${message}`)
      throw error // Re-throw to allow caller to handle state
    }
  }

  const handleUpdateLiveViewPreset = async () => {
    if (!selectedLiveViewPreset) return

    // Check if this is a built-in preset
    const preset = presetsData?.presets?.find(p => p.name === selectedLiveViewPreset)
    if (preset?.category === 'built-in') {
      toast.error('Cannot modify built-in presets. Use "Save As" to create a copy.')
      return
    }

    try {
      // Fetch complete current settings from backend (includes all 24+ fields)
      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${API_URL}/config/webui`)
      if (!response.ok) {
        throw new Error('Failed to fetch complete settings')
      }
      const completeSettings = await response.json()

      // Merge UI-controlled values into complete settings
      // This preserves stream config, exposure, white balance, ISP, focus peaking, etc.
      const mergedSettings = {
        ...completeSettings,
        sharpness: liveControls.sharpness,
        brightness: liveControls.brightness,
        contrast: liveControls.contrast,
        saturation: liveControls.saturation,
        noise_reduction_mode: liveControls.noiseReductionMode,
        ae_metering_mode: liveControls.aeMeteringMode,
        af_mode: liveControls.afMode,
        af_range: liveControls.afRange,
        af_speed: liveControls.afSpeed
      }

      const presetData = {
        name: selectedLiveViewPreset,
        description: preset?.description || '',
        workflow: 'liveview',
        settings: {
          liveview: mergedSettings  // Now contains all settings
        }
      }

      // Update preset file
      await createPresetMutation.mutateAsync(presetData)

      // Apply to backend config (uses API utility with CSRF token handling)
      await updateWebuiMutation.mutateAsync(mergedSettings)

      const displayName = preset?.display_name || selectedLiveViewPreset
      toast.success(`Updated "${displayName}" preset`)
    } catch (error) {
      const message = error.response?.data?.error || 'Failed to update preset'
      toast.error(`Update failed: ${message}`)
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
            <h3 className="text-lg font-semibold">Live View</h3>
            <button
              onClick={toggleLiveView}
              disabled={!connected}
              className={`px-4 py-2 rounded-lg font-medium ${
                liveViewActive
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : 'bg-green-600 text-white hover:bg-green-700'
              } disabled:bg-gray-400`}
            >
              {liveViewActive ? 'Stop Live View' : 'Start Live View'}
            </button>
          </div>

          <div className="bg-gray-900 rounded-lg overflow-hidden relative" style={{ minHeight: '600px' }}>
            {currentFrame ? (
              <>
                <img
                  src={currentFrame}
                  alt="Camera preview"
                  className="w-full h-auto cursor-crosshair"
                  onClick={handleImageClick}
                />

                {/* Area of Interest Indicator - Shows both zoom center and AF region */}
                {afWindow && afWindow.active && (() => {
                  // ========================================
                  // Inverse Coordinate Transformation: Sensor → Viewport
                  // ========================================
                  // Problem: afWindow stores position in SENSOR coordinates (0-1 over full sensor)
                  //          but we need VIEWPORT coordinates (0-1 over visible frame) to render the marker
                  //
                  // When zoomed, viewport shows only a CROPPED region of the sensor:
                  //   zoom=1.0: viewport = full sensor (1:1 mapping, no transformation)
                  //   zoom=2.0: viewport = center 50% of sensor (need transformation)
                  //   zoom=4.0: viewport = center 25% of sensor (need transformation)
                  //
                  // Coordinate Systems:
                  //   Sensor Space: (0, 0) to (1, 1) - full camera sensor active area
                  //   Viewport Space: (0, 0) to (1, 1) - visible frame on screen (cropped at zoom > 1.0)
                  //
                  // Formula Derivation:
                  //   Forward transform (handleImageClick, line 692):
                  //     sensorPos = cropCenter + (viewportPos - 0.5) * cropFraction
                  //
                  //   Solving for viewportPos (inverse):
                  //     viewportPos - 0.5 = (sensorPos - cropCenter) / cropFraction
                  //     viewportPos = (sensorPos - cropCenter) / cropFraction + 0.5
                  //
                  // Parameters from backend metadata (see websocket_handlers.py line 235):
                  //   - actual_zoom_center_x/y: Where crop is ACTUALLY centered
                  //     * May differ from requested due to boundary clamping, even enforcement
                  //   - crop_fraction_x/y: How much of sensor is visible (accounts for aspect ratio)
                  //     * Symmetric when sensor and output have same aspect ratio (16:9 → 16:9)
                  //     * Asymmetric when aspect ratios differ (4:3 → 16:9)
                  //
                  // Example 1: Symmetric crop (2x zoom, centered, 16:9 → 16:9)
                  //   afWindow.x = 0.75 (sensor: 75% right)
                  //   currentCenterX = 0.5 (crop centered)
                  //   cropFractionX = 0.5 (50% of sensor visible at 2x zoom)
                  //   → markerViewportX = (0.75 - 0.5) / 0.5 + 0.5 = 0.25 / 0.5 + 0.5 = 1.0
                  //   → Marker appears at RIGHT EDGE of viewport ✓ (where 75% sensor position maps to)
                  //
                  // Example 2: Asymmetric crop (1.0x zoom, centered, 4:3 → 16:9)
                  //   afWindow.y = 0.5 (sensor: vertical center)
                  //   currentCenterY = 0.5 (crop centered)
                  //   cropFractionY = 0.75 (75% of sensor height visible, cropped to maintain 16:9)
                  //   → markerViewportY = (0.5 - 0.5) / 0.75 + 0.5 = 0 / 0.75 + 0.5 = 0.5
                  //   → Marker appears at VIEWPORT CENTER ✓ (correct despite asymmetric crop)
                  //
                  // Example 3: Click near edge (3x zoom, crop at 0.8, 0.5)
                  //   User clicked sensor position 0.9 (near right edge)
                  //   afWindow.x = 0.9
                  //   currentCenterX = 0.8 (crop had to clamp away from 0.9 to fit in bounds)
                  //   cropFractionX = 0.333 (33% visible at 3x)
                  //   → markerViewportX = (0.9 - 0.8) / 0.333 + 0.5 = 0.1 / 0.333 + 0.5 ≈ 0.8
                  //   → Marker appears at 80% across viewport (NOT at edge, because crop clamped)
                  //
                  // Fallback Behavior:
                  //   When metadata unavailable (camera initializing, connection lag):
                  //   - Falls back to zoomCenter for crop center (less accurate)
                  //   - Falls back to symmetric fractions: 1.0 / zoomLevel
                  //   - May cause slight marker misalignment until metadata arrives
                  //   - With 4:3→16:9 + symmetric fallback, Y coords can be off by ~15%
                  //
                  // See also:
                  //   - handleImageClick() (line 653): Forward transformation (viewport → sensor)
                  //   - websocket_handlers.py (line 235): Backend metadata emission
                  //   - calculate_scaler_crop() in liveview_stream.py: Crop calculation

                  let markerViewportX, markerViewportY

                  if (zoomLevel > 1.0) {
                    // Inverse transformation: sensor → viewport
                    // Formula: viewportPos = (sensorPos - cropCenter) / cropFraction + 0.5
                    const currentCenterX = metadata?.actual_zoom_center_x ?? zoomCenter.x
                    const currentCenterY = metadata?.actual_zoom_center_y ?? zoomCenter.y
                    const cropFractionX = metadata?.crop_fraction_x ?? (1.0 / zoomLevel)
                    const cropFractionY = metadata?.crop_fraction_y ?? (1.0 / zoomLevel)

                    markerViewportX = ((afWindow.x - currentCenterX) / cropFractionX) + 0.5
                    markerViewportY = ((afWindow.y - currentCenterY) / cropFractionY) + 0.5
                  } else {
                    // At 1.0x: viewport = full sensor, no transformation needed
                    markerViewportX = afWindow.x
                    markerViewportY = afWindow.y
                  }

                  return (
                    <div
                      className="absolute pointer-events-none"
                      style={{
                        left: `${markerViewportX * 100}%`,
                        top: `${markerViewportY * 100}%`,
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
                  )
                })()}
              </>
            ) : (
              <div className="h-96 flex items-center justify-center">
                <p className="text-gray-400">
                  {liveViewActive ? 'Loading live view...' : 'Click "Start Live View" to begin'}
                </p>
              </div>
            )}

            {/* Metadata Overlay - Top Right */}
            {liveViewActive && metadata && !metadata.error && (
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
                    <span className="text-gray-300">Colour Temp:</span>
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
            {liveViewActive && (
              <div className="absolute top-2 left-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg w-72 max-h-[calc(100vh-200px)] overflow-y-auto">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-sm font-semibold text-gray-200">🎨 Live Controls</h3>
                  <div className="flex gap-2">
                    {/* Show Update button only for user presets */}
                    {selectedLiveViewPreset && presetsData?.presets?.find(p => p.name === selectedLiveViewPreset)?.category === 'user' && (
                      <button
                        onClick={handleUpdateLiveViewPreset}
                        disabled={createPresetMutation.isPending}
                        className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                      >
                        ✏️ Update
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setSaveModalWorkflow('liveview')
                        setShowSaveModal(true)
                      }}
                      className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      💾 Save As
                    </button>
                    <button
                      onClick={handleResetControls}
                      className="px-2 py-1 text-xs bg-white/20 text-white rounded hover:bg-white/30"
                    >
                      Reset
                    </button>
                  </div>
                </div>

                {/* Photo Preset Selector */}
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-200 mb-2">
                    📸 Photo Preset (Capture) {applyPresetMutation.isPending && <span className="text-blue-300">(applying...)</span>}
                  </label>
                  <select
                    value={selectedPhotoPreset}
                    onChange={(e) => {
                      const newValue = e.target.value
                      setSelectedPhotoPreset(newValue)
                      handleApplyPhotoPreset(newValue)
                    }}
                    disabled={applyPresetMutation.isPending}
                    className="w-full px-2 py-1 text-xs bg-white/10 text-white rounded border border-white/20 hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {photoPresets.map((preset) => (
                      <option key={preset.name} value={preset.name}>
                        {preset.display_name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Video Preset Selector */}
                <div className="mb-3 pb-3 border-b border-white/20">
                  <label className="block text-xs font-medium text-gray-200 mb-2">
                    🎥 Live View Preset (Stream) {applyPresetMutation.isPending && <span className="text-blue-300">(applying...)</span>}
                  </label>
                  <select
                    value={selectedLiveViewPreset}
                    onChange={async (e) => {
                      const newValue = e.target.value
                      try {
                        await handleApplyLiveViewPreset(newValue)
                        setSelectedLiveViewPreset(newValue)
                      } catch (error) {
                        // handleApplyLiveViewPreset already handles error display
                        // State remains unchanged on error
                      }
                    }}
                    disabled={applyPresetMutation.isPending}
                    className="w-full px-2 py-1 text-xs bg-white/10 text-white rounded border border-white/20 hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {liveViewPresets.map((preset) => (
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
                      onChange={(e) => handleControlChange(toPicameraControl('sharpness'), parseFloat(e.target.value))}
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
                      onChange={(e) => handleControlChange(toPicameraControl('brightness'), parseFloat(e.target.value))}
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
                      onChange={(e) => handleControlChange(toPicameraControl('contrast'), parseFloat(e.target.value))}
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
                      onChange={(e) => handleControlChange(toPicameraControl('saturation'), parseFloat(e.target.value))}
                      className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>0</span>
                      <span>1.0</span>
                      <span>4</span>
                    </div>
                  </div>

                  {/* Colour Gains Section */}
                  <div className="pt-2 mt-2 border-t border-white/20">
                    <h4 className="text-xs font-semibold text-gray-200 mb-2">🎨 Colour Balance</h4>

                    {/* Red Gain Slider */}
                    <div className="mb-3">
                      <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                        <span>Red Gain</span>
                        <span className="text-red-300 font-mono">{liveControls.colourGainRed.toFixed(3)}</span>
                      </label>
                      <input
                        type="range"
                        min="1.0"
                        max="4.0"
                        step="0.001"
                        value={liveControls.colourGainRed}
                        onChange={(e) => handleControlChange(toPicameraControl('colourGainRed'), parseFloat(e.target.value))}
                        className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-red-500"
                      />
                      <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                        <span>1.0</span>
                        <span>2.5</span>
                        <span>4.0</span>
                      </div>
                    </div>

                    {/* Blue Gain Slider */}
                    <div>
                      <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                        <span>Blue Gain</span>
                        <span className="text-blue-300 font-mono">{liveControls.colourGainBlue.toFixed(3)}</span>
                      </label>
                      <input
                        type="range"
                        min="1.0"
                        max="4.0"
                        step="0.001"
                        value={liveControls.colourGainBlue}
                        onChange={(e) => handleControlChange(toPicameraControl('colourGainBlue'), parseFloat(e.target.value))}
                        className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-500"
                      />
                      <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                        <span>1.0</span>
                        <span>2.5</span>
                        <span>4.0</span>
                      </div>
                    </div>

                    <div className="mt-2 text-[10px] text-gray-300">
                      💡 Locks colour balance for LED flash illumination
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
                        handleControlChange(toPicameraControl('aeEnable'), newValue)
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
                            handleControlChange(toPicameraControl('exposureTime'), exposureTime)
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
                            handleControlChange(toPicameraControl('analogueGain'), newValue)
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
                        onChange={(e) => handleControlChange(toPicameraControl('aeMeteringMode'), parseInt(e.target.value))}
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
                        handleControlChange(toPicameraControl('afMode'), newValue)
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
                          handleControlChange(toPicameraControl('lensPosition'), newValue)
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
                        onChange={(e) => handleControlChange(toPicameraControl('afRange'), parseInt(e.target.value))}
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
                        onChange={(e) => handleControlChange(toPicameraControl('afSpeed'), parseInt(e.target.value))}
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
                      onChange={(e) => handleControlChange(toPicameraControl('noiseReductionMode'), parseInt(e.target.value))}
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

                  {/* Focus Peaking Controls */}
                  <div className="pt-2 mt-2 border-t border-white/20">
                    <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                      <span>🔍 Focus Peaking</span>
                      <input
                        type="checkbox"
                        checked={liveControls.focusPeakingEnabled}
                        onChange={(e) => {
                          const enabled = e.target.checked
                          setLiveControls(prev => ({ ...prev, focusPeakingEnabled: enabled }))
                          debouncedEmitControl('FocusPeakingEnabled', enabled)
                        }}
                        className="w-4 h-4 rounded accent-green-500"
                      />
                    </label>

                    {liveControls.focusPeakingEnabled && (
                      <div className="mt-2 space-y-2">
                        {/* Intensity Slider */}
                        <div>
                          <label className="flex justify-between items-center text-[10px] text-gray-300 mb-1">
                            <span>Intensity</span>
                            <span className="text-green-300 font-mono">{liveControls.focusPeakingIntensity}</span>
                          </label>
                          <input
                            type="range"
                            min="50"
                            max="200"
                            step="10"
                            value={liveControls.focusPeakingIntensity}
                            onChange={(e) => {
                              const value = parseInt(e.target.value)
                              setLiveControls(prev => ({ ...prev, focusPeakingIntensity: value }))
                              debouncedEmitControl('FocusPeakingIntensity', value)
                            }}
                            className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-green-500"
                          />
                          <div className="flex justify-between text-[9px] text-gray-400 mt-0.5">
                            <span>50</span>
                            <span>125</span>
                            <span>200</span>
                          </div>
                        </div>

                        {/* Colour Dropdown */}
                        <div>
                          <label className="text-[10px] text-gray-300 mb-1 block">Colour</label>
                          <select
                            value={liveControls.focusPeakingColour}
                            onChange={(e) => {
                              const colour = e.target.value
                              setLiveControls(prev => ({ ...prev, focusPeakingColour: colour }))
                              debouncedEmitControl('FocusPeakingColour', colour)
                            }}
                            className="w-full px-2 py-1 text-[10px] bg-white/10 text-white rounded border border-white/20"
                          >
                            <option value="green">🟢 Green</option>
                            <option value="red">🔴 Red</option>
                            <option value="yellow">🟡 Yellow</option>
                            <option value="cyan">🔵 Cyan</option>
                            <option value="magenta">🟣 Magenta</option>
                          </select>
                        </div>

                        {/* Algorithm Dropdown */}
                        <div>
                          <label className="text-[10px] text-gray-300 mb-1 block">Algorithm</label>
                          <select
                            value={liveControls.focusPeakingAlgorithm}
                            onChange={(e) => {
                              const algorithm = e.target.value
                              setLiveControls(prev => ({ ...prev, focusPeakingAlgorithm: algorithm }))
                              debouncedEmitControl('FocusPeakingAlgorithm', algorithm)
                            }}
                            className="w-full px-2 py-1 text-[10px] bg-white/10 text-white rounded border border-white/20"
                          >
                            <option value="laplacian">⚡ Laplacian (Fast)</option>
                            <option value="sobel">⚙️ Sobel (Balanced)</option>
                            <option value="canny">🎯 Canny (Accurate)</option>
                          </select>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-3 p-2 bg-blue-500/20 border border-blue-400/30 rounded text-[10px] text-blue-200">
                  <strong>💡 Tip:</strong> Changes apply instantly to live view only. Click live view to focus on specific area.
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

              {/* Calibration Progress Indicator */}
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
                  onClick={handleCopyLiveViewToCapture}
                  disabled={copyingSettings || !connected}
                  className="w-full px-3 py-2 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-600 font-medium"
                >
                  {copyingSettings ? 'Copying...' : '📹 Live View → 📷 Capture'}
                </button>
                <button
                  onClick={handleCopyCaptureToLiveView}
                  disabled={copyingSettings || !connected}
                  className="w-full px-3 py-2 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-600 font-medium"
                >
                  {copyingSettings ? 'Copying...' : '📷 Capture → 📹 Live View'}
                </button>
              </div>
              <div className="mt-2 p-2 bg-yellow-500/20 border border-yellow-400/30 rounded text-[10px] text-yellow-200">
                <strong>⚠️</strong> Sync settings between live view and capture modes
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
                <strong>💡</strong> Test live view settings at full resolution
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

          {/* Live View Info & HDR Indicator - Below Stream */}
          <div className="mt-2 flex flex-col sm:flex-row gap-2">
            {liveViewActive && (
              <div className="flex-1 bg-gray-50 rounded-lg px-3 py-2 border border-gray-200">
                <p className="text-xs text-gray-600">
                  📹 Live View running at ~10 FPS (1024x768) with continuous autofocus
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
        defaultWorkflow={saveModalWorkflow}
      />
    </div>
  )
}
