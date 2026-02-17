import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getControls, updateControls, getCameraSettings, updateCameraSettings, getSystemInfo, getDiagnosticInfo, getWebuiSettings, updateWebuiSettings, getPresets, applyPreset, deletePreset, createPreset, getPreferences, setPreference } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { useState, useEffect, useRef } from 'react'
import { io } from 'socket.io-client'
import toast from 'react-hot-toast'
import { CAMERA_SETTINGS } from '../constants/config'
import SavePresetModal from '../components/SavePresetModal'
import GPSSettings from '../components/GPSSettings'
import CollapsibleCard from '../components/CollapsibleCard'
import { validatePresetSettings, formatValidationErrors } from '../utils/presetValidation'

export default function Settings() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('system')
  const socketRef = useRef(null)

  // Collapsed cards state - smart defaults (common expanded, advanced collapsed)
  const [collapsedCards, setCollapsedCards] = useState({
    // System Info - start collapsed (read-only info)
    systemInstallation: true,
    systemGPIO: true,
    // Diagnostic - start collapsed
    diagnosticPaths: true,
    diagnosticControls: true,
    diagnosticHardware: true,
    // Camera Settings - common expanded, advanced collapsed
    cameraPreset: false,
    cameraFocusStrategy: false,
    cameraExposure: false,
    cameraHDR: true,
    cameraFocusBracket: true,
    cameraFormat: false,
    cameraAdvanced: true,
    // Live View Settings - common expanded, advanced collapsed
    streamResolution: false,
    streamImageQuality: false,
    streamFocus: false,
    streamExposure: false,
    streamWhiteBalance: true,
    streamISP: true,
    streamFocusPeaking: true,
  })

  const toggleCard = (id) => {
    setCollapsedCards(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const { data: controls, isLoading: controlsLoading } = useQuery({
    queryKey: QUERY_KEYS.CONTROLS,
    queryFn: () => getControls().then(res => res.data),
  })

  const { data: cameraSettings, isLoading: cameraLoading } = useQuery({
    queryKey: QUERY_KEYS.CAMERA_SETTINGS,
    queryFn: () => getCameraSettings().then(res => res.data),
  })

  const { data: webuiSettings, isLoading: webuiLoading } = useQuery({
    queryKey: QUERY_KEYS.WEBUI_SETTINGS,
    queryFn: () => getWebuiSettings().then(res => res.data),
  })

  const { data: systemInfo } = useQuery({
    queryKey: QUERY_KEYS.SYSTEM_INFO,
    queryFn: () => getSystemInfo().then(res => res.data),
  })

  const { data: diagnosticInfo } = useQuery({
    queryKey: QUERY_KEYS.DIAGNOSTIC_INFO,
    queryFn: () => getDiagnosticInfo().then(res => res.data),
  })

  const updateControlsMutation = useMutation({
    mutationFn: updateControls,
    onSuccess: () => {
      isDirtyRef.current.controls = false
      queryClient.invalidateQueries(QUERY_KEYS.CONTROLS)
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
      isDirtyRef.current.camera = false
      queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)
      // No toast - only used by handleUpdatePhotoPreset which shows its own toast
    },
    onError: (error) => {
      const message = error.response?.data?.error || 'Failed to update camera settings'
      toast.error(`Error: ${message}`)
    },
  })

  const updateWebuiMutation = useMutation({
    mutationFn: updateWebuiSettings,
    onSuccess: () => {
      isDirtyRef.current.webui = false
      queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
      // Notify backend to reload settings via WebSocket
      if (socketRef.current) {
        socketRef.current.emit('reload_stream_settings')
      }
      // No toast - only used by handleUpdateVideoPreset which shows its own toast
    },
    onError: (error) => {
      const message = error.response?.data?.error || 'Failed to update stream settings'
      toast.error(`Error: ${message}`)
    },
  })

  // Preset management
  const { data: presetsData, isLoading: presetsLoading } = useQuery({
    queryKey: QUERY_KEYS.PRESETS,
    queryFn: () => getPresets().then(res => res.data),
  })

  // User preferences (for default presets)
  const { data: preferences } = useQuery({
    queryKey: QUERY_KEYS.PREFERENCES,
    queryFn: () => getPreferences().then(res => res.data),
  })

  const applyPresetMutation = useMutation({
    mutationFn: ({ name, applyTo }) => applyPreset(name, applyTo),
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)
      queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
      // No toast here - let individual handlers control when to show toasts
      // This allows silent initialization vs. user-action feedback
    },
    onError: () => {
      // Error toasts handled by individual callers (initializePhotoPreset,
      // initializeVideoPreset, handlePhotoPresetChange, handleVideoPresetChange)
      // which provide context-specific messages. Showing a toast here would
      // duplicate because mutateAsync fires both onError and promise rejection.
    },
  })

  const deletePresetMutation = useMutation({
    mutationFn: (name) => deletePreset(name),
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.PRESETS)
      setSelectedPhotoPreset('')
      setSelectedLiveViewPreset('')
      toast.success('Preset deleted successfully!')
    },
    onError: (error) => {
      const message = error.response?.data?.error || 'Failed to delete preset'
      toast.error(`Error: ${message}`)
    },
  })

  const createPresetMutation = useMutation({
    mutationFn: (data) => createPreset(data),
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.PRESETS)
      // No toast here - used by both Update and Save As
      // Update handlers show "Updated [preset]" toast
      // Save As shows toast via SavePresetModal's onSave callback
      setShowSaveModal(false)
    },
    onError: (error) => {
      const message = error.response?.data?.error || 'Failed to save preset'
      toast.error(`Error: ${message}`)
    },
  })

  const setPreferenceMutation = useMutation({
    mutationFn: ({ key, value }) => setPreference(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.PREFERENCES)
      toast.success('Default preset updated!')
    },
    onError: (error) => {
      const message = error.response?.data?.error || 'Failed to update preference'
      toast.error(`Error: ${message}`)
    },
  })

  const [controlsForm, setControlsForm] = useState({})
  const [cameraForm, setCameraForm] = useState({})
  const [webuiForm, setWebuiForm] = useState({})
  const [selectedPhotoPreset, setSelectedPhotoPreset] = useState('')
  const [selectedLiveViewPreset, setSelectedLiveViewPreset] = useState('')
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveModalWorkflow, setSaveModalWorkflow] = useState('both') // Context for save modal

  // Track dirty state for each form to prevent overwriting user edits
  const isDirtyRef = useRef({
    controls: false,
    camera: false,
    webui: false
  })

  // Initialize forms when data loads - use useEffect to avoid re-render loop
  // Smart sync: only update form from backend when form is clean (not dirty)
  useEffect(() => {
    if (controls && !isDirtyRef.current.controls) {
      setControlsForm(controls)
    }
  }, [controls])

  useEffect(() => {
    if (cameraSettings && !isDirtyRef.current.camera) {
      setCameraForm(cameraSettings)
    }
  }, [cameraSettings])

  useEffect(() => {
    if (webuiSettings && !isDirtyRef.current.webui) {
      setWebuiForm(webuiSettings)
    }
  }, [webuiSettings])

  // Setup WebSocket connection for stream settings reload
  useEffect(() => {
    const wsUrl = `${window.location.protocol}//${window.location.hostname}:${window.location.port || (window.location.protocol === 'https:' ? '443' : '80')}`
    socketRef.current = io(wsUrl, { transports: ['websocket', 'polling'] })

    socketRef.current.on('settings_reloaded', () => {
      // Trigger refetch of webui settings - form will auto-sync if clean
      queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
    })

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect()
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Wrapper functions to mark forms as dirty when updated
  const updateControlsForm = (updates) => {
    isDirtyRef.current.controls = true
    setControlsForm(prev => ({ ...prev, ...updates }))
  }

  const updateCameraForm = (updates) => {
    isDirtyRef.current.camera = true
    setCameraForm(prev => ({ ...prev, ...updates }))
  }

  /**
   * Derives the unified focus mode from AutoCalibration and AfMode CSV values.
   * @returns {'auto-calibrate'|'manual'|'af-single'|'af-continuous'}
   */
  const focusMode = (() => {
    const autoCal = String(cameraForm.AutoCalibration ?? '0') === '1'
    if (autoCal) return CAMERA_SETTINGS.FOCUS_MODES.AUTO_CALIBRATE
    const afMode = String(cameraForm.AfMode ?? CAMERA_SETTINGS.AF_MODE_VALUES.MANUAL)
    if (afMode === CAMERA_SETTINGS.AF_MODE_VALUES.SINGLE) return CAMERA_SETTINGS.FOCUS_MODES.AF_SINGLE
    if (afMode === CAMERA_SETTINGS.AF_MODE_VALUES.CONTINUOUS) return CAMERA_SETTINGS.FOCUS_MODES.AF_CONTINUOUS
    return CAMERA_SETTINGS.FOCUS_MODES.MANUAL
  })()

  /**
   * Updates both AutoCalibration and AfMode CSV fields atomically
   * when the user selects a new focus mode from the dropdown.
   * @param {'auto-calibrate'|'manual'|'af-single'|'af-continuous'} mode
   */
  const handleFocusModeChange = (mode) => {
    const updates = {
      [CAMERA_SETTINGS.FOCUS_MODES.AUTO_CALIBRATE]:  { AutoCalibration: '1', AfMode: CAMERA_SETTINGS.AF_MODE_VALUES.MANUAL },
      [CAMERA_SETTINGS.FOCUS_MODES.MANUAL]:          { AutoCalibration: '0', AfMode: CAMERA_SETTINGS.AF_MODE_VALUES.MANUAL },
      [CAMERA_SETTINGS.FOCUS_MODES.AF_SINGLE]:       { AutoCalibration: '0', AfMode: CAMERA_SETTINGS.AF_MODE_VALUES.SINGLE },
      [CAMERA_SETTINGS.FOCUS_MODES.AF_CONTINUOUS]:    { AutoCalibration: '0', AfMode: CAMERA_SETTINGS.AF_MODE_VALUES.CONTINUOUS },
    }
    updateCameraForm(updates[mode])
  }

  const updateWebuiForm = (updates) => {
    isDirtyRef.current.webui = true
    setWebuiForm(prev => ({ ...prev, ...updates }))
  }

  const handleControlsSubmit = (e) => {
    e.preventDefault()
    updateControlsMutation.mutate(controlsForm)
  }

  // Note: handleCameraSubmit and handleWebuiSubmit removed - settings are now saved via preset Update button

  // Preset management handlers
  // Filter presets by workflow
  const photoPresets = presetsData?.presets?.filter(p => p.workflow === 'photo' || p.workflow === 'both') || []
  const liveViewPresets = presetsData?.presets?.filter(p => p.workflow === 'liveview' || p.workflow === 'video' || p.workflow === 'both') || []

  const selectedPhotoPresetData = presetsData?.presets?.find(p => p.name === selectedPhotoPreset)
  const selectedLiveViewPresetData = presetsData?.presets?.find(p => p.name === selectedLiveViewPreset)

  // Track if presets have been initialized to prevent re-initialization
  const photoPresetInitialized = useRef(false)
  const liveViewPresetInitialized = useRef(false)

  // Silent preset initialization (no toasts) for page load
  const initializePhotoPreset = async (presetName) => {
    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'capture'
      })
      await queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)
    } catch (error) {
      console.error('Failed to initialize photo preset:', error)
      const errorMsg = error.response?.data?.error || error.message

      // If preset not found or workflow mismatch, try to find a valid fallback
      if (errorMsg.includes('not found') || errorMsg.includes('workflow')) {
        console.warn(`Preset "${presetName}" is invalid, trying fallback preset`)
        // Try to apply balanced preset as fallback
        const fallbackPreset = presetsData?.presets?.find(p =>
          (p.workflow === 'photo' || p.workflow === 'both') && p.name === 'balanced'
        )
        if (fallbackPreset) {
          try {
            await applyPresetMutation.mutateAsync({
              name: fallbackPreset.name,
              applyTo: 'capture'
            })
            setSelectedPhotoPreset(fallbackPreset.name)
          } catch (fallbackError) {
            console.error('Failed to apply fallback photo preset:', fallbackError)
            const fallbackDisplayName = fallbackPreset.display_name || fallbackPreset.name
            const fallbackMsg = fallbackError.response?.data?.error || 'Failed to load preset'
            toast.error(`Failed to load fallback preset "${fallbackDisplayName}": ${fallbackMsg}`)
          }
        } else {
          // No fallback available
          const preset = presetsData?.presets?.find(p => p.name === presetName)
          const displayName = preset?.display_name || presetName
          toast.error(`Photo preset "${displayName}" not found and no fallback available`)
        }
      } else {
        // Non-recoverable error (not a preset not found issue)
        const preset = presetsData?.presets?.find(p => p.name === presetName)
        const displayName = preset?.display_name || presetName
        toast.error(`Preset "${displayName}" failed to load: ${errorMsg}`)
      }
    }
  }

  const initializeVideoPreset = async (presetName) => {
    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'liveview'
      })
      await queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
    } catch (error) {
      console.error('Failed to initialize live view preset:', error)
      const errorMsg = error.response?.data?.error || error.message

      // If preset not found or workflow mismatch, try to find a valid fallback
      if (errorMsg.includes('not found') || errorMsg.includes('workflow')) {
        console.warn(`Preset "${presetName}" is invalid, trying fallback preset`)
        // Try to apply balanced preset as fallback
        const fallbackPreset = presetsData?.presets?.find(p =>
          (p.workflow === 'liveview' || p.workflow === 'both') && p.name === 'balanced'
        )
        if (fallbackPreset) {
          try {
            await applyPresetMutation.mutateAsync({
              name: fallbackPreset.name,
              applyTo: 'liveview'
            })
            setSelectedLiveViewPreset(fallbackPreset.name)
          } catch (fallbackError) {
            console.error('Failed to apply fallback liveview preset:', fallbackError)
            const fallbackDisplayName = fallbackPreset.display_name || fallbackPreset.name
            const fallbackMsg = fallbackError.response?.data?.error || 'Failed to load preset'
            toast.error(`Failed to load fallback preset "${fallbackDisplayName}": ${fallbackMsg}`)
          }
        } else {
          // No fallback available
          const preset = presetsData?.presets?.find(p => p.name === presetName)
          const displayName = preset?.display_name || presetName
          toast.error(`Liveview preset "${displayName}" not found and no fallback available`)
        }
      } else {
        // Non-recoverable error (not a preset not found issue)
        const preset = presetsData?.presets?.find(p => p.name === presetName)
        const displayName = preset?.display_name || presetName
        toast.error(`Preset "${displayName}" failed to load: ${errorMsg}`)
      }
    }
  }

  // Initialize with default presets on mount - always have a preset selected
  // Wait for BOTH presetsData and preferences to be loaded to avoid multiple initializations
  useEffect(() => {
    if (presetsData?.presets && preferences && !selectedPhotoPreset && !photoPresetInitialized.current) {
      // Use user's default preference (only if it still exists), or "balanced" as fallback, or first available
      const savedDefault = preferences?.default_capture_preset
      const defaultExists = savedDefault && presetsData.presets.some(p => p.name === savedDefault)

      const defaultPreset = (defaultExists ? savedDefault : null) ||
                           presetsData.presets.find(p => (p.workflow === 'photo' || p.workflow === 'both') && p.name === 'balanced')?.name ||
                           presetsData.presets.find(p => p.workflow === 'photo' || p.workflow === 'both')?.name
      if (defaultPreset) {
        setSelectedPhotoPreset(defaultPreset)
        // Silent initialization - no toast
        initializePhotoPreset(defaultPreset)
        photoPresetInitialized.current = true
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presetsData, preferences]) // Wait for BOTH to be ready

  useEffect(() => {
    if (presetsData?.presets && preferences && !selectedLiveViewPreset && !liveViewPresetInitialized.current) {
      // Use user's default preference (only if it still exists), or "balanced" as fallback, or first available
      const savedDefault = preferences?.default_liveview_preset || preferences?.default_preview_preset
      const defaultExists = savedDefault && presetsData.presets.some(p => p.name === savedDefault)

      const defaultPreset = (defaultExists ? savedDefault : null) ||
                           presetsData.presets.find(p => (p.workflow === 'liveview' || p.workflow === 'both') && p.name === 'balanced')?.name ||
                           presetsData.presets.find(p => p.workflow === 'liveview' || p.workflow === 'both')?.name
      if (defaultPreset) {
        setSelectedLiveViewPreset(defaultPreset)
        // Silent initialization - no toast
        initializeVideoPreset(defaultPreset)
        liveViewPresetInitialized.current = true
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presetsData, preferences]) // Wait for BOTH to be ready

  // Auto-apply preset handlers - apply immediately when preset selected
  const handlePhotoPresetChange = async (e) => {
    const presetName = e.target.value
    setSelectedPhotoPreset(presetName)

    // Immediately apply to backend
    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'capture'
      })
      // Query invalidation triggers form update
      await queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)

      const preset = presetsData?.presets?.find(p => p.name === presetName)
      const displayName = preset?.display_name || presetName

      // Only show toast if not during initial page load
      // photoPresetInitialized is false during first initialization, true after
      if (photoPresetInitialized.current) {
        toast.success(`Applied "${displayName}" preset`)
      }
    } catch (error) {
      const message = error.response?.data?.error || 'Failed to apply preset'
      toast.error(`Apply failed: ${message}`)
    }
  }

  const handleVideoPresetChange = async (e) => {
    const presetName = e.target.value
    setSelectedLiveViewPreset(presetName)

    // Immediately apply to backend
    try {
      await applyPresetMutation.mutateAsync({
        name: presetName,
        applyTo: 'liveview'
      })
      // Query invalidation triggers form update
      await queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)

      const preset = presetsData?.presets?.find(p => p.name === presetName)
      const displayName = preset?.display_name || presetName

      // Only show toast if not during initial page load
      // liveViewPresetInitialized is false during first initialization, true after
      if (liveViewPresetInitialized.current) {
        toast.success(`Applied "${displayName}" preset`)
      }
    } catch (error) {
      const message = error.response?.data?.error || 'Failed to apply preset'
      toast.error(`Apply failed: ${message}`)
    }
  }

  // Update preset handlers - update preset file + apply to backend
  const handleUpdatePhotoPreset = async () => {
    if (!selectedPhotoPreset) return
    if (selectedPhotoPresetData?.category === 'built-in') {
      toast.error('Cannot modify built-in presets. Use "Save As" to create a copy.')
      return
    }

    try {
      // Create preset update payload with current form values
      const presetData = {
        name: selectedPhotoPreset,
        description: selectedPhotoPresetData?.description || '',
        workflow: 'photo',
        settings: {
          camera: cameraForm
        }
      }

      // Update preset file (via POST to /presets endpoint - creates/overwrites)
      await createPresetMutation.mutateAsync(presetData)

      // Apply to backend config
      await updateCameraMutation.mutateAsync(cameraForm)

      const displayName = selectedPhotoPresetData?.display_name || selectedPhotoPreset
      toast.success(`Updated "${displayName}" preset`)
    } catch (error) {
      const message = error.response?.data?.error || 'Failed to update preset'
      toast.error(`Update failed: ${message}`)
    }
  }

  const handleUpdateVideoPreset = async () => {
    if (!selectedLiveViewPreset) return
    if (selectedLiveViewPresetData?.category === 'built-in') {
      toast.error('Cannot modify built-in presets. Use "Save As" to create a copy.')
      return
    }

    try {
      // Validate settings before updating
      const validationErrors = validatePresetSettings(webuiForm)
      if (validationErrors.length > 0) {
        const errorMessage = formatValidationErrors(validationErrors, 3)
        toast.error(errorMessage)
        return
      }

      const presetData = {
        name: selectedLiveViewPreset,
        description: selectedLiveViewPresetData?.description || '',
        workflow: 'liveview',
        settings: {
          liveview: webuiForm
        }
      }

      await createPresetMutation.mutateAsync(presetData)
      await updateWebuiMutation.mutateAsync(webuiForm)

      const displayName = selectedLiveViewPresetData?.display_name || selectedLiveViewPreset
      toast.success(`Updated "${displayName}" preset`)
    } catch (error) {
      const message = error.response?.data?.error || 'Failed to update preset'
      toast.error(`Update failed: ${message}`)
    }
  }

  // Handle Save As (new preset creation from modal)
  const handleSavePreset = async (presetData) => {
    // Validation happens in SavePresetModal before calling this function
    // But we validate again here as a safety check
    const validationErrors = validatePresetSettings(webuiForm)
    if (validationErrors.length > 0) {
      const errorMessage = formatValidationErrors(validationErrors, 3)
      toast.error(errorMessage)
      throw new Error('Validation failed')
    }

    await createPresetMutation.mutateAsync(presetData)
    toast.success(`Preset "${presetData.name}" saved successfully`)
  }

  const handleSetDefaultPhotoPreset = () => {
    if (!selectedPhotoPreset) {
      toast.error('Please select a photo preset first')
      return
    }
    setPreferenceMutation.mutate({
      key: 'default_capture_preset',
      value: selectedPhotoPreset
    })
  }

  const handleSetDefaultVideoPreset = () => {
    if (!selectedLiveViewPreset) {
      toast.error('Please select a live view preset first')
      return
    }
    setPreferenceMutation.mutate({
      key: 'default_liveview_preset',
      value: selectedLiveViewPreset
    })
  }

  const handleDeletePhotoPreset = () => {
    if (!selectedPhotoPreset) return
    if (selectedPhotoPresetData?.category === 'built-in') {
      toast.error('Cannot delete built-in presets')
      return
    }
    if (confirm(`Delete preset "${selectedPhotoPresetData?.display_name}"?`)) {
      deletePresetMutation.mutate(selectedPhotoPreset)
    }
  }

  const handleDeleteVideoPreset = () => {
    if (!selectedLiveViewPreset) return
    if (selectedLiveViewPresetData?.category === 'built-in') {
      toast.error('Cannot delete built-in presets')
      return
    }
    if (confirm(`Delete preset "${selectedLiveViewPresetData?.display_name}"?`)) {
      deletePresetMutation.mutate(selectedLiveViewPreset)
    }
  }

  const handleSavePhotoPreset = () => {
    setSaveModalWorkflow('photo')
    setShowSaveModal(true)
  }

  const handleSaveVideoPreset = () => {
    setSaveModalWorkflow('liveview')
    setShowSaveModal(true)
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
    <div className="max-w-7xl mx-auto space-y-3 px-4 py-2">
      <h2 className="text-xl font-bold text-gray-900">Settings</h2>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-6">
          <button
            onClick={() => setActiveTab('system')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'system'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            System Info
          </button>
          <button
            onClick={() => setActiveTab('controls')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'controls'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Hardware Controls
          </button>
          <button
            onClick={() => setActiveTab('camera')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'camera'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Camera Settings
          </button>
          <button
            onClick={() => setActiveTab('diagnostic')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'diagnostic'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Diagnostic
          </button>
          <button
            onClick={() => setActiveTab('stream')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'stream'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Live View Settings
          </button>
        </nav>
      </div>

      {/* System Info Tab */}
      {activeTab === 'system' && (
        <div className="settings-grid-2col">
          {/* Installation Information Card */}
          <CollapsibleCard
            id="systemInstallation"
            title="📋 Installation Information"
            isCollapsed={collapsedCards.systemInstallation}
            onToggle={toggleCard}
            className="settings-card-lg"
          >
            <div className="space-y-2">
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
                <p className="font-mono text-xs break-all">{systemInfo?.mothbox_home || 'Loading...'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Config Directory</p>
                <p className="font-mono text-xs break-all">{systemInfo?.config_dir || 'Loading...'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Firmware Directory</p>
                <p className="font-mono text-xs break-all">{systemInfo?.firmware_dir || 'Loading...'}</p>
              </div>
            </div>
          </CollapsibleCard>

          {/* GPIO Pin Configuration Card */}
          <CollapsibleCard
            id="systemGPIO"
            title="🔌 GPIO Pin Configuration"
            isCollapsed={collapsedCards.systemGPIO}
            onToggle={toggleCard}
            className="settings-card-lg"
          >
            <p className="text-xs text-gray-600 mb-2">
              Source: <span className="font-medium">{systemInfo?.gpio_source || 'Loading...'}</span>
            </p>
            <div className="space-y-2">
              <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
                <span className="text-sm text-gray-600">Relay Ch1 (Attract Light)</span>
                <span className="font-mono text-lg font-semibold">{systemInfo?.gpio_pins?.Relay_Ch1 || '?'}</span>
              </div>
              <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
                <span className="text-sm text-gray-600">Relay Ch2 (Flash)</span>
                <span className="font-mono text-lg font-semibold">{systemInfo?.gpio_pins?.Relay_Ch2 || '?'}</span>
              </div>
              <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
                <span className="text-sm text-gray-600">Relay Ch3 (UV Light)</span>
                <span className="font-mono text-lg font-semibold">{systemInfo?.gpio_pins?.Relay_Ch3 || '?'}</span>
              </div>
            </div>
            {systemInfo?.gpio_source === 'defaults' && (
              <div className="mt-2 settings-info-box bg-yellow-50 border-yellow-200">
                <p className="text-xs text-yellow-800">
                  ⚠️ Using default GPIO pins. To customize, add Relay_Ch1, Relay_Ch2, and Relay_Ch3 to controls.txt
                </p>
              </div>
            )}
          </CollapsibleCard>

          {/* GPS Configuration Card */}
          <GPSSettings />
        </div>
      )}

      {/* Diagnostic Tab */}
      {activeTab === 'diagnostic' && (
        <div className="space-y-2">
          <CollapsibleCard
            id="diagnosticPaths"
            title="📁 File Paths"
            isCollapsed={collapsedCards.diagnosticPaths}
            onToggle={toggleCard}
            className="settings-card-lg"
          >
            <div className="space-y-1 text-xs font-mono">
              {diagnosticInfo?.paths && Object.entries(diagnosticInfo.paths).map(([key, value]) => (
                <div key={key} className="flex items-start">
                  <span className="text-gray-500 w-48">{key}:</span>
                  <span className={typeof value === 'boolean' ? (value ? 'text-green-600' : 'text-red-600') : ''}>
                    {String(value)}
                  </span>
                </div>
              ))}
            </div>
          </CollapsibleCard>

          <CollapsibleCard
            id="diagnosticControls"
            title="📄 Controls File Content"
            isCollapsed={collapsedCards.diagnosticControls}
            onToggle={toggleCard}
            className="settings-card-lg"
          >
            <div className="space-y-1 text-xs">
              <p>Raw lines: {diagnosticInfo?.controls_content?.raw_lines || 0}</p>
              <p>Parsed keys: {diagnosticInfo?.controls_content?.parsed_keys?.length || 0}</p>
              <p>Has GPIO pins: {diagnosticInfo?.controls_content?.has_gpio_pins ? '✓ Yes' : '✗ No'}</p>
              <div className="mt-1">
                <p className="settings-label">Sample values:</p>
                <div className="settings-info-box bg-gray-50">
                  {diagnosticInfo?.controls_content?.sample_values &&
                    Object.entries(diagnosticInfo.controls_content.sample_values).map(([key, value]) => (
                      <div key={key} className="font-mono settings-help-text">{key}: {value}</div>
                    ))
                  }
                </div>
              </div>
            </div>
          </CollapsibleCard>

          <CollapsibleCard
            id="diagnosticHardware"
            title="🔧 Hardware Modules"
            isCollapsed={collapsedCards.diagnosticHardware}
            onToggle={toggleCard}
            className="settings-card-lg"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {diagnosticInfo?.hardware_config && Object.entries(diagnosticInfo.hardware_config).map(([key, value]) => (
                key.endsWith('_enabled') && (
                  <div key={key} className="settings-info-box border">
                    <p className="settings-help-text text-gray-500">{key.replace('_enabled', '')}</p>
                    <p className={`font-semibold text-xs ${value ? 'text-green-600' : 'text-gray-400'}`}>
                      {value ? 'Enabled' : 'Disabled'}
                    </p>
                  </div>
                )
              ))}
            </div>
          </CollapsibleCard>
        </div>
      )}

      {/* Controls Tab */}
      {activeTab === 'controls' && (
        <div className="settings-card-lg">
          <h3 className="settings-section-title">Hardware Configuration</h3>
          <form onSubmit={handleControlsSubmit} className="space-y-2">
            {Object.entries(controlsForm).map(([key, value]) => (
              <div key={key} className="settings-form-group">
                <label className="settings-label">
                  {key}
                </label>
                <input
                  type="text"
                  value={value}
                  onChange={(e) => updateControlsForm({ [key]: e.target.value })}
                  className="settings-input"
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={updateControlsMutation.isPending}
              className="settings-button"
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
        <div className="space-y-2">
          <div className="bg-gradient-to-r from-blue-100 to-indigo-100 rounded-lg shadow-sm p-2 border border-blue-200">
            <h3 className="text-base font-semibold text-gray-900">Full-Resolution Capture Configuration</h3>
            <p className="text-xs text-gray-700">
              These settings control full-resolution photo captures (not live view). Changes take effect on next photo.
            </p>
          </div>

          {/* Photo Preset Management Section */}
          <CollapsibleCard
            id="cameraPreset"
            title="📸 Photo Capture Presets"
            isCollapsed={collapsedCards.cameraPreset}
            onToggle={toggleCard}
            className="settings-card-lg"
          >
            <div className="p-3 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-lg">
            <p className="settings-help-text mb-2">
              Select a preset to load and apply capture settings. Edit values, then click Update to save changes.
            </p>

            <div className="space-y-2">
              {/* Photo Preset Selector */}
              <div className="settings-form-group">
                <label className="settings-label">
                  Photo Preset
                </label>
                <select
                  value={selectedPhotoPreset}
                  onChange={handlePhotoPresetChange}
                  disabled={presetsLoading || applyPresetMutation.isPending}
                  className="settings-select"
                >
                  {photoPresets.map(p => (
                    <option key={p.name} value={p.name}>
                      {p.display_name}
                    </option>
                  ))}
                </select>
                {selectedPhotoPresetData && (
                  <p className="settings-help-text italic">
                    {selectedPhotoPresetData.description}
                  </p>
                )}
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-3 gap-1">
                {selectedPhotoPresetData?.category === 'user' && (
                  <button
                    type="button"
                    onClick={handleUpdatePhotoPreset}
                    disabled={updateCameraMutation.isPending || createPresetMutation.isPending}
                    className="settings-button-sm bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    ✓ Update
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleSetDefaultPhotoPreset}
                  disabled={!selectedPhotoPreset || setPreferenceMutation.isPending}
                  className="settings-button-sm bg-yellow-500 text-white hover:bg-yellow-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  ⭐ Default
                </button>
                <button
                  type="button"
                  onClick={handleSavePhotoPreset}
                  disabled={createPresetMutation.isPending}
                  className="settings-button-sm bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  💾 Save As
                </button>
              </div>

              {/* Delete Button (for user presets) */}
              {selectedPhotoPreset && selectedPhotoPresetData?.category === 'user' && (
                <button
                  type="button"
                  onClick={handleDeletePhotoPreset}
                  disabled={deletePresetMutation.isPending}
                  className="w-full settings-button-sm bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-300"
                >
                  🗑️ Delete
                </button>
              )}
            </div>
            </div>
          </CollapsibleCard>

          <div className="space-y-2">
            {/* Grid container for settings cards */}
            <div className="settings-grid">
              {/* Exposure Card */}
              <CollapsibleCard
                id="cameraExposure"
                title="📷 Exposure"
                isCollapsed={collapsedCards.cameraExposure}
                onToggle={toggleCard}
                className="settings-card"
              >

              {/* AeEnable Toggle */}
              <div className="settings-form-group">
                <label className="settings-label">
                  Exposure Mode
                </label>
                <select
                  value={cameraForm.AeEnable !== undefined ? cameraForm.AeEnable : 'True'}
                  onChange={(e) => setCameraForm({ ...cameraForm, AeEnable: e.target.value })}
                  className="settings-select"
                >
                  <option value="True">✨ Auto</option>
                  <option value="False">🔧 Manual</option>
                </select>
                <p className="settings-help-text">
                  {cameraForm.AeEnable === 'False' || cameraForm.AeEnable === false
                    ? 'Manual mode: You control exposure time and gain directly'
                    : 'Auto mode: Camera automatically adjusts exposure based on scene brightness'}
                </p>
              </div>

              {/* Manual Mode Controls - Show only when AeEnable is False */}
              {(cameraForm.AeEnable === 'False' || cameraForm.AeEnable === false) && (
                <>
                  {/* Exposure Time */}
                  <div className="settings-form-group">
                    <label className="settings-label">
                      Exposure Time: {cameraForm.ExposureTime || 0} µs
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="1"
                      value={(() => {
                        // Convert exposure time to logarithmic slider position (base-2)
                        const exposure = parseInt(cameraForm.ExposureTime) || 500
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
                        setCameraForm({ ...cameraForm, ExposureTime: exposureTime })
                      }}
                      className="w-full cursor-pointer"
                    />
                    <div className="flex justify-between settings-help-text">
                      <span>100µs</span>
                      <span>3ms</span>
                      <span>200ms</span>
                    </div>
                    <p className="settings-help-text">
                      Logarithmic scale: each step ≈ doubles exposure time (one photographic stop)
                    </p>
                  </div>

                  {/* Analogue Gain */}
                  <div className="settings-form-group">
                    <label className="settings-label">
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
                    <div className="flex justify-between settings-help-text">
                      <span>1x (Clean)</span>
                      <span>8x</span>
                      <span>16x (Noisy)</span>
                    </div>
                    <p className="settings-help-text">
                      Higher ISO = brighter but more noise
                    </p>
                  </div>
                </>
              )}

              {/* Auto Mode Controls - Show only when AeEnable is True */}
              {(cameraForm.AeEnable === 'True' || cameraForm.AeEnable === true || cameraForm.AeEnable === undefined) && (
                <div className="settings-form-group">
                  <label className="settings-label">
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
                  <div className="flex justify-between settings-help-text">
                    <span>-8 EV (Much darker)</span>
                    <span>0 EV</span>
                    <span>+8 EV (Much brighter)</span>
                  </div>
                  <p className="settings-help-text">
                    Adjust auto-exposure bias (positive = brighter, negative = darker)
                  </p>
                </div>
              )}
              </CollapsibleCard>
            </div>

            {/* HDR/Bracketing and Focus Bracketing - full width row */}
            <div className="settings-grid-2col">
              {/* HDR/Bracketing Card */}
              <CollapsibleCard
                id="cameraHDR"
                title="🌄 HDR Bracketing"
                isCollapsed={collapsedCards.cameraHDR}
                onToggle={toggleCard}
                className="settings-card"
              >
              <p className="settings-help-text mb-2">
                Multiple exposures for detail
              </p>

              {/* HDR Count */}
              <div className="settings-form-group">
                <label htmlFor="hdr_count" className="settings-label">
                  Number of Exposures
                </label>
                <select
                  id="hdr_count"
                  value={cameraForm.HDR || '1'}
                  onChange={(e) => updateCameraForm({ HDR: e.target.value})}
                  className="settings-select"
                >
                  <option value="1">Single Exposure (No HDR)</option>
                  <option value="3">3 Exposures (Standard HDR)</option>
                  <option value="5">5 Exposures (Extended HDR)</option>
                  <option value="7">7 Exposures (Maximum HDR)</option>
                </select>
                <p className="settings-help-text">
                  More exposures = better dynamic range, but slower capture
                </p>
              </div>

              {/* HDR Bracket Step (only if HDR enabled) */}
              {(parseInt(cameraForm.HDR) > 1) && (
                <div className="settings-form-group">
                  <label className="settings-label">
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
                  <div className="flex justify-between settings-help-text">
                    <span>1ms (Small steps)</span>
                    <span>25ms</span>
                    <span>50ms (Large steps)</span>
                  </div>
                  <p className="settings-help-text">
                    Distance between exposure times in the bracket
                  </p>
                </div>
              )}
              </CollapsibleCard>

              {/* Focus Bracketing Card */}
              <CollapsibleCard
                id="cameraFocusBracket"
                title="🎯 Focus Bracketing"
                isCollapsed={collapsedCards.cameraFocusBracket}
                onToggle={toggleCard}
                className="settings-card"
              >
              <p className="settings-help-text mb-2">
                Multiple photos at different focus positions
              </p>

              {/* Focus Bracket Steps */}
              <div className="settings-form-group">
                <label htmlFor="focus_bracket_steps" className="settings-label">
                  Number of Focus Steps
                </label>
                <select
                  id="focus_bracket_steps"
                  value={cameraForm.FocusBracket || '1'}
                  onChange={(e) => updateCameraForm({ FocusBracket: e.target.value})}
                  className="settings-select"
                >
                  <option value="1">Single Focus (No Bracketing)</option>
                  <option value="3">3 Steps</option>
                  <option value="5">5 Steps (Recommended)</option>
                  <option value="7">7 Steps</option>
                  <option value="10">10 Steps (Maximum)</option>
                </select>
                <p className="settings-help-text">
                  More steps = greater depth coverage, but slower capture
                </p>
              </div>

              {/* Focus Range (only if Focus Bracketing enabled) */}
              {(parseInt(cameraForm.FocusBracket) > 1) && (
                <>
                  <div className="settings-form-group">
                    <label className="settings-label">
                      Focus Start Position: {parseFloat(cameraForm.FocusBracket_Start || 2.0).toFixed(1)} diopters
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="10"
                      step="0.5"
                      value={cameraForm.FocusBracket_Start || 2.0}
                      onChange={(e) => setCameraForm({ ...cameraForm, FocusBracket_Start: e.target.value })}
                      className="w-full cursor-pointer"
                    />
                    <div className="flex justify-between settings-help-text">
                      <span>0 (Far)</span>
                      <span>5</span>
                      <span>10 (Near)</span>
                    </div>
                    <p className="settings-help-text">
                      Starting focus distance (lower = farther)
                    </p>
                  </div>

                  <div className="settings-form-group">
                    <label className="settings-label">
                      Focus End Position: {parseFloat(cameraForm.FocusBracket_End || 8.0).toFixed(1)} diopters
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="10"
                      step="0.5"
                      value={cameraForm.FocusBracket_End || 8.0}
                      onChange={(e) => setCameraForm({ ...cameraForm, FocusBracket_End: e.target.value })}
                      className="w-full cursor-pointer"
                    />
                    <div className="flex justify-between settings-help-text">
                      <span>0 (Far)</span>
                      <span>5</span>
                      <span>10 (Near)</span>
                    </div>
                    <p className="settings-help-text">
                      Ending focus distance (higher = closer)
                    </p>
                  </div>

                  {/* Diopter Distance Guide */}
                  <div className="settings-info-box bg-gray-50 border-gray-300">
                    <p className="settings-help-text-xs font-semibold text-gray-700 mb-1">📏 Diopter Distance Reference:</p>
                    <div className="grid grid-cols-2 gap-1 settings-help-text text-gray-600">
                      <div><span className="font-medium">0:</span> Infinity (landscape)</div>
                      <div><span className="font-medium">2:</span> ~50cm (background)</div>
                      <div><span className="font-medium">5:</span> ~20cm (mid-range)</div>
                      <div><span className="font-medium">8:</span> ~12cm (macro)</div>
                      <div><span className="font-medium">10:</span> ~10cm (extreme macro)</div>
                    </div>
                  </div>

                  <div className="settings-info-box bg-blue-50 border-blue-200">
                    <p className="settings-help-text-xs text-blue-800">
                      <strong>Tip:</strong> For insect photography, try Start=2.0, End=8.0 to cover macro to mid-range distances.
                      Focus bracketing takes priority over HDR when both are enabled.
                    </p>
                  </div>

                  {/* Advanced Focus Bracketing Settings - Collapsible */}
                  <details className="mt-4 border border-gray-300 rounded-lg">
                    <summary className="cursor-pointer px-4 py-3 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium text-gray-700">
                      ⚙️ Advanced Settings (Timing & Colour)
                    </summary>

                    <div className="p-4 space-y-4">
                      {/* Timing Controls Section */}
                      <div>
                        <h5 className="text-sm font-semibold text-gray-800 mb-3">⏱️ Timing Controls</h5>

                        {/* Flash Delay Before Capture */}
                        <div className="settings-form-group">
                          <label className="settings-label">
                            Flash Delay (Before Capture): {parseInt(cameraForm.FlashDelay_BeforeCapture || 50)} ms
                          </label>
                          <input
                            type="range"
                            min="0"
                            max="500"
                            step="10"
                            value={cameraForm.FlashDelay_BeforeCapture || 50}
                            onChange={(e) => setCameraForm({ ...cameraForm, FlashDelay_BeforeCapture: e.target.value })}
                            className="w-full cursor-pointer"
                          />
                          <div className="flex justify-between settings-help-text">
                            <span>0ms (instant)</span>
                            <span>250ms</span>
                            <span>500ms</span>
                          </div>
                          <p className="settings-help-text">
                            Time to wait after turning flash on, before capturing. Allows flash to reach full brightness.
                          </p>
                        </div>

                        {/* Flash Delay After Capture */}
                        <div className="settings-form-group">
                          <label className="settings-label">
                            Flash Delay (After Capture): {parseInt(cameraForm.FlashDelay_AfterCapture || 0)} ms
                          </label>
                          <input
                            type="range"
                            min="0"
                            max="500"
                            step="10"
                            value={cameraForm.FlashDelay_AfterCapture || 0}
                            onChange={(e) => setCameraForm({ ...cameraForm, FlashDelay_AfterCapture: e.target.value })}
                            className="w-full cursor-pointer"
                          />
                          <div className="flex justify-between settings-help-text">
                            <span>0ms (instant)</span>
                            <span>250ms</span>
                            <span>500ms</span>
                          </div>
                          <p className="settings-help-text">
                            Optional delay after capture before turning flash off. Usually 0ms is fine.
                          </p>
                        </div>

                        {/* Lens Settle Delay */}
                        <div className="settings-form-group">
                          <label className="settings-label">
                            Lens Settle Delay: {parseInt(cameraForm.FocusBracket_SettleDelay || 500)} ms
                          </label>
                          <input
                            type="range"
                            min="100"
                            max="2000"
                            step="50"
                            value={cameraForm.FocusBracket_SettleDelay || 500}
                            onChange={(e) => setCameraForm({ ...cameraForm, FocusBracket_SettleDelay: e.target.value })}
                            className="w-full cursor-pointer"
                          />
                          <div className="flex justify-between settings-help-text">
                            <span>100ms (fast)</span>
                            <span>500ms</span>
                            <span>2000ms (slow)</span>
                          </div>
                          <p className="settings-help-text">
                            Time to wait after changing focus position for lens to stabilize. Longer = sharper, but slower.
                          </p>
                        </div>
                      </div>

                      {/* Colour Consistency Section */}
                      <div className="pt-4 border-t border-gray-200">
                        <h5 className="text-sm font-semibold text-gray-800 mb-3">🎨 Colour Consistency</h5>

                        {/* Lock Colour Gains Toggle */}
                        <div className="settings-form-group">
                          <label className="flex items-center space-x-3 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={parseInt(cameraForm.FocusBracket_LockColorGains || 1) === 1}
                              onChange={(e) => setCameraForm({
                                ...cameraForm,
                                FocusBracket_LockColorGains: e.target.checked ? '1' : '0'
                              })}
                              className="settings-checkbox"
                            />
                            <div>
                              <span className="settings-label mb-0">Lock Colour Gains</span>
                              <p className="settings-help-text">
                                Ensures consistent colour across all focus bracket images (recommended for stacking)
                              </p>
                            </div>
                          </label>
                        </div>

                        {/* Colour Gain Controls (only if locked) */}
                        {parseInt(cameraForm.FocusBracket_LockColorGains || 1) === 1 && (
                          <>
                            <div className="settings-form-group pl-8">
                              <label className="settings-label">
                                Red Gain: {parseFloat(cameraForm.FocusBracket_ColorGainRed || 2.259).toFixed(3)}
                              </label>
                              <input
                                type="range"
                                min="1.0"
                                max="4.0"
                                step="0.01"
                                value={cameraForm.FocusBracket_ColorGainRed || 2.259}
                                onChange={(e) => setCameraForm({ ...cameraForm, FocusBracket_ColorGainRed: e.target.value })}
                                className="w-full cursor-pointer"
                              />
                              <div className="flex justify-between settings-help-text">
                                <span>1.0 (cool)</span>
                                <span>2.5</span>
                                <span>4.0 (warm)</span>
                              </div>
                            </div>

                            <div className="settings-form-group pl-8">
                              <label className="settings-label">
                                Blue Gain: {parseFloat(cameraForm.FocusBracket_ColorGainBlue || 1.500).toFixed(3)}
                              </label>
                              <input
                                type="range"
                                min="1.0"
                                max="4.0"
                                step="0.01"
                                value={cameraForm.FocusBracket_ColorGainBlue || 1.500}
                                onChange={(e) => setCameraForm({ ...cameraForm, FocusBracket_ColorGainBlue: e.target.value })}
                                className="w-full cursor-pointer"
                              />
                              <div className="flex justify-between settings-help-text">
                                <span>1.0 (warm)</span>
                                <span>2.5</span>
                                <span>4.0 (cool)</span>
                              </div>
                            </div>

                            <div className="settings-info-box bg-yellow-50 border-yellow-200 pl-8">
                              <p className="settings-help-text text-yellow-800">
                                <strong>Note:</strong> Locked gains ensure uniform colour when combining images in focus stacking software
                                (e.g., Helicon Focus, Zerene Stacker). Leave defaults unless you need specific white balance.
                              </p>
                            </div>
                          </>
                        )}

                        {/* AWB Info when not locked */}
                        {parseInt(cameraForm.FocusBracket_LockColorGains || 1) === 0 && (
                          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                            <p className="text-xs text-blue-800">
                              When unlocked, each focus bracket image uses auto white balance (AWB).
                              Colour may vary slightly between images based on lighting conditions during capture.
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </details>
                </>
              )}
              </CollapsibleCard>
            </div>

            {/* Third row of grid */}
            <div className="settings-grid">
              {/* Focus Strategy Card */}
              <CollapsibleCard
                id="cameraFocusStrategy"
                title="Focus Strategy"
                isCollapsed={collapsedCards.cameraFocusStrategy}
                onToggle={toggleCard}
                className="settings-card"
              >
              <div data-testid="focus-strategy-card">

              {/* Focus Mode Selector */}
              <div className="settings-form-group">
                <label htmlFor="focus_mode" className="settings-label">
                  Focus Mode
                </label>
                <select
                  id="focus_mode"
                  data-testid="focus-mode-select"
                  aria-label="Focus strategy mode"
                  aria-describedby="focus-mode-help"
                  value={focusMode}
                  onChange={(e) => handleFocusModeChange(e.target.value)}
                  className="settings-select"
                >
                  <option value={CAMERA_SETTINGS.FOCUS_MODES.AUTO_CALIBRATE}>Auto-Calibrate</option>
                  <option value={CAMERA_SETTINGS.FOCUS_MODES.MANUAL}>Manual Focus</option>
                  <option value={CAMERA_SETTINGS.FOCUS_MODES.AF_SINGLE}>Autofocus (Single)</option>
                  <option value={CAMERA_SETTINGS.FOCUS_MODES.AF_CONTINUOUS}>Autofocus (Continuous)</option>
                </select>
                <p id="focus-mode-help" className="settings-help-text">
                  {{
                    [CAMERA_SETTINGS.FOCUS_MODES.AUTO_CALIBRATE]: 'Automatically optimizes focus position periodically. Recommended for unattended operation.',
                    [CAMERA_SETTINGS.FOCUS_MODES.MANUAL]: 'Set a fixed focus distance. Best when camera-to-subject distance is constant.',
                    [CAMERA_SETTINGS.FOCUS_MODES.AF_SINGLE]: 'Runs autofocus once before each capture. Good for varying distances.',
                    [CAMERA_SETTINGS.FOCUS_MODES.AF_CONTINUOUS]: 'Continuously adjusts focus. Uses more power but adapts to movement.',
                  }[focusMode]}
                </p>
              </div>

              {/* Auto-Calibrate sub-controls */}
              {focusMode === CAMERA_SETTINGS.FOCUS_MODES.AUTO_CALIBRATE && (
                <div className="p-2 bg-green-50 border border-green-200 rounded space-y-2">
                  <div className="settings-form-group">
                    <label className="settings-label">
                      Calibration Interval: Every {cameraForm.AutoCalibrationPeriod || CAMERA_SETTINGS.CALIBRATION_INTERVAL.DEFAULT} seconds
                    </label>
                    <input
                      type="range"
                      data-testid="calibration-interval-slider"
                      aria-label="Calibration interval in seconds"
                      aria-describedby="calibration-interval-help"
                      min={CAMERA_SETTINGS.CALIBRATION_INTERVAL.MIN}
                      max={CAMERA_SETTINGS.CALIBRATION_INTERVAL.MAX}
                      value={cameraForm.AutoCalibrationPeriod || CAMERA_SETTINGS.CALIBRATION_INTERVAL.DEFAULT}
                      onChange={(e) => updateCameraForm({ AutoCalibrationPeriod: e.target.value })}
                      className="w-full cursor-pointer"
                    />
                    <div className="flex justify-between settings-help-text">
                      <span>{CAMERA_SETTINGS.CALIBRATION_INTERVAL.MIN}</span>
                      <span>500</span>
                      <span>{CAMERA_SETTINGS.CALIBRATION_INTERVAL.MAX}</span>
                    </div>
                    <p id="calibration-interval-help" className="settings-help-text">
                      More frequent = better adaptation to changing conditions
                    </p>
                  </div>

                  {/* Show current calibrated position as read-only */}
                  <div className="settings-form-group" data-testid="calibration-position-display">
                    <label className="settings-label">
                      Current Calibrated Position: {parseFloat(cameraForm.LensPosition || CAMERA_SETTINGS.LENS_POSITION.DEFAULT).toFixed(2)} diopters
                    </label>
                    <div className="w-full bg-gray-200 rounded h-2">
                      <div
                        className="bg-green-500 rounded h-2"
                        style={{ width: `${(Math.min(Math.max(parseFloat(cameraForm.LensPosition || CAMERA_SETTINGS.LENS_POSITION.DEFAULT), CAMERA_SETTINGS.LENS_POSITION.MIN), CAMERA_SETTINGS.LENS_POSITION.MAX) / CAMERA_SETTINGS.LENS_POSITION.MAX) * 100}%` }}
                      />
                    </div>
                    <div className="flex justify-between settings-help-text">
                      <span>{CAMERA_SETTINGS.LENS_POSITION.MIN} (Far)</span>
                      <span>{CAMERA_SETTINGS.LENS_POSITION.MAX / 2}</span>
                      <span>{CAMERA_SETTINGS.LENS_POSITION.MAX} (Near)</span>
                    </div>
                    <p className="settings-help-text">
                      Updated after each calibration cycle
                    </p>
                  </div>
                </div>
              )}

              {/* Manual Focus sub-controls */}
              {focusMode === CAMERA_SETTINGS.FOCUS_MODES.MANUAL && (
                <div className="settings-form-group">
                  <label className="settings-label">
                    Focus Position: {parseFloat(cameraForm.LensPosition || CAMERA_SETTINGS.LENS_POSITION.DEFAULT).toFixed(2)} diopters
                  </label>
                  <input
                    type="range"
                    data-testid="lens-position-slider"
                    aria-label="Focus position in diopters"
                    aria-describedby="lens-position-help"
                    min={CAMERA_SETTINGS.LENS_POSITION.MIN}
                    max={CAMERA_SETTINGS.LENS_POSITION.MAX}
                    step={CAMERA_SETTINGS.LENS_POSITION.STEP}
                    value={cameraForm.LensPosition || CAMERA_SETTINGS.LENS_POSITION.DEFAULT}
                    onChange={(e) => updateCameraForm({ LensPosition: e.target.value })}
                    className="w-full cursor-pointer"
                  />
                  <div className="flex justify-between settings-help-text">
                    <span>{CAMERA_SETTINGS.LENS_POSITION.MIN} (Far)</span>
                    <span>{CAMERA_SETTINGS.LENS_POSITION.MAX / 2}</span>
                    <span>{CAMERA_SETTINGS.LENS_POSITION.MAX} (Near)</span>
                  </div>
                  <p id="lens-position-help" className="settings-help-text">
                    Higher values = closer focus distance.
                  </p>
                </div>
              )}

              {/* Autofocus sub-controls (Single or Continuous) */}
              {(focusMode === CAMERA_SETTINGS.FOCUS_MODES.AF_SINGLE || focusMode === CAMERA_SETTINGS.FOCUS_MODES.AF_CONTINUOUS) && (
                <div className="space-y-2">
                  <div className="settings-form-group">
                    <label htmlFor="af_range_capture" className="settings-label">
                      Focus Range
                    </label>
                    <select
                      id="af_range_capture"
                      data-testid="af-range-select"
                      value={cameraForm.AfRange || CAMERA_SETTINGS.AF_RANGE_VALUES.MACRO}
                      onChange={(e) => updateCameraForm({ AfRange: e.target.value})}
                      className="settings-select"
                    >
                      <option value={CAMERA_SETTINGS.AF_RANGE_VALUES.NORMAL}>Normal (0.5m - infinity)</option>
                      <option value={CAMERA_SETTINGS.AF_RANGE_VALUES.MACRO}>Macro (10cm - 50cm) - For insects</option>
                      <option value={CAMERA_SETTINGS.AF_RANGE_VALUES.FULL}>Full (10cm - infinity)</option>
                    </select>
                  </div>

                  <div className="settings-form-group">
                    <label htmlFor="af_speed_capture" className="settings-label">
                      Focus Speed
                    </label>
                    <select
                      id="af_speed_capture"
                      data-testid="af-speed-select"
                      value={cameraForm.AfSpeed || CAMERA_SETTINGS.AF_SPEED_VALUES.FAST}
                      onChange={(e) => updateCameraForm({ AfSpeed: e.target.value})}
                      className="settings-select"
                    >
                      <option value={CAMERA_SETTINGS.AF_SPEED_VALUES.NORMAL}>Normal (Accurate)</option>
                      <option value={CAMERA_SETTINGS.AF_SPEED_VALUES.FAST}>Fast</option>
                    </select>
                  </div>
                </div>
              )}

              </div>
              </CollapsibleCard>

              {/* Image Format Card */}
              <CollapsibleCard
                id="cameraFormat"
                title="🖼️ Format"
                isCollapsed={collapsedCards.cameraFormat}
                onToggle={toggleCard}
                className="settings-card"
              >

              {/* File Type */}
              <div className="settings-form-group">
                <label htmlFor="image_file_type" className="settings-label">
                  File Format
                </label>
                <select
                  id="image_file_type"
                  value={cameraForm.ImageFileType || '0'}
                  onChange={(e) => updateCameraForm({ ImageFileType: e.target.value})}
                  className="settings-select"
                >
                  <option value="0">JPEG (Fast, compressed) - Recommended</option>
                  <option value="1">TIFF (Lossless, with EXIF metadata)</option>
                  <option value="2">BMP (Huge files, very fast)</option>
                </select>
                <p className="settings-help-text">
                  JPEG is best for most uses. TIFF preserves all detail with full EXIF metadata for machine vision.
                </p>
              </div>

              {/* Vertical Flip */}
              <div className="settings-form-group">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={cameraForm.VerticalFlip === '1' || cameraForm.VerticalFlip === 1}
                    onChange={(e) => updateCameraForm({ VerticalFlip: e.target.checked ? '1' : '0'})}
                    className="settings-checkbox"
                  />
                  <span className="ml-2 settings-label mb-0">
                    Flip Image Vertically
                  </span>
                </label>
                <p className="settings-help-text ml-6">
                  Enable if camera is mounted upside-down
                </p>
              </div>
              </CollapsibleCard>
            </div>

            {/* Advanced/Other Settings - full width */}
            <CollapsibleCard
              id="cameraAdvanced"
              title="⚙️ Advanced"
              isCollapsed={collapsedCards.cameraAdvanced}
              onToggle={toggleCard}
              className="settings-card"
            >
              <div className="mt-2 space-y-2">
                {Object.entries(cameraForm)
                  .filter(([key]) => !['AutoCalibration', 'AutoCalibrationPeriod', 'ExposureTime', 'AnalogueGain',
                    'ExposureValue', 'HDR', 'HDR_width', 'FocusBracket', 'FocusBracket_Start', 'FocusBracket_End',
                    'AfMode', 'LensPosition', 'AfRange', 'AfSpeed', 'ImageFileType', 'VerticalFlip'].includes(key))
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
            </CollapsibleCard>

            {/* Info Box and Submit Button - full width */}
            <div className="settings-card space-y-2">
              <div className="settings-info-box bg-yellow-50 border-yellow-200">
              <p className="text-xs text-yellow-800">
                <strong>Note:</strong> Full-resolution captures only. Use Auto-Calibrate mode or Camera page to test.
              </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Live View Settings Tab */}
      {activeTab === 'stream' && (
        <div className="space-y-2">
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

          <div className="space-y-2">
            {/* Grid container for settings cards */}
            {/* Live View Preset Section - Full Width Inline */}
            <div className="settings-card">
              <div className="flex items-center gap-4">
                <h4 className="settings-card-title mb-0 whitespace-nowrap">🎥 Live View Preset</h4>
                <select
                  value={selectedLiveViewPreset}
                  onChange={handleVideoPresetChange}
                  disabled={presetsLoading || applyPresetMutation.isPending}
                  className="settings-select flex-1"
                >
                  {liveViewPresets.map(p => (
                    <option key={p.name} value={p.name}>
                      {p.display_name}
                    </option>
                  ))}
                </select>
                {selectedLiveViewPresetData && (
                  <p className="text-xs text-gray-600 italic ml-2">
                    {selectedLiveViewPresetData.description}
                  </p>
                )}
                <div className="flex gap-2">
                  {selectedLiveViewPresetData?.category === 'user' && (
                    <button
                      type="button"
                      onClick={handleUpdateVideoPreset}
                      disabled={updateWebuiMutation.isPending || createPresetMutation.isPending}
                      className="settings-button-sm bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                    >
                      ✓ Update
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handleSetDefaultVideoPreset}
                    disabled={!selectedLiveViewPreset || setPreferenceMutation.isPending}
                    className="settings-button-sm bg-yellow-500 text-white hover:bg-yellow-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    ⭐ Default
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveVideoPreset}
                    disabled={createPresetMutation.isPending}
                    className="settings-button-sm bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    💾 Save As
                  </button>
                  {selectedLiveViewPreset && selectedLiveViewPresetData?.category === 'user' && (
                    <button
                      type="button"
                      onClick={handleDeleteVideoPreset}
                      disabled={deletePresetMutation.isPending}
                      className="settings-button-sm bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-300"
                    >
                      🗑️
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="settings-grid">

              {/* Resolution & Encoding Card */}
              <CollapsibleCard
                id="streamResolution"
                title="📐 Resolution & Encoding"
                isCollapsed={collapsedCards.streamResolution}
                onToggle={toggleCard}
                className="settings-card"
              >

                {/* Resolution Preset Selector */}
                <div className="settings-form-group">
              <label className="settings-label">
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
                className="settings-select"
              >
                {resolutionPresets.map((preset) => (
                  <option key={preset.label} value={`${preset.width}x${preset.height}`}>
                    {preset.label}
                  </option>
                ))}
              </select>
              <p className="settings-help-text">
                Current: {webuiForm.stream_width} x {webuiForm.stream_height}
              </p>
            </div>

            {/* Frame Rate Slider */}
            <div className="settings-form-group">
              <label className="settings-label">
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
              <div className="flex justify-between settings-help-text">
                <span>1 FPS (Slow)</span>
                <span>15 FPS</span>
                <span>30 FPS (Fast)</span>
              </div>
              <p className="settings-help-text">
                Lower frame rates reduce CPU and network usage
              </p>
            </div>

            {/* JPEG Quality Slider */}
            <div className="settings-form-group">
              <label className="settings-label">
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
              <div className="flex justify-between settings-help-text">
                <span>50% (Lower quality, faster)</span>
                <span>75%</span>
                <span>100% (Best quality)</span>
              </div>
              <p className="settings-help-text">
                Higher quality produces sharper images but uses more bandwidth
              </p>
            </div>

            {/* Encoding Mode */}
            <div className="settings-form-group">
              <label htmlFor="stream_mode" className="settings-label">
                Encoding Mode
              </label>
              <select
                id="stream_mode"
                value={webuiForm.stream_mode || 'simplejpeg'}
                onChange={(e) => updateWebuiForm({ stream_mode: e.target.value})}
                className="settings-select"
              >
                <option value="simplejpeg">Fast Software (simplejpeg) - Recommended</option>
                <option value="mjpeg_hardware">Hardware MJPEG (Experimental)</option>
              </select>
              <p className="settings-help-text">
                simplejpeg provides 5-7x faster encoding than PIL. Hardware MJPEG is experimental and may offer lower latency.
              </p>
            </div>

            {/* Sensor Mode / Field of View */}
            <div className="settings-form-group">
              <label htmlFor="sensor_mode" className="settings-label">
                Sensor Mode (Field of View)
              </label>
              <select
                id="sensor_mode"
                value={webuiForm.sensor_mode || 'auto'}
                onChange={(e) => updateWebuiForm({ sensor_mode: e.target.value})}
                className="settings-select"
              >
                <option value="auto">Auto (Default)</option>
                <option value="4:3">4:3 Wide (Wider FOV)</option>
                <option value="16:9">16:9 Standard</option>
                <option value="full">Full Sensor (Maximum FOV)</option>
              </select>
              <p className="settings-help-text">
                Controls the camera sensor crop mode and field of view.
                Use <strong>4:3 Wide</strong> for maximum vertical coverage at 1920x1080 output resolution.
                <strong>Auto</strong> mode may crop to 16:9 when using 1920x1080 resolution.
              </p>
            </div>
              </CollapsibleCard>

              {/* Image Quality Card */}
              <CollapsibleCard
                id="streamImageQuality"
                title="📸 Image Quality"
                isCollapsed={collapsedCards.streamImageQuality}
                onToggle={toggleCard}
                className="settings-card"
              >
                <div className="settings-grid-2col">

                {/* Sharpness Slider */}
                <div className="settings-form-group">
                <label className="settings-label">
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
                <div className="flex justify-between settings-help-text">
                  <span>0.0 (Soft)</span>
                  <span>1.0 (Default)</span>
                  <span>4.0 (Sharp)</span>
                </div>
                <p className="settings-help-text">
                  Increase for more detail, decrease for softer images. 1.0 is the normal setting.
                </p>
              </div>

              {/* Brightness Slider */}
              <div className="settings-form-group">
                <label className="settings-label">
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
                <div className="flex justify-between settings-help-text">
                  <span>-1.0 (Darker)</span>
                  <span>0.0 (Default)</span>
                  <span>+1.0 (Brighter)</span>
                </div>
                <p className="settings-help-text">
                  Adjust overall image brightness
                </p>
              </div>

              {/* Contrast Slider */}
              <div className="settings-form-group">
                <label className="settings-label">
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
                <div className="flex justify-between settings-help-text">
                  <span>0.0 (Flat)</span>
                  <span>1.0 (Default)</span>
                  <span>4.0 (High)</span>
                </div>
                <p className="settings-help-text">
                  Adjust difference between light and dark areas. 0.0 = no contrast, 1.0 = normal.
                </p>
              </div>

              {/* Saturation Slider */}
              <div className="settings-form-group">
                <label className="settings-label">
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
                <div className="flex justify-between settings-help-text">
                  <span>0.0 (Grayscale)</span>
                  <span>1.0 (Default)</span>
                  <span>4.0 (Vivid)</span>
                </div>
                <p className="settings-help-text">
                  Adjust colour intensity. 0.0 = grayscale, 1.0 = normal saturation.
                </p>
              </div>

              {/* Noise Reduction Mode Dropdown */}
              <div className="settings-form-group">
                <label htmlFor="noise_reduction_mode" className="settings-label">
                  Noise Reduction Mode
                </label>
                <select
                  id="noise_reduction_mode"
                  value={webuiForm.noise_reduction_mode !== undefined ? webuiForm.noise_reduction_mode : 0}
                  onChange={(e) => updateWebuiForm({ noise_reduction_mode: parseInt(e.target.value)})}
                  className="settings-select"
                >
                  <option value="0">Off (Fastest)</option>
                  <option value="1">Fast (Balanced)</option>
                  <option value="2">High Quality (Best for night photography)</option>
                </select>
                <p className="settings-help-text">
                  Critical for night insect photography. Higher quality reduces noise but may be slower.
                </p>
              </div>
                </div>
              </CollapsibleCard>
            </div>

            {/* Second row of grid */}
            <div className="settings-grid">
              {/* Focus Settings Card */}
              <CollapsibleCard
                id="streamFocus"
                title="🎯 Focus"
                isCollapsed={collapsedCards.streamFocus}
                onToggle={toggleCard}
                className="settings-card"
              >

              {/* Focus Mode Dropdown */}
              <div className="settings-form-group">
                <label htmlFor="af_mode" className="settings-label">
                  Focus Mode
                </label>
                <select
                  id="af_mode"
                  value={webuiForm.af_mode !== undefined ? webuiForm.af_mode : 2}
                  onChange={(e) => updateWebuiForm({ af_mode: parseInt(e.target.value)})}
                  className="settings-select"
                >
                  <option value="0">Manual Focus</option>
                  <option value="1">Auto Focus (Single)</option>
                  <option value="2">Auto Focus (Continuous) - Recommended</option>
                </select>
                <p className="settings-help-text">
                  Continuous AF keeps subjects in focus automatically
                </p>
              </div>

              {/* Focus Speed Dropdown */}
              <div className="settings-form-group">
                <label htmlFor="af_speed" className="settings-label">
                  Focus Speed
                </label>
                <select
                  id="af_speed"
                  value={webuiForm.af_speed !== undefined ? webuiForm.af_speed : 0}
                  onChange={(e) => updateWebuiForm({ af_speed: parseInt(e.target.value)})}
                  className="settings-select"
                >
                  <option value="0">Normal (Accurate)</option>
                  <option value="1">Fast (May hunt)</option>
                </select>
                <p className="settings-help-text">
                  Normal is more accurate, Fast may cause focus hunting
                </p>
              </div>

              {/* Focus Range Dropdown */}
              <div className="settings-form-group">
                <label htmlFor="af_range" className="settings-label">
                  Focus Range
                </label>
                <select
                  id="af_range"
                  value={webuiForm.af_range !== undefined ? webuiForm.af_range : 0}
                  onChange={(e) => updateWebuiForm({ af_range: parseInt(e.target.value)})}
                  className="settings-select"
                >
                  <option value="0">Normal (0.5m - infinity)</option>
                  <option value="1">Macro (10cm - 50cm)</option>
                  <option value="2">Full (10cm - infinity)</option>
                </select>
                <p className="settings-help-text">
                  Macro mode for close-up insect photography
                </p>
              </div>
              </CollapsibleCard>

              {/* Exposure Card */}
              <CollapsibleCard
                id="streamExposure"
                title="📊 Exposure"
                isCollapsed={collapsedCards.streamExposure}
                onToggle={toggleCard}
                className="settings-card"
              >

              {/* AeEnable Toggle for Stream */}
              <div className="settings-form-group">
                <label className="settings-label">
                  Live View Exposure Mode
                </label>
                <select
                  value={webuiForm.ae_enable !== undefined ? webuiForm.ae_enable : true}
                  onChange={(e) => setWebuiForm({ ...webuiForm, ae_enable: e.target.value === 'true' })}
                  className="settings-select"
                >
                  <option value="true">✨ Auto Exposure</option>
                  <option value="false">🔧 Manual Exposure</option>
                </select>
                <p className="settings-help-text">
                  {!webuiForm.ae_enable || webuiForm.ae_enable === true
                    ? 'Auto mode: Live view stream uses automatic exposure adjustment'
                    : 'Manual mode: Live view uses fixed exposure settings from Camera settings'}
                </p>
              </div>

              {/* AeMeteringMode Dropdown - Show only in Auto mode */}
              {(!webuiForm.ae_enable || webuiForm.ae_enable === true) && (
                <div className="settings-form-group">
                  <label htmlFor="ae_metering_mode" className="settings-label">
                    Metering Mode
                  </label>
                  <select
                    id="ae_metering_mode"
                    value={webuiForm.ae_metering_mode !== undefined ? webuiForm.ae_metering_mode : 0}
                    onChange={(e) => updateWebuiForm({ ae_metering_mode: parseInt(e.target.value)})}
                    className="settings-select"
                  >
                    <option value="0">Centre-Weighted</option>
                    <option value="1">Spot</option>
                    <option value="2">Matrix/Average</option>
                  </select>
                  <p className="settings-help-text">
                    Controls which part of the frame is used for exposure calculation.
                    Centre-Weighted prioritizes the center, Spot uses a small center area only, Matrix evaluates the entire frame.
                  </p>
                </div>
              )}
              </CollapsibleCard>
            </div>

            {/* Third row of grid */}
            <div className="settings-grid">
              {/* White Balance Card */}
              <CollapsibleCard
                id="streamWhiteBalance"
                title="🌡️ White Balance"
                isCollapsed={collapsedCards.streamWhiteBalance}
                onToggle={toggleCard}
                className="settings-card"
              >

              {/* AWB Enable Checkbox */}
              <div className="settings-form-group">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={webuiForm.awb_enable !== undefined ? webuiForm.awb_enable : true}
                    onChange={(e) => updateWebuiForm({ awb_enable: e.target.checked})}
                    className="settings-checkbox"
                  />
                  <span className="ml-2 settings-label mb-0">
                    Auto White Balance
                  </span>
                </label>
                <p className="settings-help-text ml-6">
                  Let camera automatically adjust colour temperature
                </p>
              </div>

              {/* AWB Mode Dropdown (only if AWB disabled) */}
              {webuiForm.awb_enable === false && (
                <div className="settings-form-group">
                  <label htmlFor="awb_mode" className="settings-label">
                    White Balance Preset
                  </label>
                  <select
                    id="awb_mode"
                    value={webuiForm.awb_mode !== undefined ? webuiForm.awb_mode : 0}
                    onChange={(e) => updateWebuiForm({ awb_mode: parseInt(e.target.value)})}
                    className="settings-select"
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
                  <p className="settings-help-text">
                    Manual white balance for specific lighting conditions
                  </p>
                </div>
              )}

              {/* Colour Gains - Manual Colour Balance */}
              <div className="settings-form-group">
                <label className="settings-label">
                  Red Gain: {webuiForm.colour_gains_red !== undefined ? webuiForm.colour_gains_red.toFixed(3) : '2.259'}
                </label>
                <input
                  type="range"
                  min="1.0"
                  max="4.0"
                  step="0.001"
                  value={webuiForm.colour_gains_red !== undefined ? webuiForm.colour_gains_red : 2.259}
                  onChange={(e) => setWebuiForm({ ...webuiForm, colour_gains_red: parseFloat(e.target.value) })}
                  className="w-full cursor-pointer"
                />
                <div className="flex justify-between settings-help-text">
                  <span>1.0</span>
                  <span>2.259 (Default)</span>
                  <span>4.0</span>
                </div>
                <p className="settings-help-text">
                  Manual red channel gain for colour balance adjustment
                </p>
              </div>

              <div className="settings-form-group">
                <label className="settings-label">
                  Blue Gain: {webuiForm.colour_gains_blue !== undefined ? webuiForm.colour_gains_blue.toFixed(3) : '1.500'}
                </label>
                <input
                  type="range"
                  min="1.0"
                  max="4.0"
                  step="0.001"
                  value={webuiForm.colour_gains_blue !== undefined ? webuiForm.colour_gains_blue : 1.500}
                  onChange={(e) => setWebuiForm({ ...webuiForm, colour_gains_blue: parseFloat(e.target.value) })}
                  className="w-full cursor-pointer"
                />
                <div className="flex justify-between settings-help-text">
                  <span>1.0</span>
                  <span>1.500 (Default)</span>
                  <span>4.0</span>
                </div>
                <p className="settings-help-text">
                  Manual blue channel gain for colour balance adjustment
                </p>
              </div>
              </CollapsibleCard>

              {/* ISP Features Card */}
              <CollapsibleCard
                id="streamISP"
                title="🔬 ISP Features"
                isCollapsed={collapsedCards.streamISP}
                onToggle={toggleCard}
                className="settings-card"
              >
              <p className="settings-help-text-xs mb-2">
                Image Signal Processor corrections for improved image quality
              </p>

              {/* Lens Shading Correction (Always enabled via tuning file) */}
              <div className="settings-form-group">
                <label className="flex items-center opacity-75">
                  <input
                    type="checkbox"
                    checked={true}
                    disabled={true}
                    className="settings-checkbox cursor-not-allowed"
                  />
                  <span className="ml-2 settings-label mb-0">
                    Lens Shading Correction
                  </span>
                  <span className="ml-2 px-2 py-0.5 text-xs font-medium text-green-600 bg-green-100 rounded">
                    Always On
                  </span>
                </label>
                <p className="settings-help-text ml-6">
                  Corrects vignetting (darker corners). Enabled automatically via camera tuning file - runtime control not available on this camera model.
                </p>
              </div>

              {/* Defect Pixel Correction (Always enabled via tuning file) */}
              <div className="settings-form-group">
                <label className="flex items-center opacity-75">
                  <input
                    type="checkbox"
                    checked={true}
                    disabled={true}
                    className="settings-checkbox cursor-not-allowed"
                  />
                  <span className="ml-2 settings-label mb-0">
                    Defect Pixel Correction
                  </span>
                  <span className="ml-2 px-2 py-0.5 text-xs font-medium text-green-600 bg-green-100 rounded">
                    Always On
                  </span>
                </label>
                <p className="settings-help-text ml-6">
                  Fixes stuck or dead pixels. Enabled automatically via camera tuning file - runtime control not available on this camera model.
                </p>
              </div>

              {/* Custom Tuning File (Disabled by default) */}
              <div className="settings-form-group">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={webuiForm.use_custom_tuning || false}
                    onChange={(e) => updateWebuiForm({ use_custom_tuning: e.target.checked})}
                    className="settings-checkbox"
                  />
                  <span className="ml-2 settings-label mb-0">
                    Use Custom Tuning File
                  </span>
                  <span className="ml-2 px-2 py-0.5 text-xs font-medium text-orange-600 bg-orange-100 rounded">
                    Advanced
                  </span>
                </label>
                <p className="settings-help-text ml-6">
                  Load custom ISP tuning from /etc/mothbox/isp_tuning/camera_isp_tuning.json.
                  Only enable if you have a camera-specific tuning file.
                  Disabled by default - libcamera's built-in tuning works well for most cameras.
                </p>
                {webuiForm.use_custom_tuning && (
                  <div className="settings-info-box bg-yellow-50 border-yellow-200 ml-6 mt-1">
                    <p className="settings-help-text text-yellow-800">
                      ⚠️ Warning: Custom tuning files must match your camera model.
                      Incompatible tuning files may cause camera initialization to fail.
                    </p>
                  </div>
                )}
              </div>

              {/* Chromatic Aberration Correction (Disabled - requires Pi 5 and calibration) */}
              <div className="settings-form-group">
                <label className="flex items-center opacity-50 cursor-not-allowed">
                  <input
                    type="checkbox"
                    checked={false}
                    disabled={true}
                    className="settings-checkbox cursor-not-allowed"
                  />
                  <span className="ml-2 settings-label mb-0 text-gray-500">
                    Chromatic Aberration Correction
                  </span>
                  <span className="ml-2 px-2 py-0.5 text-xs font-medium text-gray-600 bg-gray-200 rounded">
                    Pi 5 Only
                  </span>
                </label>
                <p className="settings-help-text ml-6">
                  Fixes colour fringing at edges. Requires Raspberry Pi 5 hardware and camera calibration with tuning file configuration.
                  Not available for runtime toggling - must be configured in tuning file before camera initialization.
                </p>
              </div>
              </CollapsibleCard>
            </div>

            {/* Focus Peaking Card */}
            <CollapsibleCard
              id="streamFocusPeaking"
              title="🔍 Focus Peaking"
              isCollapsed={collapsedCards.streamFocusPeaking}
              onToggle={toggleCard}
              className="settings-card"
            >
              <p className="settings-help-text-xs mb-2">
                Live view-only overlay to highlight in-focus areas. Helps with manual focus adjustment for macro photography.
              </p>

              <div className="space-y-2">
                {/* Enable Toggle */}
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="focus_peaking_enabled"
                    checked={webuiForm.focus_peaking_enabled || false}
                    onChange={(e) => updateWebuiForm({ focus_peaking_enabled: e.target.checked})}
                    className="settings-checkbox"
                  />
                  <label htmlFor="focus_peaking_enabled" className="ml-2 settings-label mb-0">
                    Enable Focus Peaking Overlay
                  </label>
                </div>

                <div className="ml-6 space-y-2">
                  {/* Intensity */}
                  <div className="settings-form-group">
                    <label htmlFor="focus_peaking_intensity" className="settings-label">
                      Intensity: {webuiForm.focus_peaking_intensity || 100}
                    </label>
                    <input
                      type="range"
                      id="focus_peaking_intensity"
                      min="50"
                      max="200"
                      step="10"
                      value={webuiForm.focus_peaking_intensity || 100}
                      onChange={(e) => updateWebuiForm({ focus_peaking_intensity: parseInt(e.target.value)})}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-500"
                    />
                    <div className="flex justify-between settings-help-text">
                      <span>50 (Low)</span>
                      <span>125</span>
                      <span>200 (High)</span>
                    </div>
                  </div>

                  {/* Colour */}
                  <div className="settings-form-group">
                    <label htmlFor="focus_peaking_color" className="settings-label">
                      Overlay Colour
                    </label>
                    <select
                      id="focus_peaking_color"
                      value={webuiForm.focus_peaking_color || 'green'}
                      onChange={(e) => updateWebuiForm({ focus_peaking_color: e.target.value})}
                      className="settings-select"
                    >
                      <option value="green">🟢 Green</option>
                      <option value="red">🔴 Red</option>
                      <option value="yellow">🟡 Yellow</option>
                      <option value="cyan">🔵 Cyan</option>
                      <option value="magenta">🟣 Magenta</option>
                    </select>
                  </div>

                  {/* Algorithm */}
                  <div className="settings-form-group">
                    <label htmlFor="focus_peaking_algorithm" className="settings-label">
                      Edge Detection Algorithm
                    </label>
                    <select
                      id="focus_peaking_algorithm"
                      value={webuiForm.focus_peaking_algorithm || 'laplacian'}
                      onChange={(e) => updateWebuiForm({ focus_peaking_algorithm: e.target.value})}
                      className="settings-select"
                    >
                      <option value="laplacian">⚡ Laplacian (Fast)</option>
                      <option value="sobel">⚙️ Sobel (Balanced)</option>
                      <option value="canny">🎯 Canny (Accurate)</option>
                    </select>
                    <p className="settings-help-text">
                      Laplacian is fastest for general use. Sobel offers better directional accuracy. Canny is most accurate but slower.
                    </p>
                  </div>
                </div>
              </div>
            </CollapsibleCard>
          </div>
        </div>
      )}

      {/* Save Preset Modal */}
      <SavePresetModal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        onSave={handleSavePreset}
        isSaving={createPresetMutation.isPending}
        defaultWorkflow={saveModalWorkflow}
        currentSettings={webuiForm}
      />
    </div>
  )
}
