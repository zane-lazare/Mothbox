import PropTypes from 'prop-types';
import MetadataField from './MetadataField';
import { formatISO, formatAperture, formatExposureTime, formatFocalLength } from '../../utils/metadataFormatters';

/**
 * CameraTab Component
 *
 * Displays camera and lens information along with technical camera settings
 * from photo metadata. Shows camera make/model, lens details, and exposure
 * parameters (ISO, aperture, shutter speed, focal length).
 *
 * @component
 * @param {Object} props - Component props
 * @param {Object|null} props.data - Full metadata object from backend API
 * @param {Object} [props.data.camera] - Camera and lens information
 * @param {string} [props.data.camera.make] - Camera manufacturer
 * @param {string} [props.data.camera.model] - Camera model
 * @param {string} [props.data.camera.lens] - Lens model
 * @param {Object} [props.data.capture] - Capture settings
 * @param {number} [props.data.capture.iso] - ISO sensitivity
 * @param {number} [props.data.capture.f_number] - Aperture f-number
 * @param {string} [props.data.capture.exposure_time] - Exposure time (e.g., "1/500")
 * @param {string} [props.data.capture.focal_length] - Focal length (e.g., "24mm")
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
const CameraTab = ({ data }) => {
  // Check if data is null or empty
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <p>No camera information available</p>
      </div>
    );
  }

  const camera = data.camera || {};
  const capture = data.capture || {};

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
  );
};

CameraTab.propTypes = {
  data: PropTypes.shape({
    camera: PropTypes.shape({
      make: PropTypes.string,
      model: PropTypes.string,
      lens: PropTypes.string,
      sensor: PropTypes.string,
    }),
    capture: PropTypes.shape({
      iso: PropTypes.number,
      f_number: PropTypes.number,
      exposure_time: PropTypes.string,
      focal_length: PropTypes.string,
      white_balance: PropTypes.string,
      flash: PropTypes.string,
      timestamp: PropTypes.string,
    }),
  }),
};

export default CameraTab;
