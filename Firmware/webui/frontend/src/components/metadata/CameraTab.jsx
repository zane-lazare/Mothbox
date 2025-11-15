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
 * @param {Object|null} props.data - Camera metadata object
 * @param {Object} [props.data.camera] - Camera and lens information
 * @param {string} [props.data.camera.make] - Camera manufacturer
 * @param {string} [props.data.camera.model] - Camera model
 * @param {string} [props.data.camera.lens_make] - Lens manufacturer
 * @param {string} [props.data.camera.lens_model] - Lens model
 * @param {number} [props.data.iso] - ISO sensitivity
 * @param {number} [props.data.aperture] - Aperture f-number
 * @param {number} [props.data.shutter_speed] - Shutter speed in seconds
 * @param {number} [props.data.focal_length] - Focal length in mm
 * @param {string} [props.data.exposure_mode] - Exposure mode (Auto, Manual, etc.)
 * @param {string} [props.data.metering_mode] - Metering mode (Spot, CenterWeighted, etc.)
 *
 * @example
 * const cameraData = {
 *   camera: {
 *     make: 'Arducam',
 *     model: 'OwlSight 64MP',
 *     lens_make: 'Arducam',
 *     lens_model: '6mm Wide Angle'
 *   },
 *   iso: 400,
 *   aperture: 2.8,
 *   shutter_speed: 0.033333,
 *   focal_length: 6.0,
 *   exposure_mode: 'Manual',
 *   metering_mode: 'CenterWeighted'
 * };
 *
 * <CameraTab data={cameraData} />
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

  return (
    <div className="space-y-6">
      {/* Camera Information Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 border-b pb-2">
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
            label="Lens Make"
            value={camera.lens_make || 'N/A'}
          />
          <MetadataField
            label="Lens Model"
            value={camera.lens_model || 'N/A'}
          />
        </div>
      </div>

      {/* Technical Settings Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 border-b pb-2">
          Camera Settings
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="ISO"
            value={data.iso !== undefined ? formatISO(data.iso) : 'N/A'}
            copyable={data.iso !== undefined}
          />
          <MetadataField
            label="Aperture"
            value={data.aperture !== undefined ? formatAperture(data.aperture) : 'N/A'}
            copyable={data.aperture !== undefined}
          />
          <MetadataField
            label="Shutter Speed"
            value={data.shutter_speed !== undefined ? formatExposureTime(data.shutter_speed) : 'N/A'}
            copyable={data.shutter_speed !== undefined}
          />
          <MetadataField
            label="Focal Length"
            value={data.focal_length !== undefined ? formatFocalLength(data.focal_length) : 'N/A'}
            copyable={data.focal_length !== undefined}
          />
          {data.exposure_mode && (
            <MetadataField
              label="Exposure Mode"
              value={data.exposure_mode}
            />
          )}
          {data.metering_mode && (
            <MetadataField
              label="Metering Mode"
              value={data.metering_mode}
            />
          )}
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
      lens_make: PropTypes.string,
      lens_model: PropTypes.string,
    }),
    iso: PropTypes.number,
    aperture: PropTypes.number,
    shutter_speed: PropTypes.number,
    focal_length: PropTypes.number,
    exposure_mode: PropTypes.string,
    metering_mode: PropTypes.string,
  }),
};

export default CameraTab;
