import MetadataField from './MetadataField'
import { formatISO, formatAperture } from '../../utils/metadataFormatters'

export interface CameraTabProps {
  data?: {
    camera?: {
      make?: string
      model?: string
      lens?: string
      sensor?: string
    }
    capture?: {
      iso?: number
      f_number?: number
      exposure_time?: string
      focal_length?: string
      white_balance?: string
      flash?: string
      timestamp?: string
    }
  } | null
}

/**
 * CameraTab Component
 *
 * Displays camera and lens information along with technical camera settings
 * from photo metadata. Shows camera make/model, lens details, and exposure
 * parameters (ISO, aperture, shutter speed, focal length).
 *
 * @example
 * const metadata = {
 *   camera: {
 *     make: 'Arducam',
 *     model: 'OwlSight 64MP',
 *     lens: '6mm Wide Angle'
 *   },
 *   capture: {
 *     iso: 400,
 *     f_number: 2.8,
 *     exposure_time: '1/500',
 *     focal_length: '6.0mm'
 *   }
 * };
 *
 * <CameraTab data={metadata} />
 */
const CameraTab = ({ data }: CameraTabProps) => {
  // Check if data is null or empty
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <p>No camera information available</p>
      </div>
    )
  }

  const camera = data.camera || {}
  const capture = data.capture || {}

  return (
    <div className="space-y-6">
      {/* Camera Information Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Camera Information
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Camera Make"
            value={camera.make || 'N/A'}
          />
          <MetadataField
            label="Camera Model"
            value={camera.model || 'N/A'}
          />
          <MetadataField
            label="Sensor"
            value={camera.sensor || 'N/A'}
          />
          <MetadataField
            label="Lens Model"
            value={camera.lens || 'N/A'}
          />
        </div>
      </div>

      {/* Technical Settings Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Camera Settings
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Gain (ISO)"
            value={capture.iso !== undefined && capture.iso !== null ? formatISO(capture.iso) : 'N/A'}
            copyable={capture.iso !== undefined && capture.iso !== null}
          />
          <MetadataField
            label="Aperture"
            value={capture.f_number !== undefined && capture.f_number !== null ? formatAperture(capture.f_number) : 'N/A'}
            copyable={capture.f_number !== undefined && capture.f_number !== null}
          />
          <MetadataField
            label="Exposure Time"
            value={capture.exposure_time || 'N/A'}
            copyable={!!capture.exposure_time}
          />
          <MetadataField
            label="Focal Length"
            value={capture.focal_length || 'N/A'}
            copyable={!!capture.focal_length}
          />
        </div>
      </div>
    </div>
  )
}

export default CameraTab
