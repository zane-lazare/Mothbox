import MetadataField from './MetadataField'
import { CameraIcon, SunIcon, MapPinIcon } from '@heroicons/react/24/outline'
import {
  formatISO,
  formatAperture,
  formatTimestamp,
  formatDecimalCoordinate,
} from '../../utils/metadataFormatters'

export interface MetadataEXIFProps {
  data?: {
    camera?: {
      make?: string
      model?: string
      lens?: string
      sensor?: string
    }
    capture?: {
      iso?: number
      exposure_time?: string
      f_number?: number
      focal_length?: string
      exposure_mode?: string
      white_balance?: string
      timestamp?: string
    }
    location?: {
      latitude?: number
      longitude?: number
      altitude?: number
    }
    deployment?: {
      mothbox_id?: string
      firmware_version?: string
    }
  }
}

/**
 * MetadataEXIF Component
 *
 * Displays read-only EXIF metadata from photos in a consolidated view.
 * Consolidates content from CameraTab, CaptureTab, and DeploymentTab into
 * three main sections: Camera, Capture Settings, and Location/Deployment.
 *
 * All fields are READ-ONLY with copy-to-clipboard functionality for most values.
 *
 * @example
 * const metadata = {
 *   camera: { make: 'Arducam', model: 'OwlSight 64MP', lens: '6mm Wide Angle' },
 *   capture: { iso: 400, exposure_time: '1/500', f_number: 2.8 },
 *   location: { latitude: 37.7749, longitude: -122.4194, altitude: 10.5 },
 *   deployment: { mothbox_id: 'mothbox-backyard', firmware_version: '5' }
 * };
 * <MetadataEXIF data={metadata} />
 */
export default function MetadataEXIF({ data = {} }: MetadataEXIFProps) {
  const camera = data.camera || {}
  const capture = data.capture || {}
  const location = data.location || {}
  const deployment = data.deployment || {}

  /**
   * Format GPS coordinates as "lat° N/S, lon° E/W"
   */
  const formatGPS = (lat?: number | null, lon?: number | null): string | null => {
    if (lat == null || lon == null) return null

    const latDir = lat >= 0 ? 'N' : 'S'
    const lonDir = lon >= 0 ? 'E' : 'W'

    // Use formatDecimalCoordinate for consistent 6 decimal places
    const latFormatted = formatDecimalCoordinate(Math.abs(lat))
    const lonFormatted = formatDecimalCoordinate(Math.abs(lon))

    return `${latFormatted}° ${latDir}, ${lonFormatted}° ${lonDir}`
  }

  /**
   * Format altitude as "Xm" or "X.Xm"
   */
  const formatAltitude = (alt?: number | null): string | null => {
    if (alt == null) return null
    // Don't show decimal for whole numbers
    const formatted = alt % 1 === 0 ? alt.toString() : alt.toFixed(1)
    return `${formatted}m`
  }

  return (
    <div className="space-y-4">
      {/* Camera Section */}
      <div>
        <h4 className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          <CameraIcon className="w-4 h-4" />
          Camera
        </h4>
        <div className="space-y-1 pl-6">
          <MetadataField label="Make" value={camera.make} copyable />
          <MetadataField label="Model" value={camera.model} copyable />
          <MetadataField label="Lens" value={camera.lens} copyable />
        </div>
      </div>

      {/* Capture Settings Section */}
      <div>
        <h4 className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          <SunIcon className="w-4 h-4" />
          Capture Settings
        </h4>
        <div className="space-y-1 pl-6">
          <MetadataField
            label="ISO"
            value={capture.iso !== undefined && capture.iso !== null ? formatISO(capture.iso) : null}
            copyable
          />
          <MetadataField
            label="Shutter Speed"
            value={capture.exposure_time}
            copyable
          />
          <MetadataField
            label="Aperture"
            value={capture.f_number !== undefined && capture.f_number !== null ? formatAperture(capture.f_number) : null}
            copyable
          />
          <MetadataField
            label="Focal Length"
            value={capture.focal_length}
            copyable
          />
          <MetadataField
            label="Exposure Mode"
            value={capture.exposure_mode}
            copyable
          />
          <MetadataField
            label="White Balance"
            value={capture.white_balance}
            copyable
          />
          <MetadataField
            label="Captured"
            value={formatTimestamp(capture.timestamp)}
            copyable
          />
        </div>
      </div>

      {/* Location/Deployment Section */}
      <div>
        <h4 className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          <MapPinIcon className="w-4 h-4" />
          Location &amp; Deployment
        </h4>
        <div className="space-y-1 pl-6">
          <MetadataField
            label="GPS"
            value={formatGPS(location.latitude, location.longitude)}
            copyable
            testId="gps-coordinates"
          />
          <MetadataField
            label="Altitude"
            value={formatAltitude(location.altitude)}
            copyable
          />
          <MetadataField
            label="Deployment"
            value={deployment.mothbox_id}
            copyable
          />
          <MetadataField
            label="Device"
            value={deployment.firmware_version}
            copyable
          />
        </div>
      </div>
    </div>
  )
}
