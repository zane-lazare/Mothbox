import PropTypes from 'prop-types'
import MetadataField from './MetadataField'
import { CameraIcon, SunIcon, MapPinIcon } from '@heroicons/react/24/outline'
import {
  formatISO,
  formatAperture,
  formatTimestamp,
  formatDecimalCoordinate,
} from '../../utils/metadataFormatters'

/**
 * MetadataEXIF Component
 *
 * Displays read-only EXIF metadata from photos in a consolidated view.
 * Consolidates content from CameraTab, CaptureTab, and DeploymentTab into
 * three main sections: Camera, Capture Settings, and Location/Deployment.
 *
 * All fields are READ-ONLY with copy-to-clipboard functionality for most values.
 *
 * @component
 * @param {Object} props - Component props
 * @param {Object} props.data - Full metadata object from backend API
 * @param {Object} [props.data.camera] - Camera information
 * @param {string} [props.data.camera.make] - Camera manufacturer
 * @param {string} [props.data.camera.model] - Camera model
 * @param {string} [props.data.camera.lens] - Lens model
 * @param {Object} [props.data.capture] - Capture settings
 * @param {number} [props.data.capture.iso] - ISO sensitivity
 * @param {string} [props.data.capture.exposure_time] - Exposure time (e.g., "1/500")
 * @param {number} [props.data.capture.f_number] - Aperture f-number
 * @param {string} [props.data.capture.focal_length] - Focal length (e.g., "6.0mm")
 * @param {string} [props.data.capture.exposure_mode] - Exposure mode
 * @param {string} [props.data.capture.white_balance] - White balance setting
 * @param {string} [props.data.capture.timestamp] - Capture timestamp
 * @param {Object} [props.data.location] - GPS location data
 * @param {number} [props.data.location.latitude] - Latitude in decimal degrees
 * @param {number} [props.data.location.longitude] - Longitude in decimal degrees
 * @param {number} [props.data.location.altitude] - Altitude in meters
 * @param {Object} [props.data.deployment] - Deployment information
 * @param {string} [props.data.deployment.mothbox_id] - Mothbox device ID
 * @param {string} [props.data.deployment.firmware_version] - Firmware version
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
export default function MetadataEXIF({ data = {} }) {
  const camera = data.camera || {}
  const capture = data.capture || {}
  const location = data.location || {}
  const deployment = data.deployment || {}

  /**
   * Format GPS coordinates as "lat° N/S, lon° E/W"
   * @param {number|null|undefined} lat - Latitude in decimal degrees
   * @param {number|null|undefined} lon - Longitude in decimal degrees
   * @returns {string|null} Formatted GPS string or null if invalid
   */
  const formatGPS = (lat, lon) => {
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
   * @param {number|null|undefined} alt - Altitude in meters
   * @returns {string|null} Formatted altitude or null if invalid
   */
  const formatAltitude = (alt) => {
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

MetadataEXIF.propTypes = {
  data: PropTypes.shape({
    camera: PropTypes.shape({
      make: PropTypes.string,
      model: PropTypes.string,
      lens: PropTypes.string,
      sensor: PropTypes.string,
    }),
    capture: PropTypes.shape({
      iso: PropTypes.number,
      exposure_time: PropTypes.string,
      f_number: PropTypes.number,
      focal_length: PropTypes.string,
      exposure_mode: PropTypes.string,
      white_balance: PropTypes.string,
      timestamp: PropTypes.string,
    }),
    location: PropTypes.shape({
      latitude: PropTypes.number,
      longitude: PropTypes.number,
      altitude: PropTypes.number,
    }),
    deployment: PropTypes.shape({
      mothbox_id: PropTypes.string,
      firmware_version: PropTypes.string,
    }),
  }),
}
