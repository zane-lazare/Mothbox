import type { WebuiSettings, CollapsedCardsState, PresetsData, ResolutionPreset } from '../../types/settings'
import SettingCard from './SettingCard'
import { UseMutationResult } from '@tanstack/react-query'

interface LiveViewSettingsTabProps {
  webuiForm: WebuiSettings
  updateWebuiForm: (updates: Partial<WebuiSettings>) => void
  setWebuiForm: (form: WebuiSettings) => void
  collapsedCards: CollapsedCardsState
  toggleCard: (id: string) => void

  // Preset management
  presetsData: PresetsData | undefined
  presetsLoading: boolean
  selectedLiveViewPreset: string
  setSelectedLiveViewPreset: (preset: string) => void
  handleVideoPresetChange: (e: React.ChangeEvent<HTMLSelectElement>) => void
  handleUpdateVideoPreset: () => void
  handleSetDefaultVideoPreset: () => void
  handleSaveVideoPreset: () => void
  handleDeleteVideoPreset: () => void

  // Mutations
  updateWebuiMutation: UseMutationResult<unknown, Error, WebuiSettings>
  createPresetMutation: UseMutationResult<unknown, Error, unknown>
  deletePresetMutation: UseMutationResult<unknown, Error, string>
  applyPresetMutation: UseMutationResult<unknown, Error, { name: string; applyTo: string }>
  setPreferenceMutation: UseMutationResult<unknown, Error, { key: string; value: string }>

  // Resolution presets
  resolutionPresets: ResolutionPreset[]
}

export default function LiveViewSettingsTab({
  webuiForm,
  updateWebuiForm,
  setWebuiForm,
  collapsedCards,
  toggleCard,
  presetsData,
  presetsLoading,
  selectedLiveViewPreset,
  handleVideoPresetChange,
  handleUpdateVideoPreset,
  handleSetDefaultVideoPreset,
  handleSaveVideoPreset,
  handleDeleteVideoPreset,
  updateWebuiMutation,
  createPresetMutation,
  deletePresetMutation,
  applyPresetMutation,
  setPreferenceMutation,
  resolutionPresets,
}: LiveViewSettingsTabProps) {
  // Filter presets by workflow
  const liveViewPresets = presetsData?.presets?.filter(p => p.workflow === 'liveview' || p.workflow === 'video' || p.workflow === 'both') || []
  const selectedLiveViewPresetData = presetsData?.presets?.find(p => p.name === selectedLiveViewPreset)

  return (
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
          <SettingCard
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
          </SettingCard>

          {/* Image Quality Card */}
          <SettingCard
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
          </SettingCard>
        </div>

        {/* Second row of grid */}
        <div className="settings-grid">
          {/* Focus Settings Card */}
          <SettingCard
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
          </SettingCard>

          {/* Exposure Card */}
          <SettingCard
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
                value={webuiForm.ae_enable !== undefined ? String(webuiForm.ae_enable) : 'true'}
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
          </SettingCard>
        </div>

        {/* Third row of grid */}
        <div className="settings-grid">
          {/* White Balance Card */}
          <SettingCard
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
          </SettingCard>

          {/* ISP Features Card */}
          <SettingCard
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
          </SettingCard>
        </div>

        {/* Focus Peaking Card */}
        <SettingCard
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
        </SettingCard>
      </div>
    </div>
  )
}
