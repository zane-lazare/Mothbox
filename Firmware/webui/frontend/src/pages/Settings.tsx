import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getControls, updateControls, getCameraSettings, updateCameraSettings, getSystemInfo, getDiagnosticInfo, getWebuiSettings, updateWebuiSettings, getPresets, applyPreset, deletePreset, createPreset, getPreferences, setPreference } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { useState, useEffect, useRef } from 'react'
import useSocket from '../hooks/useSocket'
import toast from 'react-hot-toast'
import SavePresetModal from '../components/SavePresetModal'
import SystemInfoTab from '../components/settings/SystemInfoTab'
import DiagnosticTab from '../components/settings/DiagnosticTab'
import CameraSettingsTab from '../components/settings/CameraSettingsTab'
import LiveViewSettingsTab from '../components/settings/LiveViewSettingsTab'
import { validateLiveviewSettings, formatLiveviewValidationErrors } from '../schemas/liveview-settings'
import type {
  ControlSettings,
  CameraSettings,
  WebuiSettings,
  TabId,
  CollapsedCardsState,
  ResolutionPreset
} from '../types/settings'

export default function Settings() {
  const queryClient = useQueryClient()
  const { socket } = useSocket()
  const [activeTab, setActiveTab] = useState<TabId>('system')

  // Collapsed cards state - smart defaults (common expanded, advanced collapsed)
  const [collapsedCards, setCollapsedCards] = useState<CollapsedCardsState>({
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

  const toggleCard = (id: string) => {
    setCollapsedCards(prev => ({ ...prev, [id]: !prev[id] }))
  }

  // Queries
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

  const { data: presetsData, isLoading: presetsLoading } = useQuery({
    queryKey: QUERY_KEYS.PRESETS,
    queryFn: () => getPresets().then(res => res.data),
  })

  const { data: preferences } = useQuery({
    queryKey: QUERY_KEYS.PREFERENCES,
    queryFn: () => getPreferences().then(res => res.data),
  })

  // Mutations
  const updateControlsMutation = useMutation({
    mutationFn: updateControls,
    onSuccess: () => {
      isDirtyRef.current.controls = false
      queryClient.invalidateQueries(QUERY_KEYS.CONTROLS)
      toast.success('Hardware controls updated successfully!')
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || 'Failed to update controls'
      toast.error(`Error: ${message}`)
    },
  })

  const updateCameraMutation = useMutation({
    mutationFn: updateCameraSettings,
    onSuccess: () => {
      isDirtyRef.current.camera = false
      queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || 'Failed to update camera settings'
      toast.error(`Error: ${message}`)
    },
  })

  const updateWebuiMutation = useMutation({
    mutationFn: updateWebuiSettings,
    onSuccess: () => {
      isDirtyRef.current.webui = false
      queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
      if (socket) {
        socket.emit('reload_stream_settings')
      }
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || 'Failed to update stream settings'
      toast.error(`Error: ${message}`)
    },
  })

  const applyPresetMutation = useMutation({
    mutationFn: ({ name, applyTo }: { name: string; applyTo: string }) => applyPreset(name, applyTo),
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)
      queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
    },
    onError: () => {
      // Error toasts handled by individual callers
    },
  })

  const deletePresetMutation = useMutation({
    mutationFn: (name: string) => deletePreset(name),
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.PRESETS)
      setSelectedPhotoPreset('')
      setSelectedLiveViewPreset('')
      toast.success('Preset deleted successfully!')
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || 'Failed to delete preset'
      toast.error(`Error: ${message}`)
    },
  })

  const createPresetMutation = useMutation({
    mutationFn: (data: any) => createPreset(data),
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.PRESETS)
      setShowSaveModal(false)
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || 'Failed to save preset'
      toast.error(`Error: ${message}`)
    },
  })

  const setPreferenceMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => setPreference(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries(QUERY_KEYS.PREFERENCES)
      toast.success('Default preset updated!')
    },
    onError: (error: any) => {
      const message = error.response?.data?.error || 'Failed to update preference'
      toast.error(`Error: ${message}`)
    },
  })

  // Form state
  const [controlsForm, setControlsForm] = useState<ControlSettings>({})
  const [cameraForm, setCameraForm] = useState<CameraSettings>({})
  const [webuiForm, setWebuiForm] = useState<WebuiSettings>({})
  const [selectedPhotoPreset, setSelectedPhotoPreset] = useState('')
  const [selectedLiveViewPreset, setSelectedLiveViewPreset] = useState('')
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveModalWorkflow, setSaveModalWorkflow] = useState<'photo' | 'liveview' | 'both'>('both')

  // Track dirty state for each form to prevent overwriting user edits
  const isDirtyRef = useRef({
    controls: false,
    camera: false,
    webui: false
  })

  // Initialize forms when data loads
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

  // Listen for stream settings reload via shared socket
  useEffect(() => {
    if (!socket) return

    const handleSettingsReloaded = () => {
      queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
    }

    socket.on('settings_reloaded', handleSettingsReloaded)

    return () => {
      socket.off('settings_reloaded', handleSettingsReloaded)
    }
  }, [socket, queryClient])

  // Wrapper functions to mark forms as dirty when updated
  const updateControlsForm = (updates: Partial<ControlSettings>) => {
    isDirtyRef.current.controls = true
    setControlsForm(prev => ({ ...prev, ...updates }))
  }

  const updateCameraForm = (updates: Partial<CameraSettings>) => {
    isDirtyRef.current.camera = true
    setCameraForm(prev => ({ ...prev, ...updates }))
  }

  const updateWebuiForm = (updates: Partial<WebuiSettings>) => {
    isDirtyRef.current.webui = true
    setWebuiForm(prev => ({ ...prev, ...updates }))
  }

  const handleControlsSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateControlsMutation.mutate(controlsForm)
  }

  // Preset management handlers
  const photoPresetInitialized = useRef(false)
  const liveViewPresetInitialized = useRef(false)

  const initializePhotoPreset = async (presetName: string) => {
    try {
      await applyPresetMutation.mutateAsync({ name: presetName, applyTo: 'capture' })
      await queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)
    } catch (error: any) {
      console.error('Failed to initialize photo preset:', error)
      const errorMsg = error.response?.data?.error || error.message

      if (errorMsg.includes('not found') || errorMsg.includes('workflow')) {
        const fallbackPreset = presetsData?.presets?.find(p =>
          (p.workflow === 'photo' || p.workflow === 'both') && p.name === 'balanced'
        )
        if (fallbackPreset) {
          try {
            await applyPresetMutation.mutateAsync({ name: fallbackPreset.name, applyTo: 'capture' })
            setSelectedPhotoPreset(fallbackPreset.name)
          } catch (fallbackError: any) {
            const fallbackMsg = fallbackError.response?.data?.error || 'Failed to load preset'
            toast.error(`Failed to load fallback preset: ${fallbackMsg}`)
          }
        } else {
          toast.error(`Photo preset not found and no fallback available`)
        }
      }
    }
  }

  const initializeVideoPreset = async (presetName: string) => {
    try {
      await applyPresetMutation.mutateAsync({ name: presetName, applyTo: 'liveview' })
      await queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)
    } catch (error: any) {
      console.error('Failed to initialize live view preset:', error)
      const errorMsg = error.response?.data?.error || error.message

      if (errorMsg.includes('not found') || errorMsg.includes('workflow')) {
        const fallbackPreset = presetsData?.presets?.find(p =>
          (p.workflow === 'liveview' || p.workflow === 'both') && p.name === 'balanced'
        )
        if (fallbackPreset) {
          try {
            await applyPresetMutation.mutateAsync({ name: fallbackPreset.name, applyTo: 'liveview' })
            setSelectedLiveViewPreset(fallbackPreset.name)
          } catch (fallbackError: any) {
            const fallbackMsg = fallbackError.response?.data?.error || 'Failed to load preset'
            toast.error(`Failed to load fallback preset: ${fallbackMsg}`)
          }
        } else {
          toast.error(`Liveview preset not found and no fallback available`)
        }
      }
    }
  }

  // Initialize with default presets on mount
  useEffect(() => {
    if (presetsData?.presets && preferences && !selectedPhotoPreset && !photoPresetInitialized.current) {
      const savedDefault = preferences?.default_capture_preset
      const defaultExists = savedDefault && presetsData.presets.some(p => p.name === savedDefault)

      const defaultPreset = (defaultExists ? savedDefault : null) ||
                           presetsData.presets.find(p => (p.workflow === 'photo' || p.workflow === 'both') && p.name === 'balanced')?.name ||
                           presetsData.presets.find(p => p.workflow === 'photo' || p.workflow === 'both')?.name
      if (defaultPreset) {
        setSelectedPhotoPreset(defaultPreset)
        initializePhotoPreset(defaultPreset)
        photoPresetInitialized.current = true
      }
    }
  }, [presetsData, preferences])

  useEffect(() => {
    if (presetsData?.presets && preferences && !selectedLiveViewPreset && !liveViewPresetInitialized.current) {
      const savedDefault = preferences?.default_liveview_preset || preferences?.default_preview_preset
      const defaultExists = savedDefault && presetsData.presets.some(p => p.name === savedDefault)

      const defaultPreset = (defaultExists ? savedDefault : null) ||
                           presetsData.presets.find(p => (p.workflow === 'liveview' || p.workflow === 'both') && p.name === 'balanced')?.name ||
                           presetsData.presets.find(p => p.workflow === 'liveview' || p.workflow === 'both')?.name
      if (defaultPreset) {
        setSelectedLiveViewPreset(defaultPreset)
        initializeVideoPreset(defaultPreset)
        liveViewPresetInitialized.current = true
      }
    }
  }, [presetsData, preferences])

  // Auto-apply preset handlers
  const handlePhotoPresetChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const presetName = e.target.value
    setSelectedPhotoPreset(presetName)

    try {
      await applyPresetMutation.mutateAsync({ name: presetName, applyTo: 'capture' })
      await queryClient.invalidateQueries(QUERY_KEYS.CAMERA_SETTINGS)

      const preset = presetsData?.presets?.find(p => p.name === presetName)
      const displayName = preset?.display_name || presetName

      if (photoPresetInitialized.current) {
        toast.success(`Applied "${displayName}" preset`)
      }
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to apply preset'
      toast.error(`Apply failed: ${message}`)
    }
  }

  const handleVideoPresetChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const presetName = e.target.value
    setSelectedLiveViewPreset(presetName)

    try {
      await applyPresetMutation.mutateAsync({ name: presetName, applyTo: 'liveview' })
      await queryClient.invalidateQueries(QUERY_KEYS.WEBUI_SETTINGS)

      const preset = presetsData?.presets?.find(p => p.name === presetName)
      const displayName = preset?.display_name || presetName

      if (liveViewPresetInitialized.current) {
        toast.success(`Applied "${displayName}" preset`)
      }
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to apply preset'
      toast.error(`Apply failed: ${message}`)
    }
  }

  const handleUpdatePhotoPreset = async () => {
    if (!selectedPhotoPreset) return
    const selectedPhotoPresetData = presetsData?.presets?.find(p => p.name === selectedPhotoPreset)

    if (selectedPhotoPresetData?.category === 'built-in') {
      toast.error('Cannot modify built-in presets. Use "Save As" to create a copy.')
      return
    }

    try {
      const presetData = {
        name: selectedPhotoPreset,
        description: selectedPhotoPresetData?.description || '',
        workflow: 'photo',
        settings: {
          camera: cameraForm
        }
      }

      await createPresetMutation.mutateAsync(presetData)
      await updateCameraMutation.mutateAsync(cameraForm)

      const displayName = selectedPhotoPresetData?.display_name || selectedPhotoPreset
      toast.success(`Updated "${displayName}" preset`)
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to update preset'
      toast.error(`Update failed: ${message}`)
    }
  }

  const handleUpdateVideoPreset = async () => {
    if (!selectedLiveViewPreset) return
    const selectedLiveViewPresetData = presetsData?.presets?.find(p => p.name === selectedLiveViewPreset)

    if (selectedLiveViewPresetData?.category === 'built-in') {
      toast.error('Cannot modify built-in presets. Use "Save As" to create a copy.')
      return
    }

    try {
      const validationErrors = validateLiveviewSettings(webuiForm)
      if (validationErrors.length > 0) {
        const errorMessage = formatLiveviewValidationErrors(validationErrors, 3)
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
    } catch (error: any) {
      const message = error.response?.data?.error || 'Failed to update preset'
      toast.error(`Update failed: ${message}`)
    }
  }

  const handleSavePreset = async (presetData: any) => {
    const validationErrors = validateLiveviewSettings(webuiForm)
    if (validationErrors.length > 0) {
      const errorMessage = formatLiveviewValidationErrors(validationErrors, 3)
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
    setPreferenceMutation.mutate({ key: 'default_capture_preset', value: selectedPhotoPreset })
  }

  const handleSetDefaultVideoPreset = () => {
    if (!selectedLiveViewPreset) {
      toast.error('Please select a live view preset first')
      return
    }
    setPreferenceMutation.mutate({ key: 'default_liveview_preset', value: selectedLiveViewPreset })
  }

  const handleDeletePhotoPreset = () => {
    if (!selectedPhotoPreset) return
    const selectedPhotoPresetData = presetsData?.presets?.find(p => p.name === selectedPhotoPreset)

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
    const selectedLiveViewPresetData = presetsData?.presets?.find(p => p.name === selectedLiveViewPreset)

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
  const resolutionPresets: ResolutionPreset[] = [
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
        <SystemInfoTab
          systemInfo={systemInfo}
          collapsedCards={collapsedCards}
          toggleCard={toggleCard}
        />
      )}

      {/* Diagnostic Tab */}
      {activeTab === 'diagnostic' && (
        <DiagnosticTab
          diagnosticInfo={diagnosticInfo}
          collapsedCards={collapsedCards}
          toggleCard={toggleCard}
        />
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
        <CameraSettingsTab
          cameraForm={cameraForm}
          updateCameraForm={updateCameraForm}
          setCameraForm={setCameraForm}
          collapsedCards={collapsedCards}
          toggleCard={toggleCard}
          presetsData={presetsData}
          presetsLoading={presetsLoading}
          selectedPhotoPreset={selectedPhotoPreset}
          setSelectedPhotoPreset={setSelectedPhotoPreset}
          handlePhotoPresetChange={handlePhotoPresetChange}
          handleUpdatePhotoPreset={handleUpdatePhotoPreset}
          handleSetDefaultPhotoPreset={handleSetDefaultPhotoPreset}
          handleSavePhotoPreset={handleSavePhotoPreset}
          handleDeletePhotoPreset={handleDeletePhotoPreset}
          updateCameraMutation={updateCameraMutation}
          createPresetMutation={createPresetMutation}
          deletePresetMutation={deletePresetMutation}
          applyPresetMutation={applyPresetMutation}
          setPreferenceMutation={setPreferenceMutation}
        />
      )}

      {/* Live View Settings Tab */}
      {activeTab === 'stream' && (
        <LiveViewSettingsTab
          webuiForm={webuiForm}
          updateWebuiForm={updateWebuiForm}
          setWebuiForm={setWebuiForm}
          collapsedCards={collapsedCards}
          toggleCard={toggleCard}
          presetsData={presetsData}
          presetsLoading={presetsLoading}
          selectedLiveViewPreset={selectedLiveViewPreset}
          setSelectedLiveViewPreset={setSelectedLiveViewPreset}
          handleVideoPresetChange={handleVideoPresetChange}
          handleUpdateVideoPreset={handleUpdateVideoPreset}
          handleSetDefaultVideoPreset={handleSetDefaultVideoPreset}
          handleSaveVideoPreset={handleSaveVideoPreset}
          handleDeleteVideoPreset={handleDeleteVideoPreset}
          updateWebuiMutation={updateWebuiMutation}
          createPresetMutation={createPresetMutation}
          deletePresetMutation={deletePresetMutation}
          applyPresetMutation={applyPresetMutation}
          setPreferenceMutation={setPreferenceMutation}
          resolutionPresets={resolutionPresets}
        />
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
