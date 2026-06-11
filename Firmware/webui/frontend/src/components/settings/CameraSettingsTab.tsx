import type { CameraSettings, CollapsedCardsState, PresetsData } from '../../types/settings'
import { CAMERA_SETTINGS } from '../../constants/config'
import SettingCard from './SettingCard'
import { UseMutationResult } from '@tanstack/react-query'

interface CameraSettingsTabProps {
  cameraForm: CameraSettings
  updateCameraForm: (updates: Partial<CameraSettings>) => void
  setCameraForm: (form: CameraSettings) => void
  collapsedCards: CollapsedCardsState
  toggleCard: (id: string) => void

  // Preset management
  presetsData: PresetsData | undefined
  presetsLoading: boolean
  selectedPhotoPreset: string
  setSelectedPhotoPreset: (preset: string) => void
  handlePhotoPresetChange: (e: React.ChangeEvent<HTMLSelectElement>) => void
  handleUpdatePhotoPreset: () => void
  handleSetDefaultPhotoPreset: () => void
  handleSavePhotoPreset: () => void
  handleDeletePhotoPreset: () => void

  // Mutations
  updateCameraMutation: UseMutationResult<unknown, Error, CameraSettings>
  createPresetMutation: UseMutationResult<unknown, Error, unknown>
  deletePresetMutation: UseMutationResult<unknown, Error, string>
  applyPresetMutation: UseMutationResult<unknown, Error, { name: string; applyTo: string }>
  setPreferenceMutation: UseMutationResult<unknown, Error, { key: string; value: string }>
}

export default function CameraSettingsTab({
  cameraForm,
  updateCameraForm,
  setCameraForm,
  collapsedCards,
  toggleCard,
  presetsData,
  presetsLoading,
  selectedPhotoPreset,
  handlePhotoPresetChange,
  handleUpdatePhotoPreset,
  handleSetDefaultPhotoPreset,
  handleSavePhotoPreset,
  handleDeletePhotoPreset,
  updateCameraMutation,
  createPresetMutation,
  deletePresetMutation,
  applyPresetMutation,
  setPreferenceMutation,
}: CameraSettingsTabProps) {
  // Filter presets by workflow
  const photoPresets = presetsData?.presets?.filter(p => p.workflow === 'photo' || p.workflow === 'both') || []
  const selectedPhotoPresetData = presetsData?.presets?.find(p => p.name === selectedPhotoPreset)

  // Focus mode helper functions
  const lensPositionPercent = (raw: string | number | undefined): number => {
    const { MIN, MAX, DEFAULT } = CAMERA_SETTINGS.LENS_POSITION
    const value = Math.min(Math.max(parseFloat(String(raw || DEFAULT)), MIN), MAX)
    return ((value - MIN) / (MAX - MIN)) * 100
  }

  const focusMode = (() => {
    const autoCal = String(cameraForm.AutoCalibration ?? '0') === '1'
    if (autoCal) return CAMERA_SETTINGS.FOCUS_MODES.AUTO_CALIBRATE
    const afMode = String(cameraForm.AfMode ?? CAMERA_SETTINGS.AF_MODE_VALUES.MANUAL)
    if (afMode === CAMERA_SETTINGS.AF_MODE_VALUES.SINGLE) return CAMERA_SETTINGS.FOCUS_MODES.AF_SINGLE
    if (afMode === CAMERA_SETTINGS.AF_MODE_VALUES.CONTINUOUS) return CAMERA_SETTINGS.FOCUS_MODES.AF_CONTINUOUS
    return CAMERA_SETTINGS.FOCUS_MODES.MANUAL
  })()

  const handleFocusModeChange = (mode: string) => {
    const updates = {
      [CAMERA_SETTINGS.FOCUS_MODES.AUTO_CALIBRATE]:  { AutoCalibration: '1', AfMode: CAMERA_SETTINGS.AF_MODE_VALUES.MANUAL },
      [CAMERA_SETTINGS.FOCUS_MODES.MANUAL]:          { AutoCalibration: '0', AfMode: CAMERA_SETTINGS.AF_MODE_VALUES.MANUAL },
      [CAMERA_SETTINGS.FOCUS_MODES.AF_SINGLE]:       { AutoCalibration: '0', AfMode: CAMERA_SETTINGS.AF_MODE_VALUES.SINGLE },
      [CAMERA_SETTINGS.FOCUS_MODES.AF_CONTINUOUS]:    { AutoCalibration: '0', AfMode: CAMERA_SETTINGS.AF_MODE_VALUES.CONTINUOUS },
    }
    const update = updates[mode]
    if (!update) return
    updateCameraForm(update)
  }

  return (
    <div className="space-y-2">
      <div className="bg-gradient-to-r from-blue-100 to-indigo-100 rounded-lg shadow-sm p-2 border border-blue-200">
        <h3 className="text-base font-semibold text-gray-900">Full-Resolution Capture Configuration</h3>
        <p className="text-xs text-gray-700">
          These settings control full-resolution photo captures (not live view). Changes take effect on next photo.
        </p>
      </div>

      {/* Photo Preset Management Section */}
      <SettingCard
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
      </SettingCard>

      <div className="space-y-2">
        {/* Grid container for settings cards */}
        <div className="settings-grid">
          {/* Exposure Card */}
          <SettingCard
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
                value={cameraForm.AeEnable !== undefined ? String(cameraForm.AeEnable) : 'True'}
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
                      const exposure = parseInt(String(cameraForm.ExposureTime)) || 500
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
                    ISO (Analogue Gain): {parseFloat(String(cameraForm.AnalogueGain || 1)).toFixed(1)}x
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="16"
                    step="0.5"
                    value={Number(cameraForm.AnalogueGain || 8.0)}
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
                  Exposure Compensation: {parseFloat(String(cameraForm.ExposureValue || 0)).toFixed(1)} EV
                </label>
                <input
                  type="range"
                  min="-8"
                  max="8"
                  step="0.1"
                  value={Number(cameraForm.ExposureValue || 0.6)}
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
          </SettingCard>
        </div>

        {/* HDR/Bracketing and Focus Bracketing - full width row */}
        <div className="settings-grid-2col">
          {/* HDR/Bracketing Card */}
          <SettingCard
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
            {(parseInt(String(cameraForm.HDR)) > 1) && (
              <div className="settings-form-group">
                <label className="settings-label">
                  Bracket Step: {cameraForm.HDR_width || 7000} µs
                </label>
                <input
                  type="range"
                  min="1000"
                  max="50000"
                  step="1000"
                  value={Number(cameraForm.HDR_width || 7000)}
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
          </SettingCard>

          {/* Focus Bracketing Card */}
          <SettingCard
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
            {(parseInt(String(cameraForm.FocusBracket)) > 1) && (
              <>
                <div className="settings-form-group">
                  <label className="settings-label">
                    Focus Start Position: {parseFloat(String(cameraForm.FocusBracket_Start || 2.0)).toFixed(1)} diopters
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.5"
                    value={Number(cameraForm.FocusBracket_Start || 2.0)}
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
                    Focus End Position: {parseFloat(String(cameraForm.FocusBracket_End || 8.0)).toFixed(1)} diopters
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.5"
                    value={Number(cameraForm.FocusBracket_End || 8.0)}
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
                          Flash Delay (Before Capture): {parseInt(String(cameraForm.FlashDelay_BeforeCapture || 50))} ms
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="500"
                          step="10"
                          value={Number(cameraForm.FlashDelay_BeforeCapture || 50)}
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
                          Flash Delay (After Capture): {parseInt(String(cameraForm.FlashDelay_AfterCapture || 0))} ms
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="500"
                          step="10"
                          value={Number(cameraForm.FlashDelay_AfterCapture || 0)}
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
                          Lens Settle Delay: {parseInt(String(cameraForm.FocusBracket_SettleDelay || 500))} ms
                        </label>
                        <input
                          type="range"
                          min="100"
                          max="2000"
                          step="50"
                          value={Number(cameraForm.FocusBracket_SettleDelay || 500)}
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
                            checked={parseInt(String(cameraForm.FocusBracket_LockColorGains || 1)) === 1}
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
                      {parseInt(String(cameraForm.FocusBracket_LockColorGains || 1)) === 1 && (
                        <>
                          <div className="settings-form-group pl-8">
                            <label className="settings-label">
                              Red Gain: {parseFloat(String(cameraForm.FocusBracket_ColorGainRed || 2.259)).toFixed(3)}
                            </label>
                            <input
                              type="range"
                              min="1.0"
                              max="4.0"
                              step="0.01"
                              value={Number(cameraForm.FocusBracket_ColorGainRed || 2.259)}
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
                              Blue Gain: {parseFloat(String(cameraForm.FocusBracket_ColorGainBlue || 1.500)).toFixed(3)}
                            </label>
                            <input
                              type="range"
                              min="1.0"
                              max="4.0"
                              step="0.01"
                              value={Number(cameraForm.FocusBracket_ColorGainBlue || 1.500)}
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
                      {parseInt(String(cameraForm.FocusBracket_LockColorGains || 1)) === 0 && (
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
          </SettingCard>
        </div>

        {/* Third row of grid */}
        <div className="settings-grid">
          {/* Focus Strategy Card */}
          <SettingCard
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
                      value={Number(cameraForm.AutoCalibrationPeriod || CAMERA_SETTINGS.CALIBRATION_INTERVAL.DEFAULT)}
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
                      Current Calibrated Position: {parseFloat(String(cameraForm.LensPosition || CAMERA_SETTINGS.LENS_POSITION.DEFAULT)).toFixed(2)} diopters
                    </label>
                    <div className="w-full bg-gray-200 rounded h-2">
                      <div
                        className="bg-green-500 rounded h-2"
                        style={{ width: `${lensPositionPercent(cameraForm.LensPosition)}%` }}
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
                    Focus Position: {parseFloat(String(cameraForm.LensPosition || CAMERA_SETTINGS.LENS_POSITION.DEFAULT)).toFixed(2)} diopters
                  </label>
                  <input
                    type="range"
                    data-testid="lens-position-slider"
                    aria-label="Focus position in diopters"
                    aria-describedby="lens-position-help"
                    min={CAMERA_SETTINGS.LENS_POSITION.MIN}
                    max={CAMERA_SETTINGS.LENS_POSITION.MAX}
                    step={CAMERA_SETTINGS.LENS_POSITION.STEP}
                    value={Number(cameraForm.LensPosition || CAMERA_SETTINGS.LENS_POSITION.DEFAULT)}
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
                      value={cameraForm.AfRange || CAMERA_SETTINGS.AF_RANGE_DEFAULT}
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
                      value={cameraForm.AfSpeed || CAMERA_SETTINGS.AF_SPEED_DEFAULT}
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
          </SettingCard>

          {/* Image Format Card */}
          <SettingCard
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
          </SettingCard>
        </div>

        {/* Advanced/Other Settings - full width */}
        <SettingCard
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
                    value={String(value)}
                    onChange={(e) => setCameraForm({ ...cameraForm, [key]: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
          </div>
        </SettingCard>

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
  )
}
