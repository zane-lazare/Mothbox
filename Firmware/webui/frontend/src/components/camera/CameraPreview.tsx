/**
 * CameraPreview Component
 *
 * Displays live camera feed with metadata overlay and AF window indicator.
 * Handles click-to-focus and zoom repositioning.
 */

import { AfWindow, CameraMetadata, LiveControls, ZoomCenter } from '../../types/camera'
import { Socket } from 'socket.io-client'
import toast from 'react-hot-toast'

interface CameraPreviewProps {
  currentFrame: string | null
  liveViewActive: boolean
  metadata: CameraMetadata | null
  afWindow: AfWindow | null
  zoomLevel: number
  zoomCenter: ZoomCenter
  liveControls: LiveControls
  socket: Socket | null
  onImageClick: (e: React.MouseEvent<HTMLImageElement>) => void
  setAfWindow: (window: AfWindow | null) => void
}

export default function CameraPreview({
  currentFrame,
  liveViewActive,
  metadata,
  afWindow,
  zoomLevel,
  zoomCenter,
  liveControls,
  socket,
  onImageClick,
  setAfWindow
}: CameraPreviewProps) {

  const handleClearAfWindow = () => {
    if (socket) {
      socket.emit('set_af_window', { x: null, y: null })
      setAfWindow(null)
      toast.success('AF window cleared')
    }
  }

  // Calculate AF window viewport position for rendering
  const calculateAfWindowPosition = () => {
    if (!afWindow || !afWindow.active) return null

    let markerViewportX: number
    let markerViewportY: number

    if (zoomLevel > 1.0) {
      const currentCenterX = metadata?.actual_zoom_center_x ?? zoomCenter.x
      const currentCenterY = metadata?.actual_zoom_center_y ?? zoomCenter.y
      const cropFractionX = metadata?.crop_fraction_x ?? (1.0 / zoomLevel)
      const cropFractionY = metadata?.crop_fraction_y ?? (1.0 / zoomLevel)

      markerViewportX = ((afWindow.x - currentCenterX) / cropFractionX) + 0.5
      markerViewportY = ((afWindow.y - currentCenterY) / cropFractionY) + 0.5
    } else {
      markerViewportX = afWindow.x
      markerViewportY = afWindow.y
    }

    return { x: markerViewportX, y: markerViewportY }
  }

  const afWindowPosition = calculateAfWindowPosition()

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden relative" style={{ minHeight: '600px' }}>
      {currentFrame ? (
        <>
          <img
            src={currentFrame}
            alt="Camera preview"
            className="w-full h-auto cursor-crosshair"
            onClick={onImageClick}
          />

          {/* Area of Interest Indicator */}
          {afWindow && afWindow.active && afWindowPosition && (
            <div
              className="absolute pointer-events-none"
              style={{
                left: `${afWindowPosition.x * 100}%`,
                top: `${afWindowPosition.y * 100}%`,
                transform: 'translate(-50%, -50%)',
                width: '20%',
                height: '20%'
              }}
            >
              <div className={`relative w-full h-full ${afWindow.focusing ? 'animate-pulse' : ''}`}>
                <div className="absolute inset-0 border-2 border-yellow-400 rounded">
                  <div className="absolute -top-1 -left-1 w-4 h-4 border-t-4 border-l-4 border-yellow-400"></div>
                  <div className="absolute -top-1 -right-1 w-4 h-4 border-t-4 border-r-4 border-yellow-400"></div>
                  <div className="absolute -bottom-1 -left-1 w-4 h-4 border-b-4 border-l-4 border-yellow-400"></div>
                  <div className="absolute -bottom-1 -right-1 w-4 h-4 border-b-4 border-r-4 border-yellow-400"></div>
                </div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                  <div className="w-6 h-0.5 bg-yellow-400"></div>
                  <div className="w-0.5 h-6 bg-yellow-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"></div>
                </div>
              </div>
            </div>
          )}

          {/* Metadata Overlay - Top Right */}
          {liveViewActive && metadata && !metadata.error && (
            <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white shadow-lg max-w-sm">
              <h4 className="text-sm font-semibold text-gray-200 mb-2">📊 Live Metadata</h4>

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
        </>
      ) : (
        <div className="h-96 flex items-center justify-center">
          <p className="text-gray-400">
            {liveViewActive ? 'Loading live view...' : 'Click "Start Live View" to begin'}
          </p>
        </div>
      )}
    </div>
  )
}
