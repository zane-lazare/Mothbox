/**
 * CalibrationPanel Component
 *
 * Quick actions for camera calibration: autofocus, calibrate, freeze settings.
 * Shows calibration progress and action results.
 */

import { ActionResult, CalibrationProgress } from '../../types/camera'

interface CalibrationPanelProps {
  autofocusing: boolean
  calibrating: boolean
  freezing: boolean
  copyingSettings: boolean
  testCapturing: boolean
  connected: boolean
  calibrationProgress: CalibrationProgress | null
  actionResult: ActionResult | null
  testCaptureResult: { success: boolean; test_photo_path?: string; metadata?: { exposure_time: number; analogue_gain: number; lens_position: number }; error?: string } | null
  onAutofocus: () => void
  onCalibrate: () => void
  onFreezeSettings: () => void
  onCopyLiveViewToCapture: () => void
  onCopyCaptureToLiveView: () => void
  onTestCapture: () => void
  children?: React.ReactNode
}

export default function CalibrationPanel({
  autofocusing,
  calibrating,
  freezing,
  copyingSettings,
  testCapturing,
  connected,
  calibrationProgress,
  actionResult,
  testCaptureResult,
  onAutofocus,
  onCalibrate,
  onFreezeSettings,
  onCopyLiveViewToCapture,
  onCopyCaptureToLiveView,
  onTestCapture,
  children
}: CalibrationPanelProps) {
  return (
    <>
      {/* Quick Actions Overlay - Bottom Left */}
      <div className="absolute bottom-2 left-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg w-64">
        <h3 className="text-sm font-semibold text-gray-200 mb-2">⚡ Quick Actions</h3>
        <div className="space-y-2">
          <button
            onClick={onAutofocus}
            disabled={autofocusing || !connected}
            className="w-full px-3 py-2 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:bg-gray-600 font-medium"
          >
            {autofocusing ? '🔍 Focusing...' : '🔍 Autofocus'}
          </button>
          <button
            onClick={onCalibrate}
            disabled={calibrating || !connected}
            className="w-full px-3 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-600 font-medium"
          >
            {calibrating ? '🔧 Calibrating...' : '🔧 Calibrate'}
          </button>
          <button
            onClick={onFreezeSettings}
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
            onClick={onCopyLiveViewToCapture}
            disabled={copyingSettings || !connected}
            className="w-full px-3 py-2 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-600 font-medium"
          >
            {copyingSettings ? 'Copying...' : '📹 Live View → 📷 Capture'}
          </button>
          <button
            onClick={onCopyCaptureToLiveView}
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
          onClick={onTestCapture}
          disabled={testCapturing || !connected}
          className="w-full px-3 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:bg-gray-600 font-medium"
        >
          {testCapturing ? '📸 Capturing...' : '🧪 Test Photo'}
        </button>

        {/* Instant Capture Button Slot */}
        {children}

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
            {testCaptureResult.success && testCaptureResult.metadata && (
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
    </>
  )
}
