/**
 * Camera Page - TypeScript Orchestrator
 *
 * Main camera control page with live preview, real-time controls, and photo capture.
 * Orchestrates extracted components and manages shared state.
 */

import { useState, useEffect, useRef } from 'react'
import { capturePhoto, triggerAutofocus, autoCalibrate, copySettings, testCaptureLiveview, freezeSettings, getPresets, applyPreset, createPreset, getPreferences, updateWebuiSettings } from '../utils/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import useSocket from '../hooks/useSocket'
import toast from 'react-hot-toast'
import SavePresetModal from '../components/SavePresetModal'
import InstantCaptureButton from '../components/InstantCaptureButton'
import { convertFromBackend, toPicameraControl } from '../utils/cameraControlMapping'
import { validateLiveviewSettings, formatLiveviewValidationErrors } from '../schemas/liveview-settings'

// Component imports
import CameraPreview from '../components/camera/CameraPreview'
import CameraControls from '../components/camera/CameraControls'
import CameraSettings from '../components/camera/CameraSettings'
import CalibrationPanel from '../components/camera/CalibrationPanel'

// Type imports
import {
  LiveControls,
  CameraMetadata,
  AfWindow,
  CalibrationProgress,
  ActionResult,
  PresetData,
  CameraSettings as CameraSettingsType,
  LastCapture,
  ZoomCenter
} from '../types/camera'

/**
 * Field list constants for API response validation
 */
const BASIC_SETTINGS_FIELDS = ['sharpness', 'brightness', 'contrast', 'saturation']
const CAMERA_CONTROL_FIELDS = ['noise_reduction_mode', 'ae_metering_mode', 'af_mode', 'af_range', 'af_speed']
const AE_FIELDS = ['ae_enable']
const MANUAL_CONTROL_FIELDS = ['exposure_time', 'analogue_gain', 'lens_position']

/**
 * Validates API response has expected fields, warns in dev mode if missing.
 */
const validateApiResponse = (data: Record<string, unknown>, expectedFields: string[], context = 'API response') => {
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
  const { socket, connected } = useSocket()
  const queryClient = useQueryClient()

  // Capture state
  const [capturing, setCapturing] = useState(false)
  const [lastCapture, setLastCapture] = useState<LastCapture | null>(null)

  // Live view state
  const [liveViewActive, setLiveViewActive] = useState(false)
  const [currentFrame, setCurrentFrame] = useState<string | null>(null)
  const [metadata, setMetadata] = useState<CameraMetadata | null>(null)

  // Action state
  const [autofocusing, setAutofocusing] = useState(false)
  const [calibrating, setCalibrating] = useState(false)
  const [freezing, setFreezing] = useState(false)
  const [copyingSettings, setCopyingSettings] = useState(false)
  const [actionResult, setActionResult] = useState<ActionResult | null>(null)
  const [testCapturing, setTestCapturing] = useState(false)
  const [testCaptureResult, setTestCaptureResult] = useState<{
    success: boolean
    test_photo_path?: string
    metadata?: { exposure_time: number; analogue_gain: number; lens_position: number }
    error?: string
  } | null>(null)
  const [calibrationProgress, setCalibrationProgress] = useState<CalibrationProgress | null>(null)

  // Live controls state
  const [liveControls, setLiveControls] = useState<LiveControls>({
    sharpness: 1.0,
    brightness: 0.0,
    contrast: 1.0,
    saturation: 1.0,
    aeMeteringMode: 0,
    aeEnable: true,
    exposureTime: 500,
    analogueGain: 8.0,
    noiseReductionMode: 0,
    afMode: 2,
    lensPosition: 3.0,
    afRange: 0,
    afSpeed: 0,
    colourGainRed: 2.259,
    colourGainBlue: 1.500,
    focusPeakingEnabled: false,
    focusPeakingIntensity: 100,
    focusPeakingColour: 'green',
    focusPeakingAlgorithm: 'laplacian'
  })

  // Zoom and focus state
  const [zoomLevel, setZoomLevel] = useState(1.0)
  const [zoomCenter, setZoomCenter] = useState<ZoomCenter>({ x: 0.5, y: 0.5 })
  const [afWindow, setAfWindow] = useState<AfWindow | null>(null)
  const [cameraSettings, setCameraSettings] = useState<CameraSettingsType | null>(null)

  // Preset management
  const [selectedPhotoPreset, setSelectedPhotoPreset] = useState('')
  const [selectedLiveViewPreset, setSelectedLiveViewPreset] = useState('')
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveModalWorkflow, setSaveModalWorkflow] = useState<'photo' | 'liveview' | 'both'>('both')

  // Refs
  const metadataIntervalRef = useRef<number | null>(null)
  const debounceTimerRef = useRef<number | null>(null)
  const zoomDebounceTimerRef = useRef<number | null>(null)
  const photoPresetInitialized = useRef(false)
  const liveViewPresetInitialized = useRef(false)

  // Fetch presets and preferences
  const { data: presetsData } = useQuery({
    queryKey: QUERY_KEYS.PRESETS,
    queryFn: () => getPresets().then(res => res.data),
    staleTime: 30000
  })

  const { data: preferences } = useQuery({
    queryKey: QUERY_KEYS.PREFERENCES,
    queryFn: () => getPreferences().then(res => res.data)
  })

  // Mutations
  const applyPresetMutation = useMutation({
    mutationFn: ({ name, applyTo }: { name: string; applyTo: string }) => applyPreset(name, applyTo),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.WEBUI_SETTINGS })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CAMERA_SETTINGS })
    }
  })

  const createPresetMutation = useMutation({
    mutationFn: createPreset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.PRESETS })
    }
  })

  const updateWebuiMutation = useMutation({
    mutationFn: updateWebuiSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.WEBUI_SETTINGS })
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || 'Failed to update stream settings'
      toast.error(`Error: ${message}`)
    }
  })

  // Filter presets by workflow
  const photoPresets = presetsData?.presets?.filter((p: PresetData) => p.workflow === 'photo' || p.workflow === 'both') || []
  const liveViewPresets = presetsData?.presets?.filter((p: PresetData) => p.workflow === 'liveview' || p.workflow === 'both') || []

  // Debounced control emission
  const debouncedEmitControl = (controlName: string, value: number | boolean | string) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }
    debounceTimerRef.current = window.setTimeout(() => {
      if (socket && liveViewActive) {
        socket.emit('update_liveview_control', {
          [controlName]: value
        })
      }
    }, 150)
  }

  // Debounced zoom emission
  const debouncedEmitZoom = (zoomLevel: number, centerX: number, centerY: number) => {
    if (zoomDebounceTimerRef.current) {
      clearTimeout(zoomDebounceTimerRef.current)
    }
    zoomDebounceTimerRef.current = window.setTimeout(() => {
      if (socket && liveViewActive) {
        socket.emit('set_zoom', {
          zoom_level: zoomLevel,
          center_x: centerX,
          center_y: centerY
        })
      }
    }, 150)
  }

  // Load default presets on mount
  useEffect(() => {
    if (presetsData?.presets && preferences !== undefined && !photoPresetInitialized.current && !selectedPhotoPreset) {
      const defaultPreset = (preferences as any)?.default_capture_preset || 'Balanced'
      const presetExists = presetsData.presets.some((p: PresetData) =>
        p.name === defaultPreset && (p.workflow === 'photo' || p.workflow === 'both')
      )
      if (presetExists) {
        setSelectedPhotoPreset(defaultPreset)
        initializePhotoPreset(defaultPreset)
        photoPresetInitialized.current = true
      }
    }
  }, [presetsData, preferences, selectedPhotoPreset])

  useEffect(() => {
    if (presetsData?.presets && preferences !== undefined && !liveViewPresetInitialized.current && !selectedLiveViewPreset) {
      const defaultPreset = (preferences as any)?.default_liveview_preset || 'Balanced'
      const presetExists = presetsData.presets.some((p: PresetData) =>
        p.name === defaultPreset && (p.workflow === 'liveview' || p.workflow === 'both')
      )
      if (presetExists) {
        initializeLiveViewPreset(defaultPreset).then(() => {
          setSelectedLiveViewPreset(defaultPreset)
          liveViewPresetInitialized.current = true
        }).catch((error: any) => {
          console.error('Failed to initialize liveview preset:', error)
          liveViewPresetInitialized.current = false
          const preset = presetsData?.presets?.find((p: PresetData) => p.name === defaultPreset)
          const displayName = preset?.display_name || defaultPreset
          const message = error.response?.data?.error || 'Failed to load preset'
          toast.error(`Preset "${displayName}" failed to load: ${message}`)
        })
      }
    }
  }, [presetsData, preferences, selectedLiveViewPreset])

  // Fetch initial settings on mount
  useEffect(() => {
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

    const fetchWebuiSettings = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const response = await fetch(`${API_URL}/config/webui`)
        if (response.ok) {
          const data = await response.json()
          const frontendControls = convertFromBackend(data)

          const defaultControls: LiveControls = {
            sharpness: 1.0,
            brightness: 0.0,
            contrast: 1.0,
            saturation: 1.0,
            noiseReductionMode: 0,
            aeMeteringMode: 0,
            aeEnable: true,
            exposureTime: 500,
            analogueGain: 8.0,
            afMode: 2,
            lensPosition: 3.0,
            afRange: 0,
            afSpeed: 0,
            colourGainRed: 2.259,
            colourGainBlue: 1.500,
            focusPeakingEnabled: false,
            focusPeakingIntensity: 100,
            focusPeakingColour: 'green',
            focusPeakingAlgorithm: 'laplacian'
          }

          setLiveControls({
            ...defaultControls,
            ...frontendControls
          })
        }
      } catch (error) {
        console.error('Failed to fetch webui settings:', error)
      }
    }

    fetchSettings()
    fetchWebuiSettings()

    return () => {
      if (metadataIntervalRef.current) {
        clearInterval(metadataIntervalRef.current)
      }
    }
  }, [])

  // Socket event handlers
  useEffect(() => {
    if (!socket) return

    const handleDisconnect = () => {
      setLiveViewActive(false)
    }

    const handleCameraFrame = (data: { image: string }) => {
      setCurrentFrame(data.image)
    }

    const handleLiveviewStatus = (data: { streaming: boolean }) => {
      setLiveViewActive(data.streaming)
    }

    const handleMetadataUpdate = (data: CameraMetadata) => {
      setMetadata(data)
    }

    const handleCalibrationProgress = (data: CalibrationProgress) => {
      setCalibrationProgress(data)
    }

    const handleControlUpdated = (data: { success: boolean; error?: string }) => {
      if (!data.success) {
        console.error('Control update failed:', data.error)
        toast.error(`Failed to update control: ${data.error}`)
      }
    }

    const handleZoomUpdated = (data: { success: boolean; error?: string }) => {
      if (!data.success) {
        console.error('Zoom update failed:', data.error)
        toast.error(`Failed to update zoom: ${data.error}`)
      }
    }

    const handleAfWindowUpdated = (data: { success: boolean; x: number | null; y: number | null; error?: string }) => {
      if (data.success) {
        if (data.x !== null && data.y !== null) {
          setAfWindow({
            x: data.x,
            y: data.y,
            active: true,
            focusing: true
          })
          setTimeout(() => {
            setAfWindow(prev => prev ? { ...prev, focusing: false } : null)
          }, 3000)
        } else {
          setAfWindow(null)
        }
      } else {
        console.error('AF window update failed:', data.error)
        toast.error(`Failed to update AF window: ${data.error}`)
      }
    }

    const handleSettingsReloaded = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const response = await fetch(`${API_URL}/config/webui`)
        if (response.ok) {
          const data = await response.json()
          const validatedData = validateApiResponse(data, [
            ...BASIC_SETTINGS_FIELDS,
            ...CAMERA_CONTROL_FIELDS,
            ...AE_FIELDS
          ], 'settings_reloaded event')

          setLiveControls(prev => ({
            ...prev,
            sharpness: (validatedData.sharpness as number) ?? prev.sharpness,
            brightness: (validatedData.brightness as number) ?? prev.brightness,
            contrast: (validatedData.contrast as number) ?? prev.contrast,
            saturation: (validatedData.saturation as number) ?? prev.saturation,
            noiseReductionMode: (validatedData.noise_reduction_mode as number) ?? prev.noiseReductionMode,
            aeMeteringMode: (validatedData.ae_metering_mode as number) ?? prev.aeMeteringMode,
            aeEnable: (validatedData.ae_enable as boolean) ?? prev.aeEnable,
            afMode: (validatedData.af_mode as number) ?? prev.afMode,
            afRange: (validatedData.af_range as number) ?? prev.afRange,
            afSpeed: (validatedData.af_speed as number) ?? prev.afSpeed
          }))
        }
      } catch (error) {
        console.error('Failed to refresh settings after settings_reloaded event:', error)
      }
    }

    socket.on('disconnect', handleDisconnect)
    socket.on('camera_frame', handleCameraFrame)
    socket.on('liveview_status', handleLiveviewStatus)
    socket.on('metadata_update', handleMetadataUpdate)
    socket.on('calibration_progress', handleCalibrationProgress)
    socket.on('control_updated', handleControlUpdated)
    socket.on('zoom_updated', handleZoomUpdated)
    socket.on('af_window_updated', handleAfWindowUpdated)
    socket.on('settings_reloaded', handleSettingsReloaded)

    return () => {
      socket.emit('stop_liveview')
      socket.off('disconnect', handleDisconnect)
      socket.off('camera_frame', handleCameraFrame)
      socket.off('liveview_status', handleLiveviewStatus)
      socket.off('metadata_update', handleMetadataUpdate)
      socket.off('calibration_progress', handleCalibrationProgress)
      socket.off('control_updated', handleControlUpdated)
      socket.off('zoom_updated', handleZoomUpdated)
      socket.off('af_window_updated', handleAfWindowUpdated)
      socket.off('settings_reloaded', handleSettingsReloaded)
    }
  }, [socket])

  // Poll metadata when preview is active
  useEffect(() => {
    if (liveViewActive && socket) {
      metadataIntervalRef.current = window.setInterval(() => {
        socket.emit('get_metadata')
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
  }, [liveViewActive, socket])

  // Handlers
  const handleCapture = async () => {
    setCapturing(true)
    try {
      const response = await capturePhoto()
      setLastCapture(response.data)

      if (response.data.hdr_mode) {
        toast.success(
          `HDR capture complete: ${response.data.hdr_count} exposures with ${response.data.hdr_width}µs bracket width`,
          { duration: 5000 }
        )
      } else {
        toast.success('Photo captured successfully!')
      }
    } catch (error: any) {
      console.error('Capture failed:', error)
      const message = error.response?.data?.error || 'Failed to capture photo'
      toast.error(`Capture failed: ${message}`)
    } finally {
      setCapturing(false)
    }
  }

  const toggleLiveView = async () => {
    if (!socket) return

    if (liveViewActive) {
      socket.emit('stop_liveview')
      setCurrentFrame(null)
    } else {
      try {
        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const response = await fetch(`${API_URL}/config/webui`)
        if (response.ok) {
          const data = await response.json()
          const validatedData = validateApiResponse(data, [
            ...BASIC_SETTINGS_FIELDS,
            ...CAMERA_CONTROL_FIELDS,
            ...AE_FIELDS,
            ...MANUAL_CONTROL_FIELDS
          ], 'preview start settings refresh')

          setLiveControls(prev => ({
            ...prev,
            sharpness: (validatedData.sharpness as number) ?? prev.sharpness,
            brightness: (validatedData.brightness as number) ?? prev.brightness,
            contrast: (validatedData.contrast as number) ?? prev.contrast,
            saturation: (validatedData.saturation as number) ?? prev.saturation,
            noiseReductionMode: (validatedData.noise_reduction_mode as number) ?? prev.noiseReductionMode,
            aeMeteringMode: (validatedData.ae_metering_mode as number) ?? prev.aeMeteringMode,
            aeEnable: (validatedData.ae_enable as boolean) ?? prev.aeEnable,
            exposureTime: (validatedData.exposure_time as number) ?? prev.exposureTime,
            analogueGain: (validatedData.analogue_gain as number) ?? prev.analogueGain,
            afMode: (validatedData.af_mode as number) ?? prev.afMode,
            lensPosition: (validatedData.lens_position as number) ?? prev.lensPosition,
            afRange: (validatedData.af_range as number) ?? prev.afRange,
            afSpeed: (validatedData.af_speed as number) ?? prev.afSpeed
          }))

          await new Promise<void>((resolve) => {
            let isResolved = false
            const timeoutMs = 1000

            const handleReloaded = (data: { success?: boolean; error?: string }) => {
              if (isResolved) return
              isResolved = true
              clearTimeout(timeoutId)
              socket.off('settings_reloaded', handleReloaded)

              if (data && data.success === false) {
                console.warn(
                  `[${new Date().toISOString()}] Backend settings reload failed:`,
                  data.error,
                  `| Socket connected: ${socket?.connected}`
                )
                toast.error(`Settings reload failed: ${data.error}. Stream may use cached settings.`, { duration: 5000 })
              }

              resolve()
            }

            const timeoutId = setTimeout(() => {
              if (isResolved) return
              isResolved = true
              socket.off('settings_reloaded', handleReloaded)

              console.error(
                `[${new Date().toISOString()}] Settings reload timed out after ${timeoutMs}ms`,
                `| Socket connected: ${socket?.connected}`
              )
              toast.error(`Settings reload timed out. Stream will use cached settings.`, { duration: 5000 })

              resolve()
            }, timeoutMs)

            if (!socket?.connected) {
              clearTimeout(timeoutId)
              console.error(
                `[${new Date().toISOString()}] Cannot reload settings: WebSocket not connected`
              )
              toast.error('WebSocket disconnected. Cannot reload settings.', { duration: 5000 })
              resolve()
              return
            }

            socket.once('settings_reloaded', handleReloaded)
            socket.emit('reload_stream_settings')
          })
        }
      } catch (error) {
        console.error('Failed to refresh settings before preview start:', error)
      }

      socket.emit('start_liveview')
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
    } catch (error: any) {
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
    setCalibrationProgress(null)
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
    } catch (error: any) {
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
    } catch (error: any) {
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
    } catch (error: any) {
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
    } catch (error: any) {
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
    } catch (error: any) {
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

  const handleControlChange = (controlName: string, value: number | boolean | string) => {
    const key = controlName.charAt(0).toLowerCase() + controlName.slice(1) as keyof LiveControls

    setLiveControls(prev => ({
      ...prev,
      [key]: value
    }))

    debouncedEmitControl(controlName, value)
  }

  const handleZoomChange = (value: number) => {
    setZoomLevel(value)

    if (value === 1.0) {
      setZoomCenter({ x: 0.5, y: 0.5 })
    }

    const centerX = afWindow?.x ?? zoomCenter.x
    const centerY = afWindow?.y ?? zoomCenter.y

    debouncedEmitZoom(value, centerX, centerY)
  }

  const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!liveViewActive) return

    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const viewportX = Math.max(0, Math.min(x / rect.width, 1))
    const viewportY = Math.max(0, Math.min(y / rect.height, 1))

    let sensorX: number, sensorY: number

    if (zoomLevel > 1.0) {
      const currentCenterX = metadata?.actual_zoom_center_x ?? zoomCenter.x
      const currentCenterY = metadata?.actual_zoom_center_y ?? zoomCenter.y
      const cropFractionX = metadata?.crop_fraction_x ?? (1.0 / zoomLevel)
      const cropFractionY = metadata?.crop_fraction_y ?? (1.0 / zoomLevel)

      sensorX = currentCenterX + (viewportX - 0.5) * cropFractionX
      sensorY = currentCenterY + (viewportY - 0.5) * cropFractionY
    } else {
      sensorX = viewportX
      sensorY = viewportY
    }

    const clampedX = Math.max(0, Math.min(sensorX, 1))
    const clampedY = Math.max(0, Math.min(sensorY, 1))

    setZoomCenter({ x: clampedX, y: clampedY })

    setAfWindow({
      x: clampedX,
      y: clampedY,
      active: true,
      focusing: true
    })

    if (socket) {
      if (zoomLevel > 1.0) {
        socket.emit('set_zoom', {
          zoom_level: zoomLevel,
          center_x: clampedX,
          center_y: clampedY
        })
      }

      socket.emit('set_af_window', {
        x: clampedX,
        y: clampedY,
        window_size: 0.2
      })

      toast.success(`Area of interest: (${(clampedX * 100).toFixed(0)}%, ${(clampedY * 100).toFixed(0)}%)`)
    }

    setTimeout(() => {
      setAfWindow(prev => prev ? { ...prev, focusing: false } : null)
    }, 3000)
  }

  const handleResetControls = () => {
    const defaults: Partial<LiveControls> = {
      sharpness: 1.0,
      brightness: 0.0,
      contrast: 1.0,
      saturation: 1.0,
      afMode: 2,
      lensPosition: 3.0,
      afRange: 0,
      afSpeed: 0,
      colourGainRed: 2.259,
      colourGainBlue: 1.500
    }

    setLiveControls(prev => ({
      ...prev,
      ...defaults
    }))
    setZoomLevel(1.0)
    setZoomCenter({ x: 0.5, y: 0.5 })
    setAfWindow(null)

    if (socket && liveViewActive) {
      Object.entries(defaults).forEach(([key, value]) => {
        const controlName = key.charAt(0).toUpperCase() + key.slice(1)
        socket.emit('update_liveview_control', {
          [controlName]: value
        })
      })
      socket.emit('set_zoom', {
        zoom_level: 1.0,
        center_x: 0.5,
        center_y: 0.5
      })
      socket.emit('set_af_window', {
        x: null,
        y: null
      })
      toast.success('Controls, focus, zoom, and AF window reset to defaults')
    }
  }

  const initializePhotoPreset = async (presetName: string) => {
    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'capture'
      })
    } catch (error: any) {
      console.error('Failed to initialize photo preset:', error)
      const preset = presetsData?.presets?.find((p: PresetData) => p.name === presetName)
      const displayName = preset?.display_name || presetName
      const message = error.response?.data?.error || 'Failed to load preset'
      toast.error(`Preset "${displayName}" failed to load: ${message}`)
    }
  }

  const handleApplyPhotoPreset = async (presetName: string) => {
    if (!presetName) {
      return
    }

    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'capture'
      })

      const preset = presetsData?.presets?.find((p: PresetData) => p.name === presetName)
      const displayName = preset?.display_name || presetName
      if (photoPresetInitialized.current) {
        toast.success(`Applied "${displayName}" to capture settings`)
      }
    } catch (error: any) {
      console.error('Apply photo preset failed:', error)
      const message = error.response?.data?.error || 'Failed to apply preset'
      toast.error(`Apply failed: ${message}`)
      setSelectedPhotoPreset('')
    }
  }

  const initializeLiveViewPreset = async (presetName: string) => {
    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'liveview'
      })

      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${API_URL}/config/webui`)
      if (response.ok) {
        const data = await response.json()
        const validatedData = validateApiResponse(data, [
          ...BASIC_SETTINGS_FIELDS,
          ...CAMERA_CONTROL_FIELDS
        ], 'preset initialization')

        setLiveControls(prev => ({
          ...prev,
          sharpness: (validatedData.sharpness as number) ?? prev.sharpness,
          brightness: (validatedData.brightness as number) ?? prev.brightness,
          contrast: (validatedData.contrast as number) ?? prev.contrast,
          saturation: (validatedData.saturation as number) ?? prev.saturation,
          noiseReductionMode: (validatedData.noise_reduction_mode as number) ?? prev.noiseReductionMode,
          aeMeteringMode: (validatedData.ae_metering_mode as number) ?? prev.aeMeteringMode,
          afMode: (validatedData.af_mode as number) ?? prev.afMode,
          afRange: (validatedData.af_range as number) ?? prev.afRange,
          afSpeed: (validatedData.af_speed as number) ?? prev.afSpeed
        }))
      }
    } catch (error) {
      console.error('Failed to initialize video preset:', error)
      liveViewPresetInitialized.current = false
      throw error
    }
  }

  const handleApplyLiveViewPreset = async (presetName: string) => {
    if (!presetName) {
      return
    }

    await applyPresetMutation.mutateAsync({
      name: presetName,
      applyTo: 'liveview'
    })

    const preset = presetsData?.presets?.find((p: PresetData) => p.name === presetName)
    const displayName = preset?.display_name || presetName
    if (liveViewPresetInitialized.current) {
      toast.success(`Applied "${displayName}" to stream`)
    }

    const API_URL = import.meta.env.VITE_API_URL || '/api'
    const response = await fetch(`${API_URL}/config/webui`)
    if (response.ok) {
      const data = await response.json()
      const validatedData = validateApiResponse(data, [
        ...BASIC_SETTINGS_FIELDS,
        ...CAMERA_CONTROL_FIELDS
      ], 'settings update after preset')

      setLiveControls(prev => ({
        ...prev,
        sharpness: (validatedData.sharpness as number) ?? prev.sharpness,
        brightness: (validatedData.brightness as number) ?? prev.brightness,
        contrast: (validatedData.contrast as number) ?? prev.contrast,
        saturation: (validatedData.saturation as number) ?? prev.saturation,
        noiseReductionMode: (validatedData.noise_reduction_mode as number) ?? prev.noiseReductionMode,
        aeMeteringMode: (validatedData.ae_metering_mode as number) ?? prev.aeMeteringMode,
        afMode: (validatedData.af_mode as number) ?? prev.afMode,
        afRange: (validatedData.af_range as number) ?? prev.afRange,
        afSpeed: (validatedData.af_speed as number) ?? prev.afSpeed
      }))
    }
  }

  const handleUpdateLiveViewPreset = async () => {
    if (!selectedLiveViewPreset) return

    const preset = presetsData?.presets?.find((p: PresetData) => p.name === selectedLiveViewPreset)
    if (preset?.category === 'built-in') {
      toast.error('Cannot modify built-in presets. Use "Save As" to create a copy.')
      return
    }

    try {
      const validationErrors = validateLiveviewSettings(liveControls)
      if (validationErrors.length > 0) {
        const errorMessage = formatLiveviewValidationErrors(validationErrors, 3)
        toast.error(errorMessage)
        return
      }

      const API_URL = import.meta.env.VITE_API_URL || '/api'
      const response = await fetch(`${API_URL}/config/webui`)
      if (!response.ok) {
        throw new Error('Failed to fetch complete settings')
      }
      const completeSettings = await response.json()

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

      const presetData: PresetData = {
        name: selectedLiveViewPreset,
        description: preset?.description || '',
        workflow: 'liveview',
        settings: {
          liveview: mergedSettings
        }
      }

      await createPresetMutation.mutateAsync(presetData)
      await updateWebuiMutation.mutateAsync(mergedSettings)

      const displayName = preset?.display_name || selectedLiveViewPreset
      toast.success(`Updated "${displayName}" preset`)
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to update preset'
      toast.error(`Update failed: ${message}`)
    }
  }

  const handleSavePreset = async (presetData: PresetData) => {
    try {
      const validationErrors = validateLiveviewSettings(liveControls)
      if (validationErrors.length > 0) {
        const errorMessage = formatLiveviewValidationErrors(validationErrors, 3)
        toast.error(errorMessage)
        throw new Error('Validation failed')
      }

      await createPresetMutation.mutateAsync(presetData)
      toast.success(`Preset "${presetData.name}" saved successfully`)
      setShowSaveModal(false)
    } catch (error: any) {
      console.error('Save preset failed:', error)
      const message = error.response?.data?.error || 'Failed to save preset'
      toast.error(`Save failed: ${message}`)
      throw error
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

      {/* Camera Preview Section */}
      <div className="space-y-2">
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

          <div className="relative">
            <CameraPreview
              currentFrame={currentFrame}
              liveViewActive={liveViewActive}
              metadata={metadata}
              afWindow={afWindow}
              zoomLevel={zoomLevel}
              zoomCenter={zoomCenter}
              liveControls={liveControls}
              socket={socket}
              onImageClick={handleImageClick}
              setAfWindow={setAfWindow}
            />

            {/* Live Controls Overlay */}
            {liveViewActive && (
              <CameraControls
                liveControls={liveControls}
                zoomLevel={zoomLevel}
                afWindow={afWindow}
                selectedPhotoPreset={selectedPhotoPreset}
                selectedLiveViewPreset={selectedLiveViewPreset}
                photoPresets={photoPresets}
                liveViewPresets={liveViewPresets}
                applyPresetMutationPending={applyPresetMutation.isPending}
                createPresetMutationPending={createPresetMutation.isPending}
                socket={socket}
                presetsData={presetsData}
                onControlChange={handleControlChange}
                onZoomChange={handleZoomChange}
                onResetControls={handleResetControls}
                onApplyPhotoPreset={handleApplyPhotoPreset}
                onApplyLiveViewPreset={handleApplyLiveViewPreset}
                onUpdateLiveViewPreset={handleUpdateLiveViewPreset}
                onShowSaveModal={(workflow) => {
                  setSaveModalWorkflow(workflow)
                  setShowSaveModal(true)
                }}
                setLiveControls={setLiveControls}
                setAfWindow={setAfWindow}
                setSelectedPhotoPreset={setSelectedPhotoPreset}
                setSelectedLiveViewPreset={setSelectedLiveViewPreset}
                debouncedEmitControl={debouncedEmitControl}
              />
            )}

            {/* Calibration and Action Panels */}
            <CalibrationPanel
              autofocusing={autofocusing}
              calibrating={calibrating}
              freezing={freezing}
              copyingSettings={copyingSettings}
              testCapturing={testCapturing}
              connected={connected}
              calibrationProgress={calibrationProgress}
              actionResult={actionResult}
              testCaptureResult={testCaptureResult}
              onAutofocus={handleAutofocus}
              onCalibrate={handleCalibrate}
              onFreezeSettings={handleFreezeSettings}
              onCopyLiveViewToCapture={handleCopyLiveViewToCapture}
              onCopyCaptureToLiveView={handleCopyCaptureToLiveView}
              onTestCapture={handleTestCapture}
            >
              <div className="mt-2">
                <InstantCaptureButton
                  disabled={!connected}
                  className="w-full px-3 py-2 text-sm"
                />
              </div>
            </CalibrationPanel>

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

          <CameraSettings
            liveViewActive={liveViewActive}
            cameraSettings={cameraSettings}
          />
        </div>
      </div>

      {/* Save Preset Modal */}
      <SavePresetModal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        onSave={handleSavePreset}
        isSaving={createPresetMutation.isPending}
        defaultWorkflow={saveModalWorkflow}
        currentSettings={liveControls}
      />
    </div>
  )
}
