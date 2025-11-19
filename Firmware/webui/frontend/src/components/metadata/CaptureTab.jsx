import PropTypes from 'prop-types';
import MetadataField from './MetadataField';
import { formatTimestamp } from '../../utils/metadataFormatters';

/**
 * CaptureTab Component
 *
 * Displays comprehensive photo capture metadata with technical nomenclature
 * aligned to live view camera controls.
 *
 * Sections:
 * - Capture Details: Timestamp, basic photo info
 * - Exposure Settings: Exposure mode, time, gain (ISO), metering
 * - Focus Settings: Focus mode, lens position, AF range/speed
 * - Image Processing: Noise reduction, sharpness, brightness, contrast, saturation
 * - Colour & Advanced: Aperture, colour gains, flash
 *
 * @component
 */
function CaptureTab({ data }) {
  // Handle null or undefined data
  if (!data) {
    return (
      <div className="text-gray-500 text-sm">
        No capture data available
      </div>
    );
  }

  const capture = data.capture || {};

  // Helper to check if value exists
  const hasValue = (val) => val !== undefined && val !== null;

  return (
    <div className="space-y-6">
      {/* Capture Details */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Capture Details
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Timestamp"
            value={formatTimestamp(capture.timestamp)}
            copyable={!!capture.timestamp}
          />
          <MetadataField
            label="Focal Length"
            value={capture.focal_length || 'N/A'}
            copyable={!!capture.focal_length}
          />
        </div>
      </div>

      {/* Exposure Settings */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Exposure Settings
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Exposure Mode"
            value={capture.exposure_mode || 'N/A'}
            copyable={false}
          />
          <MetadataField
            label="Exposure Time"
            value={capture.exposure_time || 'N/A'}
            copyable={!!capture.exposure_time}
          />
          <MetadataField
            label="Gain (ISO)"
            value={hasValue(capture.iso) ? capture.iso.toString() : 'N/A'}
            copyable={hasValue(capture.iso)}
          />
          {capture.exposure_mode === 'Auto' && (
            <MetadataField
              label="Metering Mode"
              value={capture.metering_mode || 'N/A'}
              copyable={false}
            />
          )}
        </div>
      </div>

      {/* Focus Settings */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Focus Settings
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Focus Mode"
            value={capture.focus_mode || 'N/A'}
            copyable={false}
          />
          {capture.focus_mode === 'Manual' && hasValue(capture.lens_position) && (
            <MetadataField
              label="Lens Position"
              value={`${capture.lens_position.toFixed(2)} diopters`}
              copyable={true}
            />
          )}
          {(capture.focus_mode === 'Auto Single' || capture.focus_mode === 'Continuous AF') && (
            <>
              <MetadataField
                label="AF Range"
                value={capture.af_range || 'N/A'}
                copyable={false}
              />
              <MetadataField
                label="AF Speed"
                value={capture.af_speed || 'N/A'}
                copyable={false}
              />
            </>
          )}
        </div>
      </div>

      {/* Image Processing */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Image Processing
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Noise Reduction"
            value={capture.noise_reduction || 'N/A'}
            copyable={false}
          />
          <MetadataField
            label="Sharpness"
            value={hasValue(capture.sharpness) ? capture.sharpness.toString() : 'N/A'}
            copyable={hasValue(capture.sharpness)}
          />
          <MetadataField
            label="Brightness"
            value={hasValue(capture.brightness) ? capture.brightness.toFixed(2) : 'N/A'}
            copyable={hasValue(capture.brightness)}
          />
          <MetadataField
            label="Contrast"
            value={hasValue(capture.contrast) ? capture.contrast.toString() : 'N/A'}
            copyable={hasValue(capture.contrast)}
          />
          <MetadataField
            label="Saturation"
            value={hasValue(capture.saturation) ? capture.saturation.toString() : 'N/A'}
            copyable={hasValue(capture.saturation)}
          />
        </div>
      </div>

      {/* Colour & Advanced */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Colour & Advanced
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Aperture"
            value={capture.f_number || 'N/A'}
            copyable={!!capture.f_number}
          />
          <MetadataField
            label="Colour Balance"
            value={capture.white_balance || 'N/A'}
            copyable={!!capture.white_balance}
          />
          {hasValue(capture.colour_gain_red) && (
            <MetadataField
              label="Red Gain"
              value={capture.colour_gain_red.toFixed(3)}
              copyable={true}
            />
          )}
          {hasValue(capture.colour_gain_blue) && (
            <MetadataField
              label="Blue Gain"
              value={capture.colour_gain_blue.toFixed(3)}
              copyable={true}
            />
          )}
          <MetadataField
            label="Flash"
            value={hasValue(capture.flash)
              ? (capture.flash ? 'Fired' : 'Did not fire')
              : 'N/A'}
            copyable={false}
          />
        </div>
      </div>
    </div>
  );
}

CaptureTab.propTypes = {
  /**
   * Full metadata object from backend API
   */
  data: PropTypes.shape({
    capture: PropTypes.shape({
      // Capture Details
      timestamp: PropTypes.string,
      focal_length: PropTypes.string,

      // Exposure Settings
      exposure_mode: PropTypes.string,
      exposure_time: PropTypes.string,
      iso: PropTypes.number,
      metering_mode: PropTypes.string,

      // Focus Settings
      focus_mode: PropTypes.string,
      lens_position: PropTypes.number,
      af_range: PropTypes.string,
      af_speed: PropTypes.string,

      // Image Processing
      noise_reduction: PropTypes.string,
      sharpness: PropTypes.number,
      brightness: PropTypes.number,
      contrast: PropTypes.number,
      saturation: PropTypes.number,

      // Colour & Advanced
      f_number: PropTypes.string,
      white_balance: PropTypes.string,
      colour_gain_red: PropTypes.number,
      colour_gain_blue: PropTypes.number,
      flash: PropTypes.bool,
    }),
  }),
};

export default CaptureTab;
