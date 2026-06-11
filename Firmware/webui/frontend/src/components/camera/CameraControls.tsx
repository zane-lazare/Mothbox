/**
 * CameraControls Component
 *
 * Real-time camera controls overlay during live preview.
 * Handles: image quality, exposure, focus, zoom, color balance, focus peaking.
 */

import { LiveControls, AfWindow, PresetData } from '../../types/camera'
import { toPicameraControl } from '../../utils/cameraControlMapping'
import { Socket } from 'socket.io-client'
import toast from 'react-hot-toast'

interface CameraControlsProps {
  liveControls: LiveControls
  zoomLevel: number
  afWindow: AfWindow | null
  selectedPhotoPreset: string
  selectedLiveViewPreset: string
  photoPresets: PresetData[]
  liveViewPresets: PresetData[]
  applyPresetMutationPending: boolean
  createPresetMutationPending: boolean
  socket: Socket | null
  presetsData?: { presets: PresetData[] }
  onControlChange: (controlName: string, value: number | boolean | string) => void
  onZoomChange: (value: number) => void
  onResetControls: () => void
  onApplyPhotoPreset: (presetName: string) => void
  onApplyLiveViewPreset: (presetName: string) => void
  onUpdateLiveViewPreset: () => void
  onShowSaveModal: (workflow: 'photo' | 'liveview' | 'both') => void
  setLiveControls: React.Dispatch<React.SetStateAction<LiveControls>>
  setAfWindow: (window: AfWindow | null) => void
  setSelectedPhotoPreset: (preset: string) => void
  setSelectedLiveViewPreset: (preset: string) => void
  debouncedEmitControl: (controlName: string, value: number | boolean | string) => void
}

export default function CameraControls({
  liveControls,
  zoomLevel,
  afWindow,
  selectedPhotoPreset,
  selectedLiveViewPreset,
  photoPresets,
  liveViewPresets,
  applyPresetMutationPending,
  createPresetMutationPending,
  socket,
  presetsData,
  onControlChange,
  onZoomChange,
  onResetControls,
  onApplyPhotoPreset,
  onApplyLiveViewPreset,
  onUpdateLiveViewPreset,
  onShowSaveModal,
  setLiveControls,
  setAfWindow,
  setSelectedPhotoPreset,
  setSelectedLiveViewPreset,
  debouncedEmitControl
}: CameraControlsProps) {

  return (
    <div className="absolute top-2 left-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg w-72 max-h-[calc(100vh-200px)] overflow-y-auto">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-gray-200">🎨 Live Controls</h3>
        <div className="flex gap-2">
          {selectedLiveViewPreset && presetsData?.presets?.find(p => p.name === selectedLiveViewPreset)?.category === 'user' && (
            <button
              onClick={onUpdateLiveViewPreset}
              disabled={createPresetMutationPending}
              className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              ✏️ Update
            </button>
          )}
          <button
            onClick={() => onShowSaveModal('liveview')}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            💾 Save As
          </button>
          <button
            onClick={onResetControls}
            className="px-2 py-1 text-xs bg-white/20 text-white rounded hover:bg-white/30"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Photo Preset Selector */}
      <div className="mb-3">
        <label className="block text-xs font-medium text-gray-200 mb-2">
          📸 Photo Preset (Capture) {applyPresetMutationPending && <span className="text-blue-300">(applying...)</span>}
        </label>
        <select
          value={selectedPhotoPreset}
          onChange={(e) => {
            const newValue = e.target.value
            setSelectedPhotoPreset(newValue)
            onApplyPhotoPreset(newValue)
          }}
          disabled={applyPresetMutationPending}
          className="w-full px-2 py-1 text-xs bg-white/10 text-white rounded border border-white/20 hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {photoPresets.map((preset) => (
            <option key={preset.name} value={preset.name}>
              {preset.display_name}
            </option>
          ))}
        </select>
      </div>

      {/* Live View Preset Selector */}
      <div className="mb-3 pb-3 border-b border-white/20">
        <label className="block text-xs font-medium text-gray-200 mb-2">
          🎥 Live View Preset (Stream) {applyPresetMutationPending && <span className="text-blue-300">(applying...)</span>}
        </label>
        <select
          value={selectedLiveViewPreset}
          onChange={async (e) => {
            const newValue = e.target.value
            try {
              await onApplyLiveViewPreset(newValue)
              setSelectedLiveViewPreset(newValue)
            } catch {
              // Error already handled in parent
            }
          }}
          disabled={applyPresetMutationPending}
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
            <span className="text-blue-300 font-mono">{(liveControls.sharpness ?? 1.0).toFixed(1)}</span>
          </label>
          <input
            type="range"
            min="0"
            max="4"
            step="0.1"
            value={liveControls.sharpness ?? 1.0}
            onChange={(e) => onControlChange(toPicameraControl('sharpness'), parseFloat(e.target.value))}
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
            <span className="text-blue-300 font-mono">{(liveControls.brightness ?? 0.0).toFixed(1)}</span>
          </label>
          <input
            type="range"
            min="-1"
            max="1"
            step="0.1"
            value={liveControls.brightness ?? 0.0}
            onChange={(e) => onControlChange(toPicameraControl('brightness'), parseFloat(e.target.value))}
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
            <span className="text-blue-300 font-mono">{(liveControls.contrast ?? 1.0).toFixed(1)}</span>
          </label>
          <input
            type="range"
            min="0"
            max="4"
            step="0.1"
            value={liveControls.contrast ?? 1.0}
            onChange={(e) => onControlChange(toPicameraControl('contrast'), parseFloat(e.target.value))}
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
            <span className="text-blue-300 font-mono">{(liveControls.saturation ?? 1.0).toFixed(1)}</span>
          </label>
          <input
            type="range"
            min="0"
            max="4"
            step="0.1"
            value={liveControls.saturation ?? 1.0}
            onChange={(e) => onControlChange(toPicameraControl('saturation'), parseFloat(e.target.value))}
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
              <span className="text-red-300 font-mono">{(liveControls.colourGainRed ?? 1.5).toFixed(3)}</span>
            </label>
            <input
              type="range"
              min="1.0"
              max="4.0"
              step="0.001"
              value={liveControls.colourGainRed ?? 1.5}
              onChange={(e) => onControlChange(toPicameraControl('colourGainRed'), parseFloat(e.target.value))}
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
              <span className="text-blue-300 font-mono">{(liveControls.colourGainBlue ?? 1.5).toFixed(3)}</span>
            </label>
            <input
              type="range"
              min="1.0"
              max="4.0"
              step="0.001"
              value={liveControls.colourGainBlue ?? 1.5}
              onChange={(e) => onControlChange(toPicameraControl('colourGainBlue'), parseFloat(e.target.value))}
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
              onControlChange(toPicameraControl('aeEnable'), newValue)
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

        {/* Manual Exposure Controls */}
        {!liveControls.aeEnable && (
          <>
            {/* Exposure Time Slider */}
            <div className="pt-2 mt-2">
              <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
                <span>⏱️ Exposure Time</span>
                <span className="text-orange-300 font-mono">{liveControls.exposureTime as number} µs</span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={(() => {
                  const exposure = (liveControls.exposureTime as number) || 500
                  const minLog = Math.log2(100)
                  const maxLog = Math.log2(200000)
                  const logValue = Math.log2(Math.max(100, Math.min(200000, exposure)))
                  return Math.round(((logValue - minLog) / (maxLog - minLog)) * 100)
                })()}
                onChange={(e) => {
                  const sliderValue = parseInt(e.target.value)
                  const minLog = Math.log2(100)
                  const maxLog = Math.log2(200000)
                  const logValue = minLog + (sliderValue / 100) * (maxLog - minLog)
                  const exposureTime = Math.round(Math.pow(2, logValue))
                  setLiveControls(prev => ({ ...prev, exposureTime: exposureTime }))
                  onControlChange(toPicameraControl('exposureTime'), exposureTime)
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
                <span className="text-orange-300 font-mono">{(liveControls.analogueGain ?? 1.0).toFixed(1)}x</span>
              </label>
              <input
                type="range"
                min="1"
                max="16"
                step="0.5"
                value={liveControls.analogueGain ?? 1.0}
                onChange={(e) => {
                  const newValue = parseFloat(e.target.value)
                  setLiveControls(prev => ({ ...prev, analogueGain: newValue }))
                  onControlChange(toPicameraControl('analogueGain'), newValue)
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

        {/* Metering Mode */}
        {liveControls.aeEnable && (
          <div className="pt-2 mt-2 border-t border-white/20">
            <label className="block text-xs font-medium text-gray-200 mb-1">
              📊 Metering Mode
            </label>
            <select
              value={liveControls.aeMeteringMode as number}
              onChange={(e) => onControlChange(toPicameraControl('aeMeteringMode'), parseInt(e.target.value))}
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

        {/* Focus Mode */}
        <div className="pt-2 mt-2 border-t border-white/20">
          <label className="block text-xs font-medium text-gray-200 mb-1">
            🎯 Focus Mode
          </label>
          <select
            value={liveControls.afMode as number}
            onChange={(e) => {
              const newValue = parseInt(e.target.value)
              setLiveControls(prev => ({ ...prev, afMode: newValue }))
              onControlChange(toPicameraControl('afMode'), newValue)
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

        {/* Manual Focus Slider */}
        {liveControls.afMode === 0 && (
          <div className="pt-2 mt-2">
            <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
              <span>🔍 Lens Position</span>
              <span className="text-orange-300 font-mono">{(liveControls.lensPosition ?? 0.0).toFixed(1)} dpt</span>
            </label>
            <input
              type="range"
              min="0"
              max="10"
              step="0.1"
              value={liveControls.lensPosition ?? 0.0}
              onChange={(e) => {
                const newValue = parseFloat(e.target.value)
                setLiveControls(prev => ({ ...prev, lensPosition: newValue }))
                onControlChange(toPicameraControl('lensPosition'), newValue)
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

        {/* AF Range */}
        {(liveControls.afMode === 1 || liveControls.afMode === 2) && (
          <div className="pt-2 mt-2">
            <label className="block text-xs font-medium text-gray-200 mb-1">
              📏 AF Range
            </label>
            <select
              value={liveControls.afRange as number}
              onChange={(e) => onControlChange(toPicameraControl('afRange'), parseInt(e.target.value))}
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

        {/* AF Speed */}
        {(liveControls.afMode === 1 || liveControls.afMode === 2) && (
          <div className="pt-2 mt-2">
            <label className="block text-xs font-medium text-gray-200 mb-1">
              ⚡ AF Speed
            </label>
            <select
              value={liveControls.afSpeed as number}
              onChange={(e) => onControlChange(toPicameraControl('afSpeed'), parseInt(e.target.value))}
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

        {/* Noise Reduction */}
        <div className="pt-2 mt-2 border-t border-white/20">
          <label className="flex justify-between items-center text-xs font-medium text-gray-200 mb-1">
            <span>Noise Reduction</span>
            <span className="text-blue-300 font-mono">
              {liveControls.noiseReductionMode === 0 ? 'Off' :
               liveControls.noiseReductionMode === 1 ? 'Fast' : 'High Quality'}
            </span>
          </label>
          <select
            value={liveControls.noiseReductionMode as number}
            onChange={(e) => onControlChange(toPicameraControl('noiseReductionMode'), parseInt(e.target.value))}
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
            onChange={(e) => onZoomChange(parseFloat(e.target.value))}
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
                    if (socket) {
                      socket.emit('set_af_window', { x: null, y: null })
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
              checked={liveControls.focusPeakingEnabled as boolean}
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
                  <span className="text-green-300 font-mono">{liveControls.focusPeakingIntensity as number}</span>
                </label>
                <input
                  type="range"
                  min="50"
                  max="200"
                  step="10"
                  value={liveControls.focusPeakingIntensity as number}
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
                  value={liveControls.focusPeakingColour as string}
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
                  value={liveControls.focusPeakingAlgorithm as string}
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
  )
}
