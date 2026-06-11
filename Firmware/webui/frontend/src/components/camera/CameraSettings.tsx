/**
 * CameraSettings Component
 *
 * Displays camera settings summary and HDR status below the live preview.
 */

import { CameraSettings as CameraSettingsType } from '../../types/camera'

interface CameraSettingsProps {
  liveViewActive: boolean
  cameraSettings: CameraSettingsType | null
}

export default function CameraSettings({
  liveViewActive,
  cameraSettings
}: CameraSettingsProps) {
  return (
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
              parseInt(cameraSettings.HDR || '1') > 1
                ? 'bg-purple-600 text-white'
                : 'bg-gray-200 text-gray-600'
            }`}>
              {parseInt(cameraSettings.HDR || '1') === 1
                ? 'Single'
                : `${cameraSettings.HDR} Exp HDR`}
            </span>
          </div>
          {parseInt(cameraSettings.HDR || '1') > 1 && (
            <p className="mt-1 text-[10px] text-purple-700">
              Bracket: {cameraSettings.HDR_width || '7000'}µs · {cameraSettings.HDR} images
            </p>
          )}
        </div>
      )}
    </div>
  )
}
